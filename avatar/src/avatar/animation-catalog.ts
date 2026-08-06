import { animationFilesByEvent, type AssetManifest } from '../../shared/animations'

export type AnimationType = string

export type AnimationCatalog = Record<string, readonly string[]>

let pending: Promise<AnimationCatalog> | null = null

export function loadAnimationCatalog(
  fetchManifest: () => Promise<AssetManifest> = defaultFetch,
): Promise<AnimationCatalog> {
  pending ??= fetchManifest()
    .then(animationFilesByEvent)
    .catch((error) => {
      pending = null
      throw error
    })
  return pending
}

function defaultFetch(): Promise<AssetManifest> {
  return fetch('./assets/manifest.json').then((response) => {
    if (!response.ok) throw new Error(`manifest.json returned ${response.status}`)
    return response.json() as Promise<AssetManifest>
  })
}

export function resetAnimationCatalog(): void {
  pending = null
}

export function randomAnimation(choices: readonly string[]): string {
  return choices[Math.floor(Math.random() * choices.length)]!
}

export function nextAnimation(
  choices: readonly string[],
  previous: string | null = null,
): string {
  const previousIndex = previous == null ? -1 : choices.indexOf(previous)
  return choices[(previousIndex + 1) % choices.length]!
}
