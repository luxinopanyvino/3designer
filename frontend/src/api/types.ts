export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  version: number | null
  error: boolean
  image_url?: string | null
  created_at: string
}

export interface Version {
  version: number
  model_url: string | null
  preview_url?: string | null
  dimensions_mm: { x: number; y: number; z: number }
  volume_mm3: number
  watertight: boolean
  warnings: string[]
  source?: string
  created_at: string
}

export type Mode = 'organic' | 'sketch'

export interface SessionData {
  id: string
  created_at: string
  messages: Message[]
  versions: Version[]
}

export interface Health {
  status: string
  ollama: {
    reachable: boolean
    models: string[]
    vision_model_present: boolean
  }
  organic_available: boolean
  export_formats: string[]
  bed_size_mm: number
}

export type Stage = 'idle' | 'organic_generating' | 'vectorizing' | 'sketch_refining'

export interface EventHandlers {
  onStatus: (stage: Stage, attempt: number) => void
  onCompleted: (version: Version) => void
  onError: (message: string, attempts: number) => void
}
