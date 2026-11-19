import type { VRM } from '@pixiv/three-vrm'

const VISEMES = ['aa', 'ee', 'ih', 'oh', 'ou'] as const

export type LipSyncUpdate = (delta: number, level: number, speaking: boolean) => void

export function createAmplitudeLipSync(vrm: VRM | null): LipSyncUpdate {
  let smoothed = 0
  let phase = 0

  return (delta: number, level: number, speaking: boolean) => {
    if (!vrm?.expressionManager) return
    const audible = speaking && level > 0.008
    const normalized = audible ? Math.min(1, Math.max(0, level) * 2.8) : 0
    const smoothing = 1 - Math.exp(-delta / (normalized > smoothed ? 0.055 : 0.1))
    smoothed += (normalized - smoothed) * smoothing
    phase += delta * (8 + smoothed * 9)
    const active = Math.floor(phase) % VISEMES.length

    for (let index = 0; index < VISEMES.length; index += 1) {
      const shape = Math.max(0, 1 - Math.abs(index - active) * 0.72)
      const flutter = 0.74 + Math.sin(phase * 5.7 + index) * 0.18
      vrm.expressionManager.setValue(
        VISEMES[index],
        Math.min(0.62, smoothed * shape * flutter),
      )
    }
  }
}
