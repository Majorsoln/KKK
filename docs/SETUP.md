# ELITEFX — RUNBOOK: KUSIMAMISHA NA KUENDESHA (server yoyote)

> Kila kitu kinaendeshwa kwa **scripts za `scripts\`**. Amri za `python -m src.data.cli ...`
> zipo ndani yake — hutakiwi kuzikumbuka. Hati hii ni mazingira pekee; **vigezo vya maamuzi
> viko `config\data.yaml`** (§4).

```
MARA MOJA        scripts\setup.bat
KILA SIKU        scripts\catchup.bat   ->   scripts\record.bat
WAKATI WOWOTE    scripts\status.bat
```

---

## 1. MARA MOJA — mashine mpya

**Mahitaji:** Windows · MT5 imesakinishwa **na imeingia kwenye akaunti** · Python 3.11/3.12 ·
diski yenye nafasi (L0 ≈ 31GB; L1–L5 zinahitaji zaidi).

```cmd
cd C:\Users\<mtumiaji>\project
git clone https://github.com/Majorsoln/KKK.git elitefx-engine
cd elitefx-engine
scripts\setup.bat
```

`scripts\setup.bat` inafanya: `env.local.bat` (kutoka template) → venv → dependencies →
tests → muundo wa research → `check-mt5`. Tests zikifeli, **usiendelee**.

Kisha vitu **viwili** vya kujaza kwa mkono:

| Kitu | Iko wapi | Thamani |
|---|---|---|
| Njia ya terminal | `scripts\env.local.bat` → `ELITEFX_MT5_TERMINAL` | `where /r "C:\Program Files" terminal64.exe` |
| Kitambulisho cha broker | `config\data.yaml` → `recorder.broker_id` | jina fupi la kudumu, mf. `dukascopy-demo` |

Mwisho, hamisha data ya kihistoria (kama unayo) — diski ile ile ni rename ya papo hapo:
```cmd
move "<njia-ya-zamani>\ticks" "research\data\L0_raw\provenance=aggregator"
scripts\catchup.bat 2026-04-27
```

---

## 2. MT5 — nini hasa kinahitajika

**Terminal ikiwa imeingia kwenye akaunti, script inajiunganisha nayo. Huhitaji login wala
nywila popote.** `ELITEFX_MT5_LOGIN/PASSWORD/SERVER` ni **hiari** — zinajazwa tu kama
unataka script yenyewe ilazimishe login (server isiyo na mtu, au akaunti zaidi ya moja).

Kinachohitajika kila mara ni **njia ya terminal** (`ELITEFX_MT5_TERMINAL`). Bila yake:
`-10003 IPC initialize failed` — hata terminal ikiwa wazi mbele yako.

**MT5 inakubali CLIENT MMOJA kwa wakati.** `record`, `catchup` na `probe-history` zote
zinatumia terminal ile ile; mbili zikikimbia pamoja, ya pili inapata
`(-1, 'Terminal: Call failed')` — dalili inayofanana kabisa na "history haipo" ingawa data
ipo. Mfuatano: `Ctrl+C` → `catchup.bat` → `record.bat`. (`status.bat` haigusi MT5.)

Ukaguzi wakati wowote:
```cmd
python -m src.data.cli check-mt5
```
Inaonyesha: terminal · server (= **kitambulisho cha broker**; `terminal_info().company` **si**
broker — inaripoti msambazaji wa terminal) · `broker_id` · symbols zilizopo kati ya 12.

---

## 3. KILA SIKU

```cmd
scripts\catchup.bat          :: backfill -> hash-l0 -> verify-l0 -> check-freshness
scripts\record.bat           :: recorder inayoendelea (Ctrl+C kusimamisha)
```
Catch-up ndefu: `scripts\catchup.bat 2026-04-27`.

**Kikomo si siku moja bali kina cha history ya broker** (~siku 100 kwa Dukascopy demo).
`reconcile` inaziba mapengo yote ndani ya dirisha hilo, kwa hiyo laptop kuzimwa usiku,
wikendi au wiki hakupotezi chochote.

| Hatua | Inayohitajika |
|---|---|
| **Dev (T0–T6)** | endesha `record.bat` unapofanya kazi; usiache zaidi ya **~siku 60** bila kuiendesha |
| **Shadow/Live (T7+)** | Task Scheduler (§7) — kukosa siku kunaathiri trading, si utafiti tu |

`status.bat` ikirudisha `ALERT`, endesha `catchup.bat`. Kipimo ndicho kinachotawala, si hisia.

---

## 4. CONFIG — iko wapi na kwa nini

| Faili | Ina nini | Nani anahariri |
|---|---|---|
| `config\data.yaml` | **vigezo vyote vya data/features/labels/utafiti** — symbols, storage, recorder, reconcile, splits, vizingiti vya R0–R9 | **PD** |
| `config\risk.yaml` | vigezo vyote vya risk/cost vya engine (RCE) | **PD** |
| `scripts\env.local.bat` | sifa za **mashine hii** (njia ya MT5, storage root, login hiari) | mtumiaji wa mashine |

**Kanuni:** kigezo cha **maamuzi** hakiandikwi kwenye code wala scripts — kinakaa
`config\*.yaml` (lango G10). Scripts na env zinabeba **mazingira** pekee: njia na sifa za
kuingia. Ndiyo maana mashine ikibadilika, config haibadiliki.

`env.local.bat` **haipushwi kamwe** (`.gitignore` + lango G13, linalothibitisha pia kwamba
template inabaki tupu). Majina ya env yenyewe yanatoka `config\data.yaml`
(`recorder.mt5.*_env`) — yanaweza kubadilishwa hapo bila kugusa code.

Vigezo vinavyoulizwa mara nyingi:
```yaml
recorder:
  broker_id:  "dukascopy-demo"    # LAZIMA (§2.2) — bila hii recorder inakataa kuanza
  mt5:
    symbol_suffix: ""             # broker akiwa na "EURUSD.raw" -> ".raw"
  reconcile:
    lookback_days: 30             # dirisha la catchup ya default
