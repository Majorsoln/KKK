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

### 0.1 SAHIHI YA PD — inafanywaje (PD 2026-08-07)

Hadi leo "sahihi ya PD" ilitajwa mara 15 kwenye hati hii bila kuelezwa **inafanywaje** —
yaani `VERIFIED` haikuwa na maana ya kiufundi. Sasa inayo:

```cmd
scripts\sign.bat DF-05 VERIFIED --evidence research\reports\quality\quality_report.json ^
                 --reason "partitions 25,498 · kufeli 0.6% · nimekagua sababu zote"
git add docs\SIGNATURES.md
git commit -m "sahihi: DF-05 VERIFIED"
```

**Commit ndiyo sahihi.** Si sanduku la kutia alama wala ujumbe wa gumzo. Mstari unaowekwa
kwenye `docs/SIGNATURES.md` unafunga vitu vinne pamoja:

| Kinachofungwa | Kinatoka wapi | Kinazuia nini |
|---|---|---|
| **NANI** | `git config user.name/email` ya mashine yako | mtu mwingine — mtekelezaji au model — kujipandisha hadhi |
| **LINI** | muda wa commit + **mfuatano** wake kwenye historia | kudai pre-registration baada ya kuona matokeo (RS-01/G4) |
| **NINI** | ID ya rejista + uamuzi | sahihi isiyo na kipengele halisi |
| **KWA NINI** | `config_hash` + `code_rev` + **SHA256 ya faili la ushahidi** | kusaini ripoti kisha kuiandika upya, au kubadilisha vizingiti |

Uamuzi nne pekee: **`VERIFIED`** (inahitaji `--evidence`) · **`LESSON`** · **`APPROVED`**
(pre-registration, kabla ya matokeo) · **`REJECTED`** (ushahidi hautosha — kinarudi `IMPLEMENTED`).

**Mistari haifutwi wala haihaririwi.** Ukibadilisha mawazo, unaweka mstari mpya; wa mwisho ndio
unaotawala. Historia ya kubadili mawazo ni sehemu ya ushahidi.

**Kabla ya sahihi ya kwanza:** fungua `docs/SIGNATURES.md`, badilisha mstari `**PD:**` uweke
utambulisho wako halisi wa git. Sahihi za `VERIFIED`/`APPROVED`/`LESSON` kutoka kwa mtu mwingine
yeyote **zinakataliwa na lango G14** — hivyo mimi (au mtekelezaji yeyote) siwezi kusaini kwa
niaba yako hata nikitaka.

Amri nyingine: `python -m src.governance.cli pending` (nini kinasubiri sahihi yangu?) ·
`verify` (lango G14) · `show` (sahihi zote).

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

**▶ HALI YA SASA (2026-08-07).** T0 `IMEFUNGWA` — DF-01..04, DF-17, DF-18 ziko `VERIFIED` kwa
data halisi (ledger §3.5). **T1 (R0): code imekamilika** (DF-05..08, DF-14, RS-03 ziko
`IMPLEMENTED`; malango G1 na G2 yanakimbia kila build); kipimo cha data halisi kinaendelea, na
`VERIFIED` inasubiri sahihi ya PD baada ya `audit.bat` kwa symbols zote 12. **TRACK E:**
`IMPLEMENTED`, inasubiri namba halisi za broker (T7). Nyingine: zinasubiri mfuatano.

---

### T0 — MSINGI ▶ `IMEFUNGWA` 2026-08-06 (ripoti: `docs/T0_REPORT.md` · ledger §3.5)
**PROMPT:**
```
Tekeleza TERM T0 (docs/IMPLEMENTATION_PLAN.md §2, rejista DF-01..DF-04):
1. Jenga recorder wa tick feed ya broker (MT5): bid/ask/volumes kila siku ya trading,
   partitions za L0 zenye tag `provenance: broker` + SHA256 (spec §2.2 ya DATA_FEATURE_STANDARD).
2. Andika normalization ya Toleo A/B -> schema moja (spec §2.1); L0 haibadilishwi.
3. Hash partitions ZOTE za L0 zilizopo (SHA256 kwa kila partition) + rekodi manifest.
4. Simamisha muundo wa research repo (§9 ya DATA_FEATURE_STANDARD).
USIGUSE RCE. Mwisho: sasisha rejista (hadhi + ushahidi) na toa ripoti ya T0.
```
**WEWE (PD):**
- **KUSOMA:** `DATA_FEATURE_STANDARD.md` §2.1–2.2; rejista §3.3 + ledger §3.5; `docs/T0_REPORT.md`.
- **RUNBOOK:** `docs/SETUP.md` — hatua zote za kusimamisha (env, storage, broker_id, production,
  kuhamia server nyingine) pamoja na makosa halisi na suluhisho zake.
- **KUFANYA:** chagua/thibitisha **broker na akaunti** (demo au live) ya kurekodi feed — hili
  haliwezi kufanywa na mtu mwingine; toa access ya MT5 kwa mazingira ya recorder; amua
  **storage ya research** (nje ya repo hii, §9) na uweke `ELITEFX_RESEARCH_ROOT`; thibitisha
  sehemu mpya `storage:` na `recorder:` za `config/data.yaml`.
- **KUPITIA:** ripoti ya normalization (tofauti za A↔B zilizoonekana) + manifest ya hashes.
- **SAHIHI YA EXIT:** recorder unarekodi kila siku · schema moja inasomeka symbols 12 · hashes zipo.
- **HALI:** zana zote nne zimejengwa na zina tests (ripoti §2). Vigezo vitatu vya exit vinasubiri
  vitu vyako vitatu hapo juu — ndio pekee vinavyozuia `VERIFIED`.

---

### TRACK E — ENGINE (RCE) ▶ `IMEJENGWA — INASUBIRI NAMBA ZA BROKER` (sambamba na T1–T5)
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

### T1 — R0 (DATA AUDIT) ▶ `CODE IMEKAMILIKA · KIPIMO CHA DATA HALISI KINAENDELEA` (ledger §3.5)
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
- **KUENDESHA:** `scripts\audit.bat` (SETUP §3.1) — hatua 6, haigusi MT5.
- **KUSOMA** (zote ziko `research/reports/quality/`):

  | Faili | Swali linalojibiwa |
  |---|---|
  | `quality_report.json` | data ni safi kiasi gani, kwa symbol/mwaka, dhidi ya vizingiti vyote |
  | `threshold_study.json` | kizingiti kilichotumika ni sahihi, au kinafelisha data nzuri? |
  | `calendar_vs_assumed.json` | kalenda tuliyodhani ilikuwa na makosa mangapi; Toleo A ↔ B |
  | `variant_comparison.json` | matoleo mawili ya schema yanatoa data moja? |
  | `provenance_comparison.json` | **spread ya broker ni pana kiasi gani kuliko ya aggregator?** |

- **KUFANYA:** (1) thibitisha `broker_server_tz` na kalenda kwa broker halisi; (2) chagua
  vizingiti kutoka `threshold_study.json` na uviandike `config/data.yaml` → `quality:`;
  (3) amua hatma ya partitions zilizofeli (default: exclude + rekodi wigo uliopungua).
- **KUPITIA:** uthibitisho kwamba sentinel inafelisha build ya uvujaji wa makusudi (demo ya G1) —
  `pytest -k sentinel` ina test inayodai jina la feature iliyovuja.
- **SAHIHI YA EXIT:** R0 PASS/LESSON kwa kila symbol. Vipengele vinavyopanda `VERIFIED`:
  DF-05, DF-06, DF-07, DF-08, DF-14, RS-03.

---

