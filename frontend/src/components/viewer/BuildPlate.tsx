import { useMemo } from 'react'
import { BufferGeometry, Line, LineBasicMaterial, Vector3 } from 'three'

/** Print-bed grid on the XY plane (Z-up scene): 10 mm cells, bold border. */
export default function BuildPlate({ size }: { size: number }) {
  const half = size / 2

  const border = useMemo(() => {
    const geometry = new BufferGeometry().setFromPoints([
      new Vector3(-half, -half, 0),
      new Vector3(half, -half, 0),
      new Vector3(half, half, 0),
      new Vector3(-half, half, 0),
      new Vector3(-half, -half, 0),
    ])
    return new Line(geometry, new LineBasicMaterial({ color: '#5a80b8' }))
  }, [half])

  return (
    <group>
      {/* gridHelper lives in the XZ plane; rotate it into XY for a Z-up world */}
      <gridHelper
        args={[size, size / 10, '#3d4453', '#262b36']}
        rotation={[Math.PI / 2, 0, 0]}
        position={[0, 0, -0.05]}
      />
      <primitive object={border} />
    </group>
  )
}
