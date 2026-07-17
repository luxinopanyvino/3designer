import { useGLTF } from '@react-three/drei'
import { useEffect, useMemo } from 'react'
import { Mesh, MeshStandardMaterial } from 'three'

const MATERIAL = new MeshStandardMaterial({
  color: '#ff8c42', // PLA orange
  roughness: 0.55,
  metalness: 0.05,
})

/** GLB comes from trimesh with Z-up millimeter coordinates, matching the scene. */
export default function ModelMesh({ url }: { url: string }) {
  const { scene } = useGLTF(url)

  const prepared = useMemo(() => {
    const clone = scene.clone(true)
    clone.traverse((obj) => {
      if (obj instanceof Mesh) {
        obj.material = MATERIAL
        obj.castShadow = true
      }
    })
    return clone
  }, [scene])

  useEffect(() => () => useGLTF.clear(url), [url])

  return <primitive object={prepared} />
}
