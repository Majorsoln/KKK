# T5 — GRID PANA (tangazo la KABLA)

> Kila kitu kinachoweza kuchaguliwa baada ya kuona matokeo kimefungwa hapa: cell ipi,
> ubashiri upi, kizingiti kipi, na uamuzi upi kwa kila jibu. Faili hili linaandikwa
> **kabla `build-labels` haijaendeshwa** kwenye grid mpya.

---

## 1. Kilichogunduliwa

`cost-audit` ya symbols 10 (2026-08-17), safu ya `EV net`:

| `sl_atr` | 0.50 | 0.75 | 1.00 | 1.50 | **2.00** |
|---|---|---|---|---|---|
| `EV net` (tp bora) | −0.2006 | −0.1023 | −0.0589 | −0.0062 | **+0.0039** |

Kwa `sl = 2.0`, `tp` inayopanda: −0.0329 · −0.0210 · −0.0162 · −0.0050 · **+0.0039**

**Mihimili yote miwili ni monotone hadi ukingo wa grid, na hakuna hata mmoja umegeuka.**

`sl_atr` iliishia **2.0**, `tp_atr` iliishia **3.0** — thamani kubwa kuliko zote
zilizotangazwa. Cell bora tuliyoipata ni **cell ya pembeni, kwa mihimili yote miwili**.

Hilo si matokeo; ni **dalili kwamba hatukutazama mahali pa kutosha**.

## 2. Nadharia inayopimwa

`commission_R = commission_pips ÷ sl_pips`

Gharama kwa **R** ni gharama kwa **pips** iliyogawanywa na upana wa stop. Stop mara mbili
pana inagawanya gharama ile ile kwa R mara mbili kubwa. Overshoot inafuata sheria ile ile
(`touch_past_pips ÷ sl_pips`).

Kwa utambulisho `√n ≤ κ·SR* ÷ cost_R`, gharama nusu inatoa `n_max` mara **nne** kubwa.

> **Ubashiri:** `EV net` itaendelea kupanda na `sl_atr` hadi kitu kingine kianze kubana.

## 3. Kitu kingine kinachobana — na ndiyo maana hii si njia ya bure

`horizon_bars = 24`. Barriers zikiwa pana, uwezekano wa kugusa yoyote kati yao ndani ya
bars 24 unashuka, na **timeout inapanda**.

Kwenye cell 2.0/3.0: timeout ni **0.236**, na cap ni **0.35**. Nafasi iliyobaki ni ndogo.

Timeout haiharibu EV kwa kuifanya hasi — inaidilute kuelekea sifuri, kwa sababu
`timeout_return_r` ni takriban sifuri kwa wastani. Kwa hiyo mgongano ni:

| Stop pana | inashusha | gharama kwa R |
|---|---|---|
| Stop pana | inapandisha | timeout |

**Optimum ni ya ndani mara horizon inapohesabiwa.** Grid ya awali haikufika mahali
mgongano huo unaanza kuonekana. Grid mpya inapaswa kuufikia.

`horizon_bars` **HAIBADILIKI**. Kuipandisha kungebadilisha embargo (bars 36), muundo wa
folds, na mpango wa splits uliosainiwa (DF-14) — mabadiliko makubwa zaidi kuliko swali
hili. Cap ya timeout inaruhusiwa kubana, na kubana kwake ni **jibu**.

## 4. Grid mpya

```yaml
sl_atr: [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
tp_atr: [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
```

Cells **49** badala ya 25. Hakuna data mpya: ticks zile zile, points zile zile,
`decision_time` zile zile. Ni **hesabu upya ya barriers kwenye path iliyopo**.

Ujenzi ni wa `(symbol, mwaka)`, kwa hiyo kumbukumbu haitegemei idadi ya cells kwa jumla —
points ~545 × cells 49 = rows 26,705 kwa chunk. `MemoryError` ya awali (2.15 GiB)
ilitokana na array ya ticks za mwaka, si cells.

## 5. Cell iliyotangazwa — imechaguliwa kwa NADHARIA, si kwa EV

> **Cell ni PANA KULIKO ZOTE kwenye grid mpya inayopita `max_timeout_frac = 0.35`.**

