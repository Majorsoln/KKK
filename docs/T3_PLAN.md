# T3 — MPANGO ULIOREKEBISHWA BAADA YA MAPITIO YA NJE

**Tarehe:** 2026-08-13 · **Chanzo:** `REVIEW_EXPERT_1.md` · `REVIEW_EXPERT_2.md` · uchambuzi wangu
**Inachukua nafasi ya:** §3.9 ya `IMPLEMENTATION_PLAN.md` (pendekezo la kwanza — limebatilika)
**Hadhi:** mpango wa kutekelezwa. Vigezo vyake vinahitaji sahihi ya PD kabla ya kuanza.

---

## 0. Kilichobadilika, kwa sentensi moja

Tulikuwa tunauliza *"je tunaweza kupima kwamba edge inazidi breakeven?"*
Tunapaswa kuuliza *"je tunaweza kupima kwamba edge inatosha **kutradiwa**?"*

Swali la kwanza linahitaji data mara nne zaidi ya tuliyonayo, na likijibiwa "ndiyo" linarudisha
Sharpe **0.24** — ambayo kwa MinBTL inaruhusu config **moja**. Hakuna mradi hapo.
Swali la pili linahitaji **chini ya tuliyonayo tayari**.

Kwa hiyo: **pendekezo langu la §3.9 — historia hadi 2003, symbols 28, dense rebuild — limeahirishwa
kabisa.** Halikuwa baya; lilikuwa linajibu swali baya.

---

## 1. Yaliyothibitishwa na wataalamu wote wawili, bila kuonana

| | |
|---|---|
| Kata **Transformer, LSTM, CNN, PPO** | sasa hivi, si baadaye |
| Kata **self-supervised pretraining** | si njia ya kununua uwezo kwa bajeti hii ya labels |
| **Meta-labelling** ndilo umbo sahihi | SETUP-v1 inaweka upande; model ya pili inaamua chukua/acha |
| **Sample-uniqueness weighting** ni lazima | `z = +28.8` yetu "itupwe kabisa kama ushahidi" |
| **Lengo endelevu** kwa screening | binary inapoteza magnitude |
| **Dense sampling ni udanganyifu** | 23× raw inanunua 2–3× effective |
| **2003 kwa robustness, si trade labels** | cost model ya leo haitumiki 2003 |
| **Alternative bars** si sasa | FX haina volume halisi |
| **Instrument breadth > history depth** | kwa effective N |
| **Trees (XGBoost) ndiyo architecture ya utafiti** | hadi ithibitishwe haitoshi |

> **Tahadhari ya uaminifu:** karibu kila moja ya haya ni jibu la swali nililowauliza mimi.
> Makubaliano yao ni dhaifu kuliko yanavyoonekana. Chenye uzito ni **walichokileta wenyewe**
> (§2 na §3 hapa chini).

## 1.1 Walipotofautiana — na uamuzi wangu

| | Wa 1 | Wa 2 | Uamuzi |
|---|---|---|---|
| Lengo kuu | H1 dense, net-R ranking | cross-sectional, siku 1–5 | **Meta-labelling kwenye L4 iliyopo kwanza.** Uchambuzi wa nguvu wa wa 2 unaua dense rebuild; wa 2 mwenyewe aliishia hapo |
| Cross-sectional | jaribio la pembeni | jengo lenyewe | **Config ya pili** kwenye bajeti (2 kati ya 7) — si kubadilisha mfumo kabla ya jaribio la kwanza |
| Horizon | 24H ibaki | pima IC decay curve | **24H inabaki ya msingi** (imeshasainiwa). Decay curve ni **characterisation** isiyoruhusiwa kuchagua horizon |
| HMM | kata | weka moja, filtered | **Kata.** Bajeti ni 7; thamani yake haijathibitishwa. Protocol yake imeandikwa kwa siku zijazo |
| Uongo mkubwa | volatility-momentum | multiple testing | **Vyote viwili** — matched sample kwa cha kwanza, budget counter kwa cha pili |

---

## 2. Kile wa 1 alicholeta chenyewe

