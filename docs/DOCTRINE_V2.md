# ELITEFX — DOCTRINE v2
## Injini ya Kugundua Strategy Kiotomatiki

**Tarehe:** 2026-08-18 · **Hadhi:** rasimu ya majadiliano, **kabla ya utekelezaji**
**Chanzo:** muundo wa PD (nukta 28), pamoja na vikwazo vilivyopimwa v1
**Inabadilisha:** doctrine yote ya v1 (`docs/archive/v1/`)
**HAIGUSI:** `docs/RISK_COST_ENGINE.md` na `config/risk.yaml` — RCE inabaki **kama ilivyo**

---

## 0. Hadhi ya hati hii

Hii ni **rasimu ya kujadiliwa**, si kibali cha kuanza kujenga. Hakuna mstari wa code
utakaoandikwa kwa msingi wake kabla PD hajaipitisha.

Kilichowekwa `docs/archive/v1/`:

| hati | ilikuwa inafanya nini | kwa nini imehifadhiwa |
|---|---|---|
| `KAIROS_1_STANDARD.md` | tabaka tatu, models 10 | muundo ni sahihi; **hatujawahi kujenga tabaka la DECISION** |
| `DATA_FEATURE_STANDARD.md` | sheria 8+ za features | sheria za uvujaji zinahamia v2 zikiwa **hai** |
| `DATA_SPLIT_PLAN.md` | train/val/holdout | inabadilishwa na §7 |
| `IMPLEMENTATION_PLAN.md` | mpango wa awamu | umepitwa na matukio |
| `RESEARCH_PLAN_R0.md` | mpango wa R0–R4 | R0–R2 zimekamilika; R3+ zinabadilishwa |
| `T3_PLAN.md` | pre-registration ya meta-labelling | jaribio limekwisha, tokeo hasi |

Zilizobaki `docs/` ni **ushahidi**, si doctrine: T0, T4, T5, T6, mapitio ya wataalamu,
`SIGNATURES.md`, `TRIAL_BUDGET.md`, `RIPOTI_MAENDELEO.md`. **Hazitupwi.** Ndizo
zinazothibitisha kwa nini v2 inaonekana hivi.

---

## 1. Kwa nini v1 imeachwa — sababu nne zilizopimwa, si maoni

1. **Tulijenga tabaka moja kati ya matatu.** Awamu nne zimeenda kwenye kanuni **moja**
   ya kuingia (SETUP-v1) pamoja na grid ya exits. Kwa lugha ya KAIROS-1, hiyo ni
   **input** ya tabaka la DECISION. Tabaka lenyewe — *"strategy ipi inafaa?"* —
   halikujengwa hata kidogo.

2. **Kutafuta exit kando na entry ndiko kulikotuua.** Cells 49 zilitafutwa baada ya
   kuona matokeo; **0 kati ya 49** zilibaki chanya kwenye pool tusiyoichagua.

3. **Kila kasoro na kila uteuzi ulikuwa mkubwa kuliko athari yenyewe.**

   | | thamani |
   |---|---|
   | kasoro ya labelling | 0.0124 R |
   | uteuzi wa symbols (EURCHF/EURGBP) | 0.0190 R |
   | athari ya SETUP-v1 dhidi ya control | 0.0560 R |
   | EV net iliyowahi kufikiwa (ikiwa imependelewa zaidi) | 0.0205 R |

4. **Edge ipo, lakini ni ndogo kuliko gharama.** Drift halisi ya bars 24:
   **+0.0593 ATR** (`t` 1.84). Gharama ya round-trip: **0.1094 ATR**. Uwiano **1.84×**.

**Hitimisho linalobeba v2:** hypothesis moja iliyopimwa kwa ukali haitoshi. Tunahitaji
**wagombea wengi**, wanaopimwa kwa **rekodi**, wakilindwa dhidi ya **bahati**.

---

## 2. Vikwazo saba vinavyovuka kutoka v1 vikiwa HAI

Hivi si mapendekezo. Ni vitu vilivyogharimu awamu nne kuvijua.

**K1 — RCE ndiyo mamlaka ya gharama.** Model haikadirii gharama. Haiguswi.

**K2 — Strategy ni kitu KIMOJA: uchambuzi kamili hadi entry NA exit.** Exit
inatangazwa **ndani ya** strategy, si kutafutwa baadaye. Ndiyo sababu ya kifo cha T5.

