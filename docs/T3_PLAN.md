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
- Model: **moja**, hyperparameters zimefungwa kwenye code **kabla** ya run
- Cell: **moja iliyofungwa mapema.** Kuichagua baada ya kuona jedwali la EV ni **uteuzi juu ya
  label** — irekodiwe kama registered rule mpya pamoja na ukiri huo
- Baseline: SETUP-v1 chukua-zote
- Uzito: `uniqueness` kutoka `effective-n`, si idadi ghafi

**Amri (zikiwa zimejengwa 2026-08-14, tests 383 zinapita):**

```
python -m src.data.cli build-features
python -m src.data.cli meta-label --cell 2.0/3.0
```

`build-features` inajenga L3 — features 25 kwa kila symbol, holdout haisomwi kabisa (G2).
`meta-label` inaunganisha: features → points za cell → uzito wa `uniqueness` → purged 5-fold →
malango matatu. `budget.guard()` iko **kabla** ya kazi yoyote.

#### Model ya kwanza ni logistic yenye L2, si XGBoost — na kwa nini

Mpango wa awali ulisema "XGBoost moja". Umebadilika baada ya kupima mazingira: **`xgboost`,
`sklearn` na `lightgbm` hazijafungwa** popote kwenye mnyororo wetu. Chaguo lilikuwa kati ya
kuongeza dependency isiyopimika hapa, au kuanza na baseline ambayo wataalamu wote wawili
walikuwa **wameidai kama ya lazima kabla ya chochote kigumu zaidi**. Nimechagua la pili.

Hii si kupunguza lengo. Sehemu ngumu ya jaribio hili si model — ni purged CV, standardization ya
ndani ya fold, uzito wa uniqueness, na malango yasiyoweza kupindishwa. Vyote hivyo ni
**model-agnostic**, na ndivyo vilivyojengwa na kupimwa. Model ni kipande kinachobadilishwa kwa
flag moja:

```
python -m src.data.cli meta-label --model xgboost      # `pip install xgboost` ikishafanyika
```

Booster ikiingia, inapita **malango yale yale**, na inagharimu **config nyingine ya bajeti** —
si "run ile ile kwa model bora". Kama logistic ikifaulu na booster ikaongeza kidogo, tofauti hiyo
ni ndogo kuliko kelele ya sampuli yetu; kama logistic ikianguka na booster ikafaulu, hilo ni dai
kubwa linalohitaji hatua 4 kwanza.

#### Breakeven inatoka wapi — na dhana yake

`breakeven = p_tp ya msingi + gap_to_breakeven`, ambapo `gap` inatoka `cost_audit.json`
(`−EV_net ÷ dev_dp`, `dev_dp = 1 + tp/sl = 2.5`). Hiyo ni **linearization** inayodhania uzito
unahama **TP ↔ SL** huku timeout ikibaki ile ile. Subset iliyochaguliwa na model inaweza kuwa na
timeout rate tofauti, kwa hiyo `R` **halisi** ya kila decile inaripotiwa kando kama ushahidi —
**si kama lango**. Lango lililotangazwa kabla ya run halibadilishwi baada ya kuona data.

`N_eff` **inahesabiwa upya kwa rows zilizopata score**, si kunakiliwa kutoka `effective_n.json`.
Ile ni ya setups 25,314; baada ya NaN za features na coverage ya folds sampuli ni ndogo, na
kutumia namba kubwa kungefanya kifungu cha nguvu kisifanye kazi — ndicho kitu pekee
kinachozuia sampuli ndogo kutoa jibu la kusadikisha.

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

#### MATOKEO — 2026-08-14 · config 2/7 · **IMEFELI**

`meta_label_logistic.json` · setups 25,314 · folds 5/5 · NaN 0 · N_eff 10,168 ≥ N_req 3,545

| Lango | Thamani | Kizingiti | |
|---|---|---|---|
| Calibration | slope **1.0713** | [0.8, 1.2] | **PASS** |
| Discrimination | ρ **0.8182** | ≥ 0.70 | **PASS** |
| Kiuchumi | fitted **0.3159** | ≥ 0.3212 | **FAIL** |

