# ELITEFX — RUNBOOK YA KUSIMAMISHA MFUMO (server yoyote)

> **Hadhi:** hati ya utekelezaji, si spec. Inaeleza jinsi ya kusimamisha tabaka la data
> (`src/data/`) kwenye mashine mpya — development, VPS ya kurekodi, au server ya live.
> Kila hatua hapa **imethibitishwa kwa vitendo** wakati wa T0 (2026-08-05/06), pamoja na
> makosa yaliyotokea njiani (§7).
>
> Vigezo vyote vya maamuzi viko `config/data.yaml` na `config/risk.yaml`. Hati hii
> **haina** kigezo chochote kipya — inaeleza mazingira tu.

---

## 0. MUHTASARI — hatua saba

```
1. Mahitaji ya mashine        →  Windows + MT5 + Python 3.11/3.12
2. Repo + venv + dependencies →  git clone · pip install -e ".[dev,mt5]"
3. Environment variables      →  MT5 (4) + storage (2)
4. Storage ya research        →  init-research · L0 inaingia wapi
5. Kitambulisho cha broker    →  config: recorder.broker_id
6. Kuanzisha                  →  hash-l0 · verify-l0 · backfill · record
7. Production                 →  Task Scheduler + ukaguzi wa kila siku
```

---

## 1. MAHITAJI YA MASHINE

| Kitu | Sharti | Sababu |
|---|---|---|
| OS | **Windows** (10/11 au Server) | `MetaTrader5` ya Python ni Windows-only. Linux inahitaji Wine — haijajaribiwa. |
| MT5 terminal | imesakinishwa **na imeingia** kwenye akaunti | recorder inaunganishwa na terminal, si na broker moja kwa moja |
| Akaunti | demo au live ya broker unayemtaka | demo inatosha kwa kurekodi ticks |
| Python | **3.11 au 3.12** | `requires-python = ">=3.11"` |
| Diski | L0 ya sasa ≈ 31GB; L1–L5 zinahitaji **zaidi** | ona §4.3 |
| Mtandao | thabiti | recorder inavuta kila dakika |

**Mashine ikizimwa, `reconcile` inaziba mapengo ikianza tena** (§6.4). Kikomo si siku moja
bali **kina cha history ya broker** (~siku 100 kwa Dukascopy demo). Ona §8 kwa tofauti kati
ya dev na production.

---

## 2. REPO + VENV + DEPENDENCIES

```cmd
cd C:\Users\<mtumiaji>\project
git clone https://github.com/Majorsoln/KKK.git elitefx-engine
cd elitefx-engine

python -m venv .venv
.venv\Scripts\activate.bat
pip install -e ".[dev,mt5]"
pytest
```

**Unatarajia:** tests zote kijani. Zikifeli hapa, **usiendelee** — mazingira si sahihi.

> `research/` inakaa **ndani ya repo** (§9 ya `DATA_FEATURE_STANDARD.md`), lakini
> `research/data/` iko kwenye `.gitignore` — data haipushwi kamwe (lango G11).
> Usiweke repo ndani ya folda ya data; ziwe ndugu, si mzazi na mtoto.

---

## 3. ENVIRONMENT VARIABLES

### 3.1 Syntax inatofautiana kwa shell — kosa la kawaida

| Shell | Kutambua | Session hii | Kudumu |
|---|---|---|---|
| **cmd** | `C:\...>` | `set VAR=thamani` (bila quotes) | `setx VAR "thamani"` |
| **PowerShell** | `PS C:\...>` | `$env:VAR = "thamani"` | `setx VAR "thamani"` |

`setx` inaanza kufanya kazi kwenye **process mpya** — fungua terminal mpya baada yake.
**Nywila usiiweke `setx`** (inaandikwa kwenye registry).

### 3.2 Vigezo vinavyohitajika

