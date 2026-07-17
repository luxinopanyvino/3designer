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
          <p>Describe la pieza que quieres imprimir. Por ejemplo:</p>
          <ul>
            <li>"una caja de 80x60x30 mm con tapa y paredes de 2 mm"</li>
            <li>"un soporte en L con dos agujeros M4"</li>
            <li>"un gancho de pared para auriculares"</li>
          </ul>
          <p>Luego refínala: "hazla 10 mm más ancha", "añade agujeros M3"…</p>
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
