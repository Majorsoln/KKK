# ELITEFX — RIPOTI YA MAENDELEO

**Hadi 2026-08-11** · branch `claude/ml-capabilities-planning-rgrq6b` · sahihi za PD: **11** ·
tests: **287** zinapita · `config_hash` `sha256:4ce1768`

> Hii ni ripoti ya **hatua zilizopita**, si mpango. Kila namba iliyoandikwa hapa imepimwa kwenye
> data halisi na ina faili la ushahidi lenye SHA256 kwenye `docs/SIGNATURES.md`. Kumbukumbu kamili
> ya kiufundi iko `docs/IMPLEMENTATION_PLAN.md` §3.5–§3.6.

---

## 1. Tulipo

| Awamu | Hali | Kilichofungwa |
|---|---|---|
| **T0 — Msingi** | ✅ IMEFUNGWA (2026-08-06) | L0 immutable + SHA256; recorder wa broker; normalization A/B; malango ya repo |
| **T1 — R0 ukaguzi wa data** | ✅ IMEFUNGWA (2026-08-10) | Siku **33,440/34,781 (96.1%)** zinafaa kutumika; sahihi 6 za VERIFIED |
| **T2 — R1 labels** | 🔄 R1 **PASS** | L4 cells **1,308,025**; jiometri inashikilia; setup dhidi ya control **+0.0251 p_tp / +0.0638 R**; inasubiri sahihi ya exit |
| T3–T7 | ⏳ zinasubiri mfuatano | features, baselines, EV, holdout, live |

**Data:** ticks **bilioni 3.4** · symbols **12** · 2016-01-04 → 2026-08-07 · partitions **25,510**.

---

## 2. T0 — Msingi (imefungwa 2026-08-06)

Lengo: kuhakikisha data ya chanzo haiwezi kubadilika kimya, na kwamba kila kitu kinaweza
kuzalishwa upya.

- **L0 haibadilishwi kamwe.** Kila partition ina SHA256 kwenye manifest; lango la CI linakagua kila
  build. Kubadilisha kunahitaji `--allow-mutation --reason` ya PD, na tukio linaingia `mutation_log`.
- **Matoleo mawili ya schema yanaunganishwa.** Toleo A (symbols 9, µs, kwa siku) na Toleo B
  (EURCHF/GBPJPY/XAUUSD, ms, kwa mwezi) yanatoa schema **moja** ya kawaida bila kugusa L0.
- **Recorder wa broker.** Feed ya Dukascopy demo inarekodiwa kila siku; inajitibu yenyewe siku
  zikirukwa (kalenda dhidi ya **disk**, si state ya kumbukumbu).
- **Malango ya repo.** `research/data/` (GB 31) haipushwi kamwe — imethibitishwa kwa jaribio hasi.

Vipengele `VERIFIED`: DF-01, DF-02, DF-03, DF-04, DF-17, DF-18.

---

## 3. T1 — Ukaguzi wa data (imefungwa 2026-08-10)

Swali la R0: **je data tuliyonayo inatosha kujenga chochote?** Jibu: **ndiyo**, na sasa tunajua
sehemu zake mbovu kwa jina na kwa idadi.

### 3.1 Hali ya mwisho

| Kigezo cha §R0 | Namba | |
|---|---|---|
| Siku zinazopita §3 | **33,440 / 34,781 (96.1%)** | — |
| Miaka ≥ 10 | ndogo kuliko zote **10.6** | PASS |
| Siku zilizotarajiwa bila data | **0** | PASS |
| Jumamosi zenye ticks (zisizoelezeka) | **0** | PASS |
| Toleo A ↔ B: schema moja | True | PASS |
| **spread broker ÷ aggregator** | **1.0** kwa siku 5 | PASS |
| `clock_drift` | p1…p99 = **0.0** | PASS |

Sababu za kufeli, kwa siku:

| Sababu | Siku | % |
|---|---|---|
| `excluded_by_pd` (uamuzi wa PD, 2023) | 912 | 2.62 |
| `low_coverage` | 250 | 0.72 |
| `stale_feed` | 213 | 0.61 |
| `intrasession_gap` | 178 | 0.51 |
| `session_mismatch` | 131 | 0.38 |
| `bad_timestamps` · `quote_violation` | 39 | 0.11 |

### 3.2 Jibu kubwa kuliko yote

**Spread ya broker haizidi ya data tuliyofundishia.** Siku 5 zinazopishana, symbols 12,
linganisho 51: uwiano wa median = **1.0** (min 0.8714, max 1.0). Hilo lilikuwa hatari kubwa ya R0 —
kama broker angekuwa ghali zaidi, kila EV ingekuwa ya matumaini na `cost_stress_mult: 1.5`
ingekuwa haitoshi. Sasa ni bima ya ziada ya kweli, si kufunika pengo.

### 3.3 Maamuzi mawili ya PD

1. **`min_coverage` 0.995 → 0.95.** Kizingiti cha zamani kilimaanisha dakika 7 zinazokosekana kwa
   siku zinatosha kufelisha siku nzima — kipimo cha ukamilifu wa feed, si cha kama siku inaweza
   kufanyiwa biashara. Siku **2,383** zilirudi.
2. **2023 ya Toleo B imeondolewa** (siku 912). `symbol-profile` ilionyesha EURCHF, GBPJPY na
   XAUUSD — symbols zote tatu za chanzo kimoja — zikipoteza saa 1–2 **kwa siku** mwaka 2023 pekee,
   kisha kurudi 2024. Vyombo hivyo havishirikiani chochote kama masoko; kinachoshirikiana ni
   **chanzo**. Athari: labels za touch zinatatuliwa kwa path ya ticks, kwa hiyo pengo la saa 2
   lingeficha barrier zilizoguswa na label ingesema `timeout` wakati SL/TP iliguswa — si kelele,
   ni **jibu la uongo**.

### 3.4 Kasoro nne zilizokamatwa na namba zisizowezekana

Hakuna hata moja iliyokamatwa na test. Zote zilijitangaza kwa namba ambayo haiwezi kuwa kweli.

| Namba iliyoonekana | Ilikuwa inasema nini | Kilichorekebishwa |
|---|---|---|
| `1140 + 300 = 1440` | Toleo B linakata mwezi **saa 05:00 UTC**, si usiku wa manane — tarehe 1 iko nusu kwenye kila faili | vipande vinaunganishwa kabla ya kuhukumiwa |
| `p50 = −171,679,765 s` | `clock_drift` ilikuwa inalinganisha tick ya mwisho na `now()` — umri wa faili, si ubora. Haikuweza kufeli kimuundo | inapima tick iliyo nje ya siku yake |
| `coverage max = 2.0084` | provenance haikuwa kwenye ufunguo — aggregator na broker walichanganywa | siku 51 zilirudi |
| `coverage max = 2.0028` | kujumlisha kunadhani vipande **havipishani**; faili mbili zenye siku ile ile ni **nakala** | muda wa kipande unatofautisha nusu na nakala |

Matokeo: `session_mismatch` **568 → 131** bila kizingiti chake kuguswa hata mara moja.

### 3.5 Sikukuu 16

Siku 16 zilizoripotiwa "zinahitaji maelezo" zilikuwa **zote** 25 Desemba (9) au 1 Januari (7).
Soko la FX halifungwi siku hizo — linabaki wazi likiwa jembamba. **Dhana ya kalenda ndiyo ilikuwa
mbaya, si data.** Siku hizo zinabaki (siku ghali ndizo model ya gharama inazohitaji zaidi), na
swali halisi lililokuwa limefichwa ndani yake lilipata jibu: **Jumamosi zenye ticks = 0.**

---

## 4. T2 — SETUP-v1 (pre-registration imesainiwa 2026-08-11)

