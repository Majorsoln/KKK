# Mapitio ya nje — MTAALAMU WA 1

**Tarehe:** 2026-08-13 · **Duru:** 3 (jibu la kwanza + F1–F7 + F8–F11)
**Hadhi:** imeandikwa **kabla** mtaalamu wa 2 na 3 hawajajibu.

> **Kwa nini imeandikwa sasa.** Jibu la mtaalamu likikaa kichwani mwangu hadi
> baada ya kusikia wengine, litabadilika bila mimi kujua — nitakumbuka toleo
> linalolingana na wanayosema wenzake. Ni sababu ile ile ya pre-registration:
> kilichoandikwa kabla hakiwezi kubadilishwa na kile kinachokuja baadaye.
> Hakuna neno la sehemu hii litakalohaririwa baada ya mtaalamu wa 2 kuzungumza.

---

## 1. Hukumu yake kwa ufupi

**Hakukataa soko. Alikataa swali letu.**

> "I would not conclude that H1 FX cannot contain an edge. But I would reject the current
> formulation: *predict which fixed SL/TP barrier wins, then stack enough models to turn that
> probability into EV.* That is not the quantity I would spend the next year estimating."

Uhakika: **juu** kwamba muundo wa swali ubadilike · **wa kati** kwamba faida itadumu.

---

## 2. Maelezo ya jaribio la kwanza — kama alivyoyaandika mwisho

```
Kila H1 close halali  →  OBSERVATION MOJA  →  lengo: signed executable net-R
```

| Kipengele | Uamuzi wake |
|---|---|
| Observation | **bar moja ya H1**, si 2 (long/short), si 25 (cells) |
| Upande | `sign(R̂_signed)` kutoka head MOJA ya signed-return |
| Score ya fursa | `\|R̂_signed\|` |
| Long/short mbili | **diagnostic pekee** — `R̂_long ≈ −R̂_short`; asymmetry isiyokuwepo kwenye data halisi = red flag |
| Horizon | 24H ya msingi; {6, 12, 48} kama secondary zilizotangazwa, **hakuna kuchagua mshindi baadaye** |
| SETUP-v1 | feature na benchmark (`setup_v1_flag`), **si mamlaka ya upande** |
| Barrier grid | kwa **tathmini**, si kwa kufundisha |
| Models | linear/logistic · XGBoost · ranking rahisi. **Hakuna deep, hakuna PPO** |
| Uzito | uniqueness weighting ni **lazima** |
| Uthibitisho | block bootstrap · placebo mbili (random-label, shuffled-score) |

### Features 25 alizoziainisha

| Kundi | Features |
|---|---|
| Returns / momentum (6) | `ret_1h` · `ret_4h` · `ret_8h` · `ret_24h` · `ret_48h` · `impulse_4h_atr` |
| Volatility (5) | `ATR14` · `ATR14_percentile_252` · `realized_vol_24h` · `realized_vol_72h` · `vol_ratio_24h_168h` |
| Trend structure (5) | `EMA20_distance_atr` · `EMA50_distance_atr` · `EMA20_vs_EMA50_atr` · `ADX14` · `efficiency_ratio_24h` |
| Mean-reversion (4) | `RSI14` · `BB_zscore_20` · `close_position_24h_range` · `distance_to_24h_high_atr` |
| Market / execution (4) | `spread_p50` · `spread_ratio_528` · `hour_sin` · `hour_cos` |
| Benchmark (1) | `setup_v1_flag` |

**Hoja yake ya muundo:** SETUP-v1 isiingie kama bendera pekee — malighafi yake (impulse
magnitude, ATR percentile, spread ratio) iwekwe wazi, kisha bendera iongezwe. Hivyo swali
linajibika: *je model inaigundua SETUP yenyewe, au SETUP ina taarifa ya ziada baada ya
features zote kuwepo?*

---

## 3. Malango ya kuua — yaliyorekebishwa

