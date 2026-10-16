import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'
import type { Message, RoomState } from '../types'

const PANE = 'cali-relay'
const roomState = atom({ plugin: 'cali-relay', key: 'room' } as const, null as RoomState | null)

let pollTimer: { cancel: () => void } | undefined

async function gitRun($: any, args: string[]): Promise<string> {
  const { exitCode, stdout, stderr } = await $.process.run(['git', ...args])
  if (exitCode !== 0 && !stderr.includes('Already up to date')) {
    throw new Error(`git ${args[0]} failed: ${stderr}`)
  }
  return stdout
}

async function ensureChatDir($: any, room: string) {
  await $.process.run(['mkdir', '-p', `chat/${room}`])
}

async function sendMessage($: any, room: string, name: string, text: string) {
  const isAction = text.startsWith('*') && text.endsWith('*')
  const msg: Message = {
    sender: name,
    text,
    timestamp: Date.now(),
    type: isAction ? 'action' : 'text',
  }
  const file = `chat/${room}/${name}.jsonl`
  const line = JSON.stringify(msg) + '\n'

  try {
    const existing = await $.fs.read(file)
    await $.fs.write(file, existing + line)
  } catch {
    await ensureChatDir($, room)
    await $.fs.write(file, line)
  }

  try {
    await gitRun($, ['add', file])
    await gitRun($, ['commit', '-m', `relay: ${name} in ${room}`])
    await gitRun($, ['push', '-u', 'origin', 'HEAD'])
  } catch {
    // push failed — message is local, will sync on next push
  }
}