Kabla ya label yoyote, sheria ya "bar ipi inastahili kuwa wakati wa kuamua" lazima iandikwe na
kusainiwa. Hili ni **darasa la tatu la uvujaji** — la uchaguzi. Sheria ikitunwa baada ya kuona
matokeo, kila namba ya baadaye ni ya baada ya ukweli, na **hakuna test inayoweza kuikamata.**

### 4.1 Sheria

Bar ya H1 iliyofungwa ni decision point ikiwa **zote tatu** zinatimia:

| # | Kigezo | Kizingiti |
|---|---|---|
| 1 | **Gharama** | `spread_p50` ≤ 1.5 × median ya bars 528 zilizopita |
| 2 | **Volatility** | ATR14 ndani ya percentile 20–95 ya miezi 6 iliyopita |
| 3 | **Mwendo** | \|close − close[4]\| ≥ **2.5** × ATR14 |

### 4.2 Kutuna kwa RATE (inaruhusiwa kabla ya labels pekee)

| `min_atr_mult` | 1.0 | 1.5 | 2.0 | **2.5** | 3.0 |
|---|---|---|---|---|---|
| rate | 26.33% | 15.21% | 8.42% | **4.46%** | 2.32% |

1.0 haikuwa inachuja: bei inatembea ~2σ ndani ya bars 4 na ATR14 ni ~1.3σ, kwa hiyo "msukumo wa
1 ATR" ni **wa kawaida**. 2.5 inatua kwenye 5% ambayo bajeti nzima ya §0.1 ilijengwa juu yake.

**Kigezo ni scale-free — imepimwa:** kwa 2.5, symbols zote 12 ziko kati ya **3.9% na 4.9%**.
EURCHF (tulivu kabisa) na XAUUSD (ya wazimu) zinatoa namba ile ile. Namba zingetawanyika, kigezo
kingekuwa kinapima **bei**, si fursa.

**Control 0.10 → 0.05:** kichujio kilipofikia 4.46%, "10% ya bars zisizo setup" ilitoa control
56,471 dhidi ya setups 26,390 — mara mbili ya kinachopimwa. Nguvu ya ulinganisho inategemea kundi
**dogo**; control ya ziada haikuwa inanunua chochote, ilikuwa inagharimu 68% ya kazi.

### 4.3 Kasoro iliyokutwa kabla ya sahihi

**Hukumu ya R0 haikuwa ikifika popote.** Hakuna faili lililokuwa likisoma `quality_report.json` —
wala `build_l2`, wala `detect_setups`, wala `bars.py`. Siku zote zilizofeli §3 zilikuwa zinaingia
kwenye decision points **kimya**, ikiwemo siku 912 zilizoondolewa kwa sahihi ya PD.

Ushahidi ulikuwa kwenye output yenyewe: **EURCHF eligible 49,598 — zaidi ya EURUSD 49,393** —
ingawa mwaka mzima wa 2023 ulikuwa umeondolewa. Siku nane za kazi ya T1 zilikuwa hazina athari.

Baada ya kuunganishwa:

| symbol | kabla | baada | bars zilizoondoka |
|---|---|---|---|
| EURCHF | 49,598 | **43,544** | 6,088 |
| GBPJPY | 49,648 | **43,812** | 5,886 |
| XAUUSD | 47,259 | **40,645** | 6,681 |
| EURUSD (Toleo A) | 49,393 | 49,027 | 368 |

$$259 \text{ siku} \times 24 = 6{,}216 \approx 6{,}088$$

**Rate ya pooled inabaki 4.46%** — kichujio hakikubadilika, ni denominator iliyosafishwa.

### 4.4 Hali ya mwisho ya SETUP-v1

setups **25,374** · control **27,089** · **jumla ya decision points 52,463** ·
holdout imetengwa **7,366**.

### 4.5 Labels (L4) zimejengwa

