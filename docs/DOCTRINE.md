# ELITEFX — DOCTRINE

Toleo la pili. Lililotangulia lilielekeza utafutaji wa michanganyiko ya
indicators; lilishindwa kwa sababu zilizopimwa, na sababu hizo zimeandikwa
hapa kama msingi wa kile kinachofuata.

---

## 1 · Lengo

> Kugundua strategy za FX zinazothibitika **kitakwimu** kuwa si bahati.

Si kugundua strategy zinazoonekana nzuri kwenye backtest. Tofauti kati ya
mambo hayo mawili ndiyo mradi mzima.

---

## 2 · Kanuni inayotawala

**Kila namba inayoingia kwenye uamuzi lazima ipimwe na injini yenyewe, katika
mchakato huu, kabla ya kutumika.** Hakuna kizingiti kilichorithiwa, hakuna
kilichobuniwa, hakuna kilichochaguliwa baada ya kuona matokeo.

---

## 3 · Kwa nini toleo la kwanza lilishindwa

Sifuri haikuwa hukumu kuhusu FX. Ilikuwa **lazima kihesabu**.

Lango la uchumi lilidai `x̄ ≥ 2c + t·s/√n`. Kwa `s ≈ 165 pips` (iliyopimwa) na
trades 33 (wastani uliopimwa):

```
x̄ ≥ 6.8 + 1.694 × 165/√33 = 55.6 pips kwa kila trade
```

Lango lilikuwa likidai pips 55 kwa kila trade. Waliopita **hawakuwa** kikundi
chenye matumaini — walikuwa walio-overfit kuliko wote kwenye bwawa. Sakafu ya
kelele ikawakataa kwa usahihi.

Mambo matatu yaliyofuata kutoka hapo:

**3.1 · Idadi ya majaribio si kizuizi kikuu.** `K` 1000→240 inashusha bar kwa
0.15 ya Sharpe. Trades 33→3000 inashusha kelele mara 9.5. Majaribio ni gharama
ya **logarithm**; sampuli ni faida ya **mzizi wa pili**.

**3.2 · Trades si uchunguzi.** Trades 33 zilizojilimbikiza kwenye miezi 2 ni
uchunguzi 2–6, si 33. Legs sita kwa tarehe moja ni uchunguzi mmoja.

**3.3 · Miaka 8.25 ina dari.** Kwa majaribio 240, Sharpe ya chini
inayothibitika ni ~1.5. Edge nyingi halisi ziko 0.6–1.0 — **hazionekani**.

---

## 4 · Strategy ni nini

> **Strategy ni vitu SITA vilivyotangazwa. Si utafutaji.**

| | swali | mfano (F0) |
|---|---|---|
| **1 · Nanga** | Tunaangalia lini? | 08:00 Europe/London, kila siku ya kazi |
| **2 · Mwelekeo** | Upande upi, na **kwa nini**? | Uza EUR — makampuni yanunua fedha za kigeni saa zao |
| **3 · Kuingia** | Bei gani hasa? | tick-VWAP ya upande unaotekelezeka, dakika 5 |
| **4 · Stop** | Umbali gani? | `k × ATR(dirisha la kushikilia)` |
| **5 · Kutoka** | Lini au wapi? | 12:00 America/New_York |
| **6 · Ukubwa** | `f(ishara) ∈ [0,1]` | `1.0` — F0 haina ishara |

### 4.1 · Kutoka ni kwa SAA, si kwa bei

Sababu ya kiuchumi ina **umri unaojulikana**. Mtiririko wa mwisho wa mwezi
unaisha fix inapopita. Mtiririko wa saa za nchi unaisha kikao kinapoisha.
Kushikilia zaidi si kushikilia edge — ni kushikilia **kelele**.

`TP` ya bei ingekuwa inakisia sababu inaisha wapi. Saa **inaijua**.

### 4.2 · Stop ni bima, si mkakati

Trade ya masaa manne haipaswi kugonga stop. Ikigonga, kuna kitu kimeharibika —
habari isiyotarajiwa au hitilafu ya kalenda. Stop ipo kufunga msiba, si
kufunga trade.

### 4.3 · Kutengeneza strategy ni KUANDIKA, si kutafuta

```
sababu iliyochapishwa → vitu sita → hash → ledger → endesha MARA MOJA → kubali/kataa
```

**Ikishindwa, haibadilishwi.** Kuhamisha 08:00 kwenda 08:15 *"kwa sababu ndipo
mtiririko unaanza kweli"* ni **jaribio jipya**. Likiwa halijaandikwa, ni njia
ile ile iliyoua toleo la kwanza.

---

## 5 · RCE — mamlaka ya gharama, ukubwa na ruhusa

RCE haibadiliki bila ruhusa wazi. Spec yake iko `docs/RISK_COST_ENGINE.md`.

```
entry → stop → sl_pips → cost_pips → LOTS

lots = risk_per_trade ÷ ((sl_pips + cost_pips) × pip_value_acct)
```

**`sl_pips` iko kwenye denominator.** Lots haziwezi kupatikana kabla ya stop,
na stop haiwezi kupatikana kabla ya entry. Kwa hiyo strategy **lazima**
itangaze entry na stop kabla RCE haijafanya kazi yoyote.

