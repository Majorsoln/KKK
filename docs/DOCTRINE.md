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

**8.6 · Swali la mlipaji.** (Imeongezwa 2026-09-10, baada ya ukosoaji wa nje.)

Niliandika mahali pengine kwamba *"wazo linalojulikana na kila mtu, na
linaloweza kuandikwa kwa sheria rahisi, halibaki likilipa kwa muda mrefu."*
**Ile ilikuwa dhana, si nadharia, na niliiandika kama nadharia.** Ni ya uongo
kwa mifano inayojulikana: carry inajulikana tangu 1980 na bado inalipa;
month-end rebalancing imechapishwa tangu 2009 na bado ina athari kwenye baadhi
ya matukio; risk premia nyingi zinajulikana **na** zinalipa kwa sababu mtu
fulani analazimika kulipa.

Inabadilishwa na swali linalojibika:

> **Ni nani analipa kwa edge hii? Kwa nini analipa? Na kwa nini
> hawajaweza — au hawataki — kuiondoa?**

Kila familia lazima ijibu swali hili **kwa maandishi, kabla ya kupimwa**,
pamoja na mekanizimu ya §6.1. Majibu halali ni ya aina tatu:

```
LAZIMA        mlipaji ana wajibu (mandate, hedge ratio, index tracking,
              settlement) — analipa hata akijua gharama
HAJALI        mlipaji ana lengo lingine (corporate flow, tourism,
              remittance) — gharama ni ndogo kwake kuliko muda wake
HAWEZI        edge ipo lakini uwezo wake ni mdogo, au gharama ya
              kuivuna inazidi thamani kwa mchezaji mkubwa
```

Ikiwa hakuna jibu kati ya matatu, familia haitangazwi. Na **jibu hili si
ushahidi kwamba edge ipo** — ni sharti la kuingia tu, si kipimo.

---

## 9 · Familia — mzunguko wa kwanza

Kigezo cha kuchagua familia ya kwanza si *"ipi itafanya kazi"* bali
***"ipi itatujibu"***. F0 ina matukio 2,100; ushahidi wake unaishia 2007, kwa
hiyo hatujui itafanya kazi — lakini tutajua **jibu**.

| | familia | nanga | matukio | kizingiti | majaribio |
|---|---|---|---|---|---|
| **F0** | Mtiririko wa saa za nchi | 08:00 · 17:00 London · 16:30 NY | **1,924** siku (legs 3,848) | 3.4 bps | 1 |
| **Gotobi** | Malipo ya waagizaji wa Japani | 08:30 → 09:50 JST, siku ÷ 5 | **500** | 2.8 bps (pips 3.9) | **1** |
| **F1** | Hedge ya hisa → fix ya mwisho wa mwezi | 16:00 London ±(60, 15) dk | **96** · legs **4** | 5.2 bps (pips 5.7) | **1** |

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

### 9.5 · F1 — lango la §6.2 limefunguka kwa NNE kati ya sita

`scripts/gate_probe.py`, 2026-09-09, matukio 96, dirisha saa 1.25,
commission $7/lot. **Hakuna strategy iliyoendeshwa; hakuna α iliyotumika.**

```
symbol         σ   gharama   uwiano   jibu    pengo hadi 8%
EURUSD     26.25      1.02    3.89%   PITA    +1.080 pips
GBPUSD     32.16      1.55    4.82%   PITA    +1.023 pips
USDJPY     25.22      1.35    5.35%   PITA    +0.668 pips
USDCAD     29.03      2.10    7.23%   PITA    +0.222 pips
USDCHF     20.68      1.66    8.03%   KATAA   −0.006 pips
AUDUSD     17.34      1.72    9.92%   KATAA   −0.333 pips
```

**Ubashiri wangu ulikuwa mbaya kwa mara 3.1.** Nilibashiri EURUSD `σ = 8.45`
kwa kupanua `√muda` kutoka F0 leg B; halisi ni **26.25**. Ni ubashiri wangu
wa **nne** uliokosea kwenye mradi huu, na sababu ni ile ile kila mara:

> **Dirisha la TUKIO si upanuzi wa `√muda` wa saa ya kawaida.** Fix ya mwisho
> wa mwezi ina volatility mara **3.1** ya saa ya kawaida kwa EURUSD na mara
> **1.7** kwa USDJPY. Mtiririko wa mamlaka unaleta mwendo, si tu bei.
> Kuanzia sasa, `σ` ya dirisha la tukio **inapimwa**, haipanuliwi.

**Kuchuja symbols ni utaratibu wa §6, si marekebisho.** `SYMBOLS` (sita) ni
seti ya **mekanizimu** (§6.1); `QUALIFIED` (nne) ni ya **gharama** (§6.2).
Doctrine inasema waziwazi: *"Symbol iliyokataliwa haiingii kwenye hesabu ya
majaribio wala kwenye pooling."*

Ulinzi unaofanya hili liwe salama: lango linatumia **σ na gharama pekee**,
halioni faida hata kidogo. **Haliwezi kuchagua symbol kwa sababu ilifanya
vizuri, kwa sababu halijui ilivyofanya.** Ndiyo maana §6.2 iliandikwa kwa
`σ` na gharama tangu mwanzo.

USDCHF imekataliwa kwa **pips 0.006** — ndani ya kelele ya kipimo. Sheria
iliyotangazwa ndiyo inayoamua, si hukumu yangu.

Gharama: kikapu kina legs **nne**, si sita. `N_eff` inapungua, na `Σw = 0`
sasa inasawazisha nne. Mekanizimu unabaki: EUR, GBP, JPY, CAD zote zina
masoko makubwa ya hisa yanayohitaji hedge.

**Kinachohitajika kabla ya `p`:** ishara ya hisa. Sasa inastahili
kutafutwa — lango limefunguka.

#### JIBU (2026-09-10) — F1 HAIJANUSURIKA

Ishara kamili **96/96**. Malango yote matatu yamepita kwa trades halisi
(gharama 7.3% kwa USDCAD, leg mbaya kabisa). Kisha:

