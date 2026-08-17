# ELITEFX — External Review Brief #2

**Prepared for:** an external practitioner or researcher who works on systematic trading
and/or ML on market data. No familiarity with brief #1 is assumed.
**Prepared:** 2026-08-17
**Status:** request for adversarial review. Not a proposal to approve.

---

## 0. What we are asking for, and what we are explicitly releasing you from

Since brief #1 we have completed four research phases. Every one of them returned a
**negative or inconclusive** result. The pipeline is clean, the measurements are
reproducible, and we can now state a fairly precise *impossibility structure* for what we
have been attempting.

We want you to tell us whether that structure is real, or whether it is an artefact of
**how we decided to do research** rather than of the market.

**You are released from our doctrine.** §6 lists the methodological commitments we have
been operating under — trial budgets, pre-registration, a cost identity, an effective-N
envelope, a fixed labelling scheme. We have treated these as load-bearing. Several of them
may be wrong, or right in principle but calibrated so conservatively that they have made
the project unfalsifiable-in-practice. **If your answer is "your governance is the
problem, not your alpha", that is a legitimate and valuable answer.** Please say it
plainly.

Equally legitimate: *"this space is saturated, retail-cost H1 FX breakout has no edge, stop
and do something structurally different."* We would rather lose the direction than spend
another year confirming it.

Concrete beats polite. Where you disagree, say what you would do instead.

**The questions are in §8, and the forced choice is in §9.** Everything before that is
context so your answers can be specific.

---

## 1. The system, in one page

**Goal:** an ML component that decides *whether to take* a trade. A separate, already-built
Risk & Cost Engine (RCE) decides sizing, stops and exposure limits; it is out of scope here
and is not modifiable. So the question is narrowly: **can we identify, in advance, which
candidate trades are worth taking?**

**Instrument universe:** 11 FX pairs + spot gold — EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD,
AUDUSD, NZDUSD, EURGBP, EURJPY, EURCHF, GBPJPY, XAUUSD.

**Data:** bid/ask **tick** data from a single broker (Dukascopy, demo account, MT5 feed),
`2016-01-04` → `2024-03-31` used for train+validation. `2024-04-01` → `2026-04-30` is a
**holdout that has never been read, not once**. H1 bars are built from ticks (~50,260 bars
per symbol). Data quality gates run at bar level; failed days are excluded, not patched.

**Entry rule (SETUP-v1)** — mechanical, fixed before any label existed:

| Gate | Rule |
|---|---|
| Trigger | \|close − close[−4]\| ≥ 2.5 × ATR(14); direction = sign of that move |
| Spread | bar spread ≤ 1.5 × rolling median spread (528 bars) |
| Volatility band | ATR percentile within [0.20, 0.95] over trailing 6 months |

Fires on ~4.5% of eligible bars. **It was tuned to hit a rate target only, never to improve
outcomes** — that constraint was self-imposed (see §6).

**Labels:** triple-barrier on the **tick path**, at trade price (so spread is inside the
path, not added afterwards). Barrier grid is 7 stop levels × 7 target levels in ATR units:
`sl ∈ {0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0}`, `tp ∈ {0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0}`.
Horizon **24 H1 bars**. Timeout is a **third outcome class** with its recorded terminal
return, not silently dropped. Ties (a gap covering both barriers) resolve to stop-first.

**Sample:** 52,321 decision points — 25,314 SETUP-v1 firings and 27,007 **controls** (a
5%-sampled, hash-reproducible set of eligible non-setup bars, so that "the filter helps"
can be tested against something). × 49 cells = 2,563,729 barrier outcomes.

**Validation:** purged 5-fold CV, embargo 36 bars (1.5 × horizon), standardisation from the
training fold only, sample weights from label-overlap uniqueness.

**Feature set:** 25 features, all scale-free (log returns, ATR-relative distances,
percentile ranks, ratios) so that one model can be trained across instruments of very
different price scale.

---

## 2. What has been measured

All numbers below are out-of-sample within train+val (purged CV) or are simple population
statistics on train+val. **None involve the holdout.** `R` = multiples of the initial stop
distance, net of assumed commission, with spread already inside the path.

### 2.1 The entry rule does select better-than-random trades

