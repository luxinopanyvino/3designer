import { OrbitControls } from '@react-three/drei'
import { Canvas } from '@react-three/fiber'
import { Suspense } from 'react'
import BuildPlate from './BuildPlate'
import ModelMesh from './ModelMesh'

/** CAD-style scene: Z is up, 1 unit = 1 mm. */
export default function Viewer({ modelUrl }: { modelUrl: string | null }) {
  return (
    <Canvas
      className="viewer-canvas"
      camera={{ position: [170, -170, 130], up: [0, 0, 1], fov: 40, near: 1, far: 5000 }}
    >
      <color attach="background" args={['#15171c']} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[150, -100, 250]} intensity={1.4} />
      <directionalLight position={[-120, 150, 100]} intensity={0.5} />
      <BuildPlate size={220} />
      <Suspense fallback={null}>{modelUrl && <ModelMesh url={modelUrl} />}</Suspense>
      <OrbitControls makeDefault target={[0, 0, 20]} maxPolarAngle={Math.PI * 0.95} />
    </Canvas>
  )
}
