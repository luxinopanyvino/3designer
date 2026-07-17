@echo off
setlocal

REM Launch PrintCAD backend and frontend in separate windows.
REM Run this script from the repository root.

set ROOT_DIR=%~dp0

start "PrintCAD Backend" cmd /k "cd /d "%ROOT_DIR%backend" && uv run uvicorn app.main:app --reload --port 8000"
start "PrintCAD Frontend" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

if exist "%ROOT_DIR%organic\vendor\TripoSR" (
    start "PrintCAD Organic" cmd /k "cd /d "%ROOT_DIR%organic" && uv run uvicorn service:app --port 8001"
) else (
    echo Organic service skipped: run the setup in organic\README.md to enable it.
)

echo Backend and frontend windows launched.
endlocal
