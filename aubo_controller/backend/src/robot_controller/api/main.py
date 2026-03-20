"""
FastAPI server for Aubo Robot Controller.

Provides REST API and WebSocket endpoints for robot control.
"""

from __future__ import annotations

import asyncio
import socket
from contextlib import asynccontextmanager
from typing import List, Optional
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from robot_controller.robot_controller import (
    AuboRobotController,
    RobotConnectionState,
    RobotMode,
    JointPositions,
    CartesianPosition,
    create_controller,
)
from robot_controller.mujoco_sim.simulator import AuboSimulator, create_simulator
from robot_controller.camera_service import CameraService, create_camera_service
from robot_controller.config import (
    get_config,
    save_config,
    update_config,
    AppConfig,
    RobotConfig,
    MotionConfig,
    SimulatorConfig,
)


# Global instances
controller: Optional[AuboRobotController] = None
simulator: Optional[AuboSimulator] = None
camera_service: Optional[CameraService] = None


# Pydantic models for API


# Pydantic models for API
class JointCommand(BaseModel):
    positions: List[float]
    speed: float = 0.5
    acceleration: float = 0.5
    blocking: bool = True


class CartesianCommand(BaseModel):
    position: List[float]
    orientation: List[float]
    speed: float = 0.5
    acceleration: float = 0.5
    blocking: bool = True


class ConnectionRequest(BaseModel):
    robot_ip: str = "192.168.1.100"
    robot_port: int = 8080
    simulation: bool = True


class ConnectionTestRequest(BaseModel):
    robot_ip: str = "192.168.1.100"
    robot_port: int = 8080
    timeout: float = 5.0


class ConfigUpdateRequest(BaseModel):
    # Robot settings
    robot_ip: Optional[str] = None
    robot_port: Optional[int] = None
    simulation: Optional[bool] = None
    connection_timeout: Optional[int] = None
    heartbeat_interval: Optional[int] = None
    # Camera settings
    camera_ip: Optional[str] = None
    camera_port: Optional[int] = None
    use_mock: Optional[bool] = None
    # Motion settings
    default_speed: Optional[float] = None
    default_acceleration: Optional[float] = None
    joint_velocity_limit: Optional[float] = None
    joint_acceleration_limit: Optional[float] = None
    cartesian_velocity_limit: Optional[float] = None
    collision_detection: Optional[bool] = None
    collision_threshold: Optional[float] = None
    # Simulator settings
    gui_enabled: Optional[bool] = None
    timestep: Optional[float] = None
    gravity: Optional[float] = None
    solver_iterations: Optional[int] = None
    model_path: Optional[str] = None


class SimulatorConfigRequest(BaseModel):
    gui_enabled: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    timestep: float = 0.002
    gravity: float = -9.81
    solver_iterations: int = 100
    model_path: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global controller, simulator, camera_service

    config = get_config()
    controller = create_controller(
        robot_ip=config.robot.robot_ip,
        port=config.robot.robot_port,
        simulation=config.robot.simulation,
        collision_detection=config.motion.collision_detection,
        collision_threshold=config.motion.collision_threshold,
    )
    simulator = create_simulator(
        use_gui=config.simulator.gui_enabled,
        timestep=config.simulator.timestep,
        gravity=config.simulator.gravity,
        solver_iterations=config.simulator.solver_iterations,
    )
    simulator.reset()  # Initialize to home position
    camera_service = create_camera_service(use_mock=config.camera.use_mock)

    print("=" * 50)
    print("Aubo Controller API started")
    print(f"  Mode: {'Simulation' if config.robot.simulation else 'Real Robot'}")
    print(f"  Robot IP: {config.robot.robot_ip}:{config.robot.robot_port}")
    print(f"  Collision Detection: {config.motion.collision_detection}")
    print(f"  API Server: http://{config.api_host}:{config.api_port}")
    print("=" * 50)

    yield

    # Cleanup
    if controller:
        await controller.disconnect()
    if simulator and simulator.viewer:
        simulator.close_viewer()

    print("Aubo Controller API stopped")


