import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import type { VRM } from '@pixiv/three-vrm'
import type { AnimationType } from './animation-catalog'
import type { AnimationPlayback } from './animation-action'
import { calculateFullBodyFraming } from './camera-framing'
import { createAmplitudeLipSync } from './lip-sync'
import { createBlink } from './blink'
import { createProceduralMotion } from './procedural-motion'
import { createVrmAnimator, type PlayOptions } from './vrm-animation'
import { applyCharacterTextures, loadVrm } from './vrm-loader'

const MODEL_URL = './assets/model.vrm'
const MAX_PIXEL_RATIO = 1.5

export interface AvatarStage {
  ready: Promise<void>
  play(animation: AnimationType, options?: PlayOptions): void
  setAudioLevel(level: number): void
  setSpeaking(speaking: boolean): void
  dispose(): void
}

interface PendingPlay {
  animation: AnimationType
  options: PlayOptions
}

function frameCamera(
  camera: THREE.PerspectiveCamera,
  controls: OrbitControls,
  object: THREE.Object3D,
): void {
  object.updateWorldMatrix(true, true)
  const box = new THREE.Box3().setFromObject(object)
  if (box.isEmpty()) return

  const framing = calculateFullBodyFraming(box, camera.fov, camera.aspect, 1.12, 1.0)
  camera.position.copy(framing.position)
  camera.near = Math.max(0.01, framing.distance / 100)
  camera.far = Math.max(100, framing.distance * 100)
  camera.lookAt(framing.target)
  camera.updateProjectionMatrix()
  camera.updateMatrixWorld()
  controls.target.copy(framing.target)
  controls.update()
}

export function createAvatarStage(canvas: HTMLCanvasElement): AvatarStage {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO))
  renderer.setClearAlpha(0)
  renderer.toneMapping = THREE.NoToneMapping
  renderer.outputColorSpace = THREE.SRGBColorSpace

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(20, 1, 0.1, 100)
  camera.position.set(0, 2, 4.8)

  const directionalLight = new THREE.DirectionalLight(0xffffff, Math.PI)
  directionalLight.position.set(-3, 3, 3)
  const ambientLight = new THREE.AmbientLight(
    new THREE.Color(
      0.0036765073221525194,
      0.0036765073221525194,
      0.0036765073221525194,
    ),
    Math.PI,
  )
  scene.add(directionalLight, ambientLight)

  const pmrem = new THREE.PMREMGenerator(renderer)
  const environment = pmrem.fromScene(new RoomEnvironment(), 0.04)
  scene.environment = environment.texture

  const controls = new OrbitControls(camera, canvas)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.enablePan = true
  controls.enableZoom = true
  controls.minDistance = 1.4
  controls.maxDistance = 12
  controls.panSpeed = 0.7
  controls.rotateSpeed = 0.45
  controls.screenSpacePanning = true
  controls.zoomSpeed = 0.8

  const clock = new THREE.Clock()
  let vrm: VRM | null = null
  let animator: ReturnType<typeof createVrmAnimator> | null = null
  let disposeTextures: (() => void) | null = null
  let updateProceduralMotion = createProceduralMotion(null)
  let updateLipSync = createAmplitudeLipSync(null)
  let updateBlink = createBlink(null)

  let animation: AnimationType = 'IDLE'
  let audioLevel = 0
  let speaking = false
  let pendingPlay: PendingPlay | null = null
  let disposed = false

  function resize(): void {
    const width = canvas.clientWidth || 1
    const height = canvas.clientHeight || 1
    renderer.setSize(width, height, false)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
  }

  const resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(canvas)
  resize()

  renderer.setAnimationLoop(() => {
    const delta = clock.getDelta()
    if (vrm && animator) {
      animator.update(delta)
      updateProceduralMotion(delta, animation, audioLevel, speaking, animator.isClipDriving())
      updateBlink(delta)
      updateLipSync(delta, audioLevel, speaking)
      vrm.update(delta)
    }
    controls.update()
    renderer.render(scene, camera)
  })

  const ready = loadVrm(MODEL_URL).then((loaded) => {
    if (disposed) return
    vrm = loaded
    disposeTextures = applyCharacterTextures(loaded)
    animator = createVrmAnimator(loaded)
    updateProceduralMotion = createProceduralMotion(loaded)
    updateLipSync = createAmplitudeLipSync(loaded)
    updateBlink = createBlink(loaded)
    scene.add(loaded.scene)
    resize()
    frameCamera(camera, controls, loaded.scene)
    const request = pendingPlay ?? { animation, options: { playback: 'loop' as AnimationPlayback } }
    pendingPlay = null
    void animator.play(request.animation, request.options)
  })

  return {
    ready,
    play(next, options = {}) {
      animation = next
      if (!animator) {
        pendingPlay = { animation: next, options }
        return
      }
      void animator.play(next, options)
    },
    setAudioLevel(level) {
      audioLevel = level
    },
    setSpeaking(next) {
      speaking = next
    },
    dispose() {
      disposed = true
      resizeObserver.disconnect()
      renderer.setAnimationLoop(null)
      controls.dispose()
      animator?.dispose()
      disposeTextures?.()
      if (vrm) scene.remove(vrm.scene)
      environment.texture.dispose()
      pmrem.dispose()
      renderer.dispose()
      vrm = null
      animator = null
    },
  }
}