Gharama nayo iko kwenye denominator: SL ikigongwa, hasara **pamoja na spread,
commission na swap** ni **hasa** `risk_per_trade`.

### 5.1 · Kulenga volatility hakuhitaji mfumo wa pili

```
sl_pips = k × ATR(dirisha)   →   lots ∝ 1/ATR
```

Kutangaza stop kwa ATR **kunatoa kulenga volatility kienyewe**. Hakuna
mgongano na RCE, na RCE haibadiliki.

Sehemu ya **ishara** inaingia kwa kupunguza hatari, si lots moja kwa moja:

```
risk_halisi = risk_msingi × f(ishara)        f ∈ [0, 1]
```

---

## 6 · Sifa ya symbol (§ mpya, uamuzi wa PD 2026-09-07)

> **Si "symbol zote kwenye familia zote". Kila symbol inaingia kwenye familia
> inayoifaa — na "inayoifaa" ni kitu kinachopimwa KABLA, si kinachochaguliwa
> baada.**

Kwa kila jozi ya `(familia, symbol)`, malango matatu yanapimwa kabla ya run
yoyote. Yote lazima yapite.

**6.1 · Lango la sababu.** Je sababu ya kiuchumi inahusika na symbol hii?
F1 ni hedge ya hisa zenye dola — haihusiki na EURGBP. Gotobi ni malipo ya
waagizaji wa Japani — ni USDJPY pekee. Hili si la hesabu; linaamuliwa na
sababu iliyochapishwa, na linaandikwa.

**6.2 · Lango la gharama.** `gharama_RT ≤ 8% × σ(dirisha la kushikilia)`.
Chini ya hapo, ishara yenye utabirikaji halisi wa FX haiwezi kuvuka `2×`
gharama. Hii ni hesabu, si maoni.

**6.3 · Lango la mzunguko.** Matukio ya kutosha kufikia `n ≥ (t*/s)²` kwa
Sharpe-kwa-tukio `s` iliyotangazwa kwa familia hiyo.

Matokeo ni **jedwali la sifa**: familia × symbols → ndani/nje, likiwa
limeamuliwa na kuandikwa kabla ya run. Symbol iliyokataliwa haiingii kwenye
hesabu ya majaribio wala kwenye pooling.

---

## 7 · Kipimo lazima kithibitishwe kabla ya familia yoyote

Toleo la kwanza lilikalibrisha **kiwango cha kukosea kwa kupitisha** na
halikuwahi kupima **uwezo wa kuona**. Halitarudiwa.

**7.1 · Udhibiti chanya.** Panda edge inayojulikana **kwenye bei, kabla ya
uteuzi** — si kwenye P&L baada yake. Maumbo matatu: thabiti · sawia na
volatility na iliyojilimbikiza kwenye miezi michache · yenye mfululizo.
Ripoti dhidi ya `δ = (μ/σ)√n`.

> **LANGO 1.** Injini isipoona edge iliyopandwa kwa `δ` inayolingana na
> familia zetu, **hakuna familia inayojengwa.** Kasoro inatafutwa, kisha
> inaendeshwa tena.

**7.1a · Matokeo ya LANGO 1 (2026-09-08 · `2e8e5ef`).** Siku 500 · SL 25 pips ·
spread 1.6 · σ 13 pips/saa · replicates 10 · B 400 · α 0.05. Mnyororo mzima
ulipimwa: ticks → kikapu → RCE → trades → curve ya siku → block bootstrap.

```
umbo         pips        δ   iliyopimwa  kinadharia    pengo
CONSTANT     0.00    -1.12         0.0%        0.3%    +0.3%
CONSTANT     4.00     1.13        30.0%       30.5%    +0.5%
CONSTANT     8.00     3.36       100.0%       95.7%    -4.3%
CLUSTERED    4.00     1.15        20.0%       31.0%   +11.0%
CLUSTERED    8.00     3.27        90.0%       94.8%    +4.8%
SERIAL       4.00     1.29        40.0%       36.2%    -3.8%
SERIAL       8.00     3.58        90.0%       97.4%    +7.4%
```

Pengo kubwa kuliko yote (pale kinadharia > 50%): **+7.4%**, chini ya kikomo cha
30%. **Lango limepita.** Injini inaona edge iliyopandwa karibu na kikomo cha
kinadharia; hakuna hatua inayopoteza ushahidi kwa kiasi kikubwa.

Mipaka mitatu ya usomaji, ambayo lazima isemwe pamoja na jibu:

1. **`pips = 0` si kipimo cha UKUBWA.** Hapo wastani wa kweli ni **hasi**
   (`δ = −1.12`, ni gharama), kwa hiyo 0% inaonyesha tu kwamba injini
   haitangazi strategy inayopoteza. Ukubwa halisi wa bootstrap umepimwa
   pekee kwenye `tests/analysis/test_bootstrap.py`: **1–12%** kwa replicates
   120, `ρ = 0` na `0.5`.
2. **Replicates 10 zinatoa azimio la ±15%** kwa kila kiwango. Pengo la ±7% liko
   ndani ya kelele. Hitimisho la kweli ni *"hakuna pengo kubwa lililoonekana"*,
   si *"pengo ni 7.4%"*.
