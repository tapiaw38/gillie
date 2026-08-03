import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'

function zoomFromArguments(): number {
  const flag = process.argv.find((argument) => argument.startsWith('--avatar-zoom='))
  const parsed = Number(flag?.split('=')[1])
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1.5
}

const avatarBridge = {
  zoom: zoomFromArguments(),
  getSnapshot: () => ipcRenderer.invoke('avatar:get-snapshot'),
  hide: () => ipcRenderer.send('avatar:hide'),
  subscribe: (listener: (payload: unknown) => void) => {
    const handler = (_event: IpcRendererEvent, payload: unknown) => listener(payload)
    ipcRenderer.on('avatar:event', handler)
    return () => ipcRenderer.off('avatar:event', handler)
  },
}

contextBridge.exposeInMainWorld('avatarBridge', avatarBridge)