| | |
|---|---|
| decision points zilizopata labels | **52,321** |
| cells (points × grid 5×5) | **1,308,025** — sawasawa `52,321 × 25` |
| timeout | **2.8%** (kikomo cha §5.5 ni 35%) |
| tie-break | **0.00%** |
| points bila ticks | **0**, kwa symbol zote |
| muda | **2,215s (dakika 37)** |
| 2023 ya EURCHF/GBPJPY/XAUUSD | points **0** — hukumu ya R0 imeshikilia hadi mwisho |

**Timeout 2.8% ndiyo namba muhimu.** Ukaguzi mkuu wa R1 ni jiometri: bila drift,
`p_tp/(p_tp+p_sl)` inapaswa kukaribia `sl/(sl+tp)`. Timeout ikikaribia 35%, ukaguzi huo
ungekuwa unalinganisha sehemu ndogo mno ya sampuli na ungepoteza maana. Kwa 2.8%, unabaki
na meno.

**Tie-break 0.00% — si "haijatokea", ni "haiwezi kutokea".** Nilipima badala ya kufurahia:
kwa BUY, SL **na** TP zote zinapimwa kwa **bid**. Tick moja ingelazimika kuwa `≤ X` na `≥ Y`
kwa wakati mmoja ikiwa `X < Y` — haiwezekani. Jaribio la gap 400 × cells 25 × pande 2:
**0 kati ya 20,000**. §5.2 yenyewe ina hoja hii ndani yake. Kwa hiyo sheria uliyosaini
**haijawahi kuguswa na data hata mara moja**, na haitaguswa kwa grid hii. Inabaki kwa grid
zijazo zinazopima pande mbili tofauti. R1 inaandika hili kwa maneno — "0.00% ✓" peke yake
ingesomeka kama ushahidi wa usalama badala ya ukimya.

### 4.6 Kilichokosekana — na build ya pili

T2 inadai vipimo vitatu ambavyo build ya kwanza **haikuwa imerekodi malighafi yake**:

| Kipimo | Kinatoka wapi | Kwa nini haikuweza kupimwa baadaye |
|---|---|---|
| quantile MID dhidi ya bei ya trade (§5.1) | `terminal_trade` kwa kila point | bei ya kufungia ya mwisho haipo kwenye kilichoandikwa |
| fill/slippage (§5.3, K1-07) | `touch_past_pips` kwa kila cell | bei ya tick iliyogusa barrier haipo — ni bei ya barrier pekee iliyokuwepo |
| M1 dhidi ya tick | ukaguzi wa sampuli wakati wa build | ungehitaji kupita kwenye ticks za miaka 8 mara ya pili |

Vyote vinahitaji **ticks zikiwa tayari kwenye kumbukumbu**. Kuvipata baadaye siyo "kuhesabu
tena" — ni kusoma L0 nzima upya. Kwa hiyo L4 imepanda toleo **2** na build inarudiwa mara moja:
**dakika ~40**. Mbadala ulikuwa kufunga T2 na "haijapimwa" mara tatu, kwenye vipengele
vitatu ambavyo mpango unavitaja kwa jina.

Amri sasa ni moja: `scripts\labels.bat` (setups → labels → R1), yenye onyo lile lile la
`audit.bat` ikiwa branch iko nyuma.

---

## 5. Sahihi zilizowekwa (11)

| # | Kipengele | Uamuzi | Kinachosemwa |
|---|---|---|---|
| 1–4 | DF-05 | APPROVED | `min_coverage` 0.95 · 2023 ya Toleo B inaondoka |
| 5 | DF-05 | **VERIFIED** | 96.1% ya siku; checks saba zote chini ya 0.72% |
| 6 | RS-03 | **VERIFIED** | kalenda kutoka data; Jumamosi 0; sikukuu 16 zote 25Des/1Jan |
| 7 | DF-06 | **VERIFIED** | symbols 12 zina TF 7; A↔B schema moja |
| 8 | DF-07 | **VERIFIED** | as-of imethibitishwa |
| 9 | DF-08 | **VERIFIED** | sentinel ya uvujaji: leaked=0 |
| 10 | DF-14 | **VERIFIED** | G2: folds 5 ndani ya TRAIN+VAL; holdout haijaguswa |
| 11 | DF-20 | APPROVED | SETUP-v1 **pre-registration** |

