import { useAppStore } from '../../store/useAppStore'

const STAGE_LABELS: Record<string, string> = {
  organic_generating: 'Reconstruyendo la forma 3D (TRELLIS)…',
  vectorizing: 'Vectorizando contornos…',
  sketch_refining: 'Limpiando la geometría (IA)…',
}

export default function GenerationStatus() {
  const stage = useAppStore((s) => s.stage)

  return (
    <div className="bubble assistant generating">
      <div className="status-row">
        <span className="spinner" />
        <span>{STAGE_LABELS[stage] ?? 'Procesando…'}</span>
      </div>
    </div>
  )
}
