@echo off
:: ===========================================================================
::  scripts\audit.bat  —  T1 / R0: ukaguzi kamili wa data (DF-05..DF-08, RS-03).
::      scripts\audit.bat                  -> symbols zote za config
::      scripts\audit.bat EURUSD,XAUUSD    -> symbols ulizotaja
::
::  HAUGUSI MT5 — ni salama hata `record.bat` ikiwa inaendelea.
::  Ni kazi ndefu (inasoma L0 nzima). Ikikatika, iendeshe tena: hatua 1 na 2
::  zina cache, kwa hiyo zinaendelea zilipoishia badala ya kuanza upya.
:: ===========================================================================
call "%~dp0_common.bat" || exit /b %ERRORLEVEL%
set "SYMS="
if not "%~1"=="" set "SYMS=--symbols %~1"

echo === 1/5  KALENDA — sessions kutoka DATA (RS-03) ===
python -m src.data.cli build-calendar %SYMS%

echo === 2/5  L1 — checks za ubora + quality_report.json (DF-05) ===
python -m src.data.cli check-l1 %SYMS%

echo === 3/5  TOLEO A vs TOLEO B baada ya normalization (RS-03) ===
python -m src.data.cli compare-variants

echo === 4/5  L2 — bars za TF 7 kutoka ticks (DF-06) ===
python -m src.data.cli build-l2 %SYMS%

echo === 5/5  SENTINEL + SPLITS — malango G1 na G2 (DF-08, DF-14) ===
python -m src.data.cli sentinel
python -m src.data.cli splits --out research\reports\quality\splits.json
