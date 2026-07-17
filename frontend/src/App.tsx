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

  const ollamaOk = health?.ollama.reachable && health.ollama.code_model_present

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          PrintCAD <span className="subtitle">diseño 3D imprimible con IA local</span>
        </h1>
        <div className="header-actions">
          <span className={`health-dot ${ollamaOk ? 'ok' : 'bad'}`} title={ollamaOk ? 'Ollama listo' : 'Ollama no disponible o falta el modelo'} />
          <button className="ghost" onClick={() => void newSession()}>
            Nueva sesión
          </button>
        </div>
      </header>
      {health && !ollamaOk && (
        <div className="banner">
          {health.ollama.reachable
            ? 'El modelo de código no está en Ollama. Ejecuta: ollama pull qwen2.5-coder:14b'
            : 'No se puede conectar con Ollama en localhost:11434. ¿Está arrancado?'}
        </div>
      )}
      <main className="app-main">
        <ChatPanel />
        <ViewerPanel />
      </main>
    </div>
  )
}
