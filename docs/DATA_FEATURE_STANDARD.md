# ELITEFX — DATA & FEATURE STANDARD — spec ya tabaka la data (PD 2026-08-03)

> **Hadhi:** standard ya uzalishaji, sawa na `KAIROS_1_STANDARD.md`. Hati hii ni **spec**, si
> utekelezaji. Datasets, notebooks na runs za utafiti **zinabaki nje ya folda hii** (sheria ya
> README). Kinachokaa hapa ni **mkataba**: data inaonekanaje, feature inakubalikaje, label
> inahesabiwaje — ili namba za utafiti ziwe zile zile zitakazoingia kwenye engine.

---

## 0. HOJA — KWA NINI TUNAANZA NA DATA

KAIROS-1 ina models kumi (§1.1). Model bora kwenye data mbovu inatoa **jibu la uongo kwa ujasiri
mkubwa** — ndiyo hali hatari kuliko zote, kwa sababu calibration, EV-gate na sizing zote
zinaiamini. Kwa hiyo mpangilio wa kazi ni:

```
DATA  →  LABELS  →  FEATURES  →  MODELS
  ▲        ▲          ▲
  │        │          └─ hakuna feature bila hypothesis + kipimo
  │        └─ label mbovu = model inajifunza kitu kingine, si tulichokusudia
  └─ data mbovu = kila kitu kilicho juu yake ni bandia (GIGO)
```

**Kanuni tano zisizovunjwa:**

1. **Kikomo ni LABELS, si bars.** Bars ni milioni; setups ni maelfu. Kila feature inayoongezwa
   inagawana bajeti ile ile ya labels.
2. **Kila kitu ni point-in-time.** Namba yoyote inayoingia kwenye feature au label lazima
   ingekuwa **inajulikana wakati ule**. TF saba = nafasi saba za uvujaji.
3. **Chanzo kimoja kwa kila kiasi.** ATR moja, spread moja, pip_value moja — zikihesabiwa mahali
   pawili, siku moja zitatofautiana (sheria ile ile ya `cost_pips` §4.2 ya KAIROS-1).
4. **Dataset ni artifact, si hali ya kompyuta.** Kila dataset ina `dataset_id` + fingerprint;
   matokeo yasiyoweza kuzalishwa upya hayapo.
5. **Kipimo kabla ya ujenzi.** Eneo lolote (data, label, feature family, model) linaingia **TU**
   likishinda kizingiti kilichoandikwa **kabla** ya kuona namba. Lisiposhinda → **LESSON**.

### 0.1 Bajeti ya labels — hesabu halisi (imesahihishwa kwa data halisi, PD 2026-08-04)
```
H1 bars kwa mwaka  ≈ 24 × 5 × 52          = 6,240
Miaka 10.3 (2016-01 → 2026-04), symbol 1   ≈ 64,000 bars
Setups zinazostahili (≈5% ya bars; §4.3)   ≈ 3,200 labels
Pooled, symbols 12                         ≈ 38,000 labels → ≈ 770 features (bajeti @50)
  kati yake TRAIN+VAL (80%)                ≈ 30,800  ·  HOLDOUT ≈ 7,800
Barrier grid ×25                           ≈ 960,000 rows (zinahusiana — si sample huru)
```
**Matokeo ya hesabu hii (uamuzi wa design):** training ni **pooled** (symbols zote pamoja, features
zilizo scale-free + symbol embedding), si model kwa kila symbol. Model kwa kila symbol inagawanya
data mara 12 bila kuongeza taarifa. Per-symbol inabaki kwa **calibration** pekee.

**Bajeti hii inabana TRADE labels pekee.** Labels za kila-bar (direction ya bar ijayo, regime,
malengo ya pretraining §5A ya KAIROS-1) hazibanwi na bajeti hii — bars za H1 ni ~770,000 pooled na
ticks ni ~bilioni 3.4. Hii ndiyo njia halali ya kulisha deep models bila kuvunja kanuni ya 1.

---

## 1. TABAKA ZA DATA (L0 → L5)

```
L0  RAW        TICKS bid+ask (µs/ms)                 immutable · append-only · hashed
 │
L1  CLEAN      UTC · gaps · duplicates · sanity      ripoti ya ubora + PASS/FAIL
 │
L2  BARS       TF 7 zilizojengwa kutoka M1           + spread stats kwa kila bar
 │
L3  FEATURES   kwa TF, as-of closed bar pekee        feature card kwa kila moja
 │
L4  LABELS     quantile · barrier · fill · quality   zinatatuliwa kwa path ya TICKS
 │
L5  DATASETS   train / validation / holdout          manifest + fingerprint
```

Kila tabaka **haiandiki** juu ya lililo chini yake. L0 haibadilishwi kamwe — marekebisho yote ni
L1 na kuendelea, ili tuweze kujenga upya kila kitu kutoka chanzo.

---

## 2. L0 — RAW

| Kitu | Sharti | Sababu |
|---|---|---|
| Granularity | **TICKS** (bid+ask, quote volumes) | ticks ndizo zinatatua labels za touch (§5.2) kwa usahihi wa juu kuliko M1 |
| Bei | **bid NA ask** | spread ya kihistoria ni malighafi ya RCE §3.1; mid pekee = gharama ya kubuni |
| Volume | quote volumes (bid_vol/ask_vol); real volume haipatikani FX | intensity (§4 F6) |
| Muda | timestamp **UTC** (µs au ms) | rollover/swap ni server time; kila kitu kingine ni UTC |
| Umbizo | parquet, Hive partition `symbol=XXX` | kusoma sehemu bila kufungua yote |
| Hadhi | **immutable, append-only**, SHA256 kwa kila partition | reproducibility (kanuni 4) |

