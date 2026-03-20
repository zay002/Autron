import { useState, useEffect } from 'react'
import { useRobotStore } from '../store/robotStore'

const JOINT_NAMES = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6']
const JOINT_LIMITS = {
  min: [-180, -90, -180, -180, -90, -180],
  max: [180, 90, 180, 180, 90, 180],
}

type TabType = 'control' | 'config' | 'console'

export function ControlConsole() {
  const {
    connectionState,
    jointPositions,
    endEffectorPosition,
    config,
    connectionTestResult,
    connect,
    disconnect,
    testConnection,
    moveJoints,
    loadConfig,
    updateConfig,
  } = useRobotStore()

  const [activeTab, setActiveTab] = useState<TabType>('control')
  const [targetPositions, setTargetPositions] = useState<number[]>([0, -45, 90, 0, 90, 0])
  const [speed, setSpeed] = useState(50)
  const [logs, setLogs] = useState<string[]>([])
  const [robotIp, setRobotIp] = useState('192.168.1.100')

  // Load config on mount
  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  // Update robot IP from config
  useEffect(() => {
    if (config?.robot?.robot_ip) {
      setRobotIp(config.robot.robot_ip)
    }
  }, [config])

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs((prev) => [...prev.slice(-100), `[${timestamp}] ${message}`])
  }

  useEffect(() => {
    if (connectionState === 'connected') {
      addLog('Connected to robot')
    } else if (connectionState === 'disconnected') {
      addLog('Disconnected from robot')
    }
  }, [connectionState])

  const handleConnect = async () => {
    if (connectionState === 'connected') {
      await disconnect()
    } else {
      await connect(robotIp, config?.robot?.simulation ?? true)
    }
  }

  const handleTestConnection = async () => {
    addLog(`Testing connection to ${robotIp}...`)
    await testConnection(robotIp)
  }

  const handleMoveToPosition = async () => {
    const radians = targetPositions.map((deg) => (deg * Math.PI) / 180)
    await moveJoints(radians, speed / 100)
    addLog(`Moving to: ${targetPositions.map((p) => p.toFixed(1)).join(', ')}°`)
  }

  const handleSliderChange = (index: number, value: number) => {
    const newPositions = [...targetPositions]
    newPositions[index] = value
    setTargetPositions(newPositions)
  }

  const isConnected = connectionState === 'connected'

  return (
    <div style={styles.container}>
      {/* Tab Navigation */}
      <div style={styles.tabBar}>
        {(['control', 'config', 'console'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              ...styles.tab,
              ...(activeTab === tab ? styles.tabActive : {}),
            }}
          >
            {tab === 'control' ? 'Control' : tab === 'config' ? 'Config' : 'Console'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={styles.content}>
        {activeTab === 'control' && (
          <ControlTab
            robotIp={robotIp}
            setRobotIp={setRobotIp}
            connectionState={connectionState}
            connectionTestResult={connectionTestResult}
            targetPositions={targetPositions}
            speed={speed}
            jointPositions={jointPositions}
            endEffectorPosition={endEffectorPosition}
            isConnected={isConnected}
            onConnect={handleConnect}
            onTestConnection={handleTestConnection}
            onMoveToPosition={handleMoveToPosition}
            onSliderChange={handleSliderChange}
            onSpeedChange={setSpeed}
            onQuickPosition={(name, positions) => {
              setTargetPositions(positions)
              addLog(`Selected ${name} position`)
            }}
          />
        )}

        {activeTab === 'config' && (
          <ConfigTab
            config={config}
            robotIp={robotIp}
            onRobotIpChange={setRobotIp}
            onUpdateConfig={updateConfig}
          />
        )}

        {activeTab === 'console' && (
          <ConsoleTab logs={logs} />
        )}
      </div>
    </div>
  )
}

interface ControlTabProps {
  robotIp: string
  setRobotIp: (ip: string) => void
  connectionState: string
  connectionTestResult: { reachable: boolean; message: string } | null
  targetPositions: number[]
  speed: number
  jointPositions: number[]
  endEffectorPosition: number[]
  isConnected: boolean
  onConnect: () => void
  onTestConnection: () => void
  onMoveToPosition: () => void
  onSliderChange: (index: number, value: number) => void
  onSpeedChange: (speed: number) => void
  onQuickPosition: (name: string, positions: number[]) => void
}

function ControlTab({
  robotIp,
  setRobotIp,
  connectionState,
  connectionTestResult,
  targetPositions,
  speed,
  jointPositions,
  endEffectorPosition,
  isConnected,
  onConnect,
  onTestConnection,
  onMoveToPosition,
  onSliderChange,
  onSpeedChange,
  onQuickPosition,
}: ControlTabProps) {
  return (
    <div style={styles.scrollContent}>
      {/* Connection Panel */}
      <Panel title="Connection">
        <div style={styles.connectionRow}>
          <input
            type="text"
            placeholder="Robot IP"
            value={robotIp}
            onChange={(e) => setRobotIp(e.target.value)}
            disabled={isConnected}
            style={styles.input}
          />
          <button
            onClick={onTestConnection}
            disabled={isConnected}
            style={styles.testButton}
          >
            Test
          </button>
        </div>

        {/* Connection Test Result */}
        {connectionTestResult && (
          <div
            style={{
              ...styles.testResult,
              background: connectionTestResult.reachable ? '#1a4731' : '#4a1f1f',
              borderColor: connectionTestResult.reachable ? '#38a169' : '#e53e3e',
            }}
          >
            <span style={styles.testIcon}>
              {connectionTestResult.reachable ? '✓' : '✗'}
            </span>
            <span>{connectionTestResult.message}</span>
          </div>
        )}

        <div style={styles.connectionButtons}>
          <button
            onClick={onConnect}
            style={{
              ...styles.button,
              flex: 1,
              background: isConnected ? '#e53e3e' : '#38a169',
            }}
          >
            {isConnected ? 'Disconnect' : 'Connect'}
          </button>
        </div>

        <div style={styles.statusRow}>
          <span style={styles.statusLabel}>Status:</span>
          <span
            style={{
              ...styles.statusValue,
              color: isConnected ? '#38a169' : '#e53e3e',
            }}
          >
            {connectionState}
          </span>
        </div>
      </Panel>

      {/* Joint Control Panel */}
      <Panel title="Joint Control">
        <div style={styles.jointGrid}>
          {JOINT_NAMES.map((name, i) => (
            <div key={name} style={styles.jointControl}>
              <div style={styles.jointHeader}>
                <span style={styles.jointName}>{name}</span>
                <span style={styles.jointValue}>{targetPositions[i].toFixed(1)}°</span>
              </div>
              <input
                type="range"
                min={JOINT_LIMITS.min[i]}
                max={JOINT_LIMITS.max[i]}
                value={targetPositions[i]}
                onChange={(e) => onSliderChange(i, parseFloat(e.target.value))}
                disabled={!isConnected}
                style={styles.slider}
              />
            </div>
          ))}
        </div>

        <div style={styles.speedControl}>
          <span>Speed: {speed}%</span>
          <input
            type="range"
            min={10}
            max={100}
            value={speed}
            onChange={(e) => onSpeedChange(parseInt(e.target.value))}
            style={styles.slider}
          />
        </div>

        <button
          onClick={onMoveToPosition}
          disabled={!isConnected}
          style={{
            ...styles.button,
            width: '100%',
            marginTop: '12px',
            opacity: isConnected ? 1 : 0.5,
          }}
        >
          Move to Position
        </button>
      </Panel>

      {/* Quick Positions */}
      <Panel title="Quick Positions">
        <div style={styles.quickButtons}>
          {[
            { name: 'Home', positions: [0, -45, 90, 0, 90, 0] },
            { name: 'Ready', positions: [0, -30, 60, 0, 60, 0] },
            { name: 'Folded', positions: [0, 0, 0, 0, 0, 0] },
          ].map((pos) => (
            <button
              key={pos.name}
              onClick={() => onQuickPosition(pos.name, pos.positions)}
              disabled={!isConnected}
              style={styles.quickButton}
            >
              {pos.name}
            </button>
          ))}
        </div>
      </Panel>

      {/* Robot State */}
      <Panel title="Robot State">
        <div style={styles.stateGrid}>
          <StateItem label="J1" value={(jointPositions[0] * 180 / Math.PI).toFixed(1)} unit="°" />
          <StateItem label="J2" value={(jointPositions[1] * 180 / Math.PI).toFixed(1)} unit="°" />
          <StateItem label="J3" value={(jointPositions[2] * 180 / Math.PI).toFixed(1)} unit="°" />
          <StateItem label="J4" value={(jointPositions[3] * 180 / Math.PI).toFixed(1)} unit="°" />
          <StateItem label="J5" value={(jointPositions[4] * 180 / Math.PI).toFixed(1)} unit="°" />
          <StateItem label="J6" value={(jointPositions[5] * 180 / Math.PI).toFixed(1)} unit="°" />
        </div>
        <div style={styles.stateGrid}>
          <StateItem label="X" value={endEffectorPosition[0].toFixed(3)} unit="m" />
          <StateItem label="Y" value={endEffectorPosition[1].toFixed(3)} unit="m" />
          <StateItem label="Z" value={endEffectorPosition[2].toFixed(3)} unit="m" />
        </div>
      </Panel>
    </div>
  )
}

interface ConfigTabProps {
  config: any
  robotIp: string
  onRobotIpChange: (ip: string) => void
  onUpdateConfig: (updates: any) => void
}

function ConfigTab({ config, robotIp, onRobotIpChange, onUpdateConfig }: ConfigTabProps) {
  const [localConfig, setLocalConfig] = useState(config)

  useEffect(() => {
    setLocalConfig(config)
  }, [config])

  if (!localConfig) return <div style={styles.scrollContent}>Loading...</div>

  return (
    <div style={styles.scrollContent}>
      {/* Robot Settings */}
      <Panel title="Robot Settings">
        <div style={styles.formGroup}>
          <label style={styles.label}>Robot IP</label>
          <input
            type="text"
            value={robotIp}
            onChange={(e) => onRobotIpChange(e.target.value)}
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Robot Port</label>
          <input
            type="number"
            value={localConfig.robot?.robot_port || 8080}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                robot: { ...localConfig.robot, robot_port: parseInt(e.target.value) },
              })
            }
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={localConfig.robot?.simulation ?? true}
              onChange={(e) =>
                setLocalConfig({
                  ...localConfig,
                  robot: { ...localConfig.robot, simulation: e.target.checked },
                })
              }
            />
            <span>Simulation Mode</span>
          </label>
        </div>
      </Panel>

      {/* Motion Settings */}
      <Panel title="Motion Settings">
        <div style={styles.formGroup}>
          <label style={styles.label}>Default Speed ({((localConfig.motion?.default_speed || 0.5) * 100).toFixed(0)}%)</label>
          <input
            type="range"
            min={0.1}
            max={1.0}
            step={0.1}
            value={localConfig.motion?.default_speed || 0.5}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                motion: { ...localConfig.motion, default_speed: parseFloat(e.target.value) },
              })
            }
            style={styles.slider}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Default Acceleration ({((localConfig.motion?.default_acceleration || 0.5) * 100).toFixed(0)}%)</label>
          <input
            type="range"
            min={0.1}
            max={1.0}
            step={0.1}
            value={localConfig.motion?.default_acceleration || 0.5}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                motion: { ...localConfig.motion, default_acceleration: parseFloat(e.target.value) },
              })
            }
            style={styles.slider}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={localConfig.motion?.collision_detection ?? true}
              onChange={(e) =>
                setLocalConfig({
                  ...localConfig,
                  motion: { ...localConfig.motion, collision_detection: e.target.checked },
                })
              }
            />
            <span>Collision Detection</span>
          </label>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Collision Threshold (m)</label>
          <input
            type="number"
            step={0.01}
            value={localConfig.motion?.collision_threshold || 0.05}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                motion: { ...localConfig.motion, collision_threshold: parseFloat(e.target.value) },
              })
            }
            style={styles.input}
          />
        </div>
      </Panel>

      {/* Simulator Settings */}
      <Panel title="Simulator Settings">
        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={localConfig.simulator?.gui_enabled ?? true}
              onChange={(e) =>
                setLocalConfig({
                  ...localConfig,
                  simulator: { ...localConfig.simulator, gui_enabled: e.target.checked },
                })
              }
            />
            <span>Enable GUI</span>
          </label>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Gravity (m/s²)</label>
          <input
            type="number"
            step={0.1}
            value={localConfig.simulator?.gravity || -9.81}
            onChange={(e) =>
              setLocalConfig({
                ...localConfig,
                simulator: { ...localConfig.simulator, gravity: parseFloat(e.target.value) },
              })
            }
            style={styles.input}
          />
        </div>
      </Panel>

      {/* Save Button */}
      <button
        onClick={async () => {
          await onUpdateConfig(localConfig)
        }}
        style={styles.saveButton}
      >
        Save Configuration
      </button>
    </div>
  )
}

