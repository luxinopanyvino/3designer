import { useAppStore } from '../../store/useAppStore'
import ExportMenu from '../ExportMenu'
import DimensionsOverlay from './DimensionsOverlay'
import SketchViewer from './SketchViewer'
import Viewer from './Viewer'

export default function ViewerPanel() {
  const versions = useAppStore((s) => s.versions)
  const currentVersion = useAppStore((s) => s.currentVersion)
  const version = versions.find((v) => v.version === currentVersion)

  return (
    <section className="viewer-panel">
      {version?.source === 'sketch' ? (
        <SketchViewer version={version} />
      ) : (
        <Viewer modelUrl={version?.model_url ?? null} />
      )}
      {version && <DimensionsOverlay version={version} />}
      <ExportMenu />
    </section>
  )
}
