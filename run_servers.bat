@echo off
REM RetailOps MCP Server Runner
title RetailOps MCP Server Orchestrator

echo ==================================================
echo         RetailOps MCP Server Launcher
echo ==================================================
echo.

REM Check if python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] python command not found in system PATH.
    echo Please install Python 3.11+ and make sure it is added to PATH.
    echo.
    pause
    exit /b 1
)

python "%~dp0run_servers.py"

echo.
echo ==================================================
echo Servers stopped.
echo ==================================================
pause
