import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { fileURLToPath } from 'node:url'
import type { ChildProcess } from 'node:child_process'
import { test } from 'vitest'
import {
  NativeProcessAudioListener,
  createNdjsonParser,
  resolveNativeHelperPath,
} from './native-process-audio-listener'
import type { AudioListenerStatus, VoiceActivity } from './types'

function fakeChild(): ChildProcess {
  const child = new EventEmitter() as unknown as ChildProcess & {
    stdout: EventEmitter
    stderr: EventEmitter
  }
  child.stdout = new EventEmitter() as never
  child.stderr = new EventEmitter() as never
  child.kill = () => child.emit('exit', 0, 'SIGTERM')
  return child
}

test('NDJSON parser buffers partial messages and rejects malformed lines', () => {
  const messages: unknown[] = []
  const invalid: string[] = []
  const parse = createNdjsonParser(
    (message) => messages.push(message),
    (line) => invalid.push(line),
  )
  parse('{"type":"rea')
  parse('dy"}\nnot-json\n{"type":"level","level":0.2}\n')
  assert.deepEqual(messages, [{ type: 'ready' }, { type: 'level', level: 0.2 }])
  assert.deepEqual(invalid, ['not-json'])
})

test('resolves development and packaged helper locations on both native platforms', () => {
  assert.equal(
    resolveNativeHelperPath({
      platform: 'win32',
      projectRoot: 'C:\\project',
      isPackaged: true,
      resourcesPath: 'C:\\resources',
    }),
    'C:\\resources\\native\\win32\\avatar-audio-listener.exe',
  )
  assert.equal(
    resolveNativeHelperPath({
      platform: 'win32',
      projectRoot: 'C:\\project',
      isPackaged: false,
    }),
    'C:\\project\\native\\bin\\win32\\avatar-audio-listener.exe',
  )
  assert.equal(
    resolveNativeHelperPath({
      platform: 'darwin',
      projectRoot: '/project',
      isPackaged: false,
    }),
    '/project/native/bin/darwin/avatar-audio-listener',
  )
})

test('native listener activates on audio, smooths speech, and never hides the window', async () => {
  const activities: VoiceActivity[] = []
  const sessions: boolean[] = []
  const statuses: AudioListenerStatus[] = []
  const child = fakeChild()
  const listener = new NativeProcessAudioListener({
    platform: 'darwin',
    helperPath: fileURLToPath(import.meta.url),
    processDiscovery: async () => ({ pids: [10, 11], rootPids: [10] }),
    spawnProcess: (() => child) as never,
    onActivity: (activity) => activities.push(activity),
    onSession: (active) => sessions.push(active),
    onStatus: (status) => statuses.push(status),
    sessionIdleMs: 35,
    speechReleaseMs: 15,
  })

  await listener.start()
  child.stdout?.emit('data', '{"type":"ready","source":"Codex"}\n')
  child.stdout?.emit('data', '{"type":"level","level":0.3}\n')
  child.stdout?.emit('data', '{"type":"level","level":0}\n')
  await new Promise((resolve) => setTimeout(resolve, 22))

  assert.deepEqual(sessions, [true])
  assert.deepEqual(activities, ['listening', 'speaking', 'listening'])
  assert.equal(statuses.at(-1)?.capturing, true)

  await new Promise((resolve) => setTimeout(resolve, 25))
  assert.deepEqual(sessions, [true, false])
  listener.stop()
})
