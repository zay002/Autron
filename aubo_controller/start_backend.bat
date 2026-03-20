@echo off
REM Start Aubo Controller Backend
REM Usage: double-click this file or run from command line

cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
set PYTHONPATH=./src
python -m robot_controller.api.main
pause
