# KAIROS-1 — ADAPTIVE ENTRY INTELLIGENCE ENGINE — STANDARD RASMI

> **Hadhi:** standard ya uzalishaji. Idara ya **models** — inayotoa mapendekezo ya entry kwa
> **RISK & COST ENGINE** (`engine/docs/RISK_COST_ENGINE.md`). Design: PD 2026-08-02. Marekebisho
> matano (§3) yamekubaliwa na PD baada ya mjadala. Hati hii ni **spec**, si utekelezaji.

---

## 1. KAIROS-1 NI NINI

Si signal-generator. Ni **injini ya akili ya kuingia** yenye tabaka **tatu**, inayojibu maswali
matatu kwa mfuatano:

| Tabaka | Swali | Models |
|---|---|---|
| **UNDERSTANDING** | Soko liko katika hali gani, na linaelekea wapi? | HMM · Transformer · LSTM · CNN |
| **DECISION** | Setup hii ina ubora gani, na strategy ipi inafaa? | XGBoost · PPO |
| **VALIDATION** | Je trade hii ina thamani chanya — na inaweza kutekelezeka? | Quantile NN · Barrier · EV · Fill |

**Kanuni ya msingi:** *trade haihukumiwi kwa kuonekana nzuri, bali kwa kuwa na edge halisi,
inayotekelezeka, inayolipa baada ya gharama.*

### 1.1 Models na kazi zao
| Model | Kazi | Tokeo |
|---|---|---|
| **HMM** | market regime (D1→H1) | `{regime, direction, volatility, confidence}` |
| **Transformer** | price sequence → mwelekeo + probability | `P(up/down/neutral)` |
| **LSTM** | kumbukumbu: "tumewahi kuona hali hii?" | historical similarity + matokeo yake |
| **CNN** | patterns: sweep, break-retest, order block, MSS | pattern + confidence |
| **XGBoost** | ubora wa setup | `A+/A/B/reject` + score |
| **PPO** | strategy selection (trend/breakout/reversal/MR) | strategy iliyochaguliwa |
| **Quantile NN** | distribution ya move → SL/TP | `Q10, Q50, Q90` |
| **Barrier** | P(TP/SL/timeout) — madarasa MATATU | `p_tp · p_sl · p_timeout` |
| **EV** | thamani inayotarajiwa (madarasa matatu, §2.1) | `EV_signal` |
| **Fill** | uwezekano wa kujaza ndani ya cap | `P(fill)` |

**Lango la kuingia kwa kila model (halali kwa ZOTE):** hakuna model inayoingia kwa nafasi yake
kwenye mchoro — inaingia kwa kushinda §6 dhidi ya baseline ya R4. Kwa deep models (Transformer,
LSTM, CNN) njia halali ya kufikia uwezo huo kwa bajeti ya trade-labels iliyopo ni **pretraining
(§5A)**. Kwa **PPO**: baseline yake ya lazima ni **contextual bandit / quality-per-strategy
classifier** — PPO isiyoshinda bandit rahisi kwenye purged CV haiingii (offline RL kwa maelfu ya
trades ni hatari kubwa ya kukariri kelele; hii ni R4-logic ile ile ngazi ya juu).

### 1.2 Timeframe hierarchy — kila TF ina KAZI moja (PD 2026-08-02)
| TF | Kazi | Inalisha |
|---|---|---|
| **D1** | Macro Bias — mwelekeo mkuu | HMM · Transformer |
| **H4** | Structural Trend — uthibitisho wa trend | HMM · CNN · Transformer |
| **H2** | Filter Regime — hali ya soko | HMM |
| **H1** | **Decision + Execution — injini kuu** | models ZOTE (uamuzi unafanyika hapa) |
| **M30** | Setup refinement — ubora wa ndani | XGBoost · CNN |
| **M15** | Trigger confirmation — timing | CNN · XGBoost |
| **M5** | Intrabar analytics — spread, slippage, volatility | **RCE** (si KAIROS-1) |

**Muhimu:** **M5 ni ya RCE**, si ya KAIROS-1. KAIROS-1 haitumii M5 kwa uamuzi wa entry — inaitumia
RCE kwa gharama/cap pekee (§0 ya `RISK_COST_ENGINE.md`). Uamuzi wa entry unafungwa kwenye **H1**;
M15 inathibitisha timing ndani ya muundo wa H1, **haihamishi** uamuzi kwenda TF ndogo.

