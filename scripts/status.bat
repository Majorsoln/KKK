@echo off
:: ===========================================================================
::  scripts\status.bat  —  ukaguzi wa haraka. HAUGUSI MT5, kwa hiyo ni salama
::  hata `record.bat` ikiwa inaendelea.
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
python -m src.data.cli config-hash
python -m src.data.cli check-freshness
