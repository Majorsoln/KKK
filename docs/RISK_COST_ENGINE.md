# ELITEFX — RISK & COST ENGINE (RCE) — spec ya idara MOJA (PD 2026-08-02)

> PD ameunganisha **RISK MANAGEMENT + COST MANAGEMENT** kuwa idara moja. Sababu ni sahihi: lots
> haziwezi kuhesabiwa bila vyote viwili (`risk_per_trade` na `cost_pips` zinakutana kwenye fomula
> moja). Idara hii inapokea pendekezo kutoka **Idara 3 (Models)** na inatoa **trade tayari kufunguliwa**
> au **REJECT + sababu**. Vipimo vya ubora (EV/gross/ratio) ni vya Idara 3 (§UBORA) — RCE
> **inatekeleza**, haigundui.

```
Idara 3 (model) ──► pendekezo: symbol, dir, entry, SL, TP
                         │
                    ┌────▼──────────────────────────────────┐
                    │ RCE                                    │
                    │ 1. BUDGET  (base → penalty → daily)    │
                    │ 2. RISK/TRADE = budget ÷ max_open      │
                    │ 3. COST_PIPS (spread+slip+comm+swap)   │
                    │ 4. LOTS = risk ÷ ((SL+cost) × pipval)  │
                    │ 5. VIABILITY GATE (checks 6)           │
                    └────┬───────────────────────────────────┘
              PASS ──────┴────── REJECT + sababu → log/dashboard
```

---

## 0. TIMEFRAMES NA KAZI ZAKE (PD 2026-08-02)

| TF | Kazi | Idara inayoitumia |
|---|---|---|
| **D1** | Macro Bias — mwelekeo mkuu | KAIROS-1 |
| **H4** | Structural Trend — uthibitisho wa trend | KAIROS-1 |
| **H2** | Filter Regime — hali ya soko | KAIROS-1 |
| **H1** | **Decision + EXECUTION — injini kuu** | KAIROS-1 **na RCE** |
| **M30** | Setup refinement — ubora wa ndani | KAIROS-1 |
| **M15** | Trigger confirmation — timing | KAIROS-1 |
| **M5** | **Intrabar analytics — spread, slippage, volatility** | **RCE** |

**RCE inatumia TF MBILI pekee, kila moja kwa kazi yake:**
- **H1 = muktadha wa utekelezaji.** Entry inatokea hapa; kwa hiyo ukwasi, spread ya msingi, bar ya
  entry, na muundo wa hatari (SL/TP, lots) vyote vinapimwa kwa uhalisia wa H1.
- **M5 = analytics za ndani ya bar.** H1 inaficha spikes; M5 ndiyo chanzo KILICHOTEULIWA cha
  **spread-spike**, **slippage cap**, na **volatility** zinazoingia kwenye gharama.

TF nyingine tano (D1/H4/H2/M30/M15) ni **ingizo la KAIROS-1** — RCE **haizigusi**. Mgawanyo huu
unazuia idara moja kuingilia hukumu ya nyingine.

---

## 1. CONFIG (yaml — PD anabadilisha bila code)

```yaml
# config/ftmo_config.yaml
base_balance:        10000     # salio la awali (rejea isiyobadilika)
base_percentage:     0.04      # 4%
penalty_factor:      0.50      # 50% ya hasara ya jumla inakuwa adhabu
win_factor:          0.50      # +50% ya faida ya leo
loss_factor:         1.00      # -100% ya hasara ya leo
max_open_trades:     7
max_correlated:      3
daily_loss_stop_frac: 0.75     # 3/4 ya base + positions wazi -> acha
max_total_dd:        1000      # kikomo cha DD ya jumla
max_spread:          {USDCHF: 2.0, USDJPY: 2.0, ...}   # pips
trade_news:          true      # on/off swichi
day_reset_tz:        "Europe/Berlin"   # 00:00 CE(S)T
correlation_groups:  {...}
```

---

## 2. BAJETI YA SIKU

