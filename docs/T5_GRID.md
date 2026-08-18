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

**Ufafanuzi wa lazima:** `max_timeout_frac` ya config inapimwa kwa **JUMLA ya cells zote**
(`r1.py`: `(barriers["outcome"] == TIMEOUT).mean()`), si kwa cell moja moja. Sheria hapa
inatumia **namba ile ile kwa cell MOJA MOJA** — ni matumizi tofauti ya kizingiti kile
kile, na yanatangazwa hapa ili yasionekane kama nilikuwa nikitaja lango la config
lisilokuwepo kwenye kiwango cha cell.

Kumbuka pia: lango la jumla **linapoteza maana grid inapopanuka**. Cells 49 zikiwa na
nyembamba nyingi (timeout ~0%) na pana chache (timeout kubwa), wastani unaficha zote mbili.
Kwa EURUSD, jumla ni **14.1%** — namba ambayo haisemi lolote kuhusu `4.0/6.0`. Hukumu ya
cell inatoka kwenye `timeout_frac` ya cell hiyo, si kwenye jumla.

### DOSARI YA TANGAZO HILI, na jinsi imetatuliwa — 2026-08-17

Mpangilio niliouandika hapo juu (`4.0/6.0`, `4.0/4.0`, `3.0/6.0`, `3.0/4.0`, `4.0/3.0`,
`3.0/3.0`, …) ulikuwa **orodha ya mfano, si mpangilio kamili**. Haukuwa monotone kwa
`sl`, wala kwa `tp`, wala kwa jumla yao (`4.0/4.0` = 8 ilikuwa kabla ya `3.0/6.0` = 9).
Cells sita za kwanza zote zimefeli timeout, kwa hiyo `…` ndiyo inayoamua jibu — na `…`
haikuwa imetafsiriwa.

**Hiyo ni dosari halisi kwenye tangazo, na ndiyo hasa aina ya nafasi ambayo tangazo
lilipaswa kuifunga.** Nikiichagua sasa kwa kuangalia EV, kila kitu kingekuwa kimeharibika.

Inatatuliwa kwa **sababu ya sheria, si kwa matokeo**: utambulisho wa gharama ni
`commission_R = commission_pips ÷ sl_pips`. Unahusu **`sl` PEKEE**. `tp` haiingii kwenye
gharama hata kidogo — inaathiri malipo, si bei ya kuingia.

> **Mpangilio kamili: `sl_atr` kubwa kwanza; kati ya zenye `sl` ile ile, `tp_atr` kubwa.**

Hilo linatokana na kile nadharia inasema, si kile jedwali linaonyesha. Kwa timeout
zilizopimwa:

| cell | timeout | |
|---|---|---|
| 4.0/6.0 | 74.0% | ✗ |
| 4.0/4.0 | 61.5% | ✗ |
| 4.0/3.0 | 49.5% | ✗ |
| **4.0/2.0** | **32.7%** | **✓ ← cell** |

**Cell iliyotangazwa: `sl 4.0 / tp 2.0`.**

**Tafsiri mbadala, iliyoandikwa ili isifichwe:** kama mpangilio ulingekuwa
"hifadhi uwiano `tp/sl = 1.5` wa cell iliyosainiwa", jibu lingekuwa **`2.0/3.0` ile ile**
(`4.0/6.0` inafeli timeout; `3.0/4.5` haipo kwenye grid). Nimechagua ya `sl`-kwanza kwa
sababu ni **hoja ya nadharia**, wakati kuhifadhi uwiano ni hoja ya kufuata sheria ya jana.
Cell `2.0/3.0` inapimwa vyovyote — ilikwisha tangazwa kama benchmark hapo juu, kwa hiyo
hakuna kuangalia kwa ziada kunakoongezwa.

