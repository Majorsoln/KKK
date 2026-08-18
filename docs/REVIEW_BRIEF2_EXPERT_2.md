# Mapitio ya brief #2 — MTAALAMU WA 2

**Tarehe ya jibu lake:** 2026-08-17 · **Chaguo la lazima (§9): C** — *badilisha protocol ya utafiti, si mkakati*
**Hadhi:** imeandikwa **kabla** ya kupatanisha na mtaalamu wa 1. Hakuna neno la sehemu 1–4
litakalohaririwa baada ya upatanisho. Sehemu ya 5 (marekebisho) imeandikwa 2026-08-18.

> Aliona brief #2 pekee. Hakuona brief #1 wala jibu la mtaalamu wa 1.

---

## 1. Sentensi yake moja

> **"Doctrine item 3 iko makosa, na iko makosa kwa namna inayogeuza hitimisho lenu:
> kulazimisha κ = 0.5 kwa kukata idadi ya trades kunashusha net Sharpe kutoka ≈0.56 hadi
> ≈0.21. Kigezo kinaharibu kile kinachodai kukilinda."**

Hii ndiyo hoja iliyonigusa zaidi kwa sababu **ilikuwa sahihi, na kosa lilikuwa langu**.
Nilikuwa nimemwambia PD kuwa "tuko mara 7 juu ya bajeti ya gharama, kwa hiyo filter
inayobakiza 14% inahitajika kimuundo". Ni kinyume chake.

---

## 2. Hoja mbili zinazobeba kila kitu

### 2.1 Hakuna `n_max`

`net Sharpe = (μ_gross − cost_R)·√G / σ_R`. Hii **inapanda** kadri `n` inavyoongezeka
maadamu net EV kwa kila trade ni chanya. κ inabana **uwiano** wa gharama kwa faida —
ni upendeleo wa uhasibu, si kigezo cha kiuchumi. Market makers wanaendesha kwa uwiano
mbaya zaidi ya 0.5 na wako salama, kwa sababu uwiano si lengo.

Kwa hesabu, kukata 3,068 → 441 kwa mwaka:

| | 3,068/mwaka | 441/mwaka |
|---|---|---|
| gross Sharpe | 1.02 | 0.39 |
| cost drag | −0.46 | −0.18 |
| **net Sharpe** | **0.56** | **0.21** |

**Sheria mbadala ya κ:** filter inayobakiza sehemu `f` lazima **ipandishe** net EV kwa
kila trade kwa **1/√f** ili tu isipoteze Sharpe. Kwa `f` = 0.14 hiyo ni **mara 2.64** —
kutoka 0.0205 hadi 0.054 R. Hii ndiyo bar ya kweli, na ni kali kuliko niliyokuwa nayo.

### 2.2 Bar yetu ya significance na lengo letu ni namba ile ile

`t = SR·√T`. Kupata `t` ≥ 2 kwa T = 8.25 kunahitaji `SR` ≥ **0.696**. SR* yetu ni **0.7**.
Tumeweka lengo **hasa** pale sample yetu inapoanza kuona — jambo linalohakikisha karibu
sarafu ya kupiga kete hata kwa mkakati unaofikia lengo kwa usahihi. Hakuna filter,
regime-gate wala kazi ya gharama inayobadilisha hilo; ni tabia ya `T`.

**Lever ambayo hatujaitumia ni `T`, si `δ`.**

---

## 3. Makosa yetu aliyoyagundua