```
base      = base_percentage × base_balance                    # inaanza 00:00 CE(S)T
penalty   = penalty_factor × max(0, base_balance − current_balance)
budget    = base − penalty + win_factor×today_profit − loss_factor×today_loss
risk_per_trade = budget ÷ max_open_trades
```

- `base_balance` = **rejea isiyobadilika** (config), si salio la sasa.
- `current_balance` = **halisi kutoka akaunti** (MT5/broker).
- `penalty` inategemea **DD ya jumla** tangu mwanzo, si ya jana pekee.
- `today_profit` / `today_loss` **zinareset** 00:00 CE(S)T. `penalty` **hairesetiwi** — inafuata DD.

**Mfano ($10,000, base 4% = $400):**

| Hali | current_balance | penalty | budget | risk/trade |
|---|---|---|---|---|
| Siku ya kwanza | 10,000 | 0 | 400 | **57.1** |
| Baada ya DD −$200 | 9,800 | 100 | 300 | **42.9** |
| Leo tayari −$150 | 9,650 | 175 | 400−175−150 = **75** | **10.7** |
| Leo +$100 baada ya hapo | 9,750 | 125 | 400−125−150+50 = **175** | **25.0** |



---

## 3. COST_PIPS — vipengele vinne

```
cost_pips = spread_pips
          + slippage_pips
          + commission_pips
          + swap_pips
```

### 3.1 Spread — MSETO: H1 base + M5 spike-guard (uamuzi wa PD 2026-08-02)
```
spread_pips = (Ask − Bid) ÷ PipSize          # PipSize: 0.01 (JPY/XAU) · 0.0001 (nyingine)

spread_base      = wastani wa spread_H1 (bars N za mwisho)      # muktadha wa EXECUTION
spread_vol_adj   = percentile_95(spread_M5, bars N za mwisho)   # kinga ya spikes
spread_effective = max(spread_base, spread_vol_adj)             # ← inayotumika kwenye cost_pips
```
**Kwa nini H1 ndiyo msingi:** entry inatokea kwenye bar ya H1; ukwasi, fill, na muundo wa hatari
(SL/TP, lots) vyote vinalingana na uhalisia wa H1. Kutumia spread ya M5 **peke yake** = kudharau
gharama → lots kubwa mno → **EV ya bandia**.

**Kwa nini M5 inaongezwa:** H1 inaficha **spikes za ndani ya bar** (upanuzi wa spread, slippage).
p95 ya M5 inanasa hizo bila kuruhusu wastani wa M5 kushusha makadirio.

**Athari:** spread halisi zaidi → position ndogo kidogo → **EV ya kweli inayoweza kuuzika**
(attestation), badala ya edge ya bandia.

### 3.2 Slippage — **CAP, si utabiri** (uamuzi wa PD 2026-08-02)

Hatutabiri slippage. **Tunaifunga.** Kila order inatumwa na `deviation` (max slippage) — bei
ikienda mbali zaidi ya kikomo, **order HAIJAZI** badala ya kujaza kwa bei mbaya.

```
cap = min( dynamic_estimate(M5_volatility) , backtest_assumption )   # inabana TU
#      ^ M5 = chanzo KILICHOTEULIWA cha slippage/volatility (§0 — kazi za TF)
slippage_pips   = cap                    (thamani ya sizing = kikomo, si makadirio)
order.deviation = cap × (PipSize ÷ point)                   # MT5 inatumia POINTS
```
**Chanzo:** M5 (kazi yake ni intrabar analytics — §0). **Inatumika:** kwenye order ya H1
(muktadha wa utekelezaji).

**Cap inayoweza kubana, isiyoweza kulegea (PD 2026-08-02):** soko likiwa tulivu, M5-volatility
inaruhusu cap **ngumu zaidi** (fills bora). Soko likichafuka, cap **HAIZIDI** dhana ya backtest —
kwa hiyo dhamana ya "live ≤ backtest" **inabaki**. Cap ikiruhusiwa kulegea, namba zilizothibitishwa
hazingekuwa halali tena.

