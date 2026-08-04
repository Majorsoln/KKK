# ELITEFX — MPANGO WA UTEKELEZAJI NA USIMAMIZI — TERMS + COMPLIANCE (PD 2026-08-04)

> **Hadhi:** mpango rasmi wa kutekeleza na kusimamia specs zote (`RISK_COST_ENGINE.md`,
> `KAIROS_1_STANDARD.md`, `DATA_FEATURE_STANDARD.md`, `RESEARCH_PLAN_R0.md`,
> `DATA_SPLIT_PLAN.md`). Lengo: kila logic iliyoandikwa kwenye mpango itekelezwe **100%** —
> na "100%" ithibitishwe kwa **rejista** (§3) na **milango ya CI** (§4), si kwa kumbukumbu ya mtu.

---

## 0. KANUNI YA 100% — maana yake halisi

```
Logic imetekelezwa 100%  ⇔  kila mstari wa rejista ya §3 una hadhi VERIFIED
```

Hadhi za kila kipengele cha rejista (mfuatano usiorukwa):

| Hadhi | Maana | Nani anaipandisha |
|---|---|---|
| `PLANNED` | ipo kwenye spec, code haijaanza | — |
| `IMPLEMENTED` | code ipo NA test yake ya spec inapita CI | mtekelezaji |
| `VERIFIED` | PD amekagua ushahidi (test/ripoti) na kutia sahihi | **PD pekee** |
| `LESSON` | eneo lilipimwa, halikufaulu, sababu imeandikwa | PD |

**Sheria tatu za msingi:**
1. **Code haitangulii spec.** Tofauti yoyote na spec = kwanza PD anabadilisha spec (na tarehe,
   mtindo `PD 2026-XX-XX`), kisha code inafuata. Kamwe kinyume.
2. **Hakuna `IMPLEMENTED` bila test inayotokana na spec.** Kila formula/gate/sheria ina test
   iliyoandikwa kutoka kwenye maneno ya spec (§4.1) — code inayopita kwa "inaonekana sawa" haipo.
3. **Hakuna `VERIFIED` bila ushahidi.** PD anaona test ikipita au ripoti — si maelezo ya mdomo.

---

## 1. MUUNDO WA USIMAMIZI

### 1.1 Majukumu
| Nafasi | Mamlaka |
|---|---|
| **PD** | anamiliki specs; anabadilisha config; anafungua HOLDOUT (mara moja); sahihi ya VERIFIED; GO/NO-GO ya R4 na ya live |
| **Mtekelezaji** | anajenga code + tests; anapandisha hadi IMPLEMENTED; hana mamlaka ya kubadilisha spec wala kizingiti |
| **CI (mashine)** | inasimamia milango ya §4 — haina ubaguzi, haina "mara hii tu" |

### 1.2 Definition of Done (kila PR/kazi)
```
☐ PR inataja spec:  "Spec: <doc> §<sehemu>"  na ID za rejista (mf. RCE-04)
☐ Tests za spec zimeongezwa/zinapita (CI kijani)
☐ Hakuna kigezo kipya nje ya config (risk.yaml / data.yaml ndizo chanzo cha ukweli)
☐ Rejista §3 imesasishwa (hadhi + tarehe + link ya ushahidi)
```

### 1.3 Mzunguko wa mapitio
- **Kila wiki:** mapitio ya rejista — nini kimepanda hadhi, nini kimekwama, LESSON mpya.
- **Mwisho wa kila TERM:** exit criteria (§2) zinakaguliwa; TERM haiishi kwa tarehe, inaisha
  kwa vigezo. Kuchelewa kunaripotiwa, kamwe hakufichwi kwa kupunguza ukali wa kigezo.
- **Badiliko la spec:** commit tofauti, PD pekee, tarehe + sababu — kisha rejista inasasishwa.

---

## 2. TERMS ZA UTEKELEZAJI (T0–T7 + tracks mbili za sambamba)

```
T0 MSINGI ─► T1 R0 ─► T2 R1 ─► T3 R2+R3 ─► T4 R4+R5 ─► T5 R6+R7 ─► T6 R8 ─► T7 SHADOW→LIVE
                │                   ▲
                ├── TRACK E: ENGINE (RCE code + tests) ── sambamba T1–T5, tayari kabla ya T7
                └── TRACK P: PRETRAINING ── sambamba T3–T5 (TRAIN+VAL pekee)
```

