import path from 'node:path'
import { pathToFileURL } from 'node:url'
import {
  app,
  BrowserWindow,
  globalShortcut,
  ipcMain,
  Menu,
  nativeImage,
  screen,
  Tray,
} from 'electron'
import { createBridgeServer, DEFAULT_PORT, type BridgeServer } from './bridge-server'
import { createAvatarMcpHandler, getAnimationEventName } from './mcp-server'
import type { WindowAction } from './mcp-server'
import { configureHyprlandWindow, getHyprlandWindowPlacement } from './hyprland-window'
import { createAudioListener } from './audio-listener'
import { isAllowedRendererNavigation } from './navigation-policy'
import { parseProtocolUrl, voiceState } from './protocol-actions'
import type {
  AudioListener,
  AudioListenerStatus,
  BridgeEvent,
  VoiceState,
} from './types'

const WINDOW_WIDTH = 430
const WINDOW_HEIGHT = 680
const startInBackground = process.argv.includes('--background')
const protocolScheme = 'avatar'
const debugEnabled = process.env.AVATAR_DEBUG === '1'

let avatarWindow: BrowserWindow | null = null
let bridge: BridgeServer | null = null
let isQuitting = false
let latestEvent: BridgeEvent | null = null
let latestListenerStatus: AudioListenerStatus | null = null
let latestVoiceState: VoiceState | null = null
let audioListener: AudioListener | null = null
let tray: Tray | null = null
let hyprlandConfigured = false
let hyprlandConfiguring = false
let hyprlandConfigurationTimer: NodeJS.Timeout | null = null
let hyprlandLastPosition: { x: number; y: number } | null = null
let rendererLoadHookAttached = false
let mcpAnimationRequestId = 0
const pendingRendererEvents = new Map<string, BridgeEvent>()

app.setName('Gillie Avatar')

function debugLog(...values: unknown[]): void {
  if (debugEnabled) console.error('[avatar]', ...values)
}

function iconPath(): string {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'icon.png')
    : path.join(__dirname, '..', '..', 'resources', 'icon.png')
}

function rendererUrl(): string {
  return (
    process.env.ELECTRON_RENDERER_URL ||
    pathToFileURL(path.join(__dirname, '..', 'renderer', 'index.html')).href
  )
}

function positionWindow(window: BrowserWindow): void {
  const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint())
  const bounds = window.getBounds()
  const margin = 24
  window.setPosition(
    Math.round(display.workArea.x + display.workArea.width - bounds.width - margin),
    Math.round(display.workArea.y + display.workArea.height - bounds.height - margin),
    false,
  )
}

function scheduleHyprlandWindowConfiguration({
  attempt = 0,
  force = false,
  position = null,
  reposition = !hyprlandConfigured,
}: {
  attempt?: number
  force?: boolean
  position?: { x: number; y: number } | null
  reposition?: boolean
} = {}): void {
  if (
    (hyprlandConfigured && !force) ||
    hyprlandConfiguring ||
    !avatarWindow ||
    avatarWindow.isDestroyed()
  ) {
    return
  }
  if (hyprlandConfigurationTimer) clearTimeout(hyprlandConfigurationTimer)
  const delays = [0, 80, 200, 500, 1000]
  hyprlandConfigurationTimer = setTimeout(
    async () => {
      hyprlandConfigurationTimer = null
      if (!avatarWindow || avatarWindow.isDestroyed()) return
      hyprlandConfiguring = true
      hyprlandConfigured = await configureHyprlandWindow({
        pid: process.pid,
        width: WINDOW_WIDTH,
        height: WINDOW_HEIGHT,
        onDebug: debugLog,
        position,
        reposition,
      })
      hyprlandConfiguring = false
      if (!hyprlandConfigured && attempt + 1 < delays.length) {
        scheduleHyprlandWindowConfiguration({
          attempt: attempt + 1,
          force: true,
          position,
          reposition,
        })
      }
    },
    delays[attempt] ?? delays.at(-1),
  )
  hyprlandConfigurationTimer.unref?.()
}

function showOverlay({ focus = false }: { focus?: boolean } = {}): void {
  const window = createWindow()
  if (window.isMinimized()) window.restore()
  if (focus) {
    if (!window.isVisible()) window.show()
    window.focus()
  } else if (!window.isVisible()) {
    window.showInactive()
  }
  scheduleHyprlandWindowConfiguration()
}

async function hideOverlay(): Promise<void> {
  debugLog('hide overlay')
  const placement = await getHyprlandWindowPlacement(process.pid)
  if (placement) {
    hyprlandLastPosition = { x: placement.x, y: placement.y }
  }
  avatarWindow?.hide()
}