3. Kupanda kunafanywa kwenye **ticks za bandia** zenye σ iliyotangazwa. Kwa
   familia halisi, σ ya kila tukio itapimwa kwenye data halisi kabla ya
   kutafsiri nguvu.

**7.1b · Kalibrisheni inayotokana nayo.** `δ` ni ya mstari kwa pips na inakua
kwa `√n`:

```
δ(pips, n) = (−1.12 + 0.5625·pips) · √(n / 500)
```

| edge gross | δ @ vikao 2,100 | nguvu @ 2,100 |
|-----------:|----------------:|--------------:|
| 2 pips     | 0.01            | 5%            |
| 3 pips     | 1.17            | 32%           |
| 4 pips     | 2.33            | 75%           |
| 5 pips     | 3.48            | 97%           |

Edge inayohitajika kwa nguvu 50% (`δ = 1.645`): siku 500 → **4.9 pips** ·
F0 kwa vikao 2,100 → **3.4 pips** · F1 kwa matukio 99 → **8.5 pips**.

Maana yake kwa mzunguko wa kwanza, ikiwa σ ya kila tukio ni karibu na
iliyotangazwa hapa: **F0 inaonekana tu ikiwa iko juu ya safu yake
inayotarajiwa (2–4 pips gross).** Hilo si sababu ya kuiacha — ni sababu ya
kujua, kabla ya kujenga, kwamba jibu la "hakuna" litamaanisha *"chini ya
3.4 pips"* na si *"sifuri"*. F1 yenye matukio 99 pekee inahitaji edge kubwa
mara mbili na nusu; ndiyo gharama halisi ya familia ya mara moja kwa mwezi.

**7.2 · Kitengo cha uchambuzi.** Curve ya P&L ya portfolio kwa siku, katika
vipimo vya R. Block bootstrap, urefu kutoka Politis–White, chini kabisa siku
21. Siku **hai** zinaripotiwa, si siku za kalenda.

**7.3 · Surrogate mbili.**
- **Kalenda:** kuzungusha kwa mizidisho ya **siku 7** (si 24h — hiyo inaharibu
  siku ya wiki), kwa saa za mtaa, ndani ya mwaka mmoja.
- **Kuchanganya ishara:** tarehe zilezile, bei zilezile, ishara zimechanganywa.

Familia ya kalenda safi inapata ya kwanza; familia yenye ishara ya nje inapata
ya pili. Kuchanganya bei kwa familia yenye ishara kungeharibu uhusiano
unaozalisha ishara yenyewe — null isingekuwa na ishara kabisa, na kila kitu
kingeonekana muhimu.

**7.4 · Injini ya saa za matukio.** `(timestamp, offset, dirisha) → tick-VWAP
ya upande unaotekelezeka`. Ask kwa kununua, bid kwa kuuza. **Si mid** — mid
ingerudisha nusu ya spread kama edge ya uongo.

---

## 8 · Nidhamu

**8.1 · Ledger inayoongezwa tu.** Kila run, ikiwa ni pamoja na
iliyoachwa. Jaribio ni **ufafanuzi wowote tofauti ambao ungeweza kuchaguliwa**
— parameter, symbol, dirisha, sheria ya kutoka, regime.

**8.2 · Utekelezaji wa kundi na matokeo yaliyofungwa.** Gridi nzima
inaendeshwa hadi mwisho, matokeo yanaandikwa kwenye faili iliyofungwa,
inafunguliwa baada ya kundi kumalizika. Kusimamisha run mapema kwa sababu
inaonekana mbaya ni **uteuzi usioachwa alama**.

**8.3 · Mgao wa `α`.** Utafutaji wa toleo la kwanza (K=12,000) ni familia
iliyofungwa iliyotumia `α = 0.01` na haikutoa chochote. Programu hii inapata
`α = 0.04`:

```
mzunguko 1  0.020
mzunguko 2  0.015
akiba       0.005
```

Halali **kwa sharti moja lililoandikwa**: familia mpya zilitoka kwenye
machapisho, si kwa kuangalia waliokaribia kufaulu kwenye utafutaji ulioshindwa.

**8.4 · Uteuzi wa familia ni jaribio.** Familia tatu zikishindwa na ya nne
ikifaulu, kuiboresha ya nne ni data-snooping. Uboreshaji wote unabaki ndani ya
ledger.

**8.5 · Kila lango lina jibu la "hapana" lililoandikwa mapema.** Kufeli
hakuelezwi, hakurekebishwi, hakuendeshwi upya kwa vigezo vipya.

---

## 9 · Familia — mzunguko wa kwanza

Kigezo cha kuchagua familia ya kwanza si *"ipi itafanya kazi"* bali
***"ipi itatujibu"***. F0 ina matukio 2,100; ushahidi wake unaishia 2007, kwa
hiyo hatujui itafanya kazi — lakini tutajua **jibu**.

