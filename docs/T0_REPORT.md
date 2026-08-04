# RIPOTI YA TERM T0 — MSINGI (tabaka la data L0)

> **Kwa:** PD · **Spec:** `DATA_FEATURE_STANDARD.md` §2, §2.1, §2.2, §9
> **Rejista:** DF-01, DF-02, DF-03, DF-04 (`IMPLEMENTATION_PLAN.md` §3.3, ledger §3.5)
> **RCE HAIJAGUSWA** — hakuna faili la `src/rce/` lililoundwa wala kubadilishwa.

---

## 0. MUHTASARI WA MSTARI MMOJA

Zana zote nne za T0 zimejengwa na zina tests zinazopita (**61/61 kijani**): recorder wa feed ya
broker, normalization ya Toleo A/B, hashing ya L0 nzima + manifest, na muundo wa research repo.
Zinachosubiri ni **vitu vitatu vya PD** (akaunti ya broker, storage ya research, kuthibitisha
config mpya) — bila hivyo hakuna partition HALISI inayoweza kurekodiwa wala kuhashiwa, kwa hiyo
DF-01..DF-04 zinasimama `IMPLEMENTED`, hazipandi `VERIFIED`.

---

## 1. KILICHOJENGWA

| # | Kazi ya T0 | Iko wapi | Rejista |
|---|---|---|---|
| 1 | Recorder wa tick feed ya broker (MT5) | `src/data/recorder.py`, `src/data/mt5_source.py` | DF-04, DF-03 |
| 2 | Normalization ya Toleo A/B → schema moja | `src/data/schema.py` | DF-02 |
| 3 | SHA256 ya partitions ZOTE + manifest | `src/data/hashing.py`, `src/data/manifest.py` | DF-01, DF-03 |
| 4 | Muundo wa research repo (§9) | `src/data/research_layout.py` | §9 |
| — | CLI + milango ya CI | `src/data/cli.py`, `.github/workflows/ci.yml` | DF-01, DF-04 |
| — | Vigezo vipya vya config | `config/data.yaml` (`storage:`, `recorder:`) | DoD/G10 |

### 1.1 Recorder (DF-04, DF-03)

```
python -m src.data.cli record                 # mzunguko usioisha (§2.2)
python -m src.data.cli record --once          # poll moja (kwa uchunguzi)
```

* Inavuta ticks kwa `copy_ticks_range(..., COPY_TICKS_ALL)` — bid, ask, volumes, `flags`.
* Partition **moja kwa kila siku ya UTC**, inaandikwa **baada tu ya siku kufungwa**
  (+ `day_lag_minutes`), kwenye
  `L0_raw/provenance=broker/symbol=<SYM>/date=<YYYY-MM-DD>/ticks.parquet`.
* Kila partition inabeba metadata ya parquet: `provenance=broker`, `symbol`, `date`,
  `timestamp_tz=UTC`, `source`, `recorder_version`, `config_hash`, `code_rev`, `rows`.
* SHA256 inarekodiwa kwenye manifest **wakati ule ule** partition inapoandikwa.
* Watermark inakaa kwenye disk (`_state/recorder_state.json`): process ikifa katikati ya siku,
  poll inayofuata inavuta upya siku isiyokamilika — hakuna tick inayopotea.
* Hitilafu ya symbol moja **haiui** recorder (§2.2: "huanza, hauishii"); inaingia kwenye
  `errors` na symbols nyingine zinaendelea.

### 1.2 Normalization (DF-02)

Toleo A (`timestamp,bid,ask,bid_vol,ask_vol`, µs) na Toleo B (`ts,bid,ask,bid_volume,ask_volume`,
ms) zinasomeka kuwa schema **MOJA**: `timestamp[datetime64[us, UTC]], bid, ask, bid_vol, ask_vol`.
Ramani ya columns inatoka `config/data.yaml` kwa **mpangilio**, si kwa majina yaliyoandikwa kwenye
code — config ikibadilika, normalization inafuata bila kugusa code.

Mipaka iliyowekwa kwa makusudi:

