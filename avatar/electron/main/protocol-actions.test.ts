import assert from 'node:assert/strict'
import { test } from 'vitest'
import { parseProtocolUrl } from './protocol-actions'

test('maps Gillie Avatar URLs to lifecycle and clamped level events', () => {
  const commands = parseProtocolUrl('avatar://speaking?level=3')
  assert.ok(commands)
  assert.equal(
    commands[0].type === 'event' && commands[0].event.type === 'state'
      ? commands[0].event.state.activity
      : null,
    'speaking',
  )
  assert.deepEqual(commands[1].type === 'event' ? commands[1].event : null, {
    type: 'audio-level',
    level: 1,
  })

  const inactive = parseProtocolUrl('avatar://inactive')
  assert.ok(inactive)
  assert.equal(
    inactive[0].type === 'event' && inactive[0].event.type === 'state'
      ? inactive[0].event.state.phase
      : null,
    'inactive',
  )
})

test('maps window and animation URLs without accepting another scheme', () => {
  assert.deepEqual(parseProtocolUrl('avatar://toggle'), [{ type: 'toggle' }])
  assert.deepEqual(parseProtocolUrl('avatar://dance'), [
    { type: 'event', event: { type: 'animation', animation: 'DANCE' } },
  ])
  assert.deepEqual(parseProtocolUrl('avatar://finger-gun'), [
    { type: 'event', event: { type: 'animation', animation: 'FINGER_GUN' } },
  ])
  assert.deepEqual(parseProtocolUrl('avatar://happy'), [
    { type: 'event', event: { type: 'animation', animation: 'HAPPY' } },
  ])
  assert.equal(parseProtocolUrl('avatar://celebrate'), null)
  assert.equal(parseProtocolUrl('another-product://show'), null)
  assert.equal(parseProtocolUrl('not a URL'), null)
})
