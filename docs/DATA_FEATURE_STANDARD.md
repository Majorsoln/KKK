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

### 0.1 Bajeti ya labels — hesabu halisi
```
H1 bars kwa mwaka  ≈ 24 × 5 × 52          = 6,240
Miaka 5, symbol 1                          = 31,200 bars
Setups zinazostahili (≈5% ya bars)         ≈ 1,560 labels
Bajeti ya features @ 50 labels/feature     ≈ 31 features        ← symbol MOJA
Pooled, symbols 7                          ≈ 10,900 labels → ≈ 218 features
```
**Matokeo ya hesabu hii (uamuzi wa design):** training ni **pooled** (symbols zote pamoja, features
zilizo scale-free + symbol embedding), si model kwa kila symbol. Model kwa kila symbol inagawanya
data mara saba bila kuongeza taarifa. Per-symbol inabaki kwa **calibration** pekee.

---

## 1. TABAKA ZA DATA (L0 → L5)

```
L0  RAW        ticks / M1 bid+ask kutoka broker      immutable · append-only · hashed
 │
L1  CLEAN      UTC · gaps · duplicates · sanity      ripoti ya ubora + PASS/FAIL
 │
L2  BARS       TF 7 zilizojengwa kutoka M1           + spread stats kwa kila bar
 │
L3  FEATURES   kwa TF, as-of closed bar pekee        feature card kwa kila moja
 │
L4  LABELS     quantile · barrier · fill · quality   zinatatuliwa kwa path ya M1
 │
L5  DATASETS   train / validation / holdout          manifest + fingerprint
```

Kila tabaka **haiandiki** juu ya lililo chini yake. L0 haibadilishwi kamwe — marekebisho yote ni
L1 na kuendelea, ili tuweze kujenga upya kila kitu kutoka chanzo.

---

## 2. L0 — RAW

| Kitu | Sharti | Sababu |
|---|---|---|
| Granularity | **M1** (tick ikipatikana, bora zaidi) | M1 ndiyo inatatua labels za touch (§5.2) |
| Bei | **bid NA ask** (OHLC pande zote) | spread ya kihistoria ni malighafi ya RCE §3.1; mid pekee = gharama ya kubuni |
| Volume | tick volume + real volume ikipatikana | intensity ya M5 (§4 F6) |
| Muda | timestamp ya server + **UTC** | rollover/swap ni server time; kila kitu kingine ni UTC |
| Umbizo | parquet, columnar, partition kwa `symbol/year` | kusoma sehemu bila kufungua yote |
| Hadhi | **immutable, append-only**, SHA256 kwa kila partition | reproducibility (kanuni 4) |

**Chanzo:** broker huyu huyu atakayetumika live. Data ya broker mwingine inaweza kutumika kwa
uchunguzi, **haiwezi** kutumika kuthibitisha namba zitakazoingia live — spread na fills ni zake.

---

## 3. L1 — USAFI NA MALANGO YA UBORA

Kila partition inapita ukaguzi huu. Ikifeli → **haitumiki kwa training**, na ripoti inaandikwa.

| # | Ukaguzi | Sheria | FAIL reason |
|---|---|---|---|
| 1 | **coverage** | bars zilizopo ÷ bars zinazotarajiwa (session calendar) ≥ `min_coverage` | `low_coverage` |
| 2 | **monotonicity** | timestamps zinapanda, hakuna duplicate | `bad_timestamps` |
| 3 | **gaps** | gap ndani ya session ≤ `max_gap_bars` | `intrasession_gap` |
| 4 | **OHLC sanity** | `low ≤ min(open,close) ≤ max(open,close) ≤ high` | `ohlc_violation` |
| 5 | **quote sanity** | `bid < ask`, `spread > 0`, `spread ≤ max_plausible` | `quote_violation` |
| 6 | **DST/session** | mabadiliko ya saa yanalingana na kalenda ya broker | `session_mismatch` |
| 7 | **clock drift** | tofauti ya server↔UTC ni thabiti | `clock_drift` |
| 8 | **flat bars** | mfululizo wa bars zenye `high==low` ≤ kikomo | `stale_feed` |

**Weekend, holiday na rollover si "gaps"** — ni kalenda. Kalenda inatengenezwa kwa data yenyewe
(bars zinazoonekana) na kuthibitishwa, si kudhaniwa.

**Sera ya NaN:** hakuna imputation ya kubuni. Bar isiyokamilika inabeba `is_valid=false` na
**haitumiki** kama decision point; inaweza kutumika kama history kwa window ndefu **kama** feature
inaruhusu (imeandikwa kwenye feature card).

---

## 4. L2 — BARS ZA TF 7 + AS-OF RULE

