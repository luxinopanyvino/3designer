import { create } from 'zustand'
import * as api from '../api/client'
import type { Health, Message, Mode, Stage, Version } from '../api/types'

interface AppState {
  sessionId: string | null
  messages: Message[]
  versions: Version[]
  currentVersion: number | null
  busy: boolean
  stage: Stage
  attempt: number
  streamedCode: string
  health: Health | null
  mode: Mode
  organicSizeMm: number
  refreshHealth: () => Promise<void>
  init: () => Promise<void>
  newSession: () => Promise<void>
  sendMessage: (content: string, image?: File) => Promise<void>
  setCurrentVersion: (v: number) => void
  setMode: (mode: Mode) => void
  setOrganicSizeMm: (mm: number) => void
}

const SESSION_KEY = 'printcad-session-id'
const HEALTH_POLL_MS = 10_000

let healthTimer: number | undefined

export const useAppStore = create<AppState>((set, get) => ({
  sessionId: null,
  messages: [],
  versions: [],
  currentVersion: null,
  busy: false,
  stage: 'idle',
  attempt: 1,
  streamedCode: '',
  health: null,
  mode: 'cad',
  organicSizeMm: 80,

  refreshHealth: async () => {
    try {
      set({ health: await api.getHealth() })
    } catch {
      set({ health: null })
    }
  },

  init: async () => {
    void get().refreshHealth()
    window.clearInterval(healthTimer)
    healthTimer = window.setInterval(() => void get().refreshHealth(), HEALTH_POLL_MS)

    const saved = localStorage.getItem(SESSION_KEY)
    if (saved) {
      try {
        const session = await api.getSession(saved)
        set({
          sessionId: session.id,
          messages: session.messages,
          versions: session.versions,
          currentVersion: session.versions.at(-1)?.version ?? null,
        })
        return
      } catch {
        localStorage.removeItem(SESSION_KEY)
      }
    }
    await get().newSession()
  },

  newSession: async () => {
    const { id } = await api.createSession()
    localStorage.setItem(SESSION_KEY, id)
    set({
      sessionId: id,
      messages: [],
      versions: [],
      currentVersion: null,
      busy: false,
      stage: 'idle',
      streamedCode: '',
    })
  },

  sendMessage: async (content: string, image?: File) => {
    const { sessionId, busy, mode, organicSizeMm } = get()
    if (!sessionId || busy || (!content.trim() && !image)) return
    if (mode === 'organic' && !image) return

    set((s) => ({
      busy: true,
      stage: mode === 'organic' ? 'organic_generating' : image ? 'vision_analyzing' : 'llm_generating',
      attempt: 1,
      streamedCode: '',
      messages: [
        ...s.messages,
        {
          id: -Date.now(),
          role: 'user',
          content,
          version: null,
          error: false,
          image_url: image ? URL.createObjectURL(image) : null,
          created_at: new Date().toISOString(),
        },
      ],
    }))

    const refreshSession = async () => {
      try {
        const session = await api.getSession(sessionId)
        set({ messages: session.messages, versions: session.versions })
      } catch {
        // keep optimistic state
      }
    }

    try {
      const { job_id } = await api.postMessage(
        sessionId,
        content,
        image,
        mode,
        mode === 'organic' ? organicSizeMm : undefined,
      )
      api.subscribeEvents(sessionId, job_id, {
        onStatus: (stage, attempt) => set({ stage, attempt }),
        onCodeDelta: (text) => set((s) => ({ streamedCode: s.streamedCode + text })),
        onCompleted: async (version) => {
          await refreshSession()
          set({ busy: false, stage: 'idle', currentVersion: version.version })
        },
        onError: async () => {
          await refreshSession()
          set({ busy: false, stage: 'idle' })
        },
      })
    } catch (err) {
      set((s) => ({
        busy: false,
        stage: 'idle',
        messages: [
          ...s.messages,
          {
            id: -Date.now() - 1,
            role: 'assistant',
            content: `Error: ${(err as Error).message}`,
            version: null,
            error: true,
            created_at: new Date().toISOString(),
          },
        ],
      }))
    }
  },

  setCurrentVersion: (v: number) => set({ currentVersion: v }),
  setMode: (mode: Mode) => set({ mode }),
  setOrganicSizeMm: (mm: number) => set({ organicSizeMm: mm }),
}))