| Term | Kazi | Exit criteria (hakuna mjadala) |
|---|---|---|
| **T0 — MSINGI** | recorder wa feed ya broker (huanza, hauishii); normalization A/B → schema moja; L0 hashes; muundo wa research repo | recorder unarekodi kila siku ya trading; symbols 12 zinasomeka kwa schema moja; SHA256 za partitions zote zimehifadhiwa |
| **T1 — R0** | L1 (checks 8) + `quality_report.json`; kalenda ya sessions; L2 (TF 7 kutoka ticks + spread stats); sentinel ya uvujaji kwenye CI | R0 PASS kwa vizingiti vya `data.yaml`; sentinel inakimbia na kufelisha build ikigundua uvujaji; ulinganisho A↔B umeripotiwa |
| **T2 — R1** | L4: grid labels kwa path ya ticks + terminal returns za timeout; fill bootstrap; quality buckets | R1 PASS (base rates + jiometri + utulivu); `min_labels_per_cell ≥ 200`; M1-vs-tick disagreement imeripotiwa |
| **T3 — R2+R3** | feature cards F1–F7 (kabla ya code); L3 + screening (IC/MI + permutation + **FDR**); redundancy clustering | kila feature ina card; jedwali la screening na FDR limetoka; set ya mwisho ≤ bajeti (`labels ÷ 50`) |
| **T4 — R4+R5** | baselines B0/B1/B2; **GO/NO-GO**; calibration (isotonic kwenye validation folds) | B1/B2 > B0 kwa CI isiyogusa sifuri — AU **SIMAMA na rudi T2/T3**; ECE ≤ 0.05, Brier skill > 0 |
| **T5 — R6+R7** | EV ya madarasa 3, fill-aware, cost stress ×1.5; ablation ya familia + TF; wagombea wa Track P wanaingia hapa kupitia lango la R4 | EV_R net > baseline na inabaki chanya kwa cost ×1.5; jedwali la ablation limetoka |
| **T6 — R8** | PD anafungua HOLDOUT **mara moja**; attestation | vigezo vya `data.yaml §holdout`; attestation yenye `dataset_id` + config_hash imesainiwa — AU mzunguko unaisha LESSON |
| **T7 — SHADOW→LIVE** | integration (KAIROS→RCE→MT5); shadow/demo; kisha live + R9 monitoring (haina mwisho) | mnyororo mzima unafanya kazi demo kwa kipindi kilichotangazwa KABLA na PD; vigezo vya R9 vinapimwa live; fills za broker zinajaza calibration ya P(fill) |
| **TRACK E** (sambamba T1–T5) | `src/rce/`: budget, cost, lots, gate — kwa spec ILE ILE bila kuigusa | tests zote za RCE-* (§3.1) zinapita, ikiwemo golden test ya §6 ya spec |
| **TRACK P** (sambamba T3–T5) | pretraining ya encoder (§5A ya KAIROS-1) kwenye TRAIN+VAL pekee | corpus inaishia 2024-03-31 (CI inathibitisha); ripoti ya malengo; wagombea wanapimwa T5 |

**Terms HAZINA timeline.** Term inaisha pale exit criteria zake zinapotimia na PD kusaini —
kamwe si kwa tarehe. Mfuatano ndio mgumu; kasi inafuata ubora, si kinyume.

---

## 2A. ENEO LA UONGOZI — PROMPT YA KILA TERM + WAJIBU WA PD

> Hapa ndipo kazi inapoongozwa. Kila term ina **(a) PROMPT ya utekelezaji** — unayoitoa kwa
> session ya kazi (Claude) kuanzisha term, na **(b) WAJIBU WAKO (PD)** — unachopaswa **KUSOMA**,
> **KUPITIA**, **KUFANYA** au **KUSHIRIKI**. Term inayofuata haianzishwi kabla ya sahihi yako ya
> exit ya iliyotangulia. Safu ya **HALI** inasasishwa hapa kila term inapofunguliwa au kufungwa.

**▶ HALI YA SASA: T0 na TRACK E ziko TAYARI KUANZA. Nyingine zote: zinasubiri mfuatano.**

---

