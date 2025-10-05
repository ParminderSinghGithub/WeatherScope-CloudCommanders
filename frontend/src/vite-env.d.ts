/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Extend Navigator interface for Web Share API
interface Navigator {
  share?: (data: ShareData) => Promise<void>
}

interface ShareData {
  title?: string
  text?: string
  url?: string
}

// Leaflet types
declare module 'leaflet' {
  namespace Icon {
    interface Default {
      _getIconUrl?: string
      mergeOptions(options: any): void
    }
  }
}