Pooled over all 49 cells:

| | p(TP first \| resolved) | E[R] |
|---|---|---|
| SETUP-v1 | 0.4203 | **−0.0290** |
| Control | 0.3985 | **−0.0846** |
| difference | +0.0218 (z +32.9) | **+0.0556 R** |

Matched comparison (ATT-weighted; strata = ATR bin × spread bin × session × symbol × year;
block bootstrap by year; common support 96.4%):

> **+0.0348 R, 90% CI [+0.0051, +0.0612]**

So entry selection has demonstrable causal traction on realised R. We consider this the
single most solid positive result in the project.

### 2.2 But the absolute level is at breakeven, at every barrier setting

`EV net` by cell (10-symbol pool; see §2.4 for why 10):

| `tp` ↓ / `sl` → | 2.0 | 3.0 | 4.0 |
|---|---|---|---|
| 1.0 | −0.0210 | −0.0070 | −0.0087 |
| 2.0 | −0.0050 | +0.0057 | +0.0007 |
| 3.0 | +0.0039 | +0.0121 | +0.0060 |
| 4.0 | +0.0075 | +0.0137 | +0.0067 |
| 6.0 | +0.0177 | **+0.0205** | +0.0123 |

* Along `sl` there is an **interior maximum at 3.0**, in 6 of 7 rows. Wider stops cut cost
  per R (`commission_R = commission_pips ÷ sl_pips`) but raise timeout share, and beyond
  3.0 the dilution wins.
* Along `tp` the surface is **still rising at the grid edge (6.0)** in 7 of 7 rows, but
  timeout at `sl 3.0 / tp 6.0` is already 30.6%.

Best cell `sl 3.0 / tp 6.0`:

| | |
|---|---|
| `EV net` | **+0.0205 R** |
| 90% CI (block bootstrap by year) | [−0.0015, +0.0404] |
| **Šidák lower bound over 49 cells** | **−0.0212** |
| `cost_R` | 0.0167 (commission 0.0133 + stop overshoot 0.0034) |
| implied max trades/yr (see §3) | 441 |

It is the **argmax of 49 cells**. Corrected for that, it does not clear zero.
**No cell in the grid is demonstrably profitable.**

### 2.3 The ML filter does not add measurable economic value

Meta-labelling (SETUP-v1 fixes the side; a secondary model decides take/skip). Logistic
with L2 + Platt calibration; 25 features; purged 5-fold; uniqueness weights. Gates were
declared before the run.

| Gate | Declared threshold | Result | |
|---|---|---|---|
| Calibration (reliability slope) | ∈ [0.8, 1.2] | 1.0713 | PASS |
| Discrimination (Spearman on deciles) | ≥ 0.70 | 0.8182 | PASS |
| Economic (fitted top-decile p) | ≥ breakeven + δ_MER | 0.3159 vs 0.3212 | **FAIL** |

Top decile realised **+0.0656 R** vs pool −0.0163 R.

**Then the placebo phase invalidated most of that.** We re-ran the identical pipeline on
corrupted labels, three ways:

| Null construction | ρ null p95 | ρ p-value | top-R p-value | null median top-R vs base |
|---|---|---|---|---|
| iid shuffle (breaks everything) | +0.5176 | 0.048 | 0.143 | −0.0080 vs −0.0163 (clean) |
| circular rotation within symbol | +0.8067 | 0.095 | 0.124 | +0.0275 (contaminated) |
| block permutation within symbol | +0.8545 | 0.075 | 0.124 | +0.0283 (contaminated) |

Two findings:

1. **Our declared discrimination threshold of 0.70 sat inside the noise distribution**
   (block null p95 = 0.8545). It was never a gate. We chose it by argument, not by
   simulation, and ran the confirmatory phase before the placebo phase — our own written
   protocol said to do the reverse.
2. Any null that permutes **within symbol** preserves each symbol's base rate, and a model
   trained on such labels still selects better-than-base trades. That means a large part of
   the apparent skill was **symbol identification, not timing**. Removing per-symbol means
   drops ρ from 0.8182 to **0.5152** (p 0.040), and top-decile R to +0.0586 (**p 0.119**).