app = FastAPI(
    title="Aubo Robot Controller API",
    description="REST API and WebSocket interface for Aubo i5 robot control",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# ==================== Health & Config Endpoints ====================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Aubo Robot Controller API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    config = get_config()
    return {
        "status": "healthy",
        "controller_connected": controller.connection_state == RobotConnectionState.CONNECTED if controller else False,
        "simulation_running": simulator is not None,
        "simulation_mode": config.robot.simulation,
    }


@app.get("/config")
async def get_configuration():
    """Get current configuration."""
    config = get_config()
    return {
        "robot": {
            "robot_ip": config.robot.robot_ip,
            "robot_port": config.robot.robot_port,
            "simulation": config.robot.simulation,
            "connection_timeout": config.robot.connection_timeout,
            "heartbeat_interval": config.robot.heartbeat_interval,
        },
        "camera": {
            "camera_ip": config.camera.camera_ip,
            "camera_port": config.camera.camera_port,
            "use_mock": config.camera.use_mock,
        },
        "motion": {
            "default_speed": config.motion.default_speed,
            "default_acceleration": config.motion.default_acceleration,
            "joint_velocity_limit": config.motion.joint_velocity_limit,
            "joint_acceleration_limit": config.motion.joint_acceleration_limit,
            "cartesian_velocity_limit": config.motion.cartesian_velocity_limit,
            "collision_detection": config.motion.collision_detection,
            "collision_threshold": config.motion.collision_threshold,
        },
        "simulator": {
            "gui_enabled": config.simulator.gui_enabled,
            "viewport_width": config.simulator.viewport_width,
            "viewport_height": config.simulator.viewport_height,
            "timestep": config.simulator.timestep,
            "gravity": config.simulator.gravity,
            "solver_iterations": config.simulator.solver_iterations,
        },
    }


@app.post("/config")
async def update_configuration(request: ConfigUpdateRequest):
    """Update configuration values."""
    config = update_config(
        robot_ip=request.robot_ip,
        robot_port=request.robot_port,
        simulation=request.simulation,
        connection_timeout=request.connection_timeout,
        heartbeat_interval=request.heartbeat_interval,
        camera_ip=request.camera_ip,
        camera_port=request.camera_port,
        use_mock=request.use_mock,
        default_speed=request.default_speed,
        default_acceleration=request.default_acceleration,
        joint_velocity_limit=request.joint_velocity_limit,
        joint_acceleration_limit=request.joint_acceleration_limit,
        cartesian_velocity_limit=request.cartesian_velocity_limit,
        collision_detection=request.collision_detection,
        collision_threshold=request.collision_threshold,
        gui_enabled=request.gui_enabled,
        timestep=request.timestep,
        gravity=request.gravity,
        solver_iterations=request.solver_iterations,
        model_path=request.model_path,
    )
    save_config(config)
    return {"success": True, "message": "Configuration updated"}


# ==================== Connection Endpoints ====================

@app.post("/connect")
async def connect_robot(request: ConnectionRequest):
    """Connect to robot or start simulation."""
    global controller, simulator

    controller = create_controller(
        robot_ip=request.robot_ip,
        port=request.robot_port,
        simulation=request.simulation,
    )

    success = await controller.connect()

    # If connecting to real robot (not simulation), read live state first
    # to initialize simulator and UI from actual hardware state
    initial_state = None
    if success and not request.simulation:
        try:
            state = await controller.get_state()
            initial_state = {
                "joint_positions": state.joint_positions,
                "end_effector_position": state.end_effector_position,
                "end_effector_orientation": state.end_effector_orientation,
            }
            # Sync simulator to match real robot state
            if simulator and initial_state:
                simulator.set_joint_positions(np.array(initial_state["joint_positions"]))
        except Exception as e:
            print(f"Warning: Could not read initial robot state: {e}")

    # For simulation mode, also sync simulator to home/home position
    if success and request.simulation and simulator:
        simulator.reset()

    return {
        "success": success,
        "simulation": request.simulation,
        "robot_ip": request.robot_ip,
        "robot_port": request.robot_port,
        "connection_state": controller.connection_state.value,
        "initial_state": initial_state,
    }


@app.post("/disconnect")
async def disconnect_robot():
    """Disconnect from robot."""
    if controller:
        await controller.disconnect()
        return {"success": True}
    return {"success": False, "message": "No controller connected"}


@app.post("/stop")
async def emergency_stop():
    """
    Execute emergency stop - immediately halt all motion.

    This endpoint stops all robot motion and sets the emergency stop flag.
    The robot must be re-connected after an emergency stop.
    """
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    success = await controller.emergency_stop()
    return {
        "success": success,
        "emergency_stop_active": controller._emergency_stop_active if controller else False,
    }


@app.post("/test-connection")
async def test_connection(request: ConnectionTestRequest):
    """Test connection to robot without establishing full connection."""
    result = {
        "robot_ip": request.robot_ip,
        "robot_port": request.robot_port,
        "reachable": False,
        "message": "",
    }

    # Test IP reachability first
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(request.timeout)
        sock.connect((request.robot_ip, request.robot_port))
        sock.close()
        result["reachable"] = True
        result["message"] = "Robot is reachable"
    except socket.timeout:
        result["message"] = "Connection timeout - robot not reachable"
    except OSError as e:
        if "111" in str(e) or "Connection refused" in str(e):
            result["message"] = "Connection refused - robot may be offline or port blocked"
        else:
            result["message"] = f"Network error: {str(e)}"
    except Exception as e:
        result["message"] = f"Error: {str(e)}"

    return result


# ==================== State Endpoints ====================

@app.get("/state")
async def get_state():
    """Get current robot state."""
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    state = await controller.get_state()
    return {
        "joint_positions": state.joint_positions,
        "joint_velocities": state.joint_velocities,
        "end_effector_position": state.end_effector_position,
        "end_effector_orientation": state.end_effector_orientation,
        "connection_state": state.connection_state.value,
        "robot_mode": state.robot_mode.value,
        "timestamp": state.timestamp,
    }


# ==================== Joint Control Endpoints ====================

@app.post("/move/joints")
async def move_joints(command: JointCommand):
    """Move robot to specified joint positions."""
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    success = await controller.move_joints(
        positions=command.positions,
        speed=command.speed,
        acceleration=command.acceleration,
        blocking=command.blocking,
    )

    # Also update simulator if available
    if simulator:
        simulator.set_joint_positions(command.positions)

    return {"success": success}


@app.post("/move/cartesian")
async def move_cartesian(command: CartesianCommand):
    """Move robot end effector to specified Cartesian position."""
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    success = await controller.move_cartesian(
        position=command.position,
        orientation=command.orientation,
        speed=command.speed,
        acceleration=command.acceleration,
        blocking=command.blocking,
    )

    return {"success": success}


class JogRequest(BaseModel):
    axis: str  # 'x', 'y', 'z', 'rx', 'ry', 'rz'
    direction: int  # +1 or -1
    speed: float = 0.05


@app.post("/move/jog/start")
async def jog_start(request: JogRequest):
    """Start continuous jog motion along an axis."""
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    success = await controller.jog_start(request.axis, request.direction, request.speed)
    return {"success": success}


@app.post("/move/jog/stop")
async def jog_stop():
    """Stop continuous jog motion."""
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    success = await controller.jog_stop()
    return {"success": success}


# ==================== Mode Endpoints ====================

@app.post("/mode/teach")
async def set_teach_mode():
    """Enable teach mode."""
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    success = await controller.start_teach_mode()
    return {"success": success}


@app.post("/mode/playback")
async def set_playback_mode():
    """Enable playback mode."""
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not initialized")

    success = await controller.start_playback_mode()
    return {"success": success}


# ==================== Simulator Endpoints ====================

@app.post("/simulator/init")
async def init_simulator(request: SimulatorConfigRequest):
    """Initialize or reinitialize the simulator."""
    global simulator

    config = get_config()
    config.simulator.gui_enabled = request.gui_enabled
    config.simulator.viewport_width = request.viewport_width
    config.simulator.viewport_height = request.viewport_height
    config.simulator.timestep = request.timestep
    config.simulator.gravity = request.gravity
    config.simulator.solver_iterations = request.solver_iterations
    config.simulator.model_path = request.model_path
    save_config(config)

    if simulator and simulator.viewer:
        simulator.close_viewer()

    simulator = create_simulator(
        urdf_path=request.model_path,
        use_gui=request.gui_enabled,
        timestep=request.timestep,
        gravity=request.gravity,
        solver_iterations=request.solver_iterations,
    )

    return {
        "success": True,
        "gui": request.gui_enabled,
        "timestep": request.timestep,
        "gravity": request.gravity,
        "solver_iterations": request.solver_iterations,
    }


@app.post("/simulator/reset")
async def reset_simulator():
    """Reset simulator to home position."""
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")

    simulator.reset()
    return {"success": True}


@app.get("/simulator/state")
async def get_simulator_state():
    """Get simulator observation."""
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")

    return simulator.get_observation()


@app.post("/simulator/step")
async def step_simulator():
    """Step the simulation forward."""
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")

    simulator.step()
    return {"success": True, "time": simulator.data.time}


@app.get("/simulator/render")
async def render_simulator(width: int = 640, height: int = 480):
    """
    Get a rendered image of the current simulator state.

    Returns a PNG image of the MuJoCo-rendered robot.
    """
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")

    try:
        image_bytes = simulator.render_image(width=width, height=height)
        import base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return {
            "success": True,
            "image": f"data:image/png;base64,{image_base64}",
            "width": width,
            "height": height,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Camera Endpoints ====================

@app.get("/camera/status")
async def get_camera_status():
    """Get camera status."""
    if not camera_service:
        raise HTTPException(status_code=503, detail="Camera service not initialized")

    return camera_service.get_status()


@app.post("/camera/connect")
async def connect_camera():
    """Connect to camera."""
    if not camera_service:
        raise HTTPException(status_code=503, detail="Camera service not initialized")

    result = camera_service.connect()
    return result


@app.post("/camera/disconnect")
async def disconnect_camera():
    """Disconnect from camera."""
    if not camera_service:
        raise HTTPException(status_code=503, detail="Camera service not initialized")

    result = camera_service.disconnect()
    return result


@app.get("/camera/frame")
async def get_camera_frame():
    """
    Get a single frame from the camera.

    Returns a JPEG image encoded as base64.
    If camera is not connected, returns None.
    """
    if not camera_service:
        raise HTTPException(status_code=503, detail="Camera service not initialized")

    if not camera_service.is_connected:
        return {"success": False, "message": "Camera not connected"}

    frame_data = camera_service.get_frame()
    if frame_data is None:
        return {"success": False, "message": "Failed to get frame"}

    return {
        "success": True,
        "timestamp": frame_data["timestamp"],
        "width": frame_data["width"],
        "height": frame_data["height"],
        "frame": frame_data["frame"],
        "is_mock": frame_data["is_mock"],
    }


# ==================== WebSocket Endpoint ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time state updates."""
    await manager.connect(websocket)

    try:
        while True:
            # Receive command from client
            data = await websocket.receive_json()

            command_type = data.get("type")

            if command_type == "get_state":
                if controller:
                    state = await controller.get_state()
                    await websocket.send_json({
                        "type": "state_update",
                        "data": {
                            "joint_positions": state.joint_positions,
                            "joint_velocities": state.joint_velocities,
                            "connection_state": state.connection_state.value,
                            "robot_mode": state.robot_mode.value,
                        }
                    })

            elif command_type == "move_joints":
                positions = data.get("positions", [])
                speed = data.get("speed", 0.5)
                if controller:
                    await controller.move_joints(positions, speed)
                if simulator:
                    simulator.set_joint_positions(positions)

            elif command_type == "step_simulator":
                if simulator:
                    simulator.step()
                    obs = simulator.get_observation()
                    await websocket.send_json({
                        "type": "simulator_update",
                        "data": obs,
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(app, host=config.api_host, port=config.api_port)
