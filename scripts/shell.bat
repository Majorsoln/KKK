@echo off
:: ===========================================================================
::  scripts\shell.bat  —  ANDAA DIRISHA la cmd kwa amri za mkono.
::
::      scripts\shell.bat
::      python -m src.data.cli audit-status
::
::  Scripts nyingine (audit/catchup/record/status/sign) hujiandaa zenyewe.
::  Hii ni kwa pale unapotaka kuendesha `python -m ...` moja kwa moja —
::  mfano dirisha lako la awali likifungwa.
::
::  Inaweka: njia ya repo · env kutoka scripts\env.local.bat · venv.
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%

echo(
echo   Dirisha liko tayari.
echo     repo   : %CD%
echo     storage: %ELITEFX_RESEARCH_ROOT%
echo(
echo   Amri za haraka:
echo     python -m src.data.cli audit-status      ^:^: hatua za R0 zilizokamilika
echo     python -m src.data.cli quality-stats     ^:^: mgawanyo + vizingiti
echo(