Reading: there is weak but real time-local ranking ability; it does not convert into
statistically distinguishable money.

### 2.4 Cross-sectional dispersion dwarfs everything else — and is mostly not usable

Per-symbol realised R at cell 2.0/3.0 spans **0.196 R** (EURCHF −0.1273 → USDJPY +0.0687).
That is ~4× the entire per-trade improvement we were trying to obtain from the model.

With a Šidák correction over 12 symbols (per-symbol bound at the 0.427th percentile of a
year-block bootstrap):

| | point | 5% bound | FWER bound | survives |
|---|---|---|---|---|
| USDJPY | +0.0687 | +0.0168 | −0.0094 | no |
| GBPJPY | +0.0609 | −0.0263 | −0.0632 | no |
| EURCHF | −0.1273 | −0.1683 | **−0.2032** | **yes (negative)** |
| EURGBP | −0.1217 | −0.1592 | **−0.1795** | **yes (negative)** |

So: *which symbols to exclude* is established; *which to include* is not. Excluding
EURCHF and EURGBP moves the pool from −0.0163 R to +0.0039 R at cell 2.0/3.0 — hence the
10-symbol pool used above. (We record that this exclusion is itself selection on the
outcome, made with eyes open.)

We then asked whether a **label-free** property predicts per-symbol R, so that a rule could
be written on the property rather than on symbol names. Candidate: "trendiness" measured
from price only (efficiency ratio, ADX). Spearman across symbols: **+0.545** and +0.434.
Required for significance: **0.643** — because 12 pairs built from 9 underlyings are not 12
independent observations. The participation ratio of the return panel is **7.54**.
Directionally supportive, not established.

We also enumerated every candidate symbol the broker offers (418 instruments) under
mechanical, label-free filters (FX spot only, must contain USD or EUR, tick depth to 2016,
bar-coverage sanity, volatility floor). 36 survived. **Every one has a wider
spread-per-daily-move than every symbol we already hold** — 1.4× to 4.7×. Adding four of
them would move pool `cost_R` from 0.0271 to ~0.0441 and cut the trade budget from 167 to
63 per year.

### 2.5 Effective sample size

Four independent estimators, answer taken as the minimum (deliberately conservative):

| | |
|---|---|
| overlap-uniqueness | 11,355 |
| autocorrelation (τ = 2.49) | **10,168** |
| cross-sectional (participation ratio 7.54 of 12) | 15,903 |
| non-overlapping blocks × breadth | 15,903 |
| **N_eff** | **10,168** (from 25,314 raw setups) |

---

## 3. The structure we think we have hit

Two identities we have been using:

```
economic:      n · cost_R  ≤  κ · SR* · √n      →      n_max = (κ·SR* / cost_R)²
detectability: δ_MER = SR* / (dev_dp · √n_max)  ,      N_req ∝ 1 / δ²
```

with `SR*` = 0.7 (target Sharpe), `κ` = 0.5 (share of target return we tolerate losing to
cost), `dev_dp = 1 + tp/sl` (sensitivity of EV to a change in win probability).

The consequence, at our three examined cells:

| cell | `cost_R` | required edge (p_tp) | `N_req` |
|---|---|---|---|
| 2.0/3.0 | 0.0271 | 0.0202 | 4,175 |
| 4.0/2.0 | 0.0117 | 0.0151 | 8,063 |
| **3.0/6.0** | 0.0167 | **0.0043** | **15,831** |

`N_eff` = 10,168.

**Cheaper cost lets you trade more, which means a smaller per-trade edge suffices, which
means a larger sample is needed to demonstrate that edge.** The two levers oppose each
other. And the way out of the sample constraint — more instruments — raises cost (§2.4).
The two constraints meet **below** the data we have.

A separate structural point from the same identity: we currently generate **3,068 setups
per year** against `n_max` = **441**. We are 7× over the cost budget. A filter that keeps
roughly the best 14% is therefore **structurally required**, independent of any claim about
machine learning.

### 3.1 Sensitivity — which lever actually matters

At cell 3.0/6.0, `EV net` = +0.0205 with SE ≈ 0.0127, so **t ≈ 1.62**.

