@echo off
title SYSTEM MONITOR Widget
set PYTHON_EXE=C:\Users\evoyt\AppData\Local\hermes\tools\python-3.14.9+20261021-win32-x64\python3.exe
set SCRIPT_PATH=G:\Hermes\CODING\WidgetHardwareStats\monitor.py

echo [INFO] Starting widget...

"%PYTHON_EXE%" "%SCRIPT_PATH%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Widget started successfully.
    echo [TIP] Hotkey: Ctrl+Alt+H to toggle visibility.
) else (
    echo.
    echo [ERROR] Failed to start. Error code: %ERRORLEVEL%
    pause
)
