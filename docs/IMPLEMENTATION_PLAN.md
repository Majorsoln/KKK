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

| Term | Wiki (mak.) | Kazi | Exit criteria (hakuna mjadala) |
|---|---|---|---|
| **T0 — MSINGI** | 1–2 | recorder wa feed ya broker (huanza, hauishii); normalization A/B → schema moja; L0 hashes; muundo wa research repo | recorder unarekodi kila siku ya trading; symbols 12 zinasomeka kwa schema moja; SHA256 za partitions zote zimehifadhiwa |
| **T1 — R0** | 2 | L1 (checks 8) + `quality_report.json`; kalenda ya sessions; L2 (TF 7 kutoka ticks + spread stats); sentinel ya uvujaji kwenye CI | R0 PASS kwa vizingiti vya `data.yaml`; sentinel inakimbia na kufelisha build ikigundua uvujaji; ulinganisho A↔B umeripotiwa |
| **T2 — R1** | 2–3 | L4: grid labels kwa path ya ticks + terminal returns za timeout; fill bootstrap; quality buckets | R1 PASS (base rates + jiometri + utulivu); `min_labels_per_cell ≥ 200`; M1-vs-tick disagreement imeripotiwa |
| **T3 — R2+R3** | 2–3 | feature cards F1–F7 (kabla ya code); L3 + screening (IC/MI + permutation + **FDR**); redundancy clustering | kila feature ina card; jedwali la screening na FDR limetoka; set ya mwisho ≤ bajeti (`labels ÷ 50`) |
| **T4 — R4+R5** | 2 | baselines B0/B1/B2; **GO/NO-GO**; calibration (isotonic kwenye validation folds) | B1/B2 > B0 kwa CI isiyogusa sifuri — AU **SIMAMA na rudi T2/T3**; ECE ≤ 0.05, Brier skill > 0 |
| **T5 — R6+R7** | 2–3 | EV ya madarasa 3, fill-aware, cost stress ×1.5; ablation ya familia + TF; wagombea wa Track P wanaingia hapa kupitia lango la R4 | EV_R net > baseline na inabaki chanya kwa cost ×1.5; jedwali la ablation limetoka |
| **T6 — R8** | 1 | PD anafungua HOLDOUT **mara moja**; attestation | vigezo vya `data.yaml §holdout`; attestation yenye `dataset_id` + config_hash imesainiwa — AU mzunguko unaisha LESSON |
| **T7 — SHADOW→LIVE** | 4+ | integration (KAIROS→RCE→MT5); shadow/demo; kisha live + R9 monitoring (haina mwisho) | mnyororo mzima unafanya kazi demo; vigezo vya R9 vinapimwa live; fills za broker zinajaza calibration ya P(fill) |
| **TRACK E** | sambamba T1–T5 | `src/rce/`: budget, cost, lots, gate — kwa spec ILE ILE bila kuigusa | tests zote za RCE-* (§3.1) zinapita, ikiwemo golden test ya §6 ya spec |
| **TRACK P** | sambamba T3–T5 | pretraining ya encoder (§5A ya KAIROS-1) kwenye TRAIN+VAL pekee | corpus inaishia 2024-03-31 (CI inathibitisha); ripoti ya malengo; wagombea wanapimwa T5 |

**Makadirio ya jumla hadi attestation: wiki ~14–18.** Shadow ≥ wiki 4 baada ya hapo. Tarehe ni
makadirio; **vigezo ndivyo sheria.**

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

**Jumla: vipengele 56.** `100% = 56/56 VERIFIED` (au LESSON iliyoandikwa pale eneo lilipofeli
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
