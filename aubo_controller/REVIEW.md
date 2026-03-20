# Review And Plan

Timestamp: 2026-03-20 22:34:07 +08:00

## Rough Check

Current code is closer to the previous target, but it still does not fully meet the bar.

What looks improved:
- Config save flow is no longer double-writing in the frontend. `ConfigTab` now only calls `onUpdateConfig(localConfig)` once in [frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L500).
- Nested config is flattened before posting, which matches the backend request shape in [frontend/src/store/robotStore.ts](D:\Autron\aubo_controller\frontend\src\store\robotStore.ts#L259).
- Real robot mode now fails instead of falsely reporting success in [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L157).
- An emergency-stop endpoint now exists at `/stop` in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L299).
- Simulator model replacement has started to become configurable through `model_path` in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L91) and [backend/src/robot_controller/config.py](D:\Autron\aubo_controller\backend\src\robot_controller\config.py#L44).

What is still not truly satisfactory:
- Collision detection is still effectively a placeholder. `check_collision()` always returns `False`, so the setting exists but does not protect anything in practice in [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L114).
- Emergency stop exists, but there is no clear reset / recovery flow after it is triggered. `_emergency_stop_active` is set to `True` and I do not see a matching clear path in [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L136).
- The frontend left panel still shows only one `SimulationView`; it does not yet contain a camera panel, and there is no stacked camera-plus-Mujoco layout in [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx#L52).
- I do not see any camera service, camera API, or camera state in the current app code. That means the requested camera feature has not started yet.

Conclusion:
- Roughly speaking, the project has fixed some of the earlier plumbing issues.
- It has not yet reached the new requirement around camera integration and left-side split layout.
- Safety is still only partially addressed.

## Requirements For Claude

I did not find any runnable Claude integration inside this repo beyond `.claude/settings.local.json`, so the handoff requirements need to be explicit.

Claude should read:
- PDF path: `D:\Autron\eye-3d-camera-v2.5.4-zh.pdf`

Claude should focus on extracting:
- Device discovery / connection workflow
- Stream acquisition API
- RGB / depth / point cloud capabilities
- Frame format and transport requirements
- Any Python SDK or HTTP / TCP interface examples
- Required runtime dependencies, DLLs, or environment setup

If the PDF cannot be parsed automatically, Claude should:
- State that explicitly
- Fall back to a camera integration scaffold rather than guessing vendor-specific calls
- Keep all vendor-specific assumptions isolated behind a replaceable adapter

## Implementation Plan

### Phase 1: Camera integration design

Claude should first produce a short design note before coding:
- Decide whether the camera layer should be implemented as a backend service module, not embedded directly into FastAPI route handlers.
- Define one stable backend abstraction such as `CameraService` or `Eye3DCameraClient`.
- Keep vendor-specific logic behind that abstraction so the frontend and API do not depend on the PDF-specific SDK shape.

### Phase 2: Backend camera API

Claude should add backend endpoints for:
- Camera status
- Camera connect / disconnect
- Camera frame retrieval or stream URL
- Optional camera config endpoint if exposure / resolution / stream mode is exposed by the PDF

Backend requirements:
- No fake vendor behavior should be represented as real hardware success.
- If the vendor SDK is not available, the API must return an explicit degraded / mock / unavailable state.
- The first implementation may use a mock frame source, but the API contract should already match the intended real camera flow.

### Phase 3: Frontend layout update

Frontend requirement is explicit:
- On the left side of the page, show two vertically stacked panels.
- Top panel: camera view.
- Bottom panel: Mujoco simulation view.
- Right side: keep the control console.

More concretely:
- Update [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx) so the left column becomes a vertical stack container.
- Add a new camera component, separate from `SimulationView`.
- Do not merge camera and simulation into one canvas; they should be two clearly separated panels.

### Phase 4: Frontend camera component

Claude should add a dedicated camera panel component with:
- Connection state
- Last frame timestamp or refresh status
- Empty / unavailable state
- Visible distinction between real feed and mock feed

Preferred behavior:
- If backend only offers polling at first, polling is acceptable.
- If backend supports MJPEG or another stream form cleanly, that is acceptable too.
- The component should not block rendering of the Mujoco panel when the camera is disconnected.

### Phase 5: Validation

Before claiming completion, Claude should verify:
- Frontend builds successfully
- Backend imports successfully
- Left panel is vertically split into camera view above simulation view
- Camera panel degrades gracefully when no hardware / SDK is present
- Existing robot control UI still renders and functions

## Non-Negotiable Constraints

- Do not claim the camera SDK is integrated unless the actual vendor calls are wired and validated.
- Do not label mock images as a real camera feed.
- Do not remove the existing Mujoco view; the requirement is to stack camera plus Mujoco, not replace one with the other.
- Keep camera code modular so the eventual vendor-specific implementation can replace only the adapter layer.

## Suggested File Targets

Claude should likely touch files in this shape:
- [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx)
- New frontend component such as `frontend/src/components/CameraView.tsx`
- [frontend/src/store/robotStore.ts](D:\Autron\aubo_controller\frontend\src\store\robotStore.ts) if shared state is needed
- New backend camera module under `backend/src/robot_controller/`
- [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py)
- Possibly [backend/src/robot_controller/config.py](D:\Autron\aubo_controller\backend\src\robot_controller\config.py) if camera config needs persistence

## Final Direction

At this point, the correct next step is not broad refactoring. The correct next step is:
1. Read `eye-3d-camera-v2.5.4-zh.pdf`.
2. Define a backend camera adapter boundary.
3. Add camera endpoints.
4. Add a new `CameraView` panel.
5. Change the left side of the frontend to camera-on-top and Mujoco-on-bottom.
