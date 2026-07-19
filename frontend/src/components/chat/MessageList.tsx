import { useEffect, useRef } from 'react'
import { useAppStore } from '../../store/useAppStore'
import GenerationStatus from './GenerationStatus'
import MessageBubble from './MessageBubble'

export default function MessageList() {
  const messages = useAppStore((s) => s.messages)
  const busy = useAppStore((s) => s.busy)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, busy])

  return (
    <div className="message-list">
      {messages.length === 0 && !busy && (
        <div className="empty-hint">
          <p>Adjunta una foto (📷) y elige modo:</p>
          <ul>
            <li>
              <strong>🗿 3D (foto)</strong>: reconstrucción neuronal del objeto → malla imprimible
              (STL/3MF)
            </li>
            <li>
              <strong>📐 2D DXF</strong>: contornos de una pieza plana → plano vectorial (DXF/SVG)
            </li>
          </ul>
          <p>
            Opcional: indica la medida real en el texto ("altura 120 mm", "ancho 6 cm") o pide
            limpieza en 2D ("solo el contorno exterior").
          </p>
        </div>
      )}
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      {busy && <GenerationStatus />}
      <div ref={bottomRef} />
    </div>
  )
}
