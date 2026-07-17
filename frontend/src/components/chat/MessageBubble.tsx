import { useState } from 'react'
import { getCode } from '../../api/client'
import type { Message } from '../../api/types'
import { useAppStore } from '../../store/useAppStore'

export default function MessageBubble({ message }: { message: Message }) {
  const versions = useAppStore((s) => s.versions)
  const currentVersion = useAppStore((s) => s.currentVersion)
  const setCurrentVersion = useAppStore((s) => s.setCurrentVersion)
  const [code, setCode] = useState<string | null>(null)
  const [showCode, setShowCode] = useState(false)

  const version = message.version != null ? versions.find((v) => v.version === message.version) : undefined

  if (message.role === 'user') {
    return <div className="bubble user">{message.content}</div>
  }

  const toggleCode = async () => {
    if (!showCode && code === null && version) {
      setCode(await getCode(version.code_url))
    }
    setShowCode(!showCode)
  }

  return (
    <div className={`bubble assistant ${message.error ? 'error' : ''}`}>
      <div className="bubble-content">{message.content}</div>
      {version && (
        <div className="version-card">
          <div className="version-meta">
            <span className="dims">
              {version.dimensions_mm.x} × {version.dimensions_mm.y} × {version.dimensions_mm.z} mm
            </span>
            <span className={`badge ${version.watertight ? 'ok' : 'warn'}`}>
              {version.watertight ? 'estanco' : 'no estanco'}
            </span>
          </div>
          {version.warnings.map((w, i) => (
            <div key={i} className="warning">⚠ {w}</div>
          ))}
          <div className="version-actions">
            {currentVersion !== version.version && (
              <button className="ghost small" onClick={() => setCurrentVersion(version.version)}>
                Ver v{version.version}
              </button>
            )}
            <button className="ghost small" onClick={() => void toggleCode()}>
              {showCode ? 'Ocultar código' : 'Ver código'}
            </button>
          </div>
          {showCode && code && <pre className="code-block">{code}</pre>}
        </div>
      )}
    </div>
  )
}
