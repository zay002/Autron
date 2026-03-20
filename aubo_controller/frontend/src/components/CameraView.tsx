import { useState, useEffect, useRef } from 'react'

interface CameraStatus {
  connected: boolean
  state: string
  is_mock: boolean
  error_message: string | null
  camera_info: {
    name: string
    serial: string
    resolution: string
    firmware_version: string
  } | null
  last_frame_timestamp: number | null
}

export function CameraView() {
  const [status, setStatus] = useState<CameraStatus | null>(null)
  const [frameUrl, setFrameUrl] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<string>('Never')
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<number | null>(null)

  const fetchStatus = async () => {
    try {
      const response = await fetch('/api/camera/status')
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
        setError(null)
      }
    } catch (err) {
      setError('Failed to fetch camera status')
    }
  }

  const connect = async () => {
    try {
      const response = await fetch('/api/camera/connect', { method: 'POST' })
      const data = await response.json()
      if (data.success) {
        setStatus(data)
        startPolling()
      } else {
        setError(data.message || 'Connection failed')
      }
    } catch (err) {
      setError('Failed to connect to camera')
    }
  }

  const disconnect = async () => {
    try {
      await fetch('/api/camera/disconnect', { method: 'POST' })
      stopPolling()
      setFrameUrl(null)
      fetchStatus()
    } catch (err) {
      setError('Failed to disconnect from camera')
    }
  }

  const fetchFrame = async () => {
    try {
      const response = await fetch('/api/camera/frame')
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.frame) {
          setFrameUrl(`data:image/jpeg;base64,${data.frame}`)
          setLastUpdate(new Date(data.timestamp * 1000).toLocaleTimeString())
        }
        if (data.is_mock) {
          setStatus(prev => prev ? { ...prev, is_mock: true } : null)
        }
      }
    } catch (err) {
      // Silently fail frame fetch
    }
  }

  const startPolling = () => {
    if (pollingRef.current) return
    pollingRef.current = window.setInterval(() => {
      fetchFrame()
    }, 100) // 10 FPS
  }

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  useEffect(() => {
    fetchStatus()
    return () => stopPolling()
  }, [])

  const isConnected = status?.connected || false
  const isMock = status?.is_mock || false

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Camera</span>
        <div style={styles.headerRight}>
          {isMock && <span style={styles.mockBadge}>Mock</span>}
          <span style={{
            ...styles.statusDot,
            backgroundColor: isConnected ? '#4ade80' : '#666',
            boxShadow: isConnected ? '0 0 8px #4ade80' : 'none',
          }} />
        </div>
      </div>

      <div style={styles.content}>
        {!isConnected ? (
          <div style={styles.disconnected}>
            <div style={styles.icon}>📷</div>
            <div style={styles.message}>Camera Disconnected</div>
            <button onClick={connect} style={styles.connectButton}>
              Connect
            </button>
          </div>
        ) : (
          <>
            {frameUrl ? (
              <img src={frameUrl} alt="Camera Feed" style={styles.frame} />
            ) : (
              <div style={styles.loading}>
                <div style={styles.spinner} />
                <span>Loading...</span>
              </div>
            )}
          </>
        )}

        {error && (
          <div style={styles.error}>{error}</div>
        )}
      </div>

      <div style={styles.footer}>
        <div style={styles.info}>
          {status?.camera_info && (
            <>
              <span>{status.camera_info.name}</span>
              <span style={styles.separator}>|</span>
              <span>{status.camera_info.resolution}</span>
            </>
          )}
        </div>
        <div style={styles.timestamp}>
          Last update: {lastUpdate}
        </div>
        {isConnected && (
          <button onClick={disconnect} style={styles.disconnectButton}>
            Disconnect
          </button>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: '#0f0f23',
    borderRadius: '8px',
    border: '1px solid #1e3a5f',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 12px',
    borderBottom: '1px solid #1e3a5f',
    background: '#16213e',
  },
  title: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#fff',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  mockBadge: {
    fontSize: '10px',
    padding: '2px 6px',
    background: '#f59e0b',
    borderRadius: '4px',
    color: '#000',
    fontWeight: 500,
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    transition: 'all 0.3s ease',
  },
  content: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#0a0a15',
    position: 'relative',
  },
  disconnected: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    color: '#888',
  },
  icon: {
    fontSize: '48px',
    opacity: 0.5,
  },
  message: {
    fontSize: '14px',
    color: '#888',
  },
  connectButton: {
    padding: '8px 24px',
    background: '#3182ce',
    border: 'none',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
  },
  frame: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    color: '#888',
  },
  spinner: {
    width: '24px',
    height: '24px',
    border: '2px solid #1e3a5f',
    borderTopColor: '#60a5fa',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  error: {
    position: 'absolute',
    bottom: '8px',
    left: '8px',
    right: '8px',
    padding: '8px',
    background: '#4a1f1f',
    borderRadius: '4px',
    color: '#f87171',
    fontSize: '12px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    borderTop: '1px solid #1e3a5f',
    background: '#16213e',
    fontSize: '11px',
    color: '#888',
  },
  info: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  separator: {
    color: '#444',
  },
  timestamp: {
    color: '#666',
  },
  disconnectButton: {
    padding: '4px 12px',
    background: '#dc2626',
    border: 'none',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '11px',
    cursor: 'pointer',
  },
}
