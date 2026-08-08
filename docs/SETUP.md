# ELITEFX — RUNBOOK: KUSIMAMISHA NA KUENDESHA (server yoyote)

> Kila kitu kinaendeshwa kwa **scripts za `scripts\`**. Amri za `python -m src.data.cli ...`
> zipo ndani yake — hutakiwi kuzikumbuka. Hati hii ni mazingira pekee; **vigezo vya maamuzi
> viko `config\data.yaml`** (§4).

```
MARA MOJA        scripts\setup.bat
KILA SIKU        scripts\catchup.bat   ->   scripts\record.bat
WAKATI WOWOTE    scripts\status.bat
UKAGUZI (T1)     scripts\audit.bat
SAHIHI YA PD     scripts\sign.bat      (§10)
DIRISHA JIPYA    scripts\shell.bat     (kabla ya `python -m ...` kwa mkono)
```

> **Dirisha jipya la cmd halina env wala venv.** Scripts za `scripts\*.bat` hujiandaa zenyewe,
> lakini `python -m src.data.cli ...` moja kwa moja haitajiandaa. Endesha `scripts\shell.bat`
> mara moja kwenye kila dirisha jipya — hii ndiyo sababu ya
> `HITILAFU: storage.reports_root inategemea environment isiyowekwa`.

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

### 3.1 UKAGUZI WA DATA (T1 / R0)

```cmd
scripts\audit.bat                    :: symbols zote
scripts\audit.bat EURUSD,XAUUSD      :: symbols chache (jaribio la haraka)
```

Haigusi MT5 — ni salama hata `record.bat` ikiwa inaendelea. Hatua tano, kwa **mfuatano huu**
(ya 2 inahitaji kalenda ya ya 1; ya 5 inahitaji bars za ya 4):

| # | Amri iliyo ndani | Inatoa nini |
|---|---|---|
| 1 | `build-calendar` | `session_calendar.json` + `calendar_vs_assumed.json` (pamoja na kalenda kwa **kila toleo la schema kando**) |
| 2 | `check-l1` | `quality_report.json` — checks kwa symbol/mwaka, vizingiti **vyote** vilivyotumika, wigo wa miaka dhidi ya `min_years` |
| 2b | `quality-stats` | `threshold_study.json` — mgawanyo halisi + kizingiti gani kingefelisha ngapi |
| 3a | `compare-variants` | `variant_comparison.json` (Toleo A ↔ B baada ya normalization) |
| 3b | `compare-provenance` | `provenance_comparison.json` — **spread ya broker dhidi ya ya aggregator** kwa siku zinazopishana |
| 4 | `build-l2` | `data\L2_bars\symbol=<SYM>\tf=<TF>\bars.parquet` (TF 7 + `n_m1_bars`) |
| 5 | `sentinel` + `splits` | malango G1 na G2; `splits.json` |
| 6 | `r0-summary` | **vigezo vyote vya R0 kwenye jedwali moja** — ndio unachopitia kabla ya sahihi |

Hatua **3b** ndiyo yenye uzito mkubwa zaidi kwa fedha: models zinafunzwa kwa data ya aggregator
lakini zitafanya biashara kwa feed ya broker, na **spread ndiyo gharama** (§3.1 ya RCE). Uwiano
`broker/aggregator` ukiwa juu ya 1, kila EV iliyohesabiwa kwa data ya kihistoria ni ya matumaini
kwa kiasi hicho. Siku zinazopishana (2026-04-27…04-30) ndizo pekee zinazoruhusu ulinganisho wa
haki — siku ile ile, symbol ile ile, soko lile lile.

Baada ya hatua ya 2, **kabla ya kuondoa partition yoyote**:
```cmd
python -m src.data.cli quality-stats
```
Inasoma `quality_report.json` iliyoshaandikwa (haisomi parquet tena, ni sekunde chache) na
kuonyesha kwa kila ukaguzi: thamani zilivyotawanyika (p1…p99), kizingiti cha sasa kinafelisha
ngapi, na **kizingiti gani kingefelisha ngapi**. Ukaguzi ukifelisha nusu ya data, kwa kawaida
kipimo ndicho kibaya — si data. Chagua kizingiti hapo, kiandike `config\data.yaml` → `quality:`,
kisha `check-l1` tena (cache inajitupa yenyewe kizingiti kikibadilika).

**Ni kazi ya masaa 9–13** kwa symbols zote 12 (partitions 25,498 · ticks bilioni 3.4). Kadirio
kwa hatua, kutoka vipimo halisi:

| Hatua | Muda | Kwa nini |
|---|---|---|
| 1 `build-calendar` | ~saa 1.9 (mara ya kwanza) · **dakika chache baadaye** | inasoma column ya timestamp pekee; ina cache |
| 2 `check-l1` | ~saa 3–6 | inasoma `timestamp/bid/ask`; ina cache |
| 3a/3b ulinganisho | dakika chache | sampuli + siku zinazopishana pekee |
| 4 `build-l2` | **~saa 5–8** | inasoma TICKS ZOTE (columns 5) + resample TF 7 — hii ndiyo nzito kuliko zote |
| 5 sentinel + splits | sekunde | |

**Kila hatua inaendelea ilipoishia.** Ukikatiza (`Ctrl+C`) au mashine ikizimika, endesha
`scripts\audit.bat` tena: hatua 1 na 2 zina cache ya JSONL, na hatua 4 ina `_l2_state.json`
inayoruka **symbol iliyokwisha** (alama yake = partitions + TF + `config_hash`; L0 ikiongezeka,
symbol inajengwa upya, haibaki ya zamani kimya). Kuanza upya kabisa: `--no-cache` (hatua 1–2)
au `--no-resume` (hatua 4).

**Ni salama kuikatiza.** Ni bora kuliko kuacha mashine ikikimbia usiku mzima bila kuihitaji.

Maandishi yote yanaandikwa `research\reports\quality\audit.log` — dirisha likifungwa au PC
ikizimika, ushahidi haupotei. Baada ya kukatika, swali la kwanza:

```cmd
scripts\shell.bat
python -m src.data.cli audit-status
```
Inaonyesha hatua zilizokamilika, ngapi ziko kwenye cache, na symbols zipi za L2 zipo tayari.

**PC isilale.** `audit.bat` inaweka `standby-timeout-ac 0` yenyewe (AC pekee — betri haiguswi),
lakini **kufunga kifuniko** ni mpangilio tofauti ambao script haiwezi kuubadilisha kwa usalama:
Control Panel → Power Options → *Choose what closing the lid does* → **When plugged in: Do
nothing**. Bila hilo, kufunga laptop kunaua kazi ya saa 9.

`check-l1` ikirudisha exit 1, hiyo **si hitilafu ya script** — ni partitions zilizofeli ubora.
Zisome kwenye `quality_report.json` (`fail_reasons`), kisha ni uamuzi wa PD: kuziba kwa
`catchup.bat`, au kuziacha nje ya training (`quality.fail_action: exclude`).

---

## 4. CONFIG — iko wapi na kwa nini

| Faili | Ina nini | Nani anahariri |
|---|---|---|
| `config\data.yaml` | **vigezo vyote vya data/features/labels/utafiti** — symbols, storage, recorder, reconcile, **vizingiti vya ubora (`quality`)**, splits, vizingiti vya R0–R9 | **PD** |
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
├── data\L2_bars\symbol=<SYM>\tf=<TF>\bars.parquet     (T1 — `build-l2`)
├── data\L1_clean · L3_features · L4_labels · L5_datasets\
└── reports\quality · screening · ablation · calibration
```
`reports\` na `research\src\` **zinapushwa** (ushahidi wa kila awamu); data **haipushwi**.

L2 inaweza kujengwa upya wakati wowote kutoka L0 — ni **derived**, si chanzo. L0 pekee ndiyo
isiyoweza kuzalishwa upya (§9).

---

## 6. MAKOSA NA SULUHISHO

| Dalili | Suluhisho |
|---|---|
| `-10003 IPC initialize failed` | `ELITEFX_MT5_TERMINAL` haijawekwa au njia si sahihi (§2) |
| `Call failed` **kwa siku unayojua ipo** | client wa pili wa MT5 — simamisha `record.bat` (§2) |
| `Call failed` kwa siku za zamani | terminal haina tick history hiyo → `probe-history`, au Strategy Tester (§8) |
| `broker_id haijawekwa` | jaza `config\data.yaml` → `recorder.broker_id` |
| `UKIUKAJI WA PROVENANCE` | broker/server imebadilika → §9 |
| `verify-l0 … missing=N` | partitions zilifutwa kwa idhini → `hash-l0 --prune-missing --reason "..."` |
| `verify-l0 … changed=N` **baada ya kuandika upya kwa idhini** | manifest ina hashes za zamani → `hash-l0 --allow-mutation --reason "..."` (tukio linaingia `mutation_log`) |
| `verify-l0 … changed=N` **bila kuwa umeidhinisha kitu** | **SIMAMA.** L0 imebadilika kimya — chunguza kabla ya kufanya lolote (DF-01) |
| `check-l1` exit 1 | si hitilafu — partitions zimefeli ubora; soma `quality_report.json` (§3.1) |
| `coverage … haijahukumiwa` | kalenda haipo au haina symbol/mwezi huo → endesha `build-calendar` kwanza |
| `sentinel: bars za L2 hazipo` | endesha `build-l2` kwanza (au `sentinel --synthetic` kupima code pekee) |
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

## 10. SAHIHI YA PD

**Mara moja:** fungua `docs\SIGNATURES.md`, badilisha mstari `**PD:**` uweke utambulisho wako
halisi wa git. Uangalie kama unaujua:
```cmd
git config user.name && git config user.email
```
Usipouwa nao: `git config --global user.name "Jina Lako"` na `... user.email "barua@yako"`.

**Kusaini:**
```cmd
scripts\sign.bat DF-05 VERIFIED --evidence research\reports\quality\quality_report.json ^
                 --reason "partitions 25,498 · kufeli 0.6% · nimekagua sababu zote"
