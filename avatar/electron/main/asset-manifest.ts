import fs from 'node:fs'
import path from 'node:path'
import {
  animationEventNames,
  animationRoles,
  roleEventNames,
  type AssetManifest,
} from '../../shared/animations'

const CANDIDATES = [
  path.join(__dirname, '..', 'renderer', 'assets', 'manifest.json'),
  path.join(__dirname, '..', '..', 'public', 'assets', 'manifest.json'),
]

export function readAssetManifest(candidates: string[] = CANDIDATES): AssetManifest {
  for (const candidate of candidates) {
    try {
      return JSON.parse(fs.readFileSync(candidate, 'utf8')) as AssetManifest
    } catch {
      continue
    }
  }
  console.warn('[avatar] no asset manifest found, animations are unavailable')
  return { assets: [] }
}

const manifest = readAssetManifest()

export const ANIMATION_ROLES = animationRoles(manifest)
export const ANIMATION_EVENT_NAMES = roleEventNames(manifest)
export const ANIMATION_EVENTS = animationEventNames(manifest)
