from __future__ import annotations

from pathlib import Path


TESTBED_ROOT = Path(__file__).resolve().parents[2]
AUTRON_ROOT = TESTBED_ROOT.parent
CONTROLLER_ROOT = AUTRON_ROOT / "aubo_controller"
BACKEND_ROOT = CONTROLLER_ROOT / "backend"
BACKEND_SRC = BACKEND_ROOT / "src"
MODEL_ROOT = BACKEND_SRC / "robot_controller" / "mujoco_sim" / "models"

SOURCE_MODEL_CANDIDATES = [
    MODEL_ROOT / "aubo_i5_mujoco",
    MODEL_ROOT / "aubo_i5",
]

SOURCE_MODEL_DIR = next((path for path in SOURCE_MODEL_CANDIDATES if path.exists()), SOURCE_MODEL_CANDIDATES[0])
SOURCE_MODEL_URDF = SOURCE_MODEL_DIR / "aubo_i5.urdf"

RUNTIME_ROOT = TESTBED_ROOT / "runtime"
RUNTIME_MODEL_DIR = RUNTIME_ROOT / "aubo_i5_mujoco"
RUNTIME_MODEL_URDF = RUNTIME_MODEL_DIR / "aubo_i5.urdf"

CAMERA_ADAPTER_FILE = BACKEND_SRC / "robot_controller" / "eye3d_camera_adapter.py"
