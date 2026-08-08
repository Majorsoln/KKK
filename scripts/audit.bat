@echo off
:: ===========================================================================
::  scripts\audit.bat  —  T1 / R0: ukaguzi kamili wa data (DF-05..DF-08, RS-03).
::      scripts\audit.bat                  -> symbols zote za config
::      scripts\audit.bat EURUSD,XAUUSD    -> symbols ulizotaja
::
::  HAUGUSI MT5 — ni salama hata `record.bat` ikiwa inaendelea.
::  Ni kazi ya saa 9-13. Ikikatika, iendeshe tena: kila hatua inaendelea
::  ilipoishia (cache ya JSONL kwa 1-2, `_l2_state.json` kwa 4).
::
::  Maandishi yote yanaandikwa `research\reports\quality\audit.log` — dirisha
::  likifungwa au PC ikizimika, ushahidi haupotei.
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
set "SYMS="
if not "%~1"=="" set "SYMS=--symbols %~1"

:: PC isilale wala isizime skrini wakati wa kazi ndefu (AC pekee; betri
:: haiguswi). Thamani za awali zinarudishwa mwishoni.
set "LOG=research\reports\quality\audit.log"
if not exist "research\reports\quality" mkdir "research\reports\quality"
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change monitor-timeout-ac 15 >nul 2>&1
echo Kumbukumbu: %LOG%
echo(

echo === 1/6  KALENDA — sessions kutoka DATA (RS-03) ===
python -m src.data.cli build-calendar %SYMS% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo === 2/6  L1 — checks za ubora + quality_report.json (DF-05) ===
python -m src.data.cli check-l1 %SYMS% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo === 2b/6 VIZINGITI — mgawanyo halisi wa L1 (chagua kabla ya kuondoa data) ===
python -m src.data.cli quality-stats 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo === 3a/6 TOLEO A vs TOLEO B baada ya normalization (RS-03) ===
python -m src.data.cli compare-variants 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo === 3b/6 AGGREGATOR vs BROKER — siku zinazopishana (R0, spec 2.2) ===
python -m src.data.cli compare-provenance %SYMS% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo === 4/6  L2 — bars za TF 7 kutoka ticks (DF-06) ===
python -m src.data.cli build-l2 %SYMS% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo === 5/6  SENTINEL + SPLITS — malango G1 na G2 (DF-08, DF-14) ===
python -m src.data.cli sentinel 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"
python -m src.data.cli splits --out research\reports\quality\splits.json 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo(
echo === R0 — VIGEZO VYOTE KWENYE JEDWALI MOJA ===
python -m src.data.cli r0-summary 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -Append '%LOG%'"

echo(
echo === HALI ===
python -m src.data.cli audit-status
powercfg /change standby-timeout-ac 30 >nul 2>&1