**Mutation ya L0 (PD 2026-08-04):** default ni **KAMWE**. Kifungu pekee cha dharura (mf. partition
iliyoharibika kwenye disk): kuandika juu ya partition yenye hash iliyobadilika kunaruhusiwa **TU
kwa idhini ya PD**, kwa `--allow-mutation --reason "<sababu>"`, na tukio linaingia `mutation_log`
ya manifest (lini, sababu, hash ya zamani na mpya). Mutation bila idhini ya PD ni **UKIUKAJI WA
DF-01** — inakataliwa na build inasimama.

### 2.1 Schema halisi (kama ilivyo kwenye `data/raw/ticks/`, 2026-08-04)
Symbols 12, ticks ~bilioni 3.4, 2016-01 → 2026-04, matoleo **MAWILI**:

| | Toleo A (symbols 9) | Toleo B (EURCHF, GBPJPY, XAUUSD) |
|---|---|---|
| Columns | `timestamp, bid, ask, bid_vol, ask_vol` | `ts, bid, ask, bid_volume, ask_volume` |
| Precision | µs | ms |
| Partition | ~daily (files 2693) | ~monthly (files 124) |

**Sheria ya normalization:** L0 haibadilishwi (immutable). L1 inasoma matoleo yote mawili na
kutoa schema MOJA ya kawaida (`timestamp[UTC], bid, ask, bid_vol, ask_vol`). Symbols za Toleo B
zinapita ukaguzi wa §3 kwa uzito maalum (session boundaries zao zinaonyesha dalili za chanzo
tofauti — kuthibitishwa R0). Dirisha la pamoja: **2016-01-04 → 2026-04-30** (splits za
`config/data.yaml`).

### 2.2 Provenance ya chanzo (sera — PD 2026-08-04)
Data ya L0 iliyopo ni ya **aggregator wa kihistoria**, si feed ya broker wa live. Matumizi:

| Inaruhusiwa | Hairuhusiwi peke yake |
|---|---|
| labels zote (touch, quantile, fill-bootstrap) | spread stats za MWISHO zinazolisha RCE live |
| features, screening, baselines, models, calibration (R0–R5) | attestation ya `cost_pips`/`P(fill)` ya live |
| pretraining (§5A ya KAIROS-1) | — |

**Kitambulisho cha broker ni sehemu ya provenance (PD 2026-08-05):** `provenance: broker` peke
yake haitoshi — spread na fills ni **za broker husika**. Kila partition inabeba
`recorder.broker_id` kwenye metadata yake, na recorder **inasimama** `broker_id` ikibadilika
baada ya partitions kuandikwa (data ya brokers wawili haichanganywi chini ya tag moja; zikichanganyika
hakuna njia ya kuzitenganisha baadaye). Broker mpya → L0 root mpya, au kufuta zilizopo kwa idhini ya PD.

Kando na lebo ya PD, kila partition inabeba `broker_server` — **ukweli kutoka MT5**
(`account_info().server`, mf. `Dukascopy-demo-mt5-1`). Lebo inaweza kuandikwa vibaya; server
haiwezi. Server ikibadilika bila lebo kubadilika, recorder inasimama vilevile.
**`terminal_info().company` HAITUMIKI kamwe kama kitambulisho cha broker** — inaripoti msambazaji
wa terminal ("MetaQuotes Ltd." hata kwa akaunti ya broker mwingine kabisa).

**Sharti mbili za kufunga pengo:**
1. **Kurekodi feed ya broker wa live/demo kuanzia SASA** (ticks bid+ask → L0 partition mpya yenye
   `provenance: broker`). Kila mwezi usiorekodiwa ni data ya broker iliyopotea bure.
2. R6/R8 zinafanyika kwa data ya aggregator **+ cost stress ×1.5** (ipo) **+ ulinganisho wa
   spread** aggregator↔broker kwa kipindi kinachopishana, ukishapatikana. Attestation inaandika
   provenance ya gharama waziwazi.

**Kina cha history ya broker (kimepimwa T0, 2026-08-06):** Dukascopy demo
(`Dukascopy-demo-mt5-1`) inatoa ticks kuanzia **2026-04-27** (`probe-history`, EURUSD;
2026-04-24 haina). Matokeo mawili:

1. **Pengo halipo.** Aggregator inaishia 2026-04-30, broker inaanza 2026-04-27 — L0
   inakuwa mfululizo kutoka 2016-01-04 hadi leo.
2. **Siku 4 zinapishana** (2026-04-27 … 04-30). Hapo ndipo **ulinganisho wa spread
   aggregator↔broker** (sharti la 2 hapa chini) unafanyika kwa namba — siku zile zile,
   vyanzo viwili. Ni kipimo cha R0.

Kina hiki ni cha broker husika na kinasogea mbele kadri muda unavyopita (~miezi 3 ya
nyuma). Kwa hiyo kurekodi kila siku si hiari: kilichopita mpaka huo hakipatikani tena.

**Refresh:** L0 inaishia 2026-04-30. Kila mzunguko wa utafiti unaanza kwa append ya partitions
mpya + hashes — data ya 2026-05+ ni RESERVE (holdout ya mzunguko ujao, `DATA_SPLIT_PLAN.md` §3).

---

## 3. L1 — USAFI NA MALANGO YA UBORA

**Kitengo cha hukumu ni SIKU, si faili** (PD 2026-08-08). Siku ikifeli → **haitumiki kwa
training**, na ripoti inaandikwa. Sababu ni kipimo, si nadharia: Toleo A linaandika partition kwa
siku, Toleo B kwa **mwezi**. Kuhukumu kwa faili kunafanya mambo mawili yasiyokubalika — partition
ya mwezi ina siku ~22, kwa hiyo ina nafasi mara 22 zaidi ya kukutana na siku moja mbaya (kipimo
cha 2026-08-08: EURCHF/GBPJPY/XAUUSD zilifeli **12 kwa mwaka**, yaani partitions zao ZOTE), na
`fail_action: exclude` ingetupa **mwezi mzima kwa siku moja** — symbols zote tatu za Toleo B
zingetoweka kwenye training kwa kasoro ya kipimo, si ya data.