Kwa mpangilio, kutoka pana kwenda nyembamba: `4.0/6.0`, `4.0/4.0`, `3.0/6.0`, `3.0/4.0`,
`4.0/3.0`, `3.0/3.0`, … Ya kwanza yenye `timeout_frac ≤ 0.35` **na** `n ≥ 200`
(`min_labels_per_cell`) ndiyo cell.

**Sheria hii haijui EV ya cell yoyote.** Inatokana na utambulisho wa gharama pamoja na
kizuizi cha timeout kilichokwisha kutangazwa kwenye config. Hiyo ndiyo tofauti kati ya
ubashiri unaopimwa na uteuzi juu ya label.

Cell ya awali **2.0/3.0** inabaki kama **benchmark**, si mshindani: inalinganishwa, na
kulinganisha si kuchagua.

## 6. Uamuzi — umefungwa kabla

| Matokeo | Uamuzi |
|---|---|
| `EV net` inaendelea kupanda hadi cell iliyotangazwa, na mpaka wa chini wa CI ya 90% **juu ya sifuri** | Nadharia ya gharama **imethibitika**. Cell mpya inakuwa msingi. `cost-audit` inatoa `δ_MER` na `N_req` mpya, na T3 inarudiwa mara MOJA juu yake (config 1). |
| `EV net` inapanda lakini CI inavuka sifuri | Nadharia ina mwelekeo sahihi, **haijathibitika**. Hakuna config inayotumika. Kilichobaki ni kuboresha gharama yenyewe (commission, broker), si barriers. |
| Monotone **inageuka** kabla ya cell iliyotangazwa | Nadharia **imekanushwa**: gharama haikuwa kizuizi kinachotawala. Optimum ni ya ndani, na iko pale ilipogeuka — **lakini kuichagua ni uteuzi**, kwa hiyo inahitaji tangazo lake jipya. |
| Cell iliyotangazwa inavunja `max_timeout_frac` na hakuna cell pana inayopita | Horizon ndiyo kizuizi, si gharama. Hilo ni **jibu jipya kabisa**, na linaelekeza kwa swali la horizon — si kwa barriers. |

**Kilichokatazwa baada ya kuona jedwali:** kuchagua cell nyingine kwa sababu EV yake ni
kubwa, kupandisha `max_timeout_frac`, au kupanua grid mara ya pili hadi jibu libadilike.

## 7. Bajeti

**Kujenga labels na `cost-audit` haigharimu config.** Zote ni **vipimo** vya mgawanyo wa
labels — hazitathmini strategy, hazichagui kati ya models, na `cost-audit` inakataa
kuhesabu identities bila `--cell` iliyotajwa (ndiyo lango lililowekwa 2026-08-13).

**Kinachogharimu:** kuendesha `meta-label` juu ya cell mpya. Hiyo ni **config 1** kati ya
**5.5** zilizobaki.

## 8. Sahihi

Kupanua grid kunabadilisha `section_hash("labels")`, kwa hiyo sahihi za DF-09/DF-10/DF-21
zitaonyesha sehemu hiyo imebadilika. **Hiyo ni kweli, na inapaswa kuonekana** — grid ni
sheria iliyosainiwa, na kuibadilisha ni tangazo jipya, si ukarabati kimya.

Masharti manne ya supersession (G14) yanatumika: sheria ya awali inabaki kwenye ledger,
sababu imeandikwa hapa, ushahidi unaonyeshwa (`cost_audit_10sym_*.json`), na sahihi mpya
inatajwa `T5`.

## 9. Hatua

| # | Hatua | Amri | Bajeti |
|---|---|---|---|
| 1 | Grid kwenye config | imefanywa | hapana |
| 2 | **Sahihi ya PD kwenye tangazo hili** | — | hapana |
| 3 | Jenga labels upya (cells 49) | `build-labels` | hapana |
| 4 | Ukaguzi wa R1 | `r1-summary` | hapana |
| 5 | Chagua cell kwa sheria ya §5 | `cost-audit --cell …` | hapana |
| 6 | Uamuzi kwa jedwali la §6 | — | hapana |
| 7 | T3 ikirudiwa juu ya cell mpya | `meta-label` | **config 1** |

Hatua ya 2 ndiyo lango. Bila sahihi, hatua ya 3 haianzi.
