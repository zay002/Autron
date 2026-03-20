@echo off
setlocal

set "ROOT=D:\Autron\autron_testbed"
set "PYTHON=D:\Autron\aubo_controller\backend\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Python runtime not found: %PYTHON%
  exit /b 1
)

set "PYTHONPATH=%ROOT%\src"

echo [1/4] Preparing MuJoCo runtime model...
"%PYTHON%" "%ROOT%\scripts\prepare_mujoco_model.py" || exit /b 1

echo [2/4] Checking MuJoCo model loading...
"%PYTHON%" "%ROOT%\scripts\check_mujoco_model.py" || exit /b 1

echo [3/4] Checking camera adapter import...
"%PYTHON%" "%ROOT%\scripts\check_camera_adapter.py" || exit /b 1

echo [4/4] Running simulated API flow...
"%PYTHON%" "%ROOT%\scripts\run_simulated_flow.py" || exit /b 1

echo Simulation testbed checks completed.
