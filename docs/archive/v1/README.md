# Kumbukumbu ya doctrine ya v1

Hati hizi zilikuwa **doctrine** ya ELITEFX kuanzia 2026-06 hadi 2026-08-18. Zimewekwa
hapa pale `docs/DOCTRINE_V2.md` ilipochukua nafasi yake.

**Hazijafutwa kwa sababu tatu:**

1. Nyingi ya sheria zake zilisimama kwenye ukaguzi wa nje mara mbili. Sheria za
   uvujaji, cross-fitting, na lango la models (§6 ya KAIROS-1) zimehamia v2 zikiwa
   **hai**, si zimeandikwa upya.
2. Muundo wa KAIROS-1 haukuwa makosa. **Hatukuwahi kujenga tabaka lake la DECISION.**
   v2 ni kurudi kwenye mpango, si kuutupa.
3. Ushahidi wa kwa nini v2 inaonekana hivi upo kwenye T4, T5, T6 na mapitio ya
   wataalamu — na hati hizo zinazitaja hizi.

| hati | ilifanya nini |
|---|---|
| `KAIROS_1_STANDARD.md` | tabaka 3, models 10, sheria ya kuingia kwa model |
| `DATA_FEATURE_STANDARD.md` | sheria 8+ za features, uvujaji, cross-fitting |
| `DATA_SPLIT_PLAN.md` | train / validate / holdout |
| `IMPLEMENTATION_PLAN.md` | mpango wa awamu R0–R4 |
| `RESEARCH_PLAN_R0.md` | mpango wa utafiti wa awali |
| `T3_PLAN.md` | pre-registration ya meta-labelling (tokeo: hasi) |

**RCE haiko hapa.** `docs/RISK_COST_ENGINE.md` na `config/risk.yaml` hazijaguswa na
hazijabadilishwa na v2 — ni mamlaka ya gharama kwa v1 na v2 sawasawa.
