"""
Test script to validate that the MuJoCo Aubo i5 model loads correctly.
This test should fail if any mesh asset cannot be resolved.

Run with:
    cd backend
    set PYTHONPATH=./src
    python -m robot_controller.mujoco_sim.test_model_loading
"""

import os
import sys

# Ensure we're in the backend directory
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from robot_controller.mujoco_sim.simulator import create_simulator


def test_model_loading():
    """Validate that the Aubo i5 MuJoCo model loads without asset errors."""
    print("Testing MuJoCo model loading...")

    # This should NOT raise ValueError about missing files
    sim = create_simulator(use_gui=False)

    assert sim.model is not None, "Model should be loaded"
    assert sim.model.nbody == 7, f"Expected 7 bodies, got {sim.model.nbody}"
    assert sim.model.njnt == 6, f"Expected 6 joints, got {sim.model.njnt}"

    # Test joint positions
    positions = sim.get_joint_positions()
    assert len(positions) == 6, f"Expected 6 joint positions, got {len(positions)}"

    # Test setting joint positions
    test_positions = [0.1, -0.2, 0.3, 0.4, 0.5, 0.6]
    sim.set_joint_positions(test_positions)
    positions = sim.get_joint_positions()
    assert all(abs(p - t) < 0.001 for p, t in zip(positions, test_positions)), \
        f"Joint positions not set correctly: {positions}"

    print("All tests passed!")
    print(f"  - Model loaded: {sim.model.nbody} bodies, {sim.model.njnt} joints")
    print(f"  - Joint positions: {positions}")


if __name__ == "__main__":
    test_model_loading()
