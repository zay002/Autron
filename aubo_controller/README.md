# AUBO Controller

This directory contains the main robot control application: a FastAPI backend, a React frontend, MuJoCo simulation, and camera integration.

## Structure

- `backend/src/robot_controller/api/main.py`: REST and WebSocket API
- `backend/src/robot_controller/robot_controller.py`: high-level robot controller
- `backend/src/robot_controller/robot_client.py`: official `pyaubo_sdk` client path
- `backend/src/robot_controller/aubo_socket.py`: legacy custom socket/WebSocket path that should not remain the primary real-robot path
- `backend/src/robot_controller/mujoco_sim/`: MuJoCo simulator and robot model assets
- `backend/src/robot_controller/camera_service.py`: camera abstraction layer
- `backend/src/robot_controller/eye3d_camera_adapter.py`: current vendor-specific camera adapter
- `frontend/src/components/`: UI panels for simulation, camera, and robot control

## Run

Backend:

```powershell
cd D:\Autron\aubo_controller\backend
set PYTHONPATH=.\src
python -m robot_controller.api.main
```

Frontend:

```powershell
cd D:\Autron\aubo_controller\frontend
npm install
npm run dev
```

Full app:

```powershell
cd D:\Autron\aubo_controller
start_all.bat
```

## Current Technical Position

The intended real-robot communication path is:

- `pyaubo_sdk.RpcClient` on port `30004` for control and state requests
- `pyaubo_sdk.RtdeClient` on port `30010` for telemetry streaming

The project should not rely on a guessed robot-side protocol if it claims official AUBO support.

## Public Progress (2026-03-22)

- Frontend simulation scene now loads an integrated robot+gripper model:
  - `frontend/public/mjcf/assets/scenes/scene.xml`
  - includes `../universal_robots_auboi5/aubo_i5_with_ag95.xml`
- Frontend MuJoCo runtime added:
  - runtime actuator name->index mapping (arm + gripper)
  - initial ctrl seeding before stepping
  - simulation ownership gating (`simulationOwner`) to avoid backend polling overriding local setpoints
- Backend currently exposes:
  - `/move/joints`, `/move/cartesian`, `/move/jog/start`, `/move/jog/stop`
  - Jacobian-based IK path in simulation mode

See `PROGRESS_PUBLIC.md` for milestone status and next actions.

## What Is Still Missing

- proof that connect, startup, state read, and motion execute on a real AUBO robot
- a single truthful state model for robot, simulation, and camera connectivity
- a perception pipeline that outputs calibrated 3D information in the robot/world frame
- a planning and execution layer suitable for VLA or agent-driven tasks
- stronger safety gating for autonomous commands

## Related Files

- `PROGRESS_PUBLIC.md`: public implementation progress and next milestone checklist
- `..\TODO.md`: repository-level architecture TODO list
