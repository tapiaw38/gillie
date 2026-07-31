import fs from 'node:fs'
import path from 'node:path'
import { spawn, type ChildProcess } from 'node:child_process'
import { AudioActivityGate, DEFAULT_SPEECH_RELEASE_MS } from './audio-activity-gate'
import { discoverVoiceProcesses, type VoiceProcessTree } from './process-discovery'
import type { AudioListener, AudioListenerCallbacks, AudioListenerStatus } from './types'

export const SESSION_IDLE_MS = 8_000

export function helperExecutableName(platform: NodeJS.Platform): string {
  return platform === 'win32' ? 'avatar-audio-listener.exe' : 'avatar-audio-listener'
}

export function resolveNativeHelperPath({
  platform = process.platform,
  isPackaged = false,
  resourcesPath = process.resourcesPath,
  projectRoot = path.join(__dirname, '..', '..'),
}: {
  platform?: NodeJS.Platform
  isPackaged?: boolean
  resourcesPath?: string
  projectRoot?: string
} = {}): string {
  const executable = helperExecutableName(platform)
  const platformPath = platform === 'win32' ? path.win32 : path.posix
  return isPackaged
    ? platformPath.join(resourcesPath, 'native', platform, executable)
    : platformPath.join(projectRoot, 'native', 'bin', platform, executable)
}

export function createNdjsonParser(
  onMessage: (message: unknown) => void,
  onInvalid: (line: string) => void = () => {},
): (chunk: Buffer | string) => void {
  let pending = ''
  return (chunk) => {
    pending += chunk.toString()
    const lines = pending.split(/\r?\n/)
    pending = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.trim()) continue
      try {
        onMessage(JSON.parse(line))
      } catch {
        onInvalid(line)
      }
    }
  }
}

interface HelperMessage {
  type?: string
  level?: number
  source?: string
  message?: string
}

export interface NativeProcessAudioListenerOptions extends AudioListenerCallbacks {
  platform?: NodeJS.Platform
  isPackaged?: boolean
  resourcesPath?: string
  helperPath?: string | null
  processDiscovery?: typeof discoverVoiceProcesses
  spawnProcess?: typeof spawn
  pollIntervalMs?: number
  sessionIdleMs?: number
  speechReleaseMs?: number
}

export class NativeProcessAudioListener implements AudioListener {
  private readonly platform: NodeJS.Platform
  private readonly helperPath: string
  private readonly processDiscovery: (options: {
    platform: NodeJS.Platform
  }) => Promise<VoiceProcessTree>
  private readonly spawnProcess: typeof spawn
  private readonly onActivity: NonNullable<AudioListenerCallbacks['onActivity']>
  private readonly onDebug: AudioListenerCallbacks['onDebug']
  private readonly onSession: NonNullable<AudioListenerCallbacks['onSession']>
  private readonly onStatus: NonNullable<AudioListenerCallbacks['onStatus']>
  private readonly pollIntervalMs: number
  private readonly sessionIdleMs: number
  private readonly gate: AudioActivityGate
  private capture: ChildProcess | null = null
  private captureKey: string | null = null
  private pollTimer: NodeJS.Timeout | null = null
  private sessionTimer: NodeJS.Timeout | null = null
  private sessionActive = false
  private stopped = true
  private pollInFlight = false
  private lastStatusKey: string | null = null

  constructor({
    platform = process.platform,
    isPackaged = false,
    resourcesPath = process.resourcesPath,
    helperPath = null,
    processDiscovery = discoverVoiceProcesses,
    spawnProcess = spawn,
    onActivity = () => {},
    onDebug = null,
    onLevel = () => {},
    onSession = () => {},
    onStatus = () => {},
    pollIntervalMs = 1_500,
    sessionIdleMs = SESSION_IDLE_MS,
    speechReleaseMs = DEFAULT_SPEECH_RELEASE_MS,
  }: NativeProcessAudioListenerOptions = {}) {
    this.platform = platform
    this.helperPath =
      helperPath ?? resolveNativeHelperPath({ platform, isPackaged, resourcesPath })
    this.processDiscovery = processDiscovery
    this.spawnProcess = spawnProcess
    this.onActivity = onActivity
    this.onDebug = onDebug
    this.onSession = onSession
    this.onStatus = onStatus
    this.pollIntervalMs = pollIntervalMs
    this.sessionIdleMs = sessionIdleMs
    this.gate = new AudioActivityGate({
      onActivity,
      onLevel,
      shouldReturnToListening: () => this.sessionActive,
      speechReleaseMs,
    })
  }

  private reportStatus(status: AudioListenerStatus): void {
    const key = JSON.stringify(status)
    if (key === this.lastStatusKey) return
    this.lastStatusKey = key
    this.onStatus(status)
  }