```cmd
:: --- MT5 ---
set ELITEFX_MT5_TERMINAL=C:\Program Files\MetaTrader 5\terminal64.exe
set ELITEFX_MT5_LOGIN=<namba ya akaunti>
set ELITEFX_MT5_PASSWORD=<nywila>
set ELITEFX_MT5_SERVER=<server, mf. Dukascopy-demo-mt5-1>

:: --- storage ---
set ELITEFX_RESEARCH_ROOT=C:\Users\<mtumiaji>\project\elitefx-engine\research
set ELITEFX_HOLDOUT_ROOT=%ELITEFX_RESEARCH_ROOT%\data\L5_datasets\holdout
```

**`ELITEFX_MT5_TERMINAL` ni ya LAZIMA.** Bila yake MT5 hujitafuti yenyewe na unapata
`-10003 IPC initialize failed, MetaTrader 5 x64 not found` — hata terminal ikiwa wazi.
Tafuta njia halisi:
```cmd
where /r "C:\Program Files" terminal64.exe
```

Majina ya env yenyewe yanatoka `config/data.yaml` (`recorder.mt5.*_env`) — yanaweza
kubadilishwa hapo bila kugusa code.

### 3.2b MT5 inakubali CLIENT MMOJA kwa wakati (imegunduliwa T0)

`record`, `backfill` na `probe-history` zote zinaunganishwa na terminal ile ile. Mbili
zikikimbia kwa pamoja, ya pili inapata `(-1, 'Terminal: Call failed')` — dalili
inayofanana kabisa na "history haipo", ingawa data ipo.

**Kanuni:** simamisha `record` kabla ya kuendesha `backfill` au `probe-history`, kisha
uianzishe tena. Ukiona `Call failed` kwa siku unayojua ipo kwenye disk yako, hicho ndicho
kinachotokea.

### 3.3 Uthibitisho wa muunganisho

```cmd
python -c "import MetaTrader5 as mt5; ok=mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=15000); a=mt5.account_info(); print('ok:', ok, mt5.last_error()); print('server:', a.server if a else None); print('symbols:', len(mt5.symbols_get() or [])); mt5.shutdown()"
```

**Muhimu:** `account_info().server` ndicho kitambulisho cha broker.
`terminal_info().company` **si broker** — inaripoti msambazaji wa terminal
("MetaQuotes Ltd." hata kwa akaunti ya Dukascopy). Kosa hili lilitokea T0.

Thibitisha symbols zote 12 zipo kwa majina yale yale:
```cmd
python -c "import MetaTrader5 as mt5; mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=15000); want=['EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD','NZDUSD','EURGBP','EURJPY','EURCHF','GBPJPY','XAUUSD']; have={s.name for s in (mt5.symbols_get() or [])}; print('HAZIPO:', [w for w in want if w not in have]); mt5.shutdown()"
```
Broker akiwa na kiambishi (`EURUSD.raw`), weka `recorder.mt5.symbol_suffix` kwenye config.

---

## 4. STORAGE YA RESEARCH

### 4.1 Simamisha muundo
```cmd
python -m src.data.cli init-research
```
Inatengeneza `data/L0_raw … L5_datasets`, `reports/*`, `src/` + README (§9).

### 4.2 L0 inaingiaje

```
<RESEARCH_ROOT>\data\L0_raw\
├── provenance=aggregator\symbol=<SYM>\year=\month=\[day=]\*.parquet   (kihistoria)
└── provenance=broker\symbol=<SYM>\date=YYYY-MM-DD\ticks.parquet       (recorder)
```

Kuhamisha data iliyopo (diski ile ile = rename, papo hapo):
```cmd
move "<njia-ya-zamani>\ticks" "<RESEARCH_ROOT>\data\L0_raw\provenance=aggregator"
```
Diski nyingine bila kunakili:
```cmd
cmd /c mklink /J "<RESEARCH_ROOT>\data\L0_raw\provenance=aggregator" "<njia-ya-zamani>"
```

### 4.3 Nafasi ya diski
L0 ya sasa ≈ 31GB. **L1–L5 zinahitaji zaidi.** Diski ikijaa, badilisha
`ELITEFX_RESEARCH_ROOT` pekee — `reports/` na `src/` zinabaki kwenye repo, data inahamia
bila kugusa code wala config nyingine.