**Onyo la sura:** `4.0/2.0` ina `tp/sl = 0.5`, `p_tp` 0.745 na `dev_dp = 1.5`. Ni umbo
**kinyume** cha `2.0/3.0` (`p_tp` 0.377, malipo makubwa). Kushinda mara nyingi kwa kidogo
si strategy ile ile iliyofanyiwa T3 — na `δ_MER`, `N_req` na tabia ya drawdown zote
zinabadilika. Hilo litahesabiwa, halitadhaniwa.

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

---

## 11. MATOKEO — 2026-08-17

**Ukaguzi wa regression umepita.** Cell `2.0/3.0` imetoa `EV net +0.0039`, CI
`[−0.0147, +0.0206]` — sawasawa na kabla ya kujengwa upya. Cells 49 ni sahihi.

### Nadharia ya gharama: IMETHIBITIKA

| | `2.0/3.0` | `4.0/2.0` | `3.0/6.0` |
|---|---|---|---|
| `cost_R` | 0.0271 | **0.0117** | 0.0167 |
| `n_max`/mwaka | 166 | **902** | 441 |
| overshoot inaongeza | +36% | +16% | +25% |

`commission_R = commission_pips ÷ sl_pips` imefanya kazi kama ilivyotabiri: `sl` mara mbili
pana imeshusha gharama karibu nusu, na `n_max` imepanda mara 5.4.

### Ubashiri wa monotone: UMEKANUSHWA

`EV net` kwenye mhimili wa `sl`, `tp` imefungwa:

| tp | sl 2.0 | sl 3.0 | sl 4.0 | kilele |
|---|---|---|---|---|
| 1.0 | −0.0210 | −0.0070 | −0.0087 | 3.0 |
| 2.0 | −0.0050 | +0.0057 | +0.0007 | 3.0 |
| 3.0 | +0.0039 | +0.0121 | +0.0060 | 3.0 |
| 4.0 | +0.0075 | +0.0137 | +0.0067 | 3.0 |
| 6.0 | +0.0177 | **+0.0205** | +0.0123 | 3.0 |

**Kilele kiko `sl 3.0` kwenye safu 6 kati ya 7.** Si bahati — ni muundo, na ni hasa
mgongano niliouandika §3: gharama inashuka na `sl`, timeout inapanda, na optimum ni ya
ndani. Cell iliyotangazwa `4.0/2.0` iko **nyuma ya kilele**: `+0.0007`, CI
`[−0.0116, +0.0112]`.

Kwa jedwali la §6: *monotone ikigeuka kabla ya cell iliyotangazwa ⇒ nadharia imekanushwa;
gharama haikuwa kizuizi kinachotawala.* Ndicho kilichotokea. Mechanism ni kweli;
utawala wake si kweli.

### Cell bora: HAISHIKILII

`3.0/6.0` · `EV net +0.0205`

| Mpaka | Thamani | |
|---|---|---|
| 90% CI (jaribio moja) | `[−0.0015, +0.0404]` | ukingoni |
| **Šidák kwa cells 49** | **−0.0212** | **haishikilii** |

Ni **argmax ya cells 49**. Mpaka wa 5% ni wa cell iliyotangazwa **kabla**; huu
haukutangazwa. Kwa asilimia 0.105 inayohitajika kwa familia, jibu ni hasi.

**Hakuna cell kwenye grid nzima inayothibitika kulipa.**

## 12. Kitu kilichofungua mlango na kuufunga kwa wakati mmoja

Angalia namba mbili za mwisho kwa kila cell:

| cell | `cost_R` | lift inayohitajika | **`N_req`** |
|---|---|---|---|
| 2.0/3.0 | 0.0271 | 0.0202 p_tp | 4,175 |
| 4.0/2.0 | 0.0117 | 0.0151 p_tp | 8,063 |
| **3.0/6.0** | 0.0167 | **0.0043 p_tp** | **15,831** |

`N_eff` iliyopimwa: **10,168**.

Lift inayohitajika imeanguka **mara 7** (0.0300 → 0.0043). Lakini `N_req` imepanda
**mara 3.8**, na imepita `N_eff` yetu.

Utambulisho unaeleza kwa nini, na hakuna njia ya kuizunguka:

```
δ_MER = SR* ÷ (dev_dp · √n_max)        N_req ∝ 1 ÷ δ²
```

Gharama nafuu inaruhusu trades nyingi (`n_max` ↑), ambayo inashusha edge inayohitajika kwa
kila trade (`δ_MER` ↓) — na edge ndogo inahitaji **data nyingi zaidi** kuithibitisha.
**Levers mbili zinapigana.**

### Milango yote inafunga kwenye mahali pamoja

| Kupunguza edge inayohitajika | → panua barriers | → **N_req inapanda juu ya N_eff** |
| Kuongeza data | → ongeza symbols | → **gharama inapanda** (T4: 1.4×–4.7×) |

T4 ilishaonyesha lango la pili: symbols zote 36 zilizowezekana ni ghali kuliko zetu, na
kuziongeza kunapandisha `cost_R` ya pool kutoka 0.0271 hadi 0.0441.

**Vizuizi viwili vinakutana chini ya data tulizonazo.** Hilo si kushindwa kwa uchambuzi —
ni matokeo, na linatuambia hasa nini kingebadilisha jibu.

## 13. Kile kingebadilisha jibu — na hakuna kati yake ni model

| Lever | Kwa nini inafanya kazi | Athari |
|---|---|---|
| **Commission ndogo** | `commission_R = pips ÷ sl_pips`. 0.7 → 0.3 inaongeza `n_max` mara 5.4 kwenye cell YOYOTE, **bila kugharimu data** | inavunja mgongano wa §12 |
| **Entry rule yenye nguvu** | edge kubwa kwa trade ⇒ `δ` kubwa ⇒ `N_req` ndogo. SETUP-v1 inaleta +0.0251 p_tp dhidi ya control | inavunja mgongano kutoka upande wa pili |
| **Data ya kina kwa jozi ZENYE UKWASI** | `N_eff` ↑ bila `cost_R` ↑ — Dukascopy exotics zinashindwa hapa, vendor mwingine anaweza asishindwe | inaondoa kizuizi cha T4 |

**Model haiko kwenye orodha.** T3 imepima: `top R` p 0.119 (12 symbols), na baada ya
kuondoa utambuzi wa symbol, `ρ` 0.5152 p 0.040 — ujuzi upo, hauzai pesa. Kwenye cell mpya
bar ni ndogo zaidi (0.0043 p_tp) lakini `N_req` ni 15,831 dhidi ya `N_eff` 10,168:
**jaribio lolote litakuwa INCONCLUSIVE kwa muundo**, bila kujali matokeo. Kifungu cha nguvu
cha `metalabel.evaluate` kitalikataa lenyewe.

Kutumia config kwenye jaribio ambalo hesabu inasema haliwezi kuhitimisha ni kupoteza
config.

## 14. Bajeti

Zilizobaki: **5.5**. T5 haijatumia hata moja — `build-labels`, `r1-summary` na `cost-audit`
zote ni vipimo, na `cost-audit` inakataa kuhesabu identities bila `--cell` iliyotajwa.

Ushahidi: `research/reports/r1/cost_audit_10sym_c15043ae.json` ·
`research/reports/r1/r1_summary.json` · `research/reports/r1/label_build.json`

---

## 15. MAREKEBISHO — 2026-08-17, baada ya mapitio ya nje

Mapitio ya nje yalinifanya nifuatilie ujenzi wa `σ_R` kutoka `SE` na `N_eff`. Nikifanya
hivyo nilikuta kasoro **ndani ya labeller wetu**, si ndani ya hoja.

```
terminal_atr     = direction × (terminal_MID − entry_MID) ÷ atr_price
timeout_return_r = terminal_atr ÷ sl_atr
```

**Mid kwa mid.** Lakini TP na SL zinatatuliwa kwenye path ya **trade** (ingia kwa ask, toka
kwa bid). Darasa la timeout lilikuwa **limesamehewa round-trip spread nzima** wakati
madarasa mengine mawili yameitozwa. Athari inakua na sehemu ya timeout — ambayo kwenye
cells pana inazidi 60%.

