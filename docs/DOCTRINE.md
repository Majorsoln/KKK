# ELITEFX — DOCTRINE
## Injini ya Kugundua Strategy Kiotomatiki

**Toleo:** 1.0 · **Tarehe:** 2026-08-18 · **Hadhi:** contracts zimefungwa (A1–A10)
**Haigusi:** `docs/RISK_COST_ENGINE.md` na `config/risk.yaml` — RCE ni mamlaka huru ya
gharama na ukubwa, na haiko chini ya hati hii.

---

## 1. Mfumo ni nini

ELITEFX ni **injini inayogundua strategy zake yenyewe kutoka kwenye data**, inazipima kwa
pesa halisi baada ya gharama, na inagawa kipaumbele kwa zile zinazoonyesha uthabiti —
au inazizuia.

Si signal generator. Si model moja inayotabiri bei. Ni mfumo wa hatua tatu:

| hatua | swali | tokeo |
|---|---|---|
| **KUGUNDUA** | ni sheria zipi zinazozalisha trades kwenye pair hii? | maktaba ya strategies |
| **KUPIMA** | kila moja inaingiza pips ngapi kwa mwezi, baada ya gharama zote? | rekodi kwa kila (strategy × pair) |
| **KUGAWA** | ipi inapewa kipaumbele, ipi inazuiwa? | uzito, au veto |

### 1.1 Vipimo vina madaraja MANNE, na havichanganywi

Kila metric ina kazi **moja**. Metric ikitumika kwa kazi mbili, mojawapo itakuwa
inadanganya.

| daraja | vipimo | kazi |
|---|---|---|
| **PRIMARY OUTCOME** | `net_pips_month` **na** `net_account_return_month` (§1.2) | ndicho tunachokitafuta. Ndicho kinachoripotiwa nje. |
| **GATE** | metric yoyote yenye `noise_floor[metric]` (§9.2) | inapitisha au inakataa. Hakuna kingine kinachopitisha. |
| **RANKING** | `fitness` (§13) | inapanga walionusurika kwa kuangaliwa kwanza. **Haipitishi.** |
| **DIAGNOSTIC** | `expectancy` · `PF` · `Sharpe` · `DD` · `MFE` · `MAE` · `fill_rate` · `stability` | inaeleza **kwa nini**. Haipitishi wala haipangi. |

**Sheria:** metric isiyokuwa na `noise_floor` yake **haiwezi kuwa lango**. Inaweza kuwa
diagnostic pekee. Hilo linazuia kile kinachotokea kwa urahisi zaidi kuliko kitu
kingine chochote: kupima kwa kipimo kimoja na kuhukumu kwa kingine.

### 1.2 PRIMARY OUTCOME ni MBILI, na pesa ndiyo yenye mamlaka

Vinajibu maswali mawili tofauti:

| | inajibu nini |
|---|---|
| `net_pips_month` | *strategy imezalisha mwendo kiasi gani, bila kujali njia ya sizing?* |
| `net_account_return_month` | *strategy ile ile imezalisha kiasi gani baada ya RCE kuamua ukubwa kulingana na hali ya hatari?* |

Vinatengana kwa sababu ya mnyororo huu (RCE §2, §4):

```
DD ↑  →  budget ↓  →  risk_per_trade ↓  →  lots ↓
```

**Pips hazitegemei mpangilio. Pesa zinategemea.** Seti ile ile ya trades — 25 za
−30 pips na 13 za +60 pips, jumla **+30 pips** — inatoa:

| mpangilio | pips | pesa |
|---|---|---|
| hasara kwanza | +30 | **−$72.21** |
| faida kwanza | +30 | **+$52.68** |

**Ishara inageuka kwa mpangilio pekee.**

#### Mkataba

```
AUTHORITY: net_account_return_month
```

Ishara zikipingana, `net_account_return_month` ndiyo inayoamua. Na candidate
inapewa alama:

```
pip_sign        ∈ {POSITIVE, NEGATIVE}
money_sign      ∈ {POSITIVE, NEGATIVE}
path_dependence = (pip_sign ≠ money_sign)
```

`path_dependence = TRUE` **si kufeli peke yake** — ni **onyo lililoandikwa**
linalosema strategy inategemea mfuatano wa wins/losses, si tu wastani wao.
Halifichwi kwenye muhtasari; linaonekana kwenye ripoti ya candidate.

---

## 2. Injini haiamini kitu chochote kabla haijakipima

Kanuni inayotawala hati hii nzima:

> **Namba yoyote inayoingia kwenye uamuzi lazima ipimwe na injini yenyewe, kwenye
> mchakato huu, kabla ya kutumika.** Hakuna constant inayorithiwa. Hakuna tokeo la awali
> linalochukuliwa kama msingi. Kila kitu kinapimwa upya.

Kwa hiyo **kabla ya strategy yoyote kuzalishwa**, injini inaendesha ukaguzi wa data na
calibration mbili. Bila hizo, generator haifunguki.

```
   HATUA 0 — UKAGUZI                      HATUA 1 — CALIBRATION
   ┌────────────────────┐                ┌────────────────────────┐
   │ ubora wa data      │                │ A. GHARAMA HALISI      │
   │ (§4) — hakuna      │───────────────▶│    kwa trade, kwa pair │
   │ kinachopita        │                │    (§8)                │
   │ bila kuhakikiwa    │                ├────────────────────────┤
   └────────────────────┘                │ B. SAKAFU YA KELELE    │
                                         │    pipeline nzima juu  │
                                         │    ya data bandia (§9) │
                                         └───────────┬────────────┘
                                                     │  malango mawili
                                                     ▼  yameshawekwa
                                            HATUA 2 — KUTAFUTA
```

**Mpangilio si wa hiari.** Sakafu ya kelele inapimwa **kabla** generator haijaonyesha
strategy hata moja. Tukiona strategy nzuri kabla ya kujua "nzuri" ni nini, hatutaweza
kusahau tulichokiona.

---

## 3. Mtiririko kamili

```
     Research universe : 2016-01  →  2026-04
     Discovery/training: 2016-01  →  2024-03
     HOLDOUT (§16)     : 2024-04  →  2026-04   ← haiguswi hadi mwisho
                           │
                  ┌────────▼────────┐
                  │ Data Quality &  │  §4 — kila mara, si mara moja
                  │ Normalization   │
                  └────────┬────────┘
                  ┌────────▼────────┐
                  │  Feature Engine │  §5
                  └────────┬────────┘
              ┌────────────┴────────────┐
              ▼                         ▼
       Market Regimes  §6          Event Engine  §7
              └────────────┬────────────┘
                           ▼
                  Strategy Generator  §10
              ┌────────────┴────────────┐
              ▼                         ▼
       Rule-based Search          ML Discovery
              └────────────┬────────────┘
                           ▼
                ╔══════════════════════╗
                ║  LANGO LA UCHUMI §8  ║   gross ≥ 2 × gharama
                ╚══════════┬═══════════╝   kabla ya takwimu yoyote
                           ▼
                  Backtest Engine  §11
                           ▼
                Purged Walk-Forward · CPCV  §12
                           ▼
                ╔══════════════════════╗
                ║  SAKAFU YA KELELE §9 ║   dhidi ya kizingiti
                ╚══════════┬═══════════╝   kilichopimwa, si kilichodhaniwa
                           ▼
                  Strategy Database  §13
                           ▼
                  Training Dataset  §14
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          LightGBM     XGBoost        LSTM        §15
              └────────────┼────────────┘
                           ▼
                      Meta Model
                           ▼
              BUY · SELL · **NO TRADE**
                           ▼
                Holdout — kuguswa MARA MOJA  §16
```

