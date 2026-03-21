# Review Update

Timestamp: 2026-03-20 22:44:02 +08:00

## Overall Status

The camera feature has now started in the right direction:
- there is a dedicated backend camera service abstraction in [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py)
- there are camera API endpoints in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L501)
- the frontend left side is now vertically split with camera on top and Mujoco below in [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx#L53)
- there is a separate camera panel component in [frontend/src/components/CameraView.tsx](D:\Autron\aubo_controller\frontend\src\components\CameraView.tsx)

So structurally, the implementation is finally aligned with the requested layout.

However, the current camera integration is still only a scaffold, and there are several concrete issues that need to be addressed before this should be considered a real Eye 3D camera integration.

## Findings

### 1. High: the current camera implementation is still not based on the Eye 3D camera PDF or vendor SDK

The new backend uses only `MockCameraAdapter` and explicitly hardcodes `create_camera_service(use_mock=True)` in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L128). There is no real adapter, no vendor import, no device discovery, no configuration surface tied to the Eye camera document, and no evidence that the PDF contents were actually translated into code behavior. This is acceptable as a temporary scaffold, but it should not be presented as actual camera support.

### 2. High: frame encoding depends on `cv2`, but `opencv-python` is not declared in backend dependencies

`camera_service.py` imports `cv2` inside `get_frame()` and uses `cv2.imencode('.jpg', frame.data)` in [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py#L281). But [backend/pyproject.toml](D:\Autron\aubo_controller\backend\pyproject.toml) still does not declare any OpenCV dependency. In the current environment, `cv2` is not installed. That means camera status/connect can appear to work, but the first frame request is likely to fail at runtime. This is the most immediate implementation bug in the new camera path.

### 3. Medium: camera status contract is inconsistent between backend and frontend

The frontend `CameraStatus` interface expects a top-level `is_mock` field in [frontend/src/components/CameraView.tsx](D:\Autron\aubo_controller\frontend\src\components\CameraView.tsx#L3), but `/camera/status` returns `camera_info.is_mock`, not `is_mock` at the top level in [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py#L249). Because of that mismatch, the mock badge is not reliably driven by the status API and only gets patched later by frame-fetch logic. This is a small contract bug, but it is exactly the kind of inconsistency that makes future real-camera replacement harder.

### 4. Medium: the mock frame generator is unnecessarily expensive

`MockCameraAdapter.get_frame()` fills a 640x480 RGB frame using nested Python loops in [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py#L116). That is much slower than necessary and will become a bottleneck under polling. For a mock source this should be vectorized with NumPy, especially since the frontend polls every 100 ms in [frontend/src/components/CameraView.tsx](D:\Autron\aubo_controller\frontend\src\components\CameraView.tsx#L81).

### 5. Medium: the PDF-reading problem was handled by skipping vendor-specific implementation too early

Given the stated difficulty reading `eye-3d-camera-v2.5.4-zh.pdf`, the right fallback was not to stop at a generic mock service. The correct intermediate step should have been:
- extract the PDF outline and API chapter names first
- identify the actual transport mode: SDK, DLL, Python module, C API, TCP, HTTP, or something else
- define the adapter methods to mirror those real capabilities
- only then implement a mock adapter with the same contract

Right now the abstraction exists, but it was designed before the document was understood. That risks the wrong API boundary.

## Precise Guidance For The Camera PDF

Whoever is implementing the Eye camera integration should stop trying to "read the whole PDF" in one pass. The correct approach is narrower and more mechanical.

### Step 1: extract only the table of contents and API chapter headers

The first goal is not full comprehension. The first goal is to identify these exact items from `D:\Autron\eye-3d-camera-v2.5.4-zh.pdf`:
- installation / runtime requirements
- SDK package name
- Python examples or C++ examples
- device enumeration / discovery
- connect / open device
- start stream / stop stream
- get color image
- get depth image
- get point cloud
- save image / calibration / exposure parameters
- exception codes / return values

If automated extraction is difficult, the implementer should manually search the PDF for these keywords:
- `Python`
- `SDK`
- `绀轰緥`
- `杩炴帴`
- `鎵撳紑璁惧`
- `閲囧浘`
- `鍥惧儚`
- `娣卞害`
- `鐐逛簯`
- `褰╄壊`
- `鐩告満鍙傛暟`
- `鏍囧畾`
- `閿欒鐮乣

### Step 2: derive the adapter interface from the document, not from guesswork

The adapter should be shaped by the PDF. Before writing vendor code, the implementer should write down:
- what the device object is called
- how the SDK opens a device
- whether acquisition is pull-based or callback-based
- whether images arrive as raw bytes, NumPy arrays, buffers, or files
- whether RGB and depth are separate APIs

Only after that should they finalize `CameraAdapter`.

### Step 3: isolate vendor-specific code in a real adapter file

The codebase should keep:
- `MockCameraAdapter` for development
- a new `Eye3DCameraAdapter` for the real device

That real adapter should live in its own file, for example:
- `backend/src/robot_controller/eye3d_camera_adapter.py`

That file should contain:
- vendor imports
- device initialization
- stream start/stop
- frame conversion logic
- all PDF-specific assumptions

It should not spread vendor logic through FastAPI routes or frontend code.

### Step 4: do not block on full feature coverage

The first real integration milestone should be only:
1. enumerate or open one camera
2. get one RGB frame
3. surface it in `/camera/frame`
4. show it in the top-left panel

Depth, point cloud, parameter control, calibration, and advanced modes can come after that.

## Recommended Next Implementation Order

1. Fix the dependency issue first.
   Either add `opencv-python` to [backend/pyproject.toml](D:\Autron\aubo_controller\backend\pyproject.toml), or remove the `cv2` dependency and encode frames using Pillow instead.

2. Fix the camera status contract.
   Make `/camera/status` and the frontend `CameraStatus` agree on where `is_mock` lives.

3. Keep the current mock path working.
   It is useful for UI progress and layout verification.

4. Create `Eye3DCameraAdapter`.
   Do not modify `MockCameraAdapter` into vendor code. Add a separate adapter.

5. Base the first real adapter only on the minimum viable flow from the PDF:
   device open -> single RGB frame -> frame conversion -> API response.

6. After that, wire selection logic into `create_camera_service(...)`.
   For example, choose mock vs real adapter via config or environment variable.

## Assessment Of The Current Review Target

The left-side layout requirement is now basically satisfied.

The camera integration requirement is only partially satisfied:
- yes for architecture direction
- yes for UI placement
- no for actual Eye 3D camera support
- no for dependency completeness
- no for proof that the PDF was successfully translated into a real adapter

That means the correct next instruction to the implementer is:

"Do not keep expanding the mock camera. First fix frame encoding dependencies, then read only the API-relevant sections of `eye-3d-camera-v2.5.4-zh.pdf`, then implement a separate `Eye3DCameraAdapter` that can open the device and return one RGB frame."

---

## Additional Review Update

Timestamp: 2026-03-20 23:07:13 +08:00

### 6. High: the frontend still does not use the real Aubo i5 3D model

The current frontend simulation panel is still rendering a hand-written placeholder robot rather than the real Aubo i5 model. In [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L13), `RobotArm()` is built entirely from primitive `cylinderGeometry` and `sphereGeometry`, and the file itself describes the scene as a simplified visualization. So from the user's perspective, the system is still not using the actual Aubo i5 3D geometry.

This remains true even if the backend Mujoco layer can attempt to load `aubo_description-main/urdf/aubo_i5.urdf` in [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L64). The frontend does not render backend Mujoco output and does not load the real Aubo meshes directly, so the visible robot is still only an approximation.

### 7. Medium: the current Mujoco model usage is not proven end-to-end

The backend simulator does try to load the Aubo i5 URDF in [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L79), but that is not enough to conclude that the real model is being used correctly in the overall product:
- the visible frontend view is still custom Three.js geometry
- there is no frontend stream of rendered Mujoco frames
- there is no verification here that URDF mesh/resource resolution works robustly during normal app startup

So the claim "the project is using the real Aubo i5 model" is still too strong in its current form. At best, the backend has a partial loading path; the user-facing system still does not clearly demonstrate real-model visualization.

### 8. Medium: the repository root README is missing, so the GitHub landing page is effectively blank

The main project documentation is in [README.md](D:\Autron\aubo_controller\README.md), but the repository root [D:\Autron](D:\Autron) does not contain a top-level `README.md`. Because GitHub displays the root README on the repository landing page, this makes the repo appear blank or undocumented when opened.

This is a repository packaging issue that should be fixed. The root should contain a `README.md` that either:
- documents the project directly, or
- forwards readers into `aubo_controller/README.md`

## Updated Assessment

The left-side page layout is in the requested direction, but the requirement of "correctly using the Aubo i5 real 3D model" is still not satisfied from the frontend/user perspective. Separately, the repository presentation is incomplete because the main README is nested under `aubo_controller` instead of being visible at the repo root.

---

## Strict Review Update

Timestamp: 2026-03-20 23:18:30 +08:00

### 9. High: the current MuJoCo URDF loading fix is still wrong, because it assumes `chdir` is enough to resolve mesh assets

The reported failure

```text
ValueError: Error: Error opening file 'link0.STL'
URDF dir: D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5
CWD: D:\Autron\aubo_controller\backend
After chdir CWD: D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5
STL exists: True
```

is reproducible, and the current loader logic in [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L115) is not sufficient. The code changes the working directory to the URDF folder and then calls `mujoco.MjModel.from_xml_path(model_path)`, assuming that relative mesh paths from the URDF will resolve correctly.

That assumption is false for this model/import path.

I reproduced the issue locally and confirmed the important detail: MuJoCo is not trying to open `meshes/aubo_i5/collision/link0.STL`; it is trying to open only the basename `link0.STL` or `link1.STL`. In other words, with this URDF import flow, the directory information from the mesh path is effectively not being used in the way the current code assumes.

This is why all of the following can be true at the same time:
- the URDF file exists
- `meshes/aubo_i5/collision/link0.STL` exists
- the process has already `chdir`-ed into the URDF directory
- MuJoCo still throws `Error opening file 'link0.STL'`

### 10. High: the current test did not validate the real behavior of MuJoCo asset resolution

The current implementation appears to have stopped at "the file exists on disk" and "the process changed into the model directory". That is not enough. The real contract to test is whether `mujoco.MjModel.from_xml_path(...)` can open every referenced mesh under the exact runtime loading path.

This is a code review problem, not just a test failure:
- the loader strategy was accepted without validating actual MuJoCo behavior
- `_load_model_with_meshes()` is built around a brittle assumption
- there is no preflight check or deterministic packaging step for the mesh assets

### 11. Concrete root cause confirmed

I verified that if the collision STL files are copied into the same directory as `aubo_i5.urdf`, MuJoCo can load the model successfully. That means the immediate failure is specifically caused by the current nested mesh layout:

- current URDF location:
  [aubo_i5.urdf](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5\aubo_i5.urdf)
- current collision mesh location:
  [link0.STL](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5\meshes\aubo_i5\collision\link0.STL)

Under the present MuJoCo import path, those collision meshes are effectively expected at the URDF working directory level by basename, not under `meshes/aubo_i5/collision/`.

## Required Fix Direction

The implementer should stop trying to solve this with more `chdir` logic. That is the wrong layer.

The correct repair options are:

1. Create a deterministic packaged MuJoCo-ready model directory.
   Put the exact mesh files where the MuJoCo importer actually expects them, and keep that layout under source control or generate it explicitly as part of a model-prep step.

2. Do not depend on raw ROS URDF asset layout at runtime.
   The Aubo description package is a ROS-oriented asset layout. MuJoCo's URDF importer is not honoring the nested mesh path structure in the way this code assumes. Treat the MuJoCo-ready model as a separate prepared artifact, not as a direct runtime import of the original ROS package.

3. Prefer building a dedicated MuJoCo model package for Aubo i5.
   The clean fix is to create a curated `models/aubo_i5_mujoco/` directory with:
   - one known-good URDF or MJCF
   - a verified mesh layout
   - a startup test that loads it with `mujoco.MjModel.from_xml_path(...)`

4. Add a real validation test for model loading.
   The project should have a test whose only job is:
   - locate the packaged model
   - load it with MuJoCo
   - fail if any asset cannot be opened

## Minimal Fix The Implementer Can Apply Now

If they want the fastest path to unblocking:

1. Stop loading the original copied URDF layout as-is.
2. Create a MuJoCo-specific local model folder under:
   [models](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models)
3. Place the required `link*.STL` files in the same directory level that MuJoCo actually resolves during import.
4. Update [simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L115) to load that prepared model directly.
5. Add a regression test so this exact failure cannot come back.

## What They Should Not Do

- Do not add more `os.chdir(...)` hacks.
- Do not claim "mesh file exists" as proof that the loader is correct.
- Do not keep relying on the frontend placeholder model as evidence that Aubo i5 model integration is done.
- Do not leave the model-preparation behavior implicit. If files need to be flattened or copied, make that an explicit scripted step or commit the prepared artifact.

## Direct Instruction To The Implementer

"Your current fix is incomplete. The bug is not missing files; the bug is that MuJoCo is resolving the URDF mesh references by basename under this import flow, so `chdir` to the URDF directory is not enough. Prepare a MuJoCo-ready Aubo i5 model package with a verified mesh layout, load that package directly, and add a regression test that calls `mujoco.MjModel.from_xml_path(...)` and fails on any asset-resolution error."
---

## Review Consolidation

Timestamp: 2026-03-20 23:53:46 +08:00

### 12. High: the user-facing frontend simulation is still not the real Aubo i5 model

The current visible frontend robot is still not the actual Aubo i5 3D model. From the user perspective, the simulation panel still behaves like a simplified placeholder rather than a verified rendering of the real robot geometry. This means the requirement of "using the real Aubo i5 model" is still not satisfied at the UI level.

Even if the backend now contains a MuJoCo-ready Aubo model package, that does not close the gap by itself. The frontend display must actually render the real robot model or a true MuJoCo-rendered view, not a hand-built approximation.

### 13. High: the right-side control panel still lacks Cartesian jogging controls

The control console still does not provide the required `x`, `y`, `z`, `rx`, `ry`, `rz` motion controls. This is a functional gap in the user interaction layer.

The required behavior is not a one-shot click. It should be implemented as press-and-hold jogging:
- press starts continuous incremental motion in one axis
- release stops motion immediately
- pointer cancel / mouse leave should also stop motion

That implies both frontend and backend work:
- frontend needs hold-to-run controls
- backend needs a safe jog or repeated micro-step execution path
- motion must stop immediately when input is released

### 14. High: real-robot connection must initialize simulation from live robot state before any motion UI is trusted

When connecting to a real robot, the simulation environment and frontend state must first be synchronized from live hardware state. At minimum, the system should read:
- current joint positions
- current tool pose / TCP pose
- base/tool frame information if applicable
- any origin or calibration values needed for safe alignment

Only after that should the simulator and UI be initialized. If the system connects to real hardware while the simulator or frontend assumes a default home pose, the displayed state can diverge from the real arm immediately, which creates a real safety risk.

This is not an optional polish item. It is part of the minimum safe architecture for mixed real-robot and simulation operation.

### 15. Medium: the simulator-state path is still not stable in simulation testing

In prior simulated regression testing, most control functions succeeded:
- simulation connect
- joint move
- playback mode switch
- Cartesian command
- emergency stop
- disconnect

But `/simulator/state` still returned HTTP 500 during the same flow. That means the control path is only partially closed. The app can accept commands, but the simulator observation/state reporting layer is not yet stable enough to rely on.

### 16. Medium: the project's own startup flow is still not reliable enough for handoff testing

I was able to verify that the backend can run, but the project's own startup path is still not robust enough to treat as complete:
- `start_all.bat` starts the backend successfully
- the frontend launched by the project path did not become reliably reachable on `http://127.0.0.1:3000`
- I was able to expose the frontend through a separate fallback static-serving path, but that is not equivalent to the project being self-starting correctly

So the code side should still treat startup reliability as an active issue. A proper handoff target is:
- run `start_all.bat`
- access frontend directly at the documented port
- verify backend proxying works without fallback tooling

## Consolidated Direction To The Implementer

The next round of work should be prioritized in this order:

1. Fix the project's native startup flow so frontend and backend come up reliably from the provided launcher.
2. Replace the visible frontend placeholder robot with the real Aubo i5 model or a true MuJoCo-rendered view.
3. Add `x/y/z/rx/ry/rz` press-and-hold jogging controls on the right-side control panel.
4. On real-robot connect, read the live robot state first and initialize simulator/UI state from that live data before enabling motion trust.
5. Fix `/simulator/state` so simulation testing has a stable observation path.
---

## Model Review Clarification

Timestamp: 2026-03-21 00:16:08 +08:00

### 17. Clarification: the current MuJoCo model appears usable, but the code side still needs to document the source and preparation path correctly

After checking the current working model and rendering it, the current MuJoCo-side Aubo i5 model appears to be usable enough to treat as the active working model for now. In other words, this is no longer a case where the project is obviously loading a completely wrong placeholder model on the backend side.

However, this does **not** mean the code side can claim that the URDF-to-XML conversion pipeline is already fully correct without further explanation. The remaining issue is now one of traceability and correctness documentation:
- which exact source model variant from `D:\Autron\aubo_description-main` was used
- what preparation step was applied to make it loadable by MuJoCo
- whether the current model is based on collision meshes, visual meshes, or a mixed representation
- why this particular prepared version should be treated as the project's canonical working model

So the review position should now be:
- the current MuJoCo model can be accepted as the temporary working model
- but the implementer must stop describing it vaguely as "already correctly converted" unless they also document the source variant and preparation steps

### Required Documentation From The Implementer

The code side should explicitly record all of the following in code comments or project docs:
- source file path from `aubo_description-main`
- exact robot variant name, for example `aubo_i5`, `aubo_i5_30`, or another production variant
- whether the loaded geometry is visual geometry or collision geometry
- what file-copying / flattening / preprocessing was done to make MuJoCo load it
- which file under the project should now be treated as the authoritative working model

### Practical Rule Going Forward

If the current model is visually and structurally acceptable for the project, it is fine to continue using it.

But from this point on, model claims in code review should be precise:
- acceptable: "the project currently uses the prepared working MuJoCo model stored in the local models directory"
- not acceptable: "the URDF has been correctly converted" without showing the actual conversion basis and output contract
---

## Frontend Review Addendum

Timestamp: 2026-03-21 00:22:26 +08:00

### 18. High: the frontend still renders a hand-built placeholder arm, which is why the user sees simple geometry instead of the real Aubo i5

This is now directly confirmed by the current frontend code. In [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx), the displayed robot is still constructed manually from primitive geometries:
- `cylinderGeometry`
- `sphereGeometry`
- hard-coded link lengths
- a custom `RobotArm()` kinematic chain

So even if the backend MuJoCo side has a usable working model, the frontend is not using that model for visualization. The simple geometry seen in the browser is the expected result of the current frontend implementation.

This means the code side must stop treating "backend model is loadable" as evidence that the frontend is already showing the real robot. Those are separate layers, and the frontend layer is still incomplete.

### 19. High: the frontend needs a real-model display path, not just backend model availability

To satisfy the requirement of showing the real Aubo i5 on the page, the implementer must choose and complete one of these paths:
- render the actual robot model directly in the frontend using the prepared mesh/model assets
- or display a real MuJoCo-rendered view produced by the backend

What should not continue is the current hybrid state where:
- backend has a working robot model
- frontend still displays a fake arm
- the UI wording suggests simulation realism that the visible scene does not actually provide

### 20. Medium: the current frontend color system still uses dark blue / purple styling and does not match the requested white + orange main theme

The current frontend styling still uses a dark blue/purple visual system, for example:
- [App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx) uses `#1a1a2e`, `#16213e`, `#0f3460`
- [SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx) uses blue/purple link colors and dark backgrounds

This does not match the requested main theme direction.

The required visual direction should be updated to:
- white as the dominant base/background/surface color family
- orange as the primary accent/action color family
- secondary neutrals should be light gray / charcoal, not blue-purple

### Required Theme Direction

The code side should treat the new frontend visual requirement as:
- primary surfaces: white / off-white
- primary accent: orange
- buttons, active highlights, progress indicators, selected states: orange family
- text and separators: neutral dark gray / light gray
- remove the current blue-purple dominant palette from the main shell and control surfaces

This does not require making the interface flat or generic. It just means the main product identity should shift away from the current dark blue control-room look.

## Direct Instruction To The Implementer

"The reason the browser still shows simple geometry is that the frontend is still rendering a manually built placeholder arm in `SimulationView.tsx`; the real MuJoCo/Aubo model is not wired into the frontend display path. Replace that placeholder visualization with a real-model display path, and at the same time restyle the main frontend shell from the current dark blue/purple palette to a white + orange theme. Also keep the previously requested `x/y/z/rx/ry/rz` press-and-hold jogging controls and real-robot state synchronization requirements in scope."

## Remaining Defects Review

Timestamp: 2026-03-21 11:06:15 +08:00

### 21. High: camera connect response contract is still inconsistent with the frontend state model

The camera UI still has a real state-contract bug between frontend and backend.

In [frontend/src/components/CameraView.tsx](D:\Autron\aubo_controller\frontend\src\components\CameraView.tsx), connect() calls /api/camera/connect and then does setStatus(data). But the render path decides whether the camera is connected using status?.connected.

The problem is that [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py) returns success, message, state, and camera_info from connect(), but it does not return a top-level connected field. So after a successful connect, the frontend can still remain in the disconnected UI branch because the shape of the /camera/connect response does not match the shape expected by CameraStatus.

This is not a cosmetic issue. It means the page can claim the camera is disconnected immediately after a successful connect request.

### 22. High: real Eye 3D adapter is still not actually wired into the runtime path

The backend startup now initializes the camera service through [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py) using create_camera_service(use_mock=config.camera.use_mock).

However, [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py) still only returns a service when use_mock=True. The use_mock=False path still has no real return value and no real adapter construction.

That means the project still does not support a real camera handoff path correctly:
- mock mode works
- real-camera mode still has no complete factory path
- the existence of [backend/src/robot_controller/eye3d_camera_adapter.py](D:\Autron\aubo_controller\backend\src\robot_controller\eye3d_camera_adapter.py) is still not the same thing as having real-camera support integrated

### 23. High: the Eye 3D adapter still has broken SDK lifecycle handling for more than one instance

[backend/src/robot_controller/eye3d_camera_adapter.py](D:\Autron\aubo_controller\backend\src\robot_controller\eye3d_camera_adapter.py) still has two concrete lifecycle bugs:

- In _ensure_sdk_initialized(), self._camera is only assigned when _sdk_initialized is false. If a second adapter instance is created after the first one initialized the SDK, the second instance increments the refcount but keeps self._camera = None. Any later SDK call on that instance can fail on a null handle.
- In _cleanup_sdk(), the code resets self._sdk_refcount = 0 instead of the class variable Eye3DCameraAdapter._sdk_refcount, so the reference count bookkeeping is still wrong.

This means the current adapter implementation is still not safe to treat as a robust shared SDK wrapper.

### 24. Medium: the native project launcher still prints the wrong ports, which makes handoff testing harder than it needs to be

[start_all.bat](D:\Autron\aubo_controller\start_all.bat) still prints:
- Backend: http://localhost:12450
- Frontend: http://localhost:11451

But the actual application stack is not using those ports as its normal runtime contract.

Even if the launcher starts processes successfully, these wrong printed endpoints create immediate confusion during manual testing and make it harder to tell whether startup is actually working as intended.

The launcher output should match the real service ports exactly.

### 25. Medium: the simulator end-effector fallback name is still inconsistent with the loaded model

In [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py), the end-effector fallback code looks for body name wrist3_link.

But the actual working URDF under [backend/src/robot_controller/mujoco_sim/models/aubo_i5_30/aubo_i5_30.urdf](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5_30\aubo_i5_30.urdf) uses wrist3_Link.

That case mismatch means the fallback lookup can fail even when the intended end-effector body exists. In practice this can push the simulator into the last-resort branch that uses the last body in the model rather than the intended wrist/end-effector body.

This is exactly the kind of subtle mismatch that later shows up as "simulation pose looks off" or "Cartesian state is inconsistent".

### 26. Medium: MuJoCo image rendering still depends on OpenCV even though the backend dependency contract does not declare it

The simulator render path in [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py) still imports cv2 inside _render_frame() and uses it to encode PNG bytes.

But [backend/pyproject.toml](D:\Autron\aubo_controller\backend\pyproject.toml) does not declare opencv-python.

So the render path still has an undeclared runtime dependency. That makes the feature fragile across fresh environments, CI, or handoff machines.

If OpenCV is required, it needs to be declared. If it is not required, the render path should use an already-declared imaging dependency instead.

### 27. Low: the camera disconnected placeholder still contains mojibake text instead of a valid icon

[frontend/src/components/CameraView.tsx](D:\Autron\aubo_controller\frontend\src\components\CameraView.tsx) still renders 馃摲 in the disconnected state.

This is minor compared with the integration defects above, but it is still a clear encoding/cleanup issue in a user-visible part of the page.

## Updated Direction To The Implementer

The remaining work should now be treated as:

1. Keep the already-confirmed frontend review items in scope: replace the visible placeholder robot, add x/y/z/rx/ry/rz press-and-hold jogging, initialize sim/UI from live robot state on real connect, and shift the main theme to white + orange.
2. Fix the camera API contract first so /camera/connect and /camera/status expose a consistent state shape to the frontend.
3. Finish the real-camera factory path so use_mock=False actually constructs and returns the Eye 3D adapter-backed service.
4. Correct the Eye 3D SDK singleton/refcount implementation before treating the adapter as production-ready.
5. Fix the launcher output and remaining simulator state/rendering inconsistencies so manual testing is not blocked by avoidable environment and naming problems.

## Re-Review: Fix Verification & Feature Implementation

Timestamp: 2026-03-21 11:20:14 +08:00

### Findings (ordered by severity)

### 1. High: MuJoCo render path is still not functionally available, so the frontend cannot reliably display the real robot view

The frontend has switched to backend rendering (/api/simulator/render), but the backend render implementation still fails at runtime.

Evidence:
- [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L14) now fetches /api/simulator/render?width=640&height=480.
- [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L343) calls self._renderer.update_scene(self.data, "human").
- Local module test with current code raised: ValueError: The camera "human" does not exist.

Impact:
- The previous placeholder-geometry issue is structurally improved, but the real render feature is still unavailable in practice.

### 2. High: Camera frame feature still fails in runtime environment

Camera connect/status contract is improved, but frame retrieval still fails.

Evidence:
- [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py#L299) depends on rom PIL import Image during frame encoding.
- Local module test with current .venv returned None for frame and status error No module named 'PIL'.
- API smoke also returned success=False for /camera/frame.

Impact:
- Camera panel can connect, but cannot produce image stream in current runtime.

### 3. High: Cartesian jog is still a non-functional stub on backend

UI now has press-and-hold controls, but backend jog does not move the robot/simulator.

Evidence:
- Frontend press-and-hold events are present at [frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L282), [frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L292).
- Backend jog_start only sets a flag at [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L393), and jog_stop only clears it at [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L396).
- Local test confirmed joint state does not change during jog hold.

Impact:
- Requirement "按住持续移动" is not truly implemented yet; it is only API/UX scaffolding.

### 4. High: "Real robot connect then sync simulator" remains unreachable because real connect is still hard-fail

The sync logic exists in API, but the real connection path still fails by design.

Evidence:
- Sync block exists at [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L304).
- Real connect still returns error at [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L157), [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L175).

Impact:
- The safety-critical sync workflow is not operational until SDK integration is complete.

### 5. Medium: Eye3D adapter multi-instance lifecycle is still unsafe

The adapter increments shared refcount but does not provide a valid SDK handle for later instances.

Evidence:
- Refcount increment path: [backend/src/robot_controller/eye3d_camera_adapter.py](D:\Autron\aubo_controller\backend\src\robot_controller\eye3d_camera_adapter.py#L128).
- Subsequent SDK calls use instance handle: [backend/src/robot_controller/eye3d_camera_adapter.py](D:\Autron\aubo_controller\backend\src\robot_controller\eye3d_camera_adapter.py#L152).
- In the "already initialized" branch, self._camera is not assigned.

Impact:
- Works in single-instance happy path, but fragile for restart/recreate scenarios.

### 6. Medium: End-effector fallback body name still mismatches current URDF naming

Evidence:
- Fallback uses wrist3_link in [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L245).
- URDF uses wrist3_Link in [backend/src/robot_controller/mujoco_sim/models/aubo_i5_30/aubo_i5_30.urdf](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5_30\aubo_i5_30.urdf#L188).

Impact:
- Fallback pose/orientation source can degrade to unintended body selection.

## What is correctly fixed in this round

- Frontend now uses backend simulator render route instead of hard-coded primitive robot drawing: [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L14).
- Left panel layout (camera over simulation) is in place: [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx#L49).
- White + orange main theme direction is largely applied in shell/components: [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx#L93), [frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L665).
- Camera connect response now includes connected and aligns better with frontend state model: [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py#L182), [backend/src/robot_controller/camera_service.py](D:\Autron\aubo_controller\backend\src\robot_controller\camera_service.py#L204).
- Config update flattening on frontend is implemented and no longer posts nested config blindly: [frontend/src/store/robotStore.ts](D:\Autron\aubo_controller\frontend\src\store\robotStore.ts#L312).

## Re-review conclusion

This update is a real step forward on structure and UI integration, but from a delivery standard it is **not yet "correctly fixed and fully implemented"**. The remaining blockers are runtime-critical: simulator rendering, camera frame streaming, and non-stub jogging behavior.

## Re-Review Addendum: Frontend View Interaction & Scene Information

Timestamp: 2026-03-21 11:31:27 +08:00

### 28. High: frontend simulation panel is still a passive video-like canvas, not an interactive free camera view

User feedback is accurate: currently it is "can only watch, cannot operate camera".

Code evidence:
- [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L15) only polls /api/simulator/render.
- [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L97) renders a plain <canvas> without any mouse/pointer/wheel interaction handlers.
- There is no local camera state (azimuth/elevation/lookat/distance) in this component.

Impact:
- Frontend does not support orbit/pan/zoom/reset for the simulation view.
- This does not meet the expected "web-side free camera operation" requirement.

### 29. High: backend render API does not expose camera pose control contract

Code evidence:
- [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L563) /simulator/render only accepts width and height.
- There is no API for camera parameters (azimuth/elevation/distance/lookat/fov) and no camera state update endpoint.

Impact:
- Even if frontend adds mouse interactions, there is no backend contract to apply viewpoint updates.
- Current architecture can only stream a fixed/default view.

### 30. High: scene lacks coordinate context (axes/grid/pose overlay), so operators cannot judge pose safely

User feedback "no coordinate information" is accurate at scene level.

Code evidence:
- [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L88) only shows title/status plus render canvas.
- No axis widget, no world/grid lines, no camera pose indicator, no TCP/world coordinate overlay in this panel.

Impact:
- Operators cannot infer orientation or depth reliably from the current render alone.
- This is a usability and safety risk for teleoperation/jogging workflows.

### 31. Medium: "white model" appearance is currently expected because model visual path is not fully materialized for MuJoCo rendering

Code evidence:
- URDF visual meshes reference .3ds assets in [backend/src/robot_controller/mujoco_sim/models/aubo_i5_30/aubo_i5_30.urdf](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5_30\aubo_i5_30.urdf#L14).
- Working folder flattening currently ships collision STL files (link0.STL ... link6.STL) in models/aubo_i5_30 root.

Impact:
- Rendered scene tends toward untextured/white industrial mesh style ("白模").
- So "see arm shape but no realistic appearance" is consistent with current asset pipeline.

## Direct instruction to code side (from current user feedback)

Current status is not acceptable as "feature completed". The user can only watch a static viewpoint render.

Required implementation for next iteration:

1. Add frontend free-camera interaction in SimulationView (drag rotate, right-drag pan, wheel zoom, double-click reset).
2. Add backend camera-control contract (at least azimuth/elevation/distance/lookat) and make /simulator/render use these parameters.
3. Add scene coordinate information in the simulation panel (axes + grid + pose readout overlay for TCP/world coordinates).
4. Upgrade model appearance pipeline from collision-only white mesh toward visual mesh/material pipeline, or explicitly mark current mode as "collision-view" to avoid misleading presentation.

Until these are done, the correct statement is:
"The page can display simulation frames, but web-side camera interaction and coordinate-aware visualization are not yet implemented."

## Re-Review Addendum: Black Screen / Model Not Visible

Timestamp: 2026-03-21 11:44:38 +08:00

### 32. High: user feedback "cannot see robot model, screen is black" is valid and reproducible

Current code has entered a state where interaction controls were added, but visible rendering quality regressed to near-black output in default workflow.

I reproduced this with local simulator module:
- after sim.reset(), rendered frame statistics were approximately min=0, max=190, mean=1.46
- this means the frame is overwhelmingly dark; the robot can become effectively invisible to the user

### 33. High: frontend camera-pan implementation currently has a hard TypeScript error

In [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L191), prev is referenced before definition in pan logic:
- const scale = prev.distance * 0.002

This breaks production build (
pm run build fails with TS2304: Cannot find name 'prev').

Impact:
- camera-control feature is not in a production-ready state
- release build cannot pass until this is fixed

### 34. High: rendering defaults are not operator-friendly (dark background + white model + no scene contrast)

Code evidence:
- default camera is [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L16): zimuth=0, elevation=-30, distance=3, lookat=[0,0,0.3]
- backend applies that pose directly in [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L357)
- generated model geoms are white (
gba="1 1 1 1") in [generated_test.xml](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\models\aubo_i5_30\generated_test.xml#L15)

Impact:
- with dark frame background and weak scene contrast, users can perceive the frame as "all black"
- current visual defaults are not acceptable for operational use

### 35. Medium: even though free-camera controls and coordinate overlays were added, they do not solve visibility if the base render remains dark

Yes, code now includes:
- camera query params in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L564)
- mouse interaction and overlays in [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L167)

But user-visible outcome is still "black screen". So this cannot be marked complete until visibility baseline is fixed.

## Direct instruction to code side

The user currently cannot see the robot model (perceived full-black frame). Treat this as a blocking issue, not a cosmetic issue.

Required fixes before next handoff:

1. Fix the TypeScript compile error in SimulationView pan logic (undefined prev).
2. Establish a visible default render baseline:
   - improve camera default pose for immediate robot visibility
   - add scene contrast (ground/grid/background/light tuning)
   - keep overlay text readable but secondary
3. Add a render sanity check in backend (e.g., reject or warn when frame luminance is near-zero for consecutive frames).
4. Do not mark "camera control complete" until user can reliably see and manipulate the robot model from page load.

The correct current status is:
"Free-camera API and UI scaffolding were added, but the simulation view is still not functionally acceptable because model visibility can collapse to a black frame."

## Re-Review Addendum: Regression to Pure Black Frame

Timestamp: 2026-03-21 12:29:59 +08:00

### 36. Critical: /simulator/render can return all-zero pixels while still reporting success=true

This directly matches current user feedback: "the frame is pure black".

Verification result (runtime API):
- Requesting /simulator/render returns success=true
- Decoded raw image bytes are all zero (min=0, max=0, mean=0)

Code evidence:
- [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L586) returns success if no exception is thrown.
- There is no pixel-level sanity check before returning success.

Impact:
- Frontend sees successful responses but draws a black frame.
- This is a blocking functional regression.

### 37. High: frontend treats zero-image as valid success frame and provides no visibility warning

Code evidence:
- [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L64) always writes decoded RGB bytes into canvas.
- There is no luminance/variance validation and no fallback error state for all-black content.

Impact:
- User gets a black screen with no actionable error signal.

### 38. High: launcher does not prevent stale backend process conflicts

Code evidence:
- [start_all.bat](D:\Autron\aubo_controller\start_all.bat#L29) blindly starts backend/frontend in new terminals.
- No existing-port conflict check, no PID replacement, no post-launch version/health identity check.

Impact:
- New code can be edited but old backend process can still serve requests.
- "code is updated but behavior did not change" becomes very likely during manual testing.

### 39. Medium: simulator default model path is hardcoded absolute path, reducing portability and predictability

Code evidence:
- [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L81) hardcodes D:/Autron/aubo_controller/manipulator_grasp/assets/scenes/scene.xml.

Impact:
- Rendering behavior depends on local machine path state.
- Environment drift can cause regressions that are hard to trace.

## Direct instruction to code side

Treat this as a release blocker. The user currently sees pure black output after feature completion.

Required fixes:

1. In backend render endpoint, reject all-zero (or near-zero luminance) frames as failure and return clear diagnostics.
2. In frontend SimulationView, add black-frame detection and show explicit error message instead of silent black canvas.
3. In launcher/startup flow, enforce single backend instance and verify the running process identity/version after startup.
4. Remove hardcoded absolute simulator model path; load from config/relative path and log the resolved model path at startup.

Current truthful status:
"Feature scaffolding exists, but rendering pipeline regressed: backend can return success with black frames, so user-visible model rendering is not functionally complete."

## Re-Review Addendum: Physics Not Advancing, Interaction Lag, Rotation Direction

Timestamp: 2026-03-21 12:40:47 +08:00

### 40. Critical: gravity/collision are configured but not actually simulated continuously, so free objects remain visually suspended

Root cause is not missing gravity values; it is missing simulation progression in the render path.

Evidence:
- Simulator gravity is set in [simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L102).
- Table collision is re-enabled in [simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L418).
- But /simulator/render only calls 
ender_image(...) and never steps physics in [main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L563).
- Runtime verification: repeated 
ender_image() keeps data.time unchanged ( .0 -> 0.0), while explicit step() advances time ( .0 -> 0.01).

Impact:
- Objects with free joints appear floating because physics integration is effectively paused unless /simulator/step is called manually.

### 41. High: frontend drag latency and flicker are expected with current request model

Evidence in [SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx):
- etchAndRender is bound to camera via useCallback ([SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L29)).
- The polling effect depends on that callback and recreates a new interval on every camera update ([SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L246)).
- Every render fetch also triggers an extra /simulator/state request via etchTcpPose() ([SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L92)).
- There is no in-flight cancellation / sequence guard, so out-of-order responses can paint stale frames.

Impact:
- During drag, network/decode load spikes and frame order can jitter, causing visible lag and frequent flashing.

### 42. Medium: left-drag rotation direction still mismatches user expectation

Evidence:
- Current rotate mapping is hardcoded at [SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L200): zimuth: prev.azimuth - dx * 0.5.

Given current user acceptance feedback, this mapping is still opposite of expected behavior.

Impact:
- Camera manipulation feels unintuitive even when drag events are received correctly.

## Direct instruction to code side

Treat this as unfinished despite feature scaffolding.

1. Add continuous physics stepping for live render mode (background step loop or step-on-render with stable dt), not just manual /simulator/step.
2. Decouple render polling from camera state changes to avoid interval recreation on every mouse move.
3. Add request sequencing / cancellation in frontend render fetch to prevent stale-frame flicker.
4. Reduce per-frame extra calls (do not fetch TCP pose at render FPS; use lower-rate telemetry channel).
5. Reverse left-drag azimuth mapping to match operator expectation, and keep it consistent with double-click reset orientation.

Current truthful status:
"Model and scene can load, but physics is not advancing continuously, so gravity/collision effects are not reflected in the live view; interaction loop also introduces drag latency/flicker and rotation direction mismatch."

## Re-Review Addendum: ERROR Overlay, JSON/Black Loop, State Desync, TCP/Base Axes

Timestamp: 2026-03-21 12:54:26 +08:00

### 43. Critical: frontend currently keeps stale image on canvas while also showing error overlay, so user sees "ERROR and simulation frame" simultaneously

Evidence:
- In [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L362), overlay is shown when loading || error.
- Canvas content is not cleared when error occurs (error only sets state; previous frame remains on canvas).

Impact:
- UI shows contradictory state: old frame still visible + ERROR message on top.
- This exactly matches current user report.

### 44. High: JSON/black problems are amplified by duplicated render pipelines and unsafe response parsing

Evidence:
- The component has two render request paths simultaneously:
  - etchAndRender callback [SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L32)
  - an independent polling block with duplicated decode/draw logic [SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L264)
- Both paths call 
esponse.json() without guarding non-JSON responses.
- Black-frame detection (mean < 1) flips to error state at [SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L301), while stale canvas remains.

Impact:
- Frequent parse/black oscillation manifests as "JSON or black" instability.
- Complexity and duplicated code paths make behavior non-deterministic under transient backend responses.

### 45. High: right-side status is still not synchronized with simulator view state

Evidence:
- Right panel data is from store getState() -> /api/state via [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx#L21) and [frontend/src/store/robotStore.ts](D:\Autron\aubo_controller\frontend\src\store\robotStore.ts#L276).
- /api/state comes from controller, not simulator state [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L389).
- Simulation controller still returns placeholder FK data (end_effector_position=[0,0,0]) in [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L289).

Impact:
- Right-side values can disagree with visible simulation pose.
- User cannot trust right panel for simulator teleoperation.

### 46. High: simulator jogging/cartesian control is still non-intuitive and functionally incomplete for direct visual control

Evidence:
- jog_start/jog_stop in controller only toggles a boolean, no kinematic update [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L376).
- move_cartesian in simulation path returns success but does not update simulator pose [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L266).
- Backend only syncs simulator on joint move command, not cartesian/jog [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L427).

Impact:
- User cannot perform intuitive end-effector visual control in simulation from right-side controls.

### 47. Medium: flange/TCP information is not clearly exposed in right panel

Evidence:
- Right panel shows only X/Y/Z from endEffectorPosition [frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L316).
- No explicit flange frame name, no orientation (
x/ry/rz or quaternion) block in right panel.

Impact:
- End-effector/flange pose cannot be clearly validated during operation.

### 48. Medium: XYZ axes are screen-fixed overlay, not anchored to robot base frame

Evidence:
- Axes origin is hardcoded to canvas pixel coordinates (cx=50, cy=h-50) in [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L134).

Impact:
- Displayed axes do not represent robot base frame placement.
- User statement "xyz轴没有移动到机械臂底座" is correct.

### 49. High: current frontend build is broken by SimulationView dead code/unused symbols

Evidence from local build:
- 
pm run build fails with:
  - jointPositions is declared but its value is never read
  - etchAndRender is declared but its value is never read

Impact:
- Current frontend cannot pass production build checks.

## Direct instruction to code side

1. Remove duplicated render pipeline in SimulationView and keep one deterministic fetch/decode path.
2. On render error, clear canvas (or replace with explicit fallback layer) so UI never shows stale frame + error simultaneously.
3. Guard JSON parsing with 
esponse.ok and content-type checks; return structured error handling path for non-JSON payloads.
4. Unify right panel telemetry source with simulator state when in simulation mode (/simulator/state), not controller placeholders.
5. Implement actual simulator-side cartesian/jog behavior or disable these controls until implemented; do not return fake success.
6. Add explicit flange/TCP pose block in right panel including orientation (either quaternion or rx/ry/rz) and source frame label.
7. Replace pixel-fixed XYZ overlay with base-frame anchored visualization (model-space transform from robot base).
8. Fix current TypeScript build errors and require 
pm run build pass before next handoff.

Current truthful status:
"The page can render simulation frames, but error-handling and state synchronization are still inconsistent; right-side control/status does not yet provide trustworthy simulator-linked operation."

## Re-Review Addendum: Requirement Compliance & Limp Joints Regression

Timestamp: 2026-03-21 12:58:01 +08:00

### 50. Critical: simulation joints are effectively "limp" because physics steps run with zero control torque

Your report is correct: the arm does not maintain posture and behaves as if joints have no holding force.

Evidence:
- In [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L248), step() sets self.data.ctrl[:] = 0 when no control is provided.
- In [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L359), 
ender_image() now calls self.step() every frame.
- This means every rendered frame advances dynamics under gravity with zero joint holding effort.
- Runtime verification: a fixed joint pose drifts heavily after repeated steps (q0 -> q50 -> q250 changed significantly).

Impact:
- Arm appears "瘫软" during normal viewing.
- Any visual/manual operation becomes untrustworthy.

### 51. High: previous required fixes are still not fully compliant (build and simulation panel architecture)

Evidence:
- Frontend production build still fails: 
pm run build reports unused symbols in [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L12), [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L32).
- SimulationView still contains duplicated render logic paths, increasing instability risk [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L32), [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L264).

Impact:
- Not yet at handoff quality.

### 52. High: right panel is still not synchronized to simulator truth

Evidence:
- Right panel data comes from store getState() -> /api/state [frontend/src/store/robotStore.ts](D:\Autron\aubo_controller\frontend\src\store\robotStore.ts#L276).
- /api/state is controller state, not simulator observation [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L389).
- Simulation controller still returns placeholder end-effector position [0,0,0] [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L289).

Impact:
- Right-side X/Y/Z and joint info can diverge from what user sees in simulation.

### 53. Medium: flange/TCP display still not clear enough for operation

Evidence:
- Right panel only shows X/Y/Z without explicit flange orientation or frame label [frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L316).

Impact:
- Cannot clearly validate flange pose during operation.

### 54. Medium: XYZ axis overlay is still screen-fixed, not anchored at robot base

Evidence:
- Axes are drawn at fixed canvas pixel position (cx=50, cy=h-50) in [frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L134).

Impact:
- Axis widget does not represent real base frame location.

## Direct instruction to code side

1. Stop stepping dynamics with zero torque in render path; implement posture holding for simulation (e.g., PD position hold to commanded joints) before each physics step.
2. Separate "view refresh" from "physics integration" loops and make the integration policy explicit.
3. Unify right panel telemetry with /simulator/state when in simulation mode.
4. Add explicit flange pose block on right panel (position + orientation + frame label).
5. Replace screen-fixed axis overlay with base-frame anchored visualization.
6. Resolve frontend build errors and require 
pm run build pass before next submission.

Current truthful status:
"Scene/model can render, but joint dynamics are currently unheld, causing limp-arm behavior; major sync and operability requirements remain incomplete."

## Re-Review Addendum: Simulation Control and Real-Robot Sync Requirements

Timestamp: 2026-03-21 13:12:33 +08:00

### 55. Critical: simulation cartesian/jog control is still a placeholder, so right-side controls cannot truly drive the simulated arm

Evidence:
- In [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L266), `move_cartesian()` in simulation mode only toggles `_is_motion_active` and returns success without changing joint pose.
- In [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L376), `jog_start()` only sets a boolean flag.
- In [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L396), `jog_stop()` only clears that flag.
- Runtime check in current codebase confirms this behavior: `move_cartesian` returns `True`, but `get_state()` joint values and end-effector position remain unchanged.

Impact:
- Frontend appears to provide Cartesian/jog controls, but those controls do not produce actual simulator motion.
- This exactly matches user feedback: "right panel cannot control robot."

### 56. High: right-side status is still not sourced from simulator truth in simulation mode

Evidence:
- App polling calls `getState()` every second in [frontend/src/App.tsx](D:\Autron\aubo_controller\frontend\src\App.tsx#L20).
- Store `getState()` fetches `/api/state` in [frontend/src/store/robotStore.ts](D:\Autron\aubo_controller\frontend\src\store\robotStore.ts#L278).
- `/api/state` returns controller state, not simulator observation in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L392).
- Controller simulation `get_state()` still returns placeholder end-effector position `[0, 0, 0]` in [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L289).

Impact:
- Right panel joint/TCP data can be stale or structurally wrong versus the left simulation view.
- User cannot rely on right panel as "current simulator state."

### 57. Critical: real-robot synchronization path is still unreachable because real SDK connection is not implemented

Evidence:
- `connect()` for non-simulation mode still hard-fails with "SDK not implemented" in [backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L169).
- `/connect` contains initial sync logic for real robot in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L301), but this branch depends on successful real connection and is therefore not operational today.
- Runtime check confirms `simulation=False` connect result: `False`, state `error`.

Impact:
- Requirement "connect real robot -> simulator synchronized to real state -> synchronized control" is not delivered yet.

### 58. High: API command-to-simulator synchronization is incomplete and inconsistent

Evidence:
- `/move/joints` updates simulator (`simulator.set_joint_positions`) in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L425).
- `/move/cartesian` and `/move/jog/*` do not update simulator state in [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L432), [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L455).

Impact:
- Different control modalities have different behavior quality.
- User sees partial success on joint sliders but "no effect" on Cartesian/jog.

### 59. Medium: right panel has UI fields for joints, but missing trustworthy data contract and clear simulator/real source labeling

Evidence:
- Joint/TCP UI exists in [frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L306).
- Data source does not switch between simulator telemetry and real telemetry based on active mode.
- No explicit source indicator ("simulator" vs "real robot") for shown values.

Impact:
- User perceives "joint info not shown or not useful" because displayed values are not guaranteed to represent active scene/hardware.

## Direct instruction to code side

1. Implement real simulation motion semantics for all control paths:
   - `move_joints` (already partial),
   - `move_cartesian` (IK or mapped incremental solver),
   - `jog_start/jog_stop` (continuous task loop with safe stop).
2. In simulation mode, right panel must read simulator state (`/simulator/state`) as the single source of truth.
3. In real mode, after SDK connect succeeds:
   - read live robot joint/TCP state immediately,
   - set simulator to that state,
   - start a periodic sync loop from real robot -> simulator/UI,
   - only then enable operation controls.
4. Make control synchronization symmetric:
   - command to real robot,
   - mirror to simulator when acknowledged,
   - reject/rollback UI optimistic update on failure.
5. Add explicit right-panel source tag and timestamp for telemetry (`source=simulator|robot`, `last_update`).
6. Keep controls disabled when not connected, and show explicit reason message in panel (not only button disable).

Current truthful status:
"The right panel UI exists, but core control and telemetry contracts are still incomplete: simulation Cartesian/jog is not truly implemented, and real-robot sync/control is not operational because SDK connection path remains unimplemented."
