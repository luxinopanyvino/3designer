import { exportUrl } from '../api/client'
import { useAppStore } from '../store/useAppStore'

export default function ExportMenu() {
  const sessionId = useAppStore((s) => s.sessionId)
  const currentVersion = useAppStore((s) => s.currentVersion)
  const formats = useAppStore((s) => s.health?.export_formats ?? ['stl', 'step'])

  if (!sessionId || currentVersion === null) return null

  return (
    <div className="export-menu">
      {formats.map((format) => (
        <a
          key={format}
          className="export-button"
          href={exportUrl(sessionId, format, currentVersion)}
          download
        >
          {format.toUpperCase()}
        </a>
      ))}
    </div>
  )
}
