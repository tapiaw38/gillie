import type { VRM } from '@pixiv/three-vrm'

const MIN_INTERVAL = 2
const MAX_INTERVAL = 6
const DURATION = 0.24

function nextInterval(): number {
  return MIN_INTERVAL + Math.random() * (MAX_INTERVAL - MIN_INTERVAL)
}

export type BlinkUpdate = (delta: number) => void

export function createBlink(vrm: VRM | null): BlinkUpdate {
  let next = nextInterval()
  let progress = 0

  return (delta: number) => {
    if (!vrm?.expressionManager) return
    if (progress > 0) {
      progress += delta / DURATION
      if (progress >= 1) {
        progress = 0
        next = nextInterval()
        vrm.expressionManager.setValue('blink', 0)
      } else {
        vrm.expressionManager.setValue('blink', Math.sin(progress * Math.PI))
      }
      return
    }
    next -= delta
    if (next <= 0) progress = Number.EPSILON
  }
}
