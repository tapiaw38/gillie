import assert from 'node:assert/strict'
import { test } from 'vitest'
import { createAudioListener } from './audio-listener'
import { LinuxPipeWireListener } from './linux-pipewire-listener'
import { NativeProcessAudioListener } from './native-process-audio-listener'

test('selects the native listener implementation for each supported platform', () => {
  assert.ok(createAudioListener({ platform: 'linux' }) instanceof LinuxPipeWireListener)
  assert.ok(
    createAudioListener({ platform: 'darwin' }) instanceof NativeProcessAudioListener,
  )
  assert.ok(createAudioListener({ platform: 'win32' }) instanceof NativeProcessAudioListener)
  assert.equal(createAudioListener({ platform: 'freebsd' }), null)
})