| # | Ukaguzi | Sheria | FAIL reason |
|---|---|---|---|
| 1 | **coverage** | bars zilizopo ÷ bars zinazotarajiwa (session calendar) ≥ `min_coverage` — L0 (ticks): **dakika zenye quote** dhidi ya median ya siku kamili za symbol/mwezi | `low_coverage` |
| 2 | **monotonicity** | timestamps zinapanda; **kurudi nyuma = 0 daima**; duplicate ≤ `max_duplicate_frac` (MT5 inatoa quotes mbili kwenye µs moja) | `bad_timestamps` |
| 3 | **gaps** | L0 (ticks): pengo ≤ `max_gap_seconds` · L2 (bars): ≤ `max_gap_bars`. Kizingiti kinaruhusiwa kuwa cha **kila symbol** — XAUUSD ina mapumziko ya kila siku (~saa 1) ambayo si pengo la data | `intrasession_gap` |
| 4 | **OHLC sanity** | `low ≤ min(open,close) ≤ max(open,close) ≤ high` — **inakaguliwa L2**, kwa sababu ticks hazina OHLC (§4) | `ohlc_violation` |
| 5 | **quote sanity** | quote **isiyowezekana**: `bid > ask`, `bid == ask`, `bei ≤ 0` → FAIL daima. Spread pana → FAIL **tu** ikizidi sakafu **NA** `spread_outlier_mult` × median ya siku | `quote_violation` |
| 6 | **DST/session** | mabadiliko ya saa yanalingana na kalenda ya broker — mipaka ni median ya **symbol/mwezi**; hatua ya saa 1 kamili inaandikwa kama DST, si FAIL | `session_mismatch` |
| 7 | **clock drift** | tofauti ya server↔UTC ni thabiti | `clock_drift` |
| 8 | **flat bars** | mfululizo wa bars zenye `high==low` ≤ `max_flat_bars` — **inakaguliwa L2** · L0 (ticks): quote ile ile kwa `max_stale_seconds` | `stale_feed` |

**Weekend, holiday na rollover si "gaps"** — ni kalenda. Kalenda inatengenezwa kwa data yenyewe
(bars zinazoonekana) na kuthibitishwa, si kudhaniwa.

**Sikukuu si "soko limefungwa" — ni "soko jembamba".** Kipimo cha 2026-08-10 kilipata siku 16 zenye
ticks ambazo kalenda ya kudhaniwa ilisema zimefungwa, na **zote 16** zilikuwa 25 Desemba (9) au
1 Januari (7) — hakuna ubaguzi hata mmoja. Soko la FX halifungwi siku hizo; linabaki wazi likiwa na
ukwasi mwembamba sana na spread pana. Dhana ndiyo ilikuwa mbaya, si data. Siku hizo **zinabaki**,
kwa sheria ile ile ya `quote_sanity`: siku ghali ndizo model ya gharama inazohitaji zaidi, na
kuziondoa kungefanya kila EV iwe ya matumaini. Kwa hiyo `compare_with_assumed` ina makundi mawili
tofauti — `holiday_thin` (inaeleweka) na `unexpected_active` (**Jumamosi** yenye ticks, inayohitaji
maelezo). Kuziunganisha kungeficha swali halisi ndani ya 16 zinazoeleweka; jibu la swali hilo ni
**sifuri**. Kama siku hizo zinafaa kufanyiwa biashara ni swali la §4.3 (setup), si la ubora wa data.

**Vizingiti vinatoka kwenye mgawanyo wa data, si mezani.** Baada ya `check-l1`, `quality-stats`
inaonyesha kwa kila ukaguzi thamani halisi zilivyotawanyika na ni partitions ngapi zingefeli kwa
kila kizingiti kinachopendekezwa. PD anachagua kutoka hapo na kuandika `config/data.yaml`.
Kizingiti kilichofelisha nusu ya data ni **dalili ya kipimo kibaya**, si ya data mbovu —
kikaguliwe kabla ya kuondoa partition hata moja.

**Kila ukaguzi unaotegemea kalenda unafanyika kwa SIKU, si kwa faili** (checks 1, 3, 6). Partition
ya mwezi (Toleo B) ina siku ~22; kuikagua kama kipande kimoja kungeita usiku kati ya sessions
`intrasession_gap` na kulinganisha mipaka ya session na siku ya kwanza pekee.

**Siku moja inaweza kuwa kwenye partitions MBILI — inaunganishwa kabla ya kuhukumiwa.** Toleo B
halikati mwezi usiku wa manane bali **saa 05:00 UTC**, kwa hiyo tarehe 1 iko nusu kwenye faili ya
mwezi uliopita (00:00–04:59) na nusu kwenye ya mwezi huu (05:00–23:59). Kipimo cha 2026-08-09
kilionyesha hili moja kwa moja: EURCHF ilitoa mistari **miwili kwa tarehe ile ile**, tarehe 1 ya
karibu kila mwezi, mmoja `close ±1140 min` na mwingine `open ±300 min` — na `1140 + 300 = 1440`,
siku moja kamili. Kila nusu, ikihukumiwa peke yake, inaonekana imevunjika (coverage 5/24 au 19/24,
mipaka ya session mbali na kalenda); pamoja ni siku nzima yenye afya. Kwa `fail_action: exclude`
hiyo ilikuwa ikitupa **tarehe 1 ya kila mwezi** kwa symbols zote tatu za Toleo B — siku ~380 za
biashara halisi, kwa kasoro ya kipimo, si ya data. Ni kasoro ile ile ya "kitengo cha hukumu"
ikiwa upande wa pili: kwanza faili moja ilikuwa na siku nyingi; hapa siku moja iko kwenye faili
nyingi. Kinachounganishwa ni **malighafi** (dakika zinajumlishwa, mipaka ya muda inachukua mwanzo
wa kwanza na mwisho wa mwisho), si majibu — uwiano uliokwishakokotolewa hauwezi kujumlishwa.
Checks zisizotegemea kalenda zinabaki za kila kipande: kasoro ndani ya nusu moja ni kasoro ya siku
nzima. Idadi ya vipande vilivyounganishwa inaripotiwa kama `totals.split_day_pieces_merged`.