  async start(): Promise<void> {
    if (!['darwin', 'win32'].includes(this.platform) || !this.stopped) return
    this.stopped = false
    if (!fs.existsSync(this.helperPath)) {
      this.reportStatus({
        available: false,
        capturing: false,
        monitoring: false,
        source: null,
        error: `Native listener is missing: ${this.helperPath}`,
      })
      return
    }
    this.reportStatus({
      available: true,
      capturing: false,
      monitoring: true,
      source: null,
    })
    await this.poll()
    this.pollTimer = setInterval(() => void this.poll(), this.pollIntervalMs)
    this.pollTimer.unref?.()
  }

  async poll(): Promise<void> {
    if (this.stopped || this.pollInFlight) return
    this.pollInFlight = true
    try {
      const processes = await this.processDiscovery({ platform: this.platform })
      const selectedPids =
        this.platform === 'win32' ? processes.rootPids.slice(0, 1) : processes.pids
      const key = selectedPids.join(',')
      if (!key) {
        this.detach()
        return
      }
      if (this.capture && this.captureKey === key) return
      this.detach({ sessionEnded: false })
      this.startCapture(selectedPids, key)
    } catch (error) {
      this.reportStatus({
        available: true,
        capturing: false,
        monitoring: true,
        source: null,
        error: error instanceof Error ? error.message : String(error),
      })
    } finally {
      this.pollInFlight = false
    }
  }

  private startCapture(processIds: number[], key: string): void {
    const args = processIds.flatMap((processId) => ['--pid', String(processId)])
    const child = this.spawnProcess(this.helperPath, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    this.capture = child
    this.captureKey = key
    const parse = createNdjsonParser(
      (message) => this.handleHelperMessage(child, message as HelperMessage),
      (line) => this.onDebug?.(`native listener emitted invalid JSON: ${line}`),
    )
    child.stdout?.on('data', parse)
    child.stderr?.on('data', (chunk: Buffer) =>
      this.onDebug?.(`native listener stderr: ${chunk.toString()}`),
    )
    child.once('error', (error: Error) => {
      if (this.capture !== child) return
      this.capture = null
      this.captureKey = null
      this.reportStatus({
        available: false,
        capturing: false,
        monitoring: true,
        source: null,
        error: error.message,
      })
    })
    child.once('exit', (code: number | null, signal: NodeJS.Signals | null) => {
      if (this.capture !== child) return
      this.capture = null
      this.captureKey = null
      this.gate.reset()
      this.reportStatus({
        available: true,
        capturing: false,
        monitoring: !this.stopped,
        source: null,
        ...(code && !this.stopped
          ? {
              error: `Native listener exited with code ${code}${signal ? ` (${signal})` : ''}.`,
            }
          : {}),
      })
    })
  }

  handleHelperMessage(child: ChildProcess, message: HelperMessage): void {
    if (this.capture !== child || message == null || typeof message !== 'object') return
    if (message.type === 'ready') {
      this.reportStatus({
        available: true,
        capturing: true,
        monitoring: true,
        source: message.source || 'Supported voice app',
      })
      return
    }
    if (message.type === 'error') {
      this.reportStatus({
        available: false,
        capturing: false,
        monitoring: true,
        source: null,
        error: String(message.message || 'Native listener failed.'),
      })
      return
    }
    if (message.type !== 'level' || !Number.isFinite(message.level)) return

    const level = Math.max(0, Math.min(1, Number(message.level)))
    if (level > 0.008) {
      if (this.sessionTimer) clearTimeout(this.sessionTimer)
      this.sessionTimer = setTimeout(() => this.endSession(), this.sessionIdleMs)
      this.sessionTimer.unref?.()
      if (!this.sessionActive) {
        this.sessionActive = true
        this.onSession(true)
        this.onActivity('listening')
      }
    }
    this.gate.handleLevel(level)
  }

  endSession(): void {
    if (this.sessionTimer) clearTimeout(this.sessionTimer)
    this.sessionTimer = null
    if (!this.sessionActive) return
    this.sessionActive = false
    this.gate.reset()
    this.onSession(false)
  }

  detach({ sessionEnded = true }: { sessionEnded?: boolean } = {}): void {
    if (this.capture) {
      const child = this.capture
      this.capture = null
      this.captureKey = null
      child.kill()
    }
    this.gate.reset()
    if (sessionEnded) this.endSession()
    this.reportStatus({
      available: true,
      capturing: false,
      monitoring: !this.stopped,
      source: null,
    })
  }

  stop(): void {
    if (this.stopped) return
    this.stopped = true
    if (this.pollTimer) clearInterval(this.pollTimer)
    this.pollTimer = null
    this.detach()
  }
}
