import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../../store/useAppStore'

export default function MessageInput() {
  const [value, setValue] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const busy = useAppStore((s) => s.busy)
  const sendMessage = useAppStore((s) => s.sendMessage)
  const hasModel = useAppStore((s) => s.versions.length > 0)
  const visionAvailable = useAppStore((s) => s.health?.ollama.vision_model_present ?? true)
  const mode = useAppStore((s) => s.mode)
  const setMode = useAppStore((s) => s.setMode)
  const organicAvailable = useAppStore((s) => s.health?.organic_available ?? false)
  const organicSizeMm = useAppStore((s) => s.organicSizeMm)
  const setOrganicSizeMm = useAppStore((s) => s.setOrganicSizeMm)

  useEffect(() => {
    if (!image) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(image)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [image])

  const canSend = mode === 'organic' ? image !== null : value.trim() !== '' || image !== null

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
          className={`mode-option ${mode === 'cad' ? 'active' : ''}`}
          onClick={() => setMode('cad')}
          title="Piezas funcionales: código CAD paramétrico, editable por chat, export STEP"
        >
          ⚙ Funcional (CAD)
        </button>
        <button
          className={`mode-option ${mode === 'organic' ? 'active' : ''}`}
          disabled={!organicAvailable}
          onClick={() => setMode('organic')}
          title={
            organicAvailable
              ? 'Formas orgánicas: reconstrucción neuronal desde una foto (TRELLIS)'
              : 'Servicio orgánico no disponible — arranca organic/ (uv run uvicorn service:app --port 8001)'
          }
        >
          🗿 Orgánico (foto)
        </button>
        {mode === 'organic' && (
          <label className="size-input">
            tamaño
            <input
              type="number"
              min={5}
              max={220}
              value={organicSizeMm}
              onChange={(e) => setOrganicSizeMm(Number(e.target.value) || 80)}
            />
            mm
          </label>
        )}
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
          disabled={busy || !visionAvailable}
          title={
            visionAvailable
              ? 'Adjuntar imagen de referencia'
              : 'Modelo de visión no disponible (ollama pull qwen3-vl:8b)'
          }
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
              ? 'Adjunta una foto del objeto (el texto es opcional)…'
              : image
                ? 'Añade dimensiones reales… (p. ej. "el ancho real es 60 mm")'
                : hasModel
                  ? 'Refina el modelo… (p. ej. "hazlo 10 mm más ancho")'
                  : 'Describe la pieza a imprimir o adjunta una foto…'
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