Toleo lake la kwanza lilikuwa **Top-10% ≥ +0.05R**. Baada ya kuonyeshwa kwamba top-10% ya
wagombea dense ni biashara ~59 kwa siku wakati uwezo halisi ni ~5 (≈ **0.9%**), alibadili:

> "+0.05R ilikuwa **arbitrary** — research-quality hurdle, si threshold iliyotokana na
> gharama zenu. Sitaki mu-sign kama ukweli wa kiuchumi."

**Malango mawili ya ngazi:**

| Lango | Kipimo | Sharti |
|---|---|---|
| **Ranking (kitakwimu)** | Top-10% | Spearman ρ > 0 kwa deciles 10 za pooled OOF, one-sided p < 0.05 |
| **Kiuchumi (uwezo)** | Top-1% | `E[R_net] > 0`, na **95% lower bound > 0** (block bootstrap) |
| **Mtiririko** | zote | `R_1% ≥ R_5% ≥ R_10%` — top-1% hairuhusiwi kuwa mbaya kiuchumi kuliko top-10% |
| **Utulivu** | folds | 4/5 chanya; hakuna fold mbaya kuliko −0.05R |

**Sheria ya kuua:** kikiwa chochote kati ya hivyo kimefeli, **hypothesis ya ranking imekufa** —
si mradi mzima wa FX.

> "If this experiment fails, I would not respond by adding more features or models. That
> failure would be evidence against the underlying hypothesis itself."

---

## 4. Effective N — alikataa kutoa namba moja

> "There is no defensible scalar. If I gave you one number, I would be creating false precision."

Envelope, ikichukua **ndogo kuliko zote**:

| Kipimo | Njia |
|---|---|
| `N_time` | `N ÷ τ`, ambapo `τ = 1 + 2Σρ_k` (integrated autocorrelation time) |
| `N_uniq` | `Σ u_i`, ambapo `u_i = (1/H)·Σ_t 1/C_t` — concurrency ya labels za 24H |
| `N_cross` | participation ratio `(Σλ)² ÷ Σλ²` ya correlation matrix baada ya kuondoa factor kuu |
| `N_regime` | idadi ya blocks huru kwa cluster-bootstrap |

`N_eff = min(...)`. Na `÷50` ni **heuristic ya bajeti ya utafiti, si theorem** — ledger
iandike makadirio + sheria + upeo wa unyeti, si namba moja ya kichawi.

---

## 5. Jaribio la kuua athari ya SETUP (siku 4–6)

**Stratified bins zilizotangazwa**, si propensity scores — kwa sababu treatment ni
**deterministic**; model wa propensity ungeongeza nafasi nyingine ya kukosea.

Bins: ATR percentile · spread percentile · momentum magnitude · hour/session · pair · year.

**+0.0638R ikishuka nusu si kufeli** — ni tafsiri mpya: *"SETUP inatoa kichujio cha wastani cha
fursa, ambacho taarifa yake ya ziada sasa lazima ijifunzwe na kupangwa"* badala ya *"SETUP
inagundua taarifa yenye nguvu."*

---

## 6. Stop zilizoruka (F6)

$$R_{stop} = -\left(1 + \frac{\text{overshoot}_{pips}}{SL_{pips}}\right)$$

> "It is **not merely an evaluation correction.** If two trades have identical predicted
> probability but Trade A has a 10-pip stop and Trade B a 2-pip stop, the same absolute
> overshoot has radically different economic consequences."

Na tofauti anayoisisitiza: maswali **mawili**, yote yanapaswa kuripotiwa —
(1) njia ya bei ya kihistoria ingezalisha nini, (2) execution model ipi ni ya kutetereka kwa
broker halisi. **Usibadilishe cap ya 0.3 kwa overshoot ya kihistoria bila kutofautisha hayo.**

---

## 7. Uwezo (F7)