| Change | resulting t |
|---|---|
| commission 0.7 → 0.35 pips per round turn | 2.14 |
| commission → 0 (not achievable) | 2.66 |
| **entry-rule effect × 2** | **4.34** |
| sample × 3.5 | 3.03 (blocked, §2.4) |

Only effect size fixes both problems at once: it raises EV **and** shrinks `N_req`.

### 3.2 One embarrassing item

The commission figure of **0.7 pips round-turn has been an assumed parameter in every
calculation since the labelling phase, and has never been checked against the broker's
actual schedule.** Dukascopy is a commission broker; a plausible real figure is ~0.35 pips
round-turn equivalent. If so, every cost number above is 2× pessimistic. We are checking.
We mention it because it is exactly the kind of unexamined constant that an outside reader
notices immediately.

---

## 4. What we have *not* tried

* **The entry rule.** SETUP-v1 was written as a deliberately naive benchmark and has never
  been revised. Three research phases optimised the filter, the universe, and the exit —
  all of them downstream of it.
* **Position sizing / anything other than 1R per trade.** Everything above assumes fixed
  risk per trade and no compounding, no vol targeting, no Kelly.
* **Horizons other than 24 H1 bars**, and any exit that is not a static double barrier
  (no trailing stops, no time-varying targets, no partial exits).
* **Any instrument class other than spot FX + gold**, and any holding period longer than
  one day.
* **Gradient boosting or anything non-linear** — the model above is a regularised logistic.
  (This was a deliberate ordering, not an oversight: we wanted the linear baseline first.)

---

## 5. The step we are proposing

**SETUP-v2: gate the momentum impulse on trend regime.** Hypothesis: a breakout in a
trending market continues; the same breakout in a mean-reverting market does not. So add a
regime condition (efficiency ratio / ADX, both already implemented and label-free) to the
existing impulse trigger.

Two properties we like:

1. It targets **effect size**, the only lever in §3.1 that resolves both constraints.
2. The gate's threshold would be set to bring the trade count down to the cost-implied
   `n_max` (≈441/yr from ≈3,068/yr) — a **label-free** criterion derived from the cost
   identity, rather than an arbitrary rate target.

It requires no new data; labels rebuild on existing ticks in ~45 minutes.

**We would like you to attack this proposal specifically**, including the possibility that
it is a way of appearing to make progress while remaining in the same saturated space.

---

## 6. Our doctrine — please treat all of this as challengeable

These are self-imposed. Several were adopted from the literature on backtest overfitting.
We now suspect at least some of them have made the project unable to reach a conclusion.

| # | Commitment | How it might be wrong |
|---|---|---|
| 1 | **Trial budget of 7.5 configurations** for the whole project, from MinBTL: `N ≤ exp(SR*²·years/2)` with SR* 0.7, 8.25 years. Non-renewable. Two spent. | Assumes independent trials and a particular selection structure. Arguably it prices exploration as if it were confirmation, and 7.5 total may make iterative research impossible. |
| 2 | **Everything pre-registered**: barrier cell, feature list, thresholds, decision rules — written and signed before each run. | We have now twice found our own pre-registration under-specified, and had to resolve the ambiguity mid-flight. A conventional train / validate / holdout split with free exploration on train might be both safer and far more productive. |
| 3 | **The cost identity** with κ = 0.5 and SR* = 0.7 as hard inputs. | SR* 0.7 is an aspiration, not a constraint; κ = 0.5 is arbitrary. The identity assumes fixed 1R sizing, no compounding, and cost linear in trade count. |
| 4 | **N_eff as the minimum of four estimators.** | Taking the min of four conservative estimators may be extremely conservative. If the true effective N is 15,000+, several "inconclusive" verdicts above flip. |
| 5 | **δ_MER framing**: power the study for the *smallest economically tradable* edge. | This is what generates the §3 trap. Powering for the *measured* effect instead would give very different sample requirements. |
| 6 | **Pooled training across instruments**, justified by scale-free features. | §2.4 shows the *economics* do not pool even though the features do. Per-symbol or per-cluster modelling was never attempted. |
| 7 | **Meta-labelling architecture** — entry rule fixes side, model only decides take/skip. | Joint learning of side and size, or direct regression on realised R, are both excluded by construction. |
| 8 | **Static double barrier, 24-bar horizon, ATR units.** | Fixed horizon is arbitrary. Trailing or adaptive exits change the entire EV surface and were never in scope. |
| 9 | **The holdout is untouchable until a candidate passes everything else.** | It has now sat unused through four phases. There is a real argument that we should have spent it earlier on a cheap, decisive question. |
| 10 | **Single broker, single data source.** | All cost and all microstructure conclusions inherit that one feed. |

