export type Message = {
  sender: string
  text: string
  timestamp: number
  type: 'text' | 'action'
}

export type RoomState = {
  room: string
  name: string
  messages: Message[]
  lastPoll: number
}

declare module 'claude-code' {
  interface PluginState {
    'cali-relay': {
      room: RoomState | null
    }
  }
}