* **L0 haibadilishwi.** Normalization ni ya wakati wa kusoma; test inathibitisha SHA256 ya faili
  inabaki ile ile baada ya kusoma.
* **Hakuna usafi wa kubuni.** Hakuna kupanga upya rows, kuondoa duplicates wala kujaza NaN —
  hizo ni checks 8 za L1 (T1). Normalization inayosafisha kimya ingeficha hitilafu ambazo R0
  inapaswa kuziona.

### 1.3 Hashing + manifest (DF-01, DF-03)

```
python -m src.data.cli hash-l0      # hash partitions ZOTE + andika manifest
python -m src.data.cli verify-l0    # lango la CI: hesabu upya, linganisha
```

`manifest_l0.json` ina: `config_hash`, `code_rev`, hesabu ya partitions kwa provenance, na kwa
kila partition — `sha256`, `size_bytes`, `symbol`, `provenance`, `schema_variant`, `rows`,
`first_ts`, `last_ts`.

Sheria ya immutability ipo kwenye code, si kwenye nia njema: partition mpya inaongezwa (append);
partition iliyopo yenye hash ile ile inathibitishwa; **partition iliyobadilika inakataliwa**
(`ManifestError: UKIUKAJI WA DF-01`) na `verify-l0` inarudisha exit 1. Kuandika juu ya hash
kunawezekana **tu** kwa `--allow-mutation --reason "..."`, na kunaacha alama kwenye `mutation_log`.

### 1.4 Muundo wa research (§9)

```
python -m src.data.cli init-research
```
Inatengeneza `data/{L0_raw,L1_clean,L2_bars,L3_features,L4_labels,L5_datasets}`,
`reports/{quality,screening,ablation,calibration}`, `src/`, pamoja na `README.md` inayoeleza
sheria nne (L0 haibadilishwi · provenance inaandikwa · dataset_id kwa kila dataset · holdout/
RESERVE zinakaa nyuma ya ruhusa ya R8). Ni **idempotent** — haigusi kilichopo.

---

## 2. USHAHIDI

### 2.1 Tests za spec (§4.1)

```
$ python -m pytest -q
61 passed
```

| Faili | Inathibitisha nini |
|---|---|
| `tests/data/test_schema_normalization.py` | matoleo mawili → frame ILE ILE bit-kwa-bit; ms→µs; symbols 12 zina toleo lililotangazwa; kusoma hakubadilishi L0; toleo lisilotarajiwa linasimamisha kazi |
| `tests/data/test_hashing_manifest.py` | hash thabiti na nyeti; append-only; partition iliyobadilika = FAIL; verify inagundua mabadiliko/kupotea/kutokuhashiwa; mutation_log |
| `tests/data/test_recorder.py` | partition kwa kila siku iliyofungwa; tag ya provenance kwenye metadata; manifest + SHA256; siku isiyokamilika haiandikwi; hakuna kuandika mara mbili; watermark inaendelea baada ya restart; siku tupu ya trading = ONYO; Jumamosi si ONYO; hitilafu ya symbol moja haiui recorder |
| `tests/data/test_freshness.py` | OK / ALERT / NOT_STARTED / SKIPPED; pengo ndani ya kipindi kilichorekodiwa; wikendi na sikukuu hazizalishi ONYO |
| `tests/data/test_research_layout.py` | folda zote za §9; idempotency; README |
| `tests/data/test_cli.py` | exit codes za milango ya CI (0 sawa/skipped · 1 ukiukaji/ONYO · 2 hitilafu) |

### 2.2 Mzunguko kamili kwa data ya kufikirika

Data halisi ya L0 iko nje ya repo na bado haipatikani kwa session hii, kwa hiyo mtiririko mzima
uliendeshwa kwa partitions za kufikirika (Toleo A daily + Toleo B monthly + feed ya "broker"
kupitia chanzo cha replay):

