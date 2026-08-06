@echo off
:: ===========================================================================
::  CATCH-UP — endesha baada ya mashine kuzimwa au kabla ya kuanza kazi.
::  Simamisha record.bat kwanza (MT5 = client mmoja, §3.2b).
::
::      scripts\catchup.bat                 -> dirisha la default (siku 30)
::      scripts\catchup.bat 2026-04-27      -> kuanzia tarehe uliyotaja
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%

echo === 1/4  BACKFILL: kuziba siku zilizorukwa ===
if "%~1"=="" (
    python -m src.data.cli backfill
) else (
    python -m src.data.cli backfill --from %~1
)

echo === 2/4  HASH-L0: partitions mpya zinaingia manifest ===
python -m src.data.cli hash-l0

echo === 3/4  VERIFY-L0: uadilifu wa L0 (DF-01) ===
python -m src.data.cli verify-l0 --require-storage

echo === 4/4  FRESHNESS: siku ya trading bila data? (DF-04) ===
python -m src.data.cli check-freshness --json --out research\reports\quality\freshness.json