| # | Kosa | Hukumu yangu |
|---|---|---|
| 1 | §3.1 iliandika "sample × 3.5" kama **imezuiwa na §2.4**. §2.4 inazuia upanuzi wa **vyombo**, si wa **muda**. Dukascopy ina tick depth kabla ya 2016. | Kosa la wazi la kwangu. Limekubaliwa. |
| 2 | Gate ya §2.3 ilifeli juu ya **probability iliyofit** (0.3159 dhidi ya 0.3212), wakati realised top-decile R ilipita kwa raha (+0.0656). Kupima kwa output ya model badala ya pesa yenyewe ni kosa la muundo. | Limekubaliwa. **Gate on money.** |
| 3 | Spearman juu ya deciles 12 inatupa power bure. Regression endelevu juu ya score inatumia observations 10,168 zote badala ya ~1,000. | Limekubaliwa — takriban mara 3 ya `t` bure. |
| 4 | Šidák juu ya cells 49 zisizojitegemea. Cells 49 kutoka trades 25,314 pengine ni hypotheses 4–6 huru. | Limekubaliwa. Participation ratio, si idadi ghafi. |
| 5 | Bajeti ya trials 7.5 ilishindwa kazi yake yenyewe: **haikuzuia** uteuzi uliotokea kweli (pool ya symbols 10, argmax cell, marekebisho ya pre-registration katikati ya safari) — ilizuia tu uchunguzi halali. | Limekubaliwa kwa uchungu. Ni "mbaya wa pande zote mbili". |
| 6 | Constant ya commission: tuliiita "isiyochunguzwa" na kudhani ni ya kihafidhina. Yeye anasema tier ya chini ni **hasa** 0.7 pips round turn, na MT5 inaongeza ~$5/$1M juu yake — kwa hiyo namba zetu ni **za matumaini kidogo**, si za kihafidhina mara 2. Hatukumodel currency-conversion fee kabisa. | Limekubaliwa. Ni kazi ya siku moja, si utafiti. |
| 7 | Kuondoa EURCHF/EURGBP ndiyo **uteuzi mkubwa zaidi usiotozwa** kwenye document — ulisogeza pool kutoka −0.0163 hadi +0.0039, kisha tukaripoti grid nzima juu ya waliobaki. | Limekubaliwa. Linahitaji kupimwa upya. |

---

## 4. Mashambulizi manne juu ya SETUP-v2

1. **Lengo lake la calibration linatoka kwenye kigezo kilichovunjika.** Tulipendekeza
   kuweka gate ili 3,068 → 441 kwa sababu 441 ni `n_max`. Kama `n_max` haipo, tunatune
   gate kufikia kivuli.
2. **`N_eff` ya hypothesis ya regime si 10,168.** ER na ADX ni state variables za polepole,
   zenye autocorrelation kubwa. Sample halisi ni idadi ya **matukio huru ya regime**, si
   trades ndani yake — kwa miaka 8.25 na symbols 12 zinazohusiana, pengine mia chache, si
   elfu kumi. *Hili ndilo alilotaka tulijibu kabla ya kutumia trial.*
3. **Tunageuza tokeo la cross-section kuwa la time-series.** §2.4 iligundua trendiness
   inatabiri wastani wa R **kwa kila symbol**. SETUP-v2 inadhani inatabiri tokeo **kwa
   kila bar** ndani ya symbol. Ni madai mawili tofauti.
4. **Collinearity na trigger.** `|close − close[−4]| ≥ 2.5·ATR(14)` **ni** tukio la
   efficiency ratio kubwa juu ya window ya bars 4. Gate ya ER ya window fupi ni redundant
   kimitambo; ya window ndefu ni variable ya regime ya polepole ya hoja 2.

Na: gate ya trend-regime juu ya H1 breakout ni miongoni mwa mawazo yaliyochimbwa zaidi
kwenye retail systematic FX. *"It reads as motion, not progress."*

**Hukumu yangu: SETUP-v2 imewekwa rafuni.** Sina jibu la hoja ya 2.

---

## 5. Marekebisho — 2026-08-18, baada ya kugundua dosari ya labelling

Kuchukua uderivation wake wa `σ_R` kwa uzito ndiko kulikofichua dosari yetu ya labelling
(`timeout_return_r` ilikuwa mid-kwa-mid wakati TP/SL zinatatuliwa kwenye trade path).
Namba tulizompa zilikuwa zimevimba. Model yake ilizaa namba zetu **kwa usahihi kamili**,
kwa hiyo nimeijenga upya badala ya kuitupa. Kwa convention yake (gross = net + commission
+ overshoot):

| | alivyokuwa nayo | baada ya marekebisho |
|---|---|---|
| SE | 0.0127 | **0.0126** |
| `σ_R` (derived) | 1.28 | **1.275** |
| `cost_R` | 0.0167 | **0.0167** |
| net EV | +0.0205 | **+0.0081** |
| `t` | 1.62 | **0.64** |
| gross Sharpe | 1.02 | **0.68** |
| **cost drag** | **−0.46** | **−0.46** |
| net Sharpe | 0.56 | **0.22** |
| gharama kama sehemu ya gross | 45% | **67%** |

**Mambo matatu ya kuwa sahihi juu yake, kwa sababu yanaelekea pande tofauti:**

