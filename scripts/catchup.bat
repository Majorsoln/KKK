@echo off
:: ===========================================================================
::  scripts\catchup.bat  —  kabla ya kuanza kazi, au baada ya mashine kuzimwa.
::      scripts\catchup.bat                -> dirisha la default (siku 30)
::      scripts\catchup.bat 2026-04-27     -> kuanzia tarehe uliyotaja
::
::  Simamisha record.bat kwanza (MT5 = client MMOJA).
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%

echo === 1/4  BACKFILL — siku zilizorukwa ===
if "%~1"=="" (python -m src.data.cli backfill) else (python -m src.data.cli backfill --from %~1)

echo === 2/4  HASH-L0 — partitions mpya zinaingia manifest (DF-01) ===
python -m src.data.cli hash-l0

echo === 3/4  VERIFY-L0 — uadilifu wa L0 (DF-01) ===
python -m src.data.cli verify-l0 --require-storage

echo === 4/4  FRESHNESS — siku ya trading bila data? (DF-04) ===
python -m src.data.cli check-freshness --json --out research\reports\quality\freshness.json
