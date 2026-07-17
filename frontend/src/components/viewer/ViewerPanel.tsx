import { useAppStore } from '../../store/useAppStore'
import ExportMenu from '../ExportMenu'
import DimensionsOverlay from './DimensionsOverlay'
import Viewer from './Viewer'

export default function ViewerPanel() {
  const versions = useAppStore((s) => s.versions)
  const currentVersion = useAppStore((s) => s.currentVersion)
  const version = versions.find((v) => v.version === currentVersion)

  return (
    <section className="viewer-panel">
      <Viewer modelUrl={version?.model_url ?? null} />
      {version && <DimensionsOverlay version={version} />}
      <ExportMenu />
    </section>
  )
}