| | familia | nanga | matukio | kizingiti | majaribio |
|---|---|---|---|---|---|
| **F0** | Mtiririko wa saa za nchi | 08:00 · 17:00 London · 16:30 NY | **1,924** siku (legs 3,848) | 3.4 bps | 1 |
| **Gotobi** | Malipo ya waagizaji wa Japani | 08:30 → 09:50 JST, siku ÷ 5 | **500** | 2.8 bps (pips 3.9) | **1** |
| **F1** | Hedge ya hisa → fix ya mwisho wa mwezi | 16:00 London ±(60, 15) dk | **96** | 5.2 bps (pips 5.7) | **1** |

**9.0 · F0 imetangazwa** (`src/families/f0.py`, fingerprint kwenye ledger).
Legs mbili kwa siku, mielekeo tofauti: `A` kufunguka→kufunga London **SELL**
(saa za ndani za euro), `B` kufunga London→kufunga New York **BUY** (saa za
ndani za dola). Kwamba zinapingana ndiyo inayofanya F0 isiwe bet ya mwelekeo
wa dola.

**Nanga ya kati ni 17:00 Europe/London, si 12:00 NY** kama jedwali
lilivyoandika kwa kifupi. Ni kitu kile kile kwa wiki 49/52; zinatofautiana
kwenye wiki za mpito wa DST. Kipimo 2018–2025: **siku 131 kati ya 1,924
(6.8%)**. Mekanizimu unasema *"madawati ya Ulaya yanaenda nyumbani"* — hiyo ni
saa ya London. Kushika mpaka wa Ulaya kwenye saa ya Marekani kungefupisha leg A
hadi masaa 8 kwa siku hizo 131, kwa sababu ya nchi isiyohusika. Ndiyo kasoro
ambayo §11 inaionya. Marekebisho haya ni **tangazo**, si uteuzi: yameandikwa
kabla ya row moja ya data kusomwa, mbadala haujaendeshwa, na hayagharimu
jaribio.

Matukio ni **siku 1,924**, si 2,100 kama ilivyokadiriwa. Curve ni ya siku, kwa
hiyo `n` ya bootstrap ni 1,924 — `√(1924/2100) = 0.957` ya nguvu ya §7.1b.
Legs mbili kwa siku zinarudisha sehemu ya hiyo, kwa sababu wastani wa siku
unabeba matukio mawili.

**Stop ni `4.0 × wastani wa |kutoka − kuingia|` kwa vikao 20 vilivyopita.** Si
ATR: injini inasoma ncha mbili za dirisha (dakika 20 kati ya 1,440), si dirisha
zima, kwa hiyo high-low haipatikani. `4.0` inatoka kwenye hesabu, si ladha:
`E|X| = 0.798σ`, kwa hiyo stop ni `3.19σ` na `P(kuvuka) ≈ 0.3%`.

**Lango la 6.2 linapimwa kwa KILA leg.** Leg A ni masaa 9, leg B ni 4.4 —
`σ ∝ √muda`, kwa hiyo uwiano wa gharama wa leg B ni mbaya kwa mara ~1.4.
Kuchanganya legs kungefanya leg fupi ijifiche nyuma ya ndefu. Familia ni
yote-au-hakuna, kwa hiyo lango linaamuliwa na **leg mbaya kabisa**.

**Jumla ya majaribio ya mzunguko 1 = 8.** `0.020/8 = 0.0025` → **z ≈ 2.81**.

F1 ina matukio **99**, si 594. Legs sita kwa tarehe moja ni uchunguzi mmoja.
Kitu chochote chini ya **3 bps** ni null bila kujali `p`.

**Kupungua kwa mwaka kunapimwa kwa kila familia.** Ushahidi wa F0 unaishia
2007; Gotobi inauzwa kama EA sokoni. Msongamano unatarajiwa.

### 9.2 · F0 — JIBU (2026-09-08, EURUSD, 2018–2025)

Malango yote matatu ya §6 yamepita **kabla ya `p` kuhesabiwa**: sababu ·
gharama 6.6% (leg B, kikomo 8%) · matukio 1,913 dhidi ya 86 yanayohitajika.
Kisha:

```
trades 3,825 · siku hai 1,913/1,924
wastani  −0.02323 R/siku   ·   p 0.9740   ·   CI95 [−0.04515, −0.00095]
kizingiti: p ≤ 0.0025
```

**F0 HAIJANUSURIKA.** Jaribio **1 kati ya 8** limetumika; yaliyobaki 7.

> **Namba hizi zilitolewa na injini yenye kasoro** (stop haikuigwa — §11).
> Zinabaki hapa kama rekodi. Jibu linalotumika ni la §9.3.

> Run hii ilifanywa chini ya fingerprint **`d510f52d40922d45af3099b64ea8cfe6`**,
> ambapo tangazo lilisema *"njia haiigwi"*. Tangazo la sasa
> (**`2929bc0cdfd04487fea3f5fc32814686`**) linasema *"ikigongwa, R = −1.0"*.
> Ni familia mbili tofauti kwa mkataba wa §8.1 — na ndiyo maana zote mbili
> zimeandikwa. Ya kwanza ndiyo iliyotoa namba zilizo hapo juu. **Ya pili
> haitaendeshwa**: F0 imefungwa, na mwelekeo wa marekebisho unajulikana
> (kuiga stop kunaweza tu kufanya matokeo hasi yawe mabaya zaidi).

