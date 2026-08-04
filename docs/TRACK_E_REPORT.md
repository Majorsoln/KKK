# RIPOTI YA TRACK E — RISK & COST ENGINE (`src/rce/`)

> **Kwa:** PD · **Spec:** `RISK_COST_ENGINE.md` (imetekelezwa KAMA ILIVYO — haijabadilishwa)
> **Rejista:** RCE-01..RCE-13 (`IMPLEMENTATION_PLAN.md` §3.1, ledger §3.5) · **Lango:** G7

---

## 0. MUHTASARI

`src/rce/` imejengwa kwa mpangilio ulioagizwa: **golden tests kwanza** (commit tofauti,
`b957867`, zikiwa nyekundu kwa sababu code haikuwepo), kisha code hadi zikawa kijani.
Vipengele **RCE-01..RCE-13 vyote ni `IMPLEMENTED`** na tests **109/109 kijani** (jumla ya repo:
170). Hakuna kigezo cha maamuzi kilichoandikwa kwenye code — vyote vinatoka
`config/risk.yaml` na `config/broker_costs.yaml`.

---

## 1. MPANGILIO WA KAZI (kama ulivyoagizwa)

| Hatua | Ilifanyika |
|---|---|
| 1. Golden tests kutoka namba za spec | commit `b957867` — jedwali la §2 (safu 4) + mfano wa §6; git history ndiyo ushahidi wa mpangilio (RS-01/G4) |
| 2. Code hadi tests zipite | `budget → cost → lots → gate`, kisha `engine` inayounganisha |
| 3. Hakuna signal queue (§5b) | `evaluate()` haina hali; audit ya `ast` inathibitisha njia ya kurudia haipo |

---

## 2. KILICHOJENGWA

| Faili | Spec | Rejista |
|---|---|---|
| `src/rce/config.py` | §1 | config + **fingerprint** (sha256 ya risk.yaml + broker_costs.yaml) |
| `src/rce/budget.py` | §2 | RCE-01, RCE-02 |
| `src/rce/cost.py` | §3.1–§3.5 | RCE-03, RCE-04, RCE-06, RCE-07, RCE-08 |
| `src/rce/lots.py` | §4 | RCE-09 |
| `src/rce/gate.py` | §5 | RCE-10, RCE-11 |
| `src/rce/fills.py` | §3.2 (fill rate) | RCE-05 |
| `src/rce/engine.py` | § mchoro + §5b | RCE-12, RCE-13 |
| `src/rce/symbols.py` | §3.3, §3.4, §4 | namba za broker (`broker_costs.yaml`) |
| `config/broker_costs.yaml` | §3.3 | template ya PD (`confirmed_by_pd: false`) |

Mambo machache yanayostahili kutajwa:

* **Bajeti (§2):** `today_profit` na `today_loss` ni vihesabu **viwili tofauti**, si namba moja
  — ndiyo maana safu ya 4 inatoa 175 (`400 − 125 − 150 + 50`), si 225. `penalty` inafuata DD ya
  jumla na **hairesetiwi**; ni `DayCounters` pekee zinazoreset 00:00 kwenye `day_reset_tz`
  (imethibitishwa kwa CET na CEST).
* **Spread (§3.1):** `max(wastani wa H1 bars 100, p95 ya M5 bars 288)`; matokeo yanaonyesha
  **kipimo kilichoshinda** (`H1_base` au `M5_p95`) kwenye log.
* **Slippage (§3.2):** `min(dynamic, dhana ya backtest)` — test inathibitisha dynamic ya pips 5.0
  **hairuhusiwi** kupandisha cap juu ya 0.3. `order.deviation` inatolewa kwa **POINTS**
  (0.3 pips × (0.01 ÷ 0.001) = points 3).
