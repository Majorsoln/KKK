# ELITEFX — MGAWANYO WA DATA (TRAIN / VALIDATION / HOLDOUT) — PD 2026-08-04

> **Hadhi:** utekelezaji rasmi wa §7 ya `DATA_FEATURE_STANDARD.md` kwa data halisi ya ticks
> (2016-01-04 → 2026-04-30, symbols 12, ticks ~bilioni 3.4). Mipaka ya tarehe iko kwenye
> `config/data.yaml` (§splits) — hicho ndicho chanzo cha ukweli; hati hii ni maelezo.

---

## 1. MGAWANYO KWA MUHTASARI

```
2016-01-04 ──────────────────────────────► 2024-03-31 │ 2024-04-01 ──► 2026-04-30 │ 2026-05-01+
            TRAIN + VALIDATION (miezi 99, ~80%)        │   HOLDOUT (miezi 25, ~20%) │  RESERVE
            purged 5-fold CV + embargo                 │   INAFUNGULIWA R8 PEKEE    │  mzunguko ujao
```

| Sehemu | Kipindi | Miezi | Labels (makadirio, pooled 12) | Inatumika |
|---|---|---|---|---|
| TRAIN+VAL | 2016-01-04 → 2024-03-31 | 99 | ~30,800 | R1–R7 (purged CV) |
| HOLDOUT | 2024-04-01 → 2026-04-30 | 25 | ~7,800 | **R8 pekee, mara moja** |
| RESERVE | 2026-05-01 na kuendelea | inakua | — | mzunguko ujao / shadow; haionwi sasa |

Makadirio: setups ≈5% ya H1 bars ≈ labels 26/symbol/mwezi. Kwa symbols 7 za config ya sasa,
punguza kwa ~40% — mgawanyo wa tarehe haubadiliki (split ni ya wakati, si ya symbol).

## 2. FOLDS TANO ZA TRAIN+VALIDATION (blocks za muda, zinafuatana)

| Fold | Kipindi | Miezi | Regimes kuu ndani yake |
|---|---|---|---|
| F1 | 2016-01-04 → 2017-08-31 | 20 | Brexit vote, USD range |
| F2 | 2017-09-01 → 2019-04-30 | 20 | vol spike 2018, trade war |
| F3 | 2019-05-01 → 2020-12-31 | 20 | COVID crash + recovery (vol extremes) |
| F4 | 2021-01-01 → 2022-08-31 | 20 | inflation, mwanzo wa rate hikes, USD trend |
| F5 | 2022-09-01 → 2024-03-31 | 19 | kilele cha hikes, JPY intervention, disinflation |

- **Pooled:** symbols ZOTE ziko kwenye fold ile ile ya wakati (§7 ya standard).
- **Purge:** label yoyote ya train ambayo horizon yake (bars 24 za H1) inaingia kwenye fold ya
  validation inaondolewa.
- **Embargo:** bars 36 za H1 (= horizon × 1.5) pande zote za fold ya validation. Inahesabiwa kwa
  **bars**, si saa za ukuta (weekend si embargo).
- **Walk-forward anchored** (uthibitisho wa pili): train inaanzia F1 na kupanuka; validation ni
  block inayofuata. Folds zile zile zinatumika — hakuna mgawanyo mpya.

## 3. SHERIA ZA KUGUSA (nani anaruhusiwa wapi)

| Kazi | TRAIN+VAL | HOLDOUT (kabla ya R8) |
|---|---|---|
| L0–L2 build, hashes, quality checks (R0) | ✔ | ✔ — ukaguzi wa ubora si modeling; hakuna outcome inayoangaliwa |
| Kalenda ya sessions | ✔ | ✔ |
| L4 labels — **kuzihesabu** (build) | ✔ | ✔ (zinahifadhiwa, hazitazamwi) |
| L4 labels — **takwimu/base rates** (R1) | ✔ | ✘ |
| Screening, redundancy, baselines, models, calibration, EV (R2–R7) | ✔ | ✘ |
| Isotonic calibration | validation folds PEKEE | ✘ |
| Ripoti/plots zozote zenye outcomes | ✔ | ✘ |
| R8 attestation | — | ✔ **mara moja** |

**Holdout iliyoonekana imekufa** (§R8 ya `RESEARCH_PLAN_R0.md`). Mzunguko ujao unatumia RESERVE
(2026-05+, inakua kila mwezi) kama holdout mpya — ndiyo maana haionwi sasa.

## 4. KWA NINI MIPAKA IKO HAPA

1. **Holdout = miezi 25 ya karibuni zaidi.** Ndiyo inayofanana zaidi na hali ya live —
   attestation inapima kile kitakachokutana na soko la kesho, si la 2017.
2. **80/20 kwa mfuatano wa wakati** = `holdout_frac: 0.2` iliyokuwepo kwenye config; hakuna
   kigezo kipya, ni tarehe za kigezo kilichopo.
3. **Kila fold ina regime tofauti** (jedwali §2) — IC_stability na calibration-kwa-kundi
   vinapimwa dhidi ya hali halisi tofauti, si dhidi ya mwaka mmoja uliojirudia.
4. **Mwisho wa pamoja 2026-04-30:** Toleo A inaishia 2026-04-30, Toleo B 2026-05-01 —
   tunakata zote 2026-04-30 ili symbols zote ziwe na dirisha moja.

## 5. NJE YA WIGO
Ubora wa data na normalization ya schema mbili (Toleo A/B) → R0 ya `RESEARCH_PLAN_R0.md`.
Provenance ya broker (data ya aggregator vs feed ya live) → uamuzi wa PD unasubiriwa; mgawanyo
huu hautegemei uamuzi huo.