| | |
|---|---|
| **Jaribio la kuua athari ya SETUP** | stratified bins zilizotangazwa (ATR · spread · momentum · session · pair · mwaka). +0.0638R ikishuka nusu si kufeli — ni tafsiri mpya |
| **Placebo mbili** | random-label na shuffled-score. *"Je pipeline yetu inaweza kutengeneza matokeo chanya pale hakuna signal?"* |
| **Held-out kwa symbol** | lango la pili, si la kwanza |
| **Features 25 kwa majina** | tunaweza kuanza siku ya kwanza |
| **Ufahamu wa exit geometry** | `E[R_24h]` dhaifu lakini **MFE yenye nguvu** ⇒ tatizo si entry alpha, ni **sera ya kutoka** |
| **"Ledger haiondoi selection bias"** | *"inaifanya ionekane. Hizo ni tofauti."* |

## 3. Kile wa 2 alicholeta chenyewe

| | |
|---|---|
| **δ_MER** | usipower kwa breakeven; power kwa **tradability**. Ndiyo hoja bora kuliko zote |
| **Identity ya gharama** | `√n ≤ κ·SR*/cost_R` — cost inakua kama `n`, target kama `√n` |
| **Config budget counter** | MinBTL kama **lango la CI**, si nia njema |
| **Shimo la A2** | HMM yenye filtered probabilities lakini **parameters zilizofit full-sample** — sentinel yetu haingeliona |
| **"Uchumi unaweka threshold; takwimu inaweka evidence standard"** | kubadilisha threshold ili kigezo kipitike kunavunja utengano huo |
| **Kigezo cha kufikika** | null simulation **kabla** ya run: je kigezo kinaweza kufikika kabisa? |

---

## 4. Vigezo vya kusainiwa — na jinsi vinavyotokana

Vyote vinahesabika **bila kugusa outcome data**, isipokuwa `cost_R` na `N_eff` ambavyo ni vipimo.

```
cost_R  ──►  n_max  ──►  δ_MER  ──►  N_req  ──►  je N_eff inatosha?
                │
                └──►  SR*  ──►  config budget
```

| Kigezo | Chanzo | Amri |
|---|---|---|
| `cost_R` | **kipimo** — commission + P(stop)·E[overshoot\|stop] | `cost-audit` |
| `N_eff` | **kipimo** — envelope ya makadirio manne | `effective-n` |
| `SR*` | uamuzi wa PD | — |
| `κ` | uamuzi wa PD (sehemu ya return unayokubali kuipoteza kwa gharama) | — |
| `n_max` | `(κ·SR*/cost_R)²` | `cost-audit` |
| `δ_MER` | `SR*/(2√n_max)` | `cost-audit` |
| `N_req` | `(z_α/2+z_β)²·p(1−p)/δ²` | `cost-audit` |
| bajeti | `exp(SR*²·miaka/2)` | `cost-audit` |

**Saini identity, si namba.** `n_max` inategemea `cost_R` na `N_eff` ambavyo ni vipimo;
namba iliyosainiwa leo inaweza kuwa si sahihi kesho. Identity inajirekebisha.

### 4.1 Kwa nini `SR* = 0.7` na si nyingine

| SR* | bajeti | tatizo |
|---|---|---|
| 1.0 | ~62 | ni ahadi kubwa; mtajaribiwa kuifikia kwa kutafuta |
| **0.7** | **~7.5** | vikwazo vitatu vinakubaliana hapa pekee |
| 0.5 | ~3 | mradi hauwezi kutekelezwa — *"hitimisho la uaminifu si kusaini 0.5, ni kutokufanya mradi"* |

Saini pamoja na dokezo: **kama edge halisi ni 0.5 tu, tunakubali hatutaiona.**

### 4.2 `two_sided = True` ni chaguo, si usahihi

Hypothesis ni ya upande mmoja (tunachukua hatua tu ikiwa **juu** ya breakeven). One-sided ingedai
`N_req = 31,500` badala ya `40,000` kwa δ = 0.007. **Tumechagua ya tahadhari kwa makusudi:** lango
linaloruhusu pesa halisi kupita liwe gumu kuliko lazima, si rahisi kuliko lazima.

---

## 5. Hatua — kwa mfuatano, na kila moja ikiwa na lango

### Hatua 0 — VIPIMO VIWILI ✅ **IMEKAMILIKA 2026-08-13**

```cmd
python -m src.data.cli cost-audit --cell 2.0/3.0
python -m src.data.cli effective-n --delta 0.0235
```

**Matokeo — sasa ni vipimo, si makadirio:**