### T0 — MSINGI ▶ `TAYARI KUANZA`
**PROMPT:**
```
Tekeleza TERM T0 (docs/IMPLEMENTATION_PLAN.md §2, rejista DF-01..DF-04, DF-16):
1. Jenga recorder wa tick feed ya broker (MT5) kama COMPONENT INAYOWEZA KUPELEKWA KWA
   TENANT YEYOTE (broker-agnostic): bid/ask/volumes kila siku ya trading, partitions za
   L0 zenye tag `provenance: broker` + `tenant_id` + SHA256 (spec §2.2–2.3).
2. Tekeleza sera za data planes (spec §2.3 + config §data_planes): HUB — append-only,
   hakuna delete path kabisa; TENANT — append-only + SHA256 wakati zipo, prune ya umri
   (miezi 6) pekee, telemetry inasafirishwa HUB kabla ya prune, HAKUNA njia ya training
   kwenye tenant runtime.
3. Andika normalization ya Toleo A/B -> schema moja (spec §2.1); L0 haibadilishwi.
4. Hash partitions ZOTE za L0 zilizopo (SHA256 kwa kila partition) + rekodi manifest.
5. Simamisha muundo wa research repo (§9 ya DATA_FEATURE_STANDARD).
USIGUSE RCE. Mwisho: sasisha rejista (hadhi + ushahidi) na toa ripoti ya T0.
```
**WEWE (PD):**
- **KUSOMA:** `DATA_FEATURE_STANDARD.md` §2.1–2.2; rejista §3.3 (DF-01..04).
- **KUFANYA:** chagua/thibitisha **broker na akaunti** (demo au live) ya kurekodi feed — hili
  haliwezi kufanywa na mtu mwingine; toa access ya MT5 kwa mazingira ya recorder; amua
  **storage ya research** (nje ya repo hii, §9).
- **KUPITIA:** ripoti ya normalization (tofauti za A↔B zilizoonekana) + manifest ya hashes.
- **SAHIHI YA EXIT:** recorder unarekodi kila siku · schema moja inasomeka symbols 12 · hashes zipo.

---

### TRACK E — ENGINE (RCE) ▶ `TAYARI KUANZA` (sambamba na T1–T5)
**PROMPT:**
```
Tekeleza TRACK E (rejista RCE-01..RCE-13): jenga src/rce/ kwa spec RISK_COST_ENGINE.md
KAMA ILIVYO — hakuna kuibadilisha, hakuna kigezo nje ya config/risk.yaml.
Mpangilio: (1) andika KWANZA golden tests kutoka namba za spec — jedwali la bajeti §2
(safu 4), mfano wa lots §6 (0.16 lots / $34.88); (2) kisha code: budget -> cost_pips
(spread mseto, slippage cap, commission round-turn, swap modes 3 + triple WED, pip
conversion) -> lots (volume_step/min/max + REJECT) -> gate (checks 6 kwa mpangilio,
REJECT reasons + config-fingerprint kwenye log); (3) hakuna signal queue (§5b).
Mwisho: tests zote RCE-* kijani kwenye CI + rejista imesasishwa.
```
**WEWE (PD):**
- **KUFANYA:** toa **namba halisi za broker**: commission (round-turn?), swap za symbols,
  volume_min/step/max — zinaingia `broker_costs.yaml`, si kwenye code.
- **KUPITIA:** matokeo ya golden tests (yanalingana na mifano ya spec yako bit-kwa-bit).
- **SAHIHI YA EXIT:** RCE-01..13 zote IMPLEMENTED → wewe unazipandisha VERIFIED.

---

### T1 — R0 (DATA AUDIT) ▶ `INASUBIRI T0`
**PROMPT:**
```
Tekeleza TERM T1 (rejista DF-05..DF-08, DF-14, RS-03): L1 checks 8 + quality_report.json
kwa kila symbol/mwaka; kalenda ya sessions kutoka data (si kudhaniwa) kwa matoleo yote
mawili ya schema; L2 bars TF 7 kutoka ticks + spread stats kwa kila bar; as-of rule +
test yake (mfano wa §4.1); sentinel ya shuffle kwenye CI (G1); splitter anayesoma
config/data.yaml pekee (G2 holdout guard inaanza HAPA). Ripoti: R0 dhidi ya vizingiti
vya data.yaml + ulinganisho A<->B.
```
**WEWE (PD):**
- **KUSOMA:** `quality_report.json` (muhtasari) + ripoti ya ulinganisho A↔B.
- **KUFANYA:** thibitisha `broker_server_tz` na kalenda kwa broker halisi; amua hatma ya
  partitions zilizofeli (default: exclude + rekodi wigo uliopungua).
- **KUPITIA:** uthibitisho kwamba sentinel inafelisha build ya uvujaji wa makusudi (demo ya G1).
- **SAHIHI YA EXIT:** R0 PASS/LESSON kwa kila symbol.

---

