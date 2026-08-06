import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  loadAnimationCatalog,
  nextAnimation,
  randomAnimation,
  resetAnimationCatalog,
} from './animation-catalog'
import { animationFilesByEvent, type AssetManifest } from '../../shared/animations'

function installedManifest(): AssetManifest {
  return JSON.parse(
    readFileSync(
      join(__dirname, '..', '..', 'public', 'assets', 'manifest.json'),
      'utf8',
    ),
  )
}

describe('Gillie Avatar animation contract', () => {
  beforeEach(() => {
    resetAnimationCatalog()
  })

  it('derives every playable clip from the shipped asset manifest', async () => {
    const catalog = await loadAnimationCatalog(async () => installedManifest())

    expect(catalog).toEqual(animationFilesByEvent(installedManifest()))
    expect(catalog.IDLE).toEqual(['idle.vrma'])
    expect(catalog.TALK).toHaveLength(3)
    expect(catalog.FINGER_GUN).toEqual(['finger-gun.vrma'])
  })

  it('never lists the model itself as something to play', async () => {
    const catalog = await loadAnimationCatalog(async () => installedManifest())

    expect(Object.keys(catalog)).not.toContain('MODEL')
    expect(Object.values(catalog).flat()).not.toContain('model.vrm')
  })

  it('picks up a new clip from the manifest without touching the code', async () => {
    const catalog = await loadAnimationCatalog(async () => ({
      assets: [
        { path: 'model.vrm', role: 'model' },
        { path: 'animations/dance1.vrma', role: 'dance' },
        { path: 'animations/dance2.vrma', role: 'dance' },
      ],
    }))

    expect(catalog.DANCE).toEqual(['dance1.vrma', 'dance2.vrma'])
  })

  it('reads the manifest once and reuses it', async () => {
    const fetchManifest = vi.fn(async () => installedManifest())
    await loadAnimationCatalog(fetchManifest)
    await loadAnimationCatalog(fetchManifest)

    expect(fetchManifest).toHaveBeenCalledTimes(1)
  })

  it('retries after a failed read instead of caching the failure', async () => {
    await expect(
      loadAnimationCatalog(async () => {
        throw new Error('offline')
      }),
    ).rejects.toThrow('offline')

    await expect(
      loadAnimationCatalog(async () => installedManifest()),
    ).resolves.toHaveProperty('IDLE')
  })

  it('can select the last clip of a category without escaping it', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.999)
    expect(randomAnimation(['talk1.vrma', 'talk2.vrma', 'talk3.vrma'])).toBe('talk3.vrma')
    vi.restoreAllMocks()
  })

  it('cycles through every clip without consecutive repeats', () => {
    const choices = ['talk1.vrma', 'talk2.vrma', 'talk3.vrma']
    const first = nextAnimation(choices)
    const second = nextAnimation(choices, first)
    const third = nextAnimation(choices, second)

    expect([first, second, third]).toEqual(choices)
    expect(nextAnimation(choices, third)).toBe(first)
  })
})