Lango la 3 lina masharti **mawili**. Sharti la mpaka wa chini **limepita**
(0.3043 > breakeven 0.2977). Lililoanguka ni la nukta: **0.3159 dhidi ya 0.3212** —
pungufu la **0.0053 p_tp**.

**Kilichopatikana ni halisi lakini hakitoshi.** Lift ya decile ya juu ni
0.3159 − 0.2911 = **0.0248 p_tp**, dhidi ya 0.0300 iliyohitajika. Ni **83%** ya njia.
Deciles zinapanda kwa mpangilio (ρ 0.82) — model **inapanga**, haibahatishi.

#### Kosa la MUUNDO lililofichuliwa na matokeo haya

`R` halisi kwa decile inasimulia hadithi tofauti na lango:

| | decile 1 | decile 10 | jumla |
|---|---|---|---|
| `R` halisi | −0.0600 | **+0.0656** | −0.0163 |

Lift ya `R` ni 0.0656 − (−0.0163) = **+0.0819 R**, wakati bar iliyoandikwa kabla ya
hatua 3 ilikuwa **+0.0751 R**. Lango la `p_tp` linatoa lift ya 0.0248 × 2.5 = **+0.0620 R**
kwa data ile ile.

Tofauti ya **0.0199 R** ina chanzo kimoja: lango liliandikwa kwenye nafasi ya `p_tp`
kwa kutumia `dEV/dp_tp = 1 + tp/sl`, **linearization inayodhania timeout rate haibadiliki**.
Subset iliyochaguliwa na model ina muundo tofauti wa timeout/overshoot, kwa hiyo proxy
inapima chini ya uchumi halisi.

**Hili ni kosa langu la muundo, si la data.** Nilichagua kupima kitu kinachokaribiana na
kile tunachokitaka badala ya kile tunachokitaka chenyewe. Nililiona likiwezekana na
niliandika onyo kabla ya run — onyo hilo sasa limetimia.

**Halibadilishi hukumu.** Kusoma run hii upya kwa lango jipya ni **kuhamisha lango baada
ya kuona data**, na ndilo kosa ambalo muundo huu wote upo kulizuia. Config 2 imetumika,
hukumu ni IMEFELI, na `+0.0656 R` haina CI wala haijapimwa dhidi ya null yoyote.

**Kinachofuata, kwa mpangilio:**

1. **Hatua 4 (placebo) — bure.** Inatoa null ya `ρ` **na** ya `R` ya decile ya juu bila
   kugharimu chochote. Ndiyo njia pekee ya kujua kama `+0.0656 R` ni kitu au ni kelele,
   bila kutumia config nyingine.
2. Uamuzi wa config 3 ni wa PD, ukiwa na ufichuzi huu mezani.

### Hatua 4 — PLACEBO (haigharimu bajeti — ni ukaguzi wa pipeline)

**Amri (imejengwa 2026-08-14):**

```
python -m src.data.cli placebo --reps 20
```

Njia ya kuharibu labels ni **mzunguko wa duara ndani ya kila symbol**, si kuchanganya
rows. Kuchanganya kunavunja autocorrelation ya labels pia, na null inayotokana nayo ni
**nyembamba kupita kiasi** — kila kitu kinaonekana muhimu ukilinganisha nayo. Mzunguko
unahifadhi muundo wote wa mfululizo na unavunja **upatanifu na features pekee**, ambao
ndio hasa unaodaiwa.

Inaripoti p-value ya upande mmoja `(#{null ≥ halisi} + 1) ÷ (N + 1)` kwa takwimu tatu:
`ρ`, `top fitted`, na **`top R halisi`**. Ya tatu ndiyo inayojibu swali lililoachwa wazi
na hatua 3 — bila kugharimu bajeti, kwa sababu labels zilizoharibiwa haziwezi kuchagua
strategy.

#### MATOKEO — 2026-08-14 · `rotation` · marudio 20

| Takwimu | Halisi | null p50 | null p95 | null max | p |
|---|---|---|---|---|---|
| discrimination `ρ` | +0.8182 | +0.3763 | +0.8067 | **+0.8182** | 0.095 |
| top fitted | +0.3159 | +0.2972 | +0.3087 | +0.3095 | 0.048 |
| top `R` halisi | +0.0661 | +0.0275 | +0.0537 | +0.0573 | 0.048 |

