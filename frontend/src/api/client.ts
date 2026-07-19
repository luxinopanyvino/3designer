import type { EventHandlers, Health, Mode, SessionData, Stage, Version } from './types'

const API = '/api'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export function getHealth(): Promise<Health> {
  return request(`${API}/health`)
}

export function createSession(): Promise<{ id: string }> {
  return request(`${API}/sessions`, { method: 'POST' })
}

export function getSession(id: string): Promise<SessionData> {
  return request(`${API}/sessions/${id}`)
}

export function postMessage(
  id: string,
  content: string,
  image: File,
  mode: Mode,
  targetSizeMm?: number,
): Promise<{ job_id: string }> {
  const form = new FormData()
  form.append('content', content)
  form.append('mode', mode)
  form.append('image', image)
  if (targetSizeMm) form.append('target_size_mm', String(targetSizeMm))
  return request(`${API}/sessions/${id}/messages`, { method: 'POST', body: form })
}

export function exportUrl(sessionId: string, format: string, version: number | 'latest' = 'latest'): string {
  return `${API}/sessions/${sessionId}/export?format=${format}&version=${version}`
}

export function subscribeEvents(sessionId: string, jobId: string, handlers: EventHandlers): () => void {
  const source = new EventSource(`${API}/sessions/${sessionId}/events?job_id=${jobId}`)

  source.addEventListener('status', (e) => {
    const data = JSON.parse((e as MessageEvent).data)
    handlers.onStatus(data.stage as Stage, data.attempt)
  })
  source.addEventListener('completed', (e) => {
    handlers.onCompleted(JSON.parse((e as MessageEvent).data) as Version)
    source.close()
  })
  source.addEventListener('error', (e) => {
    // Both SSE transport errors and our named "error" event land here.
    const data = (e as MessageEvent).data
    if (data) {
      const parsed = JSON.parse(data)
      handlers.onError(parsed.message, parsed.attempts)
    } else {
      handlers.onError('Se perdió la conexión con el servidor.', 0)
    }
    source.close()
  })

  return () => source.close()
}
