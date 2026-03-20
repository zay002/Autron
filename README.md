# Autron - Physical World Intelligent Agent

> Building an Aubot-class intelligent agent capable of perceiving and interacting with the physical world through robotics, computer vision, and AI.

## Vision

The ultimate goal of **Autron** is to create an intelligent agent that:

- **Perceives** the physical world through multi-modal sensors (RGB cameras, depth sensors, force feedback)
- **Understands** environment context using computer vision and AI
- **Acts** by controlling robotic systems with precision and safety
- **Learns** from interactions to improve performance over time

Inspired by the **Aubo i5** industrial robot arm, we are building a full-stack system that bridges digital intelligence with physical reality.

## Project Structure

```
Autron/
├── aubo_controller/          # Main robot control system
│   ├── backend/              # FastAPI backend
│   │   └── src/robot_controller/
│   │       ├── robot_controller.py    # Core robot control
│   │       ├── mujoco_sim/            # Physics simulation
│   │       ├── camera_service.py       # Camera abstraction
│   │       └── eye3d_camera_adapter.py # Eye 3D camera SDK
│   ├── frontend/             # React + Three.js UI
│   └── start_all.bat         # One-click launcher
├── aubo_description-main/    # Aubo robot 3D models & URDF
├── AuboStudio_SDK_API.pdf   # Aubo robot SDK documentation
└── eye-3d-camera-v2.5.4-zh.pdf  # Eye 3D camera documentation
```

## Current Progress

### Phase 1: Robot Control Foundation ✅
- [x] FastAPI backend with joint and Cartesian control
- [x] Mujoco physics simulation with real Aubo i5 URDF model
- [x] WebSocket real-time state updates
- [x] Emergency stop and safety controls

### Phase 2: Camera Integration ✅
- [x] Camera service abstraction layer with adapter pattern
- [x] Eye 3D M2-EyePro camera SDK integration
- [x] Mock camera adapter for development/testing
- [x] Frontend camera view panel (top-left of UI)

### Phase 3: User Interface ✅
- [x] Left panel: Camera view (top) + Mujoco simulation (bottom)
- [x] Right panel: Control console with joint sliders, config, logs
- [x] Status indicators for backend, robot, and simulation

### Phase 4: Physical World Perception 🔄 IN PROGRESS
- [ ] Eye 3D camera frame acquisition
- [ ] Depth image and point cloud support
- [ ] Visual servoing for object tracking

### Phase 5: Intelligent Control 🔄 PLANNED
- [ ] Collision detection with real-time avoidance
- [ ] Trajectory planning and optimization
- [ ] AI-based skill learning from demonstrations

## Technology Stack

### Backend
- **FastAPI** - REST API and WebSocket server
- **Mujoco** - Physics simulation engine
- **NumPy** - Numerical computation
- **Eye3DViewer SDK** - 3D camera integration

### Frontend
- **React 18** - UI framework
- **Three.js / React Three Fiber** - 3D visualization
- **Zustand** - State management
- **Vite** - Build tool

### Robotics
- **Aubo i5** - 6-DOF industrial robot arm
- **pyaubo_sdk** - Aubo robot SDK (when available)
- **Eye 3D M2-EyePro** - RGB-D camera

## Quick Start

```bash
# Navigate to controller
cd aubo_controller

# Start backend and frontend
start_all.bat

# Or manually:
# Backend
cd backend
set PYTHONPATH=./src
.venv\Scripts\activate.bat
python -m robot_controller.api.main

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Access the UI at **http://localhost:3000**

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/state` | GET | Robot state (positions, velocities) |
| `/move/joints` | POST | Move to joint positions |
| `/move/cartesian` | POST | Move to Cartesian position |
| `/camera/status` | GET | Camera connection status |
| `/camera/frame` | GET | Get camera frame (JPEG base64) |
| `/stop` | POST | Emergency stop |
| `/ws` | WebSocket | Real-time state stream |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Camera View │  │ Mujoco View │  │  Control Console    │ │
│  │  (top)     │  │  (bottom)   │  │  (right panel)     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                          │ REST / WebSocket
┌─────────────────────────┴──────────────────────────────────┐
│                        Backend                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ FastAPI     │  │ Mujoco Sim   │  │ Camera Service   │  │
│  │ Server     │  │ (Physics)    │  │ (Eye3D Adapter)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                     Robot / Simulator                        │
│  ┌──────────────────┐  ┌─────────────────────────────────┐ │
│  │   Aubo i5 Arm    │  │    Eye 3D Camera M2-EyePro     │ │
│  │  (or Simulation) │  │    (or Mock Camera)            │ │
│  └──────────────────┘  └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Roadmap

### Near Term (v0.2)
- Complete Eye 3D camera RGB frame acquisition
- Integrate depth imaging
- Add point cloud visualization

### Medium Term (v0.3)
- Visual servoing for object tracking
- Collision-free trajectory planning
- MoveIt-compatible motion planning

### Long Term (v1.0)
- AI skill learning from human demonstrations
- Self-supervised environment exploration
- Multi-agent coordination capabilities

## References

- [Aubo Robot Official](https://www.aubo-robotics.com/)
- [Mujoco Documentation](https://mujoco.readthedocs.io/)
- [Eye 3D Camera SDK](./eye-3d-camera-v2.5.4-zh.pdf)

## License

MIT License - See individual project directories for details.

---

**Autron** - Where intelligence meets physical reality.
