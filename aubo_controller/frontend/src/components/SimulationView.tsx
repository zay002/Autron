import { Canvas } from '@react-three/fiber'
import { OrbitControls, Grid, Environment } from '@react-three/drei'
import { useRobotStore } from '../store/robotStore'

// Robot link colors
const LINK_COLORS = {
  base: '#4a5568',
  link1: '#3182ce',
  link2: '#3182ce',
  link3: '#3182ce',
  link4: '#805ad5',
  link5: '#805ad5',
  link6: '#e53e3e',
  endEffector: '#38a169',
}

function RobotArm() {
  const jointPositions = useRobotStore((state) => state.jointPositions)

  // Simple kinematic chain based on joint positions
  // This is a simplified visualization - actual DH parameters would be used in production
  const joint1 = jointPositions[0] || 0
  const joint2 = jointPositions[1] || 0
  const joint3 = jointPositions[2] || 0
  const joint4 = jointPositions[3] || 0
  const joint5 = jointPositions[4] || 0
  const joint6 = jointPositions[5] || 0

  // Calculate link positions (simplified forward kinematics)
  const link1Length = 0.3
  const link2Length = 0.4
  const link3Length = 0.35
  const link4Length = 0.25
  const link5Length = 0.2
  const link6Length = 0.15

  // Base position
  const baseY = 0.05

  return (
    <group position={[0, baseY, 0]}>
      {/* Base */}
      <mesh position={[0, 0, 0]}>
        <cylinderGeometry args={[0.1, 0.12, 0.1, 32]} />
        <meshStandardMaterial color={LINK_COLORS.base} />
      </mesh>

      {/* Joint 1 */}
      <group rotation={[0, 0, joint1]}>
        {/* Link 1 */}
        <mesh position={[0, link1Length / 2, 0]}>
          <cylinderGeometry args={[0.06, 0.06, link1Length, 16]} />
          <meshStandardMaterial color={LINK_COLORS.link1} />
        </mesh>

        {/* Joint 2 */}
        <group position={[0, link1Length, 0]} rotation={[0, 0, joint2]}>
          {/* Link 2 */}
          <mesh position={[0, link2Length / 2, 0]}>
            <cylinderGeometry args={[0.05, 0.05, link2Length, 16]} />
            <meshStandardMaterial color={LINK_COLORS.link2} />
          </mesh>

          {/* Joint 3 */}
          <group position={[0, link2Length, 0]} rotation={[0, 0, joint3]}>
            {/* Link 3 */}
            <mesh position={[0, link3Length / 2, 0]}>
              <cylinderGeometry args={[0.04, 0.04, link3Length, 16]} />
              <meshStandardMaterial color={LINK_COLORS.link3} />
            </mesh>

            {/* Joint 4 */}
            <group position={[0, link3Length, 0]} rotation={[0, 0, joint4]}>
              {/* Link 4 */}
              <mesh position={[0, link4Length / 2, 0]}>
                <cylinderGeometry args={[0.035, 0.035, link4Length, 16]} />
                <meshStandardMaterial color={LINK_COLORS.link4} />
              </mesh>

              {/* Joint 5 */}
              <group position={[0, link4Length, 0]} rotation={[joint5, 0, 0]}>
                {/* Link 5 */}
                <mesh position={[0, link5Length / 2, 0]}>
                  <cylinderGeometry args={[0.03, 0.03, link5Length, 16]} />
                  <meshStandardMaterial color={LINK_COLORS.link5} />
                </mesh>

                {/* Joint 6 */}
                <group position={[0, link5Length, 0]} rotation={[0, 0, joint6]}>
                  {/* Link 6 */}
                  <mesh position={[0, link6Length / 2, 0]}>
                    <cylinderGeometry args={[0.025, 0.025, link6Length, 16]} />
                    <meshStandardMaterial color={LINK_COLORS.link6} />
                  </mesh>

                  {/* End Effector */}
                  <mesh position={[0, link6Length + 0.05, 0]}>
                    <sphereGeometry args={[0.06, 16, 16]} />
                    <meshStandardMaterial color={LINK_COLORS.endEffector} />
                  </mesh>
                </group>
              </group>
            </group>
          </group>
        </group>
      </group>
    </group>
  )
}

export function SimulationView() {
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Robot Simulation</span>
        <span style={styles.badge}>Simulation</span>
      </div>
      <div style={styles.canvas}>
        <Canvas
          camera={{ position: [1.5, 1.5, 1.5], fov: 50 }}
          style={{ background: '#0a0a15' }}
        >
          <ambientLight intensity={0.5} />
          <directionalLight position={[5, 5, 5]} intensity={1} />
          <directionalLight position={[-3, 3, -3]} intensity={0.3} />

          <RobotArm />

          {/* Ground grid */}
          <Grid
            args={[10, 10]}
            cellSize={0.1}
            cellThickness={0.5}
            cellColor="#1e3a5f"
            sectionSize={1}
            sectionThickness={1}
            sectionColor="#0f3460"
            fadeDistance={10}
            fadeStrength={1}
            followCamera={false}
            infiniteGrid
          />

          <OrbitControls
            makeDefault
            minPolarAngle={0}
            maxPolarAngle={Math.PI / 2}
            enablePan={true}
            panSpeed={0.5}
            rotateSpeed={0.5}
          />

          <Environment preset="city" background={false} />
        </Canvas>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    background: '#0f0f23',
    borderBottom: '1px solid #1e3a5f',
  },
  title: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#fff',
  },
  badge: {
    fontSize: '11px',
    padding: '2px 8px',
    background: '#0f3460',
    borderRadius: '4px',
    color: '#60a5fa',
  },
  canvas: {
    flex: 1,
    position: 'relative',
  },
}