---

## 5. KITAMBULISHO CHA BROKER (§2.2)

`config/data.yaml`:
```yaml
recorder:
  broker_id:  "dukascopy-demo"     # LAZIMA — jina fupi la kudumu
```

**Ni ya lazima.** Bila yake recorder inakataa kuanza: partition isiyojua broker wake
haiwezi kutumika kwenye attestation, kwa sababu spread na fills ni za broker husika.

Kando na lebo yako, kila partition inabeba **`broker_server`** kiotomatiki kutoka MT5.
Ukibadilisha broker (au akaunti ikahamia server nyingine) bila kubadilisha L0,
recorder **inasimama** na `UKIUKAJI WA PROVENANCE`. Suluhisho:

- **L0 root tofauti kwa broker mpya** (`ELITEFX_RESEARCH_ROOT` nyingine) — inayopendekezwa; au
- kufuta partitions za broker wa zamani **kwa idhini ya PD**, kisha:
  ```cmd
  rmdir /s /q "<L0>\provenance=broker"
  rmdir /s /q "<L0>\_state"
  python -m src.data.cli hash-l0 --prune-missing --reason "<sababu + idhini ya PD>"
  ```

---

## 6. KUANZISHA (mfuatano)

### 6.1 Fingerprint + hashes
```cmd
python -m src.data.cli config-hash
python -m src.data.cli hash-l0
```
Mara ya kwanza inasoma L0 nzima (dakika chache). Baadaye ni **resume** — sekunde chache.

### 6.2 Lango la uadilifu
```cmd
python -m src.data.cli verify-l0 --require-storage
echo %ERRORLEVEL%
```
Hii **haiwezi kuruka** partition yoyote (inasoma GB 31 → ~6 min). Unatarajia
`PASS · changed=0 missing=0` na exit `0`.

### 6.3 Ziba mapengo kabla ya kuanza kurekodi
```cmd
python -m src.data.cli backfill --dry-run --from <YYYY-MM-DD>
python -m src.data.cli backfill --from <YYYY-MM-DD>
```
`--dry-run` inaonyesha bila kuvuta. Ikiwa kubwa: `--max-days 200` na kurudia
(inaendelea pale ilipoishia — ukweli ni disk, si state).

`no_ticks` **si kufeli**: ni broker kutokuwa na ticks za siku hiyo.

**Kabla ya backfill ndefu, pima kina cha history kwanza** — vinginevyo unaweza kutumia saa
nyingi kwenye maombi yanayofeli (kila kufeli ni ~sekunde 100 za timeout ya MT5):
```cmd
python -m src.data.cli probe-history --symbol EURUSD --from 2026-01-01
```
Binary search inajibu kwa maombi <10 badala ya mamia, na **inapima siku za trading pekee**
(wikendi/likizo hazina ticks kihalali — kuzipima kunatoa jibu la uongo). Kisha backfill
kuanzia siku iliyorudishwa (`earliest_available`).

Ripoti ikisema *"history inafika angalau mwanzo wa dirisha ulilotoa"*, mpaka halisi uko
nyuma zaidi — rudia kwa dirisha pana (`--from` ya zamani zaidi).

#### Kulazimisha MT5 ipakue tick history (Strategy Tester)

MT5 haihifadhi tick history yote; haina kitufe cha "download ticks". Njia rasmi ni
**Strategy Tester**:

1. MT5 → **View → Strategy Tester** (`Ctrl+R`)
2. Expert: yoyote (mf. `Examples\MACD\MACD Sample`) — matokeo yake hayana maana kwetu
3. Symbol + Period (`M1`)
4. **Modelling: "Every tick based on real ticks"** ← ndicho kinacholazimisha upakuaji
5. Date range: kipindi unachokitaka
6. **Start**; angalia **Journal** kwa `real ticks synchronized`