**Kanuni ya dhahabu — cap = dhana ya utafiti:**
`episodes()` ilihesabu kila trade ikitoza `SLIP_STOP = 0.3` (stop) / `SLIP_MARKET = 0.1` (market).
Tukiweka **cap ILE ILE**, basi:
```
slippage ya live  ≤  slippage iliyodhaniwa kwenye backtest     ← KWA UJENZI
```
Namba zilizothibitishwa (EV, ratio) **zinabaki halali** — hazitegemei bahati ya broker. Hii ndiyo
faida kubwa: **pengo kati ya utafiti na live linafungwa**, si kupunguzwa.

**Kinachopotea (uwazi):** orders zingine hazitajaza. Hiyo ni **bei ya usalama** — trade
iliyokosekana ni bure; fill mbaya kwenye edge nyembamba ni ghali.

**Kipimo cha lazima — FILL RATE.** Cap ikiwa ngumu sana, trades zinapungua kuliko utafiti ulivyodhani
→ **strategy halisi inakuwa tofauti na iliyothibitishwa.** Kwa hiyo:
```
fill_rate = orders zilizojaza ÷ orders zilizotumwa
KAMA fill_rate < fill_rate_min  →  ONYO: "cap ni ngumu; strategy inatofautiana na utafiti"
```
Hatua ikitokea: (a) legeza cap **NA** rekodi kwamba dhana ya gharama imebadilika (namba za utafiti
zinahitaji kupimwa upya), au (b) acha strategy hiyo kwa broker huyu.

**MIPAKA — cap inalinda ENTRY pekee.** SL/TP ziko kwa broker; soko likiruka (gap, news), SL inaweza
kujaza mbali zaidi. **Hilo haliwezi kufungwa** (ukiliweka cap, huondoki kwenye trade — mbaya zaidi).
Backtest yetu tayari ni gap-honest (stop = touch), kwa hiyo hatari hii imo kwenye namba — lakini
**si bounded**. Ni tail-risk halali inayobaki.

**Data (bure, bila mradi mpya):** kila fill inarekodi `requested_px`, `fill_px`, `slippage halisi`,
`fill_rate`. Hii ni **kipimo**, si model — inatuambia kama cap inafaa na kama broker anabadilika.
Ikitokea baadaye tunataka usahihi zaidi, data ipo tayari; **lakini haihitajiki kwa mfumo kufanya kazi.**

### 3.3 Commission — **pande MBILI (round-turn)**
```
commission_pips = commission_per_lot_round_turn ÷ pip_value_per_lot
```
Broker akitoa bei ya **upande mmoja**, inaongezwa maradufu. `broker_costs.yaml` **ihifadhi round-turn**
(jina la field liwe wazi: `commission_usd_round_turn`).

### 3.4 Swap — spec kamili
```
1. Chagua kwa mwelekeo:   BUY → swap_long   ·   SELL → swap_short
   (swap_long/swap_short/swap_mode zinatoka MT5: SymbolInfoDouble/SymbolInfoInteger)

2. Badilisha kwa swap_mode:
   CURRENCY  →  thamani inatumika moja kwa moja
   POINTS    →  swap × point × contract_size
   INTEREST  →  (swap ÷ 100) × contract_size

3. Rollover: swap inatozwa TU kama trade iko wazi wakati wa rollover (00:00 server time).
   Jumatano → Alhamisi  =  swap × 3  (triple swap)
   siku nyingine        =  swap × 1

4. swap_pips = jumla_ya_swap_ya_usiku_zote ÷ pip_value_per_lot
   usiku_zinazotarajiwa = kutoka takwimu za strategy (mfano D1 ≈ 3.5 usiku; H1 intraday = 0)
```

### 3.5 Pip conversion
Sarafu ya akaunti ikitofautiana na quote-currency, `pip_value` inabadilishwa kwa rate ya sasa:
```
pip_value_acct = pip_value_quote × rate(quote_ccy → account_ccy)
```
Mfano: akaunti USD, EURGBP → pip_value inategemea GBPUSD. Inatumika kwenye lots NA kwenye
`commission_pips`/`swap_pips` (zote zinatokana na fedha, si pips).

---

## 4. LOTS

