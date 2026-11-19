import type { VRM } from '@pixiv/three-vrm'
import * as THREE from 'three'
import type { AnimationType } from './animation-catalog'

type BoneName =
  | 'hips'
  | 'chest'
  | 'leftUpperArm'
  | 'rightUpperArm'
  | 'leftLowerArm'
  | 'rightLowerArm'

const BONE_NAMES: readonly BoneName[] = [
  'hips',
  'chest',
  'leftUpperArm',
  'rightUpperArm',
  'leftLowerArm',
  'rightLowerArm',
]

export interface ProceduralMotionState {
  animation: AnimationType
  audioLevel: number
  baseRotations: Map<BoneName, THREE.Quaternion>
  clipDriving: boolean
  speaking: boolean
  time: number
}

export function applyProceduralMotion(vrm: VRM | null, state: ProceduralMotionState): void {
  const { animation, audioLevel, baseRotations, clipDriving, speaking, time } = state
  if (!vrm?.humanoid) return
  const talking = speaking || animation === 'TALK'
  const energy = talking ? Math.min(1, Math.max(audioLevel * 2.5, 0.18)) : 0
  const wave = Math.sin(time * (talking ? 4.2 : 1.4))
  const blend = clipDriving ? 0.35 : 1
  const yaw = clipDriving ? 0 : 1

  const rotate = (name: BoneName, x: number, y: number, z: number) => {
    const bone = vrm.humanoid?.getNormalizedBoneNode(name)
    const base = baseRotations.get(name)
    if (!bone || !base) return
    const offset = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(x * blend, y * blend, z * blend),
    )
    if (clipDriving) {
      bone.quaternion.multiply(offset)
    } else {
      bone.quaternion.copy(base).multiply(offset)
    }
  }

  rotate(
    'chest',
    Math.sin(time * 1.5) * 0.025 + energy * 0.018,
    Math.sin(time * 0.8) * 0.02 * yaw,
    0,
  )
  rotate('hips', 0, Math.sin(time * 0.8) * 0.025 * yaw, Math.sin(time * 0.7) * 0.018 * yaw)
  const rest = clipDriving ? 0 : 0.48
  rotate('leftUpperArm', -energy * 0.12 + wave * energy * 0.08, 0, rest - energy * 0.16)
  rotate('rightUpperArm', energy * 0.12 - wave * energy * 0.08, 0, -rest + energy * 0.16)
  rotate('leftLowerArm', -energy * 0.08 + wave * energy * 0.1, 0, 0)
  rotate('rightLowerArm', energy * 0.08 - wave * energy * 0.1, 0, 0)

  if (!clipDriving && (animation === 'HAPPY' || animation === 'DANCE')) {
    const bounce = Math.abs(Math.sin(time * 3.2)) * (animation === 'DANCE' ? 0.16 : 0.08)
    const beat = animation === 'DANCE' ? 0.32 : 0.18
    rotate('hips', bounce, Math.sin(time * 2.4) * beat, Math.sin(time * 2.4) * beat * 0.65)
    rotate('leftUpperArm', -0.35 + wave * beat, 0, 0.1)
    rotate('rightUpperArm', 0.35 - wave * beat, 0, -0.1)
  }
}

export type ProceduralMotionUpdate = (
  delta: number,
  animation: AnimationType,
  audioLevel: number,
  speaking: boolean,
  clipDriving?: boolean,
) => void

export function createProceduralMotion(vrm: VRM | null): ProceduralMotionUpdate {
  let elapsed = 0
  const baseRotations = new Map<BoneName, THREE.Quaternion>()

  if (vrm?.humanoid) {
    for (const name of BONE_NAMES) {
      const bone = vrm.humanoid.getNormalizedBoneNode(name)
      if (bone) baseRotations.set(name, bone.quaternion.clone())
    }
  }

  return (delta, animation, audioLevel, speaking, clipDriving = false) => {
    elapsed += delta
    applyProceduralMotion(vrm, {
      animation,
      audioLevel,
      baseRotations,
      clipDriving,
      speaking,
      time: elapsed,
    })
  }
}
