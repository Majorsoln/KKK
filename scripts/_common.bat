@echo off
:: Inaandaa mazingira kwa script yoyote: repo root + env + venv.
cd /d "%~dp0.."
if not exist "scripts\env.local.bat" (
    echo.
    echo   HITILAFU: scripts\env.local.bat haipo.
    echo   Tengeneza kwa:  copy scripts\env.example.bat scripts\env.local.bat
    echo   kisha ujaze login/password/server.
    echo.
    exit /b 2
)
call "scripts\env.local.bat"
if not exist ".venv\Scripts\activate.bat" (
    echo   HITILAFU: .venv haipo. Ona docs\SETUP.md §2.
    exit /b 2
)
call ".venv\Scripts\activate.bat"
exit /b 0
