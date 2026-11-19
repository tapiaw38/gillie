import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

const gillieAPI = {
  readFile: (filePath: string): Promise<string> => ipcRenderer.invoke('fs:readFile', filePath),
  listDir: (dirPath: string): Promise<string[]> => ipcRenderer.invoke('fs:listDir', dirPath),
  listDirShallow: (dirPath: string): Promise<string[]> =>
    ipcRenderer.invoke('fs:listDirShallow', dirPath),
  glob: (pattern: string, base: string): Promise<string[]> =>
    ipcRenderer.invoke('fs:glob', pattern, base),
  fetchUrl: (url: string): Promise<string> => ipcRenderer.invoke('net:fetchUrl', url),
  avatar: {
    listAssets: (): Promise<{ model: string | null; animations: string[] }> =>
      ipcRenderer.invoke('avatar:listAssets'),
    importModel: (): Promise<{ model: string | null; animations: string[] }> =>
      ipcRenderer.invoke('avatar:importModel'),
    importAnimations: (): Promise<{ model: string | null; animations: string[] }> =>
      ipcRenderer.invoke('avatar:importAnimations'),
    removeAnimation: (name: string): Promise<{ model: string | null; animations: string[] }> =>
      ipcRenderer.invoke('avatar:removeAnimation', name),
    save: (): Promise<{ model: string | null; animations: string[] }> =>
      ipcRenderer.invoke('avatar:save'),
  },
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('electronAPI', gillieAPI)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-expect-error Electron exposes this global in non-isolated preload mode.
  window.electron = electronAPI
  // @ts-expect-error Electron exposes this global in non-isolated preload mode.
  window.electronAPI = gillieAPI
}
