import { useEffect, useState, useRef } from 'react'
import { useRobotStore } from '../store/robotStore'

interface CameraState {
  azimuth: number
  elevation: number
  distance: number
  lookat: [number, number, number]
}

export function SimulationView() {
  const { connectionState } = useRobotStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [camera, setCamera] = useState<CameraState>({
    azimuth: 45,
    elevation: -25,
    distance: 2.5,
    lookat: [0, 0, 0],
  })
  const [tcpPose, setTcpPose] = useState<{position: number[], orientation: number[]} | null>(null)
  const isDraggingRef = useRef(false)
  const lastMouseRef = useRef({ x: 0, y: 0 })
  const dragModeRef = useRef<'rotate' | 'pan' | null>(null)
  const renderSeqRef = useRef(0)  // Sequence counter for request ordering
  const tcpFetchTimeRef = useRef(0)  // Track last TCP fetch time
  const cameraRef = useRef(camera)  // Keep camera ref for interval callback

  // Fetch TCP pose from simulator state
  const fetchTcpPose = async () => {
    try {
      const response = await fetch('/api/simulator/state')
      if (response.ok) {
        const data = await response.json()
        setTcpPose({
          position: data.end_effector_position,
          orientation: data.end_effector_orientation,
        })
      }
    } catch (err) {
      // Silently fail
    }
  }

  // Draw coordinate axes overlay
  const drawAxesOverlay = (ctx: CanvasRenderingContext2D, w: number, h: number, cam: CameraState) => {
    const cx = 50
    const cy = h - 50
    const axisLen = 30

    ctx.save()
    ctx.lineWidth = 2

    // X axis (red)
    ctx.strokeStyle = '#ff4444'
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(cx + axisLen, cy)
    ctx.stroke()
    ctx.fillStyle = '#ff4444'
    ctx.fillText('X', cx + axisLen + 5, cy + 5)

    // Y axis (green)
    ctx.strokeStyle = '#44ff44'
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(cx, cy - axisLen)
    ctx.stroke()
    ctx.fillStyle = '#44ff44'
    ctx.fillText('Y', cx - 5, cy - axisLen - 5)

    // Z axis (blue)
    ctx.strokeStyle = '#4444ff'
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.lineTo(cx - axisLen * 0.7, cy + axisLen * 0.7)
    ctx.stroke()
    ctx.fillStyle = '#4444ff'
    ctx.fillText('Z', cx - axisLen * 0.7 - 15, cy + axisLen * 0.7 + 5)

    ctx.restore()

    // Draw camera info
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'
    ctx.fillRect(w - 140, 10, 130, 65)
    ctx.fillStyle = '#ffffff'
    ctx.font = '11px monospace'
    ctx.fillText(`Az: ${cam.azimuth.toFixed(0)}°`, w - 130, 28)
    ctx.fillText(`El: ${cam.elevation.toFixed(0)}°`, w - 130, 43)
    ctx.fillText(`Dist: ${cam.distance.toFixed(1)}m`, w - 130, 58)

    // Draw TCP pose if available
    if (tcpPose) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'
      ctx.fillRect(w - 140, h - 85, 130, 75)
      ctx.fillStyle = '#ff9800'
      ctx.font = '11px monospace'
      ctx.fillText('TCP Position:', w - 130, h - 68)
      ctx.fillStyle = '#ffffff'
      ctx.fillText(`X: ${tcpPose.position[0].toFixed(3)}m`, w - 130, h - 53)
      ctx.fillText(`Y: ${tcpPose.position[1].toFixed(3)}m`, w - 130, h - 38)
      ctx.fillText(`Z: ${tcpPose.position[2].toFixed(3)}m`, w - 130, h - 23)
    }
  }

  // Mouse handlers for camera control
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true
    lastMouseRef.current = { x: e.clientX, y: e.clientY }
    if (e.button === 0) {
      dragModeRef.current = 'rotate'
    } else if (e.button === 2) {
      dragModeRef.current = 'pan'
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current) return

    const dx = e.clientX - lastMouseRef.current.x
    const dy = e.clientY - lastMouseRef.current.y
    lastMouseRef.current = { x: e.clientX, y: e.clientY }

    if (dragModeRef.current === 'rotate') {
      setCamera(prev => ({
        ...prev,
        azimuth: prev.azimuth + dx * 0.5,
        elevation: Math.max(-89, Math.min(89, prev.elevation + dy * 0.5)),
      }))
    } else if (dragModeRef.current === 'pan') {
      setCamera(prev => {
        const scale = prev.distance * 0.002
        return {
          ...prev,
          lookat: [
            prev.lookat[0] - dx * scale,
            prev.lookat[1] + dy * scale,
            prev.lookat[2],
          ],
        }
      })
    }
  }

  const handleMouseUp = () => {
    isDraggingRef.current = false
    dragModeRef.current = null
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 1.1 : 0.9
    setCamera(prev => ({
      ...prev,
      distance: Math.max(0.5, Math.min(20, prev.distance * delta)),
    }))
  }

  const handleDoubleClick = () => {
    setCamera({
      azimuth: 0,
      elevation: -30,
      distance: 3,
      lookat: [0, 0, 0],
    })
  }

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
  }

  // Update camera ref when camera changes
  useEffect(() => {
    cameraRef.current = camera
  }, [camera])

  // Poll for rendered images - use ref to access latest camera
  useEffect(() => {
    const interval = window.setInterval(() => {
      const seq = ++renderSeqRef.current
      const cam = cameraRef.current
      const params = new URLSearchParams({
        width: '640',
        height: '480',
        azimuth: cam.azimuth.toString(),
        elevation: cam.elevation.toString(),
        distance: cam.distance.toString(),
        lookat_x: cam.lookat[0].toString(),
        lookat_y: cam.lookat[1].toString(),
        lookat_z: cam.lookat[2].toString(),
      })
      fetch(`/api/simulator/render?${params}`)
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          return res.json()
        })
        .then(data => {
          if (seq !== renderSeqRef.current) return
          if (!data.success) {
            // Clear canvas and show error
            const canvas = canvasRef.current
            if (canvas) {
              const ctx = canvas.getContext('2d')
              if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
            }
            setError(data.error || 'Render failed')
            setLoading(false)
            return
          }
          const canvas = canvasRef.current
          if (!canvas) return
          const ctx = canvas.getContext('2d')
          if (!ctx) return
          const base64Data = data.image.replace('data:image/raw;base64,', '')
          const binaryString = atob(base64Data)
          const bytes = new Uint8Array(binaryString.length)
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i)
          }
          let sum = 0
          for (let i = 0; i < bytes.length; i++) sum += bytes[i]
          const mean = sum / bytes.length
          if (mean < 1) {
            setError('Rendered frame is black. Check lighting or camera pose.')
            setLoading(false)
            return
          }
          const imgData = ctx.createImageData(data.width, data.height)
          const pixels = imgData.data
          for (let i = 0; i < data.width * data.height; i++) {
            pixels[i * 4] = bytes[i * 3]
            pixels[i * 4 + 1] = bytes[i * 3 + 1]
            pixels[i * 4 + 2] = bytes[i * 3 + 2]
            pixels[i * 4 + 3] = 255
          }
          ctx.putImageData(imgData, 0, 0)
          drawAxesOverlay(ctx, data.width, data.height, cam)

          // Fetch TCP pose at lower rate (every 1 second)
          const now = Date.now()
          if (now - tcpFetchTimeRef.current > 1000) {
            tcpFetchTimeRef.current = now
            fetchTcpPose()
          }

          setLoading(false)
        })
        .catch(err => {
          console.error('Render fetch error:', err)
          if (seq === renderSeqRef.current) {
            // Clear canvas on error
            const canvas = canvasRef.current
            if (canvas) {
              const ctx = canvas.getContext('2d')
              if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
            }
            setError(String(err))
            setLoading(false)
          }
        })
    }, 100)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Robot Simulation</span>
        <span style={styles.badge}>
          {connectionState === 'connected' ? 'Live' : 'Simulation'}
        </span>
      </div>
      <div
        ref={containerRef}
        style={styles.canvasContainer}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
      >
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          style={styles.canvas}
        />
        {(loading || error) && (
          <div style={styles.overlay}>
            <div style={styles.overlayContent}>
              {loading && <span style={styles.loadingText}>Rendering...</span>}
              {error && <span style={styles.errorText}>Error: {error}</span>}
              {!loading && !error && (
                <>
                  <span style={styles.placeholderIcon}>🤖</span>
                  <span style={styles.placeholderText}>Loading simulation...</span>
                </>
              )}
            </div>
          </div>
        )}
        <div style={styles.controls}>
          <span style={styles.controlHint}>Drag: Rotate</span>
          <span style={styles.controlHint}>Right-drag: Pan</span>
          <span style={styles.controlHint}>Scroll: Zoom</span>
          <span style={styles.controlHint}>Double-click: Reset</span>
        </div>
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
  canvasContainer: {
    flex: 1,
    position: 'relative',
    background: '#fafafa',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'grab',
    userSelect: 'none',
  },
  canvas: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(250, 250, 250, 0.9)',
  },
  overlayContent: {
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
  errorText: {
    fontSize: '14px',
    color: '#d32f2f',
  },
  controls: {
    position: 'absolute',
    bottom: '8px',
    left: '8px',
    background: 'rgba(0, 0, 0, 0.5)',
    padding: '4px 8px',
    borderRadius: '4px',
    display: 'flex',
    gap: '12px',
  },
  controlHint: {
    fontSize: '10px',
    color: '#fff',
  },
}
