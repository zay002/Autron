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
    jogStart,
    jogStop,
    loadConfig,
    updateConfig,
  } = useRobotStore()

  const [activeTab, setActiveTab] = useState<TabType>('control')
  const [targetPositions, setTargetPositions] = useState<number[]>([0, -45, 90, 0, 90, 0])
  const [speed, setSpeed] = useState(50)
  const [logs, setLogs] = useState<string[]>([])
  const [robotIp, setRobotIp] = useState('192.168.1.100')
  const [cameraIp, setCameraIp] = useState('192.168.1.101')

  // Load config on mount
  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  // Update IPs from config
  useEffect(() => {
    if (config?.robot?.robot_ip) {
      setRobotIp(config.robot.robot_ip)
    }
    if (config?.camera?.camera_ip) {
      setCameraIp(config.camera.camera_ip)
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

  const handleJogStart = async (axis: string, direction: number) => {
    await jogStart(axis, direction)
  }

  const handleJogStop = async () => {
    await jogStop()
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
            targetPositions={targetPositions}
            speed={speed}
            jointPositions={jointPositions}
            endEffectorPosition={endEffectorPosition}
            isConnected={isConnected}
            onMoveToPosition={handleMoveToPosition}
            onSliderChange={handleSliderChange}
            onSpeedChange={setSpeed}
            onQuickPosition={(name, positions) => {
              setTargetPositions(positions)
              addLog(`Selected ${name} position`)
            }}
            onJogStart={(axis, direction) => {
              handleJogStart(axis, direction)
              addLog(`Jog ${axis}${direction > 0 ? '+' : '-'}`)
            }}
            onJogStop={() => handleJogStop()}
          />
        )}

        {activeTab === 'config' && (
          <ConfigTab
            config={config}
            robotIp={robotIp}
            cameraIp={cameraIp}
            onRobotIpChange={setRobotIp}
            onCameraIpChange={setCameraIp}
            onUpdateConfig={updateConfig}
            connectionState={connectionState}
            connectionTestResult={connectionTestResult}
            onConnect={handleConnect}
            onTestConnection={handleTestConnection}
            onSave={() => {
              updateConfig({
                robot: { ...config?.robot, robot_ip: robotIp },
                camera: { ...config?.camera, camera_ip: cameraIp },
              })
              addLog('Configuration saved')
            }}
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
  targetPositions: number[]
  speed: number
  jointPositions: number[]
  endEffectorPosition: number[]
  isConnected: boolean
  onMoveToPosition: () => void
  onSliderChange: (index: number, value: number) => void
  onSpeedChange: (speed: number) => void
  onQuickPosition: (name: string, positions: number[]) => void
  onJogStart: (axis: string, direction: number) => void
  onJogStop: () => void
}

function ControlTab({
  targetPositions,
  speed,
  jointPositions,
  endEffectorPosition,
  isConnected,
  onMoveToPosition,
  onSliderChange,
  onSpeedChange,
  onQuickPosition,
  onJogStart,
  onJogStop,
}: ControlTabProps) {
  return (
    <div style={styles.scrollContent}>
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

      {/* Cartesian Jog */}
      <Panel title="Cartesian Jog">
        <div style={styles.jogPanel}>
          {[
            { axis: 'x', label: 'X', unit: 'm' },
            { axis: 'y', label: 'Y', unit: 'm' },
            { axis: 'z', label: 'Z', unit: 'm' },
            { axis: 'rx', label: 'RX', unit: 'rad' },
            { axis: 'ry', label: 'RY', unit: 'rad' },
            { axis: 'rz', label: 'RZ', unit: 'rad' },
          ].map(({ axis, label, unit }) => (
            <div key={axis} style={styles.jogRow}>
              <span style={styles.jogLabel}>{label}</span>
              <button
                onMouseDown={() => onJogStart(axis, -1)}
                onMouseUp={onJogStop}
                onMouseLeave={onJogStop}
                disabled={!isConnected}
                style={styles.jogButton}
              >
                -
              </button>
              <span style={styles.jogUnit}>{unit}</span>
              <button
                onMouseDown={() => onJogStart(axis, 1)}
                onMouseUp={onJogStop}
                onMouseLeave={onJogStop}
                disabled={!isConnected}
                style={styles.jogButton}
              >
                +
              </button>
            </div>
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
  cameraIp: string
  onRobotIpChange: (ip: string) => void
  onCameraIpChange: (ip: string) => void
  onUpdateConfig: (updates: any) => void
  connectionState: string
  connectionTestResult: { reachable: boolean; message: string } | null
  onConnect: () => void
  onTestConnection: () => void
  onSave: () => void
}

function ConfigTab({
  config,
  robotIp,
  cameraIp,
  onRobotIpChange,
  onCameraIpChange,
  onUpdateConfig,
  connectionState,
  connectionTestResult,
  onConnect,
  onTestConnection,
  onSave,
}: ConfigTabProps) {
  const isConnected = connectionState === 'connected'

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
            value={config?.robot?.robot_port || 8080}
            onChange={(e) =>
              onUpdateConfig({
                robot: { ...config?.robot, robot_port: parseInt(e.target.value) },
              })
            }
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={config?.robot?.simulation ?? true}
              onChange={(e) =>
                onUpdateConfig({
                  robot: { ...config?.robot, simulation: e.target.checked },
                })
              }
            />
            <span>Simulation Mode</span>
          </label>
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Timeout (s)</label>
          <input
            type="number"
            value={config?.robot?.connection_timeout || 10}
            onChange={(e) =>
              onUpdateConfig({
                robot: { ...config?.robot, connection_timeout: parseInt(e.target.value) },
              })
            }
            style={styles.input}
          />
        </div>

        {/* Connection Test */}
        <div style={styles.connectionTest}>
          <button
            onClick={onTestConnection}
            disabled={isConnected}
            style={styles.testButton}
          >
            Test Connection
          </button>
          {connectionTestResult && (
            <div
              style={{
                ...styles.testResult,
                background: connectionTestResult.reachable ? '#e8f5e9' : '#ffebee',
                borderColor: connectionTestResult.reachable ? '#4caf50' : '#f44336',
                color: connectionTestResult.reachable ? '#2e7d32' : '#d32f2f',
              }}
            >
              {connectionTestResult.reachable ? '✓' : '✗'} {connectionTestResult.message}
            </div>
          )}
        </div>

        {/* Connect Button */}
        <button
          onClick={onConnect}
          style={{
            ...styles.button,
            width: '100%',
            marginTop: '12px',
            background: isConnected ? '#f44336' : '#4caf50',
          }}
        >
          {isConnected ? 'Disconnect' : 'Connect'}
        </button>

        <div style={styles.statusRow}>
          <span style={styles.statusLabel}>Status:</span>
          <span
            style={{
              ...styles.statusValue,
              color: isConnected ? '#4caf50' : '#f44336',
            }}
          >
            {connectionState}
          </span>
        </div>
      </Panel>

      {/* Camera Settings */}
      <Panel title="Camera Settings">
        <div style={styles.formGroup}>
          <label style={styles.label}>Camera IP</label>
          <input
            type="text"
            value={cameraIp}
            onChange={(e) => onCameraIpChange(e.target.value)}
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>Camera Port</label>
          <input
            type="number"
            value={config?.camera?.camera_port || 8081}
            onChange={(e) =>
              onUpdateConfig({
                camera: { ...config?.camera, camera_port: parseInt(e.target.value) },
              })
            }
            style={styles.input}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={config?.camera?.use_mock ?? true}
              onChange={(e) =>
              onUpdateConfig({
                camera: { ...config?.camera, use_mock: e.target.checked },
              })
              }
            />
            <span>Use Mock Camera</span>
          </label>
        </div>
      </Panel>

      {/* Motion Settings */}
      <Panel title="Motion Settings">
        <div style={styles.formGroup}>
          <label style={styles.label}>Default Speed ({((config?.motion?.default_speed || 0.5) * 100).toFixed(0)}%)</label>
          <input
            type="range"
            min={0.1}
            max={1.0}
            step={0.1}
            value={config?.motion?.default_speed || 0.5}
            onChange={(e) =>
              onUpdateConfig({
                motion: { ...config?.motion, default_speed: parseFloat(e.target.value) },
              })
            }
            style={styles.slider}
          />
        </div>

        <div style={styles.formGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={config?.motion?.collision_detection ?? true}
              onChange={(e) =>
                onUpdateConfig({
                  motion: { ...config?.motion, collision_detection: e.target.checked },
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
            value={config?.motion?.collision_threshold || 0.05}
            onChange={(e) =>
              onUpdateConfig({
                motion: { ...config?.motion, collision_threshold: parseFloat(e.target.value) },
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
              checked={config?.simulator?.gui_enabled ?? true}
              onChange={(e) =>
                onUpdateConfig({
                  simulator: { ...config?.simulator, gui_enabled: e.target.checked },
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
            value={config?.simulator?.gravity || -9.81}
            onChange={(e) =>
              onUpdateConfig({
                simulator: { ...config?.simulator, gravity: parseFloat(e.target.value) },
              })
            }
            style={styles.input}
          />
        </div>
      </Panel>

      {/* Save Button */}
      <button onClick={onSave} style={styles.saveButton}>
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
    background: '#fafafa',
    borderBottom: '2px solid #e0e0e0',
  },
  tab: {
    flex: 1,
    padding: '12px',
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: '#666',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  tabActive: {
    color: '#ff6d00',
    borderBottomColor: '#ff6d00',
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
    background: '#fff',
    borderRadius: '8px',
    border: '1px solid #e0e0e0',
    marginBottom: '12px',
  },
  panelTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#ff6d00',
    padding: '10px 12px',
    borderBottom: '1px solid #e0e0e0',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  panelContent: {
    padding: '12px',
  },
  input: {
    flex: 1,
    padding: '8px 12px',
    background: '#fafafa',
    border: '1px solid #e0e0e0',
    borderRadius: '4px',
    color: '#333',
    fontSize: '13px',
  },
  testButton: {
    padding: '8px 16px',
    background: '#666',
    border: 'none',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
  },
  testResult: {
    marginTop: '8px',
    padding: '8px 12px',
    borderRadius: '4px',
    border: '1px solid',
    fontSize: '12px',
  },
  button: {
    padding: '10px 16px',
    background: '#ff6d00',
    border: 'none',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: 500,
  },
  connectionTest: {
    marginTop: '12px',
  },
  statusRow: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '8px',
    fontSize: '12px',
  },
  statusLabel: {
    color: '#666',
  },
  statusValue: {
    fontWeight: 500,
    color: '#333',
  },
  jointGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
  },
  jointControl: {
    background: '#fafafa',
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #e0e0e0',
  },
  jointHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '4px',
  },
  jointName: {
    fontSize: '12px',
    color: '#666',
  },
  jointValue: {
    fontSize: '12px',
    color: '#ff6d00',
    fontFamily: 'monospace',
  },
  slider: {
    width: '100%',
    height: '6px',
    appearance: 'none',
    background: '#e0e0e0',
    borderRadius: '3px',
    cursor: 'pointer',
  },
  speedControl: {
    marginTop: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    fontSize: '12px',
    color: '#666',
  },
  quickButtons: {
    display: 'flex',
    gap: '8px',
  },
  quickButton: {
    flex: 1,
    padding: '8px',
    background: '#fafafa',
    border: '1px solid #e0e0e0',
    borderRadius: '4px',
    color: '#333',
    fontSize: '12px',
    cursor: 'pointer',
  },
  jogPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  jogRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  jogLabel: {
    width: '32px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#ff6d00',
  },
  jogButton: {
    width: '36px',
    height: '28px',
    background: '#fafafa',
    border: '1px solid #e0e0e0',
    borderRadius: '4px',
    color: '#333',
    fontSize: '14px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  jogUnit: {
    width: '36px',
    fontSize: '10px',
    color: '#888',
    textAlign: 'center',
  },
  stateGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '8px',
    marginBottom: '8px',
  },
  stateItem: {
    background: '#fafafa',
    padding: '8px',
    borderRadius: '4px',
    textAlign: 'center',
    border: '1px solid #e0e0e0',
  },
  stateLabel: {
    display: 'block',
    fontSize: '11px',
    color: '#888',
    marginBottom: '2px',
  },
  stateValue: {
    fontSize: '14px',
    color: '#333',
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
    color: '#666',
    marginBottom: '4px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    color: '#333',
    cursor: 'pointer',
  },
  saveButton: {
    width: '100%',
    padding: '12px',
    background: '#ff6d00',
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
    background: '#fafafa',
    padding: '12px',
    borderRadius: '4px',
    border: '1px solid #e0e0e0',
    height: '100%',
    overflow: 'auto',
    fontFamily: 'monospace',
    fontSize: '12px',
  },
  logLine: {
    color: '#333',
    marginBottom: '4px',
  },
}