* **Lots (§4):** kuzungusha ni **floor** kwa `volume_step` — kuzungusha juu kungepitisha hasara
  juu ya `risk_per_trade`, jambo ambalo §4 inalikataza kwa maneno yake ("hasara halisi ... ni HASA
  `risk_per_trade`").
* **Gate (§5):** checks 6 kwa mpangilio, na check ya kwanza inayofeli ndiyo sababu — zilizobaki
  **hazikimbii**. Kila rekodi ina `lifecycle`, sababu, na **config-fingerprint**.
* **§5b:** hakuna foleni, hakuna retry. Audit inasoma `src/rce/*.py` kwa `ast` na kukagua
  **majina ya vitambulisho** (si comments), kwa hiyo "hakuna njia ya kurudia" ni uthibitisho wa
  code, si ahadi.

---

## 3. USHAHIDI

### 3.1 Golden tests (G7 — zinakimbia kila commit)

```
$ python -m pytest tests/rce/test_golden_spec.py
9 passed
```

Namba zilizotoka kwenye engine (si zilizonakiliwa kutoka spec):

```
=== §2 jedwali la bajeti ===
hali                           balance  penalty   budget    risk
Siku ya kwanza                   10000     0.00   400.00   57.14      (spec: 400 · 57.1)
Baada ya DD -200                  9800   100.00   300.00   42.86      (spec: 300 · 42.9)
Leo tayari -150                   9650   175.00    75.00   10.71      (spec:  75 · 10.7)
Leo +100 baada                    9750   125.00   175.00   25.00      (spec: 175 · 25.0)

=== §6 mnyororo kamili ===
risk_per_trade  = 35.71
pip_value_acct  = 6.70
cost_pips       = 1.2 + 0.3 + 1.04 + 0 = 2.5448        (spec: 2.54)
lots            = 0.1638 -> 0.16                        (spec: 0.164 -> 0.16)
hasara SL       = $34.89                                (spec: $34.88)
deviation       = 3 points · gate = PASS
```

**Kuhusu $34.89 dhidi ya $34.88:** spec inahesabu kwa `cost_pips` iliyozungushwa (2.54);
engine inatumia thamani kamili (2.5448). Tofauti ni senti moja ya kuzungusha, na golden test
inaruhusu ukingo wa $0.01 — si tofauti ya logic. Zote zinakidhi sharti la §6: hasara ≈ risk.

### 3.2 Tests kwa kila kipengele

```
$ python -m pytest tests/rce -q
109 passed
```

| Faili | Rejista | Kinachothibitishwa |
|---|---|---|
| `test_golden_spec.py` | RCE-01, 09, 13 | jedwali la §2 · mnyororo wa §6 |
| `test_budget.py` | RCE-01, 02 | penalty ya DD · `max(0,·)` · vihesabu viwili · reset ya CET/CEST · penalty haireseti |
| `test_cost_spread_slippage.py` | RCE-03, 04 | mseto H1/M5 · windows za config · cap inabana tu · deviation kwa POINTS · `limit` bila cap = hitilafu |
| `test_commission_swap_pipvalue.py` | RCE-06, 07, 08 | round-turn na one_side ×2 · modes 3 zote · triple WED · usiku wa sehemu · conversion ya pip_value |
| `test_lots.py` | RCE-09 | gharama kwenye denominator · floor ya step · REJECT chini ya min · cap ya max |
| `test_gate.py` | RCE-10, 11 | checks 6 · makundi YOTE ya pair · brake inahitaji positions wazi · mpangilio unaposhindana · fingerprint |
| `test_fills.py` | RCE-05 | fill_rate · ONYO < 0.60 + hatua (a)/(b) · slippage halisi · log ya jsonl |
| `test_engine_no_queue.py` | RCE-11, 12 | mnyororo 1–5 · hakuna hali baada ya REJECT · **AUD** ya `ast` (foleni/retry/kufunga positions) |
| `test_broker_costs.py` | §3.3, §4 | template haijathibitishwa → sizing imezuiwa · mapengo yanaripotiwa kwa jina |

---

## 4. MASWALI MATATU YANAYOHITAJI UAMUZI WAKO

Spec haiyajibu waziwazi; nimechagua njia inayolinda maana ya spec **bila kuibadilisha**, na
kila moja ina test. Ukiamua vinginevyo, ni **badiliko la spec (wewe)** kisha code inafuata.

1. **Ishara ya swap.** §3.4 inasema `swap_pips = jumla ÷ pip_value` na §3 inasema
   `cost_pips = ... + swap_pips` — kwa hiyo swap inayoongeza gharama lazima iwe **chanya**.
   Nimefanya `broker_costs.yaml` ihifadhi swap kama **gharama** (chanya = unalipa). MT5 inatumia
   ishara kinyume; adapter ya MT5 ndiyo itakayogeuza, mahali pamoja. **Thibitisha.**
2. **Orders za `limit`.** `slippage_cap_pips` ina `market` na `stop` pekee (= `SLIP_MARKET`/
   `SLIP_STOP` za `episodes()`). Order ya `limit` kwa sasa **inatupa hitilafu** badala ya kupewa
   cap ya kubuni. Ukitaka limit orders, ongeza kigezo chake kwenye `risk.yaml`.
3. **Symbols zisizo na `max_spread`.** Check 5 inataja `max_spread[symbol]`; config ina symbols 5
   kati ya 12. Symbol isiyo na kikomo **inapita** na onyo `max_spread_unset:<symbol>` linaandikwa
   (code haibuni kikomo). Ukipendelea "isiyo na kikomo = REJECT", ni badiliko la spec §5.

Zaidi ya hayo, nimeongeza kigezo kimoja kipya kwenye `config/risk.yaml`:
`account_currency: "USD"` — §3.5 inahitaji sarafu ya akaunti ili kubadilisha `pip_value`, na
kigezo hicho hakikuwepo popote. Kiko config (si code) kwa lango G10.

---

## 5. KINACHOZUIA `VERIFIED`

| # | Kinachohitajika | Athari yake sasa |
|---|---|---|
| 1 | **Namba za broker** → `config/broker_costs.yaml` (commission round-turn, swap + mode kwa symbol, volume_min/step/max, digits/point/contract_size) | `confirmed_by_pd: false` inazuia sizing yoyote; golden tests zinatumia namba za spec §6, kwa hiyo hazizuiwi |
| 2 | **Kuthibitisha** `account_currency` + majibu ya §4 hapo juu | code iko tayari kufuata jibu lolote |
| 3 | **Sahihi yako** juu ya golden tests | RCE-01..13 zinapanda `VERIFIED` |

Kinachofuata baada ya hapo ni **T7** (integration KAIROS-1 → RCE → MT5): adapter ya MT5
inayosoma sifa za symbol na kutuma order yenye `deviation` ya points, pamoja na kulisha
`FillTracker` kwa fills halisi (RCE-05 inakuwa RPT ya live).

---

## 6. NJE YA WIGO — KILICHOACHWA MAKUSUDI

* **Spec haijabadilishwa.** Hakuna neno lililoongezwa au kuondolewa `RISK_COST_ENGINE.md`.
* **Idara 3 haijaguswa.** RCE haihesabu EV, ratio wala uteuzi wa setup (§UBORA ya spec).
* **OPM (positions zilizo wazi) haipo** — RCE-11 inahakikisha DD inazuia entries mpya pekee, na
  audit inathibitisha hakuna function ya kufunga position kwenye idara hii.
* **Tabaka la data (T0) halijaguswa** na kazi hii.
