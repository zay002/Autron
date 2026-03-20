import { useEffect, useState } from 'react'
import { SimulationView } from './components/SimulationView'
import { ControlConsole } from './components/ControlConsole'
import { useRobotStore } from './store/robotStore'

function App() {
  const { connectionState, connect, disconnect, getState } = useRobotStore()
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
            color="#4ade80"
          />
          <StatusIndicator
            label="Robot"
            active={connectionState === 'connected'}
            color="#60a5fa"
          />
          <StatusIndicator
            label="Simulation"
            active={connectionState === 'connected'}
            color="#facc15"
          />
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        {/* Left Panel: Simulation */}
        <div style={styles.simulationPanel}>
          <SimulationView />
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
          backgroundColor: active ? color : '#666',
          boxShadow: active ? `0 0 8px ${color}` : 'none',
        }}
      />
      <span>{label}</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#1a1a2e',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    background: '#16213e',
    borderBottom: '1px solid #0f3460',
  },
  title: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#fff',
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
    fontSize: '13px',
    color: '#aaa',
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
  simulationPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: '#0f0f23',
  },
  divider: {
    width: '4px',
    background: '#0f3460',
  },
  controlPanel: {
    flex: 0.8,
    display: 'flex',
    flexDirection: 'column',
    background: '#16213e',
    overflow: 'auto',
  },
}

export default App
