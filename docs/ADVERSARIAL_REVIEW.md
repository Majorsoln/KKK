# Ukaguzi wa uadui — DOCTRINE + RCE kwa pamoja

**Tarehe:** 2026-08-18 · **Kabla ya:** `src/data/`
**Lengo:** *contradictions · undefined variables · leakage paths · double-counting ·
assumptions zinazofanya mfumo uonekane wenye faida bila kuwa nao.*

Hati mbili zimesomwa **pamoja**, si kila moja kivyake — kwa sababu mikanganyiko yote
mikubwa iliyopatikana iko **kwenye mpaka** kati yao, si ndani ya moja.

---

## Muhtasari

| # | jambo | daraja | hali |
|---|---|---|---|
| **A1** | `pips` na **pesa** zinaweza kutofautiana kwa **ishara** | 🔴 | wazi |
| **A2** | Calibration A na B zinaweza kugusa holdout | 🔴 | wazi |
| **A3** | Backtest hairekodi **budget kuisha** | 🔴 | wazi |
| **A4** | `stability`, `complexity`, `overfit_score` hazijafafanuliwa | 🟠 | wazi |
| **A5** | Madirisha ya `*_percentile` na `vol_regime` hayajatajwa | 🟠 | wazi |
| **A6** | Sheria ya kufit regime haijarudiwa §6 | 🟠 | wazi |
| **A7** | Lango la §8.4 linatumia gharama ya **matumaini** | 🟠 | wazi |
| **A8** | `max_conditions` dhidi ya recombination | 🟡 | wazi |
| **A9** | `fill_rate` — RCE inaonya, Doctrine inakataa. Kipi? | 🟡 | wazi |
| **A10** | Slippage: sizing dhidi ya backtest — **si** double-count | ⚪ | imefungwa |

---

## A1 · `pips` na pesa zinaweza kutofautiana kwa ISHARA 🔴

**Ndilo tatizo kubwa zaidi kwenye hati zote mbili, na liko kwenye kipimo cha msingi.**

§1.1 inaweka `net_pips_month` kama PRIMARY OUTCOME. RCE §4 inaweka:

```
lots           = risk_per_trade ÷ ((sl_pips + cost_pips) × pip_value)
risk_per_trade = budget ÷ max_open_trades
budget         = base − penalty_factor × DD + …
```

**Lots zinategemea NJIA.** Drawdown ikitokea, budget inashuka, lots zinashuka. Kwa hiyo
faida inayokuja **baada** ya hasara inakuja kwa ukubwa mdogo.

Lakini **pips hazitegemei mpangilio.** Seti ile ile ya trades ina jumla ile ile ya pips
haijalishi zimekuja kwa utaratibu upi. **Pesa si hivyo.**

### Ushahidi

Seti moja: trades 25 za −30 pips, trades 13 za +60 pips. Jumla: **+30 pips**, kwa
mpangilio wowote. Kwa fomula halisi za RCE (`base 4%`, `penalty_factor 0.5`,
`max_open 7`, `SL 30`, `cost 2.54`, `pip_value 6.70`):

| mpangilio | jumla ya pips | pesa |
|---|---|---|
| hasara kwanza | **+30** | **−$72.21** |
| faida kwanza | **+30** | **+$52.68** |

**Ishara inageuka kwa mpangilio pekee.** Strategy inaweza kuwa `net_pips_month` chanya
kwa miezi yote na bado ikapoteza pesa.

### Kinachotakiwa

`net_pips_month` ibaki, lakini **haiwezi kuwa PRIMARY OUTCOME peke yake.** Primary
outcome iwe **mbili**:

```
net_pips_month              ← isiyotegemea sizing (inalinganisha strategies)
net_account_return_month    ← ikipitishwa kwenye RCE sizing (ndiyo pesa)
```

Na sheria: **zikitofautiana kwa ishara, `net_account_return` ndiyo yenye mamlaka**, na
tofauti yenyewe iripotiwe kama **onyo la path-dependence**.

---

## A2 · Calibration A na B zinaweza kugusa holdout 🔴

R9: *holdout inaguswa **mara moja***. Lakini §8.3 inasema Calibration A inapima gharama
"kwa kila `(pair, TF)`", na §9.2 inasema data bandia inahifadhi "tabia za kitakwimu za
data halisi".