**Kuvunja namba.** Gharama pekee, bila edge yoyote, ingetoa:

```
leg A   1R = 124.8 pips   gharama 1.00p   →  −0.00801 R/siku
leg B   1R =  51.7 pips   gharama 1.05p   →  −0.02033 R/siku
                                    jumla  =  −0.02834 R/siku
```

Iliyopimwa ni **−0.02323**. Kwa hiyo gross ni **+0.00511 R/siku** —
**pips 0.26–0.64 kwa siku**, dhidi ya gharama ya **pips 2.05**. CI ya gross ni
`[−0.017, +0.027]`, yaani **sifuri iko ndani yake**, na ncha ya juu kabisa
inayoruhusiwa na data ni pips 1.4–3.4 — hasa kizingiti tulichotangaza kwamba
tunaweza kuona (§7.1b: pips 3.4 kwa nguvu 50%).

Mekanizimu **haujageuka; umepungua chini ya gharama.** Ishara iko upande
uliotangazwa, ni ndogo mno kuliko spread. Ushahidi wa Ranaldo unaishia ~2007;
sampuli yetu inaanza 2018.

**Hii ndiyo aina ya jibu §12 iliyoahidi.** Si "hatujui" — ni "chini ya pips
3.4, na uwezekano mkubwa karibu na 0.4", ikiwa na kizingiti kilichoandikwa
kabla ya run.

F0 haielezwi, hairekebishwi, haiendeshwi upya kwa vigezo vipya (§8).

**Vitu vitatu vilivyopatikana wakati wa run hii, ambavyo si vya F0:**

1. **RCE haihitaji v2 (Lango 3 limejibiwa).** Pengo kati ya kadirio la RCE na
   spread halisi ya ticks: wastani **+0.022 pips**, p95 **+0.096 pips** kwa
   trades 3,825. Kadirio ni sahihi ndani ya pip moja ya kumi. **RCE inabaki
   kama ilivyo.**
2. **Gharama halisi ni nusu ya iliyodhaniwa:** round-turn **1.00–1.05 pips**,
   si 2.3. Namba hii inaingia kwenye malango ya familia zinazofuata.
3. **Kanuni ya normal inakadiria stop chini kwa mara ~10.** Ona §11.

### 9.4 · Gotobi imetangazwa (`src/families/gotobi.py`, `06a78b1b…`)

Benki za Japani zinaweka **nakane** (仲値) saa 09:55 Asia/Tokyo — kiwango
kimoja cha siku kwa miamala yote ya wateja. Waagizaji wanalipa siku za
**gotobi** (tarehe ÷ 5), kwa hiyo mahitaji ya dola yanajilimbikiza na benki
zinabidi zinunue dola sokoni kabla ya fix. **BUY USDJPY**, leg moja, saa
1.33. Ni mtiririko wa **mkataba** — mwagizaji hana chaguo la kutolipa.

**Jaribio 1, si 2.** Bajeti ilitenga mawili; ninatumia moja kwa sababu kuna
ufafanuzi mmoja tu unaotokana na mekanizimu. Jumla ya mzunguko inashuka
`8 → 7`, lakini kizingiti kinabaki `p ≤ 0.0025` (kilichotangazwa kwa 8).
Kutumia machache kuliko bajeti ni **kali zaidi**, si laini.

Vitu vitatu vilivyoamuliwa na mekanizimu, si na urahisi:

1. **Kutoka kunaishia kwenye fix, hakuanzii hapo.** Shinikizo lipo kabla ya
   09:55. `execute` inasoma `[kutoka, kutoka+300s)`, kwa hiyo nanga ni
   `09:55 − 300s = 09:50`. Kuchukua `[09:55, 10:00)` kungekuwa kuuza baada ya
   mtiririko — kungefuta edge **kwa ufafanuzi**, si kwa soko.
2. **Kalenda ya benki za Japani** (`events/jp_calendar.py`). Gotobi ni siku ya
   malipo; tarehe ÷5 ikianguka siku isiyo ya kazi, malipo yanasogezwa mbele.
   Bila kalenda, **tarehe 66 kati ya 548 (12%)** zingeshikwa vibaya.
   Chaguo-msingi ni kalenda, si `()` — kusahau hakupaswi kukubalika kimya.
3. **Thamani ya pip ya JPY inabadilika kwa bei.** `1000 ÷ bei`: `$9.80` kwa
   102, `$6.17` kwa 162 — tofauti ya **37%** kwenye sampuli yetu. Kuiweka
   thabiti kungebadilisha `commission_pips` kwa kiasi kile kile, na lango la
   §6.2 lingeamua kwa namba isiyo sahihi.

Matukio yaliyopimwa: **500** (si ~600), ~62 kwa mwaka, thabiti. `n` ya
bootstrap ni 500 — nguvu ni `√(500/1913) = 0.51` ya F0.

**Ubashiri ulioandikwa kabla ya run.** Dirisha ni saa 1.33 pekee; `σ` inakua
kwa `√muda`, gharama haikui. Ninabashiri `gharama/σ ≈ 17%` dhidi ya bajeti ya
**8%** — yaani **Gotobi itakwama kwenye lango la gharama (§6.2), si kwenye
`p`.** Likikwama, jibu ni *"dirisha ni fupi mno kwa gharama hii"*, na
**halitagharimu α hata kidogo**.

