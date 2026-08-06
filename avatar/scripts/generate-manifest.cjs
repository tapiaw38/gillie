'use strict'

const fs = require('node:fs')
const path = require('node:path')

const PROJECT_ROOT = path.join(__dirname, '..')
const ASSET_ROOT = path.join(PROJECT_ROOT, 'public', 'assets')
const MANIFEST_PATH = path.join(ASSET_ROOT, 'manifest.json')

function listMedia(directory = ASSET_ROOT, prefix = '') {
  if (!fs.existsSync(directory)) return []
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relative = path.posix.join(prefix, entry.name)
    const absolute = path.join(directory, entry.name)
    if (entry.isDirectory()) return listMedia(absolute, relative)
    return /\.(?:vrm|vrma)$/i.test(entry.name) ? [relative] : []
  }).sort()
}

function roleFor(relative) {
  const filename = path.posix.basename(relative).replace(/\.(?:vrm|vrma)$/i, '')
  if (filename === 'model') return 'model'
  return filename.replace(/[-_ ]?\d+$/, '')
}

function generateManifest({ assetRoot = ASSET_ROOT, manifestPath = MANIFEST_PATH } = {}) {
  const previous = fs.existsSync(manifestPath)
    ? JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
    : {}
  const previousByPath = new Map((previous.assets ?? []).map((asset) => [asset.path, asset]))
  const assets = listMedia(assetRoot).sort((left, right) => {
    if (left === 'model.vrm') return -1
    if (right === 'model.vrm') return 1
    return left.localeCompare(right)
  }).map((assetPath) => {
    const old = previousByPath.get(assetPath) ?? {}
    return {
      path: assetPath,
      role: roleFor(assetPath),
      ...(old.license !== undefined ? { license: old.license } : { license: null }),
      ...(old.source !== undefined ? { source: old.source } : { source: null }),
    }
  })
  if (assets.filter((asset) => asset.role === 'model').length !== 1) {
    throw new Error('Expected exactly one public/assets/model.vrm')
  }
  const next = {
    schemaVersion: previous.schemaVersion ?? 1,
    proceduralMotion: previous.proceduralMotion ?? true,
    distributionAllowed: previous.distributionAllowed ?? false,
    notice: previous.notice ?? 'Character media is intentionally not committed.',
    assets,
  }
  const serialized = `${JSON.stringify(next, null, 2)}\n`
  const current = fs.existsSync(manifestPath) ? fs.readFileSync(manifestPath, 'utf8') : ''
  if (serialized !== current) fs.writeFileSync(manifestPath, serialized)
  return next
}

if (require.main === module) {
  try {
    const manifest = generateManifest()
    console.log(`Generated assets/manifest.json (${manifest.assets.length} media assets).`)
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error))
    process.exitCode = 1
  }
}

module.exports = { ASSET_ROOT, MANIFEST_PATH, listMedia, roleFor, generateManifest }
