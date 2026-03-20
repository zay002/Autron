"""
Configuration Management for Aubo Robot Controller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import json
import os


@dataclass
class RobotConfig:
    """Robot connection configuration."""
    robot_ip: str = "192.168.1.100"
    robot_port: int = 8080
    simulation: bool = True
    connection_timeout: int = 10
    heartbeat_interval: int = 1


@dataclass
class CameraConfig:
    """Camera connection configuration."""
    camera_ip: str = "192.168.1.101"
    camera_port: int = 8081
    use_mock: bool = True


@dataclass
class MotionConfig:
    """Motion control configuration."""
    default_speed: float = 0.5
    default_acceleration: float = 0.5
    joint_velocity_limit: float = 1.0  # rad/s
    joint_acceleration_limit: float = 1.0  # rad/s^2
    cartesian_velocity_limit: float = 0.5  # m/s
    collision_detection: bool = True
    collision_threshold: float = 0.05  # meters


@dataclass
class SimulatorConfig:
    """Mujoco simulator configuration."""
    gui_enabled: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    timestep: float = 0.002  # seconds
    gravity: float = -9.81
    solver_iterations: int = 100
    model_path: Optional[str] = None  # Path to URDF/XML model, None for default


@dataclass
class AppConfig:
    """Application-wide configuration."""
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list = field(default_factory=lambda: ["*"])
    log_level: str = "INFO"
    robot: RobotConfig = field(default_factory=RobotConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    simulator: SimulatorConfig = field(default_factory=SimulatorConfig)


# Global configuration instance
_config: Optional[AppConfig] = None
_config_path = os.path.join(os.path.dirname(__file__), "config.json")


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config() -> AppConfig:
    """Load configuration from file or return defaults."""
    global _config
    if os.path.exists(_config_path):
        try:
            with open(_config_path, "r") as f:
                data = json.load(f)
            _config = AppConfig(
                api_host=data.get("api_host", "0.0.0.0"),
                api_port=data.get("api_port", 8000),
                log_level=data.get("log_level", "INFO"),
                robot=RobotConfig(**data.get("robot", {})),
                camera=CameraConfig(**data.get("camera", {})),
                motion=MotionConfig(**data.get("motion", {})),
                simulator=SimulatorConfig(**data.get("simulator", {})),
            )
            return _config
        except Exception as e:
            print(f"Failed to load config: {e}")

    _config = AppConfig()
    return _config


def save_config(config: AppConfig) -> bool:
    """Save configuration to file."""
    global _config
    try:
        data = {
            "api_host": config.api_host,
            "api_port": config.api_port,
            "log_level": config.log_level,
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
                "model_path": config.simulator.model_path,
            },
        }
        with open(_config_path, "w") as f:
            json.dump(data, f, indent=2)
        _config = config
        return True
    except Exception as e:
        print(f"Failed to save config: {e}")
        return False


def update_config(
    robot_ip: Optional[str] = None,
    robot_port: Optional[int] = None,
    simulation: Optional[bool] = None,
    connection_timeout: Optional[int] = None,
    heartbeat_interval: Optional[int] = None,
    camera_ip: Optional[str] = None,
    camera_port: Optional[int] = None,
    use_mock: Optional[bool] = None,
    default_speed: Optional[float] = None,
    default_acceleration: Optional[float] = None,
    joint_velocity_limit: Optional[float] = None,
    joint_acceleration_limit: Optional[float] = None,
    cartesian_velocity_limit: Optional[float] = None,
    collision_detection: Optional[bool] = None,
    collision_threshold: Optional[float] = None,
    gui_enabled: Optional[bool] = None,
    timestep: Optional[float] = None,
    gravity: Optional[float] = None,
    solver_iterations: Optional[int] = None,
    model_path: Optional[str] = None,
) -> AppConfig:
    """Update specific configuration values."""
    config = get_config()

    # Robot settings
    if robot_ip is not None:
        config.robot.robot_ip = robot_ip
    if robot_port is not None:
        config.robot.robot_port = robot_port
    if simulation is not None:
        config.robot.simulation = simulation
    if connection_timeout is not None:
        config.robot.connection_timeout = connection_timeout
    if heartbeat_interval is not None:
        config.robot.heartbeat_interval = heartbeat_interval

    # Camera settings
    if camera_ip is not None:
        config.camera.camera_ip = camera_ip
    if camera_port is not None:
        config.camera.camera_port = camera_port
    if use_mock is not None:
        config.camera.use_mock = use_mock

    # Motion settings
    if default_speed is not None:
        config.motion.default_speed = default_speed
    if default_acceleration is not None:
        config.motion.default_acceleration = default_acceleration
    if joint_velocity_limit is not None:
        config.motion.joint_velocity_limit = joint_velocity_limit
    if joint_acceleration_limit is not None:
        config.motion.joint_acceleration_limit = joint_acceleration_limit
    if cartesian_velocity_limit is not None:
        config.motion.cartesian_velocity_limit = cartesian_velocity_limit
    if collision_detection is not None:
        config.motion.collision_detection = collision_detection
    if collision_threshold is not None:
        config.motion.collision_threshold = collision_threshold

    # Simulator settings
    if gui_enabled is not None:
        config.simulator.gui_enabled = gui_enabled
    if timestep is not None:
        config.simulator.timestep = timestep
    if gravity is not None:
        config.simulator.gravity = gravity
    if solver_iterations is not None:
        config.simulator.solver_iterations = solver_iterations
    if model_path is not None:
        config.simulator.model_path = model_path

    return config
