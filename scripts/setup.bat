@echo off
:: ===========================================================================
::  scripts\setup.bat  —  MARA MOJA kwa kila mashine.
::  venv -> dependencies -> tests -> muundo wa research -> ukaguzi wa MT5.
:: ===========================================================================
cd /d "%~dp0.."

if not exist "scripts\env.local.bat" (
    echo === Inatengeneza scripts\env.local.bat kutoka template ===
    copy /y "scripts\env.example.bat" "scripts\env.local.bat" >nul
    echo     Ihariri sasa kama njia ya MT5 si ya kawaida, kisha endesha tena.
)

echo === 1/5  venv ===
if not exist ".venv\Scripts\activate.bat" python -m venv .venv
call ".venv\Scripts\activate.bat"

echo === 2/5  dependencies ===
python -m pip install --upgrade pip >nul
pip install -e ".[dev,mt5]"

echo === 3/5  tests (zikifeli, USIENDELEE) ===
python -m pytest -q || exit /b 1

echo === 4/5  muundo wa research ===
call "scripts\env.local.bat"
python -m src.data.cli init-research

echo === 5/5  ukaguzi wa MT5 (terminal iwe imefunguliwa na imeingia) ===
python -m src.data.cli check-mt5

echo.
echo Tayari. Kila siku:  scripts\catchup.bat  kisha  scripts\record.bat
