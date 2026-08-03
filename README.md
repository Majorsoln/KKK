# ELITEFX ENGINE — mfumo wa UZALISHAJI (production)

> Folda hii ni **mfumo unaotrade**, si maabara ya utafiti. Utafiti (mizunguko, backtests, lessons,
> golden harness) unabaki nje ya folda hii. Faili la kwanza: `docs/RISK_COST_ENGINE.md` (PD 2026-08-02).

## IDARA (Doctrine: docs/SYSTEM_ARCHITECTURE_V3.md)
| # | Idara | Iko wapi | Hali |
|---|---|---|---|
| 1+2 | **RISK & COST ENGINE (RCE)** | `engine/src/rce/` | **inajengwa** — spec tayari |
| 3 | STRATEGY MODELS | `src/research/` (utafiti) → `config/models.yaml` | ipo |
| 4 | OPEN-POSITION MGMT | `engine/src/opm/` | haijaanza (RL inakaa hapa) |
| — | CONDUIT BRIDGE | `src/research/live_brain.py`, `mql5/` | itahamia hapa |

## SHERIA MBILI ZISIZOVUNJWA (mpaka wa utafiti ↔ uzalishaji)
1. **Engine HAIRUDII code ya golden.** `episodes`, bootstrap, statistics — engine **inatumia namba
   zilizothibitishwa** (EV, ratio, pairs), hairudii hesabu. Zikirudiwa, siku moja zitatofautiana na
   utafiti → live haitalingana na kilichothibitishwa (GIGO).
2. **Mtiririko ni upande MMOJA:** utafiti → uzalishaji (models + namba). Engine inarudisha **data ya
   matokeo tu** (fills, slippage halisi, gharama halisi) — malighafi ya Steward na SLIPPAGE MODEL.

## MUUNDO
```
engine/
├── docs/RISK_COST_ENGINE.md   spec kamili (bajeti · gharama · lots · gate)
├── config/risk.yaml           vigezo VYOTE (PD anahariri, hakuna code)
├── src/rce/                   budget · cost · sizing · gate
├── src/opm/                   (baadaye) open-position management
└── tests/
```

## CONFIG
`engine/config/risk.yaml` ndicho **chanzo cha ukweli** cha vigezo vya risk/cost vya engine.
`config/ftmo_config.yaml` (ya zamani) inahudumia njia ya `live_brain` hadi uhamiaji ukamilike —
kisha itastaafishwa. **Vigezo visiwe sehemu mbili baada ya uhamiaji.**