function toggleOverlay(): void {
  if (avatarWindow?.isVisible()) void hideOverlay()
  else showOverlay({ focus: true })
}

function createWindow(): BrowserWindow {
  if (avatarWindow && !avatarWindow.isDestroyed()) return avatarWindow

  avatarWindow = new BrowserWindow({
    width: WINDOW_WIDTH,
    height: WINDOW_HEIGHT,
    minWidth: 320,
    minHeight: 480,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    hasShadow: false,
    roundedCorners: false,
    autoHideMenuBar: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    title: 'Gillie Avatar',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  avatarWindow.setAlwaysOnTop(true, 'floating')
  avatarWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
  avatarWindow.setOpacity(1)
  avatarWindow.once('ready-to-show', () => {
    if (avatarWindow) positionWindow(avatarWindow)
    scheduleHyprlandWindowConfiguration()
  })
  avatarWindow.on('show', () => {
    avatarWindow?.setAlwaysOnTop(true, 'floating')
    avatarWindow?.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
    avatarWindow?.setOpacity(1)
    scheduleHyprlandWindowConfiguration({
      force: true,
      position: hyprlandLastPosition,
      reposition: !hyprlandConfigured || hyprlandLastPosition != null,
    })
  })
  avatarWindow.on('close', (event) => {
    if (isQuitting) return
    event.preventDefault()
    void hideOverlay()
  })
  avatarWindow.on('closed', () => {
    if (hyprlandConfigurationTimer) clearTimeout(hyprlandConfigurationTimer)
    hyprlandConfigurationTimer = null
    hyprlandConfigured = false
    hyprlandConfiguring = false
    rendererLoadHookAttached = false
    avatarWindow = null
  })

  const url = rendererUrl()
  avatarWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  avatarWindow.webContents.on('will-navigate', (event, targetUrl) => {
    if (!isAllowedRendererNavigation(targetUrl, url)) event.preventDefault()
  })
  void avatarWindow.loadURL(url)
  return avatarWindow
}

function flushPendingRendererEvents(): void {
  rendererLoadHookAttached = false
  if (!avatarWindow || avatarWindow.isDestroyed() || avatarWindow.webContents.isLoading()) {
    return
  }
  for (const event of pendingRendererEvents.values()) {
    avatarWindow.webContents.send('avatar:event', event)
  }
  pendingRendererEvents.clear()
}

function ensureRendererLoadHook(): void {
  if (
    rendererLoadHookAttached ||
    !avatarWindow ||
    avatarWindow.isDestroyed() ||
    !avatarWindow.webContents.isLoading()
  ) {
    return
  }
  rendererLoadHookAttached = true
  avatarWindow.webContents.once('did-finish-load', flushPendingRendererEvents)
}

function emitToRenderer(event: BridgeEvent): void {
  latestEvent = event
  pendingRendererEvents.set(event.type, event)
  if (!avatarWindow || avatarWindow.isDestroyed()) return
  if (avatarWindow.webContents.isLoading()) {
    ensureRendererLoadHook()
    return
  }
  avatarWindow.webContents.send('avatar:event', event)
  pendingRendererEvents.delete(event.type)
}

function handleBridgeEvent(event: BridgeEvent): void {
  if (event.type !== 'audio-level' || event.level > 0.025) debugLog('event', event)
  if (event.type === 'state') {
    latestVoiceState = event.state
    if (event.state.phase === 'starting' || event.state.phase === 'active') {
      showOverlay()
    }
  } else if (event.type === 'audio-level' && event.level > 0.025) {
    showOverlay()
  } else if (event.type === 'animation') {
    showOverlay()
  }
  emitToRenderer(event)
}

function handleListenerStatus(status: AudioListenerStatus): void {
  latestListenerStatus = status
  emitToRenderer({ type: 'listener-status', status })
}

async function handleMcpWindowAction(action: WindowAction): Promise<boolean> {
  if (action === 'show') showOverlay({ focus: true })
  else if (action === 'hide') await hideOverlay()
  else if (avatarWindow?.isVisible()) await hideOverlay()
  else showOverlay({ focus: true })
  return avatarWindow?.isVisible() ?? false
}

function getMcpStatus() {
  return {
    windowVisible: avatarWindow?.isVisible() ?? false,
    voiceState: latestVoiceState,
    listener: latestListenerStatus,
  }
}

function handleProtocolUrl(rawUrl: string): boolean {
  const commands = parseProtocolUrl(rawUrl, protocolScheme)
  if (!commands) return false
  for (const command of commands) {
    if (command.type === 'show') showOverlay({ focus: true })
    else if (command.type === 'hide') void hideOverlay()
    else if (command.type === 'toggle') toggleOverlay()
    else if (command.type === 'event') handleBridgeEvent(command.event)
  }
  return true
}

function handleProtocolArgv(argv: string[]): void {
  const protocolUrl = argv.find((value) => value.startsWith(`${protocolScheme}://`))
  if (protocolUrl) handleProtocolUrl(protocolUrl)
}

function createTray(): void {
  const icon = nativeImage.createFromPath(iconPath()).resize({ width: 20, height: 20 })
  tray = new Tray(icon)
  tray.setToolTip('Gillie Avatar')
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: 'Show avatar', click: () => showOverlay({ focus: true }) },
      { label: 'Hide avatar', click: () => void hideOverlay() },
      { type: 'separator' },
      { label: 'Preview listening', click: () => handleBridgeEvent(voiceState('listening')) },
      { label: 'Preview speaking', click: () => handleBridgeEvent(voiceState('speaking')) },
      {
        label: 'Preview dance',
        click: () => handleBridgeEvent({ type: 'animation', animation: 'DANCE' }),
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          isQuitting = true
          app.quit()
        },
      },
    ]),
  )
  tray.on('click', toggleOverlay)
}

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', (_event, argv) => {
    const handled = argv.some((value) => value.startsWith(`${protocolScheme}://`))
    handleProtocolArgv(argv)
    if (!handled && !argv.includes('--background')) showOverlay({ focus: true })
  })

  app.on('open-url', (event, url) => {
    event.preventDefault()
    handleProtocolUrl(url)
  })

  app.whenReady().then(async () => {
    app.setAppUserModelId('ai.gillie.avatar')
    app.dock?.hide()
    if (app.isPackaged) app.setAsDefaultProtocolClient(protocolScheme)

    ipcMain.handle('avatar:get-snapshot', () => latestEvent)
    ipcMain.on('avatar:hide', () => void hideOverlay())

    const mcpHandler = createAvatarMcpHandler({
      onAnimation: (animation) => {
        const eventName = getAnimationEventName(animation)
        if (eventName == null) return
        mcpAnimationRequestId += 1
        handleBridgeEvent({
          type: 'animation',
          animation: eventName,
          source: 'mcp',
          requestId: mcpAnimationRequestId,
        })
      },
      onWindowAction: handleMcpWindowAction,
      onVoiceState: (state) => handleBridgeEvent({ type: 'state', state }),
      onAudioLevel: (level) => handleBridgeEvent({ type: 'audio-level', level }),
      getStatus: getMcpStatus,
    })
    bridge = createBridgeServer({
      port: Number(process.env.AVATAR_BRIDGE_PORT || DEFAULT_PORT),
      onEvent: handleBridgeEvent,
      mcpHandler,
    })
    try {
      await bridge.listen()
    } catch (error) {
      console.error(
        '[avatar] local integration server unavailable:',
        error instanceof Error ? error.message : String(error),
      )
      bridge = null
    }

    createTray()
    globalShortcut.register('CommandOrControl+Shift+A', toggleOverlay)
    handleProtocolArgv(process.argv)

    audioListener = createAudioListener({
      isPackaged: app.isPackaged,
      resourcesPath: process.resourcesPath,
      onActivity: (activity) => {
        debugLog('listener activity', activity)
        handleBridgeEvent(voiceState(activity))
      },
      onDebug: debugEnabled ? (nodes) => debugLog('listener output nodes', nodes) : null,
      onLevel: (level) => handleBridgeEvent({ type: 'audio-level', level }),
      onSession: (active) => {
        debugLog('listener session', active)
        handleBridgeEvent(
          voiceState(active ? 'listening' : 'idle', active ? 'active' : 'inactive'),
        )
      },
      onStatus: (status) => {
        debugLog('listener status', status)
        handleListenerStatus(status)
      },
    })
    if (audioListener) void audioListener.start()
    else {
      handleListenerStatus({
        available: false,
        capturing: false,
        monitoring: false,
        source: null,
      })
    }

    if (!startInBackground) {
      createWindow()
      showOverlay({ focus: true })
    }
  })
}

app.on('activate', () => showOverlay({ focus: true }))

app.on('before-quit', () => {
  isQuitting = true
  if (hyprlandConfigurationTimer) clearTimeout(hyprlandConfigurationTimer)
  audioListener?.stop()
  globalShortcut.unregisterAll()
  void bridge?.close().catch((error) => debugLog('integration server close failed', error))
})

app.on('window-all-closed', () => {
})

export { tray }
