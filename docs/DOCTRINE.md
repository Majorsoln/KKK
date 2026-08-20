# ELITEFX — DOCTRINE
## Injini ya Kugundua Strategy Kiotomatiki

**Tarehe:** 2026-08-18 · **Hadhi:** rasimu ya kujadiliwa, kabla ya utekelezaji
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

**Kipimo cha mwisho ni kimoja:** *pips net kwa mwezi, na sehemu ya miezi yenye faida.*
Kila kipimo kingine ni cha ndani.

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
                    pairs · 2016–2024
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

Chanzo: ticks za bid/ask, si bars zilizotengenezwa na mtu mwingine.

Kila pair, kila mwaka, inapita ukaguzi ufuatao **kila inapopakiwa**, si mara moja:

| ukaguzi | kigezo |
|---|---|
| mpangilio | timestamps zinapanda, hakuna kurudi nyuma |
| duplicates | hakuna tick mbili zenye muda na bei ile ile |
| mapengo | kila pengo linaelezwa na kalenda ya soko, si kudhaniwa |
| timezone | UTC pekee, kila mahali |
| wikendi | kanuni moja, iliyoandikwa, inayotumika kwa pairs zote |
| OHLC | `low ≤ open, close ≤ high` kwa kila bar |
| **ya baadaye** | **hakuna thamani ya bar `t+k` inayoonekana kwenye row ya `t`** |

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
| volatility | `ATR_14`, `ATR_20`, `std_20`, `std_50`, `ATR_percentile`, `vol_regime` |
| trend | `EMA_{20,50,100,200}`, tofauti zao, `slope_EMA_{20,50,200}` |
| momentum | `RSI`, `ROC`, `MACD`, `ADX` |
| muundo wa candle | `body`, `upper_wick`, `lower_wick`, `range`, `body/range`, `close_pos_in_range` |
| nafasi sokoni | `dist_from_high_{20,50}`, `dist_from_low_{20,50}`, `dist_from_EMA200` |
| muda | `hour`, `day_of_week`, `session`, `minutes_from_session_open` |

**Sheria mbili zisizovunjika:**

* Feature ya bar `t` inatumia **hadi bar `t` ikiwa imefungwa**. Rolling extremes
  zinatumia `[t−1]`, si `[t]`.
* Feature yoyote inayotokana na model iliyofit inafundishwa **expanding au per-fold**,
  kamwe si juu ya sample nzima.

---

## 6. Regimes

Soko haliko katika hali moja. Regime inaelezwa kwanza kwa sheria (ADX, EMA, ATR
percentile), na baadaye kwa clustering (KMeans · GMM · HMM) ikiwa clustering itashinda
sheria kwenye §12.

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

## 8. LANGO LA UCHUMI — linapimwa, halidhaniwi

### 8.1 Kanuni

Gharama ya kuingia na kutoka ni **thabiti kwa kila trade** — spread ya round-trip
pamoja na commission. Haibadiliki trade ikiwa kubwa au ndogo.

Kwa hiyo:

> **Tatizo kamwe si trades za bei ghali. Ni trades ndogo mno.**

Strategy inayoshinda kidogo kuliko gharama inapoteza haijalishi ina trades ngapi, na
haijalishi asilimia yake ya kushinda ni kubwa kiasi gani.

### 8.2 Calibration A — injini inapima gharama yake yenyewe

Kabla ya strategy yoyote:

```
kwa kila pair, kwa kila TF:
    cost_ATR = (spread_ya_round_trip + commission) ÷ ATR
```

Spread inatoka kwenye **ticks halisi wakati wa kuingia**, si kwa wastani wa broker.
Commission inatoka **RCE** (§18), si kwa kudhania.

Tokeo ni jedwali la gharama kwa kila `(pair, TF)`. Ndilo linalofungua au kufunga
mlango, na linahifadhiwa kama ushahidi wenye tarehe.

### 8.3 Lango

> **Candidate yoyote yenye `gross edge kwa trade < 2 × gharama kwa trade` inakataliwa
> kabla ya takwimu yoyote kuhesabiwa.**

`2×` na si `1×` kwa sababu `1×` inadai makadirio ya gharama yawe sahihi kabisa.
`2×` inaacha nafasi ya slippage, kuzorota kwa spread, na makosa ya utekelezaji.

