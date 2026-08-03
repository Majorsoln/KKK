# ELITEFX — MPANGO WA UTAFITI R0 — kupima kila eneo, kuanzia DATA (PD 2026-08-03)

> **Hadhi:** mpango rasmi wa mzunguko wa kwanza wa utafiti. Unafuata `DATA_FEATURE_STANDARD.md`
> (data/features) na `KAIROS_1_STANDARD.md` (models). Utekelezaji unafanyika **nje ya repo hii**;
> kinachorudi hapa ni **namba zilizothibitishwa + models**, si code ya utafiti.

---

## 0. FALSAFA — PIMA KABLA YA KUJENGA

Tatizo la kawaida la mifumo ya trading ni kujenga models kumi kisha kujiuliza kwa nini haifanyi
kazi — kwa sababu **hujui eneo lipi lilishindwa**. Mpango huu unabadilisha mpangilio:

```
Kila eneo linapimwa PEKE YAKE, kwa kizingiti kilichoandikwa KABLA,
kabla eneo linalofuata halijaanza.
```

Kila awamu ina vitu vinne: **swali · kipimo · kizingiti · hatua ikifeli.** Hakuna awamu
inayoendelea kwa matumaini. Awamu isiyofaulu inatoa **LESSON** — na LESSON ni **jibu**, si
kushindwa (§6 ya KAIROS-1).

**Sheria ya HOLDOUT:** haifunguliwi hadi R8. Awamu R0–R7 zote zinatumia TRAIN/VALIDATION pekee.
Ikifunguliwa mapema, mzunguko mzima unakuwa batili — hakuna njia ya kuurekebisha.

---

## 1. RAMANI YA AWAMU

```
R0 DATA AUDIT ──► R1 LABEL AUDIT ──► R2 FEATURE SCREENING ──► R3 REDUNDANCY
                                                                    │
R8 HOLDOUT ◄── R7 ABLATION ◄── R6 FILL-AWARE EV ◄── R5 CALIBRATION ◄┴─ R4 BASELINE
```
Mishale ni **ngumu**: R2 haianzi kabla R1 haijafaulu. Sababu — IC ya feature dhidi ya label
mbovu ni namba isiyo na maana.

| Awamu | Swali kuu | Deliverable |
|---|---|---|
| **R0** | Data yetu ni safi kiasi gani? | `quality_report.json` + kalenda ya sessions |
| **R1** | Labels zetu zina maana? | curve ya utulivu wa label + base rates |
| **R2** | Feature ipi ina taarifa? | jedwali la IC/MI + utulivu wa muda |
| **R3** | Features zipi zinarudia nyingine? | clusters + wawakilishi waliochaguliwa |
| **R4** | Baseline ni ipi? | EV_R ya baseline (bar ya kushinda) |
| **R5** | Probabilities zetu ni za kweli? | reliability curve + Brier skill |
| **R6** | Edge inabaki baada ya gharama na cap? | EV_R net, fill-aware |
| **R7** | Kila familia inalipa kiasi gani? | jedwali la ablation |
| **R8** | Je inashikilia kwa data isiyoonekana? | attestation ya mwisho |

---

## 2. AWAMU KWA AWAMU

### R0 — DATA AUDIT
**Swali:** je data ya broker inatosha kujenga chochote?

| Kipimo | Kizingiti |
|---|---|
| coverage kwa symbol/mwaka | ≥ `min_coverage` (0.995) |
| partitions zilizofeli §3 ya standard | 0 zinazoingia L2 |
| gaps ndani ya session | ≤ `max_gap_bars` |
| ukamilifu wa bid **na** ask | 100% ya bars zinazotumika |
| miaka inayotumika | ≥ `min_years` (5) |

**Deliverable:** `quality_report.json` kwa kila symbol/mwaka + kalenda ya sessions
iliyothibitishwa kwa data (si kudhaniwa).

**Ikifeli:** (a) omba data ndefu/safi kwa broker, au (b) punguza symbols hadi zenye ubora, na
**rekodi** kwamba wigo umepungua. Kamwe usiendelee na partition iliyofeli "kwa sababu ni ndogo".

---

### R1 — LABEL AUDIT
**Swali:** je label inapima kile tunachodhani inapima, na ipo ya kutosha?

| Kipimo | Kizingiti |
|---|---|
| labels za L-B kwa kila kisanduku cha grid | ≥ `min_labels_per_cell` (200) |
| base rate ya `p_tp_first` | inalingana na jiometri (tp/sl) ± kiasi kinachoelezeka |
| utulivu wa base rate kwa miaka | hakuna mwaka nje ya ±2σ bila maelezo |
| M1-vs-H1 disagreement | asilimia ya labels zinazobadilika ikitumika OHLC ya H1 **iripotiwe** |
| timeout share | ≤ `max_timeout_frac` (0.35) |