**Lango la placebo limewaka: `ρ` haitofautishiki na kelele.** Marudio ya 20 yalitoa
`ρ = +0.8182` — sawa kabisa na halisi.

#### Jambo la kwanza: kizingiti cha 0.7 hakikuwa lango hata siku moja

null p95 ni **+0.8067**. Kizingiti nilichokitangaza, **0.70**, kiko **ndani** ya mgawanyo
wa kelele — chini ya asilimia 95. Maana yake: `ρ ≥ 0.7` ingepatikana kwa bahati **zaidi ya
mara moja kati ya kumi**. Lango lililopita hatua 3 halikuwa likipima chochote.

Nilichagua 0.7 **kwa hoja**, si kwa kupima. §5 ya mpango huu inasema wazi *"null simulation
**kabla** ya run"*. Niliandika sharti hilo mimi mwenyewe kisha nikaendesha hatua 3 kabla ya
hatua 4. Hilo ni kosa la mpangilio, si la takwimu, na ni langu.

#### Jambo la pili: null yenyewe imechafuliwa

Chini ya null **halisi**, model iliyofundishwa kwa labels zilizoharibiwa haipaswi kuwa na
uwezo wowote wa kuchagua trades bora. `R` ya decile yake ya juu ingepaswa kukaa kwenye
msingi wa sampuli: **−0.0163**.

Imekaa **+0.0275**.

Null haiwezi kuchagua trades zenye faida kwa bahati. Kwa hiyo **mzunguko haukuvunja
uhusiano — umeuhifadhi**. Sababu: labels zina kumbukumbu ndefu (regimes za volatility
zinaishi miezi), kwa hiyo `y(t − k)` bado inatabirika kutoka features za `t` hata `k`
ikiwa kubwa. Model inajifunza *"volatility ikiwa juu, `p_tp` inapanda"* kutoka kwenye
labels zilizozungushwa, na dai hilo linabaki kweli.

**Matokeo ya hili:** p-value zote tatu hapo juu ni **CONSERVATIVE** — kubwa kuliko
zinavyostahili. Null iliyochafuliwa ni ngumu kupita kiasi kuishinda.

`placebo` sasa inakagua hili yenyewe na kuripoti `null_contaminated`. Ukaguzi huo unapima
**chombo cha kupimia**, si strategy — hauguzi lango lolote la hatua 3 wala haubadilishi
hukumu yoyote. Ndiyo maana kuongezwa kwake baada ya kuona matokeo ni halali.

#### Hitimisho lisilo na kupendeza

Hatujui bado kama `+0.0661 R` ni kitu. Tunajua mambo matatu:

1. **Hukumu ya hatua 3 inabaki IMEFELI**, na sasa kwa sababu mbili badala ya moja: lango
   la kiuchumi lilianguka, **na** lango la discrimination lililo "pita" halikuwa lango.
2. **Kizingiti chochote cha baadaye lazima kitoke kwenye null iliyopimwa**, si kwenye
   hoja. Hii ndiyo faida halisi ya hatua 4, na imelipwa kwa config moja.
3. **Null ya `rotation` haitoshi peke yake.** Inahitaji `shuffle` kama mpaka wa pili:
   `shuffle` inavunja kila kitu (null NYEMBAMBA MNO), `rotation` inahifadhi kumbukumbu
   ndefu (null PANA MNO). Ukweli uko kati yao, na kuripoti mmoja pekee ni kudanganya
   upande mmoja.

#### MATOKEO — 2026-08-14 · `shuffle` · marudio 20

| Takwimu | Halisi | null p50 | null p95 | null max | p |
|---|---|---|---|---|---|
| discrimination `ρ` | +0.8182 | −0.1455 | +0.5176 | +0.5636 | **0.048** |
| top fitted | +0.3159 | +0.2881 | +0.2968 | +0.3024 | **0.048** |
| top `R` halisi | +0.0661 | −0.0080 | **+0.0716** | +0.1071 | **0.143** |

**Ukaguzi wa null: msingi −0.0163 R · null median −0.0080 R → "null iko kwenye msingi".**
Dhana ya uchafuzi imethibitishwa: `rotation` ilihifadhi taarifa, `shuffle` haikuhifadhi.

