import { useEffect } from 'react'
import ChatPanel from './components/chat/ChatPanel'
import ViewerPanel from './components/viewer/ViewerPanel'
import { useAppStore } from './store/useAppStore'

export default function App() {
  const init = useAppStore((s) => s.init)
  const health = useAppStore((s) => s.health)
  const newSession = useAppStore((s) => s.newSession)

  useEffect(() => {
    void init()
  }, [init])

  const organicOk = health?.organic_available ?? false

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          PrintCAD <span className="subtitle">foto → 3D imprimible o plano 2D DXF</span>
        </h1>
        <div className="header-actions">
          <span
            className={`health-dot ${organicOk ? 'ok' : 'bad'}`}
            title={organicOk ? 'Servicio 3D listo' : 'Servicio 3D (TRELLIS.2) no disponible'}
          />
          <button className="ghost" onClick={() => void newSession()}>
            Nueva sesión
          </button>
        </div>
      </header>
      {health && !organicOk && (
        <div className="banner">
          Servicio 3D (TRELLIS.2, puerto 8001) no disponible — solo modo 2D DXF. Arranca organic/
          con: uv run uvicorn service:app --port 8001
        </div>
      )}
      <main className="app-main">
        <ChatPanel />
        <ViewerPanel />
      </main>
    </div>
  )
}
