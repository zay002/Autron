@echo off
setlocal enabledelayedexpansion

REM One-click launcher for backend and frontend
REM Starts each service in a separate terminal window.
REM Automatically kills any existing processes on the configured ports.

cd /d "%~dp0"

REM Ports used by the application
set BACKEND_PORT=12450
set FRONTEND_PORT=11451

REM Check for existing processes on ports and kill them
echo Checking for existing processes on ports %BACKEND_PORT% and %FRONTEND_PORT%...

REM Find and kill any process using the backend port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
  echo Killing existing backend process on port %BACKEND_PORT% (PID: %%a)
  taskkill /F /PID %%a >nul 2>&1
)

REM Find and kill any process using the frontend port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
  echo Killing existing frontend process on port %FRONTEND_PORT% (PID: %%a)
  taskkill /F /PID %%a >nul 2>&1
)

REM Kill any existing Aubo Controller windows from previous launches
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq Aubo Controller*" >nul 2>&1

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

REM Wait a moment for port cleanup
timeout /t 1 /nobreak >nul

echo Starting backend on port %BACKEND_PORT%...
start "Aubo Controller Backend" cmd /k "cd /d \"%~dp0backend\" && call .venv\Scripts\activate.bat && set PYTHONPATH=./src && python -m robot_controller.api.main"

echo Starting frontend on port %FRONTEND_PORT%...
start "Aubo Controller Frontend" cmd /k "cd /d \"%~dp0frontend\" && npm run dev"

echo.
echo Backend and frontend launch commands have been started.
echo Backend: http://localhost:%BACKEND_PORT%
echo Frontend: http://localhost:%FRONTEND_PORT%
echo.
exit /b 0