**Kipimo cha msingi (sanity ya jiometri):** kwa random walk, `p_tp_first ≈ sl ÷ (sl + tp)`. Labels
zetu zikitofautiana **sana** na hii bila sababu, kuna hitilafu ya path au ya barrier.

**Deliverable:** curve ya utulivu (label dhidi ya horizon na upana wa barrier) — inaonyesha kama
label ni imara au ni artifact ya kigezo kimoja.

**Ikifeli:** rekebisha horizon/grid **kabla** ya features. Label mbovu inaharibu kila awamu
inayofuata.

---

### R2 — FEATURE SCREENING (univariate)
**Swali:** feature ipi ina taarifa halisi kuhusu label?

Kila feature inapimwa **ndani ya purged folds**, si in-sample:

| Kipimo | Maana | Kizingiti |
|---|---|---|
| `IC` (Spearman) | uhusiano wa cheo na label | \|IC\| ≥ `ic_min` (0.02) |
| `IC_stability` | sehemu ya folds zenye ishara ile ile | ≥ `ic_sign_stability` (0.60) |
| `MI` | uhusiano usio-linear | > 0 kwa uhakika dhidi ya permutation |
| `rolling IC` | je inaharibika kwa muda? | hakuna kuporomoka kwa kudumu |
| `autocorr` | feature inabadilika au ni tuli? | ndani ya mipaka ya familia |
| `coverage` | asilimia ya decision points zenye thamani halali | ≥ 0.95 |

**Permutation baseline ni ya lazima:** kila feature inalinganishwa na toleo lake lililochanganywa.
Feature isiyoshinda toleo lake la bahati nasibu **haipo**.

**Deliverable:** jedwali la features zote na hadhi `candidate → screened | LESSON`.

**Ikifeli familia nzima:** familia inatupwa kwa mzunguko huu na **sababu** inaandikwa. Familia ya
F2 (structure) ndiyo yenye hatari kubwa hapa — patterns nyingi ni hadithi, si taarifa.

---

### R3 — REDUNDANCY
**Swali:** tunabeba features ngapi zinazosema kitu kile kile?

```
1. Correlation matrix ya features zilizopita R2
2. Hierarchical clustering kwa distance = 1 − |ρ|
3. Kata kwenye |ρ| ≥ corr_cluster (0.80)
4. Kwa kila cluster: chagua mwakilishi MMOJA — yule mwenye IC_stability kubwa,
   ikilingana, yule wa bei ndogo ya kuhesabu
```
**Kizingiti:** feature set ya mwisho ≤ bajeti ya §0.1 ya standard (`labels ÷ 50`).

**Deliverable:** dendrogram + orodha ya wawakilishi + orodha ya zilizoondolewa na sababu.

**Kwa nini si PCA:** components hazina feature card, hazina hypothesis, na haziwezi kuelezwa
zikishindwa live. Tunachagua features halisi.

---

### R4 — BASELINE
**Swali:** bar ipi models kubwa lazima zishinde?

Baseline tatu, kila moja rahisi kimakusudi:
```
B0  bahati nasibu / base rate           — sakafu kabisa
B1  logistic regression kwenye features 5 bora za R2
B2  GBM ndogo (depth 3, trees 200) kwenye set ya R3
```
**Kizingiti:** B1 au B2 lazima izidi B0 kwa `EV_R` kwa uhakika (purged CV, CI isiyogusa sifuri).

**Ikifeli:** **SIMAMA.** Kama model rahisi haiwezi kuvuta chochote kutoka features zilizochujwa,
Transformer/PPO hazitasaidia — zitakariri kelele. Rudi R1/R2. Hii ndiyo awamu inayookoa miezi.

**Umuhimu wa kudumu:** `EV_R` ya B2 ndicho **kizingiti cha kupokelewa** cha §6 ya KAIROS-1. Model
yoyote kubwa isiyoishinda haiingii.

---

### R5 — CALIBRATION
**Swali:** "zilizopewa 70%, je zilishinda 70%?"

| Kipimo | Kizingiti |
|---|---|
| Brier **skill** score dhidi ya base rate | > 0 |
| ECE (expected calibration error) | ≤ `ece_max` (0.05) |
| reliability curve | monotonic, hakuna bucket iliyopotoka sana |
| calibration kwa symbol na kwa session | haiporomoki kwenye kundi lolote |

Isotonic au Platt inaruhusiwa — **ikijifunza kwenye validation fold pekee**, na ikihesabiwa kama
sehemu ya model (inasafiri nayo kwenda live).

**Kizingiti kigumu (§5.3 ya KAIROS-1):** probability isiyo-calibrated **hairuhusiwi** kulisha EV
wala sizing. Bila hii, lango la EV ni pambo.

---

### R6 — FILL-AWARE EV
**Swali:** edge inabaki baada ya gharama halisi na cap ya slippage?