---

## 2. PIPELINE YA UAMUZI (mfuatano rasmi)

```
[Feature Engine — multi-TF]
        ↓
[Quantile NN]        →  Q10 / Q50 / Q90  (SL/TP candidates)
        ↓
[SL FLOOR RULE]      →  SL_final                        ← STANDARD S2
        ↓
[Barrier Model]      →  p_tp_first                      ← STANDARD S1 (head TOFAUTI)
        ↓
[EV Model]           →  EV_signal
        ↓
[Fill Model]         →  P(fill)                          ← STANDARD S4
        ↓
EV_final = P(fill) × EV_signal                           ← STANDARD S5
        ↓
FILTERS:  EV_R ≥ threshold   ·   RR ≥ min   ·   quality ≥ min      ← STANDARD S3
        ↓
→ pendekezo linakwenda RCE (sizing + gate)
```

**SL/TP kutoka quantiles:**
```
BUY :  SL = Q10   ·  TP = Q90
SELL:  SL = Q90   ·  TP = Q10
```
Mafunzo: **pinball (quantile) loss** — `L = max(q·(y−ŷ), (q−1)·(y−ŷ))` — inajifunza hatari
isiyo-linganifu (under- vs over-estimation si sawa kwenye trading).

### 2.1 EV YA MADARASA MATATU (PD 2026-08-04 — inachukua nafasi ya EV ya binary)
Barrier ina madarasa matatu (TP kwanza / SL kwanza / timeout, hadi 35% ya labels). EV ya binary
`p×TP − (1−p)×SL` inadhania timeout haipo — inapotosha hadi theluthi ya matokeo. Fomula rasmi:
```
EV_signal = p_tp × TP  −  p_sl × SL  +  p_timeout × E[R | timeout]
```
- `p_tp, p_sl, p_timeout` — Barrier head (3-class, calibrated §5.3).
- `E[R|timeout]` — kutoka **terminal returns za timeout labels zenyewe** (§5.2 ya standard ya
  data): wastani kwa kila kisanduku cha grid, au regressor ndogo maalum. **SI** kutoka Quantile
  head — hiyo ingerudisha mduara ambao S1 imeukata.

---

## 3. STANDARDS SITA (S1–S5 PD 2026-08-02 · S6 PD 2026-08-04)

### S1 — MIPAKA na HUKUMU zitenganishwe (anti-circularity)
Distribution inayoweka barriers **HAIRUHUSIWI** kuzihukumu. Ni **heads mbili tofauti**:
```
Head 1 (Quantile NN)  →  Q10/Q50/Q90     = MIPAKA
Head 2 (Barrier)      →  p_tp_first      = HUKUMU
```
**Label ya Barrier Model:** `1 = TP iligusa kwanza · 0 = SL iligusa kwanza` — ni **path-dependent
touch**, si terminal return.

**Sababu:** quantiles ni za *terminal return*; SL/TP ni *touch events*. `P(kugusa Q90)` ni **kubwa
kuliko** `P(kumaliza juu ya Q90)`. Kuderivisha P(win) kutoka quantiles zilezile zilizoweka barriers
= self-confirmation: upendeleo wowote unazidishwa mara mbili.

### S2 — SAKAFU YA SL (kinga dhidi ya lots explosion)
```
SL_final = max( Q10_based ,  5 × cost_pips ,  0.5 × ATR )
```
**Sababu:** RCE inahesabu `lots = risk ÷ ((SL + cost) × pip_value)`. Soko likituliza, `Q10` inaweza
kuwa pips 2; kwa cost 2 pips, gharama ni **50% ya umbali wa SL** na lots zinakuwa kubwa mno — kelele
ndogo inagonga SL. Hii si tweak; ni **kinga ya kimfumo** dhidi ya low-volatility traps.

### S3 — KIZINGITI CHA EV KISIWE CHA PIPS
Pips hazilinganishwi kati ya TF/pairs. Tumia **mojawapo**:
```
(A)  EV ≥ k × cost_pips          (k ≈ 1.5 – 3)
(B)  EV_R = EV ÷ SL   →   EV_R ≥ threshold        ← inayopendekezwa
```
**Sababu:** kizingiti cha "pips 1" ni kikali sana D1 na legevu M5. R-units zinasawazisha TF zote,
pairs zote, volatility zote.

