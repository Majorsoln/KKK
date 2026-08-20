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
      │                                                             │
      └─► P PRETRAINING (sambamba na R1–R3; TRAIN+VAL PEKEE) ──┐    │
                                                               ▼    │
R9 LIVE ◄── R8 HOLDOUT ◄── R7 ABLATION ◄── R6 EV ◄── R5 CALIB ◄┴─ R4 BASELINE
```
Mishale ni **ngumu**: R2 haianzi kabla R1 haijafaulu. Sababu — IC ya feature dhidi ya label
mbovu ni namba isiyo na maana. Track P (pretraining, §5A ya KAIROS-1) haiitaji labels za trade,
kwa hiyo inakwenda sambamba — lakini models zake zinaingia R4+ kwa lango lile lile.

| Awamu | Swali kuu | Deliverable |
|---|---|---|
| **R0** | Data yetu ni safi kiasi gani? | `quality_report.json` + kalenda ya sessions + schema moja |
| **R1** | Labels zetu zina maana? | curve ya utulivu wa label + base rates |
| **R2** | Feature ipi ina taarifa? | jedwali la IC/MI + utulivu wa muda (FDR-corrected) |
| **R3** | Features zipi zinarudia nyingine? | clusters + wawakilishi waliochaguliwa |
| **P** | Encoder inajifunza soko bila trade labels? | pretrained encoder + ripoti ya malengo |
| **R4** | Baseline ni ipi? | EV_R ya baseline (bar ya kushinda) |
| **R5** | Probabilities zetu ni za kweli? | reliability curve + Brier skill |
| **R6** | Edge inabaki baada ya gharama na cap? | EV_R net, fill-aware, madarasa 3 |
| **R7** | Kila familia inalipa kiasi gani? | jedwali la ablation |
| **R8** | Je inashikilia kwa data isiyoonekana? | attestation ya mwisho |
| **R9** | Je inaendelea kuwa hai baada ya deployment? | vigezo vya kustaafu + ratiba ya re-attestation |

---

## 2. AWAMU KWA AWAMU

### R0 — DATA AUDIT
**Swali:** je data tuliyonayo (ticks 2016–2026, symbols 12, matoleo 2 ya schema) inatosha
kujenga chochote?

| Kipimo | Kizingiti | Kinapimwa na (T1) |
|---|---|---|
| coverage kwa symbol/mwaka | ≥ `min_coverage` (0.95 — PD 2026-08-09; ilikuwa 0.995) | `check-l1` → `quality_report.json` (`by_symbol_year`) |
| partitions zilizofeli §3 ya standard | 0 zinazoingia L2 | `check-l1` (`fail_action: exclude`) |
| gaps ndani ya session | L0: ≤ `max_gap_seconds` · L2: ≤ `max_gap_bars` | `check-l1` · `build-l2` (`bars.check_bar_gaps`) |
| ukamilifu wa bid **na** ask | 100% ya bars zinazotumika | `check-l1` check 5 (`crossed`/`zero_spread`/`bei<=0` kando) |
| miaka inayotumika | ≥ `min_years` (10) | `quality_report.json` → `coverage_by_symbol.*.meets_min_years` |
| **normalization ya Toleo A/B** (§2.1 ya standard) | schema moja; Toleo B inapita checks zote | `compare-variants` → `canonical_schema_identical` |
| **ulinganisho A↔B** (spread/sessions kwenye pair zinazofanana) | tofauti zinaelezeka | `compare-variants` + `calendar_vs_assumed.json` → `by_variant` |
| **ulinganisho aggregator↔broker** kwa siku 4 zinazopishana (2026-04-27 … 04-30) | spread/ticks zinalingana kwa kiasi kinachoelezeka — kama hazilingani, provenance ya gharama si moja | `compare-provenance` → `provenance_comparison.json` |
| **vizingiti vyenyewe** | vinatoka kwenye mgawanyo wa data, si mezani | `quality-stats` → `threshold_study.json` |

**Kazi mbili za ziada za R0 (PD 2026-08-04):**
1. **Kurekodi feed ya broker wa live/demo kuanzia sasa** (§2.2 ya standard — provenance).
   Hii inaanza R0 na haiishii kamwe.
2. Kalenda ya sessions inathibitishwa kwa matoleo yote mawili ya schema tofauti-tofauti
   (dalili za chanzo tofauti kwa EURCHF/GBPJPY/XAUUSD).

**Deliverable:** `quality_report.json` kwa kila symbol/mwaka + kalenda ya sessions
iliyothibitishwa kwa data (si kudhaniwa) + schema moja ya kawaida L1.

Faili zote zinaandikwa `research/reports/quality/` na `scripts\audit.bat` (SETUP §3.1):
`session_calendar.json` · `calendar_vs_assumed.json` · `quality_report.json` ·
`threshold_study.json` · `variant_comparison.json` · `provenance_comparison.json` ·
`splits.json`.

**Ikifeli:** (a) omba data ndefu/safi kwa broker, au (b) punguza symbols hadi zenye ubora, na
**rekodi** kwamba wigo umepungua. Kamwe usiendelee na partition iliyofeli "kwa sababu ni ndogo".

---

### R1 — LABEL AUDIT
**Swali:** je label inapima kile tunachodhani inapima, na ipo ya kutosha?

| Kipimo | Kizingiti |
|---|---|
| labels za L-B kwa kila kisanduku cha grid | ≥ `min_labels_per_cell` (200) |
| base rate (sanity ya jiometri — fomula hapa chini) | inalingana na jiometri ± kiasi kinachoelezeka |
| utulivu wa base rate kwa miaka | hakuna mwaka nje ya ±2σ bila maelezo |
| M1-vs-H1 disagreement | asilimia ya labels zinazobadilika ikitumika OHLC ya H1 **iripotiwe** |
| timeout share | ≤ `max_timeout_frac` (0.35) |
| mzunguko wa tie-break (§5.2) | **iripotiwe**; > 1% ya labels → inapanda kwa PD |
| setup dhidi ya control sample (§4.3) | base rates zinalinganishwa — filter inayotupa trades bora kuliko inazochukua ni LESSON |
| quantiles mid vs trade-price (§5.1) | tofauti kwa XAUUSD/GBPJPY **iripotiwe** — uamuzi wa mid unapimwa kwa namba |

**Kipimo cha msingi (sanity ya jiometri, imesahihishwa PD 2026-08-07):** kwa random walk,
jiometri inatabiri `sl ÷ (sl + tp)` — lakini kwa **mshindi kati ya TP na SL**, si kwa
`p_tp_first` moja kwa moja. Kwa horizon ya bars 24, hadi 35% ya labels ni timeout — theluthi ya
matokeo imechukuliwa na darasa la tatu, kwa hiyo `p_tp_first` peke yake HAIWEZI kufikia namba ya
jiometri, na kuilinganisha nayo kungeonyesha "hitilafu" kila mara. Kinacholinganishwa ni:
```
p_tp ÷ (p_tp + p_sl)  ≈  sl ÷ (sl + tp)        ← bila timeout (conditional on resolution)
```
Kumbuka pia: barriers zinapimwa kwa bei ya trade (§5.2), kwa hiyo spread inasogeza namba hii
**chini kidogo** kwa utaratibu — tofauti ndogo ya kudumu ni spread, si hitilafu ya path.

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

**FDR control ni ya lazima (PD 2026-08-04):** permutation test inalinda feature MOJA; haitulindi
tunapopima features mia kadhaa kwa pamoja — kwa bajeti ya ~770 candidates, kizingiti cha 2σ
kinaruhusu false positives kadhaa kwa bahati tu. Kwa hiyo p-values za screening zinapita
**Benjamini–Hochberg kwa `fdr_q` (0.10)** kabla ya feature yoyote kuwa `screened`.

**Uzito na SE (imesahihishwa PD 2026-08-07):** takwimu zote za screening zinahesabiwa kwa
**decision point moja = uzito mmoja** — kamwe si kwa rows za grid (960k rows za §0.1
zinahusiana kwa makusudi; kuzihesabu kama sampuli ni kujidanganya mara 25). Na `SE ≈ 1/√N`
kwa N=38k ni ya sampuli huru — yetu si huru kwa njia MBILI: (1) labels zinapishana kwa wakati
(nafasi ya setups ~bars 20, horizon 24); (2) **symbols 12 si huru** — USD iko kwenye 7, EUR
kwenye 4, na labels za timestamp moja kwenye pairs zinazoshiriki sarafu zinahusiana. Kwa
uhusiano wa wastani ρ≈0.3 kati ya symbols, effective N ni ~9k, si 38k — `ic_min` 0.02 ni
~2σ, si 4σ kama ilivyodhaniwa awali. Kwa hiyo:
```
SE inatoka BLOCK BOOTSTRAP: blocks za muda (block_days, config) zikichukuliwa pamoja
kwa symbols ZOTE (cluster ya wakati inashika uhusiano wa symbols na wa kupishana).
Kizingiti halisi = max( ic_min , p99 ya null ya bootstrap )   ← inatoka kwenye DATA,
sheria ile ile ya §3 ya data standard: vizingiti havitoki mezani.
```
Maamuzi ya per-symbol kwa labels ~3,200 **hayafanyiki** kwa kizingiti hiki — kelele.

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
EV_signal   = p_tp×TP − p_sl×SL + p_timeout×E[R|timeout]     ← madarasa 3 (§2.1 ya KAIROS-1)
              probabilities kutoka R5 (calibrated) · E[R|timeout] kutoka timeout labels zenyewe
              ⚠ E[R|timeout] per cell ni OUT-OF-FOLD (S6, PD 2026-08-07): mean ya in-sample
                ya cell inalisha EV ile ile inayohukumu — ni stacking ndogo, sheria ile ile.
cost_pips   kutoka RCE (§3 ya RISK_COST_ENGINE) — spread_effective + slip cap + comm + swap
P(fill)     kutoka L-C (§5.3 ya standard)
EV_final    = P(fill) × EV_signal                      ← S5: hakuna opportunity cost
EV_R        = EV_final ÷ SL
```