**Zote mbili zinapendekeza kusoma data yote — ikiwemo 2024-04 → 2026-04.**

Hilo si "kutumia holdout" kwa maana ya kawaida (hakuna label inayoangaliwa), lakini ni
**kuisoma**. Gharama ya 2025 ikiingia kwenye lango linalochuja wagombea, holdout
imeshaathiri uteuzi kabla haijaguswa rasmi.

### Kinachotakiwa

```
Calibration A → 2016-04 … 2024-03 PEKEE
Calibration B → data bandia iliyojengwa kutoka 2016-04 … 2024-03 PEKEE
```

Na sheria mpya: **kila hatua inayosoma data inatangaza dirisha lake, na dirisha
lolote linalovuka 2024-03 linakataliwa kiotomatiki**, si kwa nidhamu ya mtu.

---

## A3 · Backtest hairekodi budget kuisha 🔴

Ni **familia ile ile** ya `NO_FILL` (§11.1), na haikushughulikiwa.

RCE §2: `budget = base − penalty_factor × DD`. Kwa `base = $400` na
`penalty_factor = 0.5`:

```
DD = $800  →  budget = 400 − 400 = 0  →  risk = 0  →  lots = 0
```

**Kwa DD ya $800 (8% ya salio la msingi) mfumo unaacha kutrade kabisa.** Na kabla ya
hapo, `volume_min` inaingia: lots zikishuka chini ya lot ya chini ya broker, RCE
inatoa **REJECT** ("risk ndogo kuliko lot ya chini").

Backtest isiyoiga hilo inahesabu trades ambazo live isingezifungua **hasa pale mambo
yalipokuwa mabaya zaidi** — ambako ndipo strategy nyingi hupata "recovery" yao
inayoonekana vizuri kwenye chart.

### Kinachotakiwa

Tokeo la tatu la utekelezaji:

```
FILL · NO_FILL · NO_BUDGET
```

na `NO_BUDGET` ihesabiwe kando kwenye §15.2 ledger. Vilevile `min_lot_reject`.

---

## A4 · Variables tatu zinatumika bila kufafanuliwa 🟠

| variable | inatumika wapi | tatizo |
|---|---|---|
| `stability` | fitness §13 (uzito 0.15) | haijafafanuliwa popote |
| `complexity` | fitness §13 (uzito −0.10), DNA §10.2 | "masharti mangapi"? au kina cha tree? |
| `overfit_score` | Strategy DNA §13 | haijafafanuliwa |

Formula ya kupanga yenye variable isiyofafanuliwa **haiwezi kutolewa upya** — na
kipimo kisichoweza kutolewa upya si kipimo.

**Pendekezo:**

```
stability     = 1 − (sd ya net_pips_month ÷ |wastani wa net_pips_month|)
                ...ikifungwa [0, 1]
complexity    = idadi ya masharti ya entry + ya exit
overfit_score = (IS_PF − OOS_PF) ÷ IS_PF        ...juu = mbaya
```

Hizi ni mapendekezo, si maamuzi. Kinachotakiwa ni **kufafanuliwa**, si kufafanuliwa
kwa namna hii mahsusi.

---

## A5 · Madirisha ya percentile hayajatajwa 🟠

§5 ina `ATR_percentile`, `tick_count_percentile`, `vol_regime`. **Percentile
kulinganishwa na nini?**

Ikiwa ni percentile juu ya **sample nzima**, ni **uvujaji wa kimya**: bar ya 2017
ingejua kwamba volatility ya 2020 ilikuwa kubwa kiasi gani. Hakuna test itakayoiona,
na itajionyesha kama ustadi.

**Kinachotakiwa:** kila feature ya percentile inatangaza dirisha lake la nyuma
(mfano `ATR_percentile_252d`), na jina la feature linaonyesha dirisha — ili
`ATR_percentile` bila dirisha isiwepo kabisa kwenye code.

---

## A6 · Sheria ya kufit regime haijarudiwa §6 🟠

§5 inasema: *"feature yoyote inayotokana na model iliyofit inafundishwa expanding au
per-fold, kamwe si juu ya sample nzima."*