### T2 — R1 (LABEL AUDIT) ▶ `INASUBIRI T1`
**PROMPT:**
```
Tekeleza TERM T2 (rejista DF-09..DF-11, DF-20, DF-21, K1-07, RS-04):
KWANZA — sheria ya SETUP (§4.3, DF-20): decision points kwa SETUP-v1 kutoka config/data.yaml
§setups; kutuna kwa RATE (~5%) pekee, KABLA labels hazijaonekana; control sample 10%
(is_control=true, haiingii training); setup_rule_id ndani ya dataset_id; sentinel inaipima.
Hakuna label inayohesabiwa kabla PD hajasaini sheria (pre-registration, RS-01).
KISHA — L4 grid labels (5x5) kwa path ya TICKS: touch kwa bei ya kufungia (BUY: bid /
SELL: ask), gap-honest, TIE-BREAK = SL kwanza gap ikifunika zote mbili (§5.2, DF-21);
L-A quantile kwa MID (§5.1); timeout = darasa la 3 NA terminal return inarekodiwa; fill
bootstrap (stop/limit kwa ticks; market = prior 0.98); quality buckets (R_net).
Ripoti ya R1: base rates kwa fomula p_tp/(p_tp+p_sl) ~ sl/(sl+tp) (BILA timeout, RS-04),
utulivu kwa miaka, timeout share, mzunguko wa tie-break (>1% -> PD), setup-vs-control,
quantiles mid-vs-trade kwa XAUUSD/GBPJPY, M1-vs-tick disagreement, curve ya utulivu.
TRAIN+VAL PEKEE — takwimu za holdout MARUFUKU (G2).
```
**WEWE (PD):**
- **KUSAINI KWANZA:** sheria ya setup (§4.3 + config §setups) KABLA ya label yoyote — hii
  ndiyo pre-registration; bila hiyo kila namba ya R1+ ni ya baada ya ukweli.
- **KUPITIA:** ripoti ya R1 — hasa base rate vs jiometri (fomula mpya), setup-vs-control
  (je filter inatupa trades bora?), na mzunguko wa tie-break.
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
| DF-20 | §4.3 | sheria ya SETUP: mechanical, point-in-time, pre-registered; `setup_rule_id` ndani ya dataset_id; kutuna kwa RATE pekee kabla ya labels; **control sample 10%** ya bars zisizo setup inapata labels (`is_control`) — filter inapimwa, si kudhaniwa; R1 haianzi bila sahihi ya PD | UT + sentinel + PROC (pre-reg) + RPT (R1/R7 setup-vs-control) | T2 |
| DF-21 | §5.1–§5.2 | mikataba ya bei ya label: L-A entry/exit = **mid** (S1: inapendekeza, haihukumu; spread inaingia path na RCE, si mara 3); barrier **tie-break = SL kwanza** gap ikifunika zote mbili; timestamp moja → mpangilio wa kufika (stable sort); R1 inaripoti mzunguko wa tie-break na mid-vs-trade quantile diff | UT (kesi za gap/tie) + RPT | T2 |
| DF-19 | SETUP §7b | scripts za mzunguko wa kila siku (`catchup`/`record`/`status`); sifa za mashine ziko `env.local.bat` isiyopushwa; template inabaki tupu | **UT**: G13 (`test_repo_guards.py`) | T0 |
| DF-18 | §2.2 | recorder inajitibu: kalenda dhidi ya DISK (si state) → siku zilizorukwa zinazibwa; `backfill` CLI + reconcile on-start/kila polls N; siku isiyo na ticks HAIANDIKWI tupu | UT: `test_backfill_*` (state iliyopotea + siku ya kati iliyorukwa) | T0 |
| DF-17 | §9 | `research/` ndani ya repo: reports+src zinapushwa, `research/data/` haipushwi kamwe; engine hairudii code ya utafiti | **UT/CI**: `tests/test_repo_guards.py` (G11 · G12) — imethibitishwa kwa jaribio hasi | T0 |

### 3.4 UTAFITI — `RESEARCH_PLAN_R0.md` + `DATA_SPLIT_PLAN.md`
| ID | Spec | Logic | Uthibitisho | Term |
|---|---|---|---|---|
| RS-01 | §0/§3 | pre-registration: vigezo vime-commit KABLA ya kukimbiza; kubadilisha baada ya namba = kufuta awamu | **CI**: git history inathibitisha mpangilio | zote |
| RS-02 | §1 | mishale migumu: R2 haianzi kabla R1 PASS, n.k. | PROC (rejista ya awamu) | zote |
| RS-03 | R0 | vizingiti vya data audit + ulinganisho A↔B + kalenda kwa data | RPT | T1 |
| RS-04 | R1 | sanity ya jiometri kwa fomula sahihi: `p_tp/(p_tp+p_sl) ≈ sl/(sl+tp)` (BILA timeout — `p_tp_first` peke yake haiwezi kufikia jiometri kwa timeout 35%); spread inasogeza chini kidogo kwa utaratibu; utulivu kwa miaka; timeout ≤ 0.35 | RPT + UT | T2 |
| RS-15 | R2 | takwimu za screening: decision point moja = uzito mmoja (si rows za grid); SE kutoka **block bootstrap** (blocks za muda, symbols zote pamoja — symbols 12 si huru, effective N ~9k si 38k); kizingiti halisi = max(`ic_min`, p99 ya null ya bootstrap) | UT + RPT | T3 |
| RS-16 | R6 | `E[R\|timeout]` per cell ni **out-of-fold** (S6); R6 inaripoti sehemu ya signals zinazochukulika chini ya bajeti ya RCE (positions zinapishana — EV ya mfumo ni ya zinazochukulika) | UT + RPT | T5 |
| RS-17 | §5A | pretraining ni **walk-forward** kwa kila fold (data ≤ val_start − embargo; warm-start OK); GBM baseline inapimwa protocol ile ile — R4 hailinganishi vitu viwili tofauti | PROC + RPT | T4/P |
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

**Jumla: vipengele 64** (59 za awali + DF-20, DF-21, RS-15, RS-16, RS-17 — mapitio ya ushauri
wa nje, PD 2026-08-07). `100% = 64/64 VERIFIED` (au LESSON iliyoandikwa pale eneo lilipofeli
kwa vigezo — LESSON ni jibu halali; kificho ni pale tu eneo linaruka bila kupimwa).

### 3.5 LEDGER YA HADHI (hii ndiyo safu ya hadhi ya §3 — inasasishwa kila wiki)

> Vipengele visivyotajwa hapa viko `PLANNED`. Kupanda `IMPLEMENTED` ni kazi ya mtekelezaji
> (code + test ya spec inapita CI); kupanda `VERIFIED` ni **sahihi ya PD** juu ya ushahidi.

