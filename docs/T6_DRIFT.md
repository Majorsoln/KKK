# T6 — MUUNDO WA MUDA WA DRIFT

**Tarehe:** 2026-08-18 · **Chanzo:** identity ya mtaalamu wa pili, si mpango wetu
**Bajeti:** haitumii config budget — ni maelezo, si uteuzi (TRIAL_BUDGET §2)
**Hadhi:** ndicho kipimo chenye taarifa nyingi zaidi kwenye mradi mzima

---

## 1. Kwa nini kipimo hiki kilipimwa

Mtaalamu wa pili aliileta identity ambayo hoja zetu zote za T5 zinapaswa kuiheshimu:

> Sheria ya kusimama yenye mpaka, juu ya process isiyo na drift, ina **EV sifuri**.
> Barriers **haziwezi** kutengeneza return.

Kwa hiyo vipimo vyetu viwili lazima vipatane, na kwa mtazamo wa kwanza havipatani. Ama
kuna **drift ya kweli**, ama kuna **kasoro ya pili ya uhasibu**. Alisema hataitetea
mapendekezo yake yoyote — pamoja na chaguo lake mwenyewe la D — kabla ya kuona jibu.

Aliomba jedwali moja: mwendo wa wastani kutoka kwenye trigger, kwa ATR, kwa horizons
kadhaa, setup na control kando, gross na net.

---

## 2. Matokeo — pool kamili (symbols 12, setups 25,314)

| `h` (bars) | gross ATR | net ATR | 90% CI net | control net | tofauti |
|---|---|---|---|---|---|
| 3 | +0.0189 | −0.0905 | [−0.1033, −0.0782] | −0.1477 | +0.0572 |
| 6 | +0.0328 | −0.0766 | [−0.0982, −0.0553] | −0.1635 | +0.0869 |
| 12 | +0.0501 | −0.0594 | [−0.1022, −0.0186] | −0.1586 | +0.0992 |
| **24** | **+0.0593** | **−0.0501** | [−0.1355, +0.0253] | −0.1493 | **+0.0992** |
| 48 | −0.0546 | −0.1640 | [−0.3164, −0.0303] | −0.0806 | −0.0835 |
| 120 | −0.0497 | −0.1591 | [−0.3309, +0.0005] | −0.1004 | −0.0587 |
| 240 | −0.2651 | −0.3746 | [−0.5841, −0.1885] | −0.1696 | −0.2049 |

Pool ya 10 (ile ile iliyotumika kupima time exit) ina umbo lile lile, kubwa zaidi:
gross +0.0316 → +0.0521 → +0.0756 → **+0.0952** → −0.0027 → −0.0167 → −0.2188.

**Uhakiki:** kwa `h` = 24, gross kutoka H1 close ni **+0.0266 ATR** na `terminal_atr`
kutoka **ticks** ni **+0.0266 ATR** — tofauti **0.0000**. Njia mbili tofauti kabisa,
namba moja. Mpangilio mbadala (`pos+h−1`) unatofautiana kwa 0.0150, kwa hiyo mpangilio
wa bar umethibitishwa na data, si kudhaniwa.

---

## 3. DRIFT IPO. Ilikuwa imefichwa nyuma ya namba ya NET.

**Hili ndilo kosa langu, na ni la aina ile ile niliyoikosoa kwa mtaalamu wa pili siku hiyo
hiyo.**

Nilimwandikia: *"Indistinguishable from zero. The momentum trigger produces no measurable
24-hour drift."* Namba niliyoitegemea ilikuwa **−0.0062 ATR, `t` −0.18** — lakini ile ni
**net** (spread na commission zimeshatolewa). **Drift ni dhana ya gross.** Nilichukua
namba ya net nikatoa hitimisho la gross.

| kwa `h` = 24 | pool 12 | pool 10 |
|---|---|---|
| **gross** | **+0.0593 ATR** | **+0.0952 ATR** |
| `t` ya gross (kwa `N_eff`) | **+1.84** | **+2.63** |
| `p` (pande mbili) | 0.066 | **0.0085** |
| gharama | 0.1094 | 0.1013 |
| net | −0.0501 | −0.0062 |

Drift ipo, inapanda **kwa mpangilio kamili** kutoka `h` 3 hadi 24, na kwenye pool ambayo
time exit ilipimwa ni `t` **+2.63**. Si kelele.

**Kwa hiyo identity ya mtaalamu wa pili imeheshimiwa, na jibu ni (a) — drift ya kweli.**
Hakuna kasoro ya pili ya uhasibu inayohitajika kuelezea gap. Barriers hazikutengeneza
chochote; zilikuwa zikikamata kitu kilichokuwepo.