---

## 4. Mkataba wa data

### 4.1 Ingizo — ticks za bid/ask, si OHLC

```
   RAW TICKS  2016-01 → 2026-04
   ├── timestamp   (UTC, µs)
   ├── bid
   └── ask
            │
            ▼
      Data Quality  (§4.3)
            │
            ▼
      Bar Builder
            │
   ┌────┬────┬─────┬────┬────┬────┬────┐
   M5   M15  M30   H1   H2   H4   D1
   └────┴────┴─────┴────┴────┴────┴────┘
            │
            ▼
   OHLC · spread · features · events · regimes · strategies
```

**OHLC haipokelewi kama ingizo.** Inazalishwa. Sababu si upendeleo — ni kwamba mambo
matano ya doctrine hii **hayawezi kutekelezwa** bila bid/ask:

| kinachovunjika bila ticks | kinatumika wapi |
|---|---|
| spread halisi kwa kila trade | §8 Calibration A — lango zima la uchumi |
| entry kwa `ask`, exit kwa `bid` | §11 backtest — bila hii kila return imevimba |
| utekelezaji kwa kiwango cha tick | §11 — kugusa kwa barrier kunatokea ndani ya bar |
| calibration ya slippage | §12 robustness |
| calibration ya gharama ya RCE | §18 |

Data ya OHLC inatosha kwa **prototype**. Haitoshi kwa ELITEFX. **Doctrine
haibadilishwi ili iendane na data iliyopo** — data ndiyo inayotafutwa ili iendane na
doctrine.

### 4.2 Volume

`bid_vol` / `ask_vol` za FX ni **za kiashiria, si volume ya soko** — hakuna exchange
inayoripoti volume ya kweli ya spot FX. Kwa hiyo:

* Volume ya broker **haitumiki** kama feature.
* Kinachotumika ni **idadi ya ticks kwa bar**, inayohesabiwa na Bar Builder. Ni kipimo
  halisi cha shughuli za soko, na kinatoka kwenye data yetu wenyewe.

### 4.3 Ukaguzi

Kila pair, kila mwaka, inapita ukaguzi ufuatao **kila inapopakiwa**, si mara moja:

| ukaguzi | kigezo | daraja |
|---|---|---|
| timezone | UTC pekee, kila mahali | FATAL |
| mpangilio | timestamps zinapanda, hakuna kurudi nyuma | FATAL |
| duplicates | hakuna tick mbili zenye muda **na** bei zile zile | FATAL |
| **quotes zilizovuka** | **`bid ≤ ask` kila tick** | **FATAL** |
| bei halali | zote ni chanya, zenye ukomo | FATAL |
| mpaka wa dirisha | kila tick iko ndani ya dirisha lililotangazwa (§16.1) | FATAL |
| OHLC | `low ≤ open, close ≤ high` kwa kila bar | FATAL |
| **ya baadaye** | **hakuna thamani ya bar `t+k` inayoonekana kwenye row ya `t`** | FATAL |
| mapengo | pengo linalozidi ukimya wa wikendi haliwezi kudhaniwa | WARN |
| wikendi | hakuna tick ya Jumamosi — dalili ya timezone ya chanzo | WARN |
| spread kubwa | ikizidi kikomo kilichotolewa | WARN |

**`bid ≤ ask` ni FATAL kwa sababu ya kiuchumi, si ya kiufundi.** `bid > ask`
inatoa spread **hasi**, ambayo inatoa gharama **hasi** — pesa ya bure kwenye
kila trade inayoigusa. Ni aina hatari zaidi ya data mbovu kwa sababu
**haijionyeshi kama kosa kwenye matokeo; inajionyesha kama edge.**

Ukaguzi wa mwisho ndio pekee usio na msamaha: **ukishindwa, kila namba inayofuata ni ya
uongo,** na haitajionyesha kwenye matokeo kama kosa — itajionyesha kama faida.

Bars zinajengwa kutoka ticks kwa TF zote za §17. Spread ya kila bar inahifadhiwa,
haikadiriwi.

---

## 5. Feature Engine

Kwa kila bar `t`, maelezo ya hali ya soko yanayotumia **data iliyokuwa inajulikana
wakati huo tu**.

| kundi | features |
|---|---|
| returns | `return_{1,3,5,10,20,50}` |
| volatility | `ATR_14`, `ATR_20`, `std_20`, `std_50`, `ATR_percentile_252d`, `vol_regime_252d` |
| trend | `EMA_{20,50,100,200}`, tofauti zao, `slope_EMA_{20,50,200}` |
| momentum | `RSI`, `ROC`, `MACD`, `ADX` |
| muundo wa candle | `body`, `upper_wick`, `lower_wick`, `range`, `body/range`, `close_pos_in_range` |
| nafasi sokoni | `dist_from_high_{20,50}`, `dist_from_low_{20,50}`, `dist_from_EMA200` |
| muda | `hour`, `day_of_week`, `session`, `minutes_from_session_open` |
| shughuli | `tick_count`, `tick_count_percentile_252d` — kutoka ticks, si volume ya broker (§4.2) |
| spread | `spread_p50`, `spread_per_atr` — kutoka ticks halisi (§4.1) |

**Sheria mbili zisizovunjika:**

* Feature ya bar `t` inatumia **hadi bar `t` ikiwa imefungwa**. Rolling extremes
  zinatumia `[t−1]`, si `[t]`.
* **Kila percentile inatangaza dirisha lake ndani ya JINA lake.** `ATR_percentile`
  bila dirisha **hairuhusiwi kuwepo kwenye code**. Sababu: percentile juu ya sample
  nzima ingempa bar ya 2017 taarifa ya volatility ya 2020 — uvujaji ambao hakuna
  test itakayouona, na utakaojionyesha kama ustadi.
* Feature yoyote inayotokana na model iliyofit inafundishwa **expanding au per-fold**,
  kamwe si juu ya sample nzima.

---

## 6. Regimes

Soko haliko katika hali moja. Regime inaelezwa kwanza kwa sheria (ADX, EMA, ATR
percentile), na baadaye kwa clustering (KMeans · GMM · HMM) ikiwa clustering itashinda
sheria kwenye §12.

**Regime detector ni `model-derived feature`, kwa hiyo iko chini ya sheria ya §5 bila
ubaguzi:** inafundishwa **expanding au per-fold, kamwe si juu ya sample nzima.** HMM
iliyofit juu ya 2016–2024 kisha kutumika kwa 2017 ni uvujaji wa moja kwa moja, na
haitajionyesha kama kosa — itajionyesha kama regime detection nzuri.

**Kipimo cha sample kwa regime ni tofauti, na ni kigezo:** hypothesis ya regime
haipimwi kwa idadi ya **trades**, bali kwa idadi ya **matukio huru ya regime**. ER na
ADX ni variables za polepole; trades elfu ndani ya regimes mia si sample ya mia moja
tu — ni sample ya mia. Regime yoyote inayodai kufanya kazi lazima iripoti idadi hiyo.

---

## 7. Event Engine

