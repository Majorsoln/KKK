# BAJETI YA MAJARIBIO — kikomo kinachotekelezwa na code

**SR\* : 0.7**  ·  **miaka : 8.25**  ·  **bajeti : 7.5 configs**

> MinBTL (Bailey & López de Prado): `N ≤ exp(SR*² · miaka ÷ 2)`.
> Bajeti si mali ya dataset pekee — ni **function ya kile unachotarajia
> kupata**. SR\* ya juu inatoa bajeti kubwa kwa sababu ni ahadi kubwa.

> **Ya mradi mzima. Hairudishwi.** Per-phase reset ndiyo hasa
> multiple-testing surface tunayoifunga.

> `REPLICATION` haipunguzi bajeti — **kwa sharti** kwamba matokeo yake
> hayaruhusiwi kutumika kwa uteuzi wa strategy. Bila sharti hilo, kila
> config ingeitwa "validation".

> **Mamlaka ya faili hili.** Faili lenyewe liliandikwa na zana
> (`budget-init`) na kucommitiwa na mtekelezaji — kama `quality_report.json`
> na ripoti nyingine. **Halina mamlaka lenyewe.** Kinachofunga `SR* = 0.7`,
> `κ = 0.50` na cell `2.0/3.0` ni **sahihi ya PD kwenye `SIGNATURES.md`**
> (DF-20, 2026-08-13, ushahidi `research\reports\r1\cost_audit.json`).
>
> Kama namba za kichwa hapa juu zikitofautiana na zilizosainiwa, **sahihi
> ndiyo ya kweli na faili hili ni kosa.** Msomaji afuate ledger, si hili.

## Mgao uliotangazwa (si reset — ni mgawanyo wa 7.5 ile ile)

| Eneo | Mgao | Kinachohusika |
|---|---|---|
| Meta-labelling + variants zake | **3** | jaribio la msingi la T3 |
| Cross-sectional | **2** | umbo mbadala |
| Akiba | **2** | kwa kile tusichokijua bado |

> **Sub-allocation, si reset.** Awamu zinapata nidhamu bila kuzalisha bajeti mpya. Bajeti
> ikiisha kwenye eneo moja, haikopwi kutoka jingine bila PD kusaini mstari mpya
> unaoeleza kwa nini.

## Kisichopunguza bajeti

| | |
|---|---|
| Kufikiri, kuandika code, kubuni feature | kugusa outcome data ndiyo gharama |
| Sweep ya trigger (rate pekee, kabla ya labels) | ledger inathibitisha ilikuwa kabla; ndiyo mfano wa jinsi mechanism inavyopaswa kufanya kazi |
| `cost-audit` na `effective-n` | ni **vipimo vya muundo**, si utabiri — havichagui strategy |
| `REPLICATION` iliyotangazwa | **kwa sharti** matokeo yake hayaingii kwenye uteuzi |

## Vinavyopunguza

Kila **evaluation ya model dhidi ya labels**. Configs zinazohusiana zinapungua kwa
**cluster weight** (ONC/hierarchical), si moja kwa moja — cells 25 za grid ni clusters 2–3
(narrow/mid/wide), zinapungua 2–3.

---

| # | Tarehe (UTC) | Config | Aina | Uzito | Imebaki | Sababu |
|---|---|---|---|---|---|---|
| 1 | 2026-08-14T16:04:18+00:00 | `setup-effect-2.0-3.0` | EVALUATION | 1.000 | 6.548 | athari ya SETUP-v1 haielezwi na mazingira: +0.0348 R ndani ya strata (ATR/spread/session/symbol/mwaka), imepungua 32% kutoka +0.0515 ghafi, CI 90% [+0.0051, +0.0612] haiguzi sifuri, common support 96.4%. Momentum HAIKUDHIBITIWA - ndiyo treatment yenyewe |