Makadirio yangu yameshakosea mara mbili kwenye mradi huu (kugongwa kwa stop
kwa mara 6; marekebisho ya §9.3 kwa mara 15). Lango linapimwa, halikadiriwi.

---

#### JIBU (2026-09-09) — Gotobi HAIINGII, na haiwezi kuingia

```
trades 276/500 · siku hai 276 · zilizogongwa stop 3 (1.09%)
σ 15.17 pips · gharama 1.41 pips · uwiano 9.3%  dhidi ya bajeti 8%
LANGO LA GHARAMA (§6.2) LIMEKATAA. `p` haijahesabiwa.
```

**Jaribio HALIJATUMIKA.** Symbol iliyokataliwa na §6 haiingii kwenye hesabu ya
majaribio wala kwenye pooling. Mzunguko bado una **6** kati ya 7.

**Ubashiri wangu ulikuwa mbaya kwa mara 1.8** — nilibashiri 17%, halisi ni
9.3%. σ ilikuwa kubwa (15.17 dhidi ya 12) na gharama ndogo (1.41 dhidi ya
2.1) kuliko nilivyokadiria. Ni ubashiri wangu wa **tatu** uliokosea kwenye
mradi huu.

**Haiwezi kuingia kwa nanga yoyote inayokubalika na mekanizimu.** Hii si
maoni; ni hesabu:

```
σ inayohitajika kwa 8%     =  1.41 / 0.08  =  17.62 pips
σ ∝ √muda                  →  dirisha  1.80 saa
kuingia kungekuwa                          08:02 JST
Tokyo inafunguka                           09:00 JST
```

Kuingia mapema zaidi kunahitajika ili kupita, lakini mapema zaidi ni
**mbali zaidi na mtiririko**, si karibu. Na kwenda upande mwingine kunazidi
kuwa mbaya:

```
kuingia 09:00 (kufunguka Tokyo)   saa 0.83   σ 11.99   uwiano 11.8%
kuingia 08:30 (iliyotangazwa)     saa 1.33   σ 15.17   uwiano  9.3%
```

Hakuna nanga inayopita. **Gotobi imefungwa.**

**Kilichokataa si soko — ni muundo wa akaunti.** Kwa bei ~130:

```
commission   0.91 pips   (65% ya gharama)
spread       0.50 pips   (35%)
bila commission:  uwiano 3.3%   ← lingepita kwa urahisi
```

`$7` kwa lot round-turn ni ndogo kwa dirisha la saa 9; kwa dirisha la saa 1.3
ni **theluthi mbili ya gharama yote**. Familia za dirisha fupi zimezuiwa na
muundo wa gharama, si na kukosa edge — na hilo halijulikani mpaka lipimwe.
**Ni uamuzi wa broker, si wa utafiti**, na ukifanywa lazima utangazwe kabla
ya run yoyote.

**Kasoro ya data iliyopatikana njiani.** Madirisha **185 kati ya 500 (37%)**
hayakuwa na tick hata moja saa 23:30 UTC — yaani **08:30 JST, kabla Tokyo
haijafunguka**. Nanga niliyoichagua ilikuwa na kasoro ya mekanizimu tangu
mwanzo: flow ya nakane haipo kabla ya soko kufunguka, na feed inathibitisha.
Haibadilishi jibu (lango limekataa kwa sababu nyingine), lakini inaandikwa:
**familia yoyote ya baadaye yenye nanga kabla ya 09:00 JST lazima ithibitishe
ukwasi kwanza.**

### 9.3 · F0 inapimwa upya MARA MOJA, kwenye injini iliyorekebishwa

Namba za §9.2 zilitolewa na injini yenye kasoro inayojulikana (§11): stop
haikuigwa. Nilidhani mwelekeo wa marekebisho unajulikana; **haukujulikana**,
na kipimo cha 2021 kimeonyesha kinaboresha kwa `+0.011 R/siku`.

**Hii si kuendesha upya baada ya kufeli** (§8). Tofauti ni ya msingi na
inaandikwa hapa ili isije ikadaiwa vinginevyo:

1. Kasoro ilipatikana na **kipimo kilichotangazwa** (`--angalia-stop`), si
   kwa kutafuta sababu ya kufeli. Ingerekebishwa hata kama F0 ingenusurika.
2. **Tangazo halibadiliki** — mekanizimu, nanga, mwelekeo, `k`, kila kitu ni
   kile kile. Ni injini iliyorekebishwa, si dhana mpya.
3. **Sheria ya uamuzi imeandikwa kabla:** `p ≤ 0.0025`. Ile ile.
4. Namba mpya **inachukua nafasi** ya ya zamani kama jibu; ya zamani inabaki
   kwenye rekodi kama historia. **Hatuchagui iliyo bora kati ya mbili.**

Jaribio ni **lile lile**, si la pili. F0 imeshatumia moja kati ya nane.