Si kila bar ni trade. Events ndizo trigger:

`BREAKOUT` · `PULLBACK` · `TREND_CONTINUATION` · `MEAN_REVERSION` ·
`VOLATILITY_EXPANSION` · `VOLATILITY_CONTRACTION` · `MOMENTUM_SHIFT`

Mfano wa breakout: `close[t] > rolling_high_20[t−1]` — **si** `rolling_high_20[t]`.
Kanuni ya §5 inatumika hapa bila upole.

---

## 8. GHARAMA — ufafanuzi MMOJA, matumizi mawili

### 8.1 Ufafanuzi mmoja

Mfumo mzima una **dhana moja** ya gharama. Haigawanyiki kwa hati.

```
REALIZED_TRADING_COST
├── ENTRY_COST    = nusu ya spread (kuingia) + slippage (kuingia) + nusu ya commission
├── EXIT_COST     = nusu ya spread (kutoka)  + slippage (kutoka)  + nusu ya commission
└── HOLDING_COST  = swap × idadi ya usiku
```

`total_expected_cost = ENTRY + EXIT + HOLDING`.

**Commission iko ENTRY/EXIT, si HOLDING.** Inalipwa kwa **muamala**, si kwa muda —
trade ya saa moja na ya wiki mbili zinalipa commission ile ile. Kuiweka HOLDING
kungefanya strategy za muda mfupi zionekane ghali kuliko zilivyo, na ndefu nafuu
kuliko zilivyo.

`config/risk.yaml` ina `commission_side: "round_turn"` — thamani ya `broker_costs.yaml`
ni ya **pande MBILI**. Kwa hiyo inagawanywa nusu kwa nusu hapa, **haitozwi mara mbili**.

**Chanzo ni kimoja:** ticks za bid/ask (§4) kwa spread na slippage; **RCE** (§18) kwa
commission na swap. Doctrine haikadirii commission wala swap, na RCE haikadirii
spread ya kihistoria.

### 8.2 Matumizi mawili ya chanzo kile kile

Hapa ndipo ilipokuwa hatari ya kujidanganya, kwa hiyo imeandikwa wazi:

| | `research_cost` | `live_sizing_cost` |
|---|---|---|
| ni nini | gharama **halisi** iliyotokea kwenye tick ile ile | **makadirio ya kihafidhina** ya mbele |
| spread | tick halisi wakati wa kuingia | `max(spread_H1_baseline, p95(spread_M5))` |
| slippage | iliyopimwa, ikiwa ndani ya cap | cap iliyowekwa na RCE |
| inatumika | backtest, lango la §8.4, `net_return` | ukubwa wa lots (RCE) |
| inamiliki | Doctrine | RCE |

> **`research_cost ≠ live_sizing_cost`, na si kosa.** Moja ni **kilichotokea**,
> nyingine ni **kadirio la kihafidhina la kitakachotokea**. Zote zinatoka kwenye data
> ile ile ya msingi.

Kudai kwamba backtest na live zina gharama ile ile kungekuwa uongo unaojionyesha kama
faida. **`live_sizing_cost ≥ research_cost` daima**; ikiwa si hivyo kwa `(pair, TF)`
yoyote, calibration imevunjika na injini inasimama.

### 8.3 Calibration A — injini inapima gharama yake yenyewe

Kabla ya strategy yoyote, kwa kila `(pair, TF)`:

```
research_cost_ATR    = (ENTRY + EXIT + HOLDING) ÷ ATR      ← ticks halisi
live_sizing_cost_ATR = RCE spread_effective + cap + comm   ← kihafidhina
```

Tokeo ni jedwali lenye safu **zote mbili**, pamoja na ukaguzi wa
`live ≥ research`. Linahifadhiwa kama ushahidi wenye tarehe (R5).

### 8.4 Lango — ni chujio la kiuchumi, si uthibitisho

> **Candidate yenye `gross edge kwa trade < 2 × live_sizing_cost` inakataliwa kabla ya
> takwimu yoyote kuhesabiwa.**

**Mamlaka ni `live_sizing_cost`, si `research_cost`.** Swali si *"ilikuwa na uchumi
kihistoria?"* bali *"ina uchumi chini ya gharama ambayo RCE itaitumia kweli
kuiweka ukubwa?"* Kutumia ya matumaini kimya ndiyo aina hasa ya dhana inayofanya
mfumo uonekane wenye faida bila kuwa nao.

**Zote mbili zinaripotiwa, kwa sababu tofauti yao ni kipimo cha udhaifu:**

| | `edge ÷ research_cost` | `edge ÷ live_sizing_cost` | tafsiri |
|---|---|---|---|
| dhaifu | 3.2× | **1.7×** | inategemea gharama kubaki nzuri |
| imara | 3.2× | **2.8×** | inastahimili gharama mbaya |

`cost_sensitivity = (edge ÷ research) ÷ (edge ÷ live)` inaingia kwenye Strategy DNA.

Sababu ya lango: gharama ni **thabiti kwa kila trade** — haibadiliki trade ikiwa
kubwa au ndogo. Kwa hiyo tatizo kamwe si trades za bei ghali; ni **trades ndogo mno**.

`2×` na si `1×` kwa sababu `1×` inadai makadirio yawe sahihi kabisa. `2×` inaacha
nafasi ya slippage, kuzorota kwa spread, na makosa ya utekelezaji.

**Lakini `2×` si ukweli wa kitakwimu, na haipitishi chochote.** Candidate yenye
`1.9×` inaweza kuwa ya kweli; yenye `3×` inaweza kuwa kelele. Lango hili ni la bei
nafuu na linakata wagombea wengi kwa hesabu ya mstari mmoja — thamani yake ni
**kupunguza idadi ya majaribio**, ambayo ndiyo inayotawala §9. Uamuzi unabaki hapa:

```
2 × cost  →  backtest  →  validation  →  sakafu ya kelele  →  UAMUZI
```

---

### 8.5 R16 inasimamia TF ya UTEKELEZAJI (Calibration A, 2026-08-23)

Calibration A ya kwanza — cells 84, symbols 12, TF 7, ticks bilioni ~2.7, miaka 8
(`research/reports/calibration_a.json`) — ilitoa matokeo yenye muundo mmoja
usiobadilika:

| | matokeo |
|---|---|
| **H1** (TF ya utekelezaji) | `live ≥ research` kwenye symbols **12/12**, `sens` 1.09–1.52 |
| **D1** | `live < research` kwenye **11/12** |
| M5 · M15 · M30 · H2 · H4 | zote zinapita |

Sababu ni **saa, si timeframe**. Mpaka wa bar ya D1 ni saa sita usiku ya seva —
rollover ya kila siku, wakati spread ni pana zaidi. Spread iliyopimwa kwenye
mpaka wa D1 dhidi ya ya H1, symbol kwa symbol:

```
AUDUSD 1.64×  NZDUSD 1.87×  USDCAD 2.39×  EURGBP 2.42×  GBPUSD 2.59×
USDJPY 2.64×  EURJPY 2.60×  EURUSD 2.65×  USDCHF 3.29×  GBPJPY 4.11×
EURCHF 4.35×  XAUUSD 2.36×                              (kati: 2.60×)
```

