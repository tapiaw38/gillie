// src/types/global.d.ts

export {}

declare global {
  interface ImportMetaEnv {
    readonly BASE_URL: string
    readonly DEV: boolean
    readonly VITE_API_URL?: string
    readonly VITE_ASSISTANT_BASE_URL?: string
    readonly VITE_ASSISTANT_API_KEY?: string
    readonly VITE_CALENDAR_BASE_URL?: string
    readonly VITE_DRIVE_BASE_URL?: string
    readonly VITE_GMAIL_BASE_URL?: string
    readonly VITE_WHATSAPP_API_BASE_URL?: string
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv
  }

  interface Window {
    electronAPI?: {
      readFile: (filePath: string) => Promise<string>
      listDir: (dirPath: string) => Promise<string[]>
      listDirShallow: (dirPath: string) => Promise<string[]>
      glob: (pattern: string, base: string) => Promise<string[]>
      fetchUrl: (url: string) => Promise<string>
      avatar: {
        listAssets: () => Promise<{ model: string | null; animations: string[] }>
        importModel: () => Promise<{ model: string | null; animations: string[] }>
        importAnimations: () => Promise<{ model: string | null; animations: string[] }>
        removeAnimation: (name: string) => Promise<{ model: string | null; animations: string[] }>
        save: () => Promise<{ model: string | null; animations: string[] }>
      }
    }
    google?: {
      accounts?: {
        oauth2?: {
          initCodeClient: (config: {
            client_id: string
            scope: string
            ux_mode: string
            callback: (response: { code: string }) => void
          }) => {
            requestCode: () => void
          }
        }
      }
    }
  }
}