**Ubashiri kabla ya run** (ili usomaji usije ukaathiriwa na matokeo): ikiwa
marekebisho ni sawia na ya 2021, wastani wa miaka nane utakuwa takribani
`−0.0125 R/siku`, gross takribani `+0.016 R/siku` = **pips 0.8–2.0 kwa siku**,
chini ya kizingiti cha pips 3.4. **Ubashiri wangu: F0 bado haitanusurika.**
Ikinusurika, ni jibu — na nitasema hivyo.

---

#### JIBU LA MWISHO (2026-09-09, injini iliyorekebishwa)

```
trades 3,825 · zilizogongwa stop 70 (1.83%) · siku hai 1,913/1,924
wastani  −0.02255 R/siku   ·   p 0.9710   ·   CI95 [−0.04388, −0.00104]
kizingiti: p ≤ 0.0025
```

**F0 HAIJANUSURIKA.** Familia imefungwa. Jaribio 1 kati ya 8 limetumika.

**Ubashiri wangu ulikuwa mbaya kwa `0.0100`** — nilibashiri `−0.0125`,
halisi ni `−0.02255`. Nilipanua marekebisho ya 2021 (`+0.0107`) kwa miaka
nane; halisi ilikuwa **`+0.00068` pekee, 3.0% ya jumla**. Sababu: athari
mbili za stop zinafutana kwa muda mrefu, ingawa hazikufutana mwaka 2021.

```
stops (70 × −1R)         −0.03638 R/siku
zilizomaliza kwa saa     +0.01383 R/siku
                         ─────────
                         −0.02255
```

Gharama kwa trades **zote** (iliyomo ndani ya −1R ya zilizogongwa pia):
`54.21 R` = `0.02817 R/siku`. Kwa hiyo:

```
gross bila masharti   +0.00562 R/siku   =  pips 0.29 – 0.70 kwa siku
CI ya gross           [−0.0157, +0.0271] =  ncha ya juu pips 1.4 – 3.4
gharama                                     pips 2.05 kwa siku
```

Sifuri iko ndani ya CI. Ncha ya juu kabisa inayoruhusiwa na data ni **pips
3.4** — hasa kizingiti tulichotangaza kwamba tunaweza kuona (§7.1b).
Hitimisho la §9.2 halijabadilika hata kidogo (`gross +0.00511 → +0.00562`).

**Kugongwa kwa stop, kwa mwaka:**

```
2018  7 · 2019  7 · 2020  8 · 2021 12
2022  7 · 2023  6 · 2024  8 · 2025 15
leg A 26/1,912 (1.36%)   ·   leg B 44/1,913 (2.30%)
MAE p50 14.3p · p95 69.3p · kubwa 250.7p
```

Kiwango ni thabiti kwa miaka minane, na ni mara **sita** ya 0.3% ya kanuni
ya normal. Leg B inagongwa mara mbili zaidi ya leg A: stop yake ni pips 51
dhidi ya 125, na gharama ya pip 1.05 ni sehemu kubwa zaidi yake.

**Lango 3 limethibitishwa tena** kwenye trades 3,755 zilizomaliza kwa saa:
pengo la spread wastani **+0.022p**, p95 **+0.096p**. RCE inabaki kama ilivyo.

### 9.1 · Zilizosimamishwa, kwa hesabu

| | sababu |
|---|---|
| **F4 momentum** | Inasawazisha kila mwezi → uchunguzi **99**, si 990. Inahitaji 7.2%/mwaka; inayowezekana G10 ni 2–4%. |
| **F2 benki kuu** | Matukio 66 ya Fed, `σ` 60 bps → inahitaji 24 bps; iliyochapishwa ni 8–10 bps. `t ≈ 1.1`. Pia ushahidi ulikufa baada ya 2015, na sampuli yetu inaanza 2016. |
| **F3 namba za mviringo** | Mzunguko 2, ikiwa imeundwa upya: ndani ya siku, stop **ipite namba inayofuata** — kama ilivyo inaweka stop ndani ya msongamano wa stops. |
| **R1 triangles** | Ufafanuzi haujakamilika. Triangle halisi ina residual sifuri. |
| **Dhahabu** | Gharama/σ ni mara 3 nafuu, lakini hakuna familia ya mzunguko 1 inayoihitaji. Njia ya pili. |
| **Historia 2003** | Baada ya mzunguko 1. Kwa F0 pekee, kwa uthibitisho, kwa gharama ya adhabu. F1 haiwezi — kabla ya 2015 ni soko lingine. |
| **ML** | Baada ya familia mbili. Meta-labelling, utabiri wa volatility/gharama, regime discovery. **Kamwe kutabiri mwelekeo.** |

---

## 10 · Kutoka "imethibitika" hadi kutrada

Familia inayopita malango yote bado si strategy.

1. **Uchambuzi wa vipengele** — USD · carry · momentum · volatility ·
   iliyobaki. Faida yote ikitoka kwenye kipengele kinachojulikana, hatujagundua
   kitu.
2. **Msongamano** — mchango wa mwaka kwa mwaka · siku 5 bora kama % ya P&L ·
   utendaji baada ya kuondoa mwezi mmoja mmoja.
3. **Mtihani wa gharama** — lazima inusurike **mara 1.5** ya gharama
   iliyopimwa.
4. **Holdout** — mara **moja**. Sheria imeandikwa na ku-hash kabla ya
   kuiangalia. Kufeli hakuelezwi.