`spread_effective` ya RCE inachukua wastani wa **saa zote**, kwa hiyo inadharau
gharama ya kutekeleza saa hiyo mahususi. Hiyo si kasoro ya RCE wala ya kipimo;
ni ukweli kuhusu soko ambao kipimo cha wastani hauwezi kuubeba.

**Uamuzi:** R16 inatathminiwa kwenye `bars.decision_tf` (H1, kwa R11). Cells za TF
nyingine zinaripotiwa kama **diagnostic** — zina taarifa ya kweli, lakini si za
kitu kinachotekelezwa. Kuchanganya mbili hizo kungefanya kimoja kati ya viwili:
kusimamisha injini kwa TF isiyotekelezwa, au kulegeza R16 hadi isishike kitu.

**Kilichokataliwa:** cap ya slippage ingeweza kupandishwa hadi D1 ipite. Pengo la
D1 ni la **spread**; kuliziba kwa namba ya **slippage** kungekuwa ni kufanya
hesabu itoe jibu badala ya kupima. Ushahidi kwamba kuepuka huko kulikuwa sahihi:
caps zilipopandishwa (0.1 → 0.3–12.0, zote kutoka kipimo), D1 iliendelea kuvunjika
kwenye 11/12.

---

## 9. SAKAFU YA KELELE — kizingiti kinapimwa, hakidhaniwi

### 9.1 Tatizo, kwa hesabu

Kadri unavyojaribu strategies nyingi zaidi, ndivyo bora zaidi kati yao inavyoonekana
nzuri **hata kama hakuna hata moja yenye edge**. Hii si dhana; ni tabia ya `max` ya
sampuli `K`.

Kwa strategies **zisizo na edge kabisa**, miezi 96, miaka 8:

| zilizojaribiwa | miezi yenye faida ya **bora** | Sharpe ya **bora** |
|---|---|---|
| 100 | 63% | 1.07 |
| 1,000 | 66% | 1.31 |
| 10,000 | 69% | 1.52 |
| 100,000 | **74%** | **1.70** |

Strategies 100,000 zisizo na thamani yoyote zinazalisha bora yenye **74% ya miezi na
Sharpe 1.70.** Ingeonekana kama mfumo wa dhahabu.

Na kwa **miaka** ni mbaya zaidi: cells 96 tu zisizo na edge zinatoa bora yenye **miaka
7 kati ya 8** yenye faida.

> **Kwa hiyo uthabiti unapimwa kwa MIEZI, si kwa miaka.** Miaka nane ni pointi nane —
> hazina uwezo wa kutofautisha ustadi na bahati.

### 9.2 Calibration B — injini inapima sakafu yake yenyewe

Jedwali hapo juu ni la nadharia. Sakafu halisi ya mchakato **wetu** inapimwa hivi:

```
endesha PIPELINE NZIMA — generator, lango la uchumi, backtest,
robustness, walk-forward, CPCV — juu ya DATA BANDIA isiyo na edge.
```

Data bandia inahifadhi tabia za kitakwimu za data halisi (volatility clustering,
mgawanyo wa returns, muundo wa spread) lakini **haina uhusiano wowote wa kutabirika**.

**Familia MOJA ya null haitoshi.** Sakafu inayotokana na generator moja ya data bandia
ni sehemu **tabia ya soko** na sehemu **tabia ya generator** — na hatuwezi kutofautisha
mbili hizo kwa kuangalia. Kwa hiyo Calibration B inaendeshwa kwa familia **tatu**
zisizohusiana:

| familia | inahifadhi nini | inavunja nini |
|---|---|---|
| **A · block resample** | autocorrelation ya ndani ya block | uhusiano kati ya blocks |
| **B · regime-preserving shuffle** | urefu na mpangilio wa regimes | mfuatano ndani ya regime |
| **C · return surrogate** | mgawanyo na wigo wa returns | awamu (phase) yote |

```
noise_floor[metric] = max( p95_A[metric], p95_B[metric], p95_C[metric] )
```

**Sakafu ni kwa kila METRIC, si namba moja.** Sakafu ya `Sharpe` haiwezi kuhukumu
`net pips/mwezi` — ni vipimo tofauti vyenye mgawanyo tofauti chini ya null ile ile.
Kila lango linapima metric yake dhidi ya sakafu yake:

```
noise_floor.net_pips_month
noise_floor.profitable_month_fraction
noise_floor.sharpe
noise_floor.profit_factor
noise_floor.max_drawdown          ← hapa ni p5, si p95 (ndogo ni bora)
noise_floor.fill_rate
```

Kila run ya Calibration B inatoa **jedwali**, si namba. Metric isiyokuwa na sakafu
yake **haiwezi kuwa lango** — inaweza kuwa diagnostic pekee (§13).

**`max`, si wastani.** Familia yoyote ikitoa sakafu ya juu, hiyo ndiyo inayotumika —
kwa sababu tofauti kati yao ni kipimo cha kutokuwa na uhakika kwetu wenyewe, na
kutokuwa na uhakika hakupunguzi bar.

Kile ambacho injini "inagundua" pale ndiyo **sakafu**. Kizingiti cha strategy halisi ni
sakafu ile — si 50%, si 85%, si namba yoyote iliyochaguliwa na binadamu.

### 9.3 Sheria tatu

**S1** — `variants_tested` inahesabiwa daima, ikiwemo waliokufa mapema, na inaingia
kwenye kila ripoti.

Si namba inayotolewa na generator (`len(walionusurika)` si hesabu — ni matokeo).
Ni **ledger ya matukio isiyofutika**, row moja kwa kila candidate iliyowahi kuzalishwa:

```
candidate_id · generation · parent_ids · variant_hash
tested_at · stage_reached · reject_reason
```

Ili swali hili lijibike kwa ushahidi, si kwa kumbukumbu:

> *"Strategy hii ilichaguliwa baada ya kujaribu variants ngapi?"*

**S2** — kizingiti kinatoka Calibration B pekee.

**S3** — Sharpe inayoripotiwa ni **deflated** kwa `variants_tested`, si ghafi.

Hii **si** kizuizi cha utafutaji mkubwa. **Ndiyo inayoufanya utafutaji mkubwa uwe na
maana** — bila sakafu, kadri unavyotafuta zaidi ndivyo unavyodanganyika zaidi.

---

## 10. Strategy — ufafanuzi na muundo

### 10.1 Ufafanuzi

> **Strategy ni uchambuzi KAMILI: kutoka data ghafi hadi entry NA exit yake.**

Exit inatangazwa **ndani ya** strategy. Haitafutwi baadaye, na haiboreshwi baada ya
kuona matokeo. Strategy mbili zenye entry ile ile na exit tofauti ni **strategy mbili
tofauti**, na zote mbili zinahesabiwa kwenye `variants_tested`.

### 10.2 Muundo

Kila strategy ina umbo lile lile, vinginevyo hazilinganishwi:

```
STRATEGY
  strategy_id            regime inayolengwa
  entry_conditions       exit_conditions
  sl_type + parameter    tp_type + parameter
  time_stop              position rule
  features_used          complexity
```

### 10.3 Generator

Condition library (EMA, RSI, ADX, ATR percentile, returns, distance, breakout) pamoja
na `AND` · `OR` · `NOT`.

**`max_conditions` = 3–5.** Strategy yenye masharti 15 inaweza kuonekana nzuri kwa
sababu imekariri historia, na complexity inaadhibiwa kwenye §13.

Njia mbili, zote zinalisha bwawa moja:

* **Rule Discovery** — mchanganyiko wa masharti
* **ML Discovery** — feature importances na interactions kutoka tree models,
  zikigeuzwa kuwa masharti yanayoweza kusomwa

Njia ya pili haipendelewi kwa sababu ni ya kisasa; ipo kwa sababu **hutegemei
hypothesis zako pekee.**

### 10.4 Evolution

Vizazi vinavyofuata (mutation, recombination) vinaruhusiwa **chini ya bajeti ya
`variants_tested` iliyotangazwa mapema.** Kila kizazi kinaongeza hesabu, na sakafu ya
§9 inapanda pamoja nayo.

**`max_conditions` ni invariant, si kigezo cha kizazi cha kwanza:**

```
child_conditions ≤ max_conditions        ...baada ya KILA mutation/recombination
```

Mzazi mwenye masharti 4 na mwenye 4 wanaweza kutoa mtoto mwenye 8. Mtoto huyo ni
`INVALID_CANDIDATE` **kabla ya backtest** — hahesabiwi kwenye `variants_tested` kwa
sababu hakupimwa, lakini anaandikwa kwenye ledger ya §9.3 na `reject_reason`.

---

## 11. Backtest Engine

### 11.1 Utekelezaji una matokeo MAWILI, si moja

Signal si trade. Kati yao kuna utekelezaji, na unaweza kushindwa:

```
signal  →  bei iliyoombwa  →  soko limehama  →  slippage > cap  →  HAKUNA FILL
signal  →  bei iliyoombwa  →  ndani ya cap   →  FILL kwa bei halisi
```

RCE inaweka cap ya slippage, na order inayozidi cap **haijazwi** (§18). Lakini kabla
ya utekelezaji kuna **ukaguzi wa RCE**, na huo unaweza kukataa kwa sababu tofauti
kabisa. Kwa hiyo signal inapita **hatua mbili**, si moja:

```
                    SIGNAL
                      │
              ┌───────▼────────┐
              │   RCE CHECK    │   ← si utekelezaji; ni RUHUSA
              └───────┬────────┘
        ┌─────────────┼──────────────────────────┐
        │             │                          │
   NO_BUDGET   MIN_LOT_REJECT          reject nyingine za RCE §5:
  (budget ≤ 0)  (risk_below_min_lot)   max_open_trades · max_correlated
        │             │                daily_loss_75pct_with_open
        │             │                max_total_dd · max_spread · news_window
        └─────────────┴──────────┬───────────────┘
                                 │  ...au PASS
                        ┌────────▼────────┐
                        │   EXECUTION     │
                        └────────┬────────┘
                     ┌───────────┴───────────┐
                   FILL                   NO_FILL
              (bei ndani ya cap)     (bei imezidi cap)
```

**`NO_BUDGET` si `NO_FILL`.** Ya kwanza inasema *"hatukuruhusiwa kujaribu"*; ya pili
inasema *"tuliruhusiwa, lakini soko lilihama."* Zikichanganywa, huwezi kujibu swali
muhimu zaidi la uchunguzi:

> *Strategy ilikufa kwa sababu haikuwa na edge, au kwa sababu RCE ilizuia hatari?*

**Kumbuka la kiufundi:** RCE haina reject reason inayoitwa `NO_BUDGET`. Budget
ikiisha, lots zinakuwa 0 na RCE inatoa `risk_below_min_lot` (`sizing.py:20`). Doctrine
inatofautisha mbili hizo kwa kurekodi `budget_at_signal` (§11.2) — `budget ≤ 0` ni
`NO_BUDGET`; `budget > 0` lakini lots chini ya `volume_min` ni `MIN_LOT_REJECT`.
**Hakuna kinachoongezwa kwa RCE**; tofauti inatoka kwenye rekodi ya Doctrine.

**Kwa nini hii si ya hiari.** Backtest ikidhani kila signal inajazwa wakati live
inakataa asilimia 30, basi:

* research inahesabu trades ambazo hazingetokea kamwe
* na — mbaya zaidi — zilizokataliwa **si sampuli ya nasibu**. Zinakataliwa pale bei
  ilipohama haraka, ambako ndiko trades bora **na** mbaya zaidi zinapoishi

Pengo la research-dhidi-ya-live linarudi kwa mlango huu, likiwa limejificha ndani ya
namba inayoonekana sahihi.

### 11.2 Rekodi kwa kila **jaribio**, si kwa kila trade

```
signal_time · requested_price · direction

rce_outcome ∈ {PASS, NO_BUDGET, MIN_LOT_REJECT, max_open_trades,
               max_correlated, daily_loss_75pct_with_open,
               max_total_dd, max_spread, news_window}
budget_at_signal · risk_per_trade_at_signal
requested_lots · allowed_lots · broker_min_lot

execution_outcome ∈ {FILL, NO_FILL}   (ikiwa rce_outcome == PASS)
reject_reason                          (kwa NO_FILL)

...ikiwa FILL:
entry_time · entry_price · SL · TP
exit_time · exit_price · exit_reason
gross_return · entry_cost · exit_cost · holding_cost · net_return
MFE · MAE · holding_time
```

`MFE` (Maximum Favorable Excursion) na `MAE` (Maximum Adverse Excursion) ni za lazima:
ndizo pekee zinazoweza kujibu maswali ya kutoka baadaye, na haziwezi kurudishwa baada
ya backtest kuisha.

Gharama zimegawanywa kwa `ENTRY / EXIT / HOLDING` kama §8.1 — si namba moja ya
jumla, kwa sababu jumla haiwezi kukaguliwa dhidi ya RCE.

**Kwa nini `budget_at_signal` na wenzake ni wa lazima:** bila wao, `NO_BUDGET` ni
hesabu tupu. Nao, kila uamuzi unaweza kutolewa upya:

```
2021-03-14 09:00 · EURUSD · BUY
budget            = $37.20
risk_per_trade    = $5.31
requested_lots    = 0.007
broker_min_lot    = 0.01
rce_outcome       = MIN_LOT_REJECT
```

Hiyo ni **audit trail**, si log.

### 11.3 `fill_rate` ni kipimo cha validation

```
fill_rate = orders zilizojazwa ÷ orders zilizoombwa
```

Strategy yenye `Sharpe 1.8` na `PF 1.7` **lakini** `fill_rate 61%` wakati backtest
ilidhani 100% **si strategy ile ile**. Kwa hiyo `fill_rate` haiishi kwenye dashboard;
inaishi kwenye ripoti ya mwisho ya kila candidate, pamoja na:

```
research_fill_rate · OOS_fill_rate · live_fill_rate · fill_rate_gap
```

Candidate inakataliwa ikiwa `OOS_fill_rate < noise_floor.fill_rate` (§9.2) — si kwa
namba iliyochaguliwa.

**`fill_rate_min: 0.60` ya `config/risk.yaml` SI lango la utafiti.** Ni **onyo la
uendeshaji** la RCE kwa live. Vipimo viwili, vyenye kazi mbili:

| | chanzo | kazi |
|---|---|---|
| `fill_rate_min` = 0.60 | RCE, `config/risk.yaml:48` | onyo la live: cap ni ngumu mno |
| `noise_floor.fill_rate` | Calibration B (§9.2) | **lango la utafiti** |

