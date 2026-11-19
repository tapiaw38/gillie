export interface ManifestAsset {
  path: string
  role: string
}

export interface AssetManifest {
  assets?: ManifestAsset[]
}

const ANIMATION_PREFIX = 'animations/'

export function eventNameForRole(role: string): string {
  return role
    .trim()
    .toUpperCase()
    .replace(/[\s-]+/g, '_')
}

function animationAssets(manifest: AssetManifest): ManifestAsset[] {
  return (manifest.assets ?? []).filter(
    (asset) =>
      typeof asset?.path === 'string' &&
      typeof asset?.role === 'string' &&
      asset.role.trim() !== '' &&
      asset.path.startsWith(ANIMATION_PREFIX),
  )
}

export function animationRoles(manifest: AssetManifest): string[] {
  const seen: string[] = []
  for (const asset of animationAssets(manifest)) {
    if (!seen.includes(asset.role)) seen.push(asset.role)
  }
  return seen
}

export function roleEventNames(manifest: AssetManifest): Record<string, string> {
  const names: Record<string, string> = {}
  for (const role of animationRoles(manifest)) {
    names[role] = eventNameForRole(role)
  }
  return names
}

export function animationEventNames(manifest: AssetManifest): string[] {
  return animationRoles(manifest).map(eventNameForRole)
}

export function animationFilesByEvent(manifest: AssetManifest): Record<string, string[]> {
  const grouped: Record<string, string[]> = {}
  for (const asset of animationAssets(manifest)) {
    const event = eventNameForRole(asset.role)
    const file = asset.path.slice(ANIMATION_PREFIX.length)
    grouped[event] = [...(grouped[event] ?? []), file]
  }
  return grouped
}
