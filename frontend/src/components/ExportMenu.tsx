import { exportUrl } from '../api/client'
import { useAppStore } from '../store/useAppStore'

const DEFAULT_FORMATS = ['stl'] as const
const SKETCH_FORMATS = ['dxf', 'svg'] as const

export default function ExportMenu() {
  const sessionId = useAppStore((s) => s.sessionId)
  const currentVersion = useAppStore((s) => s.currentVersion)
  const versions = useAppStore((s) => s.versions)
  const allFormats = useAppStore((s) => s.health?.export_formats ?? DEFAULT_FORMATS)

  if (!sessionId || currentVersion === null) return null

  const version = versions.find((v) => v.version === currentVersion)
  const formats =
    version?.source === 'sketch'
      ? SKETCH_FORMATS
      : allFormats.filter((f) => !['dxf', 'svg', 'step'].includes(f))

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
