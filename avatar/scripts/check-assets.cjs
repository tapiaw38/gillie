'use strict'

const fs = require('node:fs')
const path = require('node:path')

const PROJECT_ROOT = path.join(__dirname, '..')
const ASSET_ROOT = path.join(PROJECT_ROOT, 'public', 'assets')
const MANIFEST_PATH = path.join(ASSET_ROOT, 'manifest.json')
const MODEL_ROLE = 'model'
const ANIMATION_PREFIX = 'animations/'

function assetPaths(manifest) {
  return (manifest.assets ?? []).map((asset) => asset.path).sort()
}

function roleErrors(manifest) {
  const errors = []
  const models = []
  for (const asset of manifest.assets ?? []) {
    const label = asset.path ?? 'unknown asset'
    if (typeof asset.role !== 'string' || asset.role.trim() === '') {
      errors.push(`Missing asset role for ${label}.`)
      continue
    }
    if (asset.role === MODEL_ROLE) {
      models.push(label)
    } else if (!String(asset.path).startsWith(ANIMATION_PREFIX)) {
      errors.push(
        `Asset ${label} has role ${asset.role} but is not under ${ANIMATION_PREFIX}.`,
      )
    }
  }
  if (models.length !== 1) {
    errors.push(`Expected exactly one ${MODEL_ROLE} asset, found ${models.length}.`)
  }
  return errors
}

function listRuntimeAssets(directory = ASSET_ROOT, prefix = '') {
  if (!fs.existsSync(directory)) return []
  return fs
    .readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const relative = path.posix.join(prefix, entry.name)
      const absolute = path.join(directory, entry.name)
      if (entry.isDirectory()) return listRuntimeAssets(absolute, relative)
      return /\.(?:vrm|vrma)$/i.test(entry.name) ? [relative] : []
    })
    .sort()
}

function validateAssets({
  release = false,
  assetRoot = ASSET_ROOT,
  manifestPath = MANIFEST_PATH,
} = {}) {
  const errors = []
  let manifest
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
  } catch (error) {
    return [`Cannot read assets/manifest.json: ${error.message}`]
  }

  const expected = assetPaths(manifest)
  const actual = listRuntimeAssets(assetRoot)
  const mediaAbsent = actual.length === 0
  const proceduralOnly =
    !release &&
    manifest.proceduralMotion === true &&
    JSON.stringify(actual) === JSON.stringify(['model.vrm'])
  errors.push(...roleErrors(manifest))
  if (
    (!mediaAbsent || release) &&
    !proceduralOnly &&
    JSON.stringify(actual) !== JSON.stringify(expected)
  ) {
    errors.push("Runtime asset files do not match Gillie Avatar's stable asset contract.")
  }

  if ((!mediaAbsent && !proceduralOnly) || release) {
    for (const relative of expected) {
      const absolute = path.join(assetRoot, relative)
      if (!fs.existsSync(absolute) || fs.statSync(absolute).size === 0) {
        errors.push(`Missing or empty asset: ${relative}`)
      }
    }
  }

  if (release) {
    if (manifest.distributionAllowed !== true) {
      errors.push(
        'Asset distribution is disabled. Replace the test-only files and set distributionAllowed to true.',
      )
    }
    for (const asset of manifest.assets ?? []) {
      if (
        typeof asset.license !== 'string' ||
        asset.license.trim() === '' ||
        typeof asset.source !== 'string' ||
        asset.source.trim() === '' ||
        asset.source === 'local-test-only'
      ) {
        errors.push(
          `Incomplete release license metadata: ${asset.path ?? 'unknown asset'}`,
        )
      }
    }
  }
  return errors
}

if (require.main === module) {
  const release = process.argv.includes('--release')
  const errors = validateAssets({ release })
  if (errors.length > 0) {
    for (const error of errors) console.error(`- ${error}`)
    process.exitCode = 1
  } else {
    console.log(
      release
        ? 'Gillie Avatar assets are complete and marked for distribution.'
        : 'Gillie Avatar asset contract is valid (local character media may be absent).',
    )
  }
}

module.exports = {
  ASSET_ROOT,
  MANIFEST_PATH,
  assetPaths,
  listRuntimeAssets,
  roleErrors,
  validateAssets,
}
