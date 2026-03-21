# Autron

Autron is a robotics workspace centered on an AUBO arm, a browser control UI, MuJoCo simulation, and camera integration. The current repository already has a usable frontend/backend skeleton, but it is not yet a full real-robot perception-action stack.

## Repository Layout

- `aubo_controller/`: main application
- `aubo_controller/backend/`: FastAPI backend, robot control, simulation, camera service
- `aubo_controller/frontend/`: React UI for control, simulation, and camera panels
- `aubo_description-main/`: robot description assets and meshes
- `aubo_test/`: isolated SDK test area for `pyaubo_sdk` and official examples
- `AuboStudio_SDK_API.pdf`: local AUBO SDK reference
- `eye-3d-camera-v2.5.4-zh.pdf`: local camera manual

## Current Direction

The practical backend direction is:

- `Python` as the main control plane
- official `pyaubo_sdk` for robot communication
- Mech-Eye SDK for perception
- optional `C++` sidecar only for latency-critical execution loops

This is the right split if the project later needs VLA policies or agent-based robot control. Model orchestration, perception, planning, and tool calling are all easier in Python.

## Current Progress (2026-03-22)

- MuJoCo-WASM + Three.js simulation is running in the browser.
- AUBO model has actuator-based joint control and damping in simulation assets.
- Integrated robot+gripper model path is now active in the frontend scene (`aubo_i5_with_ag95.xml`).
- Frontend simulation ownership gating was added to avoid backend polling overriding local WASM setpoints.
- Backend still provides simulation endpoints for joint/cartesian/jog and includes a Jacobian-based IK solver path.

## Main Gaps

The project still needs:

- frontend gripper open/close controls wired to the integrated AG95 actuator
- robust local simulation state sync (rendered pose <-> Robot State / Joint Control UI)
- local Cartesian Jog control path for frontend-owned simulation
- unified IK control strategy between frontend-local sim and backend simulation endpoints
- proven end-to-end real AUBO control through the official SDK lifecycle
- Mech-Eye depth, point cloud, and calibration pipelines
- world-frame perception outputs that motion planning can consume
- safety gates before autonomous execution

## Key Documents

- `TODO.md`: architecture and implementation gaps for VLA/Agent plus Mech-Eye integration
- `AGENTS.md`: contributor instructions for this repository
- `aubo_controller/PROGRESS_PUBLIC.md`: public progress snapshot and next milestones
- `aubo_test/PYAUBO_EXAMPLES_GUIDE.md`: mapping of official `pyaubo_sdk` examples to backend functions

## Getting Started

To run the current controller app on Windows:

```powershell
cd D:\Autron\aubo_controller
start_all.bat
```

To inspect the official AUBO Python SDK examples:

```powershell
cd D:\Autron\aubo_test
.\.venv\Scripts\python.exe .\import_pyaubo_sdk.py
```
