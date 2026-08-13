# Mapitio ya nje — MTAALAMU WA 2

**Tarehe:** 2026-08-13 · **Duru:** 4 (jibu la kwanza + G1–G6 + H1–H4 + I1–I2)
**Hadhi:** imeandikwa **kabla** mtaalamu wa 3 hajajibu. Hakuna neno litakalohaririwa baadaye.

> Aliona brief ile ile, bila kuona chochote cha mtaalamu wa 1.

---

## 1. Safari ya jibu lake — marekebisho matatu

Hii ndiyo sehemu muhimu kuliko hitimisho lenyewe. Alishikilia msimamo, akapingwa kwa
hesabu, akakubali, na kila mara **akaweka hoja yenye nguvu zaidi** mahali pa iliyoanguka.

| Duru | Alichodai | Kilichotokea |
|---|---|---|
| 1 | wide-stop corner ndipo tail risk inapoishi | **Imeanguka.** `R_stop = −(1 + overshoot/sl_pips)` — gap ile ile inagharimu **kidogo** kwa R kadiri stop inavyopanuka. "Hoja hiyo si iliyorekebishwa — imepotea." |
| 2 | effect ni undetectable (0.64 SE); acha | **Namba ilikuwa mbaya mara 5.** Alitumia 2,060 (blocks za muda kwa symbol MOJA) kama observations huru. Sahihi ≈ 10,300. Pia alitumia formula ya two-sample badala ya one-sample. |
| 3 | δ_MER, si breakeven | **Imesimama** — na ndiyo hoja bora kuliko zote tulizosikia |
| 4 | n = 300/mwaka | **Alikiri ni ya hisia.** Cost identity inatoa n_max = 253 kwa κ = 0.50. "300 niliyoichagua kwa hisia ni bahati." |

---

## 2. Hoja yake ya msingi — kupima kile kisichofaa kutradiwa

Kupima kwa usahihi wa `δ = 0.007` ni kujenga jaribio ambalo, **likifaulu kabisa**, linarudisha:

| | |
|---|---|
| EV kwa trade | 0.014 R |
| Return ya mwaka (n=300, hatari 1%) | 4.2% |
| sd ya mwaka | 17.3% |
| **Sharpe** | **0.24** |
| Config budget kwa MinBTL | **1.3** — huwezi kutafuta hata mara moja |

> *"Mnajenga miundombinu ya kupima kwa usahihi kitu ambacho, kikithibitishwa, hakina thamani."*

**Geuza estimand:** usipower kwa breakeven, power kwa **tradability**.

---

## 3. Identities mbili zinazoamua kila kitu

### 3.1 Kitakwimu

$$\delta = \frac{SR^*}{2\sqrt{n}} \qquad\Longrightarrow\qquad N_{req} = \frac{7.84\,n}{SR^{*2}} = 16n \;\;(SR^*=0.7)$$

> *"Frequency ya juu inagawanya edge kwa trades nyingi, kila moja ikihitaji δ ndogo, na δ ndogo
> inahitaji data zaidi. **Frequency inanunuliwa kwa sample size.**"*

### 3.2 Kiuchumi — hii ndiyo inayobana kwanza

Cost inakua kama `n`; return target inakua kama `√n`. Kwa hiyo `cost/return ∝ √n`.

| n/mwaka | cost drag | net target (SR 0.7) | gross | cost/net |
|---|---|---|---|---|
| 300 | 6.6% | 12.1% | 18.7% | 55% |
| 644 | 14.2% | 17.8% | 32.0% | 80% |
| 1,250 | 27.5% | 24.8% | 52.3% | **111%** |
| 3,076 | 67.7% | 38.8% | 106.5% | **175%** |

$$\sqrt{n} \le \frac{\kappa \cdot SR^*}{cost_R} \qquad (\kappa = \text{cost drag kama sehemu ya net target})$$

| κ | n_max |
|---|---|
| 0.40 | 162 |
| **0.50** | **253** |
| 0.55 | 306 |
| 0.60 | 365 |

**Vyote vinahesabika kwa cost model na SR\* pekee — sifuri outcome data.**