**Picha inayotokea, na ni ya kugawanyika:**

* **Uwezo wa kupanga ni HALISI.** `ρ = +0.8182` iko juu ya null max (+0.5636) kwa **0.25**
  — mbali, si kwenye ukingo. Hii si sanaa ya pipeline.
* **Faida ya kiuchumi HAIJATHIBITIKA.** `top R` p = **0.143** — na hiyo ni chini ya null
  **nyembamba kuliko zote**, ile inayosamehe zaidi. Draws tatu kati ya 20 zilizidi
  +0.0661 kwa bahati tupu.

Sababu ya tofauti: `R` ina kelele nyingi zaidi kuliko `p_tp` (timeout, overshoot). Model
inapanga kweli, lakini mpangilio hauzai pesa za kutosha kupimika kwenye cell hii.

Hii inakubaliana kabisa na hatua 3: discrimination ilipita kwa haki, kiuchumi ilianguka
kwa haki. **`+0.0661 R` ni kelele hadi ithibitishwe vinginevyo.**

### Null ya tatu — `block`, na kwa nini ndiyo sahihi

`rotation` na `shuffle` zote zina kasoro **inayojulikana na iliyopimwa**:

| Njia | Inavunja nini | Kasoro |
|---|---|---|
| `rotation` | upatanifu wa karibu pekee | inahifadhi regimes za miezi → **signal iko ndani ya null** (imepimwa: +0.0275 dhidi ya msingi −0.0163) |
| `shuffle` | kila kitu | inavunja hata `τ = 2.49` → **null nyembamba kuliko ukweli** |
| **`block`** | nafasi za vipande | inahifadhi `τ` ndani ya kipande, inavunja upatanifu wa regimes |

`block` (chaguo-msingi sasa, urefu 32 points ≈ miezi 1.5) inabadilisha **nafasi za vipande
vya mfululizo**, si rows. Ndiyo null pekee kati ya tatu isiyo na kasoro inayojulikana.

```
python -m src.data.cli placebo --mode block --reps 200
```

Marudio 20 yana p ndogo kabisa ya `1/21 = 0.048`. Dai lolote lenye nguvu linahitaji ≥ 200.

#### MATOKEO — 2026-08-14 · `block (32)` · marudio 200

| Takwimu | Halisi | null p50 | null p95 | null max | p |
|---|---|---|---|---|---|
| discrimination `ρ` | +0.8182 | +0.4219 | **+0.8545** | +0.9273 | **0.075** |
| top fitted | +0.3159 | +0.2985 | +0.3126 | +0.3173 | 0.025 |
| top `R` halisi | +0.0661 | +0.0283 | +0.0864 | +0.1160 | **0.124** |

**Ukaguzi wa null: +0.0283 dhidi ya msingi −0.0163 — IMECHAFULIWA TENA.**

### Chanzo halisi cha uchafuzi: si muda, ni SYMBOL

Nilidhani `block` ingetatua tatizo kwa sababu nilidhani uchafuzi ulikuwa wa **kumbukumbu
ya muda**. Sikuwa sahihi. Jedwali linaonyesha mchoro tofauti kabisa:

| Njia | Inavunja `symbol → label`? | Null imechafuliwa? |
|---|---|---|
| `rotation` (ndani ya symbol) | **hapana** | ndiyo (+0.0275) |
| `block` (ndani ya symbol) | **hapana** | ndiyo (+0.0283) |
| `shuffle` (kila kitu) | **ndiyo** | **hapana** (−0.0080) |

Mchoro ni safi kabisa: **null zote zinazozungusha NDANI ya symbol zimechafuliwa; ile
inayovunja mipaka ya symbol haijachafuliwa.** Urefu wa kipande hauhusiki.

Sababu: symbols zina `p_tp` tofauti. Model inaweza kutambua symbol kutoka features
(`spread_atr`, `atr_pct`, mgawanyo wa `rsi` — vyote vina alama ya symbol), kisha
kutabiri base rate ya symbol hiyo. Hiyo inatoa:

* deciles zinazopanda (`ρ` chanya) ✓
* decile ya juu yenye `p_tp` kubwa ✓
* decile ya juu yenye `R` bora ✓

