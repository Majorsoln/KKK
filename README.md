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
├── docs/RISK_COST_ENGINE.md       spec kamili (bajeti · gharama · lots · gate) — HAIGUSWI
├── docs/DOCTRINE_V2.md            doctrine hai: injini ya kugundua strategy kiotomatiki
├── docs/SETUP.md                  runbook: kusimamisha mfumo kwenye server yoyote
├── config/risk.yaml               vigezo VYOTE vya risk/cost (PD anahariri, hakuna code)
├── config/data.yaml               vigezo VYOTE vya data/features/utafiti + storage/recorder
├── config/broker_costs.yaml       commission round-turn + usiku za strategy (PD)
├── src/data/                      L0–L3: recorder · normalization · bars · features · labels
├── src/rce/                       budget · cost · sizing · gate · engine (Track E)
├── src/opm/                       (baadaye) open-position management
└── tests/
```

## TABAKA LA DATA (T0 — `src/data/`)
```
python -m src.data.cli init-research      # §9 — muundo wa research storage (nje ya repo)
python -m src.data.cli record             # DF-04 — recorder wa feed ya broker (MT5)
python -m src.data.cli backfill --dry-run # DF-03 — siku zilizorukwa (kalenda dhidi ya disk)
python -m src.data.cli hash-l0            # DF-01 — SHA256 ya partitions ZOTE + manifest
python -m src.data.cli verify-l0          # DF-01 — lango la CI (hash check kila build)
python -m src.data.cli check-freshness    # DF-04 — ONYO: siku ya trading bila data mpya
python -m src.data.cli check-mt5          # mazingira ya MT5: server, broker_id, symbols
```
`research/` iko **ndani ya repo** (§9, PD 2026-08-04): `reports/` na `src/` zinapushwa;
**`research/data/` haipushwi kamwe** (.gitignore + lango G11). `ELITEFX_RESEARCH_ROOT` inaelekeza
mzizi wa research — badilisha env hiyo pekee ukitaka data ihamie diski nyingine.
Sifa za MT5 zinatoka environment, si config wala code.

## KUENDESHA (`docs/SETUP.md`)
```
scripts\setup.bat          # MARA MOJA: venv + deps + tests + research + check-mt5
scripts\catchup.bat        # KILA SIKU: backfill -> hash-l0 -> verify-l0 -> freshness
scripts\record.bat         # recorder inayoendelea (Ctrl+C kusimamisha)
scripts\status.bat         # ukaguzi wa haraka (haugusi MT5)
```
`catchup` na `record` **hazikimbii pamoja** — MT5 inakubali client mmoja.
Terminal ikiwa imeingia, script inajiunganisha nayo: **login/nywila si lazima**;
kinachohitajika ni `ELITEFX_MT5_TERMINAL` (`scripts\env.local.bat`, haipushwi).

## CONFIG
`engine/config/risk.yaml` ndicho **chanzo cha ukweli** cha vigezo vya risk/cost vya engine.
`engine/config/data.yaml` ndicho **chanzo cha ukweli** cha vigezo vya data/features/labels vya
utafiti. Datasets, notebooks na runs **zinabaki nje ya folda hii** — kinachorudi ni models +
namba zilizothibitishwa (attestation yenye `dataset_id`).
`config/ftmo_config.yaml` (ya zamani) inahudumia njia ya `live_brain` hadi uhamiaji ukamilike —
kisha itastaafishwa. **Vigezo visiwe sehemu mbili baada ya uhamiaji.**