### S4 — P(fill) INABOOTSTRAP KUTOKA HISTORY
Fill Model inahitaji fills — ambazo hatuna bado. Bootstrap **inayopatikana sasa**:
```
Kutoka tick/bar history:  "kama entry ingekuwa X na cap ingekuwa C,
                           je bei ilipita zaidi ya cap kabla ya kujaza?"
Label:  fill = 1 / 0
```
Kisha: **demo → fine-tune · live → calibrate.** Hii inaruhusu kuanza **bila kusubiri data ya broker**.
Bootstrap hii ni halali kwa **stop/limit**; kwa **market** orders P(fill) inaanza na prior ya juu
na inakalibiwa demo/live (§5.3 ya standard ya data — latency haipo kwenye path ya kihistoria).

### S5 — OPPORTUNITY COST HAIINGII KWENYE LANGO
```
✔  EV_final = P(fill) × EV_signal
✘  EV_final = P(fill) × EV − (1 − P(fill)) × MissedOpportunity
```
**Sababu:** trade isipojaza, **hupotezi pesa** — unakosa faida tu. Kuiondoa kwenye EV ya trade moja
ni adhabu mara mbili.
**Mahali pake:** kupanga wagombea (nani apewe slot), allocation ya capital, portfolio optimization.

### S6 — CROSS-FITTING: output ya model inayolisha model nyingine ni OUT-OF-FOLD
Pipeline ya §1 ina tabaka: outputs za UNDERSTANDING (HMM posterior, Transformer P(up/down), CNN
pattern confidence, LSTM similarity) zinalisha DECISION (XGBoost/PPO) kama features. Sheria:
```
Output yoyote ya model inayotumika kama FEATURE ya model nyingine lazima iwe
OUT-OF-FOLD prediction ndani ya purged folds ZILE ZILE za DATA_SPLIT_PLAN.
In-sample predictions kama meta-features = UVUJAJI.
```
**Sababu:** model ya juu iliyofundishwa kwenye data ile ile inatoa in-sample predictions "safi
kupita kiasi" — meta-model inajifunza ukamilifu usiokuwepo live. Uvujaji huu **HAUONEKANI** kwa
sentinel ya shuffle (§4.2 ya standard ya data) — model iliyoshafundishwa haibadilishi output
zake data ya baadaye ikichanganywa. Kinga pekee ni nidhamu ya cross-fitting.
**Inahusu pia:** features zinazotokana na model yoyote iliyofit (sheria ya 8, §6.1 ya standard
ya data) — HMM inafundishwa expanding/per-fold, kamwe si full-sample.

---

## 4. MKATABA WA INTERFACE NA RCE

### 4.1 KAIROS-1 → RCE (pendekezo)
```
symbol · direction · entry · SL_final · TP · EV_signal · EV_final
       · p_tp_first · P(fill) · quality · strategy · confidence
```

### 4.2 RCE → KAIROS-1 (muktadha)
```
cost_pips   ← RCE ndiyo MAMLAKA ya gharama; model HAIKADIRII yake
spread ya sasa · budget state · slots zilizobaki
```

**Kanuni ya gharama (muhimu):** `cost_pips` ina **chanzo KIMOJA** (RCE) na **matumizi MAWILI**:
(a) EV-gate ya model, (b) sizing ya RCE. Namba ile ile — hakuna kuhesabu mara mbili, hakuna
kutofautiana.

### 4.3 Mgawanyo wa mamlaka
| KAIROS-1 **INAAMUA** | RCE **INAAMUA** |
|---|---|
| entry, direction, SL, TP | ukubwa (lots) |
| EV, ubora, strategy | ruhusa (gate) |
| P(fill) | bajeti na risk/trade |
| — | cost_pips (mamlaka) |

Model **haiamui** ukubwa wala ruhusa. RCE **haiamui** entry wala mwelekeo.

---

## 5. NIDHAMU YA DATA NA MAFUNZO

1. **As-of boundaries (multi-TF):** bar isiyofungwa **HAITUMIKI**. Wakati wa uamuzi wa H1 saa 10:00,
   D1 inayotumika ni **iliyofungwa jana**. Timeframes 7 = nafasi 7 za uvujaji.
2. **Purged + embargoed CV:** labels zinapishana kwa muda (kila entry ina horizon) — bila purge,
   CV ni ya uongo.