...bila **ujuzi wowote wa wakati**. Na kwa sababu mzunguko wa ndani ya symbol unahifadhi
base rate ya kila symbol kamili, **ujuzi huo unabaki ndani ya null**.

### Hitimisho la hatua 4 — na ni hasi

`rotation` na `block` **zinashikilia base rate ya kila symbol sawa**. Kwa hiyo
kulinganisha nazo ndiko hasa kupima: *"je model inaongeza chochote ZAIDI ya kujua ni
symbol ipi?"*

Jibu: **hapana.**

| | p chini ya null inayoshikilia symbol |
|---|---|
| discrimination `ρ` | **0.075** — haitoshi |
| top `R` halisi | **0.124** — haitoshi |

`top fitted` p = 0.025 ni pekee iliyo chini ya 0.05. Ni takwimu dhaifu kuliko zote kati ya
tatu (inahusu ukubwa wa calibration, si uchumi), iko kwenye ukingo wa null p95 (0.3159
dhidi ya 0.3126), na ni moja kati ya vipimo vitatu vilivyoangaliwa. Haibebi hitimisho.

**`ρ = 0.8182` iliyoonekana kubwa kwenye hatua 3 ni utambuzi wa symbol, si ujuzi wa
wakati.** Model haikujifunza *lini* kuchukua trade; ilijifunza *symbol ipi* ina base rate
kubwa. Hilo si meta-labelling — na base rate tayari inalibeba.

**Amri ya kuthibitisha moja kwa moja** (haigharimu bajeti):

```
python -m src.data.cli placebo --within-symbol --reps 200
```

`--within-symbol` inaondoa base rate ya kila symbol kabla ya kupima chochote. Model
inayojua symbol pekee inaanguka hadi sifuri. Kinachobaki, kikibaki, ndicho ujuzi wa kweli
wa wakati.

#### MATOKEO — 2026-08-14 · `block (32)` · marudio 200 · **ndani ya symbol**

| Takwimu | Kabla | Baada | null p95 | p |
|---|---|---|---|---|
| discrimination `ρ` | +0.8182 | **+0.5152** | +0.4545 | **0.040** |
| top `R` halisi | +0.0661 | +0.0586 | +0.0791 | 0.119 |

**Sehemu kubwa ya `ρ` ilikuwa utambuzi wa symbol** — imeanguka kwa **0.30** mara base rate
za symbols zilipoondolewa. Dhana imethibitishwa.

**Kilichobaki ni halisi lakini kidogo.** `ρ = 0.5152` iko juu ya null p95 (0.4545), p =
**0.040**, na null bado ni conservative kidogo — kwa hiyo p halisi ni ndogo zaidi. Kuna
ujuzi wa wakati, umepimika, ni dhaifu.

**Hakizai pesa.** `top R` p = **0.119**. Ujuzi upo, hauvuki gharama.

### Kilichokuwa mbele ya macho yetu tangu mwanzo

| symbol | `p_tp` | `R` halisi |
|---|---|---|
| EURCHF | 0.2426 | **−0.1273** |
| EURGBP | 0.2595 | **−0.1217** |
| XAUUSD | 0.2826 | −0.0361 |
| … | … | … |
| EURJPY | 0.3079 | **+0.0230** |
| GBPJPY | 0.3220 | **+0.0609** |
| USDJPY | 0.3343 | **+0.0687** |

**Utofauti wa `R` kati ya symbols ni 0.1959 — mara 2.6 ya lift nzima iliyohitajika
(+0.0751 R).**

Tulitumia miezi kujenga model itakayotafuta +0.0751 R kutoka kwenye **mchanganyiko** wa
symbols 12, wakati mchanganyiko wenyewe unaficha utofauti wa 0.1959 R. Crosses tatu za
JPY zina EV chanya kwenye cell hii **bila model yoyote**; EURCHF na EURGBP zinapoteza
zaidi ya 0.12 R kila trade.

**Pooling ndilo lilikuwa kosa, si model.** Sheria ya 1 ya §6.1 (scale-free) ilifanya
features zilinganishwe kati ya symbols — na nikadhani hilo lilitosha kufanya pooling
iwe halali. Haitoshi. Features zinazolinganishwa hazifanyi **uchumi** ulinganishwe.