Ticks zinakaa `...\Terminal\<ID>\bases\<server>\ticks\<SYMBOL>\`, kisha
`copy_ticks_range` (na `backfill`) zinaweza kuzisoma. Rudia kwa kila symbol.

Journal ikisema hakuna real ticks kwa kipindi hicho, huo ndio **mpaka halisi wa broker** —
jibu la kudumu, si tatizo la kutatuliwa. Andika mpaka huo kwenye ripoti ya R0.

Backfill ina **circuit breaker**: kufeli 5 mfululizo kunasimamisha kazi
(`--max-consecutive-failures`), kwa sababu kufeli mfululizo ni jibu (mpaka wa history),
si hali ya kurudia.

### 6.4 Anzisha recorder
```cmd
python -m src.data.cli record
```
`written=0` kwenye polls nyingi ni **hali sahihi ya kupumzika** — siku ya sasa bado
haijafungwa. Recorder ni huduma isiyoisha (§2.2); haipaswi kutoka.

Inajitibu yenyewe: `reconcile` inakimbia inapoanza na kila polls 60 (config
`recorder.reconcile`), kwa hiyo siku zilizorukwa zinazibwa bila mtu kukumbuka.

### 6.5 Ukaguzi wa mwisho
```cmd
python -m src.data.cli check-freshness --json --out research\reports\quality\freshness.json
python -c "import pyarrow.parquet as pq,glob; f=sorted(glob.glob(r'research\data\L0_raw\provenance=broker\**\*.parquet',recursive=True))[-1]; m=pq.ParquetFile(f).metadata.metadata; print({k.decode():v.decode() for k,v in m.items() if k.decode() in ('broker_id','broker_server','provenance','rows')})"
```

---

## 7. MAKOSA HALISI NA SULUHISHO (yaliyotokea T0)

| Dalili | Chanzo | Suluhisho |
|---|---|---|
| `-10003 IPC initialize failed` | `ELITEFX_MT5_TERMINAL` haijawekwa | weka njia kamili ya `terminal64.exe` |
| `mt5.initialize` inaning'inia sekunde 60 | default timeout | `recorder.mt5.timeout_ms` (15000) — ipo tayari |
| `company: MetaQuotes Ltd.` ukidhani ni broker | ni msambazaji wa terminal | tumia `account_info().server` |
| `ModuleNotFoundError: MetaTrader5` | venv haijaanzishwa au extra `[mt5]` haikuwekwa | `.venv\Scripts\activate.bat` + `pip install -e ".[dev,mt5]"` |
| `Set-Variable: A positional parameter...` | `set VAR=x` ndani ya PowerShell | tumia `$env:VAR = "x"` |
| `broker_id haijawekwa` — recorder inakataa | guard ya §2.2 | jaza `recorder.broker_id` |
| `UKIUKAJI WA PROVENANCE` | broker/server imebadilika | §5 hapo juu |
| `copy_ticks_range: (-1, 'Terminal: Call failed')` **kwa siku unayojua ipo** | client wa pili wa MT5 (mf. `record` bado inaendelea) | simamisha `record` kwanza (§3.2b) |
| `copy_ticks_range: (-1, 'Terminal: Call failed')` kwa siku za zamani | terminal haina tick history hiyo | `fetch_retries` (2); ikiendelea, pakua kwa **Strategy Tester** (§6.3) au ukubali mpaka wa broker |
| backfill inafeli kila siku, ~100s kila moja | kina cha history hakitoshi | circuit breaker inasimamisha baada ya kufeli 5 mfululizo; pima kwanza kwa `probe-history` |
| `verify-l0: manifest haipo` | `hash-l0` haijakamilika | endesha `hash-l0` hadi mwisho |
| `verify-l0 ... missing=N` | partitions zilifutwa kwa idhini | `hash-l0 --prune-missing --reason "..."` |
| git inafungua **vim** kwenye merge | editor default | `Esc` → `:wq` → Enter; kisha `git config --global core.editor notepad` |
| `git pull` inakataa: local changes | config imehaririwa | `git add config/data.yaml && git commit -m "..."` kisha pull |

---

## 8. KUENDESHA RECORDER — dev dhidi ya production

**Kikomo halisi si siku moja; ni kina cha history ya broker.** Dukascopy demo inatoa
~siku 100 zinazosogea mbele (§2.2 ya standard). `reconcile` (on-start + kila polls 60)
inaziba **mapengo yote ndani ya dirisha hilo**. Kwa hiyo:

| Hatua | Inayohitajika | Sababu |
|---|---|---|
| **Dev (T0–T6)** | endesha `record` unapofanya kazi; usiache zaidi ya **~siku 60** bila kuiendesha | reconcile inaziba kilichokosekana; margin dhidi ya kikomo cha ~100 |
| **Shadow/Live (T7+)** | Task Scheduler + restart-on-failure | kukosa siku kunaathiri trading na calibration ya P(fill), si utafiti tu |

Kwenye dev, **kipimo ndicho kinachotawala, si hisia**: `check-freshness` ikirudisha `ALERT`,
endesha `backfill`. Laptop kuzimwa usiku au wikendi hakupotezi chochote.

### 8.1 Production — recorder kama huduma (T7 na kuendelea)

Dirisha la cmd si production: likifungwa, kurekodi kunasimama.

**Task Scheduler:**
1. Create Task → **Run whether user is logged on or not** · **Run with highest privileges**
2. Triggers → **At startup** (+ **Repeat** kama unataka bima ya ziada)
3. Actions → Start a program:
   - Program: `C:\...\elitefx-engine\.venv\Scripts\python.exe`
   - Arguments: `-m src.data.cli record`
   - Start in: `C:\...\elitefx-engine`
4. Settings → **If the task fails, restart every 5 minutes**, attempts 999
5. Env vars: ziwe za **system-level** (`setx /M`) au ziwekwe kwenye wrapper `.bat`
   inayoziweka kabla ya `python`

**Ukaguzi** (kila siku production; kila unapoanza kazi dev):
```cmd
python -m src.data.cli check-freshness --json --out research\reports\quality\freshness.json
python -m src.data.cli verify-l0
```
`check-freshness` ikirudisha `ALERT`, siku ya trading imepita bila data — chunguza mara moja
(§2.2: kila siku isiyorekodiwa ni data iliyopotea bure).

---

## 9. KUHAMIA SERVER NYINGINE

Kinachohitaji kuhamishwa ni **data pekee**; kila kitu kingine kinajengwa upya.

| Kitu | Hamisha? | Sababu |
|---|---|---|
| `research/data/L0_raw/**` | **NDIYO** | data haiwezi kuzalishwa upya |
| `manifest_l0.json` | ndiyo (au ijengwe upya kwa `hash-l0`) | rekodi rasmi ya hashes |
| `research/data/L0_raw/_state/` | **HAPANA — si lazima** | `reconcile` inajenga upya kutoka disk |
| repo (`src/`, `config/`, `docs/`) | `git clone` | ndiyo chanzo cha ukweli |
| `.venv` | hapana | jenga upya (§2) |
| env vars | zisimikwe upya (§3) | sifa ni za mashine |

**Sifa ya muhimu:** kwa sababu `reconcile` inatumia **disk** kama ukweli (si state),
kupoteza `_state` **hakupotezi data**. Server mpya inaanza, inagundua zilizokosekana,
inaziba, na inaendelea.

**Baada ya kuhamia — kagua kwa mpangilio huu:**
```cmd
pytest
python -m src.data.cli verify-l0 --require-storage      :: data imefika salama?
python -m src.data.cli backfill --dry-run               :: nini kilikosekana wakati wa uhamiaji?
python -m src.data.cli backfill
python -m src.data.cli record
```

**Onyo:** server mpya ikiunganishwa na **broker/server tofauti**, recorder itasimama kwa
`UKIUKAJI WA PROVENANCE` — hiyo ni kinga, si hitilafu (§5).

---

## 10. NJE YA WIGO
Vigezo vya risk/cost → `config/risk.yaml` + `docs/RISK_COST_ENGINE.md`.
Sheria za data/labels/features → `docs/DATA_FEATURE_STANDARD.md`.
Terms na rejista ya utekelezaji → `docs/IMPLEMENTATION_PLAN.md`.