git add docs\SIGNATURES.md
git commit -m "sahihi: DF-05 VERIFIED"
```
**Commit ndiyo sahihi** — bila yake ni maandishi tu. Uamuzi nne: `VERIFIED` (inahitaji
`--evidence`) · `LESSON` · `APPROVED` (pre-registration, kabla ya matokeo) · `REJECTED`.

| Amri | Inajibu nini |
|---|---|
| `python -m src.governance.cli pending` | ni vipengele vipi vinasubiri sahihi yangu? |
| `python -m src.governance.cli show` | nimesaini nini, lini, kwa sababu gani? |
| `python -m src.governance.cli verify` | sahihi zote bado ni halali? (lango G14) |

`verify` inafeli ikiwa faili la ushahidi limebadilika baada ya kusainiwa — ndiyo maana `--evidence`
ni ya lazima kwa `VERIFIED`. Na sahihi ya `VERIFIED`/`APPROVED`/`LESSON` kutoka kwa mtu asiye PD
inakataliwa: **hakuna anayeweza kusaini kwa niaba yako.**

---

**Nje ya wigo:** sheria za data/labels/features → `DATA_FEATURE_STANDARD.md` ·
risk/cost → `RISK_COST_ENGINE.md` · terms na rejista → `IMPLEMENTATION_PLAN.md`.