Imerekebishwa (`LABEL_SCHEMA_VERSION 3`), labels zimejengwa upya, kila kitu kimepimwa upya.

### Kilichobadilika

| | kabla | **baada** |
|---|---|---|
| cells chanya | 13/49 | **6/49** |
| `3.0/6.0` `EV net` | +0.0205 | **+0.0081** |
| 90% CI | [−0.0015, +0.0404] | **[−0.0138, +0.0278]** |
| Šidák (cells 49) | −0.0212 | **−0.0332** |
| `t` | 1.62 | **0.64** |
| gross Sharpe | 0.93 | **0.59** |
| net Sharpe | 0.56 | **0.22** |
| commission ÷ gross Sharpe | 39% | **62%** |
| **`2.0/3.0` (iliyosainiwa)** | +0.0039 | **−0.0029** |

`E[R]` ya setups: −0.0290 → **−0.0335**. Ya control: −0.0846 → **−0.0896**. Tofauti
kati yao **haijabadilika**: +0.0556 → +0.0560 R. Kasoro iliathiri **kiwango**, si
**athari ya entry rule** — kwa sababu ilitoza pande zote mbili sawasawa.

### Kilichosalimika

**Kilele cha ndani cha `sl` = 3.0 kimesalimika** — ni kilele kwenye safu 5 kati ya 5.
Ugunduzi huo wa kimuundo ni imara dhidi ya marekebisho.

### Kilichoanguka

**Mhimili wa `tp` si monotone tena.** Kwa `sl` 3.0: `+0.0045 → +0.0037 → +0.0081`. Dai la
"bado inapanda kwenye ukingo" ni dhaifu zaidi kuliko tulivyolisema.

### Dai langu la kati lililokanushwa na kipimo

Baada ya kugundua kasoro, nilidai kwamba **barriers zinatoza edge** na faida yote iko
kwenye timeouts. Kipimo cha `exit-audit` kimeikanusha:

> **Kutoka kwa MUDA pekee** — hakuna barrier, ingia kwenye signal, funga baada ya bars 24,
> spread na commission zimetozwa:
>
> **`EV −0.0062 ATR · SE 0.0353 · t −0.18`** — **sifuri.**

Bila barriers hakuna edge kabisa. Barriers si tatizo; ndiko kidogo kilichopo kinakotoka.
Nilikuwa nikitafsiri **mgawanyo wa uhasibu** kama **mekanizimu** — `E[R|timeout]` ni chanya
kwa sehemu **kwa muundo**, kwa sababu timeout inachuja paths zilizogusa stop.

### Hukumu ya T5, iliyoandikwa upya

Nadharia ya gharama **imethibitika** (cost_R 0.0271 → 0.0117 kwa `sl` 4.0). Utawala wake
**umekanushwa** (kilele cha ndani kwa `sl` 3.0). Cell bora **haishikilii** (Šidák −0.0332).

Na sasa, kwa nyongeza: **`t = 0.64`**. Hakuna cell iliyo karibu na kuthibitika, na tofauti
kati ya "karibu" na "mbali" ilikuwa **kasoro ya uhasibu ya mstari mmoja**.

---

## 16. UTEUZI ULIOTOZWA — 2026-08-18, pool nzima ya symbols 12

Mtaalamu wa pili aliita kuondolewa kwa EURCHF/EURGBP **"uteuzi mkubwa zaidi usiotozwa
kwenye document"**. Kabla ya kupokea jibu lake la maswali ya kurudi, tumepima. Amri moja,
haitumii config budget (`cost-audit` ni takwimu ya population, si uteuzi):

```
python -m src.data.cli cost-audit --cell 3.0/6.0
```

### Matokeo