| | Ilikadiriwa | **Ilipimwa** |
|---|---|---|
| `cost_R` (2.0/3.0) | 0.022 (commission pekee) | **0.0294** — overshoot inaongeza **34%** |
| `n_max` | 253/mwaka | **142/mwaka** (−44%) |
| `δ_MER` | 0.022 | **0.0235** (`dEV/dp_tp = 2.5`, si 2.0) |
| `N_req` | ~4,050 | **3,553** |
| `N_eff` | "~5×" / ~10,300 | **10,168** |
| **Hukumu** | — | **INATOSHA — mara 2.86** |

**Bar halisi: `+0.0300 p_tp`** (0.0065 hadi breakeven + 0.0235 δ_MER), ikilinganishwa na
**+0.0251** ambayo SETUP-v1 ililetea kwa wastani wa setups zote.

Envelope kamili ya `N_eff`:

| | | |
|---|---|---|
| `n_uniq` | 11,355 | concurrency ya labels zinazopishana |
| **`n_time`** | **10,168** | **kizuizi halisi** · τ = 2.49 |
| `n_cross` | 15,903 | factors huru **7.54** kati ya symbols 12 |
| `n_block` | 15,903 | blocks × breadth |

> **Factors 7.54, si 5.** Nilikadiria ~5 kwenye §3.9 na kwenye marekebisho yangu kwa
> mtaalamu wa 2. Kipimo kinasema **7.54** — symbols zetu ni huru zaidi kuliko nilivyodhani,
> na hiyo ndiyo sababu kubwa kwa nini mradi unabaki hai.

**Overshoot kwa R inathibitisha hoja iliyobishaniwa:**

| SL | over R |
|---|---|
| 0.50 ATR | **0.0285** |
| 2.00 ATR | **0.0153** |

Stop nyembamba inaumia **mara mbili** kwa gap ile ile — `R = overshoot/sl_pips`, kama
hesabu ilivyotabiri dhidi ya dai la mtaalamu wa 2, sasa ikithibitishwa na data.

### Hatua 1 — TANGAZA BAJETI (kabla ya evaluation ya kwanza) — **INASUBIRI SAHIHI**

`docs/TRIAL_BUDGET.md` imeandaliwa: **SR\* 0.7 · miaka 8.25 → configs 7.5**.
`budget.guard()` inakataa evaluation yoyote dhidi ya labels bajeti ikiisha.

Mgao uliotangazwa: **3** meta-labelling na variants · **2** cross-sectional · **2** akiba.

**Inakuwa halali PD anapocommit** — kama sahihi. Pamoja nayo, vitu vitatu vinahitaji
kusainiwa kwenye `SIGNATURES.md` kabla ya hatua 2:

| Kipengele | Uamuzi | Kwa nini ni uamuzi wa PD |
|---|---|---|
| `SR*` = **0.7** | bajeti = 7.5 configs | 1.0 ni ahadi kubwa inayoshawishi kutafuta; 0.5 inatoa configs 3 na mradi hauwezi kutekelezwa |
| `κ` = **0.50** | `n_max` = 142/mwaka | sehemu ya return unayokubali kuipoteza kwa gharama |
| cell = **2.0/3.0** | lengo la jaribio | **kuichagua baada ya kuona jedwali la EV ni uteuzi juu ya label** — lazima ikiriwe kwenye sababu, si kufichwa |

### Hatua 2 — UA ATHARI YA SETUP ✅ **IMEKAMILIKA 2026-08-14 · config 1/7**

Stratified bins zilizotangazwa: `atr_bin` (quantile 5) · `spread_bin` (4) · `session` ·
`symbol` · `year`. Kipimo: **`r_net` halisi** kwenye cell 2.0/3.0 — ikiwemo overshoot ya
stop na commission, si `p_tp`.

**HUKUMU: HALISI.**

| | |
|---|---|
| setups · controls | 25,314 · 27,007 |
| strata · zenye zote mbili | 2,966 · **2,503** |
| **common support** | **96.4%** |
| tofauti ghafi | **+0.0515 R** |
| **tofauti ndani ya strata** | **+0.0348 R** |
| imepungua | **32%** |
| 90% CI (block bootstrap kwa mwaka) | **[+0.0051, +0.0612]** — haiguzi sifuri |

**Theluthi mbili imebaki.** Kichujio si kioo cha volatility.

