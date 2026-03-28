import { app, shell, BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import * as fs from 'fs'
import * as nodePath from 'path'
import * as https from 'https'
import * as http from 'http'

// ── IPC: fs:readFile ───────────────────────────────────────────────────────────

ipcMain.handle('fs:readFile', async (_event, filePath: string): Promise<string> => {
  try {
    const content = fs.readFileSync(filePath, 'utf8')
    return content.length > 4000 ? content.slice(0, 4000) + '\n[... truncated]' : content
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    throw new Error(`Cannot read file "${filePath}": ${msg}`)
  }
})

// ── IPC: fs:listDir ────────────────────────────────────────────────────────────

const SKIP_DIRS = new Set([
  '.git',
  'node_modules',
  '__pycache__',
  '.venv',
  'dist',
  '.next',
  'build',
])

function listDirRecursive(dirPath: string, base: string, results: string[], limit: number): void {
  if (results.length >= limit) return
  let entries: fs.Dirent[]
  try {
    entries = fs.readdirSync(dirPath, { withFileTypes: true })
  } catch {
    return
  }
  for (const entry of entries) {
    if (results.length >= limit) break
    if (SKIP_DIRS.has(entry.name)) continue
    const fullPath = nodePath.join(dirPath, entry.name)
    const relPath = nodePath.relative(base, fullPath)
    if (entry.isDirectory()) {
      listDirRecursive(fullPath, base, results, limit)
    } else {
      results.push(relPath)
    }
  }
}

ipcMain.handle('fs:listDir', async (_event, dirPath: string): Promise<string[]> => {
  const results: string[] = []
  listDirRecursive(dirPath, dirPath, results, 100)
  return results
})

// Shallow listing (immediate children only) used for tab completion
ipcMain.handle('fs:listDirShallow', async (_event, dirPath: string): Promise<string[]> => {
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true })
    return entries
      .filter((e) => !SKIP_DIRS.has(e.name))
      .map((e) => e.name + (e.isDirectory() ? '/' : ''))
  } catch {
    return []
  }
})

// ── IPC: fs:glob ───────────────────────────────────────────────────────────────

function globMatch(pattern: string, filePath: string): boolean {
  // Convert glob pattern to regex
  const regexStr = pattern
    .replace(/[.+^${}()|[\]\\]/g, '\\$&') // escape special regex chars except * and ?
    .replace(/\*\*/g, '\u0000') // temporarily replace **
    .replace(/\*/g, '[^/]*') // * matches anything except /
    .replace(/\?/g, '[^/]') // ? matches single char except /
    .replace(/\u0000/g, '.*') // ** matches anything including /
  try {
    return new RegExp(`^${regexStr}$`).test(filePath)
  } catch {
    return false
  }
}

function globRecursive(
  dirPath: string,
  base: string,
  pattern: string,
  results: string[],
  limit: number,
): void {
  if (results.length >= limit) return
  let entries: fs.Dirent[]
  try {
    entries = fs.readdirSync(dirPath, { withFileTypes: true })
  } catch {
    return
  }
  for (const entry of entries) {
    if (results.length >= limit) break
    if (SKIP_DIRS.has(entry.name)) continue
    const fullPath = nodePath.join(dirPath, entry.name)
    const relPath = nodePath.relative(base, fullPath)
    if (entry.isDirectory()) {
      globRecursive(fullPath, base, pattern, results, limit)
    } else if (globMatch(pattern, relPath)) {
      results.push(relPath)
    }
  }
}

ipcMain.handle('fs:glob', async (_event, pattern: string, base: string): Promise<string[]> => {
  const results: string[] = []
  const resolvedBase = base || process.cwd()
  globRecursive(resolvedBase, resolvedBase, pattern, results, 100)
  return results
})

// ── IPC: net:fetchUrl ──────────────────────────────────────────────────────────

function stripHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s{2,}/g, ' ')
    .trim()
}

ipcMain.handle('net:fetchUrl', async (_event, url: string): Promise<string> => {
  return new Promise((resolve, reject) => {
    const protocol = url.startsWith('https://') ? https : http
    const req = protocol.get(
      url,
      { headers: { 'User-Agent': 'Mozilla/5.0 (gillie-ai)' } },
      (res) => {
        // Follow a single redirect
        if (
          res.statusCode &&
          res.statusCode >= 300 &&
          res.statusCode < 400 &&
          res.headers.location
        ) {
          protocol
            .get(
              res.headers.location,
              { headers: { 'User-Agent': 'Mozilla/5.0 (gillie-ai)' } },
              (res2) => {
                let body = ''
                res2.on('data', (chunk: Buffer) => {
                  body += chunk.toString()
                })
                res2.on('end', () => {
                  const text = stripHtml(body)
                  resolve(text.length > 3000 ? text.slice(0, 3000) + '\n[... truncated]' : text)
                })
              },
            )
            .on('error', reject)
          return
        }
        let body = ''
        res.on('data', (chunk: Buffer) => {
          body += chunk.toString()
        })
        res.on('end', () => {
          const text = stripHtml(body)
          resolve(text.length > 3000 ? text.slice(0, 3000) + '\n[... truncated]' : text)
        })
      },
    )
    req.on('error', reject)
    req.setTimeout(10000, () => {
      req.destroy()
      reject(new Error('Request timed out'))
    })
  })
})

const iconPath = join(__dirname, '../../resources/icon.png')

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    icon: iconPath,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: join(__dirname, '../preload/index.mjs'),
      sandbox: false,
      contextIsolation: true,
    },
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // Prevent the main window from navigating away from the app (e.g. clicking image links)
  mainWindow.webContents.on('will-navigate', (event, url) => {
    const appBase = is.dev
      ? process.env['ELECTRON_RENDERER_URL']
      : `file://${join(__dirname, '../renderer/')}`
    if (appBase && !url.startsWith(appBase)) {
      event.preventDefault()
      shell.openExternal(url)
    }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('ai.gillie')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  const { session } = require('electron')
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Access-Control-Allow-Origin': ['*'],
        'Access-Control-Allow-Methods': ['GET, POST, PUT, PATCH, DELETE, OPTIONS'],
        'Access-Control-Allow-Headers': ['Content-Type, Authorization, x-api-key'],
      },
    })
  })

  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
