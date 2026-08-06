@echo off
:: ===========================================================================
::  scripts\env.example.bat  —  TEMPLATE ya sifa za MASHINE HII
::
::  NAKILI kuwa `scripts\env.local.bat` kisha ujaze:
::      copy scripts\env.example.bat scripts\env.local.bat
::
::  `env.local.bat` HAIPUSHWI (.gitignore + lango G13).
::  Hapa ni MAZINGIRA pekee. Vigezo vya MAAMUZI viko config\data.yaml.
:: ===========================================================================

:: --- LAZIMA: njia ya terminal ya MT5 ---------------------------------------
::  Bila hii: -10003 "MetaTrader 5 x64 not found" (MT5 hujitafuti yenyewe).
::  Tafuta kwa:  where /r "C:\Program Files" terminal64.exe
set ELITEFX_MT5_TERMINAL=C:\Program Files\MetaTrader 5\terminal64.exe

:: --- LAZIMA: storage ya research -------------------------------------------
set ELITEFX_RESEARCH_ROOT=%~dp0..\research
set ELITEFX_HOLDOUT_ROOT=%ELITEFX_RESEARCH_ROOT%\data\L5_datasets\holdout

:: --- HIARI: login la MT5 ----------------------------------------------------
::  TERMINAL IKIWA TAYARI IMEINGIA kwenye akaunti, ACHA HIZI TUPU — script
::  inaunganishwa na session iliyopo. Jaza TU kama unataka script yenyewe
::  ilazimishe login (server isiyo na mtu, au akaunti zaidi ya moja).
set ELITEFX_MT5_LOGIN=
set ELITEFX_MT5_PASSWORD=
set ELITEFX_MT5_SERVER=
