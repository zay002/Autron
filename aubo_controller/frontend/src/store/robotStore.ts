import { create } from 'zustand'

interface RobotConfig {
  robot_ip: string
  robot_port: number
  simulation: boolean
  connection_timeout: number
  heartbeat_interval: number
}

interface MotionConfig {
  default_speed: number
  default_acceleration: number
  joint_velocity_limit: number
  joint_acceleration_limit: number
  cartesian_velocity_limit: number
  collision_detection: boolean
  collision_threshold: number
}

interface SimulatorConfig {
  gui_enabled: boolean
  viewport_width: number
  viewport_height: number
  timestep: number
  gravity: number
  solver_iterations: number
}

interface AppConfig {
  robot: RobotConfig
  motion: MotionConfig
  simulator: SimulatorConfig
}

interface RobotState {
  // Connection
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'running' | 'error'
  robotMode: 'teach' | 'playback' | 'auto' | 'remote'
  simulation: boolean

  // Joint state
  jointPositions: number[]
  jointVelocities: number[]

  // End effector
  endEffectorPosition: number[]
  endEffectorOrientation: number[]

  // Config
  config: AppConfig

  // Connection test
  connectionTestResult: {
    reachable: boolean
    message: string
  } | null

  // Actions
  connect: (robotIp: string, simulation: boolean) => Promise<void>
  disconnect: () => Promise<void>
  testConnection: (robotIp: string, timeout?: number) => Promise<void>
  moveJoints: (positions: number[], speed?: number) => Promise<void>
  moveCartesian: (position: number[], orientation: number[]) => Promise<void>
  getState: () => Promise<void>
  setJointPositions: (positions: number[]) => void
  loadConfig: () => Promise<void>
  updateConfig: (updates: Partial<AppConfig>) => Promise<void>
}

const DEFAULT_JOINT_POSITIONS = [0, -0.785, 1.571, 0, 1.571, 0]

