@echo off
:: ===========================================================================
::  ELITEFX — env za mashine hii.  NAKILI faili hii kuwa `env.local.bat`
::  na ujaze thamani zako.  `env.local.bat` HAIPUSHWI (.gitignore) — ina nywila.
::
::      copy scripts\env.example.bat scripts\env.local.bat
::
::  Hii ni ya MAZINGIRA pekee. Vigezo vya maamuzi viko config/data.yaml.
:: ===========================================================================

:: --- MT5 (§3.2 ya docs/SETUP.md) ---
set ELITEFX_MT5_TERMINAL=C:\Program Files\MetaTrader 5\terminal64.exe
set ELITEFX_MT5_LOGIN=
set ELITEFX_MT5_PASSWORD=
set ELITEFX_MT5_SERVER=

:: --- storage ya research (§4) ---
set ELITEFX_RESEARCH_ROOT=%~dp0..\research
set ELITEFX_HOLDOUT_ROOT=%ELITEFX_RESEARCH_ROOT%\data\L5_datasets\holdout