**Ukaguzi wa 7 (`clock_drift`) unapima siku, si `now()`.** Kipimo cha kwanza kililinganisha tick ya
mwisho na saa ya sasa; kwenye kumbukumbu ya kihistoria hiyo ni namba ya umri wa faili (p50 =
−171,679,765 s = −5.4 miaka), na ukaguzi haukuweza kufeli kimuundo — 0/34,089. **Ukaguzi usioweza
kufeli si ulinzi; ni jina linalotoa hakikisho la uwongo.** Sasa unapima kitu kinachoweza kuwa
kibovu kwenye kumbukumbu: tick iliyoandikwa nje ya siku ambayo faili linaidai (saa ya server
iliyopotoka wakati wa kuandika, au faili lililochanganywa). Sehemu ya `tz == UTC` ilikuwa na maana
tangu mwanzo na inabaki.

**Matarajio (checks 1 na 6) ni ya kila symbol NA kila siku ya wiki.** Kwa symbol: XAUUSD haifanyi
biashara saa zile zile za EURUSD. Kwa siku ya wiki: soko linafunga **21:00 UTC Ijumaa** wakati
Jumatatu–Alhamisi zinaendelea hadi usiku wa manane, kwa hiyo Ijumaa ina `21/24 = 87.5%` ya dakika
na close yake iko **dakika 180** mapema. Ijumaa ni asilimia 20 ya siku zote za trading; kuipima
kwa wastani wa wiki nzima kunaifelisha kila wiki kwa kipimo kibaya pekee. Matarajio yanatoka kwa
median ya **majirani wa siku ile ile ya wiki**, na siku yenyewe **haiingii** — vinginevyo siku
iliyoharibika ingejiwekea kizingiti chake na kupita daima.

**Spread pana si data mbovu — ni gharama.** Kipimo cha 2026-08-08 kilifelisha siku 835 bila
`crossed` hata moja: GBPJPY siku za Krismasi/Mwaka Mpya na siku za msukosuko (COVID, Omicron),
na XAUUSD ya 2025–26 ambapo kizingiti cha **200 pips = $2.00 kamili** kilikuwa 16.7 bps dhahabu
ikiwa $1,200 lakini 5.0 bps ikiwa $4,000 — kizingiti kile kile kikibana **mara tatu zaidi** bei
ilipopanda. Kilikuwa kinapima bei, si ubora. **Na muhimu zaidi:** kutoa nje siku za spread pana
kunaondoa hasa siku ambazo gharama ni kubwa; model ya gharama ingejifunza soko lisilo na sikukuu
wala msukosuko, na kila EV ingekuwa ya matumaini — upendeleo ule ule ambao `cost_stress_mult`
(§R6) ipo kuupinga. Siku hizo zinabaki, na spread yake inaingia RCE kama ilivyo.

**Ticks zenye timestamp ile ile haziondolewi — zinapangwa kwa mpangilio wa kufika.** Labels za
touch (§5) zinatatuliwa kwa mfuatano wa ticks, kwa hiyo mpangilio wa ticks zinazoshiriki kipimo
kimoja cha muda ni sehemu ya jibu. Kila `sort` kwenye tabaka hili ni **stable**; kuzifuta
kungepoteza quotes halisi, na kuzipanga upya kungefanya dataset isizalishike upya (§8).

**Checks zinakamata siku; kasoro ya KIPINDI inaondolewa kwa uamuzi.** Ukaguzi unahukumu siku moja
moja, kwa hiyo unashindwa kimyakimya pale chanzo kizima kinapoharibika kwa kiasi kidogo lakini kwa
muda mrefu. Kipimo cha 2026-08-09 (`symbol-profile`) kilionyesha EURCHF, GBPJPY na XAUUSD — symbols
zote **tatu za Toleo B**, yaani chanzo kimoja — zikipoteza saa 1–2 KWA SIKU mwaka **2023 pekee**,
kisha kurudi 2024 (median ya dakika 1429→1315→1429, 1435→1320→1435, 1380→1319→1380). Vyombo hivyo
vitatu havishirikiani chochote kama masoko; kinachoshirikiana ni **chanzo** — kwa hiyo ni feed, si
soko. `gaps` inakamata takriban asilimia 45 ya siku hizo; nyingine zinapita zikiwa na kasoro ile ile
ndogo zaidi. Athari si "ubora hafifu": labels za touch (§5) zinatatuliwa kwa **path ya ticks**, kwa
hiyo pengo la saa 2 kila siku linaficha barrier zilizoguswa humo, na label inasema `timeout` wakati
SL/TP iliguswa — si kelele, ni **jibu la uongo**.

Kipindi kinachojulikana kinaondolewa kupitia `quality.excluded_ranges`, si kwa kulegeza ukaguzi:

```yaml
excluded_ranges:
  - symbols: [EURCHF, GBPJPY, XAUUSD]   # orodha tupu = symbols zote
    from:    "2023-01-01"
    to:      "2023-12-31"
    reason:  "..."                       # LAZIMA — inasafiri hadi kwenye ripoti
```

Sheria zake nne: (a) siku iliyo ndani ya kipindi **haipimwi kabisa** — inapata `excluded_by_pd`
pamoja na sababu yake, kwa hiyo haichanganyiki na siku iliyofeli ukaguzi; (b) `--what-if`
**haiwezi** kuirudisha, kwa sababu si suala la kizingiti — vinginevyo jedwali lingemshauri PD
kulegeza `min_coverage` ili kurudisha siku alizozizuia mwenyewe; (c) kifungu kinaingia
`config_hash`, kwa hiyo kinabadilisha `dataset_id` na kinalazimu `check-l1` kuendeshwa upya;
(d) kinahitaji **sahihi ya PD** (`sign.bat DF-05 APPROVED`) kabla ya kutumika kwenye T2 — kuondoa
data ni uamuzi wa kudumu, na sababu iliyoandikwa ndiyo inayomruhusu mtu wa baadaye kuupinga.