| | pool ya 10 (iliyoteuliwa) | **pool ya 12 (kamili)** |
|---|---|---|
| `EV net` kwa cell 3.0/6.0 | +0.0081 | **−0.0109** |
| 90% CI | [−0.0138, +0.0278] | **[−0.0322, +0.0078]** |
| Šidák (cells 49) | −0.0332 | **−0.0507** |
| `t` | +0.64 | **−0.90** |
| `cost_R` | 0.0167 | 0.0186 |
| gross Sharpe (convention ya mtaalamu 2) | 0.68 | **0.22** |
| cost drag | −0.46 | **−0.53** |
| **net Sharpe** | **+0.22** | **−0.31** |
| **cells zenye EV chanya** | **6 / 49** | **0 / 49** |

**Hakuna cell hata moja kati ya 49 iliyo chanya kwenye pool kamili.** Bora ni
`sl 3.0 / tp 2.0` kwa **−0.0107 R**.

Uteuzi ulisogeza EV kwa **+0.0190 R** — mara **2.3** ya makadirio yote yaliyobaki
baada ya marekebisho ya labelling. Ni **uteuzi mkubwa kuliko dosari ya labelling**
(0.0124), na mkubwa kuliko athari nzima ya SETUP-v1 dhidi ya control (0.0056).

### Kinachoanguka

* **Eneo chanya lote la grid lilikuwa tokeo la uteuzi.** Si la barriers, si la muundo, si
  la trigger.
* **Kilele cha ndani kwa `sl` 3.0 kimekuwa uwanda.** Kwa pool kamili: `sl` 3.0 bora
  −0.0107, `sl` 4.0 bora −0.0111. Tofauti 0.0004 — hakuna kilele hapo. Dai la §15
  ("kimesalimika") lilikuwa la pool iliyoteuliwa, na sasa linabanwa: mekanizimu ya
  gharama bado inaonekana kwenye mwelekeo (`sl` 0.5 → 3.0 inaboresha kwa 0.21 R), lakini
  eneo la juu ni tambarare kati ya 3.0 na 4.0.

### Kinachosimama

Mwelekeo wa `sl` bado ni mkali sana na wa mpangilio kamili (−0.2229 → −0.0107 kutoka
`sl` 0.5 hadi 3.0). Nadharia ya gharama haijaguswa; kilichoguswa ni dai kwamba ina kilele.

### Jaribio ambalo hoja ya gharama inashindwa

Mtaalamu wa pili anasema tatizo letu ni **gharama ya utekelezaji**, si kukosa edge. Kwa
pool kamili, tumepima hoja yake mwenyewe hadi mwisho wake — tier ya juu kabisa ya
Dukascopy aliyoitaja (0.15 pips round turn badala ya 0.7):

> `commission_R` 0.0146 → 0.0031 · `cost_R` 0.0186 → 0.0071
> **`EV net` → +0.0006 R · Sharpe → 0.02 · `t` → 0.05**

**Hata kwa commission ya bure kabisa, pool kamili haizalishi chochote.** gross Sharpe ni
0.22; gharama ya aina yoyote halisi inaila yote. Hoja ya "tuna edge, gharama inaila" ni
kweli kwa pool iliyoteuliwa **pekee**.

### Njia halali iliyobaki kwa EURCHF/EURGBP

Kuondoa symbols mbili baada ya kuona EV yao ni cherry-picking. Kuondoa symbols mbili kwa
**sheria iliyotangazwa juu ya sifa zisizo na label** — spread-per-daily-move, volatility
floor — si cherry-picking; ndilo jibu la mtaalamu wa pili kwa Q5. Sheria hiyo lazima
itangazwe kwanza, kisha ianguke pale inapoanguka, hata kama itaacha EURCHF ndani.

Hatujafanya hivyo. Hadi tufanye, **namba ya kuripoti ni −0.0109, si +0.0081**.

### Hukumu ya T5, toleo la tatu

T5 ilitangaza kupima kama kupanua grid kunafungua cell inayolipa. Jibu la mwisho, kwa
data ambayo hatujaichagua: **hapana, na hakuna karibu.** `t = −0.90`.