```
trades 344 · siku hai 86/96 · zilizogongwa stop 5 (1.45%)
wastani  −0.00716 R/siku   ·   p 0.6673   ·   CI95 [−0.04858, +0.02956]
```

**Jaribio la PILI kati ya 7 limetumika.** Yaliyobaki: **5**.

**Si "hakuna nguvu" — ni jibu.** Lango la 6.3 lilidai matukio **52** ili
kuona edge iliyotangazwa; tulikuwa na **86**. Kwa hiyo:

```
Sharpe kwa siku    iliyotangazwa  +0.3927      (edge 5.7 pips)
                   iliyopimwa     −0.0387      mara 10 ndogo, ishara imegeuka
t inayotarajiwa    +3.64   (kizingiti 2.81)
t iliyopimwa       −0.36
```

Kwa vipimo vya pips:

```
edge iliyopimwa    −0.56 pips
CI 95%             [−3.63, +2.51] pips
iliyotangazwa      +5.70 pips        ← NJE ya CI
```

Edge iliyotangazwa **imekataliwa kwa uhakika**. Kinachobaki kinaweza kuwa
chochote kati ya `−3.6` na `+2.5` pips — na sifuri iko katikati kabisa.

**Tofauti na F0.** F0 ilikuwa hasi **kwa uhakika** (CI ilitenga sifuri) kwa
sababu gharama ilizidi edge. F1 ni **isiyotofautishika na sifuri**: gharama
ni ndogo (3.9%–7.3% ya σ) na dirisha la fix lina volatility kubwa, kwa hiyo
gharama haitawali. Ni edge yenyewe isiyoonekana.

**Vitu vitatu vya ziada:**

1. **LANGO 3 kwa mara ya tatu.** Pengo la spread: wastani **−0.005p**,
   p95 **+0.076p** kwa trades 339 kwenye symbols nne, ikiwemo dirisha la fix
   ambapo spread inapanuka. **RCE inabaki kama ilivyo, bila shaka yoyote.**
2. **Kugongwa kwa stop: 1.45%** (F0 ilikuwa 1.83%), yote 2020–2021 — COVID na
   mfumuko uliofuata. Thabiti kati ya familia, thabiti kwa `k = 4`.
3. **Siku 10 zilipotea** kwa kuanzisha historia ya stop (`SL_MIN_SESSIONS`).
   Kwa familia ya kila mwezi hiyo ni **miezi 10**, si siku 10 — gharama kubwa
   kuliko ilivyoonekana wakati sheria iliandikwa kwa familia ya kila siku.
   Imeandikwa kwa familia zijazo za matukio machache.

---

### 9.6 · MZUNGUKO WA KWANZA UMEKAMILIKA

```
familia    jibu                                       α
F0         p 0.9710 · gross 0.29–0.70 pips            jaribio 1
Gotobi     lango la gharama 9.3% > 8%                 hakuna
F1         p 0.6673 · edge CI [−3.6, +2.5] pips       jaribio 2
                                                      ─────────
                                            zilizotumika 2 kati ya 7
```

**Hakuna familia iliyopita kizingiti. Zote tatu zimejibiwa — lakini
hazikufa kwa sababu moja, na "hakuna iliyonusurika" ni sentensi
inayoficha tofauti hizo.** Uainishaji kwa hali umeandikwa §13:

```
F0       COST-FAILED (baada)       gross imepimwa 0.29–0.70p, gharama 2.05p
Gotobi   COST-FAILED (kabla)       lango 8.733% > 8.0%; gross haijapimwa
F1       HYPOTHESIS REJECTED       +5.7 pips haijaonekana; edge halisi
         / NOT REPLICATED          haijulikani ndani ya [−3.6, +2.5]
```

*(Namba za Gotobi ni za kipimo cha 2026-09-10, §13.10. Za mwanzo — 9.3% —
zilitokana na `σ` ya dhana na commission ya dhana. Uamuzi haukubadilika,
lakini namba zilizoandikwa sasa zimepimwa.)*

Ndicho §12 kilichoahidi: *"Njia hii inatoa jibu la kuthibitika-au-kukataliwa.
Haiahidi strategy."* Toleo la kwanza lilitumia miezi sita na mamia ya
majaribio bila jibu hata moja. Hili limetoa matatu kwa siku tatu, likitumia
majaribio mawili.

**Kilichojengwa kinabaki:** udhibiti chanya uliokalibrishwa (§7.1), block
bootstrap yenye ukubwa uliopimwa, kuiga njia ya stop (§11), kalenda ya benki
za Japani, msomaji wa madirisha, chombo cha kupima lango bila kugharimu α,
na **RCE iliyothibitishwa mara tatu**.

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
| **ML** | Baada ya familia mbili. Meta-labelling, utabiri wa volatility/gharama, regime discovery. **Kamwe kutabiri mwelekeo.** Imefafanuliwa upya §13.9. |

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

Baada ya mzunguko wa kwanza sentensi inayofaa si *"familia zimekufa"* bali:
**dhana zilikufa; chombo cha kupima kilinusurika.**

---

## 13 · Taxonomia ya kufa kwa hypothesis

*(Imeongezwa 2026-09-10, baada ya ukosoaji wa nje uliopokelewa na PD. Kabla
ya kutangaza familia yoyote mpya.)*

### 13.1 · Kwa nini PASS/FAIL haitoshi

Injini ilitoa `p` na `p` ikatoa neno moja: **IMENUSURIKA** au
**HAIJANUSURIKA**. Neno hilo ni sahihi kwa uamuzi wa kutrada, na **si sahihi
kwa maarifa**. Familia tatu zilipata neno lile lile ingawa:

- F0 **ilipimwa kikamilifu** na athari yake ya gross ilionekana — ikafa
  kwa gharama;
- Gotobi **haikupimwa kabisa** — ilikataliwa na lango kabla ya `p`;
- F1 **ilipimwa** lakini kwa matukio 86 pekee, na CI yake bado inaruhusu
  edge chanya ndogo.

