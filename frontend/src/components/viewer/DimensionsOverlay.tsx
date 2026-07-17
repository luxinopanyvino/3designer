import type { Version } from '../../api/types'

export default function DimensionsOverlay({ version }: { version: Version }) {
  const d = version.dimensions_mm
  return (
    <div className="dimensions-overlay">
      <div className="dims-line">
        v{version.version} · {d.x} × {d.y} × {d.z} mm
      </div>
      <div className="dims-line secondary">
        {(version.volume_mm3 / 1000).toFixed(1)} cm³ · {version.watertight ? 'estanco ✔' : 'no estanco ⚠'}
      </div>
      {version.warnings.map((w, i) => (
        <div key={i} className="dims-line warning">⚠ {w}</div>
      ))}
    </div>
  )
}
