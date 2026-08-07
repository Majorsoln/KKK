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

echo === 1/6  KALENDA — sessions kutoka DATA (RS-03) ===
python -m src.data.cli build-calendar %SYMS%

echo === 2/6  L1 — checks za ubora + quality_report.json (DF-05) ===
python -m src.data.cli check-l1 %SYMS%

echo === 2b/6 VIZINGITI — mgawanyo halisi wa L1 (chagua kabla ya kuondoa data) ===
python -m src.data.cli quality-stats

echo === 3a/6 TOLEO A vs TOLEO B baada ya normalization (RS-03) ===
python -m src.data.cli compare-variants

echo === 3b/6 AGGREGATOR vs BROKER — siku zinazopishana (R0, spec 2.2) ===
python -m src.data.cli compare-provenance %SYMS%

echo === 4/6  L2 — bars za TF 7 kutoka ticks (DF-06) ===
python -m src.data.cli build-l2 %SYMS%

echo === 5/6  SENTINEL + SPLITS — malango G1 na G2 (DF-08, DF-14) ===
python -m src.data.cli sentinel
python -m src.data.cli splits --out research\reports\quality\splits.json