storage:
  research_root: "${ELITEFX_RESEARCH_ROOT}"   # diski ikijaa, badilisha env HII PEKEE
```

---

## 5. MUUNDO WA DATA

```
research\                       (ndani ya repo; `research\data\` HAIPUSHWI — lango G11)
├── data\L0_raw\
│   ├── provenance=aggregator\symbol=<SYM>\year=\month=\[day=]\*.parquet
│   └── provenance=broker\symbol=<SYM>\date=YYYY-MM-DD\ticks.parquet
├── data\L1_clean … L5_datasets\     (T1 na kuendelea)
└── reports\quality · screening · ablation · calibration
```
`reports\` na `research\src\` **zinapushwa** (ushahidi wa kila awamu); data **haipushwi**.

---

## 6. MAKOSA NA SULUHISHO

| Dalili | Suluhisho |
|---|---|
| `-10003 IPC initialize failed` | `ELITEFX_MT5_TERMINAL` haijawekwa au njia si sahihi (§2) |
| `Call failed` **kwa siku unayojua ipo** | client wa pili wa MT5 — simamisha `record.bat` (§2) |
| `Call failed` kwa siku za zamani | terminal haina tick history hiyo → `probe-history`, au Strategy Tester (§8) |
| `broker_id haijawekwa` | jaza `config\data.yaml` → `recorder.broker_id` |
| `UKIUKAJI WA PROVENANCE` | broker/server imebadilika → §9 |
| `verify-l0 … missing=N` | partitions zilifutwa kwa idhini → `python -m src.data.cli hash-l0 --prune-missing --reason "..."` |
| `env.local.bat haipo` | `copy scripts\env.example.bat scripts\env.local.bat` |
| `ModuleNotFoundError: MetaTrader5` | endesha `scripts\setup.bat` (venv + extra `[mt5]`) |
| `set VAR=x` inakataa (PowerShell) | tumia cmd, au `$env:VAR = "x"` |
| git inafungua **vim** | `Esc` → `:wq` → Enter; kisha `git config --global core.editor notepad` |
| `git pull` inakataa: local changes | `git add config\data.yaml && git commit -m "..."` kisha pull |

---

## 7. PRODUCTION (T7 na kuendelea)

Task Scheduler → **Run whether user is logged on or not** · trigger **At startup** ·
program `<repo>\.venv\Scripts\python.exe` · arguments `-m src.data.cli record` ·
start in `<repo>` · **restart every 5 min on failure**. Env vars ziwe za system-level
(`setx /M`) au ziwekwe kwenye wrapper inayoita `scripts\env.local.bat` kwanza.

Task ya pili ya kila siku: `scripts\status.bat`. `ALERT` → simamisha task, endesha
`catchup.bat`, anza tena.

---

## 8. TICK HISTORY ISIYOFIKIKA

`probe-history` ikionyesha broker hana kina unachohitaji, MT5 inaweza kulazimishwa kupakua:
**View → Strategy Tester** (`Ctrl+R`) → EA yoyote → symbol + `M1` →
**Modelling: "Every tick based on real ticks"** → date range → **Start**. Angalia Journal
kwa `real ticks synchronized`, kisha `catchup.bat <tarehe>`. Journal ikisema hakuna real
ticks, huo ndio **mpaka halisi wa broker** — jibu la kudumu, linaloandikwa kwenye ripoti ya R0.

---

## 9. KUHAMIA SERVER NYINGINE

| Kitu | Hamisha? |
|---|---|
| `research\data\L0_raw\**` | **NDIYO** — haiwezi kuzalishwa upya |
| `manifest_l0.json` | ndiyo (au ijengwe upya kwa `catchup.bat`) |
| `research\data\L0_raw\_state\` | **hapana** — `reconcile` inajenga upya kutoka disk |
| repo · `.venv` · env | `git clone` + `scripts\setup.bat` |

Baada ya kuhamia: `scripts\setup.bat` → `scripts\catchup.bat`. Server mpya ikiunganishwa na
**broker tofauti**, recorder itasimama kwa `UKIUKAJI WA PROVENANCE` — hiyo ni kinga, si
hitilafu. Suluhisho: `ELITEFX_RESEARCH_ROOT` tofauti kwa broker mpya (inayopendekezwa), au
kufuta partitions za broker wa zamani kwa idhini ya PD.

---

**Nje ya wigo:** sheria za data/labels/features → `DATA_FEATURE_STANDARD.md` ·
risk/cost → `RISK_COST_ENGINE.md` · terms na rejista → `IMPLEMENTATION_PLAN.md`.
