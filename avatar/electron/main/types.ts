export type VoicePhase = 'inactive' | 'starting' | 'active' | 'stopping'
export type VoiceActivity = 'idle' | 'listening' | 'speaking'

export interface VoiceState {
  activity: VoiceActivity
  microphoneMuted: boolean
  outputMuted: boolean
  phase: VoicePhase
}

export type BridgeAnimation = string

export interface AudioListenerStatus {
  available: boolean
  capturing: boolean
  error?: string
  monitoring: boolean
  source: string | null
}

export type BridgeEvent =
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

export interface AudioListener {
  start(): Promise<void>
  stop(): void
}

export interface AudioListenerCallbacks {
  onActivity?: (activity: VoiceActivity) => void
  onDebug?: ((detail: unknown) => void) | null
  onLevel?: (level: number) => void
  onSession?: (active: boolean) => void
  onStatus?: (status: AudioListenerStatus) => void
}
