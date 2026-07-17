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
  model_url: string
  code_url: string
  dimensions_mm: { x: number; y: number; z: number }
  volume_mm3: number
  watertight: boolean
  warnings: string[]
  created_at: string
}

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
    code_model_present: boolean
    vision_model_present: boolean
  }
  export_formats: string[]
  bed_size_mm: number
}

export type Stage = 'idle' | 'vision_analyzing' | 'llm_generating' | 'executing' | 'repairing'

export interface EventHandlers {
  onStatus: (stage: Stage, attempt: number) => void
  onCodeDelta: (text: string) => void
  onCompleted: (version: Version & { code: string }) => void
  onError: (message: string, attempts: number) => void
}