interface ConsoleTabProps {
  logs: string[]
}

function ConsoleTab({ logs }: ConsoleTabProps) {
  return (
    <div style={styles.consoleContainer}>
      <div style={styles.console}>
        {logs.map((log, i) => (
          <div key={i} style={styles.logLine}>
            {log}
          </div>
        ))}
        {logs.length === 0 && (
          <div style={styles.logLine}>Console ready...</div>
        )}
      </div>
    </div>
  )
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={styles.panel}>
      <div style={styles.panelTitle}>{title}</div>
      <div style={styles.panelContent}>{children}</div>
    </div>
  )
}

function StateItem({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div style={styles.stateItem}>
      <span style={styles.stateLabel}>{label}</span>
      <span style={styles.stateValue}>
        {value}
        <span style={styles.stateUnit}>{unit}</span>
      </span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  tabBar: {
    display: 'flex',
    background: '#0f0f23',
    borderBottom: '1px solid #1e3a5f',
  },
  tab: {
    flex: 1,
    padding: '12px',
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: '#888',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  tabActive: {
    color: '#60a5fa',
    borderBottomColor: '#60a5fa',
  },
  content: {
    flex: 1,
    overflow: 'hidden',
  },
  scrollContent: {
    padding: '12px',
    overflow: 'auto',
    height: '100%',
  },
  panel: {
    background: '#0f0f23',
    borderRadius: '8px',
    border: '1px solid #1e3a5f',
    marginBottom: '12px',
  },
  panelTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#60a5fa',
    padding: '10px 12px',
    borderBottom: '1px solid #1e3a5f',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  panelContent: {
    padding: '12px',
  },
  connectionRow: {
    display: 'flex',
    gap: '8px',
  },
  input: {
    flex: 1,
    padding: '8px 12px',
    background: '#16213e',
    border: '1px solid #1e3a5f',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '13px',
  },
  testButton: {
    padding: '8px 16px',
    background: '#4a5568',
    border: 'none',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
  },
  testResult: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '8px',
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid',
    fontSize: '12px',
  },
  testIcon: {
    fontWeight: 'bold',
  },
  connectionButtons: {
    display: 'flex',
    gap: '8px',
    marginTop: '12px',
  },
  button: {
    padding: '10px 16px',
    background: '#3182ce',
    border: 'none',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: 500,
  },
  statusRow: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '8px',
    fontSize: '12px',
  },
  statusLabel: {
    color: '#888',
  },
  statusValue: {
    fontWeight: 500,
  },
  jointGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
  },
  jointControl: {
    background: '#16213e',
    padding: '8px',
    borderRadius: '4px',
  },
  jointHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '4px',
  },
  jointName: {
    fontSize: '12px',
    color: '#888',
  },
  jointValue: {
    fontSize: '12px',
    color: '#facc15',
    fontFamily: 'monospace',
  },
  slider: {
    width: '100%',
    height: '6px',
    appearance: 'none',
    background: '#1e3a5f',
    borderRadius: '3px',
    cursor: 'pointer',
  },
  speedControl: {
    marginTop: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    fontSize: '12px',
    color: '#888',
  },
  quickButtons: {
    display: 'flex',
    gap: '8px',
  },
  quickButton: {
    flex: 1,
    padding: '8px',
    background: '#16213e',
    border: '1px solid #1e3a5f',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '12px',
    cursor: 'pointer',
  },
  stateGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '8px',
    marginBottom: '8px',
  },
  stateItem: {
    background: '#16213e',
    padding: '8px',
    borderRadius: '4px',
    textAlign: 'center',
  },
  stateLabel: {
    display: 'block',
    fontSize: '11px',
    color: '#888',
    marginBottom: '2px',
  },
  stateValue: {
    fontSize: '14px',
    color: '#fff',
    fontFamily: 'monospace',
  },
  stateUnit: {
    fontSize: '10px',
    color: '#888',
    marginLeft: '2px',
  },
  formGroup: {
    marginBottom: '12px',
  },
  label: {
    display: 'block',
    fontSize: '12px',
    color: '#888',
    marginBottom: '4px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    color: '#fff',
    cursor: 'pointer',
  },
  saveButton: {
    width: '100%',
    padding: '12px',
    background: '#38a169',
    border: 'none',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    marginTop: '8px',
  },
  consoleContainer: {
    height: '100%',
    padding: '12px',
  },
  console: {
    background: '#0a0a15',
    padding: '12px',
    borderRadius: '4px',
    height: '100%',
    overflow: 'auto',
    fontFamily: 'monospace',
    fontSize: '12px',
  },
  logLine: {
    color: '#4ade80',
    marginBottom: '4px',
  },
}
