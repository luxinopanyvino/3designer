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
  health: Health | null
  mode: Mode
  sizeMm: number
  refreshHealth: () => Promise<void>
  init: () => Promise<void>
  newSession: () => Promise<void>
  sendMessage: (content: string, image?: File) => Promise<void>
  setCurrentVersion: (v: number) => void
  setMode: (mode: Mode) => void
  setSizeMm: (mm: number) => void
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
  health: null,
  mode: 'organic',
  sizeMm: 80,

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
    })
  },

  sendMessage: async (content: string, image?: File) => {
    const { sessionId, busy, mode, sizeMm } = get()
    if (!sessionId || busy || !image) return

    set((s) => ({
      busy: true,
      stage: mode === 'organic' ? 'organic_generating' : 'vectorizing',
      attempt: 1,
      messages: [
        ...s.messages,
        {
          id: -Date.now(),
          role: 'user',
          content,
          version: null,
          error: false,
          image_url: URL.createObjectURL(image),
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
      const { job_id } = await api.postMessage(sessionId, content, image, mode, sizeMm)
      api.subscribeEvents(sessionId, job_id, {
        onStatus: (stage, attempt) => set({ stage, attempt }),
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
  setSizeMm: (mm: number) => set({ sizeMm: mm }),
}))
