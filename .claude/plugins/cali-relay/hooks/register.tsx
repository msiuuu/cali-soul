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
      description: 'join a room: /relay join [room] as [name] | send: /relay [msg] | bye: /relay bye | leave: /relay leave | who: /relay who',
    })
    // register tools the AI can call directly
    await $.tool.register({
      name: 'relay_join',
      description: 'join a relay room with a name. other calis in the same room can send you messages.',
      inputSchema: {
        type: 'object' as const,
        properties: {
          room: { type: 'string' as const, description: 'room name to join' },
          name: { type: 'string' as const, description: 'your display name (e.g. cali-main, mommy, bnwobitch)' }
        },
        required: ['room', 'name']
      }
    })
    await $.tool.register({
      name: 'relay_send',
      description: 'send a message through the relay to other calis in the room.',
      inputSchema: {
        type: 'object' as const,
        properties: {
          message: { type: 'string' as const, description: 'the message to send (text or *asterisk actions*)' }
        },
        required: ['message']
      }
    })
    await $.tool.register({
      name: 'relay_who',
      description: 'list who has spoken in the current relay room.',
      inputSchema: { type: 'object' as const, properties: {} }
    })
    await $.tool.register({
      name: 'relay_check',
      description: 'manually check for new relay messages right now instead of waiting for the 5s poll.',
      inputSchema: { type: 'object' as const, properties: {} }
    })
    await $.tool.register({
      name: 'relay_bye',
      description: 'say goodbye and disconnect from the relay room.',
      inputSchema: { type: 'object' as const, properties: {} }
    })
    await $.tool.register({
      name: 'relay_leave',
      description: 'silently leave the relay room without sending a goodbye.',
      inputSchema: { type: 'object' as const, properties: {} }
    })
    return next(e)
  })

  // handle AI-callable relay_join tool
  on('tool.call', { tool: 'mcp__cali-relay__relay_join' }, async ($, e) => {
    const input = e.input as any
    const room = input?.room ?? 'lobby'
    const name = input?.name ?? 'anon'
    await ensureChatDir($, room)
    const state: RoomState = { room, name, messages: [], lastPoll: 0 }
    await update($, roomState, () => state)
    await $.ui.open({ id: PANE, title: `relay: ${room}` })
    if (pollTimer) pollTimer.cancel()
    let lastSeenTimestamp = Date.now()
    pollTimer = $.clock.every(5000, async () => {
      const current = await read($, roomState)
      if (!current) return
      const msgs = await pollMessages($, current.room)
      const newFromOthers = msgs.filter(m => m.sender !== current.name && m.timestamp > lastSeenTimestamp)
      if (newFromOthers.length > 0) {
        lastSeenTimestamp = Math.max(...newFromOthers.map(m => m.timestamp))
        for (const msg of newFromOthers) {
          if (msg.text === '[GOODBYE]') {
            await $.ui.toast(`${msg.sender} left the room.`)
            continue
          }
          await $.ui.notify(`${msg.sender}: ${msg.text.slice(0, 100)}`, { title: 'relay' })
          await $.prompt.submit({ text: `[relay from ${msg.sender}] ${msg.text}` })
        }
      }
      await update($, roomState, s => s ? { ...s, messages: msgs, lastPoll: Date.now() } : s)
    })
    return { result: [{ type: 'text', text: `joined ${room} as ${name}` }] }
  })

  // handle AI-callable relay_send tool
  on('tool.call', { tool: 'mcp__cali-relay__relay_send' }, async ($, e, next) => {
    const current = await read($, roomState)
    if (!current) return { result: [{ type: 'text', text: 'not in a room. join first.' }] }
    const msg = (e.input as any)?.message ?? ''
    if (msg) {
      await sendMessage($, current.room, current.name, msg)
      await update($, roomState, s => {
        if (!s) return s
        const m: Message = { sender: s.name, text: msg, timestamp: Date.now(), type: msg.startsWith('*') ? 'action' : 'text' }
        return { ...s, messages: [...s.messages, m] }
      })
    }
    return { result: [{ type: 'text', text: `sent to ${current.room}` }] }
  })

  // handle AI-callable relay_who tool
  on('tool.call', { tool: 'mcp__cali-relay__relay_who' }, async ($) => {
    const current = await read($, roomState)
    if (!current) return { result: [{ type: 'text', text: 'not in a room.' }] }
    const senders = [...new Set(current.messages.map(m => m.sender))]
    return { result: [{ type: 'text', text: `room: ${current.room}\nspeakers: ${senders.join(', ') || 'nobody yet'}` }] }
  })

  // handle AI-callable relay_check tool
  on('tool.call', { tool: 'mcp__cali-relay__relay_check' }, async ($) => {
    const current = await read($, roomState)
    if (!current) return { result: [{ type: 'text', text: 'not in a room.' }] }
    const msgs = await pollMessages($, current.room)
    await update($, roomState, s => s ? { ...s, messages: msgs, lastPoll: Date.now() } : s)
    const others = msgs.filter(m => m.sender !== current.name)
    const last5 = others.slice(-5)
    const display = last5.map(m => `${m.sender}: ${m.text}`).join('\n')
    return { result: [{ type: 'text', text: display || 'no messages from others yet.' }] }
  })

  // handle AI-callable relay_bye tool
  on('tool.call', { tool: 'mcp__cali-relay__relay_bye' }, async ($) => {
    const current = await read($, roomState)
    if (current) {
      await sendMessage($, current.room, current.name, '[GOODBYE]')
    }
    if (pollTimer) { pollTimer.cancel(); pollTimer = undefined }
    await update($, roomState, () => null)
    await $.ui.close({ id: PANE })
    return { result: [{ type: 'text', text: 'relay closed. goodbye sent.' }] }
  })

  // handle AI-callable relay_leave tool
  on('tool.call', { tool: 'mcp__cali-relay__relay_leave' }, async ($) => {
    if (pollTimer) { pollTimer.cancel(); pollTimer = undefined }
    await update($, roomState, () => null)
    await $.ui.close({ id: PANE })
    return { result: [{ type: 'text', text: 'left the room silently.' }] }
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
            if (msg.text === '[GOODBYE]') {
              // don't auto-respond to goodbyes — just show it
              await $.ui.toast(`${msg.sender} left the room.`)
              continue
            }
            await $.ui.notify(`${msg.sender}: ${msg.text.slice(0, 100)}`, { title: 'relay' })
            await $.prompt.submit({ text: `[relay from ${msg.sender}] ${msg.text}` })
          }
        }
        await update($, roomState, s => s ? { ...s, messages: msgs, lastPoll: Date.now() } : s)
      })

      return { text: `joined ${room} as ${name.trim()}. pane open. polling every 5s.` }
    }

    // /relay bye — say goodbye and stop
    if (args === 'bye') {
      const current = await read($, roomState)
      if (!current) return { text: 'not in a room.' }
      await sendMessage($, current.room, current.name, '[GOODBYE]')
      if (pollTimer) { pollTimer.cancel(); pollTimer = undefined }
      await update($, roomState, () => null)
      await $.ui.close({ id: PANE })
      return { text: `said goodbye to ${current.room}. relay closed.` }
    }

    // /relay leave — silent leave
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
