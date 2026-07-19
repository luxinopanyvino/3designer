import type { Version } from '../../api/types'

export default function SketchViewer({ version }: { version: Version }) {
  if (!version.preview_url) return null
  return (
    <div className="sketch-viewer">
      <img src={version.preview_url} alt={`Plano 2D v${version.version}`} />
    </div>
  )
}