Positions **5** · correlation ya jozi ≤ **0.70** · **pamoja na kizuizi cha currency/factor**.

> "Don't allow the system to believe EURUSD long + GBPUSD long + AUDUSD long + NZDUSD long
> are four independent trades. They may be essentially one USD-short macro position."

---

## 8. Uongo unaowezekana zaidi (swali 12)

> **Volatility-conditioned momentum masquerading as predictive intelligence.**

SETUP-v1 inachagua kwa makusudi mienendo mikubwa ya karibuni kwenye masoko yenye shughuli
(ATR p50 16.1 dhidi ya 14.3). Model inaweza kugundua *"mwendo mkubwa + volatility ya juu →
uwezekano kidogo zaidi wa kuendelea"* na ikaonekana kama ML alpha ya kisasa — wakati mfumo
halisi ni **volatility clustering + short-term momentum + selection conditioning**.

Hatari inaongezeka mfumo ukirundika models zinazogundua **feature ile ile fiche** mara kwa mara:
*"You get an apparently sophisticated consensus from models that are not actually independent."*

---

## 9. Kile alichokipinga kwa nguvu zaidi kwenye brief yetu

> "Combined effect on effective N: we estimate ~5×." — **"I would not accept that estimate
> without measurement. That is currently an assumption."**

Na, kuhusu utawala wetu:

> **"A ledger does not mathematically eliminate selection bias. It makes the selection
> auditable. Those are different things."**

---

## 10. Alichokiacha kwa makusudi kwenye duru ya kwanza

| Kilichoachwa | Sababu yake |
|---|---|
| held-out kwa symbol | "swali la kwanza ni *je kuna ranking yoyote?* Generalization ni lango la pili" |
| year/regime breakdown | limetolewa kupisha placebo |
| MAE / MFE | "optional" kwa duru ya kwanza |
| Dollar / volume / imbalance bars | "later — usijenge upya kabla hypothesis ya msingi haijanusurika" |
| 2003 | tumia, lakini kwa tabaka za regime; kipimo ni *"je model iliyofundishwa na crisis regimes inatenda kwa busara kwenye regimes mpya?"* |

**Placebo ndiyo aliyoichagua** kama ya lazima kuliko zote: *"Can our complete pipeline
manufacture a positive ranking result when there is no signal?"*

---

## 11. Wazo lake la mwisho — lililokuja likiwa la mwisho lakini si dogo

Kuhusu MAE/MFE:

> "If `E[R_24h]` is weak but MFE is strong, then the problem may not be entry alpha. It may be
> that **entry has information, but the 24H exit/barrier policy destroys it.** That distinction
> could completely change KAIROS-1."

---

## 12. Mahali ninapotofautiana naye (maoni yangu, si yake)

**1. MAE/MFE hazipaswi kuwa za hiari.** Amezitaja mwisho kama nyongeza, lakini hoja yake ya §11
ndiyo yenye uzito mkubwa kuliko mengi aliyoyasema: kama entry ina taarifa lakini exit policy
inaiharibu, tumekuwa tukipima kitu kibaya kwa miezi. Gharama ya kuzikusanya ni **karibu sifuri**
— ticks tayari ziko kwenye kumbukumbu wakati wa build. Kuziacha ni kuokoa kitu kisichogharimu
kitu, huku tukiacha swali linaloweza kubadilisha mradi mzima bila jibu.

**2. Lengo `Y` bado halijafafanuliwa kikamilifu.** "Realized executable net-R for a pre-specified
action" — lakini **action ipi**? Trade inayotekelezeka inahitaji SL (RCE inaihitaji kwa sizing).
Kama Y ni return ya 24H bila stop, si trade inayotekelezeka. Kama ina stop, ni ipi — na kuchagua
2.0/2.0 kwa sababu jedwali letu la EV linaipendelea ni **uteuzi juu ya label**. Hili ni pengo
lililobaki.