### T2 — R1 (LABEL AUDIT) ▶ `INASUBIRI T1`
**PROMPT:**
```
Tekeleza TERM T2 (rejista DF-09..DF-11, K1-07, RS-04): L4 grid labels (5x5) kwa path ya
TICKS — touch kwa bei ya kufungia (BUY: bid / SELL: ask), gap-honest; timeout = darasa la
3 NA terminal return inarekodiwa; fill bootstrap (stop/limit kwa ticks; market = prior
0.98); quality buckets (R_net). Ripoti ya R1: base rates dhidi ya jiometri
(p ~ sl/(sl+tp)), utulivu kwa miaka, timeout share, M1-vs-tick disagreement,
curve ya utulivu wa label. TRAIN+VAL PEKEE — takwimu za holdout MARUFUKU (G2).
```
**WEWE (PD):**
- **KUPITIA:** ripoti ya R1 — hasa base rate vs jiometri na utulivu kwa miaka.
- **KUFANYA:** ikifeli — amua horizon/grid mpya (fahamu: hiyo ni dataset mpya, si tweak).
- **SAHIHI YA EXIT:** R1 PASS/LESSON.

---

### T3 — R2+R3 (FEATURES) ▶ `INASUBIRI T2`
**PROMPT:**
```
Tekeleza TERM T3 (rejista DF-12, DF-13, K1-09, RS-05, RS-06): KWANZA feature cards za
F1-F7 zenye hypothesis (PD anazithibitisha KABLA ya code — G4); kisha L3 kwa sheria 8
(scale-free, rolling norm, as-of, bajeti 50, per-fold kwa model-derived); screening ndani
ya purged folds: IC/MI + permutation + FDR (BH, q=0.10) — pooled pekee; redundancy
clustering |rho|>=0.80 -> mwakilishi mmoja. Meta-features zote OOF (G5).
Deliverables: jedwali la screening (candidate->screened|LESSON) + dendrogram + set ya mwisho.
```
**WEWE (PD):**
- **KUSHIRIKI:** **kuandika/kuthibitisha hypothesis za feature cards** — owner wa card ni wewe;
  hakuna feature inayojengwa bila hypothesis uliyoikubali.
- **KUPITIA:** jedwali la screening + FDR, orodha ya walioondolewa na sababu.
- **SAHIHI YA EXIT:** set ya mwisho ≤ bajeti; R2/R3 PASS/LESSON kwa kila familia.

---

### TRACK P — PRETRAINING ▶ `INASUBIRI T1 (L2 bars)` (sambamba na T3–T5)
**PROMPT:**
```
Tekeleza TRACK P (rejista K1-13, §5A ya KAIROS_1_STANDARD): pretraining ya encoder kwa
malengo ya config (next_bar_direction, masked_bar, contrastive_regime) kwenye bars za
TRAIN+VAL PEKEE — corpus inaishia 2024-03-31 (G8 inathibitisha). Fine-tune heads
pekee kwenye trade labels. Wagombea wanaingia T5 kupitia lango la R4 — hakuna upendeleo.
Deliverable: encoder + ripoti ya malengo (loss curves, probing) + rejista.
```
**WEWE (PD):**
- **KUPITIA:** ripoti ya pretraining (haina namba za EV — ni uwezo wa representation tu).
- **HAKUNA SAHIHI YA ZIADA:** hukumu ya wagombea inatolewa T5 kwa vigezo vya §6 ya KAIROS-1.

---

### T4 — R4+R5 (BASELINE + CALIBRATION) ▶ `INASUBIRI T3` — **GO/NO-GO YAKO**
**PROMPT:**
```
Tekeleza TERM T4 (rejista RS-07, RS-08, K1-12): baselines B0 (base rate), B1 (logistic,
features 5 bora), B2 (GBM depth 3 / trees 200, set ya R3) — purged CV, EV_R na CI yake;
kisha calibration: isotonic kwenye validation folds pekee, ECE, Brier skill, reliability
kwa symbol na session. Andaa kifurushi cha ushahidi cha GO/NO-GO kwa PD: EV_R ya kila
baseline + CI, reliability curves. HAKUNA kuendelea bila uamuzi wa PD.
```
**WEWE (PD):**
- **KUSOMA:** kifurushi cha GO/NO-GO (EV_R + confidence intervals + calibration).
- **KUFANYA:** **UAMUZI WA GO/NO-GO — wako peke yako.** NO-GO = rudi T2/T3 na LESSON;
  hii ndiyo hatua inayookoa miezi — usiipite kwa matumaini.
- **SAHIHI YA EXIT:** GO iliyoandikwa, au NO-GO + maelekezo ya kurudi.

---