Kuita zote "zimekufa" ni kupoteza taarifa ambayo mzunguko wa pili unaihitaji.
Kuanzia sasa kila familia inapata **hali**, si alama.

### 13.2 · Hali nane

| hali | maana | kinachofuata |
|---|---|---|
| **SURVIVES** | `p ≤ kizingiti` na malango yote yamepita | §10 (holdout, karatasi) |
| **REJECTED** | edge iliyotangazwa iko nje ya CI, na CI ni ndogo ya kutosha kuwa na maana | familia inafungwa; mekanizimu inabaki na alama |
| **NOT DETECTED** | hakuna athari iliyoonekana, CI inajumuisha sifuri **na** thamani zenye maana kibiashara | si "haipo"; inahitaji matukio zaidi au haijibiki |
| **UNDERPOWERED** | `n` chini ya inayohitajika kabla ya kupima | haipaswi kuwa imepimwa; jaribio kurudishwa |
| **COST-FAILED (baada)** | athari ya gross **imepimwa**, gharama inaila | mekanizimu ipo; inahitaji symbol/dirisha/broker tofauti |
| **COST-FAILED (kabla)** | lango la §6.2 limekataa; gross **haijapimwa kamwe** | hatujui kama athari ipo; α haijatumika |
| **IMPLEMENTATION-FAILED** | mekanizimu haijafikiwa — nanga mbaya, data haipo, dirisha halipatikani | mekanizimu **haijakanushwa** |
| **REGIME-FAILED** | ilikuwa hai kwenye sehemu ya sampuli, imekufa kwenye nyingine | inahitaji kigezo cha regime kilichotangazwa mapema |
| **UNCERTAIN** | kipimo hakiaminiki (kasoro ya injini, data yenye mashaka) | inarekebishwa na kupimwa upya — si jaribio jipya |

Hali inatangazwa **pamoja na jibu**, kwenye run ile ile, kwa sheria
iliyoandikwa mapema. Haichaguliwi baada ya kuona `p`.

### 13.3 · Maswali matatu ya ukubwa wa sampuli

Kosa langu la pili la mzunguko huu: niliandika kwamba matukio 52 yanatosha,
kisha nikatumia neno hilo kama kwamba F1 imethibitisha *"mekanizimu haipo."*
**Hapana.** Hesabu ya nguvu inajibu **swali moja tu** kati ya matatu, na
matatu haya lazima yatenganishwe kila mara:

```
(a) Je, tunaweza kuona edge tuliyotangaza (+5.7 pips)?
    → hesabu ya nguvu. F1: NDIYO, matukio 86 > 52 yanayohitajika.

(b) Je, tunaweza kukataa edge chanya yenye maana kibiashara?
    → upana wa CI. F1: HAPANA. CI [−3.63, +2.51] bado inaruhusu
      +2.5 pips, ambayo ingekuwa strategy nzuri.

(c) Je, tunaweza kukadiria edge kwa usahihi wa kutosha kuitrada?
    → upana wa CI dhidi ya ukubwa wa nafasi. F1: HAPANA, mbali.
```

Kwa hiyo kauli halali kuhusu F1 ni **moja**: *"edge ya +5.7 pips
haikuonekana."* Si *"edge haipo."* Si *"mekanizimu imekufa."* Familia
inafungwa kwa sababu ya nidhamu ya α (§8.4), si kwa sababu tumethibitisha
sifuri.

### 13.4 · Uainishaji wa mzunguko wa kwanza

**F0 — COST-FAILED.**
Gross `+0.00562 R/siku` = pips 0.29–0.70. Gharama pips 2.05. Mwelekeo
ulikuwa kama ulivyotangazwa; ukubwa ulikuwa robo ya gharama. Mekanizimu
(mtiririko wa fix ya London) haijakanushwa — imeonyeshwa kuwa **ndogo mno
kwa gharama ya retail kwenye EURUSD**. Ingeweza kuishi kwa gharama ya
taasisi (pips 0.3–0.5), na hiyo ni taarifa, si strategy.

**Gotobi — COST-FAILED (kabla), pamoja na tatizo la utekelezaji.**
*(Imeandikwa upya 2026-09-10 baada ya §13.10. Ilikuwa
`IMPLEMENTATION-FAILED`, kisha `UNCERTAIN` wakati gharama haijulikani.)*

Kipimo cha mwisho, kwa `σ` iliyopimwa na commission iliyopimwa:
**8.733% dhidi ya 8.0%**. Malango mengine mawili yalipita — mekanizimu
(§6.1) na mzunguko (§6.3, matukio 276 dhidi ya 136). **Gharama pekee
ndiyo iliyoifunga.**

Athari ya gross **haijapimwa kamwe** kwa maana ya §7 — hakuna `p`, hakuna
α iliyotumika. Kinachojulikana ni `drift +1.79 pips` yenye `t = 1.84`
dhidi ya `t* = 2.81`: haifiki hata bila gharama.

Tatizo la utekelezaji halijatoweka: nanga ya 08:30 JST ni kabla Tokyo
haijafunguka, na **37% ya madirisha ya kuingia hayakuwa na tick hata
moja** (185 kati ya 500). Nanga tofauti ni **familia mpya** yenye tangazo
jipya, si Gotobi.

Theluthi mbili ya gharama ni commission, si spread. USDJPY ni USD-msingi,
kwa hiyo commission yake ni `$7.00` **hasa** — haipungui kwa bei. Broker
mwenye commission ndogo ni jaribio tofauti, si uboreshaji.

**F1 — HYPOTHESIS REJECTED / NOT REPLICATED.**
Edge iliyotangazwa +5.70 pips iko **nje** ya CI `[−3.63, +2.51]` — hiyo
ndiyo REJECTED, na inatosha kufunga familia. Lakini edge halisi
**haijulikani**: inaweza kuwa −3.6, sifuri, au +2.5. Lango la gharama
lilikuwa jepesi (3.9–7.3% ya σ), matukio yalitosha kwa swali (a) pekee.

### 13.5 · Kabla ya familia yoyote mpya: usajili wa H0