export const useRobotStore = create<RobotState>((set, get) => ({
  connectionState: 'disconnected',
  robotMode: 'teach',
  simulation: true,
  jointPositions: DEFAULT_JOINT_POSITIONS,
  jointVelocities: [0, 0, 0, 0, 0, 0],
  endEffectorPosition: [0, 0, 0],
  endEffectorOrientation: [1, 0, 0, 0],
  connectionTestResult: null,
  config: {
    robot: {
      robot_ip: '192.168.1.100',
      robot_port: 8080,
      simulation: true,
      connection_timeout: 10,
      heartbeat_interval: 1,
    },
    motion: {
      default_speed: 0.5,
      default_acceleration: 0.5,
      joint_velocity_limit: 1.0,
      joint_acceleration_limit: 1.0,
      cartesian_velocity_limit: 0.5,
      collision_detection: true,
      collision_threshold: 0.05,
    },
    simulator: {
      gui_enabled: true,
      viewport_width: 1920,
      viewport_height: 1080,
      timestep: 0.002,
      gravity: -9.81,
      solver_iterations: 100,
    },
  },

  connect: async (robotIp: string, simulation: boolean) => {
    set({ connectionState: 'connecting' })

    const state = useRobotStore.getState()
    const port = state.config?.robot?.robot_port || 8080

    try {
      const response = await fetch('/api/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          robot_ip: robotIp,
          robot_port: port,
          simulation,
        }),
      })

      const data = await response.json()

      if (data.success) {
        set({
          connectionState: 'connected',
          simulation,
        })
      } else {
        set({ connectionState: 'error' })
      }
    } catch (error) {
      console.error('Connection failed:', error)
      set({ connectionState: 'error' })
    }
  },

  disconnect: async () => {
    try {
      await fetch('/api/disconnect', { method: 'POST' })
    } catch (error) {
      console.error('Disconnect failed:', error)
    }
    set({ connectionState: 'disconnected' })
  },

  testConnection: async (robotIp: string, timeout: number = 5) => {
    set({ connectionTestResult: { reachable: false, message: 'Testing...' } })

    const state = useRobotStore.getState()
    const port = state.config?.robot?.robot_port || 8080

    try {
      const response = await fetch('/api/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          robot_ip: robotIp,
          robot_port: port,
          timeout,
        }),
      })

      const data = await response.json()
      set({ connectionTestResult: data })
    } catch (error) {
      set({
        connectionTestResult: {
          reachable: false,
          message: `Test failed: ${error}`,
        },
      })
    }
  },

  moveJoints: async (positions: number[], speed: number = 0.5) => {
    const { connectionState } = get()
    if (connectionState !== 'connected') return

    try {
      await fetch('/api/move/joints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          positions,
          speed,
          acceleration: 0.5,
          blocking: true,
        }),
      })

      // Update local state immediately for responsiveness
      set({ jointPositions: positions })
    } catch (error) {
      console.error('Move joints failed:', error)
    }
  },

  moveCartesian: async (position: number[], orientation: number[]) => {
    const { connectionState } = get()
    if (connectionState !== 'connected') return

    try {
      await fetch('/api/move/cartesian', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          position,
          orientation,
          speed: 0.5,
          acceleration: 0.5,
          blocking: true,
        }),
      })
    } catch (error) {
      console.error('Move cartesian failed:', error)
    }
  },

  getState: async () => {
    try {
      const response = await fetch('/api/state')
      if (response.ok) {
        const data = await response.json()
        set({
          jointPositions: data.joint_positions || DEFAULT_JOINT_POSITIONS,
          jointVelocities: data.joint_velocities || [0, 0, 0, 0, 0, 0],
          endEffectorPosition: data.end_effector_position || [0, 0, 0],
          endEffectorOrientation: data.end_effector_orientation || [1, 0, 0, 0],
          connectionState: data.connection_state || 'disconnected',
          robotMode: data.robot_mode || 'teach',
        })
      }
    } catch (error) {
      // Silently fail - backend might not be running
    }
  },

  setJointPositions: (positions: number[]) => {
    set({ jointPositions: positions })
  },

  loadConfig: async () => {
    try {
      const response = await fetch('/api/config')
      if (response.ok) {
        const data = await response.json()
        set({ config: data })
      }
    } catch (error) {
      console.error('Failed to load config:', error)
    }
  },

  updateConfig: async (updates: Partial<AppConfig>) => {
    try {
      // Flatten the nested config structure to match backend's ConfigUpdateRequest
      const flatUpdates: Record<string, any> = {}

      if (updates.robot) {
        if (updates.robot.robot_ip !== undefined) flatUpdates.robot_ip = updates.robot.robot_ip
        if (updates.robot.robot_port !== undefined) flatUpdates.robot_port = updates.robot.robot_port
        if (updates.robot.simulation !== undefined) flatUpdates.simulation = updates.robot.simulation
        if (updates.robot.connection_timeout !== undefined) flatUpdates.connection_timeout = updates.robot.connection_timeout
        if (updates.robot.heartbeat_interval !== undefined) flatUpdates.heartbeat_interval = updates.robot.heartbeat_interval
      }

      if (updates.motion) {
        if (updates.motion.default_speed !== undefined) flatUpdates.default_speed = updates.motion.default_speed
        if (updates.motion.default_acceleration !== undefined) flatUpdates.default_acceleration = updates.motion.default_acceleration
        if (updates.motion.joint_velocity_limit !== undefined) flatUpdates.joint_velocity_limit = updates.motion.joint_velocity_limit
        if (updates.motion.joint_acceleration_limit !== undefined) flatUpdates.joint_acceleration_limit = updates.motion.joint_acceleration_limit
        if (updates.motion.cartesian_velocity_limit !== undefined) flatUpdates.cartesian_velocity_limit = updates.motion.cartesian_velocity_limit
        if (updates.motion.collision_detection !== undefined) flatUpdates.collision_detection = updates.motion.collision_detection
        if (updates.motion.collision_threshold !== undefined) flatUpdates.collision_threshold = updates.motion.collision_threshold
      }

      if (updates.simulator) {
        if (updates.simulator.gui_enabled !== undefined) flatUpdates.gui_enabled = updates.simulator.gui_enabled
        if (updates.simulator.timestep !== undefined) flatUpdates.timestep = updates.simulator.timestep
        if (updates.simulator.gravity !== undefined) flatUpdates.gravity = updates.simulator.gravity
        if (updates.simulator.solver_iterations !== undefined) flatUpdates.solver_iterations = updates.simulator.solver_iterations
      }

      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(flatUpdates),
      })
      // Reload config after update
      await get().loadConfig()
    } catch (error) {
      console.error('Failed to update config:', error)
    }
  },
}))