**K3 — Kila namba muhimu lazima ifikiwe kwa njia MBILI zinazojitegemea.**
Kasoro zote mbili tulizozipata zilipatikana hivi: `σ_R` iliyojengwa upya, kisha
utambulisho wa optional stopping. `drift-curve` ina uhakiki wa bar-dhidi-ya-tick
uliojengwa ndani na ulishalipa gharama yake.

**K4 — Kizingiti chochote kinapimwa kwa NULL, hakidhaniwi.** Kizingiti chetu cha 0.7
kilikaa kwenye asilimia 25 ya null yake yenyewe — hakikuwa lango kamwe.

**K5 — Uteuzi wowote unatozwa.** Kuchagua symbols, cells, saa, au strategies baada ya
kuona matokeo lazima kuhesabiwe.

**K6 — Holdout inaguswa MARA MOJA.** 2024-04-01 → 2026-04-30 haijaguswa. Sheria
inaandikwa kwenye ushahidi **kabla**, kwa hiyo haiwezi kubadilishwa baada ya kuona jibu.

**K7 — Hakuna amri inayoendeshwa kimya.** Kila hatua inachapisha maendeleo.

---

## 3. Injini — mtiririko

```
                    pairs 2016–2024
                           │
                  ┌────────▼────────┐
                  │ Data Quality &  │   L0–L1 (zimekamilika, R0–R2)
                  │ Normalization   │
                  └────────┬────────┘
                  ┌────────▼────────┐
                  │  Feature Engine │   L3
                  └────────┬────────┘
              ┌────────────┴────────────┐
              ▼                         ▼
       Market Regimes              Event Engine
              └────────────┬────────────┘
                           ▼
                  Strategy Generator
              ┌────────────┴────────────┐
              ▼                         ▼
       Rule-based Search          ML Discovery
              └────────────┬────────────┘
                           ▼
                ╔══════════════════════╗
                ║  LANGO LA UCHUMI     ║   ← §5, JIPYA
                ║  gross ≥ 2 × gharama ║      kabla ya takwimu YOYOTE
                ╚══════════┬═══════════╝
                           ▼
                    Backtest Engine
                           ▼
                  Robustness Filters
                           ▼
                Purged Walk-Forward / CPCV
                           ▼
                ╔══════════════════════╗
                ║  SAKAFU YA KELELE    ║   ← §6, JIPYA
                ║  pipeline nzima juu  ║      idadi ya majaribio
                ║  ya data bandia      ║      inarekodiwa daima
                ╚══════════┬═══════════╝
                           ▼
                  Strategy Database
                           ▼
                  Training Dataset
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          LightGBM     XGBoost        LSTM
              └────────────┼────────────┘
                           ▼
                      Meta Model
                           ▼
              BUY · SELL · **NO TRADE**
                           ▼
                   Final OOS (mara moja)
```

Sanduku mbili zenye mistari miwili ndizo nyongeza zangu pekee kwenye mchoro wako.
Zote zinatokana na kitu kilichotuumiza.

---

## 4. Tabaka moja moja

### 4.1 Data (L0–L2) — **imekamilika**

Ticks za Dukascopy 2016-04 → 2026-04, pairs 12, zimehakikiwa (R0–R2): timestamps
zimepangwa, hakuna duplicates, timezone moja (UTC), OHLC ni sahihi, weekend
inashughulikiwa kwa kalenda, **hakuna data ya baadaye ndani ya row ya nyuma**. Bars
zimejengwa kwa TF 7. Hii ni hatua yako ya 1 na tayari tunayo.

### 4.2 Feature Engine (L3)

Orodha yako inakubaliwa kama ilivyo: price returns, volatility, trend, momentum,
candle structure, market position, time. **Sheria ya uvujaji inavuka ikiwa hai:**
kila feature kwa bar `t` inatumia **hadi bar `t` ikiwa imefungwa**. Rolling extremes
zinatumia `[t−1]`, kama ulivyoandika kwenye nukta 4.

### 4.3 Regimes

Sheria kwanza (ADX, EMA, ATR percentile), clustering baadaye (KMeans / GMM / HMM).
**Onyo lililopimwa:** `N_eff` ya hypothesis ya regime **si** idadi ya trades — ni
idadi ya **matukio huru ya regime**. Kwa miaka 8 na pairs 12 zinazohusiana, pengine
mia chache. Regime yoyote inayodai kufanya kazi lazima ipimwe kwa kipimo hicho.

### 4.4 Event Engine