**Sera ya NaN:** hakuna imputation ya kubuni. Bar isiyokamilika inabeba `is_valid=false` na
**haitumiki** kama decision point; inaweza kutumika kama history kwa window ndefu **kama** feature
inaruhusu (imeandikwa kwenye feature card).

---

## 4. L2 — BARS ZA TF 7 + AS-OF RULE

**Bars zote saba zinajengwa kutoka TICKS kwenye repo yetu** (kupitia M1 ya ndani kama hatua ya
kati), si kupakuliwa kutoka broker. Sababu: broker anaweza kutumia mipaka tofauti ya bar;
tukijenga wenyewe, D1/H4/H2/H1/M30/M15/M5 zote zinatoka chanzo kimoja na zinalingana kikamilifu.

Kila bar inabeba, zaidi ya OHLCV:
```
spread_mean · spread_p50 · spread_p95 · spread_max      ← malighafi ya RCE §3.1
n_ticks · n_m1_bars · is_valid
```

`n_m1_bars` = **dakika zenye quote ndani ya bar**, na ndicho kipimo cha ukamilifu wa bar.
`n_ticks` peke yake kingedanganya: bar ya H1 yenye ticks 3,600 zote zilizojaa dakika 10 za
kwanza ingeonekana kamili zaidi kuliko bar yenye ticks 600 zilizosambaa dakika 60 zote.

Ticks zenye timestamp ile ile hazipangwi upya: kila `sort` hapa ni **stable**, kwa hiyo
`open`/`close` ya bar ni ile ile kila run (§8 — kuzalisha upya).

Checks za §3 zinazohitaji bars zinafanyika **hapa**: ya 4 (OHLC sanity), ya 8 (mfululizo wa
`high == low`), na upande wa L2 wa ya 3 (`≤ max_gap_bars`, ukihesabiwa **ndani ya siku**).

### 4.1 AS-OF RULE (kinga kuu dhidi ya uvujaji)
```
Wakati wa uamuzi t (= close ya bar ya H1):
   kwa kila TF k:  bar inayotumika = bar ya MWISHO yenye close_time ≤ t
```
Mfano: uamuzi wa H1 saa 10:00 UTC → D1 ni ya **jana iliyofungwa**, H4 ni ile iliyofungwa 08:00,
M15 ni ya 09:45. Bar isiyofungwa **HAITUMIKI** kamwe.

### 4.2 Sentinel ya uvujaji (test ya lazima)
```
Chukua dataset. Badilisha (shuffle) data YOTE baada ya t.
Feature zote za decision point t lazima zibaki ZILE ZILE, bit kwa bit.
Ikibadilika hata moja → uvujaji umegunduliwa → build inasimama.
```
Test hii inakimbia kwa kila build ya L3. Si hiari.

### 4.3 DECISION POINTS — SHERIA YA SETUP (PD 2026-08-07)

Bajeti ya §0.1 inasimama juu ya "setups ≈ 5% ya bars" — lakini hadi leo hakuna hati
iliyosema **bar ipi inastahili**. Pengo hili ni darasa la TATU la uvujaji: si la wakati
(sentinel §4.2 inalikamata) wala la stacking (S6), bali **la uchaguzi** — sheria ya setup
ikitengenezwa au kutunwa baada ya kuona matokeo ya labels, kila namba ya R1+ ni ya baada ya
ukweli, na hakuna kinga ya kiufundi inayoliona. Kinga pekee ni utaratibu huu:

**SETUP-v1** — bar ya H1 iliyofungwa inakuwa decision point ikiwa **zote tatu** zinatimia
(zote ni mechanical, point-in-time, kutoka bars zilizofungwa pekee):

```
1. GHARAMA     spread_p50 ya bar ≤ spread_gate_mult × median ya spread ya symbol/mwezi
               (soko lisilolipika si setup — RCE ingelikataa hata hivyo)
2. VOLATILITY  ATR14 ya H1 ndani ya percentile band ya rolling (dirisha miezi 6)
               (soko lililokufa halina TP inayofikika; la wazimu lina slippage isiyo na cap)
3. TRIGGER     |close − close[k]| ≥ min_atr_mult × ATR14   (impulse ya mwendo, scale-free)
```

**Sheria tano za utaratibu:**
1. Vigezo vyote viko `config/data.yaml §setups`; `setup_rule_id` inaingia kwenye
   `dataset_id` — kubadilisha sheria = dataset MPYA, si tweak.
2. Kutuna vigezo ili kufikia **rate** (~5%) inaruhusiwa KABLA ya labels kuonekana — rate
   haitumii matokeo. Kutuna kwa outcome yoyote ya label = selection leakage, marufuku (RS-01).
3. **CONTROL SAMPLE:** sehemu ya bars zisizo setup, kwa nasibu (`control_sample_frac` +
   seed kwenye config), zinapata labels PIA zikiwa na `is_control=true`. Bila control,
   hatutajua kamwe kama filter inatupa trades bora kuliko inazochukua — filter ni MODEL ya
   hatua ya kwanza, na hii ndiyo njia pekee ya kuipima (R1 inalinganisha base rates; R7
   inailinganisha kwa EV). Control **haiingii training** — ni kipimo cha filter tu.
   **Sehemu ni 0.05, si 0.10** (PD 2026-08-11, kabla ya labels): kichujio kilipofikia 4.46%,
   10% ilitoa control 56,471 dhidi ya setups 26,390 — mara mbili ya kile kinachopimwa. Nguvu
   ya ulinganisho inategemea kundi **dogo**; control ya ziada haikuwa inanunua chochote,
   ilikuwa inagharimu 68% ya kazi ya kutatua paths. Sehemu ikitunwa tena, iwe **kabla ya
   labels** na kwa hoja ya nguvu ya kitakwimu — kamwe kwa outcome.
