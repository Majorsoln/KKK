# RESEARCH STORAGE — ELITEFX

Muundo huu umewekwa na `src/data/research_layout.py` kwa spec §9 ya
`docs/DATA_FEATURE_STANDARD.md`. Repo ya engine inapokea **models + namba
zilizothibitishwa** pekee (sheria 2 ya README ya engine).

Mzizi: `C:\Users\Hp\project\elitefx-engine\research`

## Folda

| Folda | Yaliyomo |
|---|---|
| `data/L0_raw/` | ticks bid+ask ghafi — immutable, append-only, SHA256 kwa kila partition (§2) |
| `data/L1_clean/` | UTC, gaps, duplicates, sanity + quality_report.json (§3) |
| `data/L2_bars/` | TF 7 zilizojengwa kutoka ticks + spread stats kwa kila bar (§4) |
| `data/L3_features/` | features kwa dataset_id, as-of closed bar pekee (§6) |
| `data/L4_labels/` | labels zilizotatuliwa kwa path ya ticks (§5) |
| `data/L5_datasets/` | train/validation/holdout + manifest.json (§7, §8) |
| `reports/quality/` | R0 — quality_report.json, kalenda ya sessions, ulinganisho A↔B |
| `reports/screening/` | R2/R3 — IC/MI, permutation, FDR, clusters |
| `reports/ablation/` | R7 — jedwali la ablation ya familia na TF |
| `reports/calibration/` | R5 — reliability curves, ECE, Brier skill |
| `src/` | code ya utafiti (haiingii repo ya engine — sheria 2 ya README) |

## Sheria zisizovunjwa

1. **L0 haibadilishwi.** Partition ikishaandikwa na kuhashiwa, badiliko lolote
   ni ukiukaji wa DF-01. Data mpya = partition MPYA (append-only).
2. **Provenance inaandikwa.** `provenance=broker` kwa feed ya broker,
   `provenance=aggregator` kwa data ya kihistoria (spec §2.2).
3. **Kila dataset ina `dataset_id` + manifest** (spec §8). Namba isiyo na
   `dataset_id` hairudi kwenye engine.
4. **HOLDOUT (2024-04-01 → 2026-04-30) na RESERVE (2026-05-01+)** zinakaa
   kwenye eneo lenye ruhusa ya kusoma kwa job ya R8 pekee (§4.3 ya
   IMPLEMENTATION_PLAN, lango G2). Utekelezaji wa ruhusa hizo ni kazi ya T1.