| ID | Hadhi | Tarehe | Ushahidi | Kinachosubiriwa kwa VERIFIED |
|---|---|---|---|---|
| DF-01 | `VERIFIED` | 2026-08-06 | **data halisi:** `verify-l0 PASS · unchanged=25486 changed=0 missing=0 untracked=0` (exit 0). Lango lilifanya kazi kabla ya hapo: `changed=4` lilipogundua partitions zilizoandikwa upya baada ya kufutwa kwa idhini — zilisasishwa kwa `--allow-mutation --reason` (`mutation_log`) | — |
| DF-02 | `VERIFIED` | 2026-08-06 | **data halisi:** EURUSD (Toleo `A`, 89,873 rows, siku) na XAUUSD (Toleo `B`, 1,952,567 rows, mwezi) zote zikitoa `timestamp/bid/ask/bid_vol/ask_vol` | — |
| DF-03 | `VERIFIED` | 2026-08-06 | **data halisi:** partitions 876 za `provenance=broker` (symbols 12 × siku 73, 2026-04-27 → 08-05) zenye `broker_id=dukascopy-demo` + `broker_server=Dukascopy-demo-mt5-1`; manifest `{aggregator: 24610, broker: 876}` | provenance ya gharama kwenye attestation (T6) |
| DF-04 | `VERIFIED` | 2026-08-06 | **data halisi:** recorder imeandika siku 73 kwa kila symbol; `check-freshness OK` na `missing_days: []` kwa symbols zote 12 | — |
| DF-17 | `VERIFIED` | 2026-08-06 | **mashine ya PD:** `git add research` ilistage `README.md` **pekee** ingawa folda ina GB 31; `git check-ignore` inathibitisha sheria; G11/G12 tests | — |
| DF-18 | `VERIFIED` | 2026-08-06 | **data halisi:** backfill 2026-04-27 → 08-05 ilijaza siku 840 zilizokosekana kwa kutumia disk kama ukweli; kufeli 8 za ukingo zilirekebishwa kwa kurudia | — |
| RCE-01..13 | `IMPLEMENTED` | 2026-08-06 | `src/rce/{budget,cost,sizing,gate,engine}.py` · `tests/rce/` (39 tests). **Golden**: jedwali la bajeti §2 (safu 4) · mfano wa §6 (lots 0.16 / $34.88 / deviation 3pt) · modes 3 za swap + triple WED · gate checks 6 kwa mpangilio · §5b (module haina hali inayodumu) | namba halisi za broker kwenye `broker_costs.yaml` (commission); kuunganishwa na MT5 (T7) |
| DF-19 | `IMPLEMENTED` | 2026-08-06 | `scripts/{setup,catchup,record,status}.bat` + `env.example.bat`; lango G13 (`test_repo_guards.py`) | kuendeshwa kwa scripts kwenye mashine ya PD |
| RS-03 | `IMPLEMENTED` | 2026-08-07 | `src/data/session_calendar.py` + `audit.py`; kalenda inatoka kwenye DATA (hakuna orodha ya sikukuu ya mkono), matarajio kwa symbol **na siku ya wiki**; `calendar_vs_assumed.json` ikiwa na kalenda kwa **kila toleo la schema kando** (kazi ya 2 ya R0); `variant_comparison.json`; `provenance_comparison.json` (aggregator↔broker, §2.2 sharti 2); `threshold_study.json` | kukimbizwa kwenye L0 halisi (partitions 25,486) na PD kupitia siku zinazotofautiana |
| DF-05 | `IMPLEMENTED` | 2026-08-07 | `src/data/quality.py` (checks 7 za L0; ya 4 na ya 8 ziko L2) + `quality_report.json` kwa symbol/mwaka, **vizingiti vyote** vilivyotumika, na wigo wa miaka dhidi ya `min_years`; `check-l1` + `quality-stats`; tests 20 | `quality_report.json` ya L0 halisi + uamuzi wa PD kuhusu partitions zinazofeli |
| DF-06 | `IMPLEMENTED` | 2026-08-07 | `src/data/bars.py` + `audit.build_l2`: TF 7 kutoka TICKS, spread stats + **`n_m1_bars`** kwa kila bar, bar bila tick HAIANDIKWI, sort ni **stable** (duplicate timestamps zinabaki kwa mpangilio wa kufika); checks za L2: OHLC (§3 ya 4), `flat_bars` (§3 ya 8), `bar_gaps` (§3 ya 3); ujenzi kwa vipande unathibitishwa kutoa bars zile zile | L2 ya symbols 12 kujengwa + checks za L2 kupita kwenye data halisi |
| DF-07 | `IMPLEMENTED` | 2026-08-07 | `src/data/asof.py`; mfano wa §4.1 ni test (`test_asof_mfano_wa_spec`: D1 ya jana, H4 ya 08:00, M15 ya 09:45) + test juu ya L2 iliyoandikwa diski | matumizi kwenye L3 (T2) |
| DF-08 | `IMPLEMENTED` | 2026-08-07 | `src/data/sentinel.py` + **lango G1 kwenye CI** (`sentinel --synthetic`, inakimbia bila storage); inataja **jina la feature iliyovuja**, si "imefeli" tu | kuunganishwa na build halisi ya L3 (T2) |
| DF-14 | `IMPLEMENTED` | 2026-08-07 | `src/data/splits.py` + **lango G2 kwenye CI** (`splits`); tarehe zote kutoka `config/data.yaml`; `random_split: true` inakataliwa; purge inapandishwa juu (siku 2 kwa embargo ya bars 36) | kutumika na datasets halisi (T2) |

**T0 IMEFUNGWA (PD 2026-08-06).** L0 ni **mfululizo 2016-01-04 → 2026-08-05**: aggregator
(partitions 24,610, miaka 10.3) + broker (876, siku 73), zote zikiwa na SHA256 zilizothibitishwa
kwa `verify-l0`. Siku 4 zinazopishana (2026-04-27…04-30) ndizo malighafi ya ulinganisho wa
spread aggregator↔broker (kipimo cha R0).

**Yaliyogunduliwa T0 na kurekebishwa** (yote yalitokana na data halisi, si tests):
`hash-l0` iliyokuwa inasoma ticks bilioni 3.4 badala ya footer (saa 3 → sekunde 23) ·
unit ya epoch kwenye statistics (tarehe zingesomeka 1970) · timeout + ushauri wa `-10003` ·
`NO_CLOSED_DAYS` badala ya `OK` isiyopima chochote · `probe-history` iliyopima siku za kalenda
badala ya siku za trading · circuit breaker ya backfill · `broker_id`/`broker_server` ·
CRLF ya scripts za Windows.

**T1 — code imekamilika, kipimo cha data halisi kinasubiri (2026-08-07).** Modules zote sita
(`session_calendar`, `quality`, `bars`, `asof`, `sentinel`, `splits`) + `audit.py` inayoziendesha
juu ya mti mzima wa L0. Tests 165 zinapita; malango G1 na G2 sasa yanakimbia kila build.

**Yaliyogunduliwa T1 kabla ya data halisi** (tests za mfumo mzima, si za sheria moja moja):
partition ya **mwezi** ilikuwa inahukumiwa kama kipande kimoja — usiku kati ya sessions
ungehesabiwa `intrasession_gap` na mipaka ya session zingelinganishwa na siku ya kwanza pekee;
sasa checks 1/3/6 zinafanyika kwa **kila siku** · matarajio ya coverage na session yalikuwa ya
**symbols zote pamoja** — XAUUSD ingefeli kila siku kwa sababu haifanyi biashara saa za EURUSD;
sasa ni kwa kila symbol · `year=` ya Hive pekee ilitambulika, kwa hiyo ripoti nzima ingekuwa
`symbol/?` (data halisi ina folda ya mwaka isiyo ya Hive) · embargo ya bars 36 (saa 36) ilikatwa
chini hadi siku 1, ikiacha nusu ya purge bila kufanya kazi; sasa inapandishwa hadi siku 2.

**Maamuzi matatu ya §3 yanayohitaji sahihi ya PD** (yameandikwa kwenye spec, yanasubiri idhini):
1. **check 1 (coverage)** kwenye L0 inapima **dakika zenye quote** dhidi ya median ya siku kamili
   za symbol/mwezi. Kuhesabu ticks kungefanya kizingiti kisiwe na maana — idadi ya ticks kwa siku
   inatofautiana mara mbili-tatu kwa kawaida kabisa.
