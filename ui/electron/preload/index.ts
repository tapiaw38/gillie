import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

const gillieAPI = {
  readFile: (filePath: string): Promise<string> =>
    ipcRenderer.invoke('fs:readFile', filePath),
  listDir: (dirPath: string): Promise<string[]> =>
    ipcRenderer.invoke('fs:listDir', dirPath),
  listDirShallow: (dirPath: string): Promise<string[]> =>
    ipcRenderer.invoke('fs:listDirShallow', dirPath),
  glob: (pattern: string, base: string): Promise<string[]> =>
    ipcRenderer.invoke('fs:glob', pattern, base),
  fetchUrl: (url: string): Promise<string> =>
    ipcRenderer.invoke('net:fetchUrl', url),
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('electronAPI', gillieAPI)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore
  window.electron = electronAPI
  // @ts-ignore
  window.electronAPI = gillieAPI
}
