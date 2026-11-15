@echo off
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
pushd "%SCRIPT_DIR%\..\.."
set "REPO_ROOT=%CD%"
popd

if exist "%REPO_ROOT%\start-share.bat" (
    call "%REPO_ROOT%\start-share.bat" %*
) else (
    echo [ERROR] start-share.bat not found in repo root (%REPO_ROOT%).
    pause
)
