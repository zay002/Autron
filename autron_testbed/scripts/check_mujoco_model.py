from __future__ import annotations

import os
from pathlib import Path

import mujoco

from autron_testbed.paths import RUNTIME_MODEL_DIR, RUNTIME_MODEL_URDF


def main() -> None:
    if not RUNTIME_MODEL_URDF.exists():
        raise SystemExit(
            "Prepared runtime URDF not found. Run scripts/prepare_mujoco_model.py first."
        )

    original_cwd = Path(os.getcwd())
    os.chdir(RUNTIME_MODEL_DIR)
    try:
        model = mujoco.MjModel.from_xml_path(str(RUNTIME_MODEL_URDF))
    finally:
        os.chdir(original_cwd)

    print("MuJoCo model load OK")
    print(f"  Model file: {RUNTIME_MODEL_URDF}")
    print(f"  nq: {model.nq}")
    print(f"  nv: {model.nv}")
    print(f"  nbody: {model.nbody}")
    print(f"  ngeom: {model.ngeom}")


if __name__ == "__main__":
    main()