Kizingiti cha utafiti kinatoka kwenye sakafu iliyopimwa **kabla ya holdout**, na
hakibadilishwi baada ya kuona matokeo.

### 11.4 Uhakiki uliojengwa ndani

Kila namba muhimu inayotoka kwenye engine lazima ifikiwe kwa **njia mbili
zinazojitegemea**, na tofauti yake ichapishwe. Mfano: return ya bar `t+24`
inayohesabiwa kutoka bars lazima ilingane na ile inayohesabiwa kutoka ticks.
Zisipolingana, moja ina kasoro — na tofauti yenyewe inaeleza ipi.

---

## 12. Validation

**Hatua za bei nafuu kwanza.** Usiendeshe backtest ya miaka 9 kwa kila candidate:

| hatua | kipindi | kazi |
|---|---|---|
| A | 2016-01 → 2020-12 | screening ya bei nafuu — kata wengi |
| B | 2016-01 → 2021-12 | |
| C | 2016-01 → 2022-12 | |
| D | 2016-01 → **2024-03** | walionusurika pekee |

**Walk-forward** juu ya walionusurika:

```
2016-01 → 2019-12  →  2020        2016-01 → 2021-12  →  2022
2016-01 → 2020-12  →  2021        2016-01 → 2022-12  →  2023-01 → 2024-03
```

**Hakuna pengo.** Kila mwezi kati ya 2016-01 na 2024-03 uko ndani ya train au test ya
walk-forward; kila mwezi kuanzia 2024-04 uko ndani ya holdout. Miezi ya 2024-01 →
2024-03 ni sehemu ya dirisha la mwisho la test, si eneo lisilo na mwenyewe.

**Purging na embargo** ni ya lazima pale label ina horizon ya baadaye: sample ya
training inayogusa kipindi cha test inaondolewa (purge), na buffer inaachwa baada ya
test (embargo).

**CPCV** inaongezwa baada ya walk-forward kwa kupima robustness dhidi ya overfitting.

**Robustness** — strategy nzuri haifi kwa mabadiliko madogo:

| jaribio | kigezo |
|---|---|
| parameter | EMA 45–55, si 50 pekee |
| SL/TP | SL 1.3–1.7 ATR, TP 1.8–2.2 SL |
| spread | 1×, 1.5×, 2× |
| slippage | ongeza gharama ya utekelezaji |
| muda | kila mwaka kando — inayofanya kazi mwaka mmoja pekee ni shaka |

**Overfit detector:** ripoti `IS` dhidi ya `OOS`. `IS 2.10 / OOS 1.28` inakubalika.
`IS 4.50 / OOS 0.91` inakataliwa.

---

## 13. Kupanga na kupitisha — vitu viwili tofauti

**Kupanga (ranking)** — fitness yenye uzito, ili kuona wagombea bora kwanza:

```
Fitness = 0.30 × expectancy + 0.20 × profit_factor + 0.15 × sharpe
        + 0.15 × stability − 0.10 × drawdown − 0.10 × complexity
```

**Kupitisha (gate)** — sakafu ya §9 **pekee**. Uzito hapo juu ni chaguo la binadamu, na
kila chaguo la binadamu ni digrii ya uhuru inayoweza kuchezewa. Haipitishi chochote.

Kwa hiyo: strategy yenye faida ndogo lakini thabiti inashinda yenye faida kubwa
isiyotabirika — na zote mbili lazima zivuke sakafu kabla hazijalinganishwa.

### Strategy Database

Kila mnusurika anahifadhiwa kama object kamili: metrics za `IS`, `OOS`, `WF`, `CPCV`,
`trade_count`, `profit_factor`, `expectancy`, `sharpe`, `max_drawdown`,
`stability_score`, `overfit_score`, pamoja na `variants_tested_when_found`,
`noise_floor_at_discovery`, na `cost_to_edge_ratio`.

---

## 14. Dataset ya ML

Strategies zilizonusurika **pekee** ndizo zinazozalisha training data. Kwa kila trade:

`X` = hali ya soko **kabla ya entry** · `strategy_id` · `regime` · `session` ·
`SL_distance` · `TP_distance`

`y` = si `WIN/LOSS` pekee, bali targets kadhaa:

```
y1 = TP kabla ya SL        y4 = MAE
y2 = return kwa R          y5 = holding_time
y3 = MFE
```

Targets nyingi zinafanya model ijifunze **tabia ya soko**, si tokeo la binary pekee.

---

## 15. Models

| model | kazi | mpangilio |
|---|---|---|
| **LightGBM** | `P(TP kabla ya SL)` kwa (hali ya soko + `strategy_id`) | wa kwanza |
| **XGBoost** | model huru ya pili | wa pili — **angalia uhusiano wa makosa**, si "ensemble ni nzuri" |
| **HMM / GMM** | regime | sambamba |
| **Bandit** | strategy ipi kwa pair ipi — kipaumbele au **veto** | baada ya database kujaa |
| **LSTM** | sequence ya bars 50 → probability | **mwisho** |
| **Meta model** | inaunganisha outputs | mwisho |

**Sheria tatu:**

1. **Hakuna model inayoingia kwa nafasi yake.** Inaingia kwa **kushinda baseline** kwenye
   purged CV. LSTM isiyoongeza `OOS` haitumiki.
2. **Cross-fitting:** output ya model inayolisha model nyingine ni **out-of-fold, daima.**
   Vinginevyo meta-model inajifunza ukamilifu usiokuwepo live.
3. **Threshold inatafutwa kwenye validation**, si kuwekwa `P > 0.5`.

### 15.1 `NO TRADE` ni darasa, si kizingiti

Model inatoa `P(BUY)` · `P(SELL)` · `P(NO_TRADE)`. Kutokutrade ni **uamuzi**
unaojifunzwa, si sheria iliyoongezwa juu ya model.

### 15.2 Aina TATU za kutokutrade — hazichanganywi kamwe

Trade isipotokea, sababu ni mojawapo ya tatu, na zina maana tofauti kabisa:

| tokeo | nani anaamua | maana |
|---|---|---|
| `MODEL_NO_TRADE` | model | *"Sioni edge hapa."* |
| `RCE_REJECT` | RCE (§18) | *"Edge inaweza kuwepo, lakini hairuhusiwi kutekelezwa."* |
| `EXECUTION_NO_FILL` | soko (§11.1) | *"Iliruhusiwa, lakini bei ilihama zaidi ya cap."* |

Zote tatu zinaandikwa kwenye ledger moja, zikiwa **zimetenganishwa**. Zikichanganywa
kuwa "hakuna trade", diagnostics inakufa: hutajua kama tatizo ni model isiyoona,
utawala unaobana, au utekelezaji unaoshindwa — na matibabu ya matatu ni tofauti
kabisa.

Uwiano wa tatu hizi ni **kipimo cha afya ya mfumo**, kinachoripotiwa kila run.

---

## 16. Migawanyo ya data

| kipindi | matumizi |
|---|---|
| **2016-01-04 → 2024-03-31** | kugundua · kufundisha · kuthibitisha |
| **2024-04-01 → 2026-04-30** | **HOLDOUT — haijaguswa, inaguswa MARA MOJA** |
| 2026+ | forward / paper validation |

### 16.1 MPAKA MGUMU — mkataba wa kufikia data, si maelezo