### T5 — R6+R7 (EV + ABLATION) ▶ `INASUBIRI T4`
**PROMPT:**
```
Tekeleza TERM T5 (rejista K1-02..K1-06, K1-08, RS-09, RS-10): pipeline kamili ya uamuzi
kwa mfuatano rasmi (§2 ya KAIROS-1) — SL floor, EV ya madarasa 3 (E[R|timeout] kutoka
timeout labels — SI quantile head), EV_final = P(fill) x EV_signal, filters kwa R-units;
cost stress x1.5; ablation ya familia F1-F7 na TF zote (ondoa -> funza upya -> delta EV_R).
Wagombea wa Track P wanapimwa hapa dhidi ya B2. Deliverables: EV_R net fill-aware +
jedwali la ablation + mapendekezo ya kuondoa familia.
```
**WEWE (PD):**
- **KUPITIA:** jedwali la ablation (ramani ya thamani ya mfumo mzima) + matokeo ya stress.
- **KUFANYA:** amua familia/TF za kuondoa (kila ondoleo = LESSON iliyoandikwa).
- **SAHIHI YA EXIT:** mchanganyiko wa mwisho umefungwa (frozen) tayari kwa R8.

---

### T6 — R8 (HOLDOUT + ATTESTATION) ▶ `INASUBIRI T5` — **MARA MOJA**
**PROMPT:**
```
Tekeleza TERM T6 (rejista RS-11, DF-03, K1-14): thibitisha vigezo vya kupita vime-commit
KABLA (G4); PD anawasha job ya R8 (yeye pekee ana ruhusa ya holdout); pima mchanganyiko
ULIOFUNGWA T5 — hakuna marekebisho baada ya kuona namba; andika ATTESTATION: dataset_id,
config_hash, feature set, vigezo vilivyotangazwa, namba, provenance ya gharama, PASS/LESSON.
```
**WEWE (PD):**
- **KUFANYA:** **wewe pekee unafungua holdout — MARA MOJA.** Kabla ya kubofya, jiulize:
  vigezo vime-commit? mchanganyiko umefungwa? Ndiyo → fungua.
- **KUPITIA + SAHIHI:** attestation. PASS → T7. LESSON → mzunguko unaisha kwa heshima;
  mzunguko ujao unatumia RESERVE mpya.

---

### T7 — SHADOW → LIVE + R9 ▶ `INASUBIRI T6`
**PROMPT:**
```
Tekeleza TERM T7 (rejista K1-10, K1-11, RCE-05, RS-12): integration KAIROS-1 -> RCE ->
MT5 kwa mkataba wa §4 ya KAIROS-1 (cost_pips chanzo kimoja; mamlaka hazichanganyiki);
shadow/demo kwa kipindi PD alichokitangaza KABLA; kila fill inarekodi requested_px/fill_px/
slippage/fill_rate; dashboard ya R9 (rolling ECE, EV_R live, PSI, fill_rate) na alerts
za vigezo vya kustaafu (data.yaml §monitoring). Ripoti ya shadow -> PD kwa uamuzi wa live.
```
**WEWE (PD):**
- **KUFANYA:** tangaza **kipindi cha shadow KABLA** ya kuanza; andaa akaunti ya demo; baada ya
  ripoti ya shadow — **uamuzi wa LIVE ni wako**.
- **KUPITIA:** dashboard ya R9 **kila wiki** (hii ni ya kudumu, haina mwisho); kila alert ya
  kustaafu inahitaji uamuzi wako ndani ya muda uliojiwekea.
- **KUSHIRIKI:** re-attestation kila robo (RESERVE mpya kama holdout).

---

## 3. REJISTA YA COMPLIANCE (traceability — kila logic ya mpango)

> Hii ndiyo hati ya "100%". Kila mstari = logic moja ya spec. Njia za uthibitisho:
> **UT** unit test · **GT** golden test (mfano wa namba kutoka spec) · **CI** lango la pipeline ·
> **RPT** ripoti inayokaguliwa na PD · **PROC** sheria ya mchakato (inakaguliwa kwenye mapitio).
> Hadhi zote zinaanza `PLANNED`; safu ya hadhi inasasishwa kwenye repo kila wiki.