Kila familia ya mzunguko wa pili itatangaza, kwenye faili ya familia yenyewe
na kwenye hash ya tangazo, **kabla ya kusoma tick hata moja**:

```
H0                    kauli sahihi ya "hakuna kitu hapa"
H1                    kauli sahihi ya "kuna kitu, cha ukubwa huu"
mlipaji               jibu la §8.6 (LAZIMA / HAJALI / HAWEZI)
gross ya chini        pips zinazohitajika kabla ya gharama
net ya chini          pips zinazohitajika baada ya gharama
gharama ya juu        kikomo cha cost_RT / σ (§6.2)
ukubwa wa chini       athari ndogo kabisa yenye maana kibiashara
kiwango cha imani     kizingiti cha p (§9)
matukio yanayohitajika (t*/s)² (§6.3)
itifaki ya uthibitisho holdout: lini, mara ngapi, sheria gani
```

Na sheria moja isiyo na ubaguzi:

> **Hakuna kuboresha baada ya kuona holdout.** Ikionekana, imetumika.

### 13.6 · Kilichopimwa dhidi ya kilichoripotiwa

Mzunguko wa kwanza uliripoti **wastani na `p` pekee**. Hiyo inaficha
mgawanyo, na mgawanyo ndiyo unaoamua kama strategy inaweza kutradiwa.
Kuanzia mzunguko wa pili kila jibu litabeba:

```
wastani · katikati · std · P10 P25 P50 P75 P90
kiwango cha kushinda · uwiano wa malipo
MAE · MFE · matarajio kwa masharti
```

Data ya haya **tayari ipo** kwenye `Trade` (`mae_pips`, `net_pips`, `r`) —
haikuchapishwa tu. Ni kazi ya kuripoti, si kipimo kipya, kwa hiyo
haigharimu α.

### 13.7 · Onyo: conditioning ni utafutaji

Ukosoaji uliopokelewa unapendekeza mtihani wa *"je, mekanizimu inanusurika
ikiwekewa masharti?"* — mwelekeo × regime ya volatility × mapato ya hisa ×
trend ya FX × tofauti ya riba × hisia ya hatari.

**Hii ndiyo hasa §8 iliandikwa kuizuia.** Vipimo sita vya masharti kwenye
familia moja ni **majaribio sita**, na yakichaguliwa baada ya kuona matokeo,
ni `2⁶ = 64` njia za kutafuta ushindi kwenye data ile ile — utafutaji wa
K=12,000 uliorudi kwa jina jipya (§3).

Inaruhusiwa kwa masharti matatu, na ukosoaji wenyewe unakubali la tatu:

1. Kigezo cha masharti kinatangazwa **kabla** ya kuendesha, kikiwa na
   mekanizimu ya kwa nini kinapaswa kutofautisha;
2. Kila kigezo kinahesabiwa kama **jaribio** kwenye bajeti ya α (§9);
3. Conditioning yoyote inayotokana na **kuangalia matokeo** inahitaji
   **sampuli mpya kabisa**, si sehemu ya ile ile.

Kwenye data yetu, sharti la (3) linamaanisha: hatuna sampuli mpya kwa F0/F1
mpaka 2003–2017 ipakuliwe, na hiyo ina gharama yake (§9.1). Kwa hiyo
conditioning inaingia mzunguko wa pili **kwa familia mpya pekee**, si kama
uchunguzi wa maiti wa familia zilizokufa.

### 13.8 · Familia za mzunguko wa pili zinapangwa kwa MEKANIZIMU

F0, Gotobi na F1 zilichaguliwa kama **strategies** — kila moja ni sheria ya
kuingia na kutoka. Matokeo yake: zilipokufa, hazikuacha maarifa
yanayohamishika, kwa sababu hakuna kitu kilichokuwa cha pamoja kati yao.

Mzunguko wa pili unapangwa kwa **chanzo cha mtiririko**. Familia ni
mekanizimu; strategy ni utekelezaji mmoja wa mekanizimu hiyo.

| | mekanizimu | mlipaji (§8.6) | zilizokwisha |
|---|---|---|---|
| **A** | mtiririko wa taasisi (rebalancing, fixes, settlement) | LAZIMA | F0, F1, Gotobi |
| **B** | kuwasili kwa taarifa (data releases, benki kuu) | HAJALI/HAWEZI | F2 (imesimamishwa §9.1) |
| **C** | muundo mdogo wa soko (msongamano wa stops, likidity gaps) | HAWEZI | F3 (imesimamishwa) |
| **D** | volatility (clustering, term structure, event premia) | LAZIMA | — |
| **E** | trend / momentum | HAJALI | F4 (imesimamishwa §9.1) |
| **F** | uhamisho kati ya masoko (rates, commodities, hisa) | HAWEZI | ishara ya F1 |

Kanuni: **familia moja kwa mekanizimu kwa mzunguko.** Familia tatu za
kundi A kwenye mzunguko mmoja — ndicho tulichofanya — ni kuweka α yote
kwenye dhana moja iliyoandikwa kwa maneno matatu tofauti. Ndiyo maana
majibu matatu yalikuja pamoja: yote yalitegemea mtiririko wa fix.

### 13.9 · Nafasi ya ML — imefafanuliwa upya

§9.1 iliandika: *"ML baada ya familia mbili. Kamwe kutabiri mwelekeo."*
Kikomo kinabaki. Kinachobadilika ni **swali** ML inaloulizwa.

**Si:** *"tafuta strategy kwenye data."* Hiyo ni utafutaji wa K=12,000
kwa jina jipya, na inaanguka kwenye §3.

**Ni:** *"mekanizimu ninayoijua tayari — iko hai lini, ina nguvu kiasi
gani, na inatradika sasa?"*

```
MEKANIZIMU  →  KICHUJIO CHA REGIME  →  MODEL YA EDGE  →  GHARAMA + RCE  →  TRADE / HAPANA
(imeandikwa    (ML: iko hai?)          (ML: ukubwa?)     (isiyo ya ML,      (uamuzi)
 na binadamu)                                             mamlaka)
```

