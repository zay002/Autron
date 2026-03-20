import { useEffect, useState } from 'react'
import { SimulationView } from './components/SimulationView'
import { CameraView } from './components/CameraView'
import { ControlConsole } from './components/ControlConsole'
import { useRobotStore } from './store/robotStore'

function App() {
  const { connectionState, getState } = useRobotStore()
  const [backendConnected, setBackendConnected] = useState(false)

  useEffect(() => {
    // Check backend health
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setBackendConnected(data.status === 'healthy')
      })
      .catch(() => setBackendConnected(false))

    // Poll for robot state
    const interval = setInterval(() => {
      getState()
    }, 100)

    return () => clearInterval(interval)
  }, [getState])

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>Aubo Robot Controller</h1>
        <div style={styles.statusBar}>
          <StatusIndicator
            label="Backend"
            active={backendConnected}
            color="#ff6d00"
          />
          <StatusIndicator
            label="Robot"
            active={connectionState === 'connected'}
            color="#4caf50"
          />
          <StatusIndicator
            label="Simulation"
            active={connectionState === 'connected'}
            color="#2196f3"
          />
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        {/* Left Panel: Camera + Simulation (stacked vertically) */}
        <div style={styles.leftPanel}>
          <div style={styles.cameraPanel}>
            <CameraView />
          </div>
          <div style={styles.simulationPanel}>
            <SimulationView />
          </div>
        </div>

        {/* Divider */}
        <div style={styles.divider} />

        {/* Right Panel: Control Console */}
        <div style={styles.controlPanel}>
          <ControlConsole />
        </div>
      </main>
    </div>
  )
}

interface StatusIndicatorProps {
  label: string
  active: boolean
  color: string
}

function StatusIndicator({ label, active, color }: StatusIndicatorProps) {
  return (
    <div style={styles.statusItem}>
      <div
        style={{
          ...styles.statusDot,
          backgroundColor: active ? color : '#ccc',
          boxShadow: active ? `0 0 8px ${color}` : 'none',
        }}
      />
      <span style={styles.statusLabel}>{label}</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#fff',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    background: '#fff',
    borderBottom: '2px solid #ff6d00',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  title: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#333',
    margin: 0,
  },
  statusBar: {
    display: 'flex',
    gap: '20px',
    alignItems: 'center',
  },
  statusItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusLabel: {
    fontSize: '13px',
    color: '#666',
    fontWeight: 500,
  },
  statusDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    transition: 'all 0.3s ease',
  },
  main: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  leftPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    padding: '4px',
    background: '#f5f5f5',
  },
  cameraPanel: {
    flex: 1,
    minHeight: '200px',
    display: 'flex',
    flexDirection: 'column',
  },
  simulationPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  },
  divider: {
    width: '4px',
    background: '#e0e0e0',
  },
  controlPanel: {
    flex: 0.8,
    display: 'flex',
    flexDirection: 'column',
    background: '#fff',
    overflow: 'auto',
    borderLeft: '1px solid #e0e0e0',
  },
}

export default App
