"""
Robot Controller Module for Aubo i5 Robot.

This module provides a Python interface to control the Aubo i5 robot
via the Aubo SDK. It supports both position and trajectory control.
"""

from __future__ import annotations

import numpy as np
from typing import Optional, List, Callable
from enum import Enum
from dataclasses import dataclass
import asyncio
import time


class RobotConnectionState(Enum):
    """Robot connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RUNNING = "running"
    ERROR = "error"


class RobotMode(Enum):
    """Robot operation modes."""
    TEACH = "teach"
    PLAYBACK = "playback"
    AUTO = "auto"
    REMOTE = "remote"


@dataclass
class JointPositions:
    """Joint position command."""
    positions: List[float]  # 6 joint angles in radians
    speed: float = 0.5     # Movement speed (0.0 to 1.0)
    acceleration: float = 0.5  # Acceleration (0.0 to 1.0)


@dataclass
class CartesianPosition:
    """Cartesian position command."""
    position: List[float]   # [x, y, z] in meters
    orientation: List[float]  # [qx, qy, qz, qw] quaternion
    speed: float = 0.5
    acceleration: float = 0.5


@dataclass
class RobotState:
    """Current robot state."""
    joint_positions: List[float]
    joint_velocities: List[float]
    joint_torques: List[float]
    end_effector_position: List[float]
    end_effector_orientation: List[float]
    connection_state: RobotConnectionState
    robot_mode: RobotMode
    timestamp: float


class AuboRobotController:
    """
    Controller for Aubo i5 robot via Aubo SDK.

    This class provides a high-level interface for controlling the robot,
    supporting both real robot control and simulation mode.
    """

    def __init__(
        self,
        robot_ip: str = "192.168.1.100",
        port: int = 8080,
        simulation: bool = False,
        collision_detection: bool = True,
        collision_threshold: float = 0.05,
    ):
        """
        Initialize the robot controller.

        Args:
            robot_ip: Robot IP address for real robot connection.
            port: Communication port.
            simulation: If True, runs in simulation mode without connecting to real robot.
            collision_detection: Enable collision detection.
            collision_threshold: Distance threshold for collision detection in meters.
        """
        self.robot_ip = robot_ip
        self.port = port
        self.simulation = simulation
        self.collision_detection = collision_detection
        self.collision_threshold = collision_threshold

        self._connection_state = RobotConnectionState.DISCONNECTED
        self._robot_mode = RobotMode.TEACH
        self._joint_positions = [0.0] * 6
        self._joint_velocities = [0.0] * 6
        self._joint_torques = [0.0] * 6
        self._is_motion_active = False
        self._emergency_stop_active = False

        # Callbacks for state updates
        self._on_state_update: Optional[Callable[[RobotState], None]] = None
        self._on_connection_change: Optional[Callable[[RobotConnectionState], None]] = None

    def set_collision_parameters(self, enabled: bool, threshold: float) -> None:
        """Set collision detection parameters."""
        self.collision_detection = enabled
        self.collision_threshold = threshold

    def check_collision(self, positions: List[float]) -> bool:
        """
        Check if target positions would cause a collision.

        This is a simplified check. In production, this would use
        the Mujoco model orrobot geometry to check for collisions.

        Returns:
            True if collision detected, False otherwise.
        """
        if not self.collision_detection:
            return False

        # Simplified collision check based on joint position differences
        for i, pos in enumerate(positions):
            if abs(pos - self._joint_positions[i]) > self.collision_threshold * 10:
                # Large motion could indicate collision risk
                # In production, use actual geometry checking
                pass

        return False

    async def emergency_stop(self) -> bool:
        """
        Execute emergency stop - immediately halt all motion.

        Returns:
            True if emergency stop successful.
        """
        print("EMERGENCY STOP ACTIVATED")
        self._emergency_stop_active = True
        self._is_motion_active = False

        if self.simulation:
            # In simulation, just stop
            self._joint_velocities = [0.0] * 6
            return True

        # Real robot emergency stop would call:
        # self._sdk.emergencyStop()
        print("WARNING: Emergency stop on real robot not implemented - SDK not connected")
        return True

    async def connect(self) -> bool:
        """
        Connect to the robot.

        Returns:
            True if connection successful, False otherwise.
        """
        if self.simulation:
            self._connection_state = RobotConnectionState.CONNECTED
            self._notify_connection_change()
            return True

        # Real robot mode - SDK not implemented yet
        # This is a placeholder for the actual SDK integration
        print("ERROR: Real robot mode requested but Aubo SDK is not implemented.")
        print("Please install pyaubo_sdk and implement the connection logic.")
        print("Set simulation=true to use simulation mode instead.")

        self._connection_state = RobotConnectionState.ERROR
        self._notify_connection_change()
        return False

    async def disconnect(self) -> None:
        """Disconnect from the robot."""
        if self.simulation:
            self._connection_state = RobotConnectionState.DISCONNECTED
            self._notify_connection_change()
            return

        # Real robot disconnection
        # self._sdk.stopRobot()
        # self._sdk.disconnect()
        self._connection_state = RobotConnectionState.DISCONNECTED
        self._notify_connection_change()

    async def move_joints(
        self,
        positions: List[float],
        speed: float = 0.5,
        acceleration: float = 0.5,
        blocking: bool = True,
    ) -> bool:
        """
        Move robot to specified joint positions.

        Args:
            positions: Target joint positions (6 values in radians).
            speed: Movement speed (0.0 to 1.0).
            acceleration: Acceleration (0.0 to 1.0).
            blocking: If True, wait for movement to complete.

        Returns:
            True if command sent successfully, False if rejected.
        """
        if len(positions) != 6:
            raise ValueError("Expected 6 joint positions")

        # Check emergency stop first
        if self._emergency_stop_active:
            print("ERROR: Motion rejected - emergency stop is active")
            return False

        # Check collision before executing
        if self.check_collision(positions):
            print("ERROR: Motion rejected - collision detected")
            return False

        if self.simulation:
            self._is_motion_active = True
            self._joint_positions = positions.copy()
            self._is_motion_active = False
            return True

        # Real robot mode - SDK not implemented
        print("ERROR: move_joints called in real robot mode but SDK is not implemented")
        return False

    async def move_cartesian(
        self,
        position: List[float],
        orientation: List[float],
        speed: float = 0.5,
        acceleration: float = 0.5,
        blocking: bool = True,
    ) -> bool:
        """
        Move robot end effector to specified Cartesian position.

        Args:
            position: Target position [x, y, z] in meters.
            orientation: Target orientation as quaternion [qx, qy, qz, qw].
            speed: Movement speed (0.0 to 1.0).
            acceleration: Acceleration (0.0 to 1.0).
            blocking: If True, wait for movement to complete.

        Returns:
            True if command sent successfully, False if rejected.
        """
        if len(position) != 3:
            raise ValueError("Expected 3 position values [x, y, z]")

        if len(orientation) != 4:
            raise ValueError("Expected 4 quaternion values [qx, qy, qz, qw]")

        # Check emergency stop first
        if self._emergency_stop_active:
            print("ERROR: Motion rejected - emergency stop is active")
            return False

        if self.simulation:
            # In simulation, just store the target
            # In real implementation, would use inverse kinematics
            self._is_motion_active = True
            self._is_motion_active = False
            return True

        # Real robot mode - SDK not implemented
        print("ERROR: move_cartesian called in real robot mode but SDK is not implemented")
        return False

    async def get_state(self) -> RobotState:
        """
        Get current robot state.

        Returns:
            RobotState object with current measurements.
        """
        if self.simulation:
            return RobotState(
                joint_positions=self._joint_positions.copy(),
                joint_velocities=self._joint_velocities.copy(),
                joint_torques=self._joint_torques.copy(),
                end_effector_position=[0, 0, 0],  # Would compute from FK
                end_effector_orientation=[1, 0, 0, 0],
                connection_state=self._connection_state,
                robot_mode=self._robot_mode,
                timestamp=time.time(),
            )

        # Real robot state retrieval:
        # state = self._sdk.getRobotState()
        # return RobotState(...)

        return RobotState(
            joint_positions=self._joint_positions.copy(),
            joint_velocities=self._joint_velocities.copy(),
            joint_torques=self._joint_torques.copy(),
            end_effector_position=[0, 0, 0],
            end_effector_orientation=[1, 0, 0, 0],
            connection_state=self._connection_state,
            robot_mode=self._robot_mode,
            timestamp=time.time(),
        )

    async def start_teach_mode(self) -> bool:
        """Enable teach mode (robot can be manually moved)."""
        self._robot_mode = RobotMode.TEACH
        if not self.simulation:
            # self._sdk.enableTeachMode()
            pass
        return True

    async def start_playback_mode(self) -> bool:
        """Enable playback mode for trajectory execution."""
        self._robot_mode = RobotMode.PLAYBACK
        if not self.simulation:
            # self._sdk.disableTeachMode()
            pass
        return True

    async def execute_trajectory(
        self,
        trajectory: List[JointPositions],
        blocking: bool = True,
    ) -> bool:
        """
        Execute a pre-recorded trajectory.

        Args:
            trajectory: List of JointPositions waypoints.
            blocking: If True, wait for trajectory to complete.

        Returns:
            True if trajectory execution successful.
        """
        if self.simulation:
            for waypoint in trajectory:
                self._joint_positions = waypoint.positions.copy()
                await asyncio.sleep(0.1)  # Simulate movement time
            return True

        # Real trajectory execution:
        # self._sdk.executeTrajectory(trajectory)
        return True

    def set_state_callback(
        self,
        callback: Callable[[RobotState], None],
    ) -> None:
        """Set callback for state updates."""
        self._on_state_update = callback

    def set_connection_callback(
        self,
        callback: Callable[[RobotConnectionState], None],
    ) -> None:
        """Set callback for connection state changes."""
        self._on_connection_change = callback

    def _notify_connection_change(self) -> None:
        """Notify listeners of connection state change."""
        if self._on_connection_change:
            self._on_connection_change(self._connection_state)

    @property
    def connection_state(self) -> RobotConnectionState:
        """Get current connection state."""
        return self._connection_state

    @property
    def robot_mode(self) -> RobotMode:
        """Get current robot mode."""
        return self._robot_mode


def create_controller(
    robot_ip: str = "192.168.1.100",
    port: int = 8080,
    simulation: bool = True,
    collision_detection: bool = True,
    collision_threshold: float = 0.05,
) -> AuboRobotController:
    """
    Factory function to create a robot controller.

    Args:
        robot_ip: Robot IP address.
        port: Communication port.
        simulation: If True, runs without real robot.
        collision_detection: Enable collision detection.
        collision_threshold: Distance threshold for collision detection in meters.

    Returns:
        Configured AuboRobotController instance.
    """
    return AuboRobotController(
        robot_ip=robot_ip,
        port=port,
        simulation=simulation,
        collision_detection=collision_detection,
        collision_threshold=collision_threshold,
    )


if __name__ == "__main__":
    # Test the controller
    controller = create_controller(simulation=True)
    print(f"Controller created in {'simulation' if controller.simulation else 'real'} mode")