```
$ python -m src.data.cli record --once --replay-dir ... --symbols EURUSD,XAUUSD
poll: written=2 empty=0 skipped=0 errors=0
  + EURUSD 2026-08-03: ticks=800 sha256:44be884b...
  + XAUUSD 2026-08-03: ticks=800 sha256:daca9ff4...

$ python -m src.data.cli hash-l0
L0 hashing: scanned=6 added=4 confirmed=2 mutated=0
provenance: {"aggregator": 4, "broker": 2}

$ python -m src.data.cli verify-l0
verify-l0: PASS · unchanged=6 changed=0 missing=0 untracked=0
```

Malango yote mawili yalijaribiwa pia yakiwa **yanapaswa kufeli**:

```
# partition ya L0 ikibadilishwa kwa makusudi:
verify-l0: FAIL · unchanged=6 changed=1 missing=0 untracked=0
  ! IMEBADILIKA (DF-01): provenance=aggregator/symbol=EURUSD/2026/2026-07-27.parquet   [exit 1]

# siku mbili za trading bila data:
DF-04 freshness: ALERT
  [ONYO] EURUSD: partitions=2 mwisho=2026-08-03 · zilizokosekana: 2026-07-30, 2026-07-31  [exit 1]
```

Mstari mmoja wa manifest (umbo halisi):

```json
"provenance=broker/symbol=EURUSD/date=2026-08-03/ticks.parquet": {
  "symbol": "EURUSD", "provenance": "broker",
  "sha256": "sha256:44be884b...", "size_bytes": 21775,
  "schema_variant": "A", "rows": 800,
  "first_ts": "2026-08-03T08:00:00+00:00", "last_ts": "2026-08-03T09:33:13+00:00"
}
```

---

## 3. UWAZI — MAMBO MATANO YA KUJUA

1. **Volumes za MT5 hazigawanywi na broker.** Spec inataka `bid_vol`/`ask_vol`; MT5 inatoa
   `volume_real` MOJA pamoja na bendera zinazoonyesha upande uliobadilika. Recorder inaweka volume
   kwenye upande ulioupdate (BID→`bid_vol`, ASK→`ask_vol`), na inahifadhi `flags` + `volume_real`
   kama columns za ziada ili ukweli wa chanzo usipotee. Huu ni **mgawanyo uliotangazwa**, si
   makadirio — na normalization haichukui columns hizo za ziada.
2. **Kalenda ni ya muda.** DF-04 inahitaji jibu la "siku hii ni ya trading?". Kalenda KAMILI
   inatengenezwa kutoka **data** kwenye T1 (spec §3). Kwa sasa: Jumamosi imefungwa; Jumapili ni
   ya hiari (soko linafunguka ~22:00 UTC) kwa hiyo ukimya wake hauzalishi ONYO; Jumatatu–Ijumaa
   ni siku kamili; sikukuu ziko kwenye `recorder.calendar.holidays_md`.
3. **Orodha ya symbols kwa kila toleo inahusu data ya aggregator PEKEE.** Recorder inaandika
   symbols zote kwa schema ya kawaida. (Hili lilikutwa na mzunguko wa §2.2: XAUUSD ya broker
   ilikuwa inakataliwa kwa sababu XAUUSD ya aggregator ni Toleo B. Limerekebishwa na lina test.)
4. **Kuandika kunachelewa kwa makusudi.** Partition inaandikwa baada ya siku kufungwa +
   `day_lag_minutes` (15). Faida: partition inaandikwa MARA MOJA (immutability halisi). Gharama:
   ticks za leo ziko kwenye kumbukumbu ya process hadi usiku wa manane wa UTC — process ikifa,
   zinavutwa upya kutoka MT5 (history ya broker), hazipotei.
5. **`--allow-mutation` ipo lakini si ya mtekelezaji.** Ni njia ya PD ya kurekodi kwamba chanzo
   kilirudia partition — inahitaji sababu iliyoandikwa na inaacha alama ya kudumu.

---

## 4. VIGEZO VIPYA VYA CONFIG (vinasubiri sahihi yako)

Vimewekwa `config/data.yaml` kwa sheria ya G10 (hakuna kigezo cha maamuzi kwenye code). PD
anathibitisha au anabadilisha:

```yaml
storage:                       # §9 — NJE ya repo hii
  research_root:  "${ELITEFX_RESEARCH_ROOT}"
  l0_root:        "${ELITEFX_RESEARCH_ROOT}/data/L0_raw"
  l0_manifest:    "${ELITEFX_RESEARCH_ROOT}/data/L0_raw/manifest_l0.json"
  holdout_root:   "${ELITEFX_HOLDOUT_ROOT}"        # G2 inatekelezwa T1

recorder:
  enabled: true · provenance_tag: "broker" · source: "mt5"
  poll_seconds: 60 · day_lag_minutes: 15 · initial_backfill_days: 3
  calendar.holidays_md: ["01-01", "12-25"]
  freshness_alert.grace_hours: 26
  mt5: symbol_suffix + majina ya ENV za login/password/server/terminal
```

Sifa za kuingia MT5 **haziko** kwenye config wala code — zinatoka environment
(`ELITEFX_MT5_LOGIN`, `ELITEFX_MT5_PASSWORD`, `ELITEFX_MT5_SERVER`, `ELITEFX_MT5_TERMINAL`).

---

## 5. KINACHOKUZUIA — VITU VITATU VYA PD

| # | Kinachohitajika | Kwa nini | Kinachofunguka |
|---|---|---|---|
| 1 | **Broker + akaunti (demo au live) + mazingira ya MT5** | `MetaTrader5` ni Windows-only; recorder inahitaji terminal iliyoingia | DF-04 inaanza kukusanya; kila siku inayopita bila hii ni data iliyopotea (§2.2) |
| 2 | **Storage ya research** (`ELITEFX_RESEARCH_ROOT`) | §9 — datasets zinabaki nje ya repo | `init-research`, `hash-l0` ya L0 HALISI, malango ya CI kuacha kuwa SKIPPED |
| 3 | **Kuthibitisha `storage:` + `recorder:`** hapo juu | config ni mamlaka yako (§1.1) | hadhi ya `VERIFIED` |

Sababu ya kiufundi ya kutopandisha hadhi: kigezo `ELITEFX_RESEARCH_ROOT` kikikosekana, malango ya
CI yanarudisha **SKIPPED** (exit 0) badala ya kufeli kwa uwongo — na SKIPPED si ushahidi.

---

## 6. HADHI DHIDI YA EXIT CRITERIA ZA T0

| Kigezo cha exit (§2) | Hali | Kinachokosekana |
|---|---|---|
| recorder unarekodi kila siku ya trading | code + tests tayari; **haujaanza** | akaunti ya broker + mazingira ya MT5 (PD) |
| symbols 12 zinasomeka kwa schema moja | **imethibitishwa kwa tests** kwa matoleo yote mawili; haijaendeshwa kwa partitions halisi | njia ya storage ya L0 halisi |
| SHA256 za partitions zote zimehifadhiwa | zana + manifest tayari, zimejaribiwa mwisho-hadi-mwisho | L0 halisi ya kuhash |

Kwa hiyo: **DF-01, DF-02, DF-03, DF-04 = `IMPLEMENTED`.** Hakuna inayopanda `VERIFIED` hadi
uendeshe zana hizi kwenye storage halisi na usaini (sheria 3 ya §0: hakuna VERIFIED bila ushahidi).

---

## 7. HATUA INAYOFUATA

1. **PD:** vitu vitatu vya §5.
2. **Baada ya storage kupatikana:** `init-research` → `hash-l0` ya L0 nzima → manifest ya kwanza
   halisi → PD anapitia (`provenance_counts`, partitions zilizofeli kusomeka).
3. **Baada ya akaunti:** recorder inaanza kama huduma inayojirudia; `check-freshness` inakimbia
   kila siku ya trading (workflow ya CI tayari ina `schedule`).
4. **Kisha T1 (R0):** L1 checks 8, kalenda ya sessions kutoka data, L2 bars, sentinel ya uvujaji,
   G2 holdout guard. Ulinganisho A↔B wa kina (spread/sessions) ni deliverable ya T1 — T0 imeweka
   njia ya kusoma matoleo yote mawili kwa schema moja, ambayo ndiyo sharti lake.