#### Onyo la lazima kabla ya hatua yoyote inayofuata

**Kuchagua crosses za JPY baada ya kuona jedwali hili ni uteuzi juu ya label** — dhambi
ile ile ambayo `r1-ev`, `cost-audit --cell` na muundo huu wote unaizuia. Jedwali sasa
linaripoti **mpaka wa chini wa block bootstrap ya miaka** kwa kila symbol, kwa sababu
kwa symbols 12 tofauti ya kubahatisha peke yake inaweza kufika ~3.4 SE, na jicho
haliwezi kutofautisha.

Config yoyote inayotumia ugunduzi huu **lazima**:
1. itangazwe kama registered rule mpya pamoja na ukiri kwamba ilitokana na jedwali hili;
2. iwe na sababu ya **kiuchumi** iliyoandikwa kabla, si "namba ilikuwa kubwa" (mfano: JPY
   crosses zina trend ndefu zaidi kwa sababu ya carry na sera ya BOJ, kwa hiyo TP:SL ya
   3:2 inawafaa);
3. ipimwe kwenye mpaka wa chini, si kwenye nukta.

#### Mipaka ya chini — 2026-08-14

| symbol | `R` | p5 |
|---|---|---|
| EURCHF | −0.1273 | **−0.1662** |
| EURGBP | −0.1217 | **−0.1582** |
| XAUUSD | −0.0361 | −0.0949 |
| USDCAD | −0.0018 | −0.0351 |
| EURJPY | +0.0230 | −0.0119 |
| GBPJPY | +0.0609 | −0.0275 |
| USDJPY | **+0.0687** | **+0.0120** |

**USDJPY pekee ndiyo yenye p5 juu ya sifuri — na hiyo ndiyo tatizo lenyewe.**

Kati ya symbols 12, bora zaidi **karibu daima** itakuwa na p5 chanya kwa bahati tupu.
Kigezo cha 5% ni cha jaribio **moja**; hapa tumeangalia 12. Marekebisho ya Šidák yanadai
kila symbol ifikie asilimia `1 − 0.95^(1/12) = 0.427`, si 5 — **tofauti ya mara kumi**.

Kwa `sd` inayokadiriwa kutoka p5 yenyewe (`(0.0687 − 0.0120)/1.645 ≈ 0.0345`), mpaka wa
USDJPY ulioreikebishwa ni takriban **−0.022**. **Haishikilii.**

Bendera ya toleo la kwanza la jedwali (`<-- juu ya sifuri`) iliwekwa kwenye p5 ghafi. Hiyo
ilikuwa **mwaliko wa kosa lile lile ambalo jedwali lilipaswa kulizuia**. Sasa bendera
inategemea mpaka wa FWER pekee, na jedwali linaripoti safu zote mbili.

#### Asymmetry ndiyo ugunduzi halisi

| Upande | Ukubwa dhidi ya kelele | Unashikilia? |
|---|---|---|
| **Kuingiza** USDJPY | +0.0687, ≈ 2 SE | **hapana** |
| **Kuondoa** EURCHF | −0.1273, ≈ 5 SE | **ndiyo** (FWER ≈ −0.19) |
| **Kuondoa** EURGBP | −0.1217, ≈ 5 SE | **ndiyo** (FWER ≈ −0.18) |

**Hatujui symbol ipi ya kuingiza. Tunajua zipi za kuondoa.** EURCHF na EURGBP zinapoteza
0.12 R kila trade, mbali kabisa na kelele, na zimekuwa zikizivuta nyingine chini muda wote.

Hii ni habari inayoweza kutumika, na ni kinyume cha ilivyoonekana jana.

#### Mtihani wa utaratibu, si wa jedwali

Jedwali linaloonyesha JPY juu na EUR-crosses chini linaweza kuwa (a) utaratibu wa
kiuchumi au (b) matokeo ya bahati yaliyopangwa. Kuvitofautisha kunahitaji kipimo
**kisichojua label**.

`placebo` sasa inaripoti Spearman kati ya mpangilio wa `R` na mpangilio wa **trendiness**
(`eff_ratio_24h`, `adx14`) — vyote vinahesabiwa **kutoka bei pekee**. Nadharia: SETUP-v1
ni bet ya kufuata trend yenye TP:SL 3:2; symbols zinazozunguka (EURCHF, EURGBP) zinaiadhibu,
zinazotrend (JPY crosses) zinailipa.

