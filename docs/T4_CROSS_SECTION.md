# T4 — SHERIA YA CROSS-SECTION (tangazo la KABLA)

> **Faili hili linaandikwa KABLA data yoyote mpya haijaguswa.** Hiyo ndiyo maana yake yote.
> Kila kitu kinachoweza kuchaguliwa baada ya kuona matokeo kimefungwa hapa: symbols zipi,
> kipimo kipi, kizingiti kipi, na uamuzi upi kwa kila jibu.

---

## 1. Swali

> Je **trendiness ya symbol**, ikipimwa **bila kugusa label yoyote**, inatabiri `R` ya
> SETUP-v1 kwenye symbol hiyo?

Ikiwa ndiyo, tunapata **sheria ya population** inayotumika kwa symbol **yoyote** — hata
isiyokuwepo kwenye data yetu leo. Ikiwa hapana, jedwali la symbols la hatua 4 ni orodha
ya matokeo, na hakuna sheria ya kuandika.

### Kwa nini swali hili na si lingine

Hatua 4 ya T3 iliishia na mambo matatu yaliyopimwa:

| Kilichopimwa | Thamani |
|---|---|
| Utofauti wa `R` kati ya symbols | **0.1959 R** |
| Lift iliyohitajika kutoka kwa model | +0.0505 R |
| Athari ya model baada ya kuondoa utambuzi wa symbol | haikulipa (`top R` p 0.119) |

Utofauti kati ya symbols ni **mara 3.9 ya lift nzima tuliyokuwa tukiitafuta kwa model**.
Lever kubwa iko kwenye cross-section, na model haikuwa kizuizi siku moja.

---

## 2. Kipimo — KIMOJA, kimetangazwa

**`trendiness` = wastani wa RANK za `eff_ratio_24h` na `adx14` kati ya symbols.**

Vyote viwili vinahesabiwa **kutoka bei pekee** (`src/data/features.py`), havijui label yoyote.
Wastani wa rank, si wa thamani ghafi: vipimo viwili vina vipimo tofauti, na kuvichanganya
kwa thamani kungefanya kimoja kitawale kwa bahati ya units.

### Kwa nini kimoja na si viwili

Kwenye hatua 4 nilipima vyote viwili (`ρ` +0.545 na +0.434) na kuripoti kubwa zaidi.
**Kuchagua kipimo baada ya kuona `ρ` yake ni uteuzi**, na gharama yake ni halisi:

| Vipimo | blocs zinazohitajika kwa ρ 0.545 | symbols |
|---|---|---|
| **1 (kimechanganywa)** | **10.1** | **15–17** |
| 2 (kwa Šidák) | 13.9 | 19–23 |

Kutangaza kipimo kimoja kunaokoa **symbols 4–6**. Trendiness ni **dhana moja** inayopimwa
kwa vyombo viwili; kuiita majaribio mawili ni kujiadhibu bila sababu, na kuchagua bora
kati yao ni kujidanganya.

---

## 3. Sheria ya kuchagua symbols — mekaniki, bila label

Symbols zinachaguliwa kwa **sheria hii pekee**, kwa mpangilio huu, kabla ya kuona `R` ya
yoyote kati yao:

0. **FX spot pekee.** Hakuna index, bond wala CFD. Sababu si ladha: labels za L4
   zinajengwa kwenye **path ya ticks inayoendelea** yenye ATR bands (§5). Vitu vyenye
   session breaks na gaps za usiku vinavunja dhana hiyo kimya — barrier "iliyoguswa"
   wakati soko limefungwa si barrier iliyoguswa.
1. **Lazima iwe na USD au EUR.** Jozi isiyo na moja kati ya hizo (mfano `AEDCNH`) karibu
   daima ni **synthetic** — broker anaijenga kutoka `AEDUSD × USDCNH`, na spread yake ni
   **jumla ya mbili**. Kwa utambulisho wa gharama `√n ≤ κ·SR*/cost_R`, symbol kama hiyo
   haiwezi kubeba setup kwa `n` yoyote.