---

## 4. Lakini drift ni NDOGO KULIKO GHARAMA — na hiyo ndiyo hukumu nzima

| | pool 12 | pool 10 |
|---|---|---|
| gross drift kwa bars 24 | +0.0593 ATR | +0.0952 ATR |
| gharama ya round-trip | 0.1094 ATR | 0.1013 ATR |
| **gharama ÷ gross** | **1.84×** | **1.06×** |

Kwenye pool tusiyoichagua, **gharama ni mara 1.84 ya edge yote iliyopo.** Kwenye pool
tuliyoichagua, ni mara 1.06 — tunakosa kwa 6% ya gharama.

Hii ndiyo taarifa ya mwisho ya mradi, na ni kali zaidi kuliko "hakuna edge":

> **Kuna drift halisi ya momentum ya takriban 0.06–0.10 ATR kwa saa 24. Gharama ya
> kuingia na kutoka ni 0.10–0.11 ATR. Tunashindwa kwa upana wa spread.**

---

## 5. GHARAMA IMEGAWANYWA — na tulikuwa hatujaitaja nusu yake

`drift-curve` inatoza spread **kwa uwazi**, tofauti na grid ambapo spread iko ndani ya
path na haionekani kama safu. Ikigawanywa:

| | ATR | sehemu |
|---|---|---|
| spread ya round-trip | **0.0656** | **60%** |
| commission (0.7 pips) | 0.0438 | 40% |
| **jumla** | **0.1094** | |

**Uhakiki huru:** `commission_R` kwa `sl` 3.0 ni 0.0146, na `0.0146 × 3.0 = 0.0438` —
sawasawa na `0.1094 − 0.0656`. Njia mbili tofauti, tarakimu ile ile.

Maana yake ni kubwa. Worklist ya mtaalamu wa pili iliweka **uthibitisho wa commission
kama kipengele cha kwanza**, kwa sababu "inabadilisha umbo la EV surface". Lakini
commission ni **40% tu** ya gharama. Hata kwa tier yake ya juu kabisa (0.15 pips):

| | gharama mpya | gross | net |
|---|---|---|---|
| pool 12 | 0.0750 | +0.0593 | **−0.0157 ATR** |
| pool 10 | 0.0733 | +0.0952 | +0.0219 ATR |

**Kwa commission ya karibu bure, pool kamili bado ni hasi.** Lever ya commission haiwezi
kufunga pengo peke yake, kwa sababu spread — ambayo hatuwezi kuipunguza kwa mtaji —
ni kubwa kuliko commission.

---

## 6. HORIZON YA BARS 24 IKO KARIBU NA KILELE, si mbali nayo

Doctrine item 8 (horizon ya bars 24 iliyofungwa) mtaalamu wa pili aliiita *"pengine
ahadi ghali zaidi kwenye orodha yenu — ghali kuliko constant ya commission"*, na
akapendekeza horizon ya siku ~10 (= bars 240).

Data inasema kinyume kabisa:

* gross bado **inapanda** kwa `h` = 24 (0.0756 → 0.0952)
* imeshaanguka kwa `h` = 48 (−0.0027)
* kwa `h` = 240 — pendekezo lake hasa — ni **−0.2188** (pool 10) / **−0.2651** (pool 12)
* tofauti ya setup-dhidi-ya-control ina kilele kwa `h` = 24 (+0.0992 / +0.1123) kisha
  **inageuka hasi** kwa 48 (−0.0835)

Kilele kiko mahali fulani ndani ya [24, 48). Tulichagua 24 kabla ya kupima chochote, na
kilikaribia. **Horizon ndefu haikufi tu — inageuza ishara.**

Yeye mwenyewe alikuwa amelitaja hili kama uwezekano: *"if drift is front-loaded, the
correct move is a shorter horizon... I would then be wrong in the opposite direction."*
Drift si front-loaded (inapanda kwa mpangilio hadi 24), lakini **inarudi nyuma yote**
baadaye, na hitimisho la vitendo ni lile lile: si ndefu zaidi.

**Onyo la unyofu:** kwa horizons ndefu, madirisha yanaingiliana sana (points kila ~bars 8,
dirisha la bars 240), kwa hiyo idadi ya observations huru ni ndogo kuliko `n` ghafi na
`t` za safu za 48–240 zimevimba. Mwelekeo ni wazi; ukubwa wa uhakika si.

---

## 7. UTEUZI WA SYMBOLS — swali la mtaalamu wa pili limejibiwa, na jibu ni "uteuzi"

