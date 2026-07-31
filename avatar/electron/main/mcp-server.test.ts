import assert from 'node:assert/strict'
import type { AddressInfo } from 'node:net'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import { onTestFinished, test } from 'vitest'
import { createBridgeServer } from './bridge-server'
import {
  ANIMATION_NAMES,
  SERVER_INSTRUCTIONS,
  WINDOW_ACTIONS,
  createAvatarMcpHandler,
  getAnimationEventName,
} from './mcp-server'
import type { VoiceState } from './types'

interface ToolText {
  content: { text: string }[]
  isError?: boolean
}

test('Gillie Avatar MCP exposes and executes the local character tools', async () => {
  const animations: string[] = []
  const windowActions: string[] = []
  let windowVisible = false
  const voiceState: VoiceState = {
    activity: 'listening',
    microphoneMuted: false,
    outputMuted: false,
    phase: 'active',
  }
  const listener = {
    available: true,
    capturing: false,
    monitoring: true,
    source: null,
  }
  const mcpHandler = createAvatarMcpHandler({
    onAnimation: (animation) => {
      animations.push(animation)
    },
    onWindowAction: (action) => {
      windowActions.push(action)
      if (action === 'show') windowVisible = true
      else if (action === 'hide') windowVisible = false
      else windowVisible = !windowVisible
      return windowVisible
    },
    onVoiceState: () => {},
    onAudioLevel: () => {},
    getStatus: () => ({ windowVisible, voiceState, listener }),
  })
  const bridge = createBridgeServer({ port: 0, onEvent: () => {}, mcpHandler })
  const address = (await bridge.listen()) as AddressInfo
  const client = new Client({ name: 'avatar-test', version: '1.0.0' })
  const transport = new StreamableHTTPClientTransport(
    new URL(`http://127.0.0.1:${address.port}/mcp`),
  )
  onTestFinished(async () => {
    await client.close()
    await bridge.close()
  })

  await client.connect(transport)
  const tools = await client.listTools()

  assert.deepEqual(
    tools.tools.map((tool) => tool.name),
    [
      'play_animation',
      'control_window',
      'get_status',
      'set_voice_state',
      'set_audio_level',
    ],
  )
  assert.equal(client.getInstructions(), SERVER_INSTRUCTIONS)
  assert.deepEqual(
    (
      tools.tools.find((tool) => tool.name === 'play_animation')?.inputSchema
        .properties as Record<string, { enum: string[] }>
    ).animation.enum,
    ANIMATION_NAMES,
  )
  assert.deepEqual(
    (
      tools.tools.find((tool) => tool.name === 'control_window')?.inputSchema
        .properties as Record<string, { enum: string[] }>
    ).action.enum,
    [...WINDOW_ACTIONS],
  )

  const animationResult = (await client.callTool({
    name: 'play_animation',
    arguments: { animation: 'finger-gun' },
  })) as unknown as ToolText
  const windowResult = (await client.callTool({
    name: 'control_window',
    arguments: { action: 'show' },
  })) as unknown as ToolText
  const statusResult = (await client.callTool({
    name: 'get_status',
    arguments: {},
  })) as unknown as ToolText

  assert.deepEqual(animations, ['finger-gun'])
  assert.deepEqual(windowActions, ['show'])
  assert.match(
    animationResult.content[0].text,
    /^You are now making the finger-gun gesture/,
  )
  assert.match(windowResult.content[0].text, /^You are now visible/)
  assert.deepEqual(JSON.parse(statusResult.content[0].text), {
    windowVisible: true,
    voiceState,
    listener,
  })
})

test('Gillie Avatar MCP maps semantic animation names to renderer events', () => {
  assert.equal(getAnimationEventName('happy'), 'HAPPY')
  assert.equal(getAnimationEventName('finger-gun'), 'FINGER_GUN')
  assert.equal(getAnimationEventName('dance'), 'DANCE')
  assert.equal(getAnimationEventName('celebrate'), null)
})

test('Gillie Avatar MCP rejects unknown animation names before invoking the app', async () => {
  const animations: string[] = []
  const bridge = createBridgeServer({
    port: 0,
    onEvent: () => {},
    mcpHandler: createAvatarMcpHandler({
      onAnimation: (animation) => {
        animations.push(animation)
      },
      onWindowAction: () => false,
      onVoiceState: () => {},
      onAudioLevel: () => {},
      getStatus: () => ({
        windowVisible: false,
        voiceState: null,
        listener: null,
      }),
    }),
  })
  const address = (await bridge.listen()) as AddressInfo
  const client = new Client({ name: 'avatar-test', version: '1.0.0' })
  const transport = new StreamableHTTPClientTransport(
    new URL(`http://127.0.0.1:${address.port}/mcp`),
  )
  onTestFinished(async () => {
    await client.close()
    await bridge.close()
  })

  await client.connect(transport)
  const result = await client.callTool({
    name: 'play_animation',
    arguments: { animation: 'download_from_the_internet' },
  })

  assert.equal(result.isError, true)
  assert.deepEqual(animations, [])
})
