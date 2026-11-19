import http, { type IncomingMessage, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import type { BridgeEvent, VoiceState } from './types'
import { ANIMATION_EVENTS } from './asset-manifest'

export const DEFAULT_PORT = 47850
const MAX_BODY_BYTES = 64 * 1024
const TRUSTED_ORIGIN =
  /^(?:https?:\/\/(?:127\.0\.0\.1|localhost|\[::1\])(?::\d+)?|codex-app:\/\/[A-Za-z0-9._~-]*)$/i
const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '[::1]'])

export const ANIMATIONS = new Set(ANIMATION_EVENTS)

export type McpHandler = (
  request: IncomingMessage,
  response: ServerResponse,
  body: unknown,
) => Promise<void>

export interface BridgeServer {
  getLastStateEvent(): Extract<BridgeEvent, { type: 'state' }> | null
  listen(): Promise<AddressInfo | string | null>
  close(): Promise<void>
}

interface BodyError extends Error {
  code?: string
}

export function isVoiceState(value: unknown): value is VoiceState {
  const candidate = value as VoiceState | null
  return (
    candidate != null &&
    typeof candidate === 'object' &&
    ['inactive', 'starting', 'active', 'stopping'].includes(candidate.phase) &&
    ['idle', 'listening', 'speaking'].includes(candidate.activity) &&
    typeof candidate.microphoneMuted === 'boolean' &&
    typeof candidate.outputMuted === 'boolean'
  )
}

export function normalizeEvent(value: unknown): BridgeEvent | null {
  const candidate = value as Record<string, unknown> | null
  if (candidate?.type === 'state' && isVoiceState(candidate.state)) {
    return { type: 'state', state: candidate.state }
  }
  if (candidate?.type === 'audio-level' && Number.isFinite(candidate.level)) {
    const level = Math.max(0, Math.min(1, Number(candidate.level)))
    const bands =
      candidate.bands != null && typeof candidate.bands === 'object'
        ? (candidate.bands as Record<string, number>)
        : undefined
    return { type: 'audio-level', level, ...(bands ? { bands } : {}) }
  }
  if (candidate?.type === 'animation' && ANIMATIONS.has(String(candidate.animation))) {
    return {
      type: 'animation',
      animation: candidate.animation as Extract<
        BridgeEvent,
        { type: 'animation' }
      >['animation'],
    }
  }
  return null
}

export function originAllowed(origin: string | undefined): boolean {
  return origin == null || TRUSTED_ORIGIN.test(origin)
}

export function hostAllowed(hostHeader: string | undefined): boolean {
  if (typeof hostHeader !== 'string' || hostHeader.length === 0) return false
  try {
    const url = new URL(`http://${hostHeader}`)
    return (
      url.username === '' &&
      url.password === '' &&
      url.pathname === '/' &&
      LOOPBACK_HOSTS.has(url.hostname.toLowerCase())
    )
  } catch {
    return false
  }
}

function jsonRpcError(
  response: ServerResponse,
  status: number,
  code: number,
  message: string,
): void {
  response.writeHead(status, { 'content-type': 'application/json' })
  response.end(
    JSON.stringify({
      jsonrpc: '2.0',
      error: { code, message },
      id: null,
    }),
  )
}

function readJsonBody(request: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let bytes = 0
    const chunks: Buffer[] = []

    request.on('data', (chunk: Buffer) => {
      bytes += chunk.length
      if (bytes > MAX_BODY_BYTES) {
        const error: BodyError = new Error('Request body is too large')
        error.code = 'BODY_TOO_LARGE'
        reject(error)
        request.resume()
        return
      }
      chunks.push(chunk)
    })
    request.on('end', () => {
      if (bytes > MAX_BODY_BYTES) return
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')))
      } catch {
        const error: BodyError = new Error('Request body is not valid JSON')
        error.code = 'INVALID_JSON'
        reject(error)
      }
    })
    request.on('error', reject)
  })
}

export function createBridgeServer({
  host = '127.0.0.1',
  port = DEFAULT_PORT,
  onEvent,
  mcpHandler = null,
}: {
  host?: string
  port?: number
  onEvent: (event: BridgeEvent) => void
  mcpHandler?: McpHandler | null
}): BridgeServer {
  let lastStateEvent: Extract<BridgeEvent, { type: 'state' }> | null = null

  const server = http.createServer((request, response) => {
    const origin = request.headers.origin
    if (!hostAllowed(request.headers.host)) {
      response.writeHead(403)
      response.end()
      return
    }

    if (request.method === 'GET' && request.url === '/health') {
      response.writeHead(200, { 'content-type': 'application/json' })
      response.end(JSON.stringify({ ok: true, lastState: lastStateEvent?.state ?? null }))
      return
    }

    if (request.url === '/mcp') {
      if (!originAllowed(origin)) {
        response.writeHead(403)
        response.end()
        return
      }
      if (request.method !== 'POST') {
        response.writeHead(405, { allow: 'POST' })
        response.end()
        return
      }
      if (mcpHandler == null) {
        response.writeHead(404)
        response.end()
        return
      }
      void readJsonBody(request)
        .then((body) => mcpHandler(request, response, body))
        .catch((error: BodyError) => {
          if (response.headersSent) return
          if (error?.code === 'BODY_TOO_LARGE') {
            jsonRpcError(response, 413, -32000, 'Request body is too large')
          } else if (error?.code === 'INVALID_JSON') {
            jsonRpcError(response, 400, -32700, 'Parse error')
          } else {
            jsonRpcError(response, 500, -32603, 'Internal server error')
          }
        })
      return
    }

    if (request.method === 'OPTIONS' && request.url === '/events' && originAllowed(origin)) {
      response.writeHead(204, {
        'access-control-allow-origin': origin ?? '',
        'access-control-allow-methods': 'POST, OPTIONS',
        'access-control-allow-headers': 'content-type',
        vary: 'Origin',
      })
      response.end()
      return
    }

    if (request.method !== 'POST' || request.url !== '/events' || !originAllowed(origin)) {
      response.writeHead(404)
      response.end()
      return
    }

    void readJsonBody(request)
      .then((body) => {
        const event = normalizeEvent(body)
        if (event == null) {
          response.writeHead(422)
          response.end()
          return
        }
        if (event.type === 'state') lastStateEvent = event
        onEvent(event)
        response.writeHead(202, {
          ...(origin ? { 'access-control-allow-origin': origin, vary: 'Origin' } : {}),
          'content-type': 'application/json',
        })
        response.end('{"accepted":true}')
      })
      .catch((error: BodyError) => {
        if (response.headersSent) return
        response.writeHead(error?.code === 'BODY_TOO_LARGE' ? 413 : 400)
        response.end()
      })
  })

  return {
    getLastStateEvent: () => lastStateEvent,
    listen: () =>
      new Promise((resolve, reject) => {
        server.once('error', reject)
        server.listen(port, host, () => {
          server.off('error', reject)
          resolve(server.address())
        })
      }),
    close: () =>
      new Promise((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()))
      }),
  }
}