Alisema kuna njia moja tu ambayo kuondoa EURCHF/EURGBP kunabaki halali: **kama uhasi wao
unaelezwa na `cost_R`, si na gross.** Hapo ingekuwa sheria ya gharama isiyo na label,
inayoweza kutangazwa na kutumika sawasawa kwa symbols zote na za baadaye.

Mgawanyo kwa cell 3.0/6.0:

| symbol | `cost_R` | **gross** | `EV net` | spread/ATR |
|---|---|---|---|---|
| USDJPY | 0.0176 | **+0.0913** | +0.0737 | 0.0252 |
| GBPJPY | 0.0145 | **+0.0705** | +0.0560 | 0.0648 |
| EURJPY | 0.0152 | **+0.0600** | +0.0447 | 0.0373 |
| GBPUSD | 0.0151 | +0.0394 | +0.0242 | 0.0447 |
| USDCAD | 0.0173 | +0.0168 | −0.0005 | 0.0688 |
| USDCHF | 0.0215 | +0.0097 | −0.0118 | 0.0842 |
| XAUUSD | 0.0040 | +0.0069 | +0.0029 | 0.1047 |
| AUDUSD | 0.0194 | −0.0121 | −0.0315 | 0.0803 |
| NZDUSD | 0.0227 | −0.0157 | −0.0384 | 0.0949 |
| EURUSD | 0.0177 | −0.0169 | −0.0346 | 0.0218 |
| **EURCHF** | 0.0342 | **−0.0817** | −0.1160 | 0.0993 |
| **EURGBP** | 0.0251 | **−0.0839** | −0.1090 | 0.0809 |

**EURCHF na EURGBP ni hasi kwa GROSS, si kwa gharama.** `cost_R` yao (0.0342, 0.0251) ni
juu kidogo ya wastani lakini si popote karibu na kuelezea −0.08. Kuwaondoa **hakuwezi**
kuandikwa kama sheria ya gharama.

> **Uteuzi ule ulikuwa uteuzi juu ya matokeo. Njia pekee ya kubaki halali imefungwa.**

### Corollary yake, iliyokanushwa

Alionya: *"kama mtawanyiko wa 0.196 R ni wa `cost_R` badala ya gross, basi §2.4 si tokeo
tofauti — ni tokeo lako la gharama kwenye mfumo mwingine wa kuratibu."*

* `sd(gross)` = **0.0545**
* `sd(cost_R)` = **0.0072**
* uwiano = **7.6×**

**Mtawanyiko ni wa gross, si wa gharama.** §2.4 si gharama iliyovaa nguo nyingine. Onyo
lake halikushika.

**Lakini** — na hili ni dhidi yetu — `SE` kwa kila symbol ni **0.0438**
(`σ_R` 1.275 ÷ √(`N_eff` kwa symbol ≈ 848)). Mtawanyiko unaotarajiwa kwa **bahati tupu**
ni 0.0438; tuliopima ni 0.0545. Uwiano 1.24, `χ²(11)` = 17.0, **`p` = 0.11**.

**Mtawanyiko si wa gharama, lakini pia haujathibitika kuwa halisi.** Vitu viwili, vyote
lazima viandikwe.

---

## 8. Hukumu ya T6

1. **Drift ya momentum ni halisi** — `t` +2.63 gross kwenye pool ya 10, +1.84 kwenye 12.
   Hypothesis ya msingi ya ELITEFX **haikuwa batili**.
2. **Ni ndogo kuliko gharama ya kuifikia** — 0.059–0.095 ATR dhidi ya 0.101–0.109 ATR.
3. **Spread ni 60% ya gharama, si commission.** Lever tuliyokuwa tukiifukuza ni ndogo
   kati ya mbili, na kubwa haiuziki kwa mtaji.
4. **Horizon ya bars 24 iko karibu na kilele.** Horizon ndefu inageuza ishara.
5. **Uteuzi wa symbols haukuwa sheria ya gharama.** Umefungwa.
6. **Mtawanyiko wa cross-section ni wa gross, si wa gharama — lakini `p` = 0.11.**

Hitimisho lililoandikwa kwa unyofu:

> ELITEFX ilipima kama msukumo wa momentum unatabiri kuendelea kwa saa 24 kwenye FX
> majors. **Unatabiri.** Athari ni takriban **0.06–0.10 ATR**. Gharama ya kuichukua kwa
> bei ya retail ni takriban **0.10–0.11 ATR**. Tofauti ni **hasi**, na haifungiki kwa
> commission peke yake kwa sababu spread ni sehemu kubwa ya gharama.
>
> Hii si "hakuna edge". Ni **edge iliyopimwa, iliyo ndogo kuliko gharama ya utekelezaji
> inayopatikana kwetu** — na ndilo tokeo ambalo kwa kweli linaweza kutumika tena.