```
2016-01-04 ──────────────── 2024-03-31 │ 2024-04-01 ────────── 2026-04
      RESEARCH / CALIBRATION           │        HOLDOUT
                                       ↑
                              HARD ACCESS BOUNDARY
```

**Holdout si labels pekee.** Spread ya 2025, volatility ya 2025, mgawanyo wa 2025 —
vikiingia kwenye calibration inayosaidia kuchagua strategy, **holdout imeshasaidia
uteuzi** hata kama hakuna `future_return` iliyoangaliwa. Tumepata taarifa kuhusu
mazingira yajayo.

Kwa hiyo hii **si kanuni ya nidhamu; ni mkataba wa code.**

**Kila hatua inayosoma data inatangaza dirisha lake:**

```yaml
stage:   cost_calibration
start:   2016-01-04
end:     2024-03-31
purpose: Calibration A (§8.3)
```

**Invariant inayoendeshwa, si kuaminiwa:**

```python
assert stage.end < HOLDOUT_START     # kwa KILA stage isiyo ya holdout
```

**Na muundo wenyewe unafanya uvujaji kuwa mgumu.** Function haipewi data yote:

```python
calibrate_cost(all_ticks)        # HAPANA — inaona kila kitu
calibrate_cost(research_window)  # NDIYO  — haiwezi kuona isiyopewa
```

Kizuizi kikiwa kwenye **saini ya function**, developer wa baadaye hawezi kukiuka
bila kuandika code inayoonekana kuwa ya ajabu. Kizuizi kikiwa kwenye maandishi,
atakisahau.

**Sheria mbili:**

* Sheria ya uteuzi inaandikwa kwenye **faili la ushahidi lenye tarehe** kabla holdout
  haijaguswa. Isiyoandikwa inaweza kubadilishwa baada ya kuona jibu, na hapo holdout
  imepotea bure.
* **Holdout hairudishwi kwenye training baada ya kuona matokeo yake.** Ikirudishwa,
  imeacha kuwa holdout milele.

---

## 17. Timeframes — uamuzi wa PD

Uongozi wa TF, kila moja na kazi **moja**:

| TF | kazi |
|---|---|
| **D1** | macro bias — mwelekeo mkuu |
| **H4** | structural trend — uthibitisho |
| **H2** | filter regime — hali ya soko |
| **H1** | **UAMUZI WA KUINGIA — hapa pekee** |
| **M30** | uboreshaji wa setup |
| **M15** | uthibitisho wa timing **ndani ya** muundo wa H1 |
| **M5** | **RCE pekee** — spread, slippage, microstructure |

**Sheria mbili zinazotokana nayo:**

* **Entry inafungwa H1.** M15 inathibitisha timing ndani ya muundo wa H1; **haihamishi**
  uamuzi kwenda TF ndogo. Strategy inayodai kuingia M15 au M5 inakataliwa na generator.
* **M5 ni ya RCE, si ya models.**

Sababu ya kiuchumi ipo §8: TF ndogo zina ATR ndogo, na gharama thabiti kwa trade
inakuwa sehemu kubwa zaidi yake. Calibration A itathibitisha hilo kwa namba halisi
za injini hii — si kwa kudhaniwa.

---

## 18. RCE

RCE ndiyo **mamlaka pekee** ya gharama, ukubwa wa position, na ruhusa ya kutrade.

* Model **haikadirii** gharama. Inaipokea.
* Model **haiamui** ukubwa wala ruhusa.
* RCE **haiamui** entry wala mwelekeo.

Namba ya gharama inayotumika kwenye lango la §8 na ile inayotumika kwenye sizing ni
**ile ile**. Hakuna kuhesabu mara mbili.

`docs/RISK_COST_ENGINE.md` na `config/risk.yaml` haziko chini ya hati hii na
hazibadilishwi nayo.

### 18.1 Madai dhidi ya RCE yanahakikiwa kwa hesabu, si kwa kukubaliwa

Mapitio ya nje (2026-08-18) yalidai kuwa jedwali la bajeti la RCE linapingana na
formula yake:

> *"base 400, DD 200, penalty 100, today_loss 150 → budget inapaswa kuwa 150,
> lakini jedwali linaonyesha 75."*

**Dai hilo si sahihi, na RCE haikubadilishwa.** Safu ya tatu ya jedwali ina
`current_balance` ya **9,650**, si 9,800 — kwa sababu hasara ya leo ya −$150
**imeshaingia kwenye salio**. Kwa hiyo DD ni 350, si 200, na `penalty = 0.5 × 350 =
175`:

| hali | salio | DD | penalty | budget | risk/trade |
|---|---|---|---|---|---|
| siku ya kwanza | 10,000 | 0 | 0 | 400 | 57.14 |
| baada ya DD −200 | 9,800 | 200 | 100 | 300 | 42.86 |
| leo tayari −150 | **9,650** | **350** | **175** | **75** | 10.71 |
| leo +100 baada ya hapo | 9,750 | 250 | 125 | 175 | 25.00 |

Safu zote nne zinajirudia kwa usahihi kutoka `config/risk.yaml`
(`penalty_factor 0.50`, `win_factor 0.50`, `loss_factor 1.00`, `max_open_trades 7`).
**Formula na mifano vinaendana.**

Kilichoandikwa hapa si utetezi wa RCE bali **kumbukumbu**: dai lililokataliwa
linaandikwa pamoja na hesabu iliyolikataa, ili lisirudi baadaye na kusababisha mtu
"kurekebisha" kitu kisicho na kasoro. Kubadilisha RCE kwa msingi wa mapitio yenye
kosa la kusoma kungeharibu sehemu pekee ya mfumo iliyothibitishwa.

---

## 19. Sheria zisizovunjika

Zifuatazo ni malango, si mapendekezo. Kila moja inaweza kupimwa kwa test.

| # | sheria |
|---|---|
| **R1** | Hakuna data ya baadaye ndani ya row ya nyuma. Ukaguzi kila upakiaji. |
| **R2** | Strategy ni entry **na** exit. Exit haitafutwi baada ya kuona matokeo. |
| **R3** | Candidate yenye `gross < 2 × live_sizing_cost` inakataliwa kabla ya takwimu. |
| **R4** | Kizingiti chochote kinatoka kwenye sakafu iliyopimwa, si kwenye maoni. |
| **R5** | **Generator haifunguki** kabla Calibration A na B (§8.3, §9.2) hazijakamilika na kuhifadhiwa kama ushahidi wenye tarehe. |
| **R6** | `variants_tested` inahesabiwa daima na inaingia kwenye kila ripoti. |
| **R7** | Kila namba muhimu inafikiwa kwa njia mbili; tofauti inachapishwa. |
| **R8** | Uthabiti unapimwa kwa **miezi**, si miaka. |
| **R9** | Holdout inaguswa mara moja, kwa sheria iliyoandikwa kabla, na hairudishwi. |
| **R10** | Output ya model inayolisha model nyingine ni out-of-fold. |
| **R11** | Entry inafungwa **H1**. |
| **R12** | RCE ndiyo mamlaka ya gharama na ukubwa. Haibadilishwi na hati hii. |
| **R13** | Backtest ina matokeo mawili: `FILL` na `NO_FILL`. Signal si trade. |
| **R14** | `MODEL_NO_TRADE`, `RCE_REJECT`, `EXECUTION_NO_FILL` haziunganishwi. |
| **R15** | Sakafu inatoka familia **tatu** za null; inayotumika ni `max`. |
| **R16** | `research_cost` na `live_sizing_cost` ni tofauti, zinatoka chanzo kimoja, na `live ≥ research` daima. |
| **R17** | PRIMARY OUTCOME ni **mbili**; `net_account_return_month` ndiyo yenye mamlaka. |
| **R18** | Kila hatua inatangaza dirisha lake la data; `stage.end < HOLDOUT_START` ni assertion, si nidhamu. |
| **R19** | Utekelezaji una hatua **mbili**: RCE CHECK kisha EXECUTION. `NO_BUDGET` ≠ `NO_FILL`. |
| **R20** | Lango la uchumi linatumia `live_sizing_cost`; `research_cost` ni diagnostic. |
| **R21** | `max_conditions` ni invariant baada ya **kila** mutation, si kizazi cha kwanza. |
| **R22** | Kila variable ya formula ina ufafanuzi wa §21; hakuna prose kwenye hesabu. |
| **R23** | Hakuna amri inayoendesha kimya. Kila hatua inachapisha maendeleo. |