```
EV_signal   kutoka p_tp_first (R5, calibrated) + SL/TP
cost_pips   kutoka RCE (§3 ya RISK_COST_ENGINE) — spread_effective + slip cap + comm + swap
P(fill)     kutoka L-C (§5.3 ya standard)
EV_final    = P(fill) × EV_signal                      ← S5: hakuna opportunity cost
EV_R        = EV_final ÷ SL
```
Trades zisizojaza ndani ya cap **hazihesabiwi kama trades** (§5.5 ya KAIROS-1).

| Kipimo | Kizingiti |
|---|---|
| `EV_R` net | > baseline ya R4 |
| `fill_rate` uliokadiriwa | ≥ `fill_rate_min` (0.60, config/risk.yaml) |
| unyeti kwa cost | EV_R inabaki chanya kwa cost × 1.5 |

**Mtihani wa cost × 1.5 ni wa makusudi:** broker akibadilika au spread ikipanda, edge ambayo
inakufa kwa 50% ya ongezeko la gharama si edge — ni bahati.

---

### R7 — ABLATION (hapa ndipo "kila eneo linapimwa")
**Swali:** kila familia ya features inachangia kiasi gani hasa?

```
Kwa kila familia F1..F7:
    ondoa familia nzima  →  funza upya  →  pima ΔEV_R (purged CV)
```
| Matokeo | Tafsiri | Hatua |
|---|---|---|
| ΔEV_R kubwa hasi | familia ni muhimu | inabaki |
| ΔEV_R ≈ 0 | familia inarudia nyingine | **ondoa** — inapunguza gharama ya data na over-fit |
| ΔEV_R chanya | familia inaumiza | ondoa, andika LESSON |

**Deliverable:** jedwali la ablation — hii ndiyo ramani ya thamani ya mfumo mzima. Inajibu
"tunahitaji TF saba kweli?" kwa namba, si kwa maoni.

**Ablation ya TF pia:** ondoa TF moja kwa wakati. Kama D1 haichangii, mzigo wa data unapungua.

---

### R8 — HOLDOUT + ATTESTATION
**Mara moja.** Mchanganyiko wa mwisho pekee. Vigezo vimeandikwa **kabla**:
```
EV_R (net, fill-aware) > baseline ya R4
calibration inashikilia kwenye holdout (ECE ≤ ece_max)
fill_rate ≥ fill_rate_min
tofauti ya EV_R kati ya validation na holdout ≤ degradation_max
```
**Deliverable — ATTESTATION:** `dataset_id` · config hash · feature set · vigezo
vilivyotangazwa kabla · namba zilizopatikana · PASS/LESSON. Hii ndiyo pekee inayosafiri kwenda
engine (sheria 2 ya README).

**Ikifeli:** mzunguko unaisha kama **LESSON**. Hakuna "jaribu tena kwenye holdout" — holdout
iliyoonekana imekufa; mzunguko ujao unahitaji data mpya au split mpya.

---

## 3. VIZUIZI VINAVYOJIRUDIA (kila awamu)

1. **Pre-registration:** vigezo vinaandikwa kabla ya kukimbiza. Kubadilisha kizingiti baada ya
   kuona namba = kufuta awamu.
2. **Purged CV kila mahali** — hata kwenye screening ya univariate.
3. **Sentinel ya uvujaji** (§4.2 ya standard) inakimbia kwa kila build.
4. **`dataset_id` kwenye kila namba.**
5. **LESSON inaandikwa kwa undani sawa na PASS.** Familia iliyofeli inasaidia mzunguko ujao tu
   kama sababu imeandikwa.

---

## 4. MFUATANO WA KAZI (nini kifanyike kwanza)

| Hatua | Kazi | Inategemea |
|---|---|---|
| 1 | Vuta M1 bid+ask, jenga L0 + hashes | — |
| 2 | Jenga L1 + `quality_report.json` (**R0**) | 1 |
| 3 | Jenga L2 (TF 7 + spread stats) + sentinel ya uvujaji | 2 |
| 4 | Jenga L-B grid labels kwa path ya M1 (**R1**) | 3 |
| 5 | Andika feature cards za familia F1–F7 (kabla ya code) | — |
| 6 | Jenga L3 + screening (**R2**) → **R3** | 4, 5 |
| 7 | Baselines (**R4**) — **lango la GO/NO-GO** | 6 |
| 8 | R5 → R6 → R7 | 7 |
| 9 | R8 + attestation → kabidhi kwa engine | 8 |

Hatua 5 inaweza kwenda sambamba na 1–4 (ni kuandika, si kuhesabu). Zingine ni mfululizo.

---

## 5. NJE YA WIGO
- Utekelezaji wa engine (sizing, gate, execution) → `RISK_COST_ENGINE.md`
- Muundo wa models na standards tano → `KAIROS_1_STANDARD.md`
- OPM / RL ya positions zilizo wazi — **si sehemu ya R0.** Inahitaji fills halisi, ambazo
  hazipo hadi live ianze.