---

## 7. What we believe is solid, so you can aim at the right things

We are fairly confident about these, and would want strong reasons to doubt them:

* The tick-path labelling is correct: spread is inside the path, gaps are honest, timeout
  is a real third class, and a 130,634-cell M1-vs-tick cross-check disagrees on 0.01%.
* The CV is genuinely purged; the placebo run on iid-shuffled labels produced no spurious
  signal.
* The entry rule beats its control on realised R after matching (**+0.0348 R**, CI
  [+0.0051, +0.0612]).
* Every candidate instrument available to us is more expensive to trade than what we hold.
* The interior maximum in stop width at 3.0 ATR is a structural feature, not noise (6 of 7
  target levels agree).

---

## 8. Questions

Ordered by how much the answer would change what we do next.

**Q1.** Is the §3 trap real, or is it an artefact of doctrine items 3–5? Specifically: is
"power the study for the minimum economically viable edge" the right target, or should we
power for the effect we have actually measured (+0.0348 R matched)?

**Q2.** Given a demonstrated entry effect of +0.0348 R over control but an absolute level of
roughly zero, is the correct diagnosis "the entry rule is close and needs strengthening" or
"the level is set by cost and the entry rule is irrelevant at this cost structure"?

**Q3.** We are 7× over the cost-implied trade budget (3,068/yr vs 441/yr). Should the
reduction come from (a) a stricter entry rule, (b) a filter model, (c) a wider stop, or
(d) is the budget itself the wrong constraint?

**Q4.** Our discrimination threshold (Spearman ≥ 0.7 on deciles) turned out to sit inside
the noise distribution. Beyond "simulate the null first" — what would you use as the
primary success statistic for a take/skip filter at N_eff ≈ 10⁴, and what threshold?

**Q5.** Cross-sectional dispersion is 0.196 R while the target improvement is ~0.05 R, but
only the *negative* tail survives multiplicity correction. How would you exploit dispersion
of that shape without it degenerating into instrument cherry-picking?

**Q6.** Is a trial budget of 7.5 for an entire project a defensible way to run research, or
should the budget apply only to confirmatory tests, with exploration governed by a
holdout instead?

**Q7.** What would you do about the holdout? It is two years of untouched tick data across
12 instruments. Spend it now on a cheap decisive question, or keep protecting it?

**Q8.** If you think this direction should be abandoned: what specifically would you do with
this asset base — audited tick data, a clean labelling and CV pipeline, an RCE — that is
*not* "H1 breakout on FX majors"?

---

## 9. Forced choice

Please pick one and say why. Do not rank all of them; we want the one you would actually
do, with your reasoning.

| | Option |
|---|---|
| **A** | **Strengthen the entry rule** (SETUP-v2, regime-gated impulse). Targets effect size; no new data. |
| **B** | **Attack cost first**: verify and renegotiate commission, model execution properly, and re-derive the whole surface before any further modelling. |
| **C** | **Change the research protocol**, not the strategy: abandon or loosen the trial budget and the δ_MER framing, adopt train/validate/holdout, and re-run what we have already built under the looser regime. |
| **D** | **Change the problem**: different horizon, different instrument class, different edge (carry, cross-sectional momentum, execution) — keep the infrastructure, discard the hypothesis. |
| **E** | **Stop.** The result is negative and adequately established; write it up. |

---

## 10. What we will do with your answer

We are collecting independent answers from several reviewers **without showing them each
other's**, then reconciling. Where reviewers disagree, we will treat the disagreement
itself as information about which parts of our design are actually load-bearing.

A single sentence telling us that one of the ten doctrine items in §6 is wrong would be
worth more to us than agreement with everything else in this document.

Reproducible evidence for every number above exists as committed JSON reports; we can
supply any of it on request.