---

## 20. Muundo wa repo

```
src/
├── data/          ubora · normalization · bars · features
├── regimes/       rules · clustering · detector
├── events/        breakout · pullback · momentum · mean_reversion
├── strategies/    DNA · registry · conditions
├── discovery/     generator · rule_search · ml_discovery · evolution
├── backtest/      engine · execution · position · metrics
├── validation/    walk_forward · purged_cv · cpcv · robustness · noise_floor
├── dataset/       labels · builder · sampler
├── models/        lightgbm · xgboost · lstm · ensemble · bandit
└── rce/           HAIGUSWI
```

---

## 21. Kamusi ya vipimo — kila kimoja kinaweza kutekelezwa na code

**Kanuni:** *variable yoyote inayoingia kwenye formula ya deterministic lazima iwe na
ufafanuzi unaoweza kutekelezwa na code bila tafsiri.* Ikibaki kwenye prose,
developer wa baadaye atatengeneza tafsiri yake mwenyewe — na tafsiri mbili tofauti
zote zikiwa "zinatii doctrine" ndiyo mwisho wa doctrine.

Kila kipimo kina sehemu **saba**: `name · inputs · window · formula · range ·
higher_is · daraja`.

---

**`stability`** · RANKING, DIAGNOSTIC

```
inputs    : net_pips_month[t]  kwa miezi yote ya OOS
window    : miezi yote ya OOS ya walk-forward
formula   : clip( 1 − sd(net_pips_month) ÷ |mean(net_pips_month)| , 0, 1 )
range     : [0, 1]
higher_is : better
kumbuka   : mean ikikaribia 0, uwiano unalipuka → clip inarudisha 0.
            Hiyo ni sahihi: strategy isiyo na wastani haina uthabiti.
```

**`complexity`** · RANKING (adhabu)

```
inputs    : entry_conditions, exit_conditions
window    : —
formula   : len(entry_conditions) + len(exit_conditions)
range     : [2, 2 × max_conditions]
higher_is : worse
```

**`overfit_score`** · DIAGNOSTIC

```
inputs    : IS_profit_factor, OOS_profit_factor
window    : IS = walk-forward train · OOS = walk-forward test
formula   : (IS_PF − OOS_PF) ÷ IS_PF
range     : (−∞, 1]
higher_is : worse
mfano     : IS 2.10 / OOS 1.28 → 0.39 (inakubalika)
            IS 4.50 / OOS 0.91 → 0.80 (inakataliwa)
```

**`ATR_percentile_252d`** · FEATURE

```
inputs    : ATR_14[t]
window    : siku 252 za kalenda ya soko zilizopita, zikiishia bar t (imefungwa)
formula   : rank ya ATR_14[t] ndani ya dirisha ÷ ukubwa wa dirisha
range     : [0, 1]
higher_is : neutral
```

**`tick_count_percentile_252d`** · FEATURE — kama ilivyo hapo juu, ingizo
`tick_count[t]`.

**`vol_regime_252d`** · FEATURE

```
inputs    : ATR_percentile_252d[t]
window    : ule ule
formula   : LOW  kwa < 0.33 · MID kwa [0.33, 0.67) · HIGH kwa ≥ 0.67
range     : {LOW, MID, HIGH}
higher_is : neutral
```

**`cost_sensitivity`** · DIAGNOSTIC (§8.4)

```
inputs    : gross_edge, research_cost, live_sizing_cost
formula   : (gross_edge ÷ research_cost) ÷ (gross_edge ÷ live_sizing_cost)
          = live_sizing_cost ÷ research_cost
range     : [1, ∞) kwenye TF ya utekelezaji; chini ya 1 inawezekana kwingine
higher_is : worse    ...juu = strategy inategemea gharama kubaki nzuri
```

**Marekebisho (2026-08-23).** Toleo la kwanza lilidai `[1, ∞)` "kwa sababu
live ≥ research (R16)". Dai hilo halikuwa sahihi baada ya §8.2 kugawanya gharama
kuwa namba **tatu**: R16 inalinganisha `live_check` (slippage mara mbili) na
`research`, wakati `cost_sensitivity` inatumia `live_sizing` (slippage mara moja,
kama RCE inavyohesabu). Kwa hiyo `sens < 1` inawezekana bila R16 kuvunjika —
pengo ni slippage ya kutoka ambayo sizing haihesabu.

Calibration A ya 2026-08-23 inaonyesha mgawanyo huu: kwenye **H1** (TF ya
utekelezaji) `sens` ni 1.09–1.52 kwenye symbols zote 12; kwenye **D1** inashuka
hadi 0.36. Kikomo cha chini kinashikilia pale kinapohitajika, na kinaanguka pale
tu ambapo hatutekelezi.

**`path_dependence`** · PRIMARY (onyo, §1.2)

```
inputs    : net_pips_month, net_account_return_month
formula   : sign(Σ net_pips_month) ≠ sign(Σ net_account_return_month)
range     : {TRUE, FALSE}
higher_is : worse
```

Vipimo hivi ni **mapendekezo ya ufafanuzi**, si vya kutobadilika. Kinachotobadilika
ni kwamba **lazima vifafanuliwe hivi** kabla ya code kuandikwa.

---

## 22. Maamuzi yanayosubiri PD

**U1 — Ukubwa wa utafutaji wa kwanza.** Napendekeza **~1,000**, si 100,000 — si kwa
woga, bali kwa sababu Calibration B lazima ipime sakafu ya mchakato wetu halisi kwanza.
Sakafu ikishajulikana, kupanua ni salama na ni hesabu tu.

**U2 — Model kwa kila pair, au model moja yenye `pair` kama feature?** Napendekeza
**moja yenye `pair` kama feature.** Model ya kila pair inajifunza kutoka kwenye sehemu
ndogo ya data; iliyounganishwa inajifunza kutoka pairs zote na bado inaweza kutofautisha.

**U3 — Mpangilio wa kujenga.** Napendekeza:

```
1. data/        ukaguzi wa §4 — kila kitu kinapimwa upya
2. backtest/    engine yenye rekodi kamili ya §11
3. validation/noise_floor.py    ← KABLA ya generator
4. discovery/   generator + rule search
5. models/
```

Nambari 3 kabla ya 4 ni ya makusudi, kwa sababu ya §2.
