import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import {
  VRMAnimationLoaderPlugin,
  createVRMAnimationClip,
  type VRMAnimation,
} from '@pixiv/three-vrm-animation'
import type { VRM } from '@pixiv/three-vrm'
import * as THREE from 'three'
import { nextAnimation, type AnimationType } from './animation-catalog'
import {
  configureAnimationAction,
  crossFadeAnimationActions,
  type AnimationPlayback,
} from './animation-action'

export interface PlayOptions {
  onComplete?: () => void
  playback?: AnimationPlayback
}

export interface VrmAnimator {
  play(type: AnimationType, options?: PlayOptions): Promise<void>
  update(delta: number): void
  isClipDriving(): boolean
  dispose(): void
}

interface PendingCompletion {
  action: THREE.AnimationAction
  callback: () => void
  generation: number
}

function transitionSeconds(previous: AnimationType | null, next: AnimationType): number {
  if (previous === 'TALK' && next === 'IDLE') return 1.15
  if (next === 'TALK') return 0.85
  return 0.7
}

export function createVrmAnimator(vrm: VRM): VrmAnimator {
  const cache = new Map<string, VRMAnimation>()
  const previousAnimation = new Map<AnimationType, string>()
  let mixer: THREE.AnimationMixer | null = new THREE.AnimationMixer(vrm.scene)
  let current: THREE.AnimationAction | null = null
  let currentType: AnimationType | null = null
  let requestGeneration = 0
  let pendingCompletion: PendingCompletion | null = null

  const handleFinished = ({ action }: { action: THREE.AnimationAction }) => {
    const pending = pendingCompletion
    if (pending?.action !== action || pending.generation !== requestGeneration) return
    pendingCompletion = null
    pending.callback()
  }
  mixer.addEventListener('finished', handleFinished as never)

  async function load(path: string): Promise<VRMAnimation> {
    const cached = cache.get(path)
    if (cached) return cached
    const loader = new GLTFLoader()
    loader.register((parser) => new VRMAnimationLoaderPlugin(parser))
    const gltf = await loader.loadAsync(`./assets/animations/${path}`)
    const animation = gltf.userData.vrmAnimations?.[0] as VRMAnimation | undefined
    if (!animation) throw new Error(`No VRM animation found in ${path}`)
    cache.set(path, animation)
    return animation
  }

  return {
    async play(type, { onComplete, playback = 'loop' }: PlayOptions = {}) {
      if (!mixer) {
        if (playback === 'once') onComplete?.()
        return
      }
      const generation = ++requestGeneration
      pendingCompletion = null
      try {
        const path = nextAnimation(type, previousAnimation.get(type) ?? null)
        previousAnimation.set(type, path)
        const animation = await load(path)
        if (generation !== requestGeneration || !mixer) return
        const action = mixer.clipAction(createVRMAnimationClip(animation, vrm))
        const fadeSeconds = transitionSeconds(currentType, type)
        action.reset()
        configureAnimationAction(action, playback)
        if (playback === 'once' && onComplete) {
          pendingCompletion = { action, callback: onComplete, generation }
        }
        crossFadeAnimationActions(current, action, fadeSeconds)
        current = action
        currentType = type
      } catch (error) {
        console.warn('[avatar] animation load failed', error)
        if (generation === requestGeneration && playback === 'once') {
          window.setTimeout(() => {
            if (generation === requestGeneration) onComplete?.()
          }, 2400)
        }
      }
    },
    update(delta) {
      mixer?.update(delta)
    },
    isClipDriving() {
      return current != null && current.getEffectiveWeight() > 0
    },
    dispose() {
      mixer?.removeEventListener('finished', handleFinished as never)
      mixer?.stopAllAction()
      mixer = null
      current = null
      currentType = null
      pendingCompletion = null
      cache.clear()
      previousAnimation.clear()
    },
  }
}
