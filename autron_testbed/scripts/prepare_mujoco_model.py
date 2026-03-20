from __future__ import annotations

import shutil

from autron_testbed.paths import RUNTIME_MODEL_DIR, RUNTIME_MODEL_URDF, SOURCE_MODEL_DIR, SOURCE_MODEL_URDF


def copy_tree(src, dst) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> None:
    if not SOURCE_MODEL_URDF.exists():
        raise SystemExit(f"Source URDF not found: {SOURCE_MODEL_URDF}")

    RUNTIME_MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    copy_tree(SOURCE_MODEL_DIR, RUNTIME_MODEL_DIR)

    print("Prepared MuJoCo runtime model")
    print(f"  Source:  {SOURCE_MODEL_DIR}")
    print(f"  Runtime: {RUNTIME_MODEL_DIR}")
    print(f"  URDF:    {RUNTIME_MODEL_URDF}")


if __name__ == "__main__":
    main()