> *"Capacity 1,250 haiingii kabisa: cost drag inazidi net target. **Capacity si kikomo hapa; ni
> kishawishi.**"*

---

## 4. Vigezo vinavyoweza kusainiwa LEO

| Kigezo | Thamani | Chanzo |
|---|---|---|
| `SR*` | **0.7** net, annualized, holdout | nukta pekee ambapo vikwazo 3 vinakubaliana |
| `κ` | **0.50** | uamuzi wa PD; inatoa n_max |
| `n_max` | **253/mwaka** | `√n ≤ κ·SR*/cost_R` |
| `δ_MER` | **0.022** juu ya breakeven | `SR*/(2√n)` |
| `N_req` | **~4,050** | `1.96/δ²` |
| Config budget | **7**, mradi mzima, hairudishwi | `exp(SR*²·T/2)`, T=8.25 |
| Sub-allocation | 3 meta-labelling · 2 cross-sectional · 2 akiba | iliyotangazwa, si reset |

**Muhimu:** asaini **identity**, si namba. `n_max = N_eff_measured/(7.84/SR*²)`, ikihesabiwa
baada ya N_eff kupimwa, kisha kufungwa. *"Identity inajirekebisha; namba haijirekebishi."*

### Kwa nini n_max iwe constraint, si tokeo

> *"Ukiruhusu model ichague frequency baada ya kuona data, umeiruhusu **ichague effect size
> inayotakiwa kuidhihirisha**. Hiyo ni selection kwenye estimand yenyewe — aina isiyoonekana
> kwenye multiple-testing count na isiyoshikwa na purged CV."*

Model ikitaka kutrade zaidi ya n_max: **usiibadilishe, isome.** EV chanya kwenye trades nyingi
kuliko n_max inamaanisha edge ni **pana na nyembamba** — profile inayokufa kwa gharama.
Inayohitajika ni kinyume: **nyembamba na kina**.

---

## 5. Config budget — utekelezaji

| Kanuni | |
|---|---|
| Counter | mradi mzima, ngumu, **hairudishwi** — per-phase reset ni loophole inayofanya utaratibu uwe mapambo |
| Decrement | kwenye **evaluation dhidi ya labels**, si kwenye code iliyoandikwa. *"Kufikiri ni bure; kugusa outcome data ni gharama."* |
| Correlated configs | kwa **cluster weight** (ONC) — cells 25 za grid ni clusters 2–3 (narrow/mid/wide), zinadecrement 2–3 si 25 |
| Msamaha | replication ya effect iliyochapishwa **haidecrement**, kwa sharti itangazwe kama data-validation na matokeo yake **hayaruhusiwi** kutumika kwa strategy selection. Msamaha wenyewe unasainiwa |
| Bure | sweep yetu ya trigger (rate pekee, kabla ya labels) — *"ndiyo mfano wa jinsi mechanism inavyopaswa kufanya kazi"* |
| Ikifika sifuri | CI gate inakataa evaluation yoyote mpya. Mradi unaisha kwa jibu ulilokuwa nalo |

> *"Hiyo ndiyo dawa pekee ya kiufundi kwa selection leakage mliyoikiri haina detector."*

**Kwa nini SR\* = 0.7 na si nyingine:** 1.0 inatoa budget ya 62 — *"ni budget kubwa kwa sababu
ni ahadi kubwa"*, na mtajaribiwa kuifikia kwa kutafuta. 0.5 inatoa budget ya 3 — mradi
hauwezi kutekelezwa; *"hitimisho la uaminifu si kusaini 0.5, ni kutokufanya mradi."*
Saini pamoja na dokezo: **kama edge halisi ni 0.5, tunakubali hatutaiona.**

---

## 6. Nini cha kufanya kwa data tuliyonayo — na kisichohitajika

**Pendekezo letu la §8 limeahirishwa kabisa.**

> *"Kama edge ya 0.020 ipo, mtaiona kwenye data mliyonayo. Kama haipo, hakuna kiasi cha historia
> kitakachoifanya iwe faida — kitawapa tu **usahihi zaidi juu ya sifuri**."*