4. Filter inapimwa na sentinel §4.2 kama feature nyingine yoyote (ni function ya bars
   zilizofungwa — shuffle ya baadaye isibadilishe uamuzi wa setup).
5. **R1 haianzi** kabla sheria hii haijasainiwa na PD (pre-registration, RS-01).

---

## 5. L4 — LABELS (nne, kila moja kwa model yake)

Labels zinatatuliwa kwa **path ya TICKS**, si OHLC ya H1 wala M1. Sababu: bar inaonyesha kwamba
high na low zote mbili ziligusa — **haisemi ipi iligusa kwanza**. Hata ndani ya M1 moja, mpangilio
wa touch unaweza kugeuza label; ticks ndizo pekee zinazoutatua kwa uhakika. Kwa BUY, touch ya SL
inapimwa kwa **bid**, ya TP kwa **bid** (unafunga kwa bid); kwa SELL kinyume — spread iko ndani ya
label, si dhana.

### 5.1 L-A — QUANTILE (Quantile NN)
```
y = log(close[t+H] ÷ entry) ÷ ATR[t]        # terminal return, units za ATR
H = horizon (bars za H1, config)
entry = MID ya wakati wa uamuzi · close[t+H] = MID          (PD 2026-08-07)
```
Units za ATR (si pips) — inalinganisha symbols na volatility regimes (hoja ile ile ya S3).

**Kwa nini MID, si bei ya trade:** L-A **inapendekeza**, haihukumu — anayehukumu ni Barrier
head, na yeye anafundishwa kwa path ya bei ya trade (§5.2). Huo ndio mgawanyo wa S1 ukifanya
kazi: quantile ikipendekeza cell yenye matumaini kupita kiasi kwa symbol pana, Barrier head
inaikataa — hasara ni ya ufanisi, si ya usahihi. Zaidi: spread inaingia **mara moja kwenye
path** (§5.2 — je barrier ilifikwa?) na **mara moja kwenye malipo** (RCE §3 — inagharimu
nini?). Kuiingiza pia kwenye L-A ni kuihesabu mara tatu kwenye maeneo yanayogusana. L-A ni
kipimo cha **mwendo wa soko** — mid ndiyo bei isiyo na upande. R1 inaripoti tofauti ya
quantiles mid-dhidi-ya-trade-price kwa symbols pana (XAUUSD, GBPJPY) ili uamuzi huu upimwe
kwa namba, si kwa hoja.

### 5.2 L-B — BARRIER (p_tp_first) — **grid, si derived**
Anti-circularity (S1) inasema head inayoweka mipaka isihukumu. Kwa hiyo Barrier Model **hailishwi**
SL/TP zilizotoka Quantile head. Badala yake:

```
Kwa kila decision point, tengeneza labels kwa GRID ya barriers:
   sl_atr ∈ {0.5, 0.75, 1.0, 1.5, 2.0}
   tp_atr ∈ {0.5, 1.0, 1.5, 2.0, 3.0}
Fuata path ya TICKS hadi horizon H:
   1 = TP iligusa kwanza · 0 = SL iligusa kwanza · timeout = darasa la tatu
Kwa kila TIMEOUT:  rekodi pia terminal return (R-units) kwenye horizon
   → hii ndiyo malighafi ya E[R|timeout] kwenye EV ya madarasa matatu (§2.1 ya KAIROS-1)
```
**Matokeo:** `p_tp_first = f(features, sl_atr, tp_atr)` — barriers ni **INPUT**, si kitu
kilichotokana na model ile ile. Quantile head inapendekeza SL/TP, Barrier head inaziita kwa
grid iliyojifunza kwa uhuru. Mduara umekatika.

**Gap-honest:** stop = **touch** (si close). Gap ikiruka barrier, label inasoma touch kwenye bei
ya kwanza baada ya gap — ndivyo live itakavyokuwa.

**TIE-BREAK (PD 2026-08-07):** bei ya kwanza baada ya gap ikifunika SL **na** TP kwa pamoja
(gap ya wikendi/habari inayoruka barriers zote mbili) → **SL inahesabiwa kwanza.** Sababu si
"tahadhari" — ni uhalisia wa utekelezaji: live, bei inayoruka mipaka yote miwili inakutana na
stop order upande mbaya kabla ya chochote kingine. Upendeleo unaobaki unashusha EV, hauipandishi
— upande salama wa kukosea. Tick moja haiwezi kugusa zote mbili (BUY: SL na TP zote kwa bid —
ingehitaji SL > TP); ticks zenye **timestamp ile ile** (Toleo B ni ms) zinabaki kwa mpangilio wa
kufika — kila sort ya tabaka hili ni stable (§4), kwa hiyo "ya kwanza" ina maana moja kila run.
**R1 inaripoti mara ngapi tie-break ilitumika**; ikizidi 1% ya labels, inapanda kwa PD — sheria
isiyopimwa mzunguko wake ni dhana.

### 5.3 L-C — FILL (P(fill))
Utekelezaji wa S4 kwa data ya kihistoria:
```
Kwa order ya aina A (market/stop/limit) kwenye bei X na cap C (config §slippage_cap_pips):
   fuata TICKS kuanzia t:  je bei ilipatikana ndani ya X ± C kabla ya kupita?
   fill = 1 / 0        (+ rekodi slippage iliyohitajika)
```
Hii ndiyo inayoruhusu kuanza **bila kusubiri data ya broker**. Demo → fine-tune, live → calibrate.

**Mipaka ya bootstrap (uwazi):** kwa **stop/limit** orders, path ya ticks inajibu swali sahihi.
Kwa **market** orders, kutojazwa live kunatokana na latency/liquidity ya wakati ule — path ya
kihistoria haiwezi kukisia hilo. Kwa market: `P(fill)` inaanza na **prior ya juu** (≈0.98) na
inakalibiwa kwa data ya demo/live mapema iwezekanavyo; haitegemei bootstrap hii.

