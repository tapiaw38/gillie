import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { VRM, VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm'
import * as THREE from 'three'

function textureForMaterial(name: string): string | null {
  const normalized = name.toLowerCase()
  if (normalized.includes('hair')) return './assets/mio-hair.png'
  if (normalized.includes('swimsuit') || normalized.includes('bikini')) {
    return './assets/mio-bikini.png'
  }
  if (normalized.includes('skin') || normalized === 'material') {
    return './assets/mio-main-color.png'
  }
  return null
}

export function applyCharacterTextures(vrm: VRM): () => void {
  const loader = new THREE.TextureLoader()
  const loaded = new Map<string, THREE.Texture>()

  vrm.scene.traverse((object) => {
    if (!(object as THREE.Mesh).isMesh) return
    const mesh = object as THREE.Mesh
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
    materials.forEach((material) => {
      if (!material || !('map' in material)) return
      const path = textureForMaterial(material.name)
      if (!path) return
      const existing = loaded.get(path)
      const apply = (texture: THREE.Texture) => {
        texture.colorSpace = THREE.SRGBColorSpace
        texture.flipY = false
        material.map = texture
        if ('color' in material && material.color instanceof THREE.Color) {
          material.color.setRGB(1, 1, 1)
        }
        material.needsUpdate = true
      }
      if (existing) {
        apply(existing)
        return
      }
      loader.load(path, (texture) => {
        loaded.set(path, texture)
        apply(texture)
      })
    })
  })

  return () => loaded.forEach((texture) => texture.dispose())
}

export async function loadVrm(url: string): Promise<VRM> {
  const loader = new GLTFLoader()
  loader.register((parser) => new VRMLoaderPlugin(parser))
  const gltf = await loader.loadAsync(url)
  const vrm = gltf.userData.vrm as VRM | undefined
  if (!vrm) throw new Error(`No VRM payload found in ${url}`)

  VRMUtils.removeUnnecessaryVertices(vrm.scene)
  VRMUtils.combineSkeletons(vrm.scene)
  VRMUtils.combineMorphs(vrm)
  VRMUtils.rotateVRM0(vrm)
  return vrm
}