2. **check 4 (OHLC)** inafanyika **L2**, si L1: L0 ni ticks, na ticks hazina OHLC.
3. **check 6 (session)** — hatua ya **saa 1 kamili** inaandikwa kama DST na **haifelishi** siku.
   Vinginevyo tungetupa siku 24 nzuri kila mwaka (mabadiliko mawili ya saa × symbols).

**Kipimo cha kwanza kwenye data halisi (EURUSD + XAUUSD, partitions 2,767, 2026-08-07).**
Kalenda: siku 2,763 (full 2,745 · partial 18); **siku 0** zilizotarajiwa kukosa data (L0 ni
mfululizo kamili); siku 13 tulizodhani zimefungwa zina data (kalenda ya kudhaniwa ya
`calendar.py` ina makosa 13). Sentinel PASS, G2 PASS.

L1 ilifelisha 1,735/2,767 — na **sehemu kubwa ilikuwa kipimo kibaya, si data mbovu**:

| Sababu | Idadi | Uamuzi |
|---|---|---|
| `stale_feed` | 1,374 | **kosa la kipimo.** Kizingiti cha spec ni cha **bars** (`high == low`), nilikitumia kwa **ticks**. Dakika tulivu ya Asia ina ticks 40 zenye quote ile ile — si feed iliyoganda. Sasa: L0 inapima **muda** (`max_stale_seconds`), L2 inapima bars (`max_flat_bars`) |
| `low_coverage` | 647 | **kosa la kipimo — IJUMAA.** `quality-stats`: p1/p5 = `0.875` = `21/24`. Soko linafunga 21:00 Ijumaa; nilikuwa naipima kwa wastani wa Jumatatu–Alhamisi |
| `session_mismatch` | 548 | **kosa lile lile.** p90/p95/p99 = `180.0` dakika kamili = saa 3 za close ya Ijumaa. Kufeli 549/2,767 = 19.8% ≈ sehemu ya Ijumaa kwenye siku za trading (20%) |
| `bad_timestamps` | 16 | `--reason`: **zote ni duplicates (1–4), kurudi nyuma = 0**. MT5 inatoa quotes mbili kwenye µs moja — la lazima kitakwimu kwenye ticks bilioni 3.4, si kasoro. Sasa: kurudi nyuma = 0 daima; duplicate ≤ `max_duplicate_frac` |
| `intrasession_gap` | 14 | **matokeo halisi (0.5%).** Sita ni mapengo ya ~saa 14 (siku za sikukuu zilizosalia `full`); nne ni saa 1 haswa. Kizingiti kinabaki 3600s |
| `quote_violation` | 2 | **matokeo halisi** — `crossed=1361` na `crossed=228` kwenye EURUSD/2024. `crossed` na `zero_spread` sasa zinahesabiwa kando ili suluhisho lisiwe la kubahatisha |

Mgawanyo ndio uliotoa jibu, si nadharia: `session_match` haikuwa imetawanyika bali ilikuwa na
**rundo mbili** — p50 = `0.08` dakika na p90–p99 = `180.0` dakika kamili. Namba kamili kama hiyo
si kelele ya data; ni sheria ya soko. Vivyo hivyo `coverage` p1/p5 = `0.875` = `21/24` haswa.

Marekebisho: matarajio ya checks 1 na 6 sasa yanatoka kwa median ya **majirani wa siku ile ile ya
wiki**, kwa kila symbol, na **siku yenyewe haiingii** kwenye matarajio yake (vinginevyo siku
iliyoharibika ingejiwekea kizingiti chake). Tests mbili zinalinda hili:
`test_ijumaa_inapimwa_kwa_ijumaa_nyingine_si_kwa_wiki_nzima` na
`test_siku_haiwezi_kujiwekea_kizingiti_chake`.

Somo lililoandikwa kwenye spec §3: **vizingiti vinatoka kwenye mgawanyo wa data, si mezani.**
Amri `quality-stats` inasoma `quality_report.json` iliyoshaandikwa (bila kusoma parquet tena) na
kuonyesha, kwa kila ukaguzi, thamani zilivyotawanyika + **kizingiti gani kingefelisha ngapi**;
`--reason <sababu>` inaorodhesha partitions zilizofeli pamoja na `detail` yake. PD anachagua.

**Ukaguzi wa T1 dhidi ya prompt yake yenyewe (2026-08-07).** Kila kifungu cha prompt na cha
vigezo vya R0 (`RESEARCH_PLAN_R0.md` §R0) kimekaguliwa; mapungufu sita yaliyokutwa yamezibwa:

| Kilichokosekana | Kilipoandikwa | Kimezibwa na |
|---|---|---|
| `n_m1_bars` kwa kila bar | spec §4 + `bars.per_bar_stats` | `bars.build_bars` — dakika zenye quote ndani ya bar. `n_ticks` peke yake ingesema bar ya ticks 3,600 zilizojaa dakika 10 ni kamili |
| gaps za L2 (`max_gap_bars`) | §3 check 3 · R0 | `bars.check_bar_gaps` — bars zisizokuwepo **ndani ya siku**; usiku si pengo |
| **ulinganisho aggregator↔broker** | R0 · spec §2.2 sharti 2 | `compare-provenance` — spread p50/p95, ticks, dakika, kwa siku zinazopishana |
| kalenda kwa **kila toleo la schema kando** | R0 kazi ya 2 | `calendar_vs_assumed.json` → `by_variant` (symbols, wigo wa siku, session median) |
| `min_years` (miaka ≥ 10) | R0 | `quality_report.json` → `coverage_by_symbol.*.meets_min_years` |
| vizingiti **vyote** kwenye ripoti | prompt: "R0 dhidi ya vizingiti vya `data.yaml`" | `new_report` sasa inachukua block nzima ya `quality:`, si vitano vilivyochaguliwa |

**Kipimo cha pili (2026-08-07, baada ya marekebisho).** Kalenda: symbols zote 12, partitions
25,498, siku **3,297** (full 2,750 · partial 547). Siku 547 za `partial` = **Jumapili** za miaka
10.6 (~551): soko linafunguka jioni ya Jumapili (~22:00 UTC) na data yote inayo. Si hitilafu —
`compare_with_assumed` sasa inatenganisha `weekend_open` (Jumapili, inatarajiwa) na
`unexpected_active` (Jumamosi/sikukuu, **inahitaji maelezo**); bila kutenganisha, ripoti
ingeonyesha "hitilafu 547" wakati kuna sifuri, na Jumamosi moja ya kweli ingezama.
Siku **0** zilizotarajiwa kukosa data.

`check-l1` (EURUSD, partitions 400 za 2016–2017): **390/400 zimepita (97.5%)**, kutoka 37%.
`session_mismatch` = **0** (ilikuwa 548). Mgawanyo unathibitisha marekebisho:

| Ukaguzi | p50 | p99 | max | Kizingiti | Zinafeli |
|---|---|---|---|---|---|
| `coverage` | 1.0 | — (p1 = 0.9537) | — | 0.995 | 10 |
| `session_match` | 0.04 dk | 0.64 dk | 60.04 dk (DST) | 15 dk | **0** |
| `gaps` | 72 s | 233 s | 10,800 s | 3,600 s | 2 |
| `stale_feed` (mpya) | 89 s | 280 s | 10,800 s | 1,800 s | 2 |
| `monotonicity` · `quote_sanity` | 0 | 0 | 0 | 0 | **0** |

Kasoro moja ilijitokeza hapa: `quality-stats` ilisema `session_match` inafeli 3 wakati ripoti
yenyewe ina 0. Ilikuwa inahesabu upya kwa kizingiti (`> 15`) badala ya kusoma **jibu** la
ukaguzi — na `check_session_match` inapitisha hatua ya saa 1 (DST) kwa makusudi. Sasa
inahesabu kufeli kutoka kwenye jibu; ukaguzi usiofelisha chochote hauonyeshi chaguo za
vizingiti (`clock_drift` kwenye data ya kihistoria ilikuwa ikitoa kelele).