Lango hili linaendeshwa kwanza kwa sababu ni **la bei nafuu**: linakata sehemu kubwa
ya wagombea kwa hesabu ya mstari mmoja, kabla ya backtest yoyote. Hilo linapunguza
idadi ya majaribio — ambayo ndiyo inayotawala §9.

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

Kile ambacho injini "inagundua" pale ndiyo **sakafu**. Kizingiti cha strategy halisi ni
p95 ya sakafu ile — si 50%, si 85%, si namba yoyote iliyochaguliwa na binadamu.

### 9.3 Sheria tatu

**S1** — `variants_tested` inahesabiwa daima, ikiwemo waliokufa mapema, na inaingia
kwenye kila ripoti.

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

---

## 11. Backtest Engine

Kwa kila trade, rekodi hii kamili — si muhtasari:

```
entry_time · entry_price · direction · SL · TP
exit_time · exit_price · exit_reason
gross_return · spread · slippage · net_return
MFE · MAE · holding_time
```

`MFE` (Maximum Favorable Excursion) na `MAE` (Maximum Adverse Excursion) ni za lazima:
ndizo pekee zinazoweza kujibu maswali ya kutoka baadaye, na haziwezi kurudishwa
baada ya backtest kuisha.

**Uhakiki uliojengwa ndani:** kila namba muhimu inayotoka kwenye engine lazima ifikiwe
kwa **njia mbili zinazojitegemea**, na tofauti yake ichapishwe. Mfano: return ya bar
`t+24` inayohesabiwa kutoka bars lazima ilingane na ile inayohesabiwa kutoka ticks.
Zisipolingana, moja ina kasoro — na tofauti yenyewe inaeleza ipi.

---

## 12. Validation

**Hatua za bei nafuu kwanza.** Usiendeshe backtest ya miaka 9 kwa kila candidate:

| hatua | kipindi | kazi |
|---|---|---|
| A | 2016–2020 | screening ya bei nafuu — kata wengi |
| B | 2016–2021 | |
| C | 2016–2022 | |
| D | 2016–2023 | walionusurika pekee |

**Walk-forward** juu ya walionusurika:

```
2016–2019 → 2020        2016–2021 → 2022
2016–2020 → 2021        2016–2022 → 2023
```

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
unaojifunzwa, si sheria iliyoongezwa juu ya model. Ndiyo namna sahihi ya kutekeleza
veto.

---

## 16. Migawanyo ya data

| kipindi | matumizi |
|---|---|
| 2016 – 2023 | kugundua · kufundisha · kuthibitisha |
| **2024-04 → 2026-04** | **HOLDOUT — haijaguswa, inaguswa MARA MOJA** |
| 2026+ | forward / paper validation |

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

---

## 19. Sheria zisizovunjika

Zifuatazo ni malango, si mapendekezo. Kila moja inaweza kupimwa kwa test.

| # | sheria |
|---|---|
| **R1** | Hakuna data ya baadaye ndani ya row ya nyuma. Ukaguzi kila upakiaji. |
| **R2** | Strategy ni entry **na** exit. Exit haitafutwi baada ya kuona matokeo. |
| **R3** | Candidate yenye `gross < 2 × gharama` inakataliwa kabla ya takwimu. |
| **R4** | Kizingiti chochote kinatoka kwenye sakafu iliyopimwa, si kwenye maoni. |
| **R5** | `variants_tested` inahesabiwa daima na inaingia kwenye kila ripoti. |
| **R6** | Kila namba muhimu inafikiwa kwa njia mbili; tofauti inachapishwa. |
| **R7** | Uthabiti unapimwa kwa **miezi**, si miaka. |
| **R8** | Holdout inaguswa mara moja, kwa sheria iliyoandikwa kabla, na hairudishwi. |
| **R9** | Output ya model inayolisha model nyingine ni out-of-fold. |
| **R10** | Entry inafungwa **H1**. |
| **R11** | RCE ndiyo mamlaka ya gharama na ukubwa. Haibadilishwi na hati hii. |
| **R12** | Hakuna amri inayoendesha kimya. Kila hatua inachapisha maendeleo. |

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

## 21. Maamuzi yanayosubiri PD

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