### 3.1 RCE — `RISK_COST_ENGINE.md` (spec HAIGUSWI; inatekelezwa kama ilivyo)
| ID | Spec | Logic | Uthibitisho | Term |
|---|---|---|---|---|
| RCE-01 | §2 | budget = base − penalty + win_factor×profit − loss_factor×loss; penalty = 0.5 × DD ya jumla; hairesetiwi | GT: safu 4 za jedwali la §2 kama test vectors | E |
| RCE-02 | §2 | today_profit/loss zinareset 00:00 CE(S)T; base_balance ni rejea isiyobadilika | UT (timezone + reset) | E |
| RCE-03 | §3.1 | spread_effective = max(H1 base window 100, p95 ya M5 window 288) | UT | E |
| RCE-04 | §3.2 | slippage = CAP; cap = min(dynamic M5, backtest assumption); inabana TU, hailegei; order.deviation kwa POINTS | UT + AUD ya order params | E |
| RCE-05 | §3.2 | fill_rate inapimwa; < 0.60 → ONYO + hatua (a)/(b) | UT + RPT | E/T7 |
| RCE-06 | §3.3 | commission round-turn; upande mmoja → ×2 | UT | E |
| RCE-07 | §3.4 | swap kwa mwelekeo + mode (CURRENCY/POINTS/INTEREST) + triple Jumatano | UT (matawi yote 3 × triple) | E |
| RCE-08 | §3.5 | pip_value conversion kwa akaunti (lots NA comm/swap pips) | UT | E |
| RCE-09 | §4 | lots = risk ÷ ((SL + cost) × pipval); volume_step/min/max; chini ya min → REJECT | UT + GT | E |
| RCE-10 | §5 | gate: checks 6 kwa MPANGILIO wake; kila REJECT ina reason + config-fingerprint kwenye log | UT (kila check + mpangilio) | E |
| RCE-11 | §5 | DD inazuia entries MPYA pekee — haifungi positions wazi | UT | E |
| RCE-12 | §5b | hakuna signal queue; signal iliyokataliwa hairudishwi | UT + AUD ya code (hakuna retry path) | E |
| RCE-13 | §6 | mfano kamili end-to-end: lots 0.16, hasara $34.88 ≈ risk | **GT ya lazima kila commit** | E |

### 3.2 KAIROS-1 — `KAIROS_1_STANDARD.md`
| ID | Spec | Logic | Uthibitisho | Term |
|---|---|---|---|---|
| K1-01 | §1.2 | uamuzi wa entry H1 PEKEE; M5 ni ya RCE; M15 haithibitishi nje ya muundo wa H1 | AUD + UT (hakuna feature ya uamuzi ya M5) | T3–T5 |
| K1-02 | §2 | pipeline kwa mfuatano rasmi: Quantile → SL floor → Barrier → EV → Fill → filters | UT ya mtiririko | T5 |
| K1-03 | §2/S2 | SL_final = max(Q10_based, 5×cost_pips, 0.5×ATR) | UT (matawi yote 3) | T5 |
| K1-04 | §2.1 | EV = p_tp×TP − p_sl×SL + p_timeout×E[R\|timeout]; E[R\|timeout] kutoka timeout labels, SI quantile head | UT + AUD (anti-S1) | T5 |
| K1-05 | S1 | heads mbili tofauti; barrier labels ni grid input, si derived | AUD ya architecture + UT ya label source | T2/T5 |
| K1-06 | S3 | vizingiti kwa R-units/cost-multiples, kamwe si pips ghafi | UT | T5 |
| K1-07 | S4 | fill bootstrap kwa ticks; market orders = prior 0.98 + demo calibration | UT + RPT | T2/T7 |
| K1-08 | S5 | EV_final = P(fill) × EV_signal; HAKUNA opportunity cost kwenye lango | UT (formula exact) | T5 |
| K1-09 | S6 | kila output ya model inayolisha model nyingine ni OUT-OF-FOLD | **CI**: meta-features zina metadata ya fold; in-sample → build fail | T3–T5 |
| K1-10 | §4.1/4.2 | interface: fields zote za pendekezo; cost_pips chanzo KIMOJA (RCE) — model haihesabu yake | UT ya schema + AUD | T7 |
| K1-11 | §4.3 | mgawanyo wa mamlaka: model haiamui lots/ruhusa; RCE haiamui entry/mwelekeo | AUD | T7 |
| K1-12 | §5.3 | probability yoyote inayoingia maamuzi ni CALIBRATED — isiyo-calibrated hairuhusiwi kulisha EV/sizing | **CI**: artifact bila calibration report → haipandi hadhi | T4 |
| K1-13 | §5A | pretraining: corpus inaishia trainval_end; fine-tune heads; lango la R4 kwa wote; PPO lazima ishinde bandit | **CI** (tarehe ya corpus) + RPT | P |
| K1-14 | §6 | vigezo vya kupokelewa: kushinda baseline + calibration + fill-aware + pre-registration | RPT + PROC | T5–T6 |

