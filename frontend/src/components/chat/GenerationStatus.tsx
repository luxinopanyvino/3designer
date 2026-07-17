import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../../store/useAppStore'

const STAGE_LABELS: Record<string, string> = {
  vision_analyzing: 'Analizando la imagen…',
  llm_generating: 'Escribiendo código CAD…',
  executing: 'Construyendo el modelo…',
  repairing: 'Corrigiendo errores…',
  organic_generating: 'Reconstruyendo la forma 3D (TripoSR)…',
}

export default function GenerationStatus() {
  const stage = useAppStore((s) => s.stage)
  const attempt = useAppStore((s) => s.attempt)
  const streamedCode = useAppStore((s) => s.streamedCode)
  const [showCode, setShowCode] = useState(true)
  const codeRef = useRef<HTMLPreElement>(null)

  useEffect(() => {
    if (codeRef.current) codeRef.current.scrollTop = codeRef.current.scrollHeight
  }, [streamedCode])

  return (
    <div className="bubble assistant generating">
      <div className="status-row">
        <span className="spinner" />
        <span>{STAGE_LABELS[stage] ?? 'Pensando…'}</span>
        {attempt > 1 && <span className="attempt">intento {attempt}/3</span>}
        {streamedCode && (
          <button className="ghost small" onClick={() => setShowCode(!showCode)}>
            {showCode ? 'ocultar' : 'ver'} código
          </button>
        )}
      </div>
      {showCode && streamedCode && (
        <pre ref={codeRef} className="code-block streaming">
          {streamedCode}
        </pre>
      )}
    </div>
  )
}
