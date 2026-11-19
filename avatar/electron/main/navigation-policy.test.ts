import assert from 'node:assert/strict'
import { test } from 'vitest'
import { isAllowedRendererNavigation } from './navigation-policy'

test('allows only the renderer entry or its development origin', () => {
  assert.equal(
    isAllowedRendererNavigation(
      'file:///opt/GillieAvatar/resources/app.asar/out/renderer/index.html#view',
      'file:///opt/GillieAvatar/resources/app.asar/out/renderer/index.html',
    ),
    true,
  )
  assert.equal(
    isAllowedRendererNavigation(
      'file:///opt/GillieAvatar/resources/app.asar/out/renderer/other.html',
      'file:///opt/GillieAvatar/resources/app.asar/out/renderer/index.html',
    ),
    false,
  )
  assert.equal(
    isAllowedRendererNavigation('http://127.0.0.1:5173/scene', 'http://127.0.0.1:5173/'),
    true,
  )
  assert.equal(
    isAllowedRendererNavigation('https://example.com/', 'http://127.0.0.1:5173/'),
    false,
  )
})