ML inaingia kwenye **hatua mbili za kati pekee**. Hatua ya kwanza ni ya
binadamu (§4.3: kutengeneza strategy ni kuandika, si kutafuta), na ya
nne ni ya RCE (§5) — haihamishwi kwa model kamwe.

Kwa hivyo RL/PPO inaruhusiwa **kwa usimamizi wa exposure ndani ya
mekanizimu iliyothibitishwa**, na haikubaliki kama mtafutaji wa edge.
Sharti la §2 halibadiliki: kila namba inayoingia kwenye uamuzi lazima
ipimwe na injini hii, kwenye mchakato huu, kabla ya kutumika — ikiwa ni
pamoja na kila namba inayotoka kwenye model.

### 13.10 · Ukaguzi wa §2 — namba zinazoingia kwenye maamuzi bila kupimwa

*(2026-09-10. Swali: **namba zipi zinazoingia kwenye maamuzi yetu ambazo
injini hii haijazipima?**)*

| namba | chanzo | imeingia kwenye | hali |
|---|---|---|---|
| `MOVE_TO_SIGMA = 1.2533` | nadharia ya normal | lango la §6.2 la **kila** familia → kukataliwa kwa Gotobi | **IMEREKEBISHWA** |
| `commission = $7.0` RT | dhana ya chaguo-msingi | gharama ya kila familia; 65% ya gharama ya Gotobi | inapimwa — `scripts/mt5_specs.py` |
| `contract_size = 100,000` | "kawaida", `confirmed: false` | `pip_value` → `commission_pips` → gharama zote | inapimwa — script ile ile |
| slippage ya stop `= 0.3` | "HAIJAPIMWA" (imeandikwa) | **haitumiki**: stop 70 za F0 zinajaza kwa bei kamili | inabaki wazi (§11) |

**`MOVE_TO_SIGMA` ndiyo kubwa kuliko zote.** Lango la §6.2 linadai
`σ ya dirisha`. Hatukuipima. Tulipima `E|mwendo|` kisha tukazidisha kwa
`1.2533` — kigezo cha `E|X| = σ√(2/π)`, **kweli kwa mgawanyo wa normal
pekee**. Na injini hii hii ilikuwa **tayari imethibitisha** kwamba normal si
kweli kwenye data hii: kugongwa kwa stop kulitabiriwa 0.3% kwa kanuni ya
normal, halisi ni **1.83%** — mara sita.

Kwa mikia minene `σ / E|X| > 1.2533`, kwa hiyo:

```
σ yetu ilikuwa NDOGO kuliko halisi
  → uwiano gharama/σ ulikuwa MKUBWA kuliko halisi
    → lango la §6.2 lilikuwa KALI kuliko lilivyotangazwa
```

**Marekebisho:** `driver.measure` na `gate_probe` sasa zinapima `σ` moja kwa
moja — `stdev` ya mwendo wenye ishara (`stops.signed_move_pips`). Kigezo cha
normal kinabaki kikichapishwa pembeni kama `σ norm`, pamoja na uwiano
`kurtosis_hint = σ_iliyopimwa ÷ σ_ya_normal`, ili upotoshaji uonekane kwa
namba badala ya kubishaniwa.

Kwenye ticks za normal safi (fixture ya majaribio) `kurtosis_hint` ni
**1.000 ± 0.12** — kimethibitishwa kwa jaribio. Kwa hiyo tofauti yoyote
kwenye data halisi ni **tabia ya soko**, si kasoro ya hesabu.

**Hakuna jibu la mzunguko wa kwanza linalobadilika kwa hili.** `σ` inaingia
kwenye lango na kwenye Sharpe iliyotangazwa **pekee** — haiingii kwenye
`curve`, wala kwenye `R`, wala kwenye bootstrap. F0 na F1 zilishapita lango;
`σ` kubwa zaidi inalifanya jepesi tu. `p` zao ni zile zile.

#### Sheria ya Gotobi — imeandikwa KABLA ya kupima

Kilichoathirika ni **Gotobi pekee**, iliyokataliwa kwa **9.3% dhidi ya 8%**.
Uamuzi wa PD (2026-09-10): **inaendeshwa ikiwa lango litafunguka.** Sheria
imeandikwa hapa kabla namba mpya haijaonekana, ili isije ikaundwa
kuizunguka:

1. Kizingiti kinabaki **8.0%** — kilichotangazwa 2026-09-07, hakibadiliki.
2. Lango linapimwa **MARA MOJA**, kwa namba **zote** zilizorekebishwa
   pamoja: `σ` iliyopimwa **na** commission iliyopimwa kutoka MT5. Si
   marekebisho moja, kisha kingine kikishindwa. **Kipimo kimoja, jibu moja.**
3. `uwiano ≤ 8.0%` → Gotobi inaendeshwa. Tangazo ni lile lile
   (`06a78b1b…`) — nanga, mwelekeo, `k`, kila kitu. Sheria ya uamuzi ni ile
   ile: `p ≤ 0.0025`. Inagharimu **jaribio la tatu**.
4. `uwiano > 8.0%` → Gotobi imefungwa kwa mzunguko huu, kabisa. Hakuna
   marekebisho ya tatu.
5. Kama nanga ya kuingia ingebadilishwa (08:30 JST ni kabla Tokyo
   haijafunguka — 37% ya madirisha hayakuwa na tick), hiyo ni **familia
   mpya** yenye tangazo jipya na hash mpya, si Gotobi. Sheria hii
   hairuhusu hilo.

Msingi wa kuruhusu (3): ni sawa kabisa na §9.3 — namba iliyopimwa vibaya
ilirekebishwa, tangazo halikubadilika, sheria ya uamuzi iliandikwa kabla.
Tofauti na §8.5 (*"kufeli hakuendeshwi upya kwa vigezo vipya"*) ni kwamba
**hakuna kigezo kipya**: `1.2533` haikuwa kigezo cha strategy, ilikuwa kosa
la kipimo.

#### Commission — dhana yangu iliyoua familia

