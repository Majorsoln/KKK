@echo off
:: ===========================================================================
::  STATUS — ukaguzi wa haraka bila kugusa data (salama wakati record inaendelea).
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
python -m src.data.cli config-hash
python -m src.data.cli check-freshness
