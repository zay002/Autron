import { useEffect, useState, useRef } from 'react'
import { useRobotStore } from '../store/robotStore'

export function SimulationView() {
  const { connectionState, jointPositions } = useRobotStore()
  const [renderedImage, setRenderedImage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const intervalRef = useRef<number | null>(null)

  // Fetch rendered image from backend MuJoCo simulator
  const fetchRender = async () => {
    if (connectionState !== 'connected') return

    try {
      setLoading(true)
      const response = await fetch('/api/simulator/render?width=640&height=480')
      const data = await response.json()
      if (data.success && data.image) {
        setRenderedImage(data.image)
      }
    } catch (error) {
      console.error('Failed to fetch render:', error)
    } finally {
      setLoading(false)
    }
  }

  // Poll for rendered images when connected
  useEffect(() => {
    if (connectionState === 'connected') {
      // Initial fetch
      fetchRender()
      // Poll at ~10fps
      intervalRef.current = window.setInterval(fetchRender, 100)
    } else {
      setRenderedImage(null)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [connectionState])

  // Also refetch when joint positions change significantly
  useEffect(() => {
    if (connectionState === 'connected') {
      fetchRender()
    }
  }, [JSON.stringify(jointPositions)])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Robot Simulation</span>
        <span style={styles.badge}>
          {connectionState === 'connected' ? 'Live' : 'Disconnected'}
        </span>
      </div>
      <div style={styles.canvas}>
        {renderedImage ? (
          <img
            src={renderedImage}
            alt="Robot Simulation"
            style={styles.renderImage}
          />
        ) : (
          <div style={styles.placeholder}>
            <div style={styles.placeholderContent}>
              {loading ? (
                <span style={styles.loadingText}>Rendering...</span>
              ) : (
                <>
                  <span style={styles.placeholderIcon}>🤖</span>
                  <span style={styles.placeholderText}>
                    {connectionState === 'connected'
                      ? 'Connecting to simulator...'
                      : 'Connect to view simulation'}
                  </span>
                </>
              )}
            </div>
          </div>
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
    background: '#fff',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    background: '#f5f5f5',
    borderBottom: '1px solid #e0e0e0',
  },
  title: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#333',
  },
  badge: {
    fontSize: '11px',
    padding: '2px 8px',
    background: '#fff3e0',
    borderRadius: '4px',
    color: '#ff6d00',
    fontWeight: 500,
  },
  canvas: {
    flex: 1,
    position: 'relative',
    background: '#fafafa',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  renderImage: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  },
  placeholder: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    height: '100%',
  },
  placeholderContent: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
  },
  placeholderIcon: {
    fontSize: '48px',
  },
  placeholderText: {
    fontSize: '14px',
    color: '#888',
  },
  loadingText: {
    fontSize: '14px',
    color: '#ff6d00',
  },
}
