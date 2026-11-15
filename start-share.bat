@echo off
setlocal enabledelayedexpansion
title Civic Watch - Share Launcher

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

if exist "%SCRIPT_DIR%\package.json" (
    set "REPO_ROOT=%SCRIPT_DIR%"
) else if exist "%SCRIPT_DIR%\..\..\package.json" (
    pushd "%SCRIPT_DIR%\..\.."
    set "REPO_ROOT=%CD%"
    popd
) else (
    set "REPO_ROOT=%CD%"
)

cd /d "%REPO_ROOT%"

rem Execute the robust PowerShell launcher
if exist "%REPO_ROOT%\tools\share\start-share.ps1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\tools\share\start-share.ps1"
    if !errorlevel! neq 0 (
        echo.
        echo [ERROR] Share launcher exited with code !errorlevel!.
        pause
    )
    exit /b !errorlevel!
) else (
    echo [ERROR] tools\share\start-share.ps1 not found in %REPO_ROOT%!
    pause
    exit /b 1
)