```
lots = risk_per_trade ÷ ((sl_pips + cost_pips) × pip_value_acct)
```
Gharama iko kwenye **denominator** — kwa hiyo SL ikigongwa, hasara halisi (pamoja na gharama zote)
ni **HASA** `risk_per_trade`. Kisha: `lots` inarekebishwa kwa `volume_step`/`volume_min`/`volume_max`
za broker; ikishuka chini ya `volume_min` → **REJECT** ("risk ndogo kuliko lot ya chini").

---

## 5. VIABILITY GATE (mpangilio wa ukaguzi)

| # | Ukaguzi | Sheria | REJECT reason |
|---|---|---|---|
| 1 | **max open trades** | open_positions < `max_open_trades` | `max_open_trades` |
| 2 | **max correlated** | exposure ya kundi < `max_correlated` (**makundi YOTE ya pair**) | `max_correlated:<kundi>` |
| 3 | **daily-loss brake** | KAMA `today_loss ≥ 0.75 × base` **NA** open_positions > 0 → kataa | `daily_loss_75pct_with_open` |
| 4 | **total-DD** | `(base_balance − current_balance) < max_total_dd` | `max_total_dd` |
|   | *(PD 2026-08-02: DD inazuia **entries mpya** PEKEE — **HAKUNA** kufunga positions zilizo wazi)* | | |
| 5 | **max-spread** | `spread_pips ≤ max_spread[symbol]` | `max_spread` |
| 6 | **news** | KAMA `trade_news == false` NA news kubwa inakaribia → kataa | `news_window` |

Kikikataliwa: **hakuna trade**, na rekodi ya `lifecycle=REJECTED` + sababu + config-fingerprint
inaandikwa (dashboard inaonyesha).

---

## 5b. SIGNAL ILIYOKATALIWA — HAIRUDISHWI (PD 2026-08-02)
KAIROS ni **event-driven**: kila bar ni tathmini **mpya**. Signal iliyokataliwa na gate **HAIWEKWI
kwenye foleni** wala **HAIRUDIWI**. Setup ikiendelea kustahili bar inayofuata, ni **tathmini mpya**
yenye bei mpya, spread mpya, gharama mpya na EV mpya — si ufufuo wa ile ya zamani.

**Sababu:** muktadha wa soko unabadilika kila bar. Kurudia signal ile ile = (a) kuingia kwa bei
iliyoshasogea (EV imeshuka), (b) sifa ya kupita kiasi (over-fitting ya "kusubiri nafasi"),
(c) uwiano mbaya wa hasara. Hakuna signal queue kwenye mfumo huu.

---

## 6. MFANO KAMILI (end-to-end)

Akaunti $10,000 · base 4% = $400 · DD ya jumla −$200 · leo −$50 · positions wazi 2 · `max_open`=7
Model: USDJPY BUY, SL 30 pips · spread 1.2 · stop-order · commission $7/lot round-turn · usiku 0

```
penalty        = 0.50 × 200                       = $100
budget         = 400 − 100 + 0 − 50               = $250
risk_per_trade = 250 ÷ 7                          = $35.71

pip_value (USDJPY, 1 lot, akaunti USD)            ≈ $6.70
spread_pips    = 1.2
slippage_pips  = 0.3            (stop; SLIPPAGE MODEL ikikalibiwa → thamani halisi)
commission_pips= 7 ÷ 6.70                         = 1.04
swap_pips      = 0                                (intraday)
────────────────────────────────────────────────────────────
cost_pips                                          = 2.54

lots = 35.71 ÷ ((30 + 2.54) × 6.70) = 35.71 ÷ 218.0 = 0.164  →  0.16 (volume_step)
```
**Uthibitisho:** SL ikigongwa → 0.16 × 32.54 × 6.70 = **$34.88** ≈ risk iliyotengwa ✓
(tofauti ndogo inatoka kwa kuzungusha lot kwenda `volume_step`.)

Gate: open 2 < 7 ✓ · correlated ✓ · today_loss 50 < 300 ✓ · DD 200 < 1000 ✓ · spread 1.2 ≤ 2.0 ✓ ·
news ✓ → **PASS**, trade inafunguliwa.

---