`config/broker_costs.yaml` ilikuwa na `default: 7.0` kwa kila symbol.
Namba hiyo haikutoka kwa broker; niliiweka kama chaguo-msingi. Iliingia
kwenye gharama ya kila familia, na theluthi mbili ya gharama ya Gotobi
ilikuwa commission. **Tuliandika "Gotobi IMEKATALIWA" kwa namba
iliyobuniwa.**

`scripts/mt5_specs.py` inaipima: `symbol_info` inatoa `contract_size`,
`point`, `digits`, `tick_value` (→ `pip_value` halisi ya broker), na
`volume_*`; `history_deals_get` inatoa **commission halisi kwa lot**
iliyolipwa kwenye deals zilizotekelezwa — kipimo, si bei ya tangazo.

Commission **haipo** kwenye `symbol_info`; njia pekee ni deals. Akaunti
isiyo na historia haiwezi kuipima, na script inasema hivyo badala ya
kukisia. Katika hali hiyo `7.0` inabaki **ikiwa imeandikwa kama DHANA**, na
familia yoyote inayokufa kwa gharama inapata **`UNCERTAIN`**, si
`COST-FAILED`.

Utambulisho wa akaunti (login, server, jina la broker) **hauchapishwi wala
hauandikwi kwenye faili**. Sifa za symbols ndizo zinazohitajika.

#### JIBU (2026-09-10, MT5, akaunti ya demo, USD, 1:100)

```
contract_size          IMEPIMWA    FX 100,000 · XAUUSD 100
pip_value              IMETHIBITISHWA (sheria zetu dhidi ya broker)
commission             HAIJAPIMWA  hakuna deal hata moja
```

**`contract_size`: dhana ilikuwa sahihi.** Symbols 12 zote zinasoma
`100,000` (XAUUSD `100`) — sawa kabisa na kilichokuwa kwenye
`broker_costs.yaml`. `contract_size_confirmed` sasa ni **`true`**, na si
kwa sababu tuliamini, ni kwa sababu tumesoma.

**`pip_value`: sheria zetu zinakubaliana na broker kwa kila symbol yenye
quote.** Hii ndiyo tofauti kubwa kati ya "dhana iliyokuwa sahihi" na "dhana
tuliyoendelea nayo" — kipimo hakikuwa cha kuridhisha tu, kilikuwa cha
kujitegemea (`symbol_info.trade_tick_value`, njia tofauti kabisa na hesabu
yetu):

```
                 MT5    yetu   tofauti   sheria
EURUSD        10.000  10.000    +0.00%   dola ni nukuu  → contract × pip
GBPUSD        10.000  10.000    +0.00%
AUDUSD        10.000  10.000    +0.00%
NZDUSD        10.000  10.000    +0.00%
USDJPY         6.473   6.473    +0.00%   dola ni msingi → contract × pip ÷ bei
USDCHF        12.296  12.296    +0.01%
USDCAD         7.228   7.228    +0.01%
EURJPY         6.473   6.473    +0.00%   cross          → ÷ USDJPY
GBPJPY         6.473   6.473    +0.00%
EURCHF        12.296  12.296    +0.01%
EURGBP        13.511  13.511    +0.00%   cross          → × GBPUSD
XAUUSD         1.000   1.000    +0.00%   contract 100
                                ──────
                                12/12 ndani ya 1%
```

Kama tungeweka `$10` kwa zote — jaribu la kawaida — USDJPY ingekosewa kwa
**35%**, USDCAD kwa **38%**, USDCHF kwa **19%**, na kosa hilo lingeingia
kwenye `commission_pips` ya kila familia.

**Kasoro iliyopatikana njiani.** Kwenye run ya kwanza USDCAD na EURGBP
zilirudisha `pip_value 0.00`. **Si sifuri ya soko** — ni symbol
iliyoongezwa Market Watch dakika hiyo hiyo, na `trade_tick_value` inabaki
`0.0` mpaka quote ya kwanza ifike (kwa cross, MT5 inahitaji bei ya
kubadilisha sarafu ya nukuu). Bila kurekebisha, sifuri hiyo ingeandikwa
kwenye ripoti kana kwamba ni kipimo. `mt5_specs.py` sasa inasubiri quote
(`subiri_tick`) na inaandika `BILA QUOTE` pale isipofika.

Ni mfano mdogo wa kanuni ya §2 ikijirudia: **thamani inayorudishwa si
kipimo mpaka ijulikane kwamba chombo kilikuwa tayari kupima.**

#### `commission` — imepimwa, na dhana ilikuwa mbaya

Akaunti haikuwa na deal hata moja, kwa hiyo commission ilizalishwa:
`scripts/mt5_commission.py`, BUY inayofungwa papo hapo, symbols 11 kati ya
12 (XAUUSD `MARKET_CLOSED`), deals 22.

```
AUDUSD  NZDUSD                      $4
USDJPY  USDCHF  USDCAD              $6
EURUSD  EURCHF  EURGBP  EURJPY      $8
GBPUSD  GBPJPY                     $10
```

**Dhana ya `$7.0 kwa kila symbol` ilikuwa mbaya kwa pande zote mbili** —
chini kwa GBP kwa 43%, juu kwa AUD kwa 75%. Na si namba moja: ni
mgawanyo wa mara 2.5 kati ya nafuu na ghali. `broker_costs.yaml`
ilikuwa na safu kumi na mbili za `7.0` zilizoonekana kama data.

Kwa **USDJPY — symbol ya Gotobi — halisi ni `$6`, si `$7`.**

#### Ukungu wa kipimo: namba zote ni shufwa

`4, 6, 8, 10` si bahati. MT5 inaandika `deal.commission` kwa **senti**, na
kipimo kilichukuliwa kwa lot `0.01`:

```
senti 0.02 kwa RT  ÷  0.01  =  $2.00 kwa lot
```