**Bars zote saba zinajengwa kutoka M1 kwenye repo yetu**, si kupakuliwa kutoka broker. Sababu:
broker anaweza kutumia mipaka tofauti ya bar; tukijenga wenyewe, D1/H4/H2/H1/M30/M15/M5 zote
zinatoka chanzo kimoja na zinalingana kikamilifu.

Kila bar inabeba, zaidi ya OHLCV:
```
spread_mean · spread_p50 · spread_p95 · spread_max      ← malighafi ya RCE §3.1
n_ticks · n_m1_bars · is_valid
```

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

---

## 5. L4 — LABELS (nne, kila moja kwa model yake)

Labels zinatatuliwa kwa **path ya M1**, si OHLC ya H1. Sababu: bar ya H1 inaonyesha kwamba high na
low zote mbili ziligusa — **haisemi ipi iligusa kwanza**. Bila M1, label ya barrier ni ubashiri.

### 5.1 L-A — QUANTILE (Quantile NN)
```
y = log(close[t+H] ÷ entry) ÷ ATR[t]        # terminal return, units za ATR
H = horizon (bars za H1, config)
```
Units za ATR (si pips) — inalinganisha symbols na volatility regimes (hoja ile ile ya S3).

### 5.2 L-B — BARRIER (p_tp_first) — **grid, si derived**
Anti-circularity (S1) inasema head inayoweka mipaka isihukumu. Kwa hiyo Barrier Model **hailishwi**
SL/TP zilizotoka Quantile head. Badala yake:

```
Kwa kila decision point, tengeneza labels kwa GRID ya barriers:
   sl_atr ∈ {0.5, 0.75, 1.0, 1.5, 2.0}
   tp_atr ∈ {0.5, 1.0, 1.5, 2.0, 3.0}
Fuata path ya M1 hadi horizon H:
   1 = TP iligusa kwanza · 0 = SL iligusa kwanza · timeout = darasa la tatu
```
**Matokeo:** `p_tp_first = f(features, sl_atr, tp_atr)` — barriers ni **INPUT**, si kitu
kilichotokana na model ile ile. Quantile head inapendekeza SL/TP, Barrier head inaziita kwa
grid iliyojifunza kwa uhuru. Mduara umekatika.

**Gap-honest:** stop = **touch** (si close). Gap ikiruka barrier, label inasoma touch kwenye bei
ya kwanza baada ya gap — ndivyo live itakavyokuwa.

### 5.3 L-C — FILL (P(fill))
Utekelezaji wa S4 kwa data ya kihistoria:
```
Kwa order ya aina A (market/stop/limit) kwenye bei X na cap C (config §slippage_cap_pips):
   fuata M1 kuanzia t:  je bei ilipatikana ndani ya X ± C kabla ya kupita?
   fill = 1 / 0        (+ rekodi slippage iliyohitajika)
```
Hii ndiyo inayoruhusu kuanza **bila kusubiri data ya broker**. Demo → fine-tune, live → calibrate.

### 5.4 L-D — QUALITY (XGBoost)
Inatokana na L-B + gharama, si label mpya:
```
R_net = (matokeo ya barrier kwa R) − (cost_pips ÷ sl_pips)
bucket:  A+ / A / B / reject   (mipaka kwenye config)
```

### 5.5 Sheria za labels
- **Horizon moja iliyotangazwa** kwa kila familia; kubadilisha horizon = dataset mpya, si tweak.
- **Class balance inaripotiwa**, haisawazishwi kwa kubuni (resampling inapotosha calibration).
- **Timeout haitupwi kimya** — ni taarifa (setup haikwenda popote).
- Label yoyote inayohitaji data baada ya `t + H` haipo.

---

## 6. L3 — FEATURES

### 6.1 Sheria saba
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

## 9. MUUNDO WA FOLDA (nje ya repo hii)
```
research/
├── data/
│   ├── L0_raw/       <symbol>/<year>/m1_bidask.parquet   (immutable)
│   ├── L1_clean/     + quality_report.json
│   ├── L2_bars/      <symbol>/<tf>.parquet
│   ├── L3_features/  <dataset_id>/
│   ├── L4_labels/    <dataset_id>/
│   └── L5_datasets/  <dataset_id>/{train,val,holdout}.parquet + manifest.json
├── reports/          quality/ · screening/ · ablation/ · calibration/
└── src/
```
Repo hii (engine) inapokea **models + namba zilizothibitishwa** pekee.

---

## 10. NJE YA WIGO
Sizing, malango ya risk, bajeti ya siku, execution → `docs/RISK_COST_ENGINE.md`.
Pipeline ya uamuzi, standards tano za model → `docs/KAIROS_1_STANDARD.md`.
Mfuatano wa kupima kila eneo → `docs/RESEARCH_PLAN_R0.md`.