### 5.4 L-D — QUALITY (XGBoost)
Inatokana na L-B + gharama, si label mpya:
```
R_net = (matokeo ya barrier kwa R) − (cost_pips ÷ sl_pips)
bucket:  A+ / A / B / reject   (mipaka kwenye config)
```

**Gharama hapa ni commission + swap PEKEE.** Spread ishaingia kwenye path (§5.2 — barrier
inatatuliwa kwa bei ya trade). Kuiongeza tena kwenye `cost_pips` ni kuihesabu mara mbili
kwenye namba ile ile. Mamlaka ya `cost_pips` ni RCE (§6.2 F6); R1 inatoa mkunjo wa unyeti
kwa gharama zilizotajwa wazi, si jibu.

### 5.5 Sheria za labels
- **Horizon moja iliyotangazwa** kwa kila familia; kubadilisha horizon = dataset mpya, si tweak.
- **Class balance inaripotiwa**, haisawazishwi kwa kubuni (resampling inapotosha calibration).
- **Timeout haitupwi kimya** — ni taarifa (setup haikwenda popote).
- Label yoyote inayohitaji data baada ya `t + H` haipo.

### 5.6 Kile L4 inarekodi ili R1 iweze kupima (toleo 2, 2026-08-12)

Vipimo vitatu vya R1 vinahitaji malighafi ambayo **haipatikani baada ya build**: kuipata
baadaye kungehitaji kupita kwenye ticks za miaka 8 mara ya pili. Kwa hiyo inarekodiwa pale
ticks zilipo tayari kwenye kumbukumbu:

| Safu | Iko wapi | Inajibu swali gani |
|---|---|---|
| `touch_past_pips` | kila cell | bei ilipita barrier kwa kiasi gani kabla ya tick ya kwanza kuionekana? Kwa **SL** ni slippage ya stop (§5.3, inapimwa dhidi ya `slippage_cap_pips`); kwa **TP** ni limit — bei kuruka zaidi haikupi bei bora |
| `terminal_trade`, `quantile_y_trade` | kila point | L-A ikipimwa kwa bei ya trade badala ya MID — §5.1 iliamua MID **kwa hoja**; hii inairuhusu ipimwe kwa namba |
| `m1_disagree` | sampuli ya points (`labels.m1_check_frac`) | grid ile ile ikitatuliwa kwa **high/low za M1** badala ya ticks — je majibu yanatofautiana, na mara ngapi M1 moja iligusa SL na TP kwa pamoja? |

Ukaguzi wa M1 unatumia **ticks zile zile** kama chanzo cha bars, si faili la L2: kulinganisha
lazima kuwe juu ya data moja, la sivyo tofauti za chanzo zingeingia ndani ya kipimo cha
tofauti za resolution. Sampuli inachaguliwa kwa **hash** ya `(seed, symbol, muda)` — point ile
ile inaangaliwa kila run, kwenye kila mashine (sababu ile ile ya control sample, §4.3).

---

## 6. L3 — FEATURES

### 6.1 Sheria nane
1. **Scale-free.** Kila feature iwe log-return, ratio, z-score, percentile rank, au ATR-units.
   **Kamwe raw price.** Bei ya EURUSD 1.09 na XAUUSD 2400 haziwezi kulisha model moja.
2. **Point-in-time normalization.** Rolling/expanding kwa data ya nyuma pekee. Global `mean/std`
   ya dataset nzima ni uvujaji wa kawaida kabisa — hairuhusiwi.
3. **As-of** (§4.1) — bar isiyofungwa haiingii.
4. **Feature card ya lazima** (§6.3). Hakuna feature isiyo na hypothesis iliyoandikwa kabla.
5. **Bajeti** (§0.1): `labels ÷ features ≥ 50`. Kuvuka = kuomba over-fitting.
6. **Determinism:** fomula moja, mahali pamoja. ATR ya H1 ni function moja inayotumiwa na kila
   familia — haiandikwi upya.
7. **NaN ni NaN.** Window haijajaa → `is_valid=false`, si sifuri.
8. **Feature inayotokana na MODEL inafundishwa per-fold.** `hmm_state_post_k`, embeddings, na
   feature yoyote inayotokana na model iliyofundishwa (fitted) lazima ifundishwe kwa **expanding
   window / ndani ya fold ya train pekee** — HMM iliyofit dataset nzima inavujisha regimes za
   baadaye kwenye posterior za nyuma, na **sentinel ya §4.2 HAITAIGUNDUA** (shuffle ya data ya
   baadaye haibadilishi output ya model iliyoshafundishwa). Sheria hii ni ya S6 ya KAIROS-1.

### 6.2 Familia saba
| ID | Familia | TF | Mifano ya features |
|---|---|---|---|
| **F1** | Regime | D1 · H4 · H2 | `ret_z_n` · `trend_slope_atr` · `vol_ratio(short/long)` · `vol_pct_rank` · `hmm_state_post_k` · `range_pos` |
| **F2** | Structure | H4 · H1 · M30 · M15 | `bos_flag` · `mss_flag` · `sweep_flag` + `sweep_depth_atr` · `dist_swing_hi/lo_atr` · `ob_dist_atr` · `retest_count` |
| **F3** | Momentum / MR | H1 · M30 | `dist_ma_atr(20,50)` · `rsi_z` · `accel` · `consec_dir_bars` |
| **F4** | Volatility | TF zote | `atr_n` · `parkinson` · `garman_klass` · `vol_of_vol` · `atr_ratio(H1÷D1)` |
| **F5** | Time / Session | H1 | `sin/cos(hour)` · `sin/cos(dow)` · `session_{asia,london,ny,overlap}` · `mins_to_rollover` · `mins_to_news` · `news_impact` |
| **F6** | Cost / Micro | M5 | `spread_base_h1` · `spread_p95_m5` · `spread_effective` · `spread_vol` · `tick_intensity` |
| **F7** | Cross-asset | D1 · H1 | `corr_group_n` · `rel_strength_vs_basket` · `usd_proxy_ret` |

