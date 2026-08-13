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