**Ukiri wa portfolio (PD 2026-08-07):** EV hapa ni ya **kila signal peke yake**. Setups
zinafika ~kila bars 20 na horizon ni bars 24 — positions ZITAPISHANA, na bajeti ya siku ya RCE
ni yenye kikomo. Live hutachukua trades zote zilizo na label. OPM/queue inabaki nje ya wigo
(§5b ya KAIROS-1) — lakini upendeleo huu unakiriwa na **unapimwa**: R6 inaripoti *sehemu ya
signals zinazochukulika chini ya bajeti ya RCE* (simulation ya kupitisha signals kwenye budget
ya siku, kwa mpangilio wa wakati). EV ya mfumo ni ya signals zinazochukulika, si ya zote.
**Provenance ya gharama (§2.2 ya standard):** spread ya kihistoria ni ya aggregator; kwa hiyo
stress ya cost ×1.5 hapa si anasa — ndiyo bima ya pengo la aggregator↔broker hadi feed ya broker
iliyorekodiwa itoe ulinganisho halisi.
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
iliyoonekana imekufa; mzunguko ujao unahitaji data mpya (RESERVE ya 2026-05+, inayokua kila
mwezi) au split mpya.

---

### R9 — LIVE MONITORING & RE-ATTESTATION (PD 2026-08-04)
**Swali:** model iliyopasi R8 — je inaendelea kuwa hai, na tutajuaje siku imekufa?