§6 inaruhusu KMeans / GMM / HMM kwa regimes — **na hairudii sheria hiyo.** HMM
iliyofit juu ya 2016–2024 kisha kutumika kwa 2017 ni uvujaji wa moja kwa moja.

**Kinachotakiwa:** §6 iseme wazi kwamba regime detector ni **model-derived feature**,
kwa hiyo iko chini ya sheria ya §5 bila ubaguzi.

---

## A7 · Lango la uchumi linatumia gharama ya matumaini 🟠

§8.2 inaanzisha `research_cost` (halisi) na `live_sizing_cost` (kihafidhina), na
`live ≥ research` daima.

§8.4 inaweka lango: `gross < 2 × research_cost → kataa`.

**Kwa hiyo lango linatumia namba ndogo kati ya mbili.** Candidate inaweza kupita lango
kwa `research_cost` na bado isiwe na uchumi kwa gharama ambayo live itaitumia
kuiweka ukubwa.

**Kinachotakiwa:** lango litumie `live_sizing_cost`, au litumie zote mbili na
kuripoti candidate zinazopita moja pekee kama **darasa lake**. Kutumia ya matumaini
kimya ndiyo aina hasa ya assumption iliyotafutwa kwenye ukaguzi huu.

---

## A8 · `max_conditions` dhidi ya recombination 🟡

§10.3 inaweka `max_conditions = 3–5`. §10.4 inaruhusu mutation na recombination.

Mzazi mwenye masharti 4 na mwenye 4 wakichanganywa wanaweza kutoa mtoto mwenye 8.
**Haijatajwa kama kikomo kinatumika kwa vizazi vyote au kwa kizazi cha kwanza pekee.**

---

## A9 · `fill_rate` — RCE inaonya, Doctrine inakataa 🟡

`config/risk.yaml:48` ina `fill_rate_min: 0.60` — na maelezo yake ni **ONYO**.
Doctrine §11.3 inasema candidate yenye `OOS_fill_rate` ya chini **inakataliwa**.

Si mgongano wa kimantiki (RCE ni ya live, Doctrine ni ya utafiti) lakini **kizingiti
cha Doctrine hakijatajwa.** "Chini sana" si namba.

**Kinachotakiwa:** kizingiti kitoke `noise_floor.fill_rate` (§9.2), si kwa kuchaguliwa.

---

## A10 · Slippage: sizing dhidi ya backtest ⚪ *imefungwa*

Nilichunguza kama slippage inatozwa mara mbili:

* RCE inaiweka kwenye **denominator** ya lots — inapunguza **ukubwa**
* Backtest inaitoza kwenye **return** — inapunguza **matokeo**

Ni kazi mbili tofauti kwa namba ile ile, si kuhesabu mara mbili. Vilevile commission:
`commission_side: "round_turn"` inagawanywa nusu ENTRY na nusu EXIT (§8.1) — jumla ni
ile ile, si mara mbili.

Imeandikwa hapa **ili isije "ikarekebishwa"** na mtu atakayeiona baadaye.

---

## Kilichokwisha kufungwa kwenye pass hii

| | |
|---|---|
| commission ilikuwa chini ya `HOLDING_COST` | imehamia ENTRY/EXIT (§8.1) — inalipwa kwa muamala, si kwa muda |
| sakafu moja kwa metrics zote | `noise_floor[metric]` (§9.2) |
| pengo 2024-01 → 2024-03 | dirisha la mwisho la walk-forward limepanuliwa hadi 2024-03 |
| metrics zinazopigana | madaraja manne (§1.1): PRIMARY · GATE · RANKING · DIAGNOSTIC |

---

## Hukumu

Hati hazihitaji kuandikwa upya. Zinahitaji **mikataba mitatu ifungwe** kabla ya code:

1. **A1** — primary outcome iwe pips **na** pesa; pesa ina mamlaka
2. **A2** — kila hatua inayosoma data inatangaza dirisha; kuvuka 2024-03 ni kosa la kiotomatiki
3. **A3** — `NO_BUDGET` ni tokeo la utekelezaji, si tukio la kando

Nne zilizobaki (A4–A7) ni **ufafanuzi**, si mabadiliko ya muundo — lakini bila hizo
code itafanya maamuzi ambayo hati hazijayafanya, na hapo hati itakuwa imeacha kuwa
doctrine.
