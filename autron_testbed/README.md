# Autron Testbed

Local-only test project for validating the current `Autron` progress without changing the main app.

This project is intentionally outside [aubo_controller](D:\Autron\aubo_controller). It is meant for:

- isolated MuJoCo model preparation and loading checks
- quick camera-adapter import checks
- simulated backend operation regression checks
- simulated frontend UI interaction checks
- local regression verification before touching the main controller

## Launchers

`start_test.bat`
- model and adapter checks only

`start_simulation_test.bat`
- backend API simulation flow

`start_frontend_simulation_test.bat`
- full frontend simulation flow through a headless local browser
- does not connect to a real robot or a real camera
- uses mock camera and simulation robot mode only
- serves the existing frontend `dist` build through a local static proxy server

## Run

Frontend operation test:

```bat
start_frontend_simulation_test.bat
```
