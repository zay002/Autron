# Public Progress

Date: 2026-03-22

## Done

- Browser simulation pipeline is active: MuJoCo-WASM physics + Three.js rendering.
- Frontend scene switched to integrated robot+gripper model (`aubo_i5_with_ag95.xml`).
- Arm actuator mapping logic added in frontend runtime (name->index mapping).
- Initial actuator target seeding added to reduce startup collapse risk.
- Local simulation ownership flag added to prevent backend polling from overwriting local setpoints.

## In Progress

- Verifying integrated AG95 behavior in the merged model path.
- Stabilizing pose hold under gravity with current actuator gains/limits.

## Next Milestones

1. Add frontend AG95 binary controls (`OPEN` / `CLOSE`) and wire to local MuJoCo actuator target.
2. Sync `Robot State` and `Joint Control` with local simulation runtime (not only store defaults).
3. Enable Cartesian control path for frontend-owned simulation:
   - Short term: route through backend IK endpoint and apply returned joints.
   - Mid term: optional frontend-local IK module.
4. Implement Cartesian Jog that directly affects frontend-owned simulation.
5. Validate integrated model stability with repeatable checks:
   - startup hold pose
   - gripper open/close repeatability
   - no ownership conflict between local sim and backend polling

## Notes

- Development-process internal docs are intentionally excluded from public upload policy.