Breakout · Pullback · Trend continuation · Mean reversion · Volatility expansion /
contraction · Momentum shift. Kama ulivyoandika.

**Nyongeza kutoka kwenye vipimo vyetu:** ongeza **`POST_STOP_CONTINUATION`**. Ni
tokeo pekee jipya la mradi: bei ikishaenda 3 ATR dhidi ya nafasi, mwendo unaobaki ni
**−0.052 ATR**, si +0.059. Mzunguko wa **0.111 ATR** — mkubwa kuliko drift yenyewe.

### 4.5 Strategy Generator

Condition library + operators (AND/OR/NOT), `max_conditions` 3–5. Kama ulivyoandika.
Njia mbili: Rule Discovery na ML Discovery (feature interactions → rules).

### 4.6 Kila strategy ina umbo LILE LILE (K2)

```
STRATEGY
  entry_conditions      exit_conditions
  sl_type + parameter   tp_type + parameter
  time_stop             position rule
  regime                features_used
```

Vinginevyo hazilinganishwi, na exit inakuwa parameter ya siri inayotafutwa baadaye.

---

## 5. LANGO LA UCHUMI — kabla ya takwimu yoyote

**Hii ndiyo nyongeza yangu ya kwanza, na ndiyo muhimu zaidi.**

Gharama ni **thabiti kwa kila trade** — takriban **pips 1.3** round-trip, haijalishi
trade ni kubwa au ndogo. Kwa hiyo:

> **Tatizo si trades za bei ghali. Ni trades ndogo.**

Tulishinda pips 1.0 kwa trade na kulipa pips 1.3. Suluhisho si kupunguza 1.3 — ni
kutafuta strategy zenye **edge kubwa kwa kila trade**.

**Sheria:** candidate yoyote yenye `gross edge kwa trade < 2 × gharama kwa trade`
**inakataliwa kabla ya kuhesabiwa takwimu yoyote.**

Kwa nini `2×` na si `1×`: kwa `1×` unahitaji makadirio kuwa sahihi kabisa. Kwa `2×`
una nafasi ya makosa ya gharama, slippage, na kuzorota kwa spread.

### 5.1 Matokeo ya sheria hii kwenye timeframe

Hii ndiyo sababu ya kiuchumi ya kuchagua TF, si ladha:

| TF | ATR (pips) | gharama/ATR | mara ya H1 |
|---|---|---|---|
| M5 | 4.6 | **0.2815** | **3.46×** |
| M15 | 8.0 | 0.1625 | 2.00× |
| **H1** | 16.0 | **0.0812** | 1.00× |
| H4 | 32.0 | 0.0406 | 0.50× |
| D1 | 78.4 | **0.0166** | 0.20× |

Ulitaja M5 kama mfano wa dataset. **Nakushauri kwa nguvu tusiweke maamuzi hapo.**
Kwa M5 gharama ingekuwa **0.2815 ATR**, na edge ingehitaji kuwa **mara 4.7** ya
tuliyonayo. Data ni kubwa zaidi, lakini kila trade inakuwa ndogo mno kuvuka gharama.

Hoja yako mwenyewe — "trades kubwa" — inaelekeza **juu**, si chini. **H1 na H4 ndipo
penye nafasi; D1 ina gharama ndogo kuliko zote lakini trades chache.**

M5 inabaki kwa **RCE** (spread, slippage, microstructure) — kama RCE §0 inavyosema
tayari. Haibadiliki.

---

## 6. SAKAFU YA KELELE — idadi ya majaribio ni sehemu ya jibu

**Nyongeza yangu ya pili.**

Ulilitaja mwenyewe (nukta 23: *record `number_of_variants_tested`*). Hapa
linakuwa **la lazima na la kiotomatiki**, kwa sababu namba zake ni kubwa kuliko
zinavyoonekana:

Kwa strategies **zisizo na edge kabisa**, miezi 96 (2016–2023), miaka 8:

| strategies zilizojaribiwa | miezi yenye faida ya **bora** | Sharpe ya **bora** |
|---|---|---|
| 100 | 63% | 1.07 |
| 1,000 | 66% | 1.31 |
| 10,000 | 69% | 1.52 |
| **100,000** | **74%** | **1.70** |

Soma safu ya mwisho. Ukijaribu strategies 100,000 zisizo na edge yoyote, bora zaidi
itaonyesha **74% ya miezi yenye faida na Sharpe 1.70.** Ingeonekana kama mfumo wa
dhahabu. Ni kelele safi.

