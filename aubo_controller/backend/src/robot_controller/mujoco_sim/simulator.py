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


# Robot joint configuration for Aubo i5 (from manipulator_grasp model)
# 6 joints matching the MuJoCo MJCF model joint names
AUBO_I5_JOINT_NAMES = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]

# Joint angle limits (radians) - from model range
AUBO_I5_JOINT_LIMITS = {
    "shoulder_pan_joint": (-3.04, 3.04),
    "shoulder_lift_joint": (-3.04, 3.04),
    "elbow_joint": (-3.04, 3.04),
    "wrist_1_joint": (-3.04, 3.04),
    "wrist_2_joint": (-3.04, 3.04),
    "wrist_3_joint": (-3.04, 3.04),
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
            # Use the complete scene from manipulator_grasp which includes:
            # - aubO_i5 robot
            # - AG95 gripper
            # - Tables and objects (Apple, Banana, Hammer, Knife, Duck)
            # - Lighting, ground plane, and coordinate axes
            # Resolve relative to this file's location
            # File: backend/src/robot_controller/mujoco_sim/simulator.py
            # Go up 4 levels to reach project root: D:/Autron/aubo_controller/
            sim_dir = os.path.dirname(os.path.abspath(__file__))  # mujoco_sim/
            robot_ctrl_dir = os.path.dirname(sim_dir)  # robot_controller/
            src_dir = os.path.dirname(robot_ctrl_dir)  # src/
            backend_dir = os.path.dirname(src_dir)  # backend/
            project_root = os.path.dirname(backend_dir)  # aubo_controller/
            local_model = os.path.join(project_root, "manipulator_grasp", "assets", "scenes", "scene.xml")
            if os.path.exists(local_model):
                model_path = local_model
                print(f"Loading model from: {model_path}")
                self.model = self._load_model_with_meshes(model_path)
            else:
                print(f"WARNING: Model not found at {local_model}, using simplified arm model")
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

        # Store model path for reference
        self.model_path = model_path

        # Fix scene collision - enable collision on tables
        self._fix_table_collision()

        # Initialize to home position (all zeros - relaxed position)
        self.home_position = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # radians

        # Desired positions for posture holding (updated by set_joint_positions)
        self._desired_positions = self.home_position.copy()

        # PD control gains for posture holding
        self._kp = 10.0  # Proportional gain
        self._kd = 2.0   # Derivative gain

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

        # Update desired positions for posture holding
        self._desired_positions = np.array(positions)

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
            control: Control torques for each joint. If None, applies PD position control to hold current posture.
        """
        if control is not None:
            if len(control) != 6:
                raise ValueError(f"Expected 6 control torques, got {len(control)}")
            self.data.ctrl[:] = control
        else:
            # PD position control to hold desired joint positions
            for i, name in enumerate(AUBO_I5_JOINT_NAMES):
                joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
                if joint_id >= 0:
                    # Get DOF address for this joint
                    dof_addr = self.model.jnt_dofadr[joint_id]
                    if dof_addr >= 0:
                        current_pos = self.data.qpos[joint_id]
                        current_vel = self.data.qvel[dof_addr]
                        desired_pos = self._desired_positions[i]
                        error = desired_pos - current_pos
                        # PD control: torque = Kp * error - Kd * velocity
                        self.data.ctrl[i] = self._kp * error - self._kd * current_vel

        mujoco.mj_step(self.model, self.data)

    def get_end_effector_position(self) -> np.ndarray:
        """Get end effector position in world coordinates."""
        try:
            # Try to use ee_site if it exists
            site_id = self.data.site("ee_site")
            return self.data.site_xpos[site_id].copy()
        except Exception:
            # Fall back to wrist3 body position (URDF uses wrist3_Link)
            try:
                body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "wrist3_Link")
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
            # Fall back to wrist3 body orientation (URDF uses wrist3_Link)
            try:
                body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "wrist3_Link")
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

    def render_image(
        self,
        width: int = 640,
        height: int = 480,
        azimuth: float = 0,
        elevation: float = -30,
        distance: float = 3,
        lookat: Optional[list] = None,
    ) -> bytes:
        """
        Render the current state to an image.

        Args:
            width: Image width.
            height: Image height.
            azimuth: Camera azimuth angle in degrees (horizontal rotation).
            elevation: Camera elevation angle in degrees (vertical rotation).
            distance: Camera distance to lookat point.
            lookat: [x, y, z] lookat point.

        Returns:
            PNG image bytes.
        """
        # Step physics before rendering to advance simulation
        self.step()
        return self._render_frame(width, height, azimuth, elevation, distance, lookat)

    def _prepare_renderer(self, render_width: int = 640, render_height: int = 480) -> None:
        """Prepare the renderer with appropriate dimensions.

        Always uses 640x480 renderer for consistency. The requested dimensions
        are passed to the render call but the internal renderer stays fixed size
        to avoid MuJoCo renderer issues with dimension changes.
        """
        if not hasattr(self, "_renderer"):
            self._renderer = mujoco.Renderer(self.model, height=480, width=640)
            self._render_width = 640
            self._render_height = 480

    def _render_frame(self, width: int, height: int, azimuth: float = 0, elevation: float = -30, distance: float = 3, lookat: Optional[list] = None) -> bytes:
        """Render a single frame with specified camera pose."""
        self._prepare_renderer(width, height)

        # Configure camera pose
        cam = mujoco.MjvCamera()
        cam.azimuth = azimuth
        cam.elevation = elevation
        cam.distance = distance
        if lookat:
            cam.lookat = lookat
        else:
            # Default lookat at robot base
            cam.lookat = [0, 0, 0.3]

        # Configure scene for better visibility
        scene_option = mujoco.MjvOption()
        scene_option.frame = mujoco.mjtFrame.mjFRAME_WORLD  # Show world frame

        # Note: scene.xml already defines proper lighting, don't override
        self._renderer.update_scene(self.data, cam, scene_option)
        img = self._renderer.render()
        # Return raw RGB bytes - frontend will handle display via canvas
        return img.tobytes()

    def _configure_lighting(self) -> None:
        """Configure scene lighting for better visibility.

        Note: The scene.xml already defines lights (headlight, directional light),
        but we enhance visibility by configuring light properties.
        """
        if not hasattr(self, '_lights_configured'):
            # Enable and configure the lights defined in the model
            for i in range(min(3, self.model.nlight)):
                self.model.light_active[i] = 1
                # Position lights around the robot
                if i == 0:
                    self.model.light_pos[i] = [2, 2, 3]  # Main light upper right
                    self.model.light_dir[i] = [-0.5, -0.5, -1]
                elif i == 1:
                    self.model.light_pos[i] = [-2, 1, 2]  # Fill light left
                    self.model.light_dir[i] = [0.5, -0.3, -0.8]
                elif i == 2:
                    self.model.light_pos[i] = [0, -2, 1]  # Bottom fill
                    self.model.light_dir[i] = [0, 0.8, -0.5]
                self.model.light_specular[i] = 0.3
                self.model.light_ambient[i] = 0.4
                self.model.light_diffuse[i] = 0.5
            self._lights_configured = True

    def _fix_table_collision(self) -> None:
        """
        Fix table collision in the scene.

        The scene.xml defines tables with collision disabled (contype=0, conaffinity=0).
        This method enables collision on existing table geoms so objects can rest on them.
        """
        table_names = ["table1", "table2"]
        for name in table_names:
            geom_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, name)
            if geom_id >= 0:
                self.model.geom_contype[geom_id] = 1
                self.model.geom_conaffinity[geom_id] = 1
                print(f"Enabled collision on {name} (geom_id={geom_id})")
            else:
                print(f"Warning: Could not find geom {name}")

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
