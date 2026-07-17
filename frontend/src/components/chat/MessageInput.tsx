import { useState } from 'react'
import { useAppStore } from '../../store/useAppStore'

export default function MessageInput() {
  const [value, setValue] = useState('')
  const busy = useAppStore((s) => s.busy)
  const sendMessage = useAppStore((s) => s.sendMessage)
  const hasModel = useAppStore((s) => s.versions.length > 0)

  const send = () => {
    if (!value.trim() || busy) return
    void sendMessage(value.trim())
    setValue('')
  }

  return (
    <div className="message-input">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            send()
          }
        }}
        placeholder={hasModel ? 'Refina el modelo… (p. ej. "hazlo 10 mm más ancho")' : 'Describe la pieza a imprimir…'}
        rows={2}
        disabled={busy}
      />
      <button onClick={send} disabled={busy || !value.trim()}>
        {busy ? 'Generando…' : 'Enviar'}
      </button>
    </div>
  )
}
