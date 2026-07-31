import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'

const avatarBridge = {
  getSnapshot: () => ipcRenderer.invoke('avatar:get-snapshot'),
  hide: () => ipcRenderer.send('avatar:hide'),
  subscribe: (listener: (payload: unknown) => void) => {
    const handler = (_event: IpcRendererEvent, payload: unknown) => listener(payload)
    ipcRenderer.on('avatar:event', handler)
    return () => ipcRenderer.off('avatar:event', handler)
  },
}

contextBridge.exposeInMainWorld('avatarBridge', avatarBridge)