5. **Karatasi kisha ukubwa mdogo** — na sheria ya kuua iliyoandikwa mapema.
   Miaka miwili ya kwanza ni ukusanyaji wa data, si faida.

---

## 11 · Hitilafu zinazojulikana — majaribio kabla ya familia

Zote zinatokea **kwa mifumo**, si kwa nasibu, kwa hiyo hazionekani kama kelele.

- **DST.** London 16:00 ni New York 11:00 au 12:00 kutegemea wiki; EU na US
  zinabadilisha tarehe tofauti. **F0 ndiyo iliyo hatarini zaidi** — imeshikwa
  kwenye nanga mbili zinazohama kwa tarehe tofauti. Wiki ~6/mwaka × miaka 8 ≈
  **matukio 240 yaliyoshikwa vibaya**.
- **Siku ya mwisho ya mwezi inatofautiana kwa nchi.** 31 Desemba ni sikukuu
  Japani, si Uingereza.
- **Bar ya Jumapili** ni sehemu ya siku kwenye mpaka wa 17:00 New York.
- **Jumatano ya swap mara tatu.**
- **RCE inategemea mpangilio wa kuwasili.** `max_open_trades` inaangusha trade
  zipi ikitegemea nani amefika kwanza. Jaribio linalochanganya mpangilio na
  kudai P&L ile ile lazima liandikwe.
- **Njia kati ya kuingia na kutoka — IMETATULIWA (2026-09-09).**

  Toleo la kwanza lilichukua bei mbili na kudhania stop haigongwi.
  **Kipimo: 3.0%** ya vikao 200 vya F0, si 0.3% niliyokadiria kwa kanuni ya
  normal. Sababu mbili: mikia minene ya FX, na kwamba SELL inaingia kwa
  `bid` na kufungwa kwa `ask`, kwa hiyo **spread nzima imo ndani ya kila
  mwendo** — stop ya pips 25 iko karibu na soko kuliko namba 25 inavyoonyesha.

  Upendeleo uliokuwa ukitokana nayo: **+0.036 R/siku**, wakati athari nzima
  ya F0 ilikuwa 0.023. **Kasoro kubwa kuliko kitu chenyewe.**

  `runner.execute` sasa **inapima njia** kwa kila trade (uamuzi wa PD).
  MAE ndani ya `[kuingia + dirisha, kutoka)` ikivuka stop, trade inakufa
  hapo kwa `R = −1.0` **hasa** — usawa ni wa RCE (`risk_at_stop = lots ×
  (sl + cost) × pip_value`), si wa kwetu.

  Chaguo mbadala — kupandisha `k` mpaka kugongwa kuwe nadra — lilikataliwa:
  linaacha upendeleo wa mabaki, na stop isiyogongwa kamwe si bima (§4.2),
  ni kipimo cha lots tu. `k` inabaki **4.0**; kugongwa kunaigwa, si
  kuepukwa.

  Kilichoachwa kwa makusudi: dakika tano za kujaza na tano za kutoka
  hazihesabiwi (dakika 10 kati ya masaa 9), na fill inadhaniwa kutokea hasa
  kwenye kiwango cha stop. Vyote vinaelekea upande wa **matumaini**, kwa
  kiasi kinachojulikana, na `mae_pips` inarekodiwa ili kiweze kuonekana.

  **MAREKEBISHO (2026-09-09).** Niliandika hapa kwamba kuiga stop *"kunaweza
  tu kufanya matokeo hasi yawe mabaya zaidi"*. **Si kweli, na kipimo
  kimeonyesha.** Kuiga stop kuna athari mbili zinazopingana:

  ```
  trade iliyogusa stop kisha ikapona   →  ilirekodiwa > −1R, sasa −1R   MBAYA
  trade iliyovuka stop na ikabaki nje  →  ilirekodiwa < −1R, sasa −1R   NZURI
  ```

  Ya pili ni **kukata hasara**: stop inazuia kupoteza zaidi ya 1R. Ndiyo kazi
  yake. Nilisahau upande huo kabisa.

  Kipimo (F0, 2021, tangazo lile lile, injini mbili):

  ```
  bila kuiga stop   −0.03944 R/siku   CI [−0.0767, −0.0010]
  kwa kuiga stop    −0.02875 R/siku   CI [−0.0619, +0.0047]
                    ─────────
  tofauti           +0.01069            ← IMEBORESHA
  ```

  Kugongwa: **2.38%** (leg A 0.9%, leg B 3.9%) — inakubaliana na 3.0% ya
  sampuli. MAE p50 11.0p · p95 51.0p · kubwa 121.1p.

  Kwa hiyo **§9.2 inahitaji kupimwa upya**, na mwelekeo wa marekebisho
  haukujulikana kabla. Ona §9.3.

---

## 12 · Ahadi

**Njia hii inatoa jibu la kuthibitika-au-kukataliwa. Haiahidi strategy.**

Jibu linalowezekana zaidi ni kwamba familia moja au mbili zitanusurika, au
hakuna hata moja. F0 ikinusurika kwenye EURUSD pekee kwa Sharpe 0.4 — hiyo ni
mafanikio.
