@echo off
title Neighborhood Issue Reporter - Share Launcher
echo ========================================================
echo   Launching Neighborhood Issue Reporter ^& Cloudflare Tunnel
echo ========================================================
echo.

rem Resolve the repo root correctly whether run from root or tools\share
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%package.json" (
    set "REPO_ROOT=%SCRIPT_DIR%"
) else if exist "%SCRIPT_DIR%..\..\package.json" (
    pushd "%SCRIPT_DIR%..\.."
    set "REPO_ROOT=%CD%"
    popd
) else (
    set "REPO_ROOT=%CD%"
)

rem Locate cloudflared executable
if exist "%REPO_ROOT%\cloudflared.exe" (
    set "CLOUDFLARED_BIN=%REPO_ROOT%\cloudflared.exe"
) else if exist "%REPO_ROOT%\tools\share\cloudflared.exe" (
    set "CLOUDFLARED_BIN=%REPO_ROOT%\tools\share\cloudflared.exe"
) else (
    set "CLOUDFLARED_BIN=cloudflared.exe"
)

echo [1/3] Starting local backend on port 8000 (with auto-reload)...
start "NIR Backend (FastAPI)" cmd /k "cd /d %REPO_ROOT% && if exist .venv\Scripts\python.exe (.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) else (python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload)"

echo [2/3] Starting local frontend on port 5173...
start "NIR Web Server (Vite)" cmd /k "cd /d %REPO_ROOT% && npm run dev"

echo Waiting 4 seconds for servers to be ready...
timeout /t 4 /nobreak > nul

echo [3/3] Starting Cloudflare public tunnel...
echo Look for the 'https://...trycloudflare.com' link below!
echo ========================================================
"%CLOUDFLARED_BIN%" tunnel --url http://127.0.0.1:5173 --http-host-header localhost:5173
pause
