import { LinuxPipeWireListener } from './linux-pipewire-listener'
import {
  NativeProcessAudioListener,
  type NativeProcessAudioListenerOptions,
} from './native-process-audio-listener'
import type { AudioListener } from './types'

export function createAudioListener({
  platform = process.platform,
  ...options
}: NativeProcessAudioListenerOptions = {}): AudioListener | null {
  if (platform === 'linux') return new LinuxPipeWireListener(options)
  if (platform === 'darwin' || platform === 'win32') {
    return new NativeProcessAudioListener({ platform, ...options })
  }
  return null
}
