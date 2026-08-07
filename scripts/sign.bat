@echo off
:: ===========================================================================
::  scripts\sign.bat  —  SAHIHI YA PD (§0 ya docs\IMPLEMENTATION_PLAN.md).
::
::      scripts\sign.bat DF-05 VERIFIED --evidence research\reports\quality\quality_report.json ^
::                       --reason "partitions 25,498; kufeli 0.6%; nimekagua sababu zote"
::      scripts\sign.bat DF-20 APPROVED --reason "SETUP-v1 imekubaliwa KABLA ya labels"
::
::  Uamuzi: VERIFIED (inahitaji --evidence) · LESSON · APPROVED · REJECTED
::
::  SAHIHI HAIKAMILIKI HADI UCOMMIT. Commit yako ndiyo sahihi: jina lako la git,
::  muda wake, na mfuatano wake kwenye historia (lango G4/RS-01).
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
python -m src.governance.cli sign %*