| L4 iliyopo | Kazi |
|---|---|
| Setups 25,374 | **kufundishia meta-labelling LEO** — hakuna label mpya inayohitajika |
| Cells 1,308,025 | calibration ya barrier/EV heads |
| Control 27,089 | kazi imekwisha (+0.0251 imeshapimwa) |
| Tick-exact cells | validation set ya two-level resolver |

> *"Dense set ni **superset**. Points 25,374 zinabaki ndani ya 588,000 kama subsample yenye
> `setup_v1_flag = 1`. Rebuild haitupi chochote — inaahirisha tu."*

---

## 7. H2 — operating point haipimiki, kwa hiyo isipimwe

Top-1% ya 10,300 = obs ~103, SE = 0.049. *"Hakuna dataset ya ukubwa wa kuridhisha itakayobadilisha
hilo — top-1% daima ni 1% ya chochote ulicho nacho."*

| | Marekebisho |
|---|---|
| (a) | **Ondoa kizingiti** — allocation iwe endelevu kama function ya EV. RCE tayari inafanya sizing; ipeni EV inayoendelea badala ya bendera |
| (b) | Pima **mtiririko kwenye deciles zote 10** (n≈1,030 kila moja), si nukta ya juu |
| (c) | Top-decile kama **fitted value** kutoka curve nzima, si empirical mean ya obs 103 |
| (d) | Kwa cross-sectional: pima **IC**, kisha geuza kwa fundamental law |
| (e) | CI kwenye **strategy** kupitia block bootstrap ya pipeline nzima |

---

## 8. Kigezo cha meta-labelling — kama kinavyopaswa kusainiwa

**Muundo:** setups 25,374 · purged 5-fold, embargo 36 · XGBoost **moja**, hyperparameters
zimefungwa kwenye ledger kabla ya run · cell **moja** iliyofungwa mapema (2.0/2.0) · baseline =
SETUP-v1 take-everything (p_tp 0.505) · **hatua ya sifuri: pima N_eff kabla ya kuangalia
matokeo**.

> Kuchagua 2.0/2.0 baada ya kuona EV table **ni selection on the label** — irekodiwe kama
> registered rule mpya pamoja na ukiri huo, si kama chaguo lisilo na gharama.

**Kufaulu kunahitaji vyote vitatu:**

1. **Calibration** — reliability slope ∈ [0.8, 1.2], Spiegelhalter/HL p > 0.05
2. **Discrimination** — Spearman ρ ≥ 0.7 kwenye deciles 10, trend p < 0.01
3. **Kiuchumi** — fitted top-decile p̂ ≥ **0.532**, na 5th percentile ya block-bootstrap > 0.512

**Vipimo visivyoruhusiwa kutangaza mafanikio:** AUC · accuracy · log-loss · in-fold · cell
nyingine yoyote · "ilikaribia".

**Vifungu vitatu vya ulinzi:**

| Kifungu | |
|---|---|
| Kutotinker | run **moja**. Ikianguka, budget inapungua 1, na rule inayofuata lazima ibadilishe kitu cha **kimuundo** — si hyperparameters |
| Nguvu | N_eff ikipimwa **chini ya N_req**, jaribio ni **inconclusive** bila kujali matokeo |
| Kufikika | **null simulation kabla ya run** — permute outcomes ndani ya time blocks, endesha pipeline, angalia kama kigezo kinaweza kufikika kabisa. Kisipofikika, badilisha **design**, si threshold |

### Kosa la hesabu alilolikubali (I2)

Kigezo cha 3 hakikufunga: `0.532 − 1.645(0.0156) = 0.5063 < 0.512`. Jibu si kupandisha
threshold hadi 0.538 — *"ungekuwa umepandisha SR\* kutoka 0.7 hadi 0.90 kupitia mlango wa nyuma
wa kitakwimu"* — wala kushusha CI hadi 80% — *"ndiyo ufafanuzi wa kuhamisha goalposts."*

> **"Uchumi unaweka threshold; takwimu inaweka evidence standard."**

