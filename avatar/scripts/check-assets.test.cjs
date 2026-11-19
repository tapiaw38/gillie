'use strict'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const test = require('node:test')
const {
  MANIFEST_PATH,
  assetPaths,
  roleErrors,
  validateAssets,
} = require('./check-assets.cjs')

function readManifest() {
  return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'))
}

function createFixture(context) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'avatar-assets-'))
  const assetRoot = path.join(root, 'assets')
  fs.mkdirSync(assetRoot, { recursive: true })
  const manifestPath = path.join(assetRoot, 'manifest.json')
  fs.copyFileSync(MANIFEST_PATH, manifestPath)
  context.after(() => fs.rmSync(root, { recursive: true, force: true }))
  return { assetRoot, manifestPath }
}

test('development accepts the complete local set or no media', (context) => {
  assert.deepEqual(validateAssets(), [])
  const fixture = createFixture(context)
  assert.deepEqual(validateAssets(fixture), [])
})

test('every manifest asset carries a role and sits where its role implies', () => {
  assert.deepEqual(roleErrors(readManifest()), [])
})

test('an animation listed outside the animations directory is rejected', () => {
  const errors = roleErrors({
    assets: [
      { path: 'model.vrm', role: 'model' },
      { path: 'dance.vrma', role: 'dance' },
    ],
  })
  assert.ok(errors.some((error) => error.includes('not under animations/')))
})

test('a manifest without exactly one model is rejected', () => {
  assert.ok(
    roleErrors({ assets: [{ path: 'animations/idle.vrma', role: 'idle' }] }).some(
      (error) => error.includes('exactly one model asset'),
    ),
  )
})

test('development rejects a partial local media set', (context) => {
  const fixture = createFixture(context)
  const partial = path.join(fixture.assetRoot, assetPaths(readManifest())[1])
  fs.mkdirSync(path.dirname(partial), { recursive: true })
  fs.writeFileSync(partial, 'local test media')
  assert.ok(
    validateAssets(fixture).some((error) =>
      error.includes('Runtime asset files do not match'),
    ),
  )
})

test('test-only assets are rejected by the release gate', () => {
  const errors = validateAssets({ release: true })
  assert.ok(errors.some((error) => error.includes('distribution is disabled')))
  assert.ok(errors.some((error) => error.includes('Incomplete release license metadata')))
})