Soko si stationary. Attestation ya R8 ni picha ya wakati mmoja; bila vigezo vya kustaafu
vilivyoandikwa KABLA, mfumo utaendelea kutrade model iliyokufa kwa sababu hakuna kipimo
kilichotangazwa cha kifo chake.

**Awamu ya SHADOW (kabla ya pesa halisi):** demo/paper kwa muda uliotangazwa; inathibitisha
mnyororo mzima (data → KAIROS → RCE → fills) na inaanza kujaza data ya broker (fills, slippage,
spread) — malighafi ya calibration ya P(fill) na ulinganisho wa provenance.

**Vigezo vya kustaafu (pre-registered, `config/data.yaml` §monitoring):**
| Kipimo | Kizingiti cha kustaafu |
|---|---|
| rolling ECE ya live (baada ya trades ≥ `min_live_trades`) | > `live_ece_mult_max` × ECE ya validation |
| EV_R halisi ya live (rolling) | < `live_ev_frac_min` × EV_R ya attestation |
| fill_rate | < `fill_rate_min` (tayari kwenye RCE — hurudi hapa kama trigger ya utafiti) |
| drift ya features (PSI kwenye features za mwakilishi) | > `psi_max` kwa kudumu |

Kikigongwa chochote → model inasimamishwa kwa entries mpya (**RCE haiguswi** — positions wazi
zinafuata sheria zake), na mzunguko mpya wa utafiti unaanza kwenye data iliyoongezeka.

**Ratiba ya re-attestation:** kila robo mwaka AU trigger yoyote hapo juu — kipi kitangulie.
Kila re-attestation inatumia RESERVE mpya kama holdout (holdout ya zamani imeshaonekana).

**Deliverable:** dashboard ya vigezo hivi + rekodi ya kila tathmini (hata "hakuna hatua").

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
| 0 | **Anza kurekodi feed ya broker** (haina mwisho) + hash L0 iliyopo | — |
| 1 | Normalization ya Toleo A/B → schema moja (L1 inasoma zote) | — |
| 2 | Jenga L1 + `quality_report.json` (**R0**) | 1 |
| 3 | Jenga L2 (TF 7 kutoka ticks + spread stats) + sentinel ya uvujaji | 2 |
| 4 | Jenga L-B grid labels kwa path ya TICKS + terminal returns za timeout (**R1**) | 3 |
| 5 | Andika feature cards za familia F1–F7 (kabla ya code) | — |
| 6 | Jenga L3 + screening na FDR (**R2**) → **R3** | 4, 5 |
| P | **Pretraining** ya encoder (TRAIN+VAL pekee, §5A ya KAIROS-1) | 3 |
| 7 | Baselines (**R4**) — **lango la GO/NO-GO** | 6 |
| 8 | R5 → R6 (EV madarasa 3) → R7 | 7 |
| 9 | R8 + attestation → kabidhi kwa engine | 8 |
| 10 | **R9**: shadow → live monitoring → re-attestation kila robo | 9 |

Hatua 0, 5 na P zinakwenda sambamba na mfululizo mkuu. Zingine ni mfululizo.

---

## 5. NJE YA WIGO
- Utekelezaji wa engine (sizing, gate, execution) → `RISK_COST_ENGINE.md`
- Muundo wa models na standards tano → `KAIROS_1_STANDARD.md`
- OPM / RL ya positions zilizo wazi — **si sehemu ya R0.** Inahitaji fills halisi, ambazo
  hazipo hadi live ianze.
