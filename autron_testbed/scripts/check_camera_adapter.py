from __future__ import annotations

import sys

from autron_testbed.paths import BACKEND_SRC, CAMERA_ADAPTER_FILE


def main() -> None:
    if not CAMERA_ADAPTER_FILE.exists():
        raise SystemExit(f"Camera adapter file not found: {CAMERA_ADAPTER_FILE}")

    sys.path.insert(0, str(BACKEND_SRC))
    from robot_controller.eye3d_camera_adapter import Eye3DCameraAdapter

    adapter = Eye3DCameraAdapter()

    print("Camera adapter import OK")
    print(f"  File: {CAMERA_ADAPTER_FILE}")
    print(f"  Class: {adapter.__class__.__name__}")
    print(f"  Default DLL path: {adapter._dll_path}")


if __name__ == "__main__":
    main()