**Common support 96.4% — bora kuliko ilivyoogopwa.** Nilikuwa nimeonya kwamba gate ya
momentum ingeacha setups bila controls zinazolingana. Haikutokea.

#### Kikwazo cha dai hili — kisomwe kabla ya kuendelea

**Momentum HAIKUDHIBITIWA, na siyo kwa kusahau.** Orodha ya mtaalamu wa 1 iliitaja; niliiacha
kwa sababu **huwezi kudhibiti kinachofafanua treatment**. Setups zina `|impulse| ≥ 2.5·ATR`
**daima**; controls zenye msukumo huo ni zile zilizofeli gate nyingine tu. Common support
isingekuwepo.

Kwa hiyo dai halisi ni finyu kuliko linavyoonekana:

> Makali **hayaelezwi na** kiwango cha volatility, spread, saa, symbol, wala mwaka.
> **Hayasemi** makali si "momentum tu" — kwa sababu momentum ndiyo sheria yenyewe.

Hilo linajibu swali lililoulizwa (*je ni uteuzi wa volatility?* — **hapana**), lakini
lisidaiwe kujibu zaidi ya hapo.

**CI ni pana.** Mpaka wa chini ni `+0.0051` — karibu na sifuri. Block bootstrap kwa miaka 9
inatoa resampling ya mikubwa. Athari ni chanya, **haijabanwa vizuri**.

#### Bar ya kweli, kwa R — iandikwe KABLA ya hatua 3

Vitu vyote kwa units zilezile, cell 2.0/3.0 (`dEV/dp_tp = 2.5`):

| | R |
|---|---|
| EV net ya setups sasa | **−0.0163** |
| hadi breakeven | +0.0163 |
| δ_MER (0.0235 p_tp × 2.5) | +0.0588 |
| **JUMLA INAYOHITAJIKA** | **+0.0751** |
| kichujio kizima kililetea | **+0.0348** |

**Model inahitaji mara 2.2 ya kile kichujio kizima kilifanya** — lakini kwenye **decile ya
juu** badala ya wastani wa setups zote.

Inawezekana **kama** kuna heterogeneity ndani ya setups; ndicho hasa kupanga kunanunua.
Lakini ni bar ya juu, na imeandikwa **kabla ya jaribio**, si baada.

### Hatua 3 — META-LABELLING KWENYE L4 ILIYOPO (config 2)

**Hakuna label mpya. Hakuna rebuild.** Points 25,374 zilizosainiwa.

- Sample: setups 25,374 · purged 5-fold · embargo 36 bars · holdout haiguswi
- Model: XGBoost **moja**, hyperparameters zimefungwa kwenye ledger **kabla** ya run
- Cell: **moja iliyofungwa mapema.** Kuichagua baada ya kuona jedwali la EV ni **uteuzi juu ya
  label** — irekodiwe kama registered rule mpya pamoja na ukiri huo
- Baseline: SETUP-v1 chukua-zote
- Uzito: `uniqueness` kutoka `effective-n`, si idadi ghafi

**Kufaulu kunahitaji vyote vitatu:**

| # | Kigezo | Kizingiti |
|---|---|---|
| 1 | Calibration | reliability slope ∈ [0.8, 1.2]; Spiegelhalter/HL p > 0.05 |
| 2 | Discrimination | Spearman ρ ≥ 0.7 kwenye deciles 10; trend p < 0.01 |
| 3 | Kiuchumi | fitted top-decile p̂ ≥ breakeven + δ_MER; 5th percentile ya block-bootstrap > breakeven |

**Vipimo visivyoruhusiwa kutangaza mafanikio:** AUC · accuracy · log-loss · in-fold · cell
nyingine · "ilikaribia".

**Vifungu vinne vya ulinzi:**

| | |
|---|---|
| **Calibration ni logistic, si isotonic** | top bin ya isotonic **ni** empirical mean — hainunui nguvu yoyote. Faida yote inatokana na pooling ya parameters mbili kwenye N nzima |
| **Goodness-of-fit gate** | fitted ikaribiane na empirical ndani ya 1 SE kwenye deciles mbili za juu. Ikizidi, njia ya parametric inakataliwa **na kigezo kinaanguka** |
| **Kufikika** | null simulation **kabla** ya run. Kigezo kisipofikika, badilisha **design**, si threshold |
| **Kutotinker** | run **moja**. Ikianguka, bajeti inapungua 1, na rule inayofuata lazima ibadilishe kitu cha **kimuundo** — si hyperparameters |