### 3.3 DATA — `DATA_FEATURE_STANDARD.md`
| ID | Spec | Logic | Uthibitisho | Term |
|---|---|---|---|---|
| DF-01 | §2 | L0 = ticks bid+ask, immutable, append-only, SHA256 kila partition | UT + CI (hash check kila build) | T0 |
| DF-02 | §2.1 | normalization A/B → schema moja; L0 haibadilishwi | UT (matoleo yote 2) | T0 |
| DF-03 | §2.2 | provenance: partitions mpya za broker zina tag; attestation inataja provenance ya gharama | PROC + RPT | T0/T6 |
| DF-04 | §2.2 | recorder wa feed ya broker unarekodi kila siku | **CI/alert**: siku ya trading bila data mpya → ONYO | T0+ |
| DF-05 | §3 | checks 8 za L1; ikifeli → exclude + ripoti; hakuna imputation | UT (kila check) + RPT | T1 |
| DF-06 | §4 | TF 7 kutoka ticks/M1 ya ndani; spread stats kwa kila bar | UT | T1 |
| DF-07 | §4.1 | AS-OF: bar isiyofungwa HAITUMIKI; D1 ya jana kwa uamuzi wa H1 | UT (mfano wa §4.1 kama test) | T1 |
| DF-08 | §4.2 | sentinel ya shuffle kila build ya L3; ikigundua → build inasimama | **CI ya lazima** | T1+ |
| DF-09 | §5 | labels kwa path ya TICKS; touch kwa bei ya kufungia (BUY: bid); gap-honest | UT (kesi za gap + spread) | T2 |
| DF-10 | §5.2 | grid 5×5; timeout darasa la 3 + terminal return inarekodiwa | UT | T2 |
| DF-11 | §5.5 | horizon moja iliyotangazwa; class balance inaripotiwa, haisawazishwi; timeout haitupwi | UT + RPT | T2 |
| DF-12 | §6.1 | sheria 8 za features (scale-free, rolling norm, as-of, card, bajeti 50, determinism, NaN, model-derived per-fold) | UT + **CI** (card ya lazima; bajeti; norm ya rolling) | T3 |
| DF-13 | §6.2 | F6 ni ya kusoma tu — cost ya RCE; news kwa muda pekee | AUD | T3 |
| DF-14 | §7 + SPLIT_PLAN | splits kwa tarehe za config; purge + embargo bars 36; pooled kwa wakati; random split MARUFUKU | UT + **CI** (splitter anasoma config pekee) | T1+ |
| DF-15 | §8 | kila dataset ina manifest + dataset_id; namba bila dataset_id haiingii engine | **CI**: ripoti bila dataset_id inakataliwa | T1+ |
| DF-16 | §2.3 | data planes: HUB haifuti kamwe (mafunzo hub_only); TENANT — append-only+SHA256 wakati zipo, retention miezi 6 kwa umri tu, `local_training: false`, telemetry inasafirishwa HUB kabla ya kufuta | UT (prune policy + immutability) + **CI** (hakuna njia ya training kwenye tenant runtime) + AUD | T0/T7 |

### 3.4 UTAFITI — `RESEARCH_PLAN_R0.md` + `DATA_SPLIT_PLAN.md`
| ID | Spec | Logic | Uthibitisho | Term |
|---|---|---|---|---|
| RS-01 | §0/§3 | pre-registration: vigezo vime-commit KABLA ya kukimbiza; kubadilisha baada ya namba = kufuta awamu | **CI**: git history inathibitisha mpangilio | zote |
| RS-02 | §1 | mishale migumu: R2 haianzi kabla R1 PASS, n.k. | PROC (rejista ya awamu) | zote |
| RS-03 | R0 | vizingiti vya data audit + ulinganisho A↔B + kalenda kwa data | RPT | T1 |
| RS-04 | R1 | sanity ya jiometri (random walk p ≈ sl/(sl+tp)); utulivu kwa miaka; timeout ≤ 0.35 | RPT + UT | T2 |
| RS-05 | R2 | purged folds hata kwenye screening; permutation + **FDR (BH, q=0.10)**; per-symbol IC hairuhusiwi kuamua | UT + **CI** (FDR kwenye schema ya output) | T3 |
| RS-06 | R3 | clustering \|ρ\|≥0.80 → mwakilishi mmoja; si PCA | RPT | T3 |
| RS-07 | R4 | B0/B1/B2; B > B0 na CI isiyogusa sifuri AU SIMAMA; EV_R ya B2 = kizingiti cha kudumu | RPT + PROC (GO/NO-GO ya PD) | T4 |
| RS-08 | R5 | ECE ≤ 0.05; Brier skill > 0; isotonic kwenye validation pekee; inasafiri na model | UT + RPT | T4 |
| RS-09 | R6 | EV madarasa 3, fill-aware, cost ×1.5 inabaki chanya; trades zisizojaza si trades | UT + RPT | T5 |
| RS-10 | R7 | ablation ya familia zote + TF zote; ΔEV_R chanya → ondoa + LESSON | RPT | T5 |
| RS-11 | R8 | **HOLDOUT guard**: files za kipindi cha holdout hazisomeki na jobs za R0–R7; PD anafungua mara moja; ikifeli → LESSON, hakuna kurudia | **CI** (access guard) + PROC | T1–T6 |
| RS-12 | R9 | shadow ya lazima; vigezo vya kustaafu vya `data.yaml §monitoring`; re-attestation kila robo kwa RESERVE mpya | RPT + dashboard | T7+ |
| RS-13 | §3 | LESSON inaandikwa kwa undani sawa na PASS | PROC | zote |
| RS-14 | SPLIT §3 | RESERVE (2026-05+) haionwi kabisa hadi mzunguko ujao | **CI** (access guard ile ile) | zote |