2. **Tick history inayofika `2016-01-04`** (`probe-history`).
3. **Inapita malango ya §3** ya ubora (`check-l1`) kwa kiwango kile kile cha symbols 12.
4. **Inaongeza UNDERLYING MPYA.** Kati ya zilizobaki, zinapangwa kwa idadi ya underlyings
   mpya zinazoletwa.

### Marekebisho ya 2026-08-16 — na kwa nini yanaruhusiwa

Toleo la kwanza la sheria hii lilikuwa **na sheria ya 4 pekee**. Orodha halisi ya broker
(Dukascopy, symbols 418) iliifichua kama haitoshi: iliweka `AEDCNH`, `AEDTRY`, `CNHZAR`
**juu ya orodha**, kwa sababu kila moja inaleta sarafu **mbili** mpya. Zote ni synthetic,
zenye spread ya kutisha, na hazina historia.

Sheria ya 0 na ya 1 zimeongezwa kwa sababu za **muundo wa chombo** — session structure na
gharama — **si kwa sababu ya matokeo ya symbol yoyote**. Hakuna `R`, `p_tp` wala trendiness
iliyotazamwa. Ndiyo maana marekebisho haya ni halali, na ndiyo hasa maana ya kutangaza
kabla ya kusaini: **dosari inashikwa kabla haijawa uteuzi.**

Pia iligundulika dosari ya kuchambua majina: `AUS.IDX` ilikuwa ikigawanywa `AUS`/`IDX` na
`BUND.TR` ikigawanywa `BUN`/`DTR`, zikihesabiwa kama sarafu nne mpya zisizokuwepo.
Sasa jina linagawanywa **ikiwa tu nusu zote mbili ni sarafu za ISO-4217 zinazojulikana**.

**Sheria ya 4 ndiyo yenye maana ya nguvu**, na inatokana na hesabu si ladha:

```
symbols 15  ikiwa kila symbol mpya inaleta bloc yake   (underlying MPYA)
symbols 17  ikiwa urudufu unabaki 0.63 bloc kwa symbol (jozi za sarafu zilezile)
```

Tuna underlyings 8 + dhahabu: EUR, USD, JPY, GBP, CHF, CAD, AUD, NZD, XAU. Jozi zote
zinazowezekana kati yao zinaongeza **rows**, si **blocs**. Underlyings mpya (SEK, NOK,
SGD, MXN, ZAR, PLN, XAG, na kadhalika) ndizo zinazoongeza blocs.

**Kilichokatazwa:** kuchagua symbol kwa sababu `R` yake, `p_tp` yake, au trendiness yake
inaonekana nzuri. Sheria zote hapo juu hazijui lolote kati ya hivyo.

### Idadi ya mwisho

Inachaguliwa kwa `cross-power`, si kwa kubahatisha:

```
python -m src.data.cli cross-power --rho 0.545 --blocs 7.54 --symbols 12
```

Kwa `ρ = 0.545`: **15–17** kwa jumla. Tunazo **12**, kwa hiyo tunahitaji **3–5 mpya pekee**.

**Si 28.** §3.9 ilikadiria 28 kwa hisia. Hesabu inasema tunahitaji symbols **tatu**
zilizochaguliwa vizuri — na tofauti kati ya 3 na 16 mpya ni **miezi ya kurekodi ticks**.

---

## 4. Kizingiti — kinahesabiwa, hakichaguliwi

Somo la gharama kubwa zaidi la T3: **kizingiti nilichokichagua kwa hoja (`ρ ≥ 0.7`) kilikuwa
ndani ya mgawanyo wa kelele.** Halikuwa lango.

Kwa hiyo hapa kizingiti kinatoka kwenye utambulisho, kikitumia **blocs zilizopimwa baada ya
data kufika**, si idadi ya symbols:

```
ρ_crit = z_α ÷ √(blocs − 1)          blocs = participation_ratio(panel ya R kwa symbol)
```

`placebo` inaihesabu na kuiripoti yenyewe (`blocs huru … → ρ inayohitajika …`).