Lango G14: **PASS** · vipengele `VERIFIED`: **6/64**.

> Sahihi #1–#2 na #3–#4 ni maamuzi mawili yale yale mara mbili — #1–#2 zilisainiwa kabla ya
> `git pull`, kwa hiyo `code_rev` yake inaelekeza mahali ambapo config haikuwa nayo. **#3–#4 ndizo
> za kutumia.** Zinabaki kwa sababu faili ni la kuongezwa tu; mfuatano wenyewe ni ushahidi.

---

## 6. Mafunzo

**Namba isiyowezekana ni mwalimu bora kuliko test.** Kasoro zote kubwa za T1 na T2 zilijitangaza
kwa thamani ambayo haiwezi kuwa kweli — si kwa test iliyofeli. Test zinathibitisha kile
tulichokifikiri; namba inaonyesha kile tulichokisahau.

**Data ya majaribio iliyo safi kupita kiasi inaficha kasoro.** Kasoro nne za T1 zilipita tests 245
kwa sababu data yangu ya majaribio ilikuwa na precision moja, faili zisizopishana, chanzo kimoja.
Sasa tests zinabeba data chafu kwa makusudi.

**Ripoti lazima ijitambulishe.** Ripoti ya code ya zamani inaonekana sawa kabisa na ya mpya. Hilo
lilipoteza **saa nane** tarehe 2026-08-09. Sasa kila ripoti inabeba chapa ya toleo la code +
`code_rev` + muda, na msomaji analalamika ikiwa ya zamani.

**Uamuzi ulioandikwa hauna maana bila kiungo.** Siku 912 ziliondolewa kwa sahihi, zikaandikwa
kwenye config, zikakaguliwa na test — na bado zikaingia kwenye decision points, kwa sababu hakuna
kilichozisoma. Sheria haifanyi kazi hadi kitu kiitumie.

---

## 7. R1 — matokeo (2026-08-13, HUKUMU **PASS**)

**Vigezo vigumu vyote vimepita:** cell ndogo kuliko zote 25,314 (kikomo 200) · timeout 2.79%
(kikomo 35%) · tie-break 0 (kikomo 1%) · G2 safi.

### 7.1 Kichujio kinafanya kazi

| | setup | control | tofauti |
|---|---|---|---|
| p_tp | 0.4173 | 0.3923 | **+0.0251** |
| E[R] gross | −0.0505 R | −0.1142 R | **+0.0638 R** |
| ATR p50 | 16.1 pips | 14.3 pips | +1.8 |

Hii ndiyo namba ambayo control sample ilikuwepo kwa ajili yake. SETUP-v1 haichagui trades chache
tu — inachagua **bora**. Tahadhari mbili za kweli: (1) `z = +28.8` isisomwe kama ilivyo, kwa
sababu cells 25 za point moja si huru; (2) ATR 16.1 dhidi ya 14.3 inaonyesha kichujio kinachagua
volatility ya juu — sehemu ya makali inaweza kuwa **uteuzi**, si utabiri, na features za T3 ndizo
zitakazovitenganisha.

**E[R] hasi ni sahihi.** Entry bila model inalipa spread. −0.0505 R ni **mstari wa kuanzia**
ambao model lazima iuzidi — si tokeo baya.

### 7.2 Jiometri inashikilia kwa muundo unaoeleweka