* `ρ` kubwa ⇒ kuna utaratibu, na sheria inaweza kuandikwa kwa **trendiness**, si kwa majina
  ya symbols. Sheria kama hiyo si uteuzi juu ya label.
* `ρ` ndogo ⇒ jedwali ni orodha ya matokeo, na hakuna sheria ya kuandika.

Points 12 pekee, kwa hiyo `ρ` hii ni dalili, si ushahidi. Lakini ndiyo tofauti kati ya
nadharia inayoweza kupimwa na uchimbaji.

#### MATOKEO — 2026-08-14

| symbol | `R` | p5 | **FWER** |
|---|---|---|---|
| EURCHF | −0.1273 | −0.1683 | **−0.2032** |
| EURGBP | −0.1217 | −0.1592 | **−0.1795** |
| … | … | … | … |
| EURJPY | +0.0230 | −0.0095 | −0.0288 |
| GBPJPY | +0.0609 | −0.0263 | −0.0632 |
| USDJPY | +0.0687 | +0.0168 | **−0.0094** |

**Hakuna symbol yenye FWER chanya.** USDJPY, iliyokuwa na p5 chanya, imeanguka hadi
−0.0094 marekebisho ya multiplicity yalipowekwa. (Utabiri wangu ulikuwa −0.022; mwelekeo
sahihi, ukubwa umekosea kwa 0.013.)

Upande wa kuondoa unashikilia kwa nguvu: EURCHF **−0.2032**, EURGBP **−0.1795**.

**Trendiness: `eff_ratio_24h` ρ +0.545 · `adx14` ρ +0.434.**

Mwelekeo ni sahihi — vipimo vyote viwili, vikihesabiwa **bila kujua label yoyote**,
vinapanga symbols kwa mpangilio unaokaribiana na wa `R`. Nadharia haijakanushwa.

Lakini **jozi 12 si observations 12**. Sarafu 6 zinazounda jozi hizo zinatoa blocs
chache: EUR-crosses zinasogea pamoja, JPY-crosses pamoja, dollar za commodity pamoja.
Participation ratio ni **7.54**, kwa hiyo `ρ` inayohitajika kwa 5% ni **0.643** — si 0.497
ya `n = 12`.

**+0.545 < 0.643. HAIJATHIBITIKA.**

Hili ni kosa lile lile la `effective-n` — "instrument count si observation count" — likiwa
limehamia kwenye mhimili wa cross-section badala ya ule wa muda. `placebo` sasa
inalihesabu yenyewe na kuripoti kizingiti, si kuacha jicho lihukumu.

## 9. Hitimisho la T3 — kilichojulikana baada ya configs 2

**Kinachoshikilia:**

1. **EURCHF na EURGBP zinapoteza 0.12 R kila trade**, mbali kabisa na kelele, zikishikilia
   baada ya marekebisho ya symbols 12. Ndiyo ugunduzi pekee wa mradi huu unaosimama peke
   yake.
2. **Pipeline ni safi** — `shuffle` haikuonyesha uchafuzi, na uvujaji wa muda haukupatikana
   popote.
3. **Ujuzi wa wakati upo lakini ni dhaifu** — `ρ` 0.5152 ndani ya symbol, p 0.040.

**Kisichoshikilia:**

1. `ρ = 0.8182` ya hatua 3 — **sehemu kubwa ilikuwa utambuzi wa symbol**.
2. `+0.0661 R` ya decile ya juu — p 0.119, si tofauti na kelele.
3. USDJPY kama symbol ya kuchagua — FWER −0.0094.
4. Nadharia ya trendiness — mwelekeo sahihi, ushahidi pungufu (0.545 dhidi ya 0.643).

**Kilichoshindwa si model. Ni mkabala.**

Tulitumia bajeti kutafuta lift ya **+0.0751 R** kutoka kwa model, wakati:

* utofauti kati ya symbols ni **0.1959 R** — mara 2.6 ya lengo;
* msingi wa SETUP-v1 ni **−0.0163 R**, yaani model ilipaswa kwanza kulipa hasara kabla ya
  kuanza kutafuta faida;
