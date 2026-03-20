@echo off
setlocal

set "ROOT=D:\Autron\autron_testbed"
set "PYTHON=D:\Autron\aubo_controller\backend\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Python runtime not found: %PYTHON%
  exit /b 1
)

set "PYTHONPATH=%ROOT%\src"

echo [1/3] Preparing MuJoCo runtime model...
"%PYTHON%" "%ROOT%\scripts\prepare_mujoco_model.py" || exit /b 1

echo [2/3] Checking MuJoCo model loading...
"%PYTHON%" "%ROOT%\scripts\check_mujoco_model.py" || exit /b 1

echo [3/3] Running frontend simulation UI flow...
"%PYTHON%" "%ROOT%\scripts\run_frontend_ui_flow.py" || exit /b 1

echo Frontend simulation test completed.
