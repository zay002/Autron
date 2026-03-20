# Code Review

Timestamp: 2026-03-20 22:14:55 +08:00

Scope: reviewed current code and cross-checked the claimed fixes in `RESPONSE.md`, with focus on safety controls, Mujoco model usage, and replaceability of the 3D model layer.

## Findings

### 1. High: safety settings exist only as configuration fields; there is no actual collision detection or stop logic in the control path

The system exposes `collision_detection` and `collision_threshold` in config and UI ([backend/src/robot_controller/config.py](D:\Autron\aubo_controller\backend\src\robot_controller\config.py#L24), [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L79), [frontend/src/store/robotStore.ts](D:\Autron\aubo_controller\frontend\src\store\robotStore.ts#L90)), but those values are never consulted when executing `move_joints()` or `move_cartesian()` ([backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L136), [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L346)). There is also no emergency-stop, protective-stop, or halt endpoint anywhere in the API, and no server-side abort path on unsafe motion. For a robot controller, presenting safety controls in the UI without enforcing them is materially misleading.

### 2. High: there is still no stop / emergency-stop capability exposed by the system

The only lifecycle action besides connect is `disconnect` ([backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L284)). There is no `/stop`, `/halt`, `/emergency-stop`, or equivalent API, and the controller implementation contains only a commented placeholder `# self._sdk.stopRobot()` in `disconnect()` ([backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L130)). That means the system cannot model a basic operational safety behavior such as immediately stopping motion while staying connected.

### 3. High: the frontend "Mujoco" view is not using the Mujoco model at all

`SimulationView.tsx` renders a hand-written Three.js kinematic chain with hardcoded lengths and colors ([frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L18)), while the UI badge still labels the panel as `Mujoco` ([frontend/src/components/SimulationView.tsx](D:\Autron\aubo_controller\frontend\src\components\SimulationView.tsx#L141)). This is not just an implementation shortcut; it is a representation mismatch. The user is being shown a custom approximate scene, not the backend Mujoco model and not the actual robot geometry.

### 4. Medium: the backend Mujoco simulator still does not use the real Aubo robot model by default

Although the simulator supports loading an external `model_path` ([backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L43), [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L302)), all actual construction paths call `create_simulator(...)` without any URDF/XML path ([backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L113), [backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L424)). In that case the simulator always falls back to `_create_simple_arm_model()` ([backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L89)). So the project has a hook for custom models in code, but the running application still does not use the Aubo description package or any production robot asset.

### 5. Medium: there is a backend hook for replacing the simulation model, but no app-level interface to select or swap models

From a code architecture perspective, `AuboSimulator(model_path=...)` and `create_simulator(urdf_path=...)` are a reasonable low-level seam for replacement ([backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L41), [backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L302)). But that seam is not surfaced in config, API, or frontend. `SimulatorConfigRequest` has physics fields only, no model path ([backend/src/robot_controller/api/main.py](D:\Autron\aubo_controller\backend\src\robot_controller\api\main.py#L93)), and the frontend has no mechanism to switch geometry sources. So the answer to "is there an interface to replace with a new 3D model?" is only partially yes: there is a code-level constructor parameter, but not an integrated product-level interface.

### 6. Medium: `RESPONSE.md` claims the duplicate save-write issue was fixed, but the current code still contains it

`RESPONSE.md` states that `handleSaveConfig` was removed and the save button now calls only `onUpdateConfig(localConfig)` once ([RESPONSE.md](D:\Autron\aubo_controller\RESPONSE.md#L61)). That does not match the current code. `ControlConsole.tsx` still defines `handleSaveConfig()` ([frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L83)), still passes `onSave={handleSaveConfig}` into `ConfigTab` ([frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L135)), and the save button still issues both `onUpdateConfig(localConfig)` and `onSave()` ([frontend/src/components/ControlConsole.tsx](D:\Autron\aubo_controller\frontend\src\components\ControlConsole.tsx#L510)). The flattening fix in the store is real, but the response document overstates what was fixed.

## Notes

- One important improvement is real: non-simulation robot mode now fails instead of returning false success ([backend/src/robot_controller/robot_controller.py](D:\Autron\aubo_controller\backend\src\robot_controller\robot_controller.py#L113)).
- Another real improvement is that simulator physics parameters are now applied to the Mujoco model options ([backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L76)).
- The end-effector orientation format is also now internally consistent as a quaternion ([backend/src/robot_controller/mujoco_sim/simulator.py](D:\Autron\aubo_controller\backend\src\robot_controller\mujoco_sim\simulator.py#L207)).

## Overall Assessment

The system is still a prototype controller rather than a safety-reviewed robot control stack. Safety-related settings are mostly declarative, not enforced; stop behavior is missing; the backend Mujoco layer is still using a simplified arm by default; and the frontend visualization is a separate custom model while being labeled as Mujoco. The project does leave a useful constructor-level seam for replacing the backend simulation model, but it has not yet been turned into an end-to-end configurable interface.
