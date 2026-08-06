@echo off
:: ===========================================================================
::  scripts\record.bat  —  RECORDER: huanza, hauishii (§2.2 ya standard).
::  Inaziba mapengo ikianza (reconcile), kisha inarekodi kila siku
::  ya trading inapofungwa.  Kusimamisha: Ctrl+C.
::
::  MT5 = client MMOJA: usiendeshe pamoja na catchup.bat.
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
echo === RECORDER (Ctrl+C kusimamisha) ===
python -m src.data.cli record
