import type { BridgeAnimation, BridgeEvent, VoiceActivity, VoicePhase } from './types'
import { ANIMATION_EVENT_NAMES } from './asset-manifest'

export type ProtocolCommand =
  | { type: 'show' | 'hide' | 'toggle' }
  | { type: 'event'; event: BridgeEvent }

export function voiceState(
  activity: VoiceActivity,
  phase: VoicePhase = 'active',
): BridgeEvent {
  return {
    type: 'state',
    state: {
      activity,
      microphoneMuted: false,
      outputMuted: false,
      phase,
    },
  }
}

export function parseProtocolUrl(
  rawUrl: string,
  protocolScheme = 'avatar',
): ProtocolCommand[] | null {
  try {
    const url = new URL(rawUrl)
    if (url.protocol !== `${protocolScheme}:`) return null
    const action = (url.hostname || url.pathname.replace(/^\/+/, '')).toLowerCase()
    if (action === 'show' || action === 'hide' || action === 'toggle') {
      return [{ type: action }]
    }
    if (action === 'listening') {
      return [{ type: 'event', event: voiceState('listening') }]
    }
    if (action === 'speaking') {
      const commands: ProtocolCommand[] = [
        { type: 'event', event: voiceState('speaking') },
      ]
      const level = Number(url.searchParams.get('level'))
      if (Number.isFinite(level)) {
        commands.push({
          type: 'event',
          event: { type: 'audio-level', level: Math.max(0, Math.min(1, level)) },
        })
      }
      return commands
    }
    if (action === 'thinking') {
      return [{ type: 'event', event: voiceState('idle') }]
    }
    if (action === 'inactive' || action === 'stop') {
      return [{ type: 'event', event: voiceState('idle', 'inactive') }]
    }
    const animation: BridgeAnimation | undefined = ANIMATION_EVENT_NAMES[action]
    if (animation) {
      return [{ type: 'event', event: { type: 'animation', animation } }]
    }
    return null
  } catch {
    return null
  }
}