Kugawa kwa volume kunazidisha mviringo kwa `1/volume`. Kwa `0.01` ukungu
ni **±$1.00 kwa lot** — na kwa USDJPY $1 ni takribani **pips 0.13**, wakati
uamuzi wa Gotobi unategemea 9.3% kushuka hadi 8.0% (≈ pips 0.19).
**Ukungu ni karibu sawa na tofauti inayoamuliwa.**

Niliandika kwenye script *"volume ni 0.01 daima; hakuna hoja ya
kuipandisha"*. Hoja ipo, na ni hii. `--volume` sasa ipo, chaguo-msingi
`0.10` (ukungu $0.20), kikomo kigumu `1.00` (ukungu $0.02), na position
moja kwa wakati ili margin isirundikane.

#### Kipimo kikali (`--volume 1.0`, ukungu ±$0.01/lot)

```
symbol                    $/lot RT      ÷ 7.00
USDJPY  USDCHF  USDCAD        7.00      1.0000
EURUSD                        8.12      1.1600
EURCHF  EURJPY                8.13      1.1614
EURGBP                        8.14      1.1629
GBPUSD                        9.46      1.3514
GBPJPY                        9.47      1.3529
AUDUSD                        5.02      0.7171
NZDUSD                        4.06      0.5800
```

Safu ya kulia ni **bei ya sarafu ya msingi kwa dola**, kila moja. Si
jedwali la namba 12 — ni namba moja na sheria moja:

> **commission = $7.00 round-turn kwa lot, inayotozwa kwa sarafu ya
> MSINGI, ikibadilishwa kuwa dola kwa bei ya sasa.**

Broker anatoza **$3.50 kwa upande kwa lot ya sarafu ya msingi**.

Hii ni bora kuliko jedwali kwa sababu mbili. Ya kwanza: bei inabadilika.
EURUSD ilianzia 1.04 na kufika 1.25 kwenye sampuli yetu, kwa hiyo namba
iliyogandishwa ya `8.12` ingekuwa imekosea kwa **20%** kwenye ncha za
dirisha. Ya pili: kwa pairs zinazonukuliwa kwa dola, bei ya sarafu ya
msingi **ni `mid` yenyewe** — backtest tayari inayo, hakuna chanzo kipya.

`backtest.driver.commission_usd` inatekeleza sheria. **RCE haijaguswa**:
inapokea namba ya dola iliyokwisha kubadilishwa, kama ilivyokuwa.
Crosses (EURGBP, GBPJPY) zinahitaji bei ya tatu ambayo backtest haisomi,
kwa hiyo zinakataliwa waziwazi badala ya kukadiriwa kimya.

#### Ubashiri wangu ulikuwa mbaya, na kipimo kikali kimeuonyesha

Nilibashiri hapa kwamba Gotobi ingefungua lango (7.9%–8.4%), kwa msingi
kwamba USDJPY ilikuwa **`$6`**, si `$7`.

**`$6.00` ilikuwa mviringo, si kipimo.** Kwa lot `0.01`, `$7.00` RT ni
senti 3.5 kwa upande; MT5 iliandika senti 3, na kugawa kwa 0.01 kukatoa
`$6.00`. Kipimo cha `1.00` kinasema **`$7.00` hasa**.

Kwa hiyo **dhana yangu ya asili ilikuwa sahihi kabisa kwa USDJPY**, na
hoja nzima ya ubashiri wangu imekufa. Gotobi haina punguzo la commission.
Kinachobaki ni marekebisho ya `σ` pekee:

```
9.3%  →  8.0%   kunahitaji  kurtosis_hint ≥ 1.16
```

Laplace inatoa 1.13; Student-t yenye ν=4 inazidi. Inawezekana, si hakika.

**Ubashiri upya: sijui.** Uwiano utakuwa kati ya 8.0% na 9.3%, na 8.0%
iko ncha ya kile kinachowezekana. Ubashiri wangu wa §9.3 ulikuwa mbaya kwa
mara nne; huu wa kwanza ulikuwa mbaya kwa sababu nilijenga juu ya kipimo
chenye ukungu. **Kanuni: kipimo chenye ukungu mkubwa kuliko tofauti
inayoamuliwa si kipimo, ni pendekezo.**

#### Athari kwa familia zilizopita

**F0 (EURUSD).** Commission halisi ni `7.00 × EURUSD`, si `7.00` — juu kwa
**16%** kwa bei ya leo, 4%–25% kwenye dirisha. `commission_pips` inapanda
kutoka 0.70 hadi ~0.78. F0 ilikuwa na gross ya pips 0.29–0.70 dhidi ya
gharama ya 2.05; kupanda kwa gharama hakuwezi kuibadilisha kuwa hai.
Jibu la §9.3 linabaki. **Sitasema kwamba `p` yake ingekuwa mbaya zaidi** —
gharama inaingia kwenye `lots` pia (`hatari ÷ (sl + gharama)`), kwa hiyo
mwelekeo wake kwenye `R` hauko wazi, na nilishakosea mara moja kwa kudai
mwelekeo bila kupima (§11).

**F1 (EURUSD, GBPUSD, USDJPY, USDCAD).** GBPUSD inapanda kwa **35%**
(`7.00 → 9.46`). Lango la F1 lilikuwa 3.9%–7.3% ya σ. Kupanda huko
kunaweza kuvusha symbol moja kupita 8%, na symbol iliyokataliwa
haipaswi kuwa ilitradiwa. **Hilo linahitaji kupimwa, si kudhaniwa** —
`gate_probe` inalifanya bila kugharimu α.

Ukubwa wa athari kwenye jibu la F1 ni mdogo: commission ya wastani
inapanda kwa ~0.09 pips kwenye kikapu, wakati pengo kati ya edge
iliyotangazwa (+5.70) na ncha ya juu ya CI (+2.51) ni **pips 3.2**.
Hali ya `HYPOTHESIS REJECTED` haibadiliki.

#### JIBU LA GOTOBI (2026-09-10, `family_run.py`, kipimo kimoja)

```
trades 273 · madirisha bila tick 185/500 (37.0%) · siku hai 276/500
gharama    1.41 pips        (commission ilibaki $7.00 — msingi ni USD)
σ         16.17 pips        iliyopimwa
σ norm    15.17 pips        kurtosis_hint 1.066
uwiano     8.733%           kizingiti 8.0%
```

