import { create } from 'zustand'
import * as api from '../api/client'
import type { Health, Message, Stage, Version } from '../api/types'

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
  init: () => Promise<void>
  newSession: () => Promise<void>
  sendMessage: (content: string) => Promise<void>
  setCurrentVersion: (v: number) => void
}

const SESSION_KEY = 'printcad-session-id'

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

  init: async () => {
    api.getHealth().then((health) => set({ health })).catch(() => set({ health: null }))

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

  sendMessage: async (content: string) => {
    const { sessionId, busy } = get()
    if (!sessionId || busy || !content.trim()) return

    set((s) => ({
      busy: true,
      stage: 'llm_generating',
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
      const { job_id } = await api.postMessage(sessionId, content)
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
}))