**F6 ni ya kusoma tu.** RCE ndiyo **mamlaka** ya `cost_pips` (§4.2 ya KAIROS-1). Model inapokea
namba za RCE kama muktadha; **haihesabu** zake. Hakuna gharama mbili kwenye mfumo.

**F5 na news:** kalenda ya news ni data ya nje yenye hatari ya uvujaji (revisions). Inatumika kwa
**muda pekee** (dakika hadi tukio + impact tier iliyokuwa inajulikana kabla), si kwa matokeo.

### 6.3 FEATURE CARD (lazima kwa kila feature)
```yaml
name:        dist_ma_atr_20
family:      F3
tf:          H1
formula:     (close - SMA(close,20)) / ATR(14)
window:      20 bars (+14 kwa ATR)
inputs:      L2/H1[close,high,low]
hypothesis:  "Umbali kutoka wastani, ukiwa umepimwa kwa volatility, unatofautisha
              mwendelezo (trend) na kurudi (mean-reversion) ndani ya regime moja."
cost:        O(1) rolling
owner:       PD
added:       2026-08-03
status:      candidate | screened | accepted | LESSON
```

---

## 7. L5 — SPLITS

```
Purged K-fold + embargo:
   embargo = horizon × 1.5          (label zinapishana; bila purge, CV ni ya uongo)
Walk-forward anchored kwa uthibitisho wa mfuatano wa wakati.
HOLDOUT = 20% ya mwisho kwa mfuatano wa wakati — INAFUNGULIWA MARA MOJA, mwisho kabisa.
```
- Split ni ya **wakati**, si random. Random split kwenye data ya soko ni uvujaji.
- Pooled training: symbols zote kwenye fold ile ile ya wakati (si symbol kwenye fold tofauti).
- Pre-registration: vigezo vya kupita vimeandikwa kabla ya kuona namba (§6 ya KAIROS-1).

---

## 8. FINGERPRINT NA UZALISHAJI UPYA

Kila dataset inatoka na `manifest.json`:
```json
{
  "dataset_id":   "ds_2026-08-03_h1_pooled_v1",
  "l0_hashes":    {"EURUSD/2021": "sha256:...", "...": "..."},
  "config_hash":  "sha256:... (config/data.yaml)",
  "code_rev":     "git sha ya research repo",
  "tf_set":       ["D1","H4","H2","H1","M30","M15","M5"],
  "features":     ["...", "..."],
  "labels":       {"family": "L-B", "horizon": 24, "grid": {"sl_atr": [...], "tp_atr": [...]}},
  "splits":       {"folds": 5, "embargo_bars": 36, "holdout_frac": 0.2},
  "quality":      {"coverage": 0.997, "failed_partitions": []}
}
```
**Matokeo yoyote ya utafiti yanataja `dataset_id`.** Namba isiyo na dataset_id haiingii kwenye
engine — ndio unavyotimizwa mtiririko wa upande mmoja (sheria 2 ya README).

---

## 9. MUUNDO WA FOLDA (`research/` — ndani ya repo, data haipushwi)
```
research/
├── data/             ← HAIPUSHWI (.gitignore: `research/data/`)
│   ├── L0_raw/       provenance=<aggregator|broker>/symbol=<SYM>/...  (immutable)
│   ├── L1_clean/     + quality_report.json
│   ├── L2_bars/      <symbol>/<tf>.parquet
│   ├── L3_features/  <dataset_id>/
│   ├── L4_labels/    <dataset_id>/
│   └── L5_datasets/  <dataset_id>/{train,val,holdout}.parquet + manifest.json
├── reports/          ← INAPUSHWA: quality/ · screening/ · ablation/ · calibration/
└── src/              ← INAPUSHWA: code ya utafiti
```

**Uamuzi wa PD 2026-08-04 (badiliko la §9):** `research/` inakaa **ndani ya repo**, si nje.
Sababu: reports (ushahidi wa kila awamu) na code ya utafiti zinasafiri na repo, kwa hiyo
attestation, LESSON na namba zinapatikana pamoja na spec zilizozizalisha. **Data pekee
(`research/data/`) haipushwi** — imezuiwa kwa ignore ya folda.

Mpaka wa engine↔utafiti **haujafutwa; umehamia kwenye code**, na sasa unatekelezwa na
mashine badala ya folda:

| Sheria (README 1 na 2) | Ilivyokuwa inalindwa | Inavyolindwa sasa |
|---|---|---|
| data haiingii repo | folda ilikuwa nje | `.gitignore` + **lango G11** (test) |
| engine hairudii code ya utafiti | folda ilikuwa nje | **lango G12** (test): `src/` (engine) hairuhusiwi ku-import `research/src` |
| mtiririko upande mmoja | folda ilikuwa nje | attestation + `dataset_id` (§8) — havijabadilika |

`research_root` inabaki kigezo cha config (`storage.research_root`, env `ELITEFX_RESEARCH_ROOT`)
— kwa hiyo **data inaweza kuhamishiwa diski nyingine wakati wowote** bila kubadilisha code wala
muundo (muhimu: L1–L5 zitahitaji nafasi kubwa kuliko L0). Repo inashikilia `research/reports/`
na `research/src/`; `research/data/` inaweza kuwa hapo hapo au mahali pengine kabisa.

Repo hii (engine) inapokea **models + namba zilizothibitishwa** pekee.

---

## 10. NJE YA WIGO
Sizing, malango ya risk, bajeti ya siku, execution → `docs/RISK_COST_ENGINE.md`.
Pipeline ya uamuzi, standards tano za model → `docs/KAIROS_1_STANDARD.md`.
Mfuatano wa kupima kila eneo → `docs/RESEARCH_PLAN_R0.md`.