Na kwa miaka: cells 96 tu zisizo na edge zinatoa cell bora yenye **miaka 7 kati ya 8**
yenye faida. **Ndiyo maana uthabiti unapimwa kwa MIEZI, si kwa miaka** — miaka 8 ni
pointi chache mno kutofautisha chochote.

### Sheria tatu

**S1 — Hesabu inaendeshwa daima.** Kila candidate iliyozalishwa inahesabiwa, hata
zilizokufa mapema. `variants_tested` ni sehemu ya kila ripoti.

**S2 — Kizingiti kinatoka kwenye null, si kwenye maoni.** Endesha **pipeline NZIMA**
— generator, backtest, filters, validation — juu ya **data bandia isiyo na edge**.
Kile ambacho mashine "inagundua" pale ndiyo sakafu. Strategy halisi lazima ivuke
sakafu ile, si 50% wala 85%.

**S3 — Deflated Sharpe.** Ripoti Sharpe iliyorekebishwa kwa `variants_tested`, si
ghafi.

Hii **si** kuzuia utafutaji mkubwa. **Ndiyo inayoufanya utafutaji mkubwa uwe na
maana** — bila sakafu, kadri unavyotafuta zaidi ndivyo unavyodanganyika zaidi.

---

## 7. Migawanyo ya data

Yako (nukta 9, 10, 25) inakubaliwa, ikiwa imeimarishwa kidogo:

| kipindi | matumizi |
|---|---|
| 2016–2020 | Stage A — screening ya bei nafuu |
| 2016–2022 | discovery + rule search |
| 2022-04 → 2024-03 | **validate** — hapa ndipo uteuzi unapothibitishwa |
| **2024-04 → 2026-04** | **HOLDOUT — haijaguswa, inaguswa MARA MOJA** |

Tofauti moja na mpango wako: ulipendekeza 2024 pekee kama final test. **Tunayo miaka
MIWILI** ambayo haijaguswa kabisa, si mmoja. Ni bora zaidi, na tayari imetangazwa
(K6).

Purged walk-forward na embargo zinabaki kama ulivyoandika. CPCV inaongezwa baada ya
walk-forward.

**Kizuizi cha unyofu:** holdout ya miaka 2 ina `SE ≈ 0.025` kwa EV. Haiwezi
kuthibitisha athari ndogo. Inaweza kuthibitisha **uthabiti wa uteuzi** — je sheria
iliyochagua strategies ilifanya kazi? Hilo ndilo swali sahihi kwake.

---

## 8. Backtest Engine na Strategy DNA

Rekodi kwa kila trade (nukta 8) zinakubaliwa zote: `entry_time, entry_price,
direction, SL, TP, exit_time, exit_price, exit_reason, gross_return, spread,
slippage, net_return, MFE, MAE, holding_time`.

**MFE/MAE ni muhimu zaidi kuliko unavyodhani** — ndizo zinazoweza kupima
`POST_STOP_CONTINUATION` moja kwa moja.

Strategy DNA (nukta 12) inakubaliwa kama ilivyo, pamoja na nyongeza tatu:
`variants_tested_when_found`, `noise_floor_at_discovery`, `cost_to_edge_ratio`.

---

## 9. Fitness na Final Score

Fitness yako yenye uzito (nukta 7) **inakubaliwa kwa KUPANGA**, si kwa **LANGO**.

Sababu: uzito (0.30, 0.20, 0.15…) ni chaguo la kibinadamu, na kila chaguo ni digrii
ya uhuru inayoweza kuchezewa. Kwa hiyo:

* **Kupanga (ranking):** fitness yako — inasaidia kuona wagombea bora kwanza
* **Lango (gate):** sakafu ya kelele ya §6 pekee — hakuna kingine kinachopitisha

Na kipimo cha mwisho cha kuripoti kinabaki **chako**: **pips net kwa mwezi, na
sehemu ya miezi yenye faida.** Ni kipimo bora kuliko changu cha EV-kwa-ATR, kwa
sababu kinapendelea kiotomatiki strategy zenye edge kubwa kwa trade — ambazo ndizo
pekee zinazoweza kuvuka gharama thabiti ya pips 1.3.

---

## 10. Models na mpangilio wa kuingia

Orodha inabaki (KAIROS-1). **Mpangilio unabadilika**, kwa sababu data ndiyo inayoamua:

| model | kazi | inahitaji | sasa? |
|---|---|---|---|
| **LightGBM** | `P(TP kabla ya SL)` kwa (market state + strategy_id) | maelfu ya trades | **ndiyo** |
| **XGBoost** | model huru ya pili; angalia **uhusiano wa makosa**, si "ensemble ni nzuri" | ile ile | **ndiyo** |
| **HMM / GMM** | regime | mamia ya matukio ya regime | **ndiyo** |
| **Bandit** | strategy ipi kwa pair ipi — **kipaumbele au VETO** | mamia kwa mchanganyiko | **ndiyo** |
| **LSTM** | sequence | mamilioni | baadaye |
| **PPO** | strategy selection | zaidi ya bandit | **lazima ishinde bandit kwanza** |
| Transformer / CNN | patterns | mamilioni | baadaye, kwa pretraining |

**Sheria ya kuingia (kutoka KAIROS-1 §6, inabaki hai):** hakuna model inayoingia kwa
nafasi yake. Inaingia kwa **kushinda baseline**. LSTM isiyoongeza OOS performance
haitumiki — kama ulivyoandika mwenyewe kwenye nukta 17.

**Cross-fitting inabaki:** output ya model inayolisha model nyingine ni **out-of-fold,
daima**. Hii ni sheria ya v1 iliyonusurika ukaguzi wote.

### 10.1 NO TRADE ni darasa, si kizingiti

Nukta 19 yako. Model inatoa `P(BUY)`, `P(SELL)`, `P(NO TRADE)`. Hii ndiyo namna
sahihi ya kutekeleza **"kuzuia"** ulilolitaja — veto ni tokeo la model, si kanuni
iliyoongezwa juu yake.

---

## 11. Muundo wa repo

Wako (nukta 26) unakubaliwa karibu kama ulivyo, ukiwa umeunganishwa na uliopo:

```
src/
├── data/          ← ipo (L0–L3, RCE bridge)
├── strategies/    ← MPYA: registry, DNA, conditions, generator
├── discovery/     ← MPYA: rule search, ML discovery, evolution
├── backtest/      ← MPYA: engine, execution, metrics
├── validation/    ← MPYA: walk_forward, cpcv, robustness, noise_floor
├── models/        ← MPYA: lightgbm, xgboost, lstm, ensemble, bandit
└── governance/    ← ipo (budget, signatures)
```

---

## 12. Maamuzi manne yanayohitaji uamuzi wako

Sitajenga chochote kabla ya haya.

**U1 — Timeframe ya maamuzi.** Napendekeza **H1 na H4**, si M5, kwa sababu za §5.1
(M5 ina gharama mara 3.46). Unakubali?

**U2 — Ukubwa wa utafutaji wa kwanza.** Napendekeza **tuanze na strategies ~1,000**,
si 100,000 — si kwa woga bali kwa sababu tunahitaji **kupima sakafu ya kelele
kwanza** kwa mchakato wetu halisi. Sakafu ikishajulikana, kupanua ni salama.

**U3 — Model kwa kila pair, au model moja yenye pair kama feature?** Napendekeza
**moja yenye pair kama feature**. Trades ~25,000 kwa pair-strategy ni chache kwa
model ya kila pair, na model iliyounganishwa inajifunza kutoka pairs zote.

**U4 — Nianze na hatua ipi?** Napendekeza mpangilio huu, kila moja ikiwa na tokeo
linaloonekana:

1. `src/strategies/` — umbo la Strategy DNA + registry (SETUP-v1 inakuwa ya kwanza)
2. `src/backtest/` — engine inayotoa rekodi zote za nukta 8
3. **`src/validation/noise_floor.py` — sakafu ya kelele, KABLA ya generator**
4. `src/discovery/` — generator + rule search
5. models

**Nambari 3 kabla ya 4 ni ya makusudi.** Tukijenga generator kwanza, tutaona
strategies nzuri kabla ya kujua nzuri ni nini — na hatutaweza kusahau tulichokiona.

---

*Nimeandika hii kwa muundo wako, si kwa wangu. Nyongeza mbili pekee (§5 na §6)
zinatoka mahali pale pale: kila kitu ambacho mradi huu umekigundua kilikuwa kikubwa
kuliko kile kilichokuwa kikitafutwa. Injini ya kugundua kiotomatiki inakuza tatizo
hilo kwa idadi ya strategies inazozalisha — kwa hiyo lango la gharama na sakafu ya
kelele si urasimu. Ndiyo vinavyofanya injini iwe na thamani badala ya kuwa mashine
ya kuzalisha matumaini.*