Tofauti kati ya `p_tp` na `sl/(sl+tp)` **inashuka SL inapopanuka**: −0.042 kwa `sl=0.5` hadi
−0.001 kwa `sl=2.0` (`tp=1.0`). Hiyo ni saini ya **spread** — umbali usiobadilika wa bei ni
sehemu kubwa ya SL nyembamba. Ingekuwa tofauti ya kudumu bila kujali SL, ingekuwa kasoro.

Safu ya `tp=3.0` inatoka nje ya mtiririko kwa sababu halali: timeout yake inafika 22.7%, na
zilizokatwa na horizon ni zile zilizokuwa zikielekea TP ya mbali.

### 7.3 Mambo mawili ya kuchukua mbele

**Cap ya stop ya RCE inagongana na data.** `slippage_cap_pips.stop = 0.3`, lakini kati ya touch
757,424 za SL, **76.06% pekee** ziko ndani ya cap (p50 0.12 · p90 1.06 · max 2,503.7 pips). Ni
kazi ya T7 — **RCE haiguswi sasa** — lakini backtest inayodhani cap inashikilia kila mara inadhani
kitu ambacho feed inakipinga robo ya muda.

**Ticks dhidi ya M1: 0.01%.** Kati ya cells 66,650 zilizoangaliwa mara mbili, M1 ilitofautiana na
ticks mara **9**. Sheria ya §5 ni kweli lakini karibu haina athari kwa grid hii — SL ya 0.5 ATR ni
pana kuliko range ya dakika moja. Ingekuwa na maana kwa barriers nyembamba. Sasa tunajua kwa namba
badala ya kwa hoja.

### 7.4 Quantile MID dhidi ya trade — jibu si dogo

| symbol | spread | ATR | gharama (ATR) |
|---|---|---|---|
| XAUUSD | 35.0p | 356.6p | **0.1049** |
| EURCHF | 1.0p | 9.8p | **0.1043** |
| GBPJPY | 1.6p | 26.0p | 0.0633 |
| EURUSD | 0.3p | 14.4p | **0.0209** |

Uamuzi wako wa §5.1 (MID, si bei ya trade) **unashikilia, na sasa una uzito**: gharama ni
**0.02–0.10 ATR**, si 0.003. Kuiweka pia kwenye L-A kungekuwa kuihesabu mara tatu kwa kiasi
kinachoonekana.

**Lakini spec ilitaja symbols zisizo sahihi.** Ilisema ipimwe kwa "symbols pana (XAUUSD,
GBPJPY)". XAUUSD ndiyo ya juu — lakini GBPJPY ni ya kati, na inayoshindana na XAUUSD ni
**EURCHF**, pair "tulivu" yenye spread ya 1.0p tu. Kinachohesabu si spread bali **spread ÷ ATR ya
symbol yenyewe**. Somo lile lile la sweep ya `min_atr_mult`: kigezo cha pips kinapima **bei**,
cha ATR kinapima **fursa**.

### 7.5 Kigezo kimoja kilikuwa hakiwezi kufeli

`min_labels_per_cell` ilionyesha **25,314 kwa kila cell** — namba ile ile mara 25. Si bahati:
kila decision point inapata cells zote 25, kwa hiyo cells zote zina idadi ile ile **daima**,
data ikiwa yoyote. Ni ukaguzi wa aina ile ile ya `clock_drift` iliyotoa 0/34,089 kwenye T1 —
inapita kwa muundo, si kwa ushahidi.

Kigezo chenye meno ni cha **cell × symbol × fold** — mahali mafunzo yanapofanyika. Symbol yenye
labels 25,314 kwa jumla lakini 40 ndani ya fold moja haiwezi kufundishwa humo, na pooled
haitasema neno. R1 sasa inapima hapo na inaweza kufeli.

### 7.6 Kinachofuata

`r1-summary` mara moja zaidi (sekunde chache — hakuna ujenzi upya). Ikitoa PASS baada ya kigezo
cha fold kuongezwa, T2 iko tayari kwa **sahihi ya exit: R1 PASS**.