Ilihitaji `kurtosis_hint ≥ 1.162`. Imepata **1.066**.

**GOTOBI IMEFUNGWA.** Sheria ya §13.10 nambari 4 imetumika bila
mabadiliko. **Jaribio halijatumika** — §6 inasema symbol iliyokataliwa
haiingii kwenye hesabu ya majaribio. Bado 2 kati ya 7.

Lango la mzunguko (§6.3) **lilipita**: matukio 276 dhidi ya 136
yanayohitajika. Lango la mekanizimu (§6.1) lilipita. **Gharama pekee
ndiyo iliyoifunga**, na sasa gharama imepimwa.

#### Uchunguzi mmoja unaovuta jicho, na kwa nini hauvutwi

Kipimo kinaonyesha **`drift +1.79 pips`** — USDJPY inapanda kwa wastani
huo kutoka 08:30 hadi 09:50 JST siku za gotobi, **mwelekeo ule ule
mekanizimu inaoutabiri**, na kubwa kuliko gharama ya 1.41.

Ni mwaliko wa kubishana na lango. Kabla ya kubishana, hesabu:

```
kosa la kawaida  =  16.17 ÷ √276  =  0.973 pips
gross   t = 1.79 ÷ 0.973 = 1.84       t* inayohitajika = 2.81
net     t = 0.38 ÷ 0.973 = 0.39
```

**Haifiki, hata bila kuhesabu gharama.** Lango halikuwa likizuia kitu
kilicho hai; lilikuwa likituokoa jaribio.

Uchunguzi unabaki umeandikwa kama taarifa ya **kundi A** (§13.8):
mtiririko wa fix ya Tokyo unaonekana kwenye mwelekeo sahihi, kwa ukubwa
usio na maana kitakwimu na usiozidi gharama ya retail. Familia yoyote ya
baadaye ikitaka kuutumia, inatangazwa upya na inalipa α yake.

#### F1: lango limepimwa upya, na limefunguka zaidi

`gate_probe --family f1` kwa namba zilizorekebishwa:

```
symbol   gh/σ   gh/σn   ilitradiwa?
EURUSD   3.9%    4.2%    ndiyo
GBPUSD   5.1%    5.5%    ndiyo
USDJPY   5.1%    5.3%    ndiyo
USDCAD   6.6%    7.2%    ndiyo
AUDUSD   8.0%    8.7%    HAPANA — ilikataliwa (§9.5)
USDCHF   7.3%    8.0%    HAPANA — ilikataliwa (§9.5)
```

**Symbols nne zilizotradiwa zote zinapita kwa upana.** Wasiwasi wangu
kwamba GBPUSD (+35% commission) ingevuka 8% haukuwa na msingi — ilifika
5.1%. **Jibu la F1 halina kasoro ya lango.**

Lakini safu ya `gh/σn` inaonyesha jambo lingine: **AUDUSD na USDCHF
zilikataliwa na §9.5 kwa namba mbili zilizokuwa mbaya** — `σ` ya dhana ya
normal na commission ya `$7` badala ya `$5.02` halisi ya AUD. Kwa namba
zilizopimwa zote mbili zinapita.

**F1 ilitradia symbols nne wakati ingeweza kutradia sita.** Kikapu chenye
legs sita kina ushahidi zaidi kuliko cha nne, na §13.3 swali (b) —
*"tunaweza kukataa edge chanya yenye maana?"* — lilijibiwa `HAPANA` kwa
sehemu kwa sababu ya upana wa CI.

Hii **haifungui F1 tena** (§8.5, na jaribio limeshatumika). Inaandikwa kwa
sababu tofauti: **lango la §6.2 lenyewe lilikuwa likikataa symbols kwa
makosa ya kipimo, si kwa gharama.** Kwa mzunguko wa pili, kila familia
inapima lango kwa namba zilizopimwa tangu mwanzo, na `gate_probe` sasa
inaonyesha safu zote mbili ili tofauti isijifiche.

#### Onyo kuhusu kupima commission kwenye demo

`scripts/mt5_commission.py` inaweza kuizalisha (BUY 0.01, funga papo hapo,
soma `deal.commission`), na ina kinga zisizo na swichi: **demo pekee**
(`trade_mode != 0` inakataliwa), volume `0.01` isiyobadilika, kufunga mara
moja, na hakuna order bila `--nakubali`.

Lakini kipimo hicho kina kikomo cha lazima kuandikwa: **broker wengi
wanaweka commission ya demo kuwa sifuri hata pale live inatoza.** Kwa hiyo
jibu la `0.00` kwenye demo **si uthibitisho kwamba commission ni sifuri**.

*(Marekebisho: niliandika kwamba spread ya EURUSD ya **pips 0.40**
inaonyesha akaunti ya raw/ECN, na kwamba aina hizo karibu daima zinatoza
commission. Run ya pili ilitoa **0.70** kwa symbol ile ile. Ni picha ya
dakika moja, na picha mbili zimetofautiana kwa 75% — kwa hiyo hoja hiyo ni
dhaifu kuliko nilivyoiandika, na haipaswi kubeba uzito. Sheria hapa chini
haitegemei: `0.00` kwenye demo haibadilishi chochote kwa sababu
haijapima live, si kwa sababu ya spread.)*

Kwa hiyo:

```
demo inatoa namba > 0   →  ni kipimo cha AINA HII ya akaunti; inatumika,
                           ikiwa imeandikwa kama "demo", na inahitaji
                           kuthibitishwa live kabla ya §10 hatua ya 5
demo inatoa 0.00        →  HAKUNA kinachobadilika. `7.0` inabaki dhana,
                           Gotobi inabaki `UNCERTAIN`
```

Hii imeandikwa **kabla** ya kuendesha, kwa sababu ya kwanza ni ya kuridhisha
na ya pili ni ya kukatisha tamaa, na sheria iliyoandikwa baada ya kuona jibu
si sheria.
