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
| **Gotobi** | Malipo ya waagizaji wa Japani | siku ÷ 5, 09:55 JST | ~600 | 2.8 bps | 2 |
| **F1** | Hedge ya hisa → fix ya mwisho wa mwezi | 16:00 London | **99** | 5.2 bps | 5 |

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

**Jumla ya majaribio ya mzunguko 1 = 8.** `0.020/8 = 0.0025` → **z ≈ 2.81**.

F1 ina matukio **99**, si 594. Legs sita kwa tarehe moja ni uchunguzi mmoja.
Kitu chochote chini ya **3 bps** ni null bila kujali `p`.

**Kupungua kwa mwaka kunapimwa kwa kila familia.** Ushahidi wa F0 unaishia
2007; Gotobi inauzwa kama EA sokoni. Msongamano unatarajiwa.

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

---

## 12 · Ahadi

**Njia hii inatoa jibu la kuthibitika-au-kukataliwa. Haiahidi strategy.**

Jibu linalowezekana zaidi ni kwamba familia moja au mbili zitanusurika, au
hakuna hata moja. F0 ikinusurika kwenye EURUSD pekee kwa Sharpe 0.4 — hiyo ni
mafanikio.