Jibu ni SE ya **fitted value** (≈0.008–0.010, si 0.0156), ikihesabiwa kwa **block bootstrap ya
pipeline nzima**, si kwa formula. Na masharti mawili yanayoifanya iwe halali:

- **Logistic, si isotonic** — isainiwe. Top bin ya isotonic **ni** empirical top-bin mean;
  inarudisha SE ya 0.0156 na hainunui chochote. Faida yote inatokana na parametric pooling ya
  parameters mbili kwenye 10,300 zote.
- **Goodness-of-fit gate** — fitted ikaribiane na empirical ndani ya 1 SE kwenye deciles mbili za
  juu. Ikizidi, njia ya parametric **inakataliwa kwa run hiyo** na kigezo kinaanguka.
  *"Bila kifungu hiki, (c) ni njia ya kununua CI nyembamba kwa kudai kitu ambacho hukukipima."*

---

## 9. Onyo lake juu ya 10,300 yenyewe

Ni **upper bound iliyokadiriwa, si iliyopimwa**. Factor 5 inadhania setups katika symbols
zinajitegemea. Lakini momentum triggers **zina cluster kwa muda** — USD impulse moja inawasha
setups kwenye USD pairs kadhaa ndani ya masaa machache; wakati huo effective factors ni chini
ya 5. Ikiwa 3: N_eff ≈ 6,200.

**Ipime kwanza kabla ya kila kitu kingine** — siku 2–3, average uniqueness kwenye concurrency
matrix iliyounganishwa cross-symbol.

---

## 10. G6 — alikiri namba zake

Sharpe "0.78 dhidi ya 1.74" kwa HMM filtered/smoothed: *"si zangu, si peer-reviewed. Zitupilie
mbali kama ushahidi."* Mechanism inabaki sahihi.

**Protocol ya matoleo matatu:**

| | Chanzo cha state probability |
|---|---|
| **A1 — halisi** | parameters zinafit walk-forward, filtered probabilities hadi t pekee |
| **A2 — leak fiche** | filtered probabilities, lakini **parameters zilifit kwenye full sample** |
| **B — leak wazi** | smoothed / Viterbi kwenye full sample |

> **A2 − A1 ndiyo ya kuvutia zaidi kwenu**: *"sentinel yenu inaangalia as-of rules kwenye features,
> na **parameter fitting ya HMM haionekani kama feature**."*

Hilo ni **shimo halisi kwenye kinga zetu**.

---

## 11. Mahali ninapotofautiana naye, na kilichobaki wazi

**1. `cost_R = 0.022` haijumuishi stop overshoot — na hilo linaweza kuvunja kila kitu.**
Identity yote ya kiuchumi (§3.2) inategemea `cost_R`. Amehesabu commission pekee (0.7 pips).
Lakini tumepima `touch_past_pips`: p50 0.12 · p90 1.06 · p99 14.59 · max 2,503.7 — mkia mzito.

Ikiwa wastani wa overshoot ni pips 1–2 kwenye `sl_pips` 32, na inaathiri ~50% ya trades
(zinazogongwa SL), gharama ya ziada ni **0.015–0.03 R** — **kubwa kama commission yenyewe au
zaidi.** Kwa `cost_R = 0.045`:

$$\sqrt{n} \le \frac{0.50 \times 0.7}{0.045} = 7.8 \quad\Longrightarrow\quad n_{max} \approx \mathbf{61}$$

**n_max ingeshuka kutoka 253 hadi ~61 kwa mwaka.** Hiyo ni tofauti kati ya mfumo na jaribio.

Namba hii **inahesabika leo**, kwa kusoma barriers parquet — hakuna rebuild, hakuna kugusa
ushahidi uliosainiwa. **Lazima ipimwe kabla κ na n_max hazijasainiwa.**

**2. n_max = 253 inamaanisha kutrade 8% ya setups** (253 kati ya 3,076/mwaka) — yaani **0.36% ya
bars zote**. Je kuna heterogeneity ya kutosha ndani ya setups kwa model kupata lift ya 0.022
kwenye 8% ya juu? Hilo ndilo jaribio lenyewe, lakini ni bar ya juu kuliko inavyoonekana.