Pia `stale_feed` na `gaps` zilikuwa zikiripoti thamani ile ile (10,800.6) kwa tukio moja —
muda peke yake hauwezi kutofautisha **feed iliyoganda** (ticks zinakuja, quote haibadiliki) na
**pengo** (hakuna ticks kabisa), na suluhisho la kila moja ni tofauti. `stale_feed` sasa
inahesabu ticks zilizo ndani ya dirisha na kusema ni ipi.

**Kipimo cha tatu — DATA YOTE (2026-08-09).** `audit.bat` kamili: partitions **25,510**, siku
**35,025**, symbols 12, 2016-01-04 → 2026-08-07. Vipimo viwili vya kwanza vilikuwa vya sampuli;
hiki ndicho cha kweli, na kila namba hapa chini imepimwa, si kukisiwa.

| | kipimo cha 2 (2026-08-08) | kipimo cha 3 (2026-08-09) |
|---|---|---|
| siku zilizopita | 31,370 / 35,025 (89.6%) | **33,227 / 35,025 (94.9%)** |
| `low_coverage` | 3,342 | **687** |
| `session_mismatch` | 679 | 568 |
| `stale_feed` | 518 | 213 |
| `intrasession_gap` | 479 | 178 |
| `bad_timestamps` | 36 | 33 |
| `quote_violation` | 6 | 6 |
| `excluded_by_pd` | — | **936** |

