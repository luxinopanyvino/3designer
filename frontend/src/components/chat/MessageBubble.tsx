import type { Message } from '../../api/types'
import { useAppStore } from '../../store/useAppStore'

export default function MessageBubble({ message }: { message: Message }) {
  const versions = useAppStore((s) => s.versions)
  const currentVersion = useAppStore((s) => s.currentVersion)
  const setCurrentVersion = useAppStore((s) => s.setCurrentVersion)

  const version = message.version != null ? versions.find((v) => v.version === message.version) : undefined

  if (message.role === 'user') {
    return (
      <div className="bubble user">
        {message.image_url && <img className="bubble-image" src={message.image_url} alt="referencia" />}
        {message.content}
      </div>
    )
  }

  const isSketch = version?.source === 'sketch'

  return (
    <div className={`bubble assistant ${message.error ? 'error' : ''}`}>
      <div className="bubble-content">{message.content}</div>
      {version && (
        <div className="version-card">
          <div className="version-meta">
            <span className="dims">
              {isSketch
                ? `${version.dimensions_mm.x} × ${version.dimensions_mm.y} mm`
                : `${version.dimensions_mm.x} × ${version.dimensions_mm.y} × ${version.dimensions_mm.z} mm`}
            </span>
            {!isSketch && (
              <span className={`badge ${version.watertight ? 'ok' : 'warn'}`}>
                {version.watertight ? 'estanco' : 'no estanco'}
              </span>
            )}
            {version.source === 'organic' && <span className="badge organic">orgánico</span>}
            {isSketch && <span className="badge sketch">2D</span>}
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
          </div>
        </div>
      )}
    </div>
  )
}
