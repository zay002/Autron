"""
Mujoco Simulation Module for Aubo i5 Robot.

This module provides aMujoco-based simulation environment for the Aubo i5 robot.
It can load the robot URDF and simulate joint movements.
"""

from __future__ import annotations

import os
import re
import numpy as np
from typing import Optional
import mujoco
import mujoco.viewer


# Robot joint configuration for Aubo i5
# 6 joints matching the real URDF joint names
AUBO_I5_JOINT_NAMES = [
    "shoulder_joint",
    "upperArm_joint",
    "foreArm_joint",
    "wrist1_joint",
    "wrist2_joint",
    "wrist3_joint",
]

# Joint angle limits (radians)
AUBO_I5_JOINT_LIMITS = {
    "shoulder_joint": (-np.pi, np.pi),       # ±360°
    "upperArm_joint": (-np.pi / 2, np.pi / 2),  # ±90°
    "foreArm_joint": (-np.pi, np.pi),       # ±180°
    "wrist1_joint": (-np.pi, np.pi),       # ±180°
    "wrist2_joint": (-np.pi / 2, np.pi / 2),  # ±90°
    "wrist3_joint": (-np.pi, np.pi),       # ±360°
}


class AuboSimulator:
    """Mujoco simulator for Aubo i5 robot."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        gui: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        timestep: float = 0.002,
        gravity: float = -9.81,
        solver_iterations: int = 100,
    ):
        """
        Initialize the Mujoco simulator.

        Args:
            model_path: Path to the robot XML model. If None, creates a simple arm model.
            gui: Whether to show the GUI window.
            viewport_width: Viewport width for rendering.
            viewport_height: Viewport height for rendering.
            timestep: Simulation timestep in seconds.
            gravity: Gravity acceleration in m/s^2.
            solver_iterations: Number of solver iterations per step.
        """
        import os

        self.gui = gui
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.timestep = timestep
        self.gravity = gravity
        self.solver_iterations = solver_iterations

        # Determine model path - use local MuJoCo-ready model by default
        if model_path is None:
            # Use the prepared MuJoCo-ready model in the local models directory
            # This avoids ROS package:// path resolution issues
            local_model = os.path.join(os.path.dirname(__file__), "models", "aubo_i5_mujoco", "aubo_i5.urdf")
            if os.path.exists(local_model):
                model_path = local_model
                print(f"Loading Aubo i5 model from: {model_path}")
                self.model = self._load_model_with_meshes(model_path)
            else:
                print("WARNING: Aubo i5 MuJoCo model not found, using simplified arm model")
                self.model = self._create_simple_arm_model()
        else:
            self.model = self._load_model_with_meshes(model_path)

        # Apply physics configuration
        self.model.opt.timestep = timestep
        self.model.opt.gravity = [0, 0, gravity]
        self.model.opt.solver = mujoco.mjtSolver.mjSOL_NEWTON
        self.model.opt.iterations = solver_iterations
        self.model.opt.ls_iterations = 50

        self.data = mujoco.MjData(self.model)
        self.viewer = None

        # Initialize to home position
        self.home_position = np.array([0.0, -0.785, 1.571, 0.0, 1.571, 0.0])  # radians

    def _load_model_with_meshes(self, model_path: str) -> mujoco.MjModel:
        """
        Load Mujoco model from local URDF with mesh files at same directory level.

        This expects the prepared MuJoCo-ready model where STL files are
        placed in the same directory as the URDF (flattened structure).
        """
        # Save current directory
        original_dir = os.getcwd()

        # Change to the URDF directory so relative paths resolve
        urdf_dir = os.path.dirname(os.path.abspath(model_path))
        os.chdir(urdf_dir)

        try:
            return mujoco.MjModel.from_xml_path(model_path)
        finally:
            # Restore original directory
            os.chdir(original_dir)

    def _create_simple_arm_model(self) -> mujoco.MjModel:
        """Create a simple 6-DOF arm model for testing."""
        xml = """
        <mujoco model="aubo_i5_simple">
            <compiler angle="radian" meshdir="." autolimits="true"/>
            <option gravity="0 0 -9.81"/>

            <!-- Base link -->
            <worldbody>
                <body name="base_link" pos="0 0 0">
                    <geom type="cylinder" size="0.1 0.05" rgba="0.5 0.5 0.5 1"/>

                    <!-- Joint 1: Shoulder -->
                    <body name="link1" pos="0 0 0">
                        <joint name="joint1" type="hinge" axis="0 0 1" pos="0 0 0"/>
                        <geom type="cylinder" size="0.08 0.15" rgba="0.3 0.3 0.8 1"/>

                        <!-- Joint 2: Upper arm -->
                        <body name="link2" pos="0 0 0.3">
                            <joint name="joint2" type="hinge" axis="0 1 0" pos="0 0 0"/>
                            <geom type="cylinder" size="0.06 0.2" rgba="0.3 0.5 0.8 1"/>

                            <!-- Joint 3: Forearm -->
                            <body name="link3" pos="0 0 0.4">
                                <joint name="joint3" type="hinge" axis="0 1 0" pos="0 0 0"/>
                                <geom type="cylinder" size="0.05 0.2" rgba="0.3 0.6 0.8 1"/>

                                <!-- Joint 4: Wrist 1 -->
                                <body name="link4" pos="0 0 0.35">
                                    <joint name="joint4" type="hinge" axis="0 1 0" pos="0 0 0"/>
                                    <geom type="cylinder" size="0.04 0.15" rgba="0.4 0.4 0.9 1"/>

                                    <!-- Joint 5: Wrist 2 -->
                                    <body name="link5" pos="0 0 0.25">
                                        <joint name="joint5" type="hinge" axis="1 0 0" pos="0 0 0"/>
                                        <geom type="cylinder" size="0.035 0.12" rgba="0.4 0.5 0.9 1"/>

                                        <!-- Joint 6: Wrist 3 (End Effector) -->
                                        <body name="link6" pos="0 0 0.2">
                                            <joint name="joint6" type="hinge" axis="0 1 0" pos="0 0 0"/>
                                            <geom type="sphere" size="0.06" rgba="0.9 0.3 0.3 1"/>

                                            <!-- End effector -->
                                            <site name="ee_site" pos="0 0 0.1" size="0.02"/>
                                        </body>
                                    </body>
                                </body>
                            </body>
                        </body>
                    </body>
                </body>
            </worldbody>

            <!-- Actuators -->
            <actuator>
                <motor joint="joint1" ctrllimited="true" ctrlrange="-100 100"/>
                <motor joint="joint2" ctrllimited="true" ctrlrange="-100 100"/>
                <motor joint="joint3" ctrllimited="true" ctrlrange="-100 100"/>
                <motor joint="joint4" ctrllimited="true" ctrlrange="-100 100"/>
                <motor joint="joint5" ctrllimited="true" ctrlrange="-100 100"/>
                <motor joint="joint6" ctrllimited="true" ctrlrange="-100 100"/>
            </actuator>
        </mujoco>
        """
        return mujoco.MjModel.from_xml_string(xml)

    def reset(self) -> None:
        """Reset the simulation to initial state."""
        mujoco.mj_resetData(self.model, self.data)
        self.set_joint_positions(self.home_position)

    def set_joint_positions(self, positions: np.ndarray) -> None:
        """
        Set joint positions.

        Args:
            positions: Array of 6 joint angles in radians.
        """
        if len(positions) != 6:
            raise ValueError(f"Expected 6 joint angles, got {len(positions)}")

        for i, name in enumerate(AUBO_I5_JOINT_NAMES):
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            if joint_id >= 0:
                self.data.qpos[joint_id] = positions[i]

        mujoco.mj_forward(self.model, self.data)

    def get_joint_positions(self) -> np.ndarray:
        """Get current joint positions."""
        positions = np.zeros(6)
        for i, name in enumerate(AUBO_I5_JOINT_NAMES):
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            if joint_id >= 0:
                positions[i] = self.data.qpos[joint_id]
        return positions

    def step(self, control: Optional[np.ndarray] = None) -> None:
        """
        Step the simulation forward.

        Args:
            control: Control torques for each joint. If None, holds current position.
        """
        if control is not None:
            if len(control) != 6:
                raise ValueError(f"Expected 6 control torques, got {len(control)}")
            self.data.ctrl[:] = control
        else:
            # Hold current position with zero control (gravity compensation would be needed for real world)
            self.data.ctrl[:] = 0

        mujoco.mj_step(self.model, self.data)

    def get_end_effector_position(self) -> np.ndarray:
        """Get end effector position in world coordinates."""
        try:
            # Try to use ee_site if it exists
            site_id = self.data.site("ee_site")
            return self.data.site_xpos[site_id].copy()
        except Exception:
            # Fall back to wrist3 body position
            try:
                body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "wrist3_link")
                if body_id >= 0:
                    return self.data.xpos[body_id].copy()
            except Exception:
                pass
            # Last resort: use last body position
            return self.data.xpos[-1].copy()

    def get_end_effector_orientation(self) -> np.ndarray:
        """
        Get end effector orientation as quaternion [w, x, y, z].

        Returns:
            4-element array representing quaternion [w, x, y, z].
        """
        try:
            # Try to use ee_site if it exists
            site_id = self.data.site("ee_site")
            rot_mat = self.data.site_xmat[site_id].reshape(3, 3)
            return self._rotation_matrix_to_quaternion(rot_mat)
        except Exception:
            # Fall back to wrist3 body orientation
            try:
                body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "wrist3_link")
                if body_id >= 0:
                    rot_mat = self.data.xmat[body_id].reshape(3, 3)
                    return self._rotation_matrix_to_quaternion(rot_mat)
            except Exception:
                pass
            # Last resort: identity quaternion
            return np.array([1.0, 0.0, 0.0, 0.0])

    def _rotation_matrix_to_quaternion(self, R: np.ndarray) -> np.ndarray:
        """Convert 3x3 rotation matrix to quaternion [w, x, y, z]."""
        trace = np.trace(R)
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (R[2, 1] - R[1, 2]) * s
            y = (R[0, 2] - R[2, 0]) * s
            z = (R[1, 0] - R[0, 1]) * s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s
        return np.array([w, x, y, z])

    def start_viewer(self) -> None:
        """Start the interactiveMujoco viewer."""
        if self.viewer is None:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        else:
            print("Viewer already running")

    def close_viewer(self) -> None:
        """Close the interactive viewer."""
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

    def render_image(self, width: int = 640, height: int = 480) -> bytes:
        """
        Render the current state to an image.

        Args:
            width: Image width.
            height: Image height.

        Returns:
            PNG image bytes.
        """
        self._prepare_renderer()
        return self._render_frame(width, height)

    def _prepare_renderer(self) -> None:
        """Prepare the renderer."""
        if not hasattr(self, "_renderer"):
            self._renderer = mujoco.Renderer(self.model, height=self.viewport_height, width=self.viewport_width)

    def _render_frame(self, width: int, height: int) -> bytes:
        """Render a single frame."""
        self._renderer.update_scene(self.data, "human")
        img = self._renderer.render(width, height)
        import cv2
        return cv2.imencode('.png', img)[1].tobytes()

    def get_observation(self) -> dict:
        """
        Get full observation state.

        Returns:
            Dictionary containing joint positions, velocities, end effector pose, etc.
        """
        return {
            "joint_positions": self.get_joint_positions().tolist(),
            "joint_velocities": self.data.qvel[:6].tolist(),
            "end_effector_position": self.get_end_effector_position().tolist(),
            "end_effector_orientation": self.get_end_effector_orientation().tolist(),
            "time": self.data.time,
        }


def create_simulator(
    urdf_path: Optional[str] = None,
    use_gui: bool = True,
    timestep: float = 0.002,
    gravity: float = -9.81,
    solver_iterations: int = 100,
) -> AuboSimulator:
    """
    Factory function to create an Aubo i5 simulator.

    Args:
        urdf_path: Optional path to URDF or XML model file.
        use_gui: Whether to show GUI.
        timestep: Simulation timestep in seconds.
        gravity: Gravity acceleration in m/s^2.
        solver_iterations: Number of solver iterations per step.

    Returns:
        Configured AuboSimulator instance.
    """
    return AuboSimulator(
        model_path=urdf_path,
        gui=use_gui,
        timestep=timestep,
        gravity=gravity,
        solver_iterations=solver_iterations,
    )


if __name__ == "__main__":
    # Test the simulator
    sim = create_simulator()
    print("Mujoco model loaded successfully")
    print(f"Number of joints: {len(AUBO_I5_JOINT_NAMES)}")
    print(f"Home position: {sim.home_position}")

    sim.reset()
    print(f"Reset to home: {sim.get_joint_positions()}")

    # Step simulation
    sim.step()
    print(f"After step: {sim.get_joint_positions()}")