### Hatua 4 — PLACEBO (haigharimu bajeti — ni ukaguzi wa pipeline)

Random-label na shuffled-score. Pipeline ikitoa matokeo chanya pale hakuna signal, **kila kitu
kilicho juu yake ni batili.** Hii inaendeshwa **kabla** ya kuamini hatua 3.

### Hatua 5 — MAE / MFE (nyongeza yangu, si yao)

Wote wawili waliziita **za hiari**. **Sikubaliani**, kwa sababu mbili:

1. Gharama ni **karibu sifuri** — ticks tayari ziko kwenye kumbukumbu wakati wa build
2. Swali linaloweza kujibiwa nazo linaweza **kubadilisha mradi mzima**:

> *Kama `E[R_24h]` ni dhaifu lakini **MFE ina nguvu** — tatizo si entry alpha. Ni kwamba entry ina
> taarifa, lakini sera ya kutoka ya 24H inaiharibu.*

Tumekuwa tukipima barrier outcomes kwa miezi. Kama hitimisho ni "entry ilikuwa sahihi, exit
ilikuwa mbaya", hilo ni jibu tofauti kabisa na "hakuna edge" — na hatuwezi kulitofautisha bila
MAE/MFE. Kuziacha ni kuokoa kitu kisichogharimu kitu.

---

## 6. Yaliyoahirishwa — na sharti la kurudi

| | Sharti la kurudi |
|---|---|
| Historia 2003–2016 | `N_eff < N_req` **au** hatua 3 imefaulu na tunahitaji stress testing |
| Symbols 12 → 28 | hatua 3 imefaulu na breadth inahitajika kwa cross-sectional |
| Dense labelling | `N_eff < N_req` na uchambuzi unaonyesha dense inasaidia (2–3×, si 23×) |
| Two-level resolver | dense ikiidhinishwa — na lazima ilingane na cells **1,308,025** zote |
| HMM | bajeti ikiruhusu; **A1 pekee** (walk-forward fit + filtered), states 2 |
| Deep models, PPO, pretraining | hatua 3 imefaulu **na** bajeti imebaki |

---

## 7. Shimo lililogunduliwa kwenye kinga zetu

**A2 — parameters zilizofit full-sample, probabilities filtered.**

Sentinel yetu inaangalia as-of rules kwenye **features**. Model iliyofit kwenye sample nzima
kisha ikitoa filtered probabilities **inaonekana safi** — na si. States zenyewe zilifafanuliwa kwa
kutumia siku zijazo.

| | Chanzo cha state probability |
|---|---|
| **A1 — halisi** | parameters walk-forward, filtered hadi `t` pekee |
| **A2 — leak fiche** | filtered, lakini parameters **full-sample** |
| **B — leak wazi** | smoothed / Viterbi |

Sheria ya 8 ya §6.1 tayari inakataza hili (*"feature inayotokana na MODEL inafundishwa
per-fold"*), lakini **hakuna kinachoikagua**. Model yoyote iliyofit inayoingia pipeline lazima
ithibitishe fit yake ilikuwa ndani ya fold.

---

## 8. Mambo mawili yaliyobaki wazi

**1. Lengo `Y` halijafafanuliwa kikamilifu.** "Realized executable net-R for a pre-specified
action" — lakini **action ipi**? Trade inayotekelezeka inahitaji SL (RCE inaihitaji kwa sizing).
Bila stop, si trade. Na kuchagua cell kwa jedwali la EV ni uteuzi juu ya label. Hatua 3
inashughulikia hili kwa kufunga cell mapema **na kukiri gharama yake kwenye rekodi** — si
kutatua, ni kulipa kwa uwazi.

**2. `n_max` inamaanisha kutrade sehemu ndogo mno.** Kwa `n_max = 253` kati ya setups 3,076 kwa
mwaka, tunatrade **8% ya setups = 0.36% ya bars zote**. Je kuna heterogeneity ya kutosha ndani ya
setups kwa model kupata `δ_MER` kwenye 8% ya juu? Hilo ndilo jaribio lenyewe — lakini ni bar ya
juu kuliko inavyoonekana, na inapaswa kusemwa kabla, si baada.
