export type VoicePhase = 'inactive' | 'starting' | 'active' | 'stopping'
export type VoiceActivity = 'idle' | 'listening' | 'speaking'

export interface VoiceState {
  activity: VoiceActivity
  locator?: { conversationId?: string; hostId?: string } | null
  microphoneMuted: boolean
  outputMuted: boolean
  phase: VoicePhase
  preferredPresentationSurface?: string | null
  sessionId?: string | null
}

export interface AudioListenerStatus {
  available: boolean
  capturing: boolean
  error?: string
  monitoring: boolean
  source: string | null
}

export type BridgeAnimation =
  | 'IDLE'
  | 'GREETING'
  | 'TALK'
  | 'HAPPY'
  | 'FINGER_GUN'
  | 'DANCE'

export type AvatarBridgeEvent =
  | { type: 'state'; state: VoiceState }
  | { type: 'audio-level'; level: number; bands?: Record<string, number> }
  | {
      type: 'animation'
      animation: BridgeAnimation
      source?: 'mcp'
      requestId?: number
    }
  | { type: 'listener-status'; status: AudioListenerStatus }
  | { type: 'bridge-status'; connected: boolean }

export interface AvatarBridge {
  zoom: number
  getSnapshot(): Promise<AvatarBridgeEvent | null>
  hide(): void
  subscribe(listener: (event: AvatarBridgeEvent) => void): () => void
}

declare global {
  interface Window {
    avatarBridge?: AvatarBridge
  }
}