* kizuizi cha kupima sheria yoyote ya cross-section si rows (25,314) bali **blocs (7.54)**.

Model haikuwa kizuizi siku moja. §3.9 iliahirisha upanuzi wa symbols kwa sababu `N_eff`
ilitosha — na ilitosha, **kwenye mhimili wa muda**. Mhimili unaobana ni mwingine.

### Hatua inayofuata — kipimo kimoja, bila bajeti

```
python -m src.data.cli cost-audit --cell 2.0/3.0 --symbols <zote ISIPOKUWA EURCHF,EURGBP>
```

Swali: msingi wa pool ukiondoa mbili zilizothibitika kupoteza, `ev_r_net` inakuwa nini?
Ikitoka −0.0163 kwenda karibu na sifuri, **lengo lote la T3 linabadilika** — na linabadilika
kwa kipimo, si kwa model.

**Ukiri wa lazima:** uteuzi huu umetokana na jedwali la `placebo` la 2026-08-14. Ni uteuzi
juu ya label, umefanywa kwa macho wazi, na umewekwa hapa ili usije ukasahaulika.
`cost-audit` ni **kipimo**, si tathmini ya strategy, kwa hiyo haigharimu config — lakini
kutumia matokeo yake kuchagua strategy kutagharimu.

#### MATOKEO — 2026-08-14 · symbols 10 (bila EURCHF, EURGBP)

| | symbols 12 | **symbols 10** |
|---|---|---|
| `ev_r_net` (cell 2.0/3.0) | −0.0163 | **+0.0039** |
| `cost_R` | 0.0294 | 0.0271 |
| `n_max`/mwaka | 142 | 166 |
| hadi breakeven | +0.0065 | **−0.0016** |
| δ_MER | 0.0235 | 0.0217 |
| **LIFT INAYOHITAJIKA** | **0.0300** p_tp | **0.0202** p_tp |
| …kwa `R` | +0.0751 R | **+0.0505 R** |

**Kuondoa symbols mbili kumeshusha bar kwa theluthi, na kumepeleka pool ng'ambo ya
breakeven** (`hadi breakeven` sasa ni **hasi**). Cell iliyosainiwa 2.0/3.0 inabaki
pekee yenye `EV net` chanya kwenye grid nzima — haijachaguliwa upya.

#### Onyo mbili, na ya pili ni kubwa

**1. `+0.0039` haina CI.** `cost-audit` ilikuwa ikiripoti `ev_r_net` kama nukta tupu.
Imeongezwa sasa (block bootstrap ya miaka, 90%). Utabiri wangu: **mpaka wa chini uko chini
ya sifuri**, kwa hiyo pool haitathibitika kulipa — bado ni bora zaidi ya ilivyokuwa.

**2. Mabadiliko mawili yanapingana.** Kuondoa symbols mbili kali kunashusha bar **na
kunashusha lift ya model kwa wakati mmoja** — kwa sababu sehemu kubwa ya lift ya hatua 3
(`ρ` kutoka 0.8182 hadi 0.5152 baada ya kuondoa base rate za symbols) **ilikuwa utambuzi
wa symbol**. Extremes zikiondoka, chakula cha model kinaondoka nacho.

Kwa hiyo: bar imeshuka kutoka 0.0300 hadi 0.0202, lakini lift ya model itashuka pia kutoka
0.0248 kwenda karibu na mabaki dhaifu ya ndani ya symbol. **Faida halisi inaweza kuwa
sifuri.** Kudai vinginevyo ni kuchukua faida ya mabadiliko moja huku ukipuuza la pili.

### Provenance — dosari iliyorekebishwa 2026-08-14

`cost-audit --symbols <subset>` ilikuwa ikiandika juu ya `cost_audit.json`, ushahidi ule ule
uliotajwa na **sahihi #19**. Populations mbili tofauti, jina moja. Sasa subset inaandika
`cost_audit_<n>sym_<sha8>.json`, na orodha ya symbols inaingia **ndani ya faili** — jina
linaweza kunakiliwa, yaliyomo hayawezi.

Faili la awali linarudishwa kwa `git checkout -- research/reports/r1/cost_audit.json`.



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
