import { execFile, spawn, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import { promisify } from 'node:util'
import { AudioActivityGate, DEFAULT_SPEECH_RELEASE_MS } from './audio-activity-gate'
import { configuredPattern } from './process-discovery'
import type { AudioListener, AudioListenerCallbacks, AudioListenerStatus } from './types'

const execFileAsync = promisify(execFile)

export const SPEECH_RELEASE_MS = DEFAULT_SPEECH_RELEASE_MS
export const AUDIO_SOURCE_IDENTITY = configuredPattern()

export interface PipeWireObject {
  id?: number | string
  type?: string
  info?: {
    state?: string
    props?: Record<string, unknown>
  }
}

export interface ProcessInfo {
  identity: string
  parentId: number
}

function nodeProperties(node: PipeWireObject | null | undefined): Record<string, unknown> {
  return node?.info?.props ?? {}
}

export function enrichPipeWireNodes(objects: PipeWireObject[]): PipeWireObject[] {
  const clients = new Map(
    objects
      .filter((object) => object?.type === 'PipeWire:Interface:Client')
      .map((client) => [String(client.id), nodeProperties(client)]),
  )
  return objects.map((object) => {
    if (object?.type !== 'PipeWire:Interface:Node') return object
    const properties = nodeProperties(object)
    const client = clients.get(String(properties['client.id']))
    if (!client) return object
    return {
      ...object,
      info: {
        ...object.info,
        props: {
          ...client,
          ...properties,
        },
      },
    }
  })
}

export function readProcessInfo(processId: number | string): ProcessInfo {
  const root = `/proc/${processId}`
  let cmdline = ''
  let comm = ''
  let executable = ''
  let status = ''
  try {
    cmdline = fs.readFileSync(`${root}/cmdline`, 'utf8').replaceAll('\0', ' ').trim()
  } catch {
  }
  try {
    comm = fs.readFileSync(`${root}/comm`, 'utf8').trim()
  } catch {
  }
  try {
    executable = fs.readlinkSync(`${root}/exe`)
  } catch {
  }
  try {
    status = fs.readFileSync(`${root}/status`, 'utf8')
  } catch {
  }
  if (!cmdline && !comm && !executable) {
    throw new Error(`Process ${processId} is not readable`)
  }
  const parentMatch = /^PPid:\s+(\d+)$/m.exec(status)
  return {
    identity: `${comm} ${executable} ${cmdline}`,
    parentId: parentMatch ? Number(parentMatch[1]) : 0,
  }
}

export function isCodexProcessTree(
  processId: number | string,
  processReader: (processId: number) => ProcessInfo = readProcessInfo,
): boolean {
  let currentId = Number(processId)
  const visited = new Set<number>()
  for (let depth = 0; depth < 10; depth += 1) {
    if (!Number.isInteger(currentId) || currentId <= 1 || visited.has(currentId)) return false
    visited.add(currentId)
    try {
      const info = processReader(currentId)
      if (AUDIO_SOURCE_IDENTITY.test(info.identity)) return true
      currentId = Number(info.parentId)
    } catch {
      return false
    }
  }
  return false
}

export function isCodexOutputNode(
  node: PipeWireObject,
  processMatcher: (processId: number | string) => boolean = isCodexProcessTree,
): boolean {
  if (node?.type !== 'PipeWire:Interface:Node') return false
  const properties = nodeProperties(node)
  if (properties['media.class'] !== 'Stream/Output/Audio') return false
  const identity = [
    properties['application.name'],
    properties['application.process.binary'],
    properties['application.process.id'],
    properties['node.name'],
    properties['node.description'],
  ]
    .filter((value) => value != null)
    .join(' ')
  if (AUDIO_SOURCE_IDENTITY.test(identity)) return true

  const processId = properties['application.process.id'] as number | string | undefined
  return processId != null && processMatcher(processId)
}

export function findCodexOutputNode(
  nodes: PipeWireObject[],
  processMatcher: (processId: number | string) => boolean = isCodexProcessTree,
): PipeWireObject | null {
  const processCache = new Map<string, boolean>()
  const cachedMatcher = (processId: number | string) => {
    const key = String(processId)
    if (!processCache.has(key)) processCache.set(key, processMatcher(processId))
    return processCache.get(key) as boolean
  }
  const matches = nodes.filter((node) => isCodexOutputNode(node, cachedMatcher))
  return (
    matches.find((node) => node.info?.state === 'running') ??
    matches.find((node) => node.info?.state === 'idle') ??
    matches[0] ??
    null
  )
}

export function pcm16Rms(buffer: Buffer): number {
  const sampleCount = Math.floor(buffer.length / 2)
  if (sampleCount === 0) return 0
  let squareSum = 0
  for (let offset = 0; offset + 1 < buffer.length; offset += 2) {
    const sample = buffer.readInt16LE(offset) / 32768
    squareSum += sample * sample
  }
  return Math.sqrt(squareSum / sampleCount)
}

export function normalizeRms(rms: number): number {
  const noiseFloor = 0.0025
  if (!Number.isFinite(rms) || rms <= noiseFloor) return 0
  return Math.min(1, (rms - noiseFloor) * 7.5)
}

function displayName(node: PipeWireObject): string {
  const properties = nodeProperties(node)
  return String(
    properties['application.name'] ??
      properties['node.description'] ??
      properties['node.name'] ??
      'Codex',
  )
}

export interface LinuxPipeWireListenerOptions extends AudioListenerCallbacks {
  pollIntervalMs?: number
  speechReleaseMs?: number
}

export class LinuxPipeWireListener implements AudioListener {
  private readonly onActivity: NonNullable<AudioListenerCallbacks['onActivity']>
  private readonly onDebug: AudioListenerCallbacks['onDebug']
  private readonly onSession: NonNullable<AudioListenerCallbacks['onSession']>
  private readonly onStatus: NonNullable<AudioListenerCallbacks['onStatus']>
  private readonly pollIntervalMs: number
  private readonly gate: AudioActivityGate
  private capture: ChildProcess | null = null
  private captureSerial: string | null = null
  currentNode: PipeWireObject | null = null
  private pollTimer: NodeJS.Timeout | null = null
  private sessionActive = false
  private stopped = true
  private pollInFlight = false
  private lastStatusKey: string | null = null
  private lastDebugKey: string | null = null

  constructor({
    onActivity = () => {},
    onDebug = null,
    onLevel = () => {},
    onSession = () => {},
    onStatus = () => {},
    pollIntervalMs = 750,
    speechReleaseMs = SPEECH_RELEASE_MS,
  }: LinuxPipeWireListenerOptions = {}) {
    this.onActivity = onActivity
    this.onDebug = onDebug
    this.onSession = onSession
    this.onStatus = onStatus
    this.pollIntervalMs = pollIntervalMs
    this.gate = new AudioActivityGate({
      onActivity,
      onLevel,
      shouldReturnToListening: () => this.currentNode != null,
      speechReleaseMs,
    })
  }

  reportStatus(status: AudioListenerStatus): void {
    const key = JSON.stringify(status)
    if (key === this.lastStatusKey) return
    this.lastStatusKey = key
    this.onStatus(status)
  }

  async start(): Promise<void> {
    if (process.platform !== 'linux' || !this.stopped) return
    this.stopped = false
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
      const { stdout } = await execFileAsync('pw-dump', {
        encoding: 'utf8',
        maxBuffer: 8 * 1024 * 1024,
        timeout: 2_500,
      })
      const nodes = enrichPipeWireNodes(JSON.parse(stdout) as PipeWireObject[])
      if (this.onDebug) {
        const outputNodes = nodes
          .filter(
            (candidate) =>
              nodeProperties(candidate)['media.class'] === 'Stream/Output/Audio',
          )
          .map((candidate) => {
            const properties = nodeProperties(candidate)
            const processId =
              (properties['application.process.id'] as number | string | undefined) ?? null
            return {
              application: properties['application.name'] ?? null,
              binary: properties['application.process.binary'] ?? null,
              node: properties['node.name'] ?? null,
              processId,
              processTreeMatches: processId != null && isCodexProcessTree(processId),
              state: candidate.info?.state ?? null,
            }
          })
        const debugKey = JSON.stringify(outputNodes)
        if (debugKey !== this.lastDebugKey) {
          this.lastDebugKey = debugKey
          this.onDebug(outputNodes)
        }
      }
      const node = findCodexOutputNode(nodes)
      if (node == null) {
        this.detach()
        return
      }

      const serial = String(nodeProperties(node)['object.serial'] ?? node.id)
      if (this.capture && this.captureSerial === serial) return
      this.detach({ sessionEnded: false })
      this.currentNode = node
      this.captureSerial = serial
      if (!this.sessionActive) {
        this.sessionActive = true
        this.onSession(true)
      }
      this.onActivity('listening')
      this.startCapture(node, serial)
    } catch (error) {
      this.reportStatus({
        available: false,
        capturing: false,
        monitoring: false,
        source: null,
        error: error instanceof Error ? error.message : String(error),
      })
    } finally {
      this.pollInFlight = false
    }
  }

  private startCapture(node: PipeWireObject, serial: string): void {
    const child = spawn(
      'pw-record',
      [
        '--target',
        serial,
        '--raw',
        '--rate',
        '16000',
        '--channels',
        '2',
        '--format',
        's16',
        '-',
      ],
      { stdio: ['ignore', 'pipe', 'ignore'] },
    )
    this.capture = child
    this.reportStatus({
      available: true,
      capturing: true,
      monitoring: true,
      source: displayName(node),
    })

    child.stdout?.on('data', (chunk: Buffer) => {
      if (this.capture === child) this.handleAudio(chunk)
    })
    child.once('error', (error: Error) => {
      if (this.capture !== child) return
      this.capture = null
      this.reportStatus({
        available: false,
        capturing: false,
        monitoring: true,
        source: displayName(node),
        error: error.message,
      })
    })
    child.once('exit', () => {
      if (this.capture !== child) return
      this.capture = null
      this.reportStatus({
        available: true,
        capturing: false,
        monitoring: true,
        source: displayName(node),
      })
    })
  }

  handleAudio(chunk: Buffer): void {
    this.gate.handleLevel(normalizeRms(pcm16Rms(chunk)))
  }

  detach({ sessionEnded = true }: { sessionEnded?: boolean } = {}): void {
    this.currentNode = null
    this.captureSerial = null
    if (this.capture) {
      const child = this.capture
      this.capture = null
      child.kill('SIGTERM')
    }
    this.gate.reset()
    if (sessionEnded && this.sessionActive) {
      this.sessionActive = false
      this.onSession(false)
    }
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
