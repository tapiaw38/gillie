import type { IncomingMessage, ServerResponse } from 'node:http'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import * as z from 'zod'
import { version } from '../../package.json'
import type { AudioListenerStatus, BridgeAnimation, VoiceState } from './types'
import type { McpHandler } from './bridge-server'
import { ANIMATION_EVENT_NAMES as EVENT_NAMES, ANIMATION_ROLES } from './asset-manifest'

export const MCP_PATH = '/mcp'

export { ANIMATION_EVENT_NAMES } from './asset-manifest'
export const ANIMATION_NAMES = ANIMATION_ROLES as [string, ...string[]]
export const WINDOW_ACTIONS = ['show', 'hide', 'toggle'] as const
const VOICE_PHASES = ['inactive', 'starting', 'active', 'stopping'] as const
const VOICE_ACTIVITIES = ['idle', 'listening', 'speaking'] as const

export const SERVER_INSTRUCTIONS =
  "This is your body on the user's desktop. The character on screen is you, not a puppet you operate, so speak from inside it and never say you have no body. Use play_animation for a deliberate gesture, then describe it in the first person: you waved, you danced. Your mouth and body already move on their own while you speak, so never call play_animation to look like you are talking. Use control_window to show or hide yourself. get_status is read-only. This body never produces audio on its own."

export type WindowAction = (typeof WINDOW_ACTIONS)[number]

export interface McpStatus {
  windowVisible: boolean
  voiceState: VoiceState | null
  listener: AudioListenerStatus | null
}

export interface McpController {
  onAnimation: (animation: string) => void | Promise<void>
  onWindowAction: (action: WindowAction) => boolean | Promise<boolean>
  onVoiceState: (state: VoiceState) => void | Promise<void>
  onAudioLevel: (level: number) => void | Promise<void>
  getStatus: () => McpStatus | Promise<McpStatus>
}

function textResult(text: string) {
  return {
    content: [{ type: 'text' as const, text }],
  }
}

export function getAnimationEventName(animation: string): BridgeAnimation | null {
  return EVENT_NAMES[animation] ?? null
}

export function createAvatarMcpServer({
  onAnimation,
  onWindowAction,
  onVoiceState,
  onAudioLevel,
  getStatus,
}: McpController): McpServer {
  const server = new McpServer(
    {
      name: 'Gillie Avatar',
      version,
    },
    {
      instructions: SERVER_INSTRUCTIONS,
    },
  )

  server.registerTool(
    'play_animation',
    {
      title: 'Play Gillie Avatar animation',
      description:
        'Play one installed character animation once in the desktop window. This shows Gillie Avatar and temporarily takes priority over voice-driven body motion.',
      inputSchema: {
        animation: z.enum(ANIMATION_NAMES).describe('The character animation to play.'),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
    },
    async ({ animation }) => {
      await onAnimation(animation)
      return textResult(
        `Animation command accepted for ${animation}. Playback is asynchronous; do not claim completion unless it is visibly confirmed.`,
      )
    },
  )

  server.registerTool(
    'control_window',
    {
      title: 'Control Gillie Avatar window',
      description:
        'Show, hide, or toggle the local Gillie Avatar window. Hiding the window does not quit Gillie Avatar.',
      inputSchema: {
        action: z.enum(WINDOW_ACTIONS).describe('The window action to perform.'),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
    },
    async ({ action }) => {
      const visible = await onWindowAction(action)
      return textResult(
        `You are now ${visible ? 'visible' : 'hidden'} on the user's screen.`,
      )
    },
  )

  server.registerTool(
    'get_status',
    {
      title: 'Get Gillie Avatar status',
      description:
        "Read Gillie Avatar's window visibility, voice state, and local listener status.",
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async () => textResult(JSON.stringify(await getStatus())),
  )

  server.registerTool(
    'set_voice_state',
    {
      title: 'Set Gillie Avatar voice state',
      description:
        "Update Gillie Avatar's normalized voice lifecycle and activity state.",
      inputSchema: {
        phase: z.enum(VOICE_PHASES),
        activity: z.enum(VOICE_ACTIVITIES),
        microphoneMuted: z.boolean().default(false),
        outputMuted: z.boolean().default(false),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (state) => {
      await onVoiceState(state as VoiceState)
      return textResult(
        `Gillie Avatar voice state set to ${state.phase}/${state.activity}.`,
      )
    },
  )

  server.registerTool(
    'set_audio_level',
    {
      title: 'Set Gillie Avatar audio level',
      description: 'Update normalized output level for Gillie Avatar lip sync.',
      inputSchema: { level: z.number().min(0).max(1) },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async ({ level }) => {
      await onAudioLevel(level)
      return textResult(`Gillie Avatar audio level set to ${level}.`)
    },
  )

  return server
}

export function createAvatarMcpHandler(controller: McpController): McpHandler {
  return async (
    request: IncomingMessage,
    response: ServerResponse,
    parsedBody: unknown,
  ) => {
    const server = createAvatarMcpServer(controller)
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true,
    })

    try {
      await server.connect(transport)
      await transport.handleRequest(request, response, parsedBody)
    } catch (error) {
      if (!response.headersSent) {
        response.writeHead(500, { 'content-type': 'application/json' })
        response.end(
          JSON.stringify({
            jsonrpc: '2.0',
            error: { code: -32603, message: 'Internal server error' },
            id: null,
          }),
        )
      }
      throw error
    } finally {
      await transport.close()
      await server.close()
    }
  }
}