Maamuzi mawili ya PD (DF-05 APPROVED, sahihi #3–#4) yalisababisha mabadiliko haya:
`min_coverage` 0.995 → 0.95, na `excluded_ranges` ya 2023 ya Toleo B. Kupungua kwa
`stale_feed`, `intrasession_gap` na `session_mismatch` **hakukuwa kwa kulegeza kizingiti chao** —
vizingiti vyao havijabadilika hata kimoja; siku zilezile za 2023 zilizokuwa zikifeli kwa sababu
kadhaa sasa zimeondolewa kwa uamuzi mmoja ulioandikwa. Hiyo ndiyo tofauti kati ya kuficha kasoro
na kuitaja: sababu moja badala ya nne, na sababu yenyewe iko kwenye config.

`excluded_by_pd` = 936, si 777 kama ilivyokadiriwa. Tofauti ni siku za Jumapili/nusu za 2023
(~52 kwa symbol) ambazo `symbol-profile` haizihesabu kwa sababu inaonyesha siku **kamili** pekee.
Kifungu kinafunika mwaka wa kalenda mzima, kwa hiyo namba ya 936 ndiyo sahihi. Uthibitisho kwamba
kutolewa nje ni sahihi kabisa: denominator ya `gaps` = 34,089 = 35,025 − 936 kamili.

**Vinavyobaki wazi baada ya kipimo hiki:**

1. **`clock_drift` haipimi chochote kwenye kumbukumbu ya kihistoria.** Inalinganisha tick ya
   mwisho na `now()`; kwenye faili ya 2016 hiyo ni −10.6 miaka, kwa hiyo p50 = −171,679,765 s.
   Haiwezi kufeli kimuundo. Sehemu yake yenye maana — `tz == UTC` — INAFANYA kazi na inapita
   34,089/34,089. Corruption ya tick ya baadaye bado inanaswa na `gaps`, `coverage` na
   ugawaji wa siku, kwa hiyo si pengo la ulinzi; ni jina linalodanganya na percentiles zisizo na
   maana. Kurekebisha kunahitaji `CHECK_SCHEMA_VERSION` kuongezwa → kipimo cha saa 8 kingine.
2. **Siku 1,594 (4.7%) hazihukumiwi kwa `coverage` wala `session_match`** — kalenda haina
   matarajio kwao (`expected == 0`, siku zisizo `full`). Zinapita kwa checks 6 kati ya 8.
3. `session_mismatch` 568, ikiongozwa na **XAUUSD ~21 kwa mwaka, kila mwaka**. p99 = 300.01 dk =
   **saa 5 kamili** — hatua ya saa kamili, si kuteleza. Idadi thabiti ya kila mwaka inaelekeza
   kwenye kalenda (sikukuu za COMEX / kufunga mapema), si kasoro ya data.
4. Jumamosi/sikukuu zenye ticks: **16**.

**Kipimo cha nne — cha mwisho (2026-08-10).** Vipengele vinne vya kipimo cha tatu vilikuwa vibaya,
vyote kwa upande wa **kitengo cha hukumu**, si data. Kila kimoja kilianikwa na namba isiyowezekana,
si na nadhani:

| Kilichoonekana | Kilichokuwa kimeharibika | Jibu |
|---|---|---|
| `session_mismatch` = 21 kwa mwaka, kila mwaka, kwa Toleo B pekee | Toleo B linakata mwezi saa **05:00 UTC**; tarehe 1 iko nusu kwenye kila faili. Mistari **miwili kwa tarehe ile ile**: `close ±1140` na `open ±300` — `1140 + 300 = 1440` | vipande vinaunganishwa kabla ya kuhukumiwa |
| `clock_drift` p50 = **−171,679,765 s** | Ilikuwa inalinganisha tick ya mwisho na `now()` — umri wa faili, si ubora. Haikuweza kufeli kimuundo | inapima tick iliyo nje ya siku yake. Sasa: `p1…p99 = 0.0`, max `0.0` |
| `coverage max` = **2.0084** | Ufunguo wa kuunganisha ulikuwa `(symbol, day)` bila provenance — aggregator na broker walichanganywa | provenance kwenye ufunguo → siku **51** zilirudi |
| `coverage max` = **2.0028** (bado) | Kujumlisha kunadhani vipande **havipishani**. Faili mbili zenye siku ile ile ni **nakala**, si nusu | muda wa kipande unatofautisha: vinavyofuatana vinajumlishwa, vinavyopishana vinachukua `max` → **1.2018** |

Matokeo ya mwisho: **33,440 / 34,781 siku (96.1%)** · `code_rev` `bbfcfdf` · `config_hash`
`sha256:8110cb5bd`.

| kufeli | siku | % |
|---|---|---|
| `excluded_by_pd` (uamuzi wa PD) | 912 | 2.62 |
| `low_coverage` | 250 | 0.72 |
| `stale_feed` | 213 | 0.61 |
| `intrasession_gap` | 178 | 0.51 |
| `session_mismatch` | 131 | 0.38 |
| `bad_timestamps` | 33 | 0.09 |
| `quote_violation` | 6 | 0.02 |

Hesabu inafungika kila upande: `35,025 − 244 = 34,781` (vipande vya siku vilivyounganishwa), na
`295 − 51 = 244` (vipande vya kweli baada ya kutoa nakala za provenance). `session_mismatch`
imeshuka **568 → 131** bila kizingiti chake kuguswa hata mara moja.

**Nakala: 1.** Siku **moja** pekee kati ya 34,781 ina data inayojirudia kwenye faili mbili. Hilo
lina athari moja inayojulikana: `build_l2` haiondoi nakala, kwa hiyo `n_ticks` ya siku hiyo ni
mara mbili (OHLC, `spread_*` na `n_m1_bars` hazibadiliki — nakala kamili ina median, max na
mean zile zile). Siku 1 kati ya 34,781 = **0.003%**; kujenga upya bars (~saa 5) kwa ajili yake
si biashara nzuri. Imeandikwa, haijafichwa.

**Kilichojifunzwa (LESSON, si kasoro).** Kila moja ya kasoro nne ilipita tests zote na kuonekana
tu kwenye data halisi, kwa sababu data ya majaribio ilikuwa **safi kupita kiasi**: precision moja,
faili zisizopishana, chanzo kimoja. Tests sasa zinabeba data chafu kwa makusudi (precision mbili
kwenye siku moja, faili zinazopishana, vyanzo viwili vya siku moja). Pia: ripoti inapigwa **chapa
ya toleo la code** na `code_rev`, kwa sababu ripoti ya code ya zamani inaonekana sawa kabisa na ya
mpya — hilo lilipoteza saa nane tarehe 2026-08-09.

**Swali la mwisho lililokuwa wazi, limejibiwa (2026-08-10).** Siku 16 zilizoripotiwa `INAHITAJI
MAELEZO` zilikuwa **zote 16** ni 25 Desemba (9) au 1 Januari (7). Soko la FX halifungwi siku hizo;
linabaki wazi likiwa jembamba. Dhana ya kalenda ndiyo ilikuwa mbaya, si data. Baada ya kutenganisha
`holiday_thin` na `unexpected_active`, swali halisi limepata jibu lake: **Jumamosi zenye ticks =
0.**

**HALI YA MWISHO YA R0 — vigezo vyote:**

| Kigezo cha §R0 | Namba | |
|---|---|---|
| siku zilizopita §3 | **33,440 / 34,781 (96.1%)** | — |
| miaka ≥ `min_years` (10) | ndogo kuliko zote **10.6** · zilizopungua 0 | PASS |
| siku zilizotarajiwa bila data | **0** | PASS |
| Jumamosi zenye ticks | **0** | PASS |
| sikukuu zenye ticks (25 Des / 1 Jan) | 16 — soko jembamba | — |
| Toleo A ↔ B: schema moja | **True** | PASS |
| spread broker ÷ aggregator | **1.0** kwa siku 5 | PASS |
| `clock_drift` | p1…p99 = **0.0**, max 0.0 | PASS |
| kufeli zote saba za §3 | ≤ 0.72% kila moja | PASS |

`vinavyohitaji uamuzi wako: 1` — na hicho ni `excluded_by_pd` (912), uamuzi wa PD mwenyewe
uliokwishasainiwa (#3). Hakuna kigezo cha R0 kilichobaki bila jibu.

`config_hash` `sha256:8110cb5bd` · `code_rev` `58e6f74` · ripoti `2026-08-10T21:18:02Z`.

**T1 imekamilika.** Sahihi ya exit imewekwa 2026-08-10 (DF-05/06/07/08/14, RS-03 → VERIFIED,
sahihi #5–#10; lango G14 PASS · vipengele VERIFIED 6).

---

### 3.6 T2 — SETUP-v1 imetunwa na kupimwa (2026-08-11)

**Kutuna kwa RATE, kabla ya labels (§4.3 sheria 2).** `--sweep` juu ya TRAIN+VAL yote:

| `min_atr_mult` | 1.0 | 1.5 | 2.0 | **2.5** | 3.0 |
|---|---|---|---|---|---|
| rate | 26.33% | 15.21% | 8.42% | **4.46%** | 2.32% |

1.0 haikuwa inachuja hata kidogo: bei inatembea ~2σ ndani ya bars 4 na ATR14 ni ~1.3σ, kwa hiyo
"msukumo wa 1 ATR" ni **wa kawaida**. Gate pekee inayomaanisha "kuna fursa" ilikuwa haina meno.
**2.5** inatua kwenye 5% ambayo bajeti nzima ya §0.1 ilijengwa juu yake.

**Kigezo ni scale-free — imepimwa, si kudhaniwa.** Kwa 2.5, symbols zote 12 ziko kati ya **3.9%
na 4.9%**: EURCHF (tulivu kabisa) na XAUUSD (ya wazimu) zinatoa namba ile ile. Namba zingetawanyika,
kigezo kingekuwa kinapima **bei**, si fursa — kasoro ile ile ya `quote_sanity` ya T1.

**Control 0.10 → 0.05.** Kichujio kilipofikia 4.46%, "10% ya bars zisizo setup" ilitoa control
56,471 dhidi ya setups 26,390 — mara mbili ya kinachopimwa. Nguvu ya ulinganisho inategemea kundi
**dogo**, kwa hiyo control ya ziada haikuwa inanunua chochote; ilikuwa inagharimu 68% ya kazi.

**KASORO ILIYOKUTWA KABLA YA SAHIHI: hukumu ya R0 haikuwa ikifika popote.** Hakuna faili lililokuwa
likisoma `quality_report.json` — wala `build_l2`, wala `detect_setups`, wala `bars.py`. Siku zote
zilizofeli §3 zilikuwa zinaingia kwenye decision points **kimya**, ikiwemo siku 912 zilizoondolewa
kwa sahihi ya PD (#3). Ushahidi ulikuwa kwenye output yenyewe: EURCHF eligible **49,598** — zaidi
ya EURUSD **49,393** — ingawa mwaka mzima wa 2023 ulikuwa umeondolewa. Siku nane za kazi ya T1
zilikuwa hazina athari yoyote.

Baada ya kuunganishwa (`load_excluded_days` + `detect_setups(excluded_days=…)`):

| | kabla | baada | zilizofeli §3 |
|---|---|---|---|
| EURCHF | 49,598 | **43,544** | 6,088 bars |
| GBPJPY | 49,648 | **43,812** | 5,886 bars |
| XAUUSD | 47,259 | **40,645** | 6,681 bars |
| EURUSD (Toleo A) | 49,393 | 49,027 | 368 bars |

~6,000 kwa kila symbol ya Toleo B = siku 259 × bars 24 — hasa mwaka wa 2023. **Rate ya pooled
inabaki 4.46%**: kichujio hakikubadilika, ni denominator iliyosafishwa.

Hukumu inapakwa **wakati wa kusoma**, si ndani ya L2: L2 ni artifact ya masaa 5 na vizingiti vya §3
vimebadilika mara mbili tayari. Sera ya NaN ya §3 inaruhusu — bar ya siku iliyofeli haitumiki kama
decision point, lakini inabaki kama historia (ATR haitobolewi shimo).

**Hali ya mwisho:** setups **25,374** · control **27,089** · jumla ya decision points **52,463** ·
holdout imetengwa **7,366** · `config_hash` `sha256:4ce1768`.

---

### 3.7 T2 — L4 imejengwa; na kile build ya kwanza haikuweza kupima (2026-08-12)

**Build ya kwanza (toleo 1):** points **52,321** · cells **1,308,025** (= 52,321 × 25, sawasawa) ·
timeout **2.8%** · tie-break **0.00%** · **2,215s (dakika 37)**. `bila ticks` = 0 kwa symbol zote.
EURCHF/GBPJPY/XAUUSD zina points **0** kwa 2023 — hukumu ya R0 imeshikilia mwanzo hadi mwisho.

**Timeout 2.8%, si 35%.** Hii ni namba muhimu zaidi kuliko inavyoonekana: §5.5 inaweka kikomo 0.35,
na mapitio ya mpango yalikuwa yameonya kwamba **RS-04 yenyewe inakufa** timeout ikikaribia 35% —
`p_tp/(p_tp+p_sl)` ingekuwa ikilinganisha sehemu ndogo mno ya sampuli. Kwa 2.8%, ukaguzi wa jiometri
unabaki na maana.

**Tie-break 0.00% — na sababu si "haijatokea", ni "HAIWEZI kutokea".** Nilikuwa nimetangaza kwamba
ninaangalia namba mbili: timeout na tie-break. Ya pili ilipokuja sifuri, nilipima kwa nini:
kwa BUY, SL **na** TP zote zinapimwa kwa **bid** (`sl_idx = bid ≤ entry − sl·ATR`,
`tp_idx = bid ≥ entry + tp·ATR`). Tick moja haiwezi kuwa `≤ X` na `≥ Y` wakati `X < Y`. Jaribio la
gap 400 × cells 25 × pande 2 lilitoa **0 kati ya 20,000**. §5.2 yenyewe ina hoja hii ndani yake
("Tick moja haiwezi kugusa zote mbili"). Kwa hiyo: sheria iliyosainiwa **haijawahi kuguswa na
data**, na haitaguswa kwa muundo huu wa grid. Inabaki kwa grid zijazo zinazopima pande mbili
tofauti. R1 inaandika hili kama `note`, si kama PASS kimya — sheria isiyoweza kuwaka ikiripotiwa
"0.00% ✓" ingesomeka kama ushahidi wa usalama, si kama ukimya.

**Kilichokosekana: vipimo vitatu vya R1 havikuwa vimerekodiwa.** T2 inadai (safu ya 108 + DF-21 +
K1-07) mid-dhidi-ya-trade quantile, fill/slippage bootstrap, na M1-dhidi-ya-tick disagreement.
Toleo 1 la L4 halikuwa na malighafi ya hata moja — na malighafi hiyo **haipatikani baada ya
build**: ingehitaji kupita kwenye ticks za miaka 8 mara ya pili. Kwa hiyo toleo **2** (§5.6 ya
standard) linarekodi `touch_past_pips`, `terminal_trade`/`quantile_y_trade`, na ukaguzi wa M1
kwa sampuli ya hash — vyote pale ticks zilipo tayari kwenye kumbukumbu. Gharama: **build moja
zaidi ya dakika ~40**. Mbadala ulikuwa kupitisha T2 na "haijapimwa" mara tatu.

### 3.8 T2 — R1 imekimbia: HUKUMU PASS (2026-08-13)

Build ya toleo 2: points **52,321** · cells **1,308,025** · timeout **2.79%** · tie-break **0** ·
M1≠tick **0.01%** · **48,562s (saa 13.5)**.

> **Makadirio yangu ya muda yalikuwa mabaya mara 22** (nilisema "dakika ~40" kwa sababu build ya
> toleo 1 ilikuwa 2,215s). Ukaguzi wa M1 ni 5% ya points na unagharimu kama `resolve_arrays`
> yenyewe — hauwezi kuelezea 22×. Sababu haijathibitishwa; `partitions_read` ndani ya
> `label_build.json` ndiyo inayoweza kuisuluhisha. Haiathiri matokeo, inaathiri makadirio yangu.

**Vigezo vigumu vyote vimepita:** cell ndogo kuliko zote **25,314** (kikomo 200) · timeout 2.79%
(< 0.35) · tie-break 0 (< 1%) · G2 safi.

**Jiometri (RS-04) inashikilia, na inashindwa kwa MUUNDO unaoeleweka.** Cells 23/25 ziko chini ya
`sl/(sl+tp)`, na ukubwa wa tofauti **unashuka SL inapopanuka**:

| `sl_atr` | 0.50 | 0.75 | 1.00 | 1.50 | 2.00 |
|---|---|---|---|---|---|
| `diff` kwa `tp=1.0` | −0.042 | −0.033 | −0.025 | −0.009 | −0.001 |

Hii ndiyo saini ya **spread**: spread ni umbali usiobadilika wa bei, kwa hiyo ni sehemu kubwa ya
SL nyembamba na ndogo ya SL pana. Kwa `sl=2.0`, `tp∈{1.5, 2.0}` zinatoa `+0.003`/`+0.005` (z ≈ 1)
— hazitofautiani na jiometri kabisa. Kama tofauti ingekuwa ya kudumu bila kujali SL, ingekuwa
drift au kasoro; hii si hivyo.

**Isipokuwa moja iliyo halali:** safu ya `tp=3.0` ina tofauti KUBWA kuliko majirani zake kwa kila
SL (mfano `sl=2.0`: `tp=2.0` → +0.005, lakini `tp=3.0` → −0.023). Sababu ni **timeout**: kwa
`tp=3.0` timeout inafika 22.7%, na zilizokatwa na horizon si sampuli ya nasibu — ni zile
zilizokuwa zikielekea TP ya mbali. Ukaguzi wa jiometri ni safi zaidi pale timeout ni ndogo.

**`z` isisomwe kama uwezekano.** `z = −19.9` kwa cell moja haina maana ya "hakika mara 19";
`n = 25,314` inafanya upendeleo mdogo kabisa uonekane sigma nyingi. Ukubwa wa `diff` ndio
unaosomwa, si `z`.

**Utulivu:** p_tp 0.409–0.428 kwa 2016–2023 (upana 0.019 — imara). **2024 ni 0.379** lakini ni
miezi mitatu tu (cells 19,125 dhidi ya ~80,000 kwa mwaka mzima), kwa hiyo si ushahidi wa
kubadilika kwa soko bado.

**SETUP-v1 INAFANYA KAZI — na hii ndiyo namba iliyokuwa ikisubiriwa:**

| | setup | control | tofauti |
|---|---|---|---|
| p_tp | 0.4173 | 0.3923 | **+0.0251** |
| E[R] gross | −0.0505 R | −0.1142 R | **+0.0638 R** |
| ATR p50 | 16.1 pips | 14.3 pips | +1.8 |

Kichujio hakichagui trades chache tu — kinachagua **bora**. Lakini `z = +28.8` **isisomwe kama
ilivyo**: cells 25 za point moja si huru, na points zinapishana kwa wakati; effective N ni ndogo
kuliko 632,850 kwa mbali (hoja ile ile ya §3.6 kipengele 5). Mwelekeo na ukubwa ndio ushahidi.
Kumbuka pia ATR p50 16.1 dhidi ya 14.3: sehemu ya makali inaweza kuwa **uteuzi wa volatility**,
si utabiri — features za T3 ndizo zitakazoweza kuvitenganisha.

**E[R] gross ni hasi kila mahali** (setups −0.0505 R). Hii ni sahihi na inatarajiwa: entry bila
model inalipa spread. Ndiyo **kiwango ambacho model lazima ikizidi** — si tokeo baya, ni mstari
wa kuanzia ulioandikwa kwa namba.

**L-C: cap ya stop ya RCE inagongana na data.** `slippage_cap_pips.stop = 0.3`, lakini kati ya
touch 757,424 za SL, **76.06% pekee** ziko ndani ya cap (p50 0.12 · p90 1.06 · p99 14.59 ·
max 2,503.7 pips). Ni matokeo ya T7, si ya sasa: **RCE haiguswi**. Lakini inaandikwa hapa kwa
sababu backtest inayodhani cap ya 0.3 inashikilia kila mara inadhani kitu ambacho feed ya
kihistoria inakipinga robo ya muda.

**M1 dhidi ya tick: 9 kati ya 66,650 (0.01%).** Sheria ya §5 ("bar haisemi ipi iligusa kwanza")
ni **kweli lakini karibu haina athari kwa grid hii** — SL ya 0.5 ATR ni pana ikilinganishwa na
range ya dakika moja. Ingekuwa na maana kwa barriers nyembamba. Faida ya kujua hili: ticks
zikija kuwa kizuizi, M1 ni mbadala unaotetereka kwa 0.01%, si dhana.

**Quantile MID dhidi ya trade — baada ya kurekebishwa, na jibu si dogo:**

| symbol | spread | ATR | `shift` (ATR) | pooled (kosa la awali) |
|---|---|---|---|---|
| XAUUSD | 35.0p | 356.6p | **0.1049** | +0.0029 |
| EURCHF | 1.0p | 9.8p | **0.1043** | −0.0035 |
| NZDUSD | 1.1p | 12.3p | 0.0905 | −0.0002 |
| GBPJPY | 1.6p | 26.0p | 0.0633 | −0.0003 |
| EURUSD | 0.3p | 14.4p | **0.0209** | −0.0009 |

`shift` = `direction × (mid − trade)`. Kila safu inalingana na `(spread_in + spread_out) ÷ 2 ÷ ATR`
iliyohesabiwa kwa **kujitegemea** hadi tarakimu ya nne — vipimo viwili huru vinavyokubaliana.

**Uamuzi wa §5.1 unashikilia, na sasa una uzito.** Gharama si 0.003 ATR bali **0.02–0.10 ATR**.
Kuiweka pia kwenye L-A kungekuwa kuihesabu mara tatu kwa kiasi kinachoonekana, si kwa kiasi cha
kupuuzwa.

**Spec ilitaja symbols zisizo sahihi.** §5.1 inasema R1 ipime "symbols pana (XAUUSD, GBPJPY)".
XAUUSD ndiyo ya juu (0.1049) — lakini GBPJPY ni ya **kati** (0.0633), na inayoshindana na XAUUSD
ni **EURCHF** (0.1043), pair "tulivu" yenye spread ya 1.0p tu. Kinachohesabu si spread kwa pips
bali **spread ÷ ATR ya symbol yenyewe**: EURCHF ina ATR ya 9.8p pekee. Somo lile lile la §6.1
sheria 1 na la sweep ya `min_atr_mult` — kigezo cha pips kinapima **bei**, cha ATR kinapima
**fursa**.

**Kigezo kilichokuwa hakiwezi kufeli (kimerekebishwa 2026-08-13).** `min_labels_per_cell` pooled
ilionyesha 25,314 kwa **kila cell** — si bahati, ni muundo: kila decision point inapata cells zote
25, kwa hiyo cells zote zina idadi ile ile daima. Kigezo kinachotoa jibu lile lile bila kujali
data ni kilekile cha `clock_drift` 0/34,089 cha T1. Kigezo chenye meno ni cha **cell × symbol ×
fold** — mahali mafunzo yanapofanyika. Symbol yenye labels 25,314 kwa jumla lakini 40 ndani ya
fold moja haiwezi kufundishwa humo, na pooled haitasema neno. R1 sasa inapima na kufeli hapo.

**Kasoro kwenye kipimo changu (imerekebishwa, 2026-08-13).** Quantile mid-dhidi-ya-trade
ilikuwa ikipimwa **bila ishara ya trade**. `quantile_y_trade` haina mwelekeo: BUY (nunua kwa ask,
funga kwa bid) iko chini ya mid; SELL iko juu kwa kiasi kile kile. Wastani wa pamoja unafuta
gharama nzima — ndiyo maana XAUUSD yenye spread ya pips 35 ilionyesha 0.0029 pekee. Namba hiyo
ingesomeka kama "uamuzi wa §5.1 hauna athari", wakati ukweli ni athari sawa pande zote mbili
zikielekeana. Kipimo sasa ni `direction × (mid − trade)`, na kinalinganishwa na
`(spread_in + spread_out) ÷ 2 ÷ ATR` iliyopimwa kwa kujitegemea — zikitofautiana, mmoja ni kosa.
Hakuna ujenzi upya: `r1-summary` peke yake inatosha.

**R1 (`r1-summary`)** ni ripoti ya vigezo vyote kwenye jedwali moja, kama `r0-summary` ya T1:
jiometri kwa cell (`p_tp` BILA timeout dhidi ya `sl/(sl+tp)`, na `z` yake), utulivu kwa miaka,
setup-dhidi-ya-control (`z` ya tofauti), quantile mid-vs-trade kwa symbol, fill/slippage dhidi ya
`slippage_cap_pips` ya RCE, buckets za L-D kwa mkunjo wa gharama, na M1-vs-tick. Inafeli — si
kuonya — pale `min_labels_per_cell < 200`, timeout > 0.35, tie-break > 1%, au point yoyote ya
holdout ikigusa takwimu (G2 inasimamisha ripoti **kabla** ya kuhesabu chochote).

**MAPITIO YA USHAURI WA NJE (PD 2026-08-07 — "nimekubali, fanya maamuzi").** Ushauri wa nje
ulileta mapengo matano; uchambuzi huru uliyathibitisha manne, ukapima moja upya, na kuongeza
mawili ambayo hayakuonwa. Maamuzi (yote yameandikwa kwenye spec + config, vipengele DF-20,
DF-21, RS-15, RS-16, RS-17):

| # | Uamuzi | Ulikubaliana na ushauri? |
|---|---|---|
| 1 | Sheria ya setup: §4.3 mpya + config §setups + **control sample 10%** | Ndiyo — na zaidi: filter ni model ya hatua ya kwanza, kwa hiyo inapimwa (control), si kuandikwa tu |
| 2 | Pretraining: **walk-forward kwa kila fold** + GBM baseline protocol ile ile | Ndiyo kwa tatizo; suluhisho tofauti — si "pretrain 5 huru" wala "kubali upendeleo", bali walk-forward + warm-start (safi NA nafuu) |
| 3 | Tie-break: **SL kwanza**; timestamp moja = mpangilio wa kufika (stable sort ilishawekwa) | Ndiyo; nusu ya kesi ilikuwa imekwisha tatuliwa — na R1 inapima mzunguko, si sheria tu |
| 4 | L-A entry: **MID**, si trade-price | **Hapana** — ushauri ulisema ask/bid; mid ni sahihi kwa S1 (L-A inapendekeza, haihukumu; spread inaingia path na RCE, si mara 3). R1 inapima tofauti kwa namba |
| 5 | Effective N: block bootstrap + uzito kwa decision point + `ic_min` kama floor | Ndiyo kwa hitimisho; chanzo kikuu ni kingine — si kupishana kwa wakati (~17%) bali **symbols 12 zisizo huru** (effective N ~9k → 0.02 ni ~2σ) |
| +A | R6 inaripoti sehemu ya signals zinazochukulika chini ya bajeti ya RCE | Halikuonwa na ushauri — positions zinapishana, EV ya mfumo ni ya zinazochukulika |
| +B | Sanity ya R1 kwa fomula `p_tp/(p_tp+p_sl)`, si `p_tp_first` | Halikuonwa — kwa timeout 35%, fomula ya awali ingeonyesha "hitilafu" kila mara |

Yote ni ya **T2+**; T1 haiguswi na hata moja. RCE haijaguswa.

**TRACK E:** `src/rce/` imejengwa kwa spec ILE ILE (haijaguswa). Kilichobaki kwa `VERIFIED`:
namba halisi za Dukascopy kwenye `config/broker_costs.yaml` (commission round-turn), na
`SymbolSpec` kusomwa moja kwa moja kutoka MT5 (volume_min/step/max, swap_*, contract_size,
point) badala ya kuandikwa kwa mkono — kazi ya T7 (integration).

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
G11 NO DATA IN GIT   parquet / `research/data/` / faili > 5MB iliyo-track → FAIL (DF-17)
G12 ENGINE ⊥ RESEARCH `src/` (engine) ikimport `research.src` → FAIL     (DF-17)
G13 NO SECRETS       `*.local.bat` iliyo-track / template yenye thamani → FAIL (DF-19)
G14 SAHIHI           sahihi isiyo ya PD · ushahidi uliobadilika · ID isiyopo (§0.1)
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