1. **Uderivation wake wa dispersion umesalia.** SE 0.0127 → 0.0126, `σ_R` 1.275. Alikuwa
   sahihi na bado ni sahihi.
2. **Makadirio yake ya gharama hayajaguswa.** Drag ni −0.46 pande zote mbili. Dosari
   ilikuwa kwenye **return**, si kwenye **gharama**. Hakuna alilolisema kuhusu gharama
   lililodhoofishwa.
3. **Kilichoanguka ni gross.** 1.02 → 0.68. Kwa **uwiano** hoja yake ya execution-cost
   imeimarika (45% → 67%); kwa **kiwango** kitu kinachotozwa kimekuwa kidogo sana.

**Kinachoanguka kwenye hoja yake:**

* *"You already have a 1.0 gross Sharpe"* — tuna 0.68.
* *"That is not a 'no edge' result. That is an execution-cost result."* — kwa `t` 0.64
  sina uhakika tofauti hiyo bado inapatikana kwetu.
* *"a costed result at the edge of detectability"* — 0.22 si ukingoni. Ni **32% ya**
  detection floor ya sample yetu (0.696). Kufikia `t` = 2 kwa SR 0.22 kunahitaji **T ≈
  miaka 80**.

**Lever yake ya muda (worklist #3) inapungua kwa hesabu:**

| | `t` |
|---|---|
| sasa, T = 8.25 | 0.64 |
| hadi ~2007, T = 17.5 | **0.93** |
| hadi ~2003, T = 23 | **1.07** |
| tier ya juu ya commission peke yake (0.15 pips), T = 8.25 | **1.47** |
| tier ya juu **+** T = 17.5 | **2.14** |
| tier mbaya (0.75 pips na MT5 add-on), T = 8.25 | **0.57** |

Njia ya kufikia `t` ≈ 2 bado ipo ndani ya framework yake — lakini sasa inahitaji lever
**mbili**, na moja kati yao ni tokeo la mtaji na volume, si la utafiti. Volume
inayonunua tier ya juu ni volume ambayo mkakati huu ungetakiwa kuipata kwanza.

**Kipimo kipya kinachogusa Q8 yake:** pure time exit — hakuna barriers kabisa, ingia
kwenye signal, funga baada ya bars 24, spread na commission zimetozwa:
**−0.0062 ATR, SE 0.0353, `t` = −0.18.** Sifuri. Hoja yake ya 1/√horizon inapima
**gharama** ya horizon ndefu kwa usahihi, lakini inadhani kuna drift ya kukamata. Kwa
saa 24 hakuna.

**Yaliyosalia bila kuguswa na marekebisho:** §2.1 (hakuna `n_max`), sheria ya 1/√f,
`t = SR·√T`, upanuzi wa muda haujazuiwa, hoja zote saba za sehemu ya 3, na mashambulizi
yote manne juu ya SETUP-v2. Vilevile setup-dhidi-ya-control (+0.0556 → **+0.0560 R**) —
dosari ilitoza setup na control sawasawa.

---

## 6. Nilipomtumia swali la kurudi

`docs/FOLLOWUP_EXPERT_2.md` — maswali sita. Lililo la msingi: alichagua **C** kwa sababu
*"the negative result is not established"*, na bullets zake mbili za msingi zilikuwa net
Sharpe 0.56 na gross 1.02. Kwa 0.22 na 0.68, **je msimamo wake unabadilika, au C yake
haitegemei kiwango?**

Upatanisho na mtaalamu wa 1 (aliyechagua **A** — shambulia effect size, horizon kwanza)
utafanyika **baada** ya jibu lake, si kabla.

---

## 7. Kipimo kilichofungwa — 2026-08-18

Kabla ya jibu lake, tumepima kile nilichoahidi kwenye Q5: pool kamili ya symbols 12 kwa
labels zilizosahihishwa. Matokeo: **EV net −0.0109 R, `t` −0.90, cells 0/49 chanya.**
Uteuzi ulikuwa na thamani ya **+0.0190 R**. Tazama `docs/T5_GRID.md` §16.

**Namba haitumwi kwake hadi ajibu Q5.** Nilimwomba ajitangazie tafsiri **kabla** ya
kuiona; kumtumia sasa kunaharibu kitu pekee ambacho swali lile lilikuwa nalo. Jibu
limeandaliwa na kufungwa: `docs/ADDENDUM_EXPERT_2_SEALED.md`. Tarehe ya kipimo iko
kwenye git, kwa hiyo mpangilio unathibitika.

**Muhuri ulishikilia.** Amejibu Q5 kwa kujitangazia tafsiri bila kuiona namba
(`97c89fc` ilikuwa imeshasukumwa, bila kutumwa). Faili sasa ni
`docs/REPLY_EXPERT_2_ROUND2.md`.

---

## 8. Jibu lake la pili — 2026-08-18, chaguo limebadilika C → D

**Alichokitoa mwenyewe, bila kuombwa mara ya pili:**

* *"That is not a 'no edge' result. That is an execution-cost result."* — **ameifuta
  kabisa.** Gross EV +0.0248 dhidi ya SE 0.0126 ni `t` ≈ 1.97 **gross**, kabla ya
  marekebisho yoyote ya multiplicity, juu ya argmax ya cells 49. Edge iliyo ukingoni
  hata **gross** si edge inayofichwa na gharama.
* *"The model reproduces your table exactly, so the decomposition is yours."* — ameifuta
  kama **hoja ya kimbinu juu ya mapitio yake mwenyewe**: alichukua ✓ zake kama zinazothibitisha
  namba zetu, wakati zilithibitisha tu kwamba algebra yake inalingana na yetu. **Vyote
  vilikuwa chini ya labeller ile ile.** Ni kosa alilolitaja kama linalostahili kutajwa
  zaidi, "kwa sababu ni aina inayomfanya mtathmini asikike na uhakika kuliko ushahidi
  unavyoruhusu".
* Scaling ya `1/√h`: sahihi ni **`1/√h` hadi `1/h`**. Alipunguza faida ya horizon, hakuiongeza.

**Hoja mpya, na ndiyo yenye thamani kubwa kuliko zote:** *sheria ya kusimama yenye mpaka,
juu ya process isiyo na drift, ina EV sifuri.* Barriers haziwezi kutengeneza return. Kwa
hiyo vipimo vyetu viwili lazima vipatane — na kwa mtazamo wa kwanza havipatani.

**Chaguo jipya: D** — badilisha tatizo, shikilia miundombinu. Si C, kwa sababu **C
tumeshaifanya** (vitu sita vya §6 vya barua yetu ndivyo worklist yake). Si E, kwa sababu E
inatupa mali ambayo *sasa* ni nzuri: labeller iliyo sahihi kwa madarasa matatu, tick base,
purged CV inayopita placebo, RCE, na — muhimu kuliko zote — **constant ya gharama ya
0.46 Sharpe kwa H1 ya bars 24 kwa bei ya retail**, ambayo ni chujio la hypothesis
linalotumika kwenye karatasi kabla ya kujenga chochote.

**D imefungwa kwa kitu kimoja:** muundo wa muda wa drift. Ikitokea gap ya 0.030 ATR ni
kasoro ya pili ya uhasibu, **D inaanguka kuwa E ndani ya wiki** — andika ripoti, na
ripoti ni bora zaidi kwa kuwa imepata kasoro mbili. Ikitokea ni drift iliyojikita mbele,
ushauri wake wa horizon ndefu ulikuwa **kinyume**, na hypothesis inayofuata ni ya horizon
FUPI yenye malengo membamba.

**Kosa lake la hesabu nililolipata:** gap yake ya "0.07 ATR" ni **0.030 ATR**. Alilinganisha
time exit **net** (spread + commission zimetolewa) dhidi ya cell **net + commission**. Lakini
sitadai hilo linatatua chochote: gap ni tofauti ya **paired** juu ya trades zile zile, kwa
hiyo SE yake si 0.0353 na pengine ni ndogo zaidi. Kurekebisha units kunapunguza gap;
kurekebisha test pengine kunaifanya iwe na maana ZAIDI. Identity yake bado inadai jibu.

**Shtaka lake la overshoot nimelipima kwenye code, si kwa hoja:** `realized_r()` inaweka
stop kuwa `−(1 + overshoot_R)` — overshoot IKO ndani ya path, kama alivyodhani inapaswa
kuwa. `ev_r_net = mean(realized) − commission_R`; **haitolewi mara ya pili.**
`cost_r_total` ni ya kuripoti pekee. **Shtaka limefungwa.** Mawili yake mengine
(granularity ya tie-break, mkanganyiko wa spread convention) hayajafungwa.