**Jumla: vipengele 57.** `100% = 57/57 VERIFIED` (au LESSON iliyoandikwa pale eneo lilipofeli
kwa vigezo — LESSON ni jibu halali; kificho ni pale tu eneo linaruka bila kupimwa).

---

## 4. MILANGO YA CI (mashine inasimamia, si mtu)

### 4.1 Tests zinatoka kwenye spec — utaratibu
Kwa kila formula/jedwali la mifano kwenye spec, test inaandikwa **kwanza** kutoka kwenye namba za
spec (mf. jedwali la bajeti §2 ya RCE, mfano wa lots §6, mfano wa as-of §4.1 wa data standard).
Code inaandikwa mpaka test ipite. Spec ikiwa haina mfano wa namba, mtekelezaji anaandika test
vector na **PD anaithibitisha kabla** ya code.

### 4.2 Milango isiyo na huruma (build inafeli, hakuna override)
```
G1  SENTINEL         shuffle-test ya uvujaji kila build ya L3            (DF-08)
G2  HOLDOUT GUARD    R0–R7 zikisoma kipindi cha holdout/RESERVE → FAIL   (RS-11, RS-14)
G3  DATASET_ID       ripoti/namba yoyote bila dataset_id + config_hash   (DF-15)
G4  PRE-REG          results kabla ya vigezo kwenye git history → FAIL   (RS-01)
G5  OOF              meta-feature bila metadata ya fold → FAIL           (K1-09)
G6  CALIBRATION      model bila calibration report → haipandi hadhi      (K1-12)
G7  GOLDEN RCE       test ya §6 (lots 0.16 / $34.88) kila commit         (RCE-13)
G8  CORPUS DATE      pretraining data > 2024-03-31 → FAIL                (K1-13)
G9  SPEC-REF         PR bila "Spec: ..." + ID za rejista → inakataliwa   (§1.2)
G10 CONFIG ONLY      kigezo cha maamuzi nje ya risk.yaml/data.yaml → FAIL (DoD)
```

### 4.3 Ulinzi wa HOLDOUT (G2 — ufafanuzi)
Partitions za kipindi cha holdout (2024-04-01 → 2026-04-30) na RESERVE (2026-05+) zinakaa kwenye
eneo tofauti la storage lenye ruhusa ya kusoma kwa **job ya R8 pekee** (inayowashwa na PD).
Hii inafanya "kuchungulia holdout" kuwa **haiwezekani kimfumo**, si mwiko wa maadili tu.

---

## 5. RIPOTI YA HALI (kila wiki, mstari mmoja kwa kila term hai)

```
TERM · vipengele VERIFIED/jumla · vilivyo IMPLEMENTED vinasubiri PD · LESSON mpya · vikwazo
```
Rejista ya §3 ndiyo chanzo; ripoti ni mtazamo wake. Mzunguko unaisha pale safu ya hadhi
inaposema 56/56 — si pale mtu anaposema "tumemaliza".

---

## 6. NJE YA WIGO
Marekebisho ya specs zenyewe (PD pekee) · maudhui ya models (KAIROS-1) · vigezo vya risk (RCE —
**hazibadilishwi na hati hii**). Hati hii inasimamia *utekelezaji na uthibitisho*, si *maamuzi*.