3. **CALIBRATION ni sharti gumu:** probability yoyote inayoingia maamuzi (`p_tp_first`, `P(fill)`)
   **lazima ipimwe**: "zilizopewa 70%, je zilishinda 70%?" (reliability curve / Brier score).
   Model isiyo-calibrated **hairuhusiwi** kulisha EV wala risk. Bila hii, lango la EV ni **pambo**.
4. **Bajeti ya data:** labels (trades), si bars, ndizo zinazopunguza. Kila model inayoongezwa
   inahitaji ihalalishwe kwa data iliyopo — si kwa matumaini.
5. **Fill-aware backtest:** trades zinazoshindwa kujaza ndani ya cap **hazihesabiwi kama trades**.
   Hii inaondoa upendeleo wa "perfect fills".
6. **Cross-fitting (S6):** output ya model inayolisha model nyingine ni out-of-fold, daima.
7. **Model-derived features** zinafundishwa expanding/per-fold (sheria ya 8, §6.1 ya standard
   ya data).

---

## 5A. NJIA YA DEEP MODELS — PRETRAINING NA MULTI-TASK (PD 2026-08-04)

**Tatizo:** trade-labels ni ~38,000 (§0.1 ya standard ya data). Transformer/LSTM/CNN
zikifundishwa from-scratch kwa labels hizo zitakariri kelele na R4 itazikataa. **Suluhisho:**
bajeti ya trade-labels inabana *hukumu za trade*, si *uelewa wa soko* — na uelewa wa soko
unaweza kujifunzwa kutoka data isiyo na labels za trade:

```
HATUA 1 — PRETRAIN (self-supervised, HAKUNA trade label):
   corpus:  bars zote za TRAIN+VAL (~770k H1 pooled; M1/ticks kwa encoders za chini)
   malengo: next-bar direction · masked-bar reconstruction · contrastive
            (sequences za regime moja karibu, tofauti mbali)
   ⚠ corpus inaishia trainval_end (2024-03-31). Kupretrain kwenye kipindi cha HOLDOUT
     ni uvujaji — marufuku kabisa.

HATUA 2 — FINE-TUNE (heads ndogo kwenye trade labels):
   encoder iliyoganda/nusu-ganda + heads: quantile · barrier(3) · quality
   parameters zinazofundishwa kwa labels 38k ni za heads pekee — ndogo

HATUA 3 — LANGO LILE LILE (§6):
   model iliyopretrainiwa inashindana na GBM baseline kama kila mtu.
   Isiposhinda → LESSON. Pretraining si tiketi ya kuingia; ni njia ya kufika mstarini.
```

**Multi-task shared trunk inaruhusiwa:** encoder mmoja + heads tofauti (quantile, barrier,
direction). S1 inahusu **labels na hukumu** — heads zibaki na labels huru (quantile: terminal
return; barrier: touch grid) na hakuna head inayolisha nyingine bila S6. Multi-task ni
regularizer mzuri kwa data ndogo; mgongano wa S1 haupo maadamu hukumu hazichanganyiki.

**Kwa nini hii ndiyo njia ya "kuona opportunity":** edge ya kuona setup sokoni inatokana na
representation ya hali ya soko (regime, structure, momentum katika muktadha). Representation
hiyo inajifunzika kutoka mamilioni ya bars bila label ya trade hata moja — kisha hukumu ya
trade (ndogo, ya gharama kubwa kwa data) inajengwa juu yake. Kutumia labels 38k kujifunza
representation NA hukumu kwa pamoja ndiko kunakofanya deep models kufeli kwenye trading.

---

## 6. VIGEZO VYA KUPOKELEWA
Model/component inaingia **TU** ikishinda bora ya sasa:
```
EV_R (net, baada ya gharama) > baseline ya sasa
calibration: Brier score / reliability inakubalika
fill-aware: EV imepimwa kwa trades zinazoweza kujaza
splits: TRAIN/VALIDATION; HOLDOUT ni MARA MOJA kwa mchanganyiko wa mwisho
pre-registration: vigezo vimeandikwa KABLA ya kuona namba
```
Isiposhinda → **LESSON**, haiingii. Hilo ni **jibu**, si kushindwa.

---

## 7. NJE YA WIGO (hati hii)
Sizing · malango ya risk · bajeti ya siku · execution — vyote ni vya
**`engine/docs/RISK_COST_ENGINE.md`**. Ufuatiliaji wa positions zilizo wazi ni idara ya nne (§4 ya
`docs/SYSTEM_ARCHITECTURE_V3.md`).
