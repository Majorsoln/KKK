@echo off
:: ===========================================================================
::  RECORDER — huanza, hauishii (§2.2 ya DATA_FEATURE_STANDARD).
::  Inaziba mapengo yenyewe ikianza (reconcile), kisha inarekodi kila siku
::  ya trading inapofungwa.  Kusimamisha: Ctrl+C.
::
::  ONYO: usiendeshe pamoja na catchup.bat — MT5 inakubali client MMOJA
::  kwa wakati (§3.2b ya docs/SETUP.md).
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
echo === RECORDER inaanza (Ctrl+C kusimamisha) ===
python -m src.data.cli record
