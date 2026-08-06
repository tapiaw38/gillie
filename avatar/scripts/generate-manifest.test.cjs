'use strict'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const test = require('node:test')
const { generateManifest, roleFor } = require('./generate-manifest.cjs')

test('derives pose roles from real media filenames', () => {
  assert.equal(roleFor('animations/dance1.vrma'), 'dance')
  assert.equal(roleFor('animations/talk2.vrma'), 'talk')
  assert.equal(roleFor('animations/kneel.vrma'), 'kneel')
})

test('generates manifest from media and preserves existing metadata', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'avatar-manifest-'))
  const assetRoot = path.join(root, 'assets')
  const manifestPath = path.join(assetRoot, 'manifest.json')
  fs.mkdirSync(path.join(assetRoot, 'animations'), { recursive: true })
  fs.writeFileSync(path.join(assetRoot, 'model.vrm'), '')
  fs.writeFileSync(path.join(assetRoot, 'animations', 'kneel.vrma'), '')
  fs.writeFileSync(
    manifestPath,
    JSON.stringify({
      distributionAllowed: false,
      assets: [{ path: 'animations/kneel.vrma', license: 'CC0-1.0', source: 'test' }],
    }),
  )

  try {
    const result = generateManifest({ assetRoot, manifestPath })
    assert.deepEqual(result.assets, [
      { path: 'model.vrm', role: 'model', license: null, source: null },
      {
        path: 'animations/kneel.vrma',
        role: 'kneel',
        license: 'CC0-1.0',
        source: 'test',
      },
    ])
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
