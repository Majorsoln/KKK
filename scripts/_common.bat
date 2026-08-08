@echo off
:: scripts\_common.bat — repo root + env + venv kwa script yoyote. Haitwi peke yake.
cd /d "%~dp0.."
if not exist "scripts\env.local.bat" (
    echo.
    echo   scripts\env.local.bat haipo. Tengeneza kwa:
    echo       copy scripts\env.example.bat scripts\env.local.bat
    echo   kisha thibitisha ELITEFX_MT5_TERMINAL. Ona docs\SETUP.md §1.
    echo.
    exit /b 2
)
call "scripts\env.local.bat"
if not exist ".venv\Scripts\activate.bat" (
    echo   .venv haipo. Endesha kwanza:  scripts\setup.bat
    exit /b 2
)
call ".venv\Scripts\activate.bat"

:: UTF-8 kwa console NA kwa Python. Bila hizi, output ikielekezwa kwenye pipe
:: (mfano log ya `Tee-Object`) inarudi kwa cp1252 ya locale, na herufi kama
:: `->`/`>=` zinaanguka amri kwa UnicodeEncodeError baada ya kazi kumalizika.
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
exit /b 0