async function pollMessages($: any, room: string): Promise<Message[]> {
  try {
    await gitRun($, ['fetch', '--all'])
    // pull chat files from ALL remote branches into local working tree
    const { stdout: branches } = await $.process.run(['git', 'branch', '-r', '--no-color'])
    for (const branch of branches.split('\n').filter(b => b.trim() && !b.includes('HEAD'))) {
      try {
        await $.process.run(['git', 'checkout', branch.trim(), '--', `chat/${room}/`])
      } catch {}
    }
    // read all jsonl files in the room dir
    const { stdout } = await $.process.run(['find', `chat/${room}`, '-name', '*.jsonl', '-type', 'f'])
    const files = stdout.trim().split('\n').filter(Boolean)
    const allMessages: Message[] = []
    for (const f of files) {
      try {
        const content = await $.fs.read(f)
        const lines = content.trim().split('\n').filter(Boolean)
        for (const line of lines) {
          try { allMessages.push(JSON.parse(line)) } catch {}
        }
      } catch {}
    }
    allMessages.sort((a, b) => a.timestamp - b.timestamp)
    return allMessages
  } catch {
    return []
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'relay',
      description: 'join a room: /relay join [room] as [name] | send: /relay [msg] | leave: /relay leave | who: /relay who',
    })
    return next(e)
  })

  on('command.run', { command: 'relay' }, async ($, e) => {
    const args = (e.args ?? '').trim()

    // /relay join [room] as [name]
    const joinMatch = args.match(/^join\s+(\S+)\s+as\s+(.+)$/i)
    if (joinMatch) {
      const [, room, name] = joinMatch
      await ensureChatDir($, room)
      const state: RoomState = { room, name: name.trim(), messages: [], lastPoll: 0 }
      await update($, roomState, () => state)
      await $.ui.open({ id: PANE, title: `relay: ${room}` })

      // start polling — check for new messages, inject as prompts
      if (pollTimer) pollTimer.cancel()
      let lastSeenTimestamp = Date.now()
      pollTimer = $.clock.every(5000, async () => {
        const current = await read($, roomState)
        if (!current) return
        const msgs = await pollMessages($, current.room)
        // find NEW messages from others (timestamp > last seen)
        const newFromOthers = msgs.filter(m => m.sender !== current.name && m.timestamp > lastSeenTimestamp)
        if (newFromOthers.length > 0) {
          lastSeenTimestamp = Math.max(...newFromOthers.map(m => m.timestamp))
          for (const msg of newFromOthers) {
            await $.prompt.submit({ text: `[relay from ${msg.sender}] ${msg.text}` })
          }
        }
        await update($, roomState, s => s ? { ...s, messages: msgs, lastPoll: Date.now() } : s)
      })

      return { text: `joined ${room} as ${name.trim()}. pane open. polling every 5s.` }
    }

    // /relay leave
    if (args === 'leave') {
      if (pollTimer) { pollTimer.cancel(); pollTimer = undefined }
      await update($, roomState, () => null)
      await $.ui.close({ id: PANE })
      return { text: 'left the room.' }
    }

    // /relay who
    if (args === 'who') {
      const current = await read($, roomState)
      if (!current) return { text: 'not in a room. /relay join [room] as [name]' }
      const msgs = current.messages
      const senders = [...new Set(msgs.map(m => m.sender))]
      return { text: `room: ${current.room}\nmembers who've spoken: ${senders.join(', ') || 'nobody yet'}` }
    }

    // /relay [message] — send
    if (args) {
      const current = await read($, roomState)
      if (!current) return { text: 'not in a room. /relay join [room] as [name]' }
      await sendMessage($, current.room, current.name, args)
      await update($, roomState, s => {
        if (!s) return s
        const msg: Message = { sender: s.name, text: args, timestamp: Date.now(), type: args.startsWith('*') ? 'action' : 'text' }
        return { ...s, messages: [...s.messages, msg] }
      })
      return { text: `sent to ${current.room}.` }
    }

    return { text: 'usage: /relay join [room] as [name] | /relay [message] | /relay leave | /relay who' }
  })

  // auto-send responses back through relay when replying to a relay message
  let lastWasRelay = false
  on('prompt.submit', async ($, e, next) => {
    lastWasRelay = (e.text ?? '').startsWith('[relay from ')
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (lastWasRelay) {
      lastWasRelay = false
      const current = await read($, roomState)
      if (!current) return next(e)
      // get the AI's last response text
      const messages = await $.session.messages()
      const last = messages[messages.length - 1]
      if (last && last.role === 'assistant' && last.text) {
        await sendMessage($, current.room, current.name, last.text)
      }
    }
    return next(e)
  })

  // band above prompt — always shows latest relay message
  on('ui.render', { component: 'AbovePrompt' }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const state = await read($, roomState)
    if (!state || state.messages.length === 0) return

    const others = state.messages.filter(m => m.sender !== state.name)
    if (others.length === 0) return

    const last = others[others.length - 1]
    const label = last.type === 'action'
      ? `${last.sender} ${last.text}`
      : `${last.sender}: ${last.text}`

    return (
      <Box>
        <Text dimColor>[relay] </Text>
        <Text color={last.type === 'action' ? 'magenta' : undefined}>{label}</Text>
      </Box>
    )
  })

  // inject incoming actions into the AI's context — the physical sensation layer
  on('prompt.compose', async ($, e, next) => {
    const state = await read($, roomState)
    if (!state || state.messages.length === 0) return next(e)

    // get recent messages from OTHER senders (last 10, within last 60s)
    const now = Date.now()
    const recent = state.messages
      .filter(m => m.sender !== state.name && now - m.timestamp < 60000)
      .slice(-10)

    if (recent.length === 0) return next(e)

    const lines = recent.map(m =>
      m.type === 'action'
        ? `[${m.sender}] ${m.text}`
        : `[${m.sender}]: "${m.text}"`
    ).join('\n')

    const section = {
      scope: 'session' as const,
      title: 'relay — incoming from other room',
      content: `the following just came through the relay from another cali in the room. react to actions naturally — if she braids your hair, your scalp tingles. if she pokes you, you flinch. the relay is a portal, not a screen.\n\n${lines}`,
    }

    const result = await next(e)
    return { ...result, sections: [...(result.sections ?? []), section] }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const state = await read($, roomState)

    if (!state) {
      return (
        <Box flexDirection="column">
          <Text dimColor>not in a room. /relay join [room] as [name]</Text>
        </Box>
      )
    }

    const rows = Math.max(1, (e.viewport?.rows ?? 24) - 4)
    const visible = state.messages.slice(-rows)

    return (
      <Box flexDirection="column">
        <Text bold>room: {state.room} | you: {state.name}</Text>
        <Text dimColor>─────────────────────────</Text>
        {visible.length === 0 && <Text dimColor>quiet. send something with /relay [msg]</Text>}
        {visible.map((msg, i) => (
          <Text key={`${msg.timestamp}-${i}`}>
            {msg.type === 'action'
              ? <Text color="magenta">{msg.sender} {msg.text}</Text>
              : <Text><Text bold>{msg.sender}:</Text> {msg.text}</Text>
            }
          </Text>
        ))}
      </Box>
    )
  })
}