**Blocs zinapimwa KABLA ya `ρ` kutazamwa.** Utaratibu:

1. Data mpya inafika, L1→L4 inajengwa.
2. `placebo` inaendeshwa → jedwali linaripoti `blocs` na `ρ_crit`.
3. **Ndipo** `ρ` inatazamwa.

Kubadilisha mpangilio huo kungeruhusu `blocs` kuchaguliwa ili `ρ_crit` iwe rahisi.

---

## 5. Uamuzi — umefungwa kabla

| Matokeo | Uamuzi |
|---|---|
| `ρ ≥ ρ_crit` | Sheria ya trendiness **inakubaliwa**. Inaandikwa kama registered rule inayotumia **kizingiti cha trendiness**, si majina ya symbols. Inapimwa kwenye holdout **mara moja**. |
| `ρ < ρ_crit`, `blocs ≥ zinazohitajika` | Sheria **inakataliwa**. Jedwali la symbols ni orodha ya matokeo. Kuondoa EURCHF/EURGBP kunabaki uamuzi wa kiutendaji **bila nadharia**, na kunaandikwa hivyo. |
| `blocs < zinazohitajika` | **INCONCLUSIVE.** Hakuna hitimisho, bila kujali `ρ`. Symbols zaidi au kufunga. |

**Kilichokatazwa baada ya kuona `ρ`:** kubadilisha kipimo, kubadilisha kizingiti, kuongeza
symbols hadi `ρ` ipite, au kuripoti `eff_ratio` na `adx` kando ili kuchagua bora.

---

## 6. Bajeti

**Upimaji huu haugharimu config.** Sababu ni ya kanuni: `trendiness` haitumii label
yoyote, kwa hiyo hakuna uteuzi juu ya label unaofanyika — ni **kipimo cha bei dhidi ya
matokeo**, si utafutaji wa strategy kwenye nafasi ya configs.

**Kinachogharimu:** kutumia sheria iliyokubaliwa kujenga strategy. Hiyo ni config, na
inagharimu **1** kati ya **5.5** zilizobaki.

---

## 7. Ukiri

Swali hili limetokana na jedwali la `placebo` la 2026-08-14 — jedwali lililotokana na
labels. **Nadharia imezaliwa kutokana na data.**

Hilo si kosa; ndivyo nadharia nyingi zinavyozaliwa. Linakuwa kosa likipimwa kwa data ile
ile iliyoizaa. Ndiyo maana:

* kipimo ni **label-free** (bei pekee);
* symbols mpya **hazikuwepo** wakati nadharia ilizaliwa;
* kizingiti kinahesabiwa kutoka blocs, si kuchaguliwa;
* uamuzi umefungwa hapo juu, kabla ya jibu kujulikana.

Bila masharti hayo manne, T4 ingekuwa T3 ikirudiwa kwa symbols zaidi.

---

## 8. Hatua

| # | Hatua | Amri | Inagharimu bajeti? |
|---|---|---|---|
| 1 | Orodha ya symbols kwa sheria ya §3 | `check-mt5` · `probe-history` | hapana |
| 2 | **Sahihi ya PD kwenye orodha** — kabla ya kurekodi | — | hapana |
| 3 | L0 → L1 → L2 kwa symbols mpya | `backfill` · `check-l1` · `build-l2` | hapana |
| 4 | Setups + labels (cell 2.0/3.0 pekee inahitajika) | `detect-setups` · `build-labels` | hapana |
| 5 | Pima blocs, kisha `ρ` | `placebo --reps 5` | hapana |
| 6 | Uamuzi kwa jedwali la §5 | — | hapana |
| 7 | Strategy ikikubaliwa | `meta-label` au mrithi wake | **ndiyo — config 1** |

Hatua ya 2 ndiyo lango. Orodha ikishasainiwa, haibadiliki; symbol ikishindwa malango ya
§3, inatolewa na **haibadilishwi na nyingine iliyochaguliwa baadaye**.
