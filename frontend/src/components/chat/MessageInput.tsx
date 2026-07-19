import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../../store/useAppStore'

export default function MessageInput() {
  const [value, setValue] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const busy = useAppStore((s) => s.busy)
  const sendMessage = useAppStore((s) => s.sendMessage)
  const mode = useAppStore((s) => s.mode)
  const setMode = useAppStore((s) => s.setMode)
  const organicAvailable = useAppStore((s) => s.health?.organic_available ?? false)
  const sizeMm = useAppStore((s) => s.sizeMm)
  const setSizeMm = useAppStore((s) => s.setSizeMm)

  useEffect(() => {
    if (!image) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(image)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [image])

  const canSend = image !== null

  const send = () => {
    if (!canSend || busy) return
    void sendMessage(value.trim(), image ?? undefined)
    setValue('')
    setImage(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div className="message-input-wrap">
      <div className="mode-toggle">
        <button
          className={`mode-option ${mode === 'organic' ? 'active' : ''}`}
          disabled={!organicAvailable}
          onClick={() => setMode('organic')}
          title={
            organicAvailable
              ? 'Foto → malla 3D imprimible (reconstrucción neuronal TRELLIS)'
              : 'Servicio 3D no disponible — arranca organic/ (uv run uvicorn service:app --port 8001)'
          }
        >
          🗿 3D (foto)
        </button>
        <button
          className={`mode-option ${mode === 'sketch' ? 'active' : ''}`}
          onClick={() => setMode('sketch')}
          title="Foto de una pieza plana → contornos vectorizados en DXF"
        >
          📐 2D DXF
        </button>
        <label className="size-input">
          {mode === 'organic' ? 'tamaño' : 'ancho'}
          <input
            type="number"
            min={5}
            max={220}
            value={sizeMm}
            onChange={(e) => setSizeMm(Number(e.target.value) || 80)}
          />
          mm
        </label>
      </div>
      {preview && (
        <div className="image-preview">
          <img src={preview} alt="referencia" />
          <button className="ghost small" onClick={() => setImage(null)}>
            quitar imagen
          </button>
        </div>
      )}
      <div className="message-input">
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          hidden
          onChange={(e) => setImage(e.target.files?.[0] ?? null)}
        />
        <button
          className="ghost attach"
          disabled={busy}
          title="Adjuntar la foto (obligatoria en ambos modos)"
          onClick={() => fileRef.current?.click()}
        >
          📷
        </button>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
          placeholder={
            mode === 'organic'
              ? 'Adjunta una foto del objeto; opcional: "altura 120 mm"…'
              : 'Adjunta una foto de la pieza plana; opcional: "ancho 50 mm", "solo contorno exterior"…'
          }
          rows={2}
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !canSend}>
          {busy ? 'Generando…' : 'Enviar'}
        </button>
      </div>
    </div>
  )
}
