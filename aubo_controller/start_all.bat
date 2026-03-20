@echo off
setlocal

REM One-click launcher for backend and frontend
REM Starts each service in a separate terminal window.

cd /d "%~dp0"

if not exist "backend\.venv\Scripts\activate.bat" (
  echo [ERROR] Backend virtual environment not found: backend\.venv
  echo Create it first or update start_all.bat to match your environment.
  pause
  exit /b 1
)

if not exist "frontend\package.json" (
  echo [ERROR] Frontend package.json not found.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found in PATH.
  pause
  exit /b 1
)

echo Starting backend...
start "Aubo Controller Backend" cmd /k "cd /d \"%~dp0backend\" && call .venv\Scripts\activate.bat && set PYTHONPATH=./src && python -m robot_controller.api.main"

echo Starting frontend...
start "Aubo Controller Frontend" cmd /k "cd /d \"%~dp0frontend\" && npm run dev"

echo.
echo Backend and frontend launch commands have been started.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
exit /b 0
