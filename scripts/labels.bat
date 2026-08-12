@echo off
:: ===========================================================================
::  scripts\labels.bat  —  T2 / R1: setups + labels + ukaguzi (DF-20, DF-09..11,
::                          DF-21, K1-07, RS-04).
::      scripts\labels.bat                  -> symbols zote za config
::      scripts\labels.bat EURUSD,XAUUSD    -> symbols ulizotaja
::
::  HAUGUSI MT5. Ni kazi ya dakika ~40 (build ya kwanza ilikuwa 2,215s kwa
::  points 52,321). Ikikatika, iendeshe tena: hali ni ya (symbol, mwaka).
::
::  DF-20 LAZIMA iwe imesainiwa kabla — hii ni pre-registration (§4.3 sheria
::  5), si urasimu: label ikihesabiwa kabla ya sahihi, kila namba ya R1+ ni ya
::  baada ya ukweli.
::
::  Maandishi yote -> research\reports\r1\labels.log
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
set "SYMS="
if not "%~1"=="" set "SYMS=--symbols %~1"

set "LOG=research\reports\r1\labels.log"
if not exist "research\reports\r1" mkdir "research\reports\r1"
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change monitor-timeout-ac 15 >nul 2>&1
echo Kumbukumbu: %LOG%

:: Somo lile lile la audit.bat: code ya zamani + kazi ndefu = kazi iliyopotea,
:: na ripoti inayoonekana halali kabisa.
set "BEHIND="
set "BRANCH="
for /f %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%b"
if not "%BRANCH%"=="" (
  git fetch origin %BRANCH% >nul 2>&1
  for /f %%c in ('git rev-list HEAD..FETCH_HEAD --count 2^>nul') do set "BEHIND=%%c"
)
if not "%BEHIND%"=="" if not "%BEHIND%"=="0" (
  echo(
  echo   ONYO: branch yako iko NYUMA kwa commits %BEHIND%.
  echo   Simamisha kwa Ctrl+C, kisha:  git pull origin %BRANCH%
  echo(
  pause
)
echo(

echo === 1/3  SETUP-v1 — decision points + control (DF-20) ===
python -m src.data.cli detect-setups %SYMS% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo === 2/3  L4 — labels kwa path ya ticks (DF-09/10/11/21) ===
python -m src.data.cli build-labels %SYMS% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo(
echo === 3/3  R1 — VIGEZO VYOTE KWENYE JEDWALI MOJA ===
python -m src.data.cli r1-summary %SYMS% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

powercfg /change standby-timeout-ac 30 >nul 2>&1
