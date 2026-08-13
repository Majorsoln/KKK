# ELITEFX — External Technical Review Brief

**Prepared for:** an external practitioner who trains production ML systems on financial
market data (FX in particular).
**Prepared:** 2026-08-13
**Status of this document:** request for adversarial review. Not a proposal to approve.

---

## 0. What we are asking you for

We want you to **attack this design**, not validate it.

Specifically, we are **not** looking for encouragement, a list of things we did well, or a
diplomatic ordering of options. We have a working measurement pipeline and a large,
audited dataset. What we do not have is confidence that the *research question we have
posed to ourselves is the right one*.

If your honest view is "this class of strategy cannot work at retail cost structure and
you should restructure around a different edge," that is the single most valuable answer
you can give us, and it will not offend anyone. We would rather discard eight months of
direction than spend two years confirming it.

Where you disagree with a decision below, please say so plainly and say what you would do
instead. Concrete beats polite.

The questions we most want answered are in **§9**. Everything before that is context so
that your answers can be specific.

---

## 1. The system and the goal

**Goal:** an automated FX trading system that decides *when to open a position, in which
direction, with what stop and target*, and does so with enough accuracy to be net
profitable after realistic costs.

The system has two halves, deliberately separated:

| Component | Responsibility | Status |
|---|---|---|
| **RCE** (Risk & Cost Engine) | position sizing, cost model, slippage caps, risk budget, hard gates | **Built, specified, frozen.** Deterministic, spec-driven, 39 tests incl. golden tests from the spec's own worked examples. Not in question. |
| **KAIROS-1** | the ML side: which trades to take, in which direction, with which barriers | **This is the problem.** |

The principal (a solo operator; referred to below as PD) states the problem as: *"the risk
engine is fine — the problem is which trades to feed it."* This review is about
KAIROS-1 only.

**Operating constraints that are real and not negotiable:**

- Retail execution via MT5 at a Dukascopy-type broker. No colocation, no L2 order book,
  no sub-second latency guarantees. Commission ≈ **$7 per lot round-turn** (~0.7 pips on a
  USD-quote major).
- Decision timeframe is **H1**. This was chosen up front, not derived.
- One person makes every substantive decision, assisted by an AI implementer. Human review
  time is a genuine bottleneck.

---

## 2. Governance model (relevant because it constrains what we can change)

Every substantive parameter and rule is **signed** by the PD into an append-only ledger
before it can be used, binding: who, when, what, why, the config fingerprint, the code
revision, and the SHA-256 of the evidence file. A CI gate (`G14`) verifies the chain.

There are currently **18 signatures**. Notably:

- The decision-point rule (`SETUP-v1`) was **pre-registered and signed before a single
  label was computed**. This was enforced in code: the label builder refuses to run
  without the signature.
- The **holdout (last 20% chronologically, 2024-04-01 onward) has never been opened** and
  opens exactly once, at the end.

We name three leakage classes explicitly and guard them separately:
1. **Temporal** — guarded by an automated sentinel and as-of rules across 7 timeframes.
2. **Stacking** — any model output feeding another model must be out-of-fold.
3. **Selection** — guarded only by pre-registration discipline. We have no technical
   detector for it and we know that is a weakness.

**Why this matters to you:** we are not free to tune thresholds after seeing results. If
your advice implies changing a pre-registered rule, that is *allowed* — it just becomes a
new registered rule with an honest record that the old one was superseded. We are not
asking you to work around the governance; we are telling you it exists so your advice can
account for it.

---

## 3. Data foundation (audited, signed)

| | |
|---|---|
| Source | Dukascopy tick history (aggregator) + a live broker-feed recorder running in parallel |
| Symbols | 12 (9 FX majors/crosses + EURCHF, GBPJPY, XAUUSD) |
| Ticks | ~3.4 billion |
| Range | 2016-01-04 → 2026-04-30 |
| Layers | L0 raw immutable + SHA-256 → L1 quality → L2 bars (7 TFs) → L3 features → L4 labels → L5 datasets |

**Quality audit (R0), completed and signed:** 33,440 of 34,781 symbol-days usable
(**96.1%**). The largest single exclusion was a PD decision to drop all of 2023 for the
three symbols whose vendor file format changed mid-history (a *source* artifact, not a
market event) — 912 days.

The trading-session calendar is **derived from the data**, not assumed. Cross-checking it
against an assumed calendar produced zero Saturdays with ticks and 16 "unexpected" thin
days, all of which are 25 December or 1 January.

Two vendor schema variants exist (µs timestamps / daily files, and ms timestamps / monthly
files cut at 05:00 UTC). Both normalise to one schema; the audit verified this.

---

## 4. Decision points and labels

### 4.1 Decision points — `SETUP-v1`

Three mechanical, point-in-time gates on H1 bars, all evaluated at bar **close**:

1. **Cost gate:** `spread_p50 / rolling_median(spread_p50, 528 bars) ≤ 1.5`
2. **Volatility band:** ATR percentile rank within `[0.20, 0.95]` (backward-looking window)
3. **Momentum trigger:** `|close − close[t−4]| ≥ 2.5 × ATR14`; the **sign of the impulse
   sets the trade direction**

Tuned **on rate only** (target ~5%), before any label existed. The multiplier sweep was:

| `min_atr_mult` | 1.0 | 1.5 | 2.0 | **2.5** | 3.0 |
|---|---|---|---|---|---|
| setup rate | 26.33% | 15.21% | 8.42% | **4.46%** | 2.32% |

At 2.5, all 12 symbols land between 3.9% and 4.9% — i.e. the criterion is scale-free
across a very quiet pair (EURCHF) and a very volatile one (XAUUSD).

A **control sample** of 5% of non-setup bars is labelled identically and never trained on.
Its only purpose is to answer "does the filter select *better* trades, or merely *fewer*?"

**Result: setups 25,374 · controls 27,089 · holdout withheld 7,366.**

### 4.2 Labels — 5×5 barrier grid on the tick path

For every decision point, all 25 cells of:

```
SL ∈ {0.50, 0.75, 1.00, 1.50, 2.00} × ATR14
TP ∈ {0.50, 1.00, 1.50, 2.00, 3.00} × ATR14
horizon = 24 H1 bars (bars, not wall-clock — so it spans weekends correctly)
```

Design decisions worth your scrutiny:

- **Resolved on the tick path**, not OHLC. A bar tells you high and low were both touched
  but not which came first.
- **Trade-price convention:** a BUY closes on **bid**, so both its SL and TP are measured
  on bid; a SELL on ask. Spread therefore enters the label path exactly once.
- **Gap-honest:** a stop is a *touch* at the first price after the gap, not a close.
- **Timeout is a third class**, with its terminal return recorded, feeding a three-class
  EV: `EV = p_tp·TP − p_sl·SL + p_timeout·E[R|timeout]`.
- **The grid is a model INPUT, not derived from another head.** A separate quantile head
  proposes SL/TP; the barrier head is trained on the fixed grid. This is deliberate
  anti-circularity: the model that sets the boundaries must not also judge them.
- The quantile head's target is measured on **mid** price, not trade price, on the
  argument that spread already enters the barrier path and the cost engine, and counting
  it a third time would be double-counting. We measured the size of this choice: it is
  **0.02–0.10 ATR** depending on the symbol (see §5.5).

**Build result: 52,321 decision points → 1,308,025 labelled cells.** Zero points lacked
tick coverage.

---

## 5. What we measured (R1) — the important section

All figures below are **TRAIN+VAL only**. The holdout has never been touched.

### 5.1 Barrier outcomes are close to geometric

Under a driftless random walk, `p_tp / (p_tp + p_sl) ≈ sl / (sl + tp)`. Excluding timeouts,
we observe:

| sl | tp | n | timeout | p_tp | geometric | diff |
|---|---|---|---|---|---|---|
| 0.50 | 0.50 | 25,314 | 0.0% | 0.438 | 0.500 | −0.062 |
| 0.75 | 1.00 | 25,314 | 0.0% | 0.396 | 0.429 | −0.033 |
| 1.00 | 1.50 | 25,314 | 0.5% | 0.379 | 0.400 | −0.021 |
| 1.50 | 1.50 | 25,314 | 2.3% | 0.495 | 0.500 | −0.005 |
| 2.00 | 1.00 | 25,314 | 2.2% | 0.666 | 0.667 | −0.001 |
| 2.00 | 2.00 | 25,314 | 10.7% | 0.505 | 0.500 | **+0.005** |

23 of 25 cells sit below the geometric expectation, and **the deviation shrinks
monotonically as the stop widens** — the signature of a fixed price-distance cost (spread),
not of drift. Timeout share overall is **2.79%**.

### 5.2 Stability across years

| year | p_tp | timeout | E[R] |
|---|---|---|---|
| 2016 | 0.428 | 3.7% | −0.022 |
| 2018 | 0.423 | 2.9% | −0.041 |
| 2020 | 0.425 | 2.6% | −0.029 |
| 2022 | 0.419 | 3.0% | −0.046 |
| 2023 | 0.409 | 3.4% | −0.068 |
| 2024¹ | 0.379 | 4.1% | −0.154 |

¹ partial year (Jan–Mar only), 19,125 cells vs ~80,000 for a full year.

2016–2023 spans 0.409–0.428. We do not read 2024 as regime change on three months.

### 5.3 Does the entry filter add anything?

| | setup | control | difference |
|---|---|---|---|
| cells | 632,850 | 675,175 | |
| p_tp | 0.4173 | 0.3923 | **+0.0251** |
| timeout | 3.2% | 2.4% | |
| E[R] gross | −0.0505 R | −0.1142 R | **+0.0638 R** |
| ATR median | 16.1 pips | 14.3 pips | +1.8 |

The filter selects genuinely better trades, not merely fewer. Two caveats we hold
ourselves to: the naive z-statistic (+28.8) is inflated because the 25 cells of one
decision point are not independent and points overlap in time; and the ATR difference
means **part of the apparent edge may be volatility selection rather than prediction** —
the entry rule mechanically selects high-ATR bars.

### 5.4 The economics, per cell

Cost in R units is `commission_pips / sl_pips`, so a wider stop is proportionally cheaper.
Using 0.7 pips commission and the observed 16.1-pip median ATR:

| sl / tp | p_tp now | cost (R) | EV net | p_tp needed for breakeven | **gap** |
|---|---|---|---|---|---|
| 2.0 / 2.0 | 0.505 | 0.022 | −0.013 | 0.512 | **+0.007** |
| 2.0 / 1.5 | 0.575 | 0.022 | −0.016 | 0.585 | +0.010 |
| 1.5 / 2.0 | 0.425 | 0.029 | −0.037 | 0.442 | +0.017 |
| 1.0 / 1.5 | 0.379 | 0.044 | −0.096 | 0.417 | +0.038 |
| 0.5 / 0.5 | 0.438 | 0.087 | −0.211 | 0.543 | **+0.105** |

**The required lift varies 15× across the same grid.** For reference, the hand-built entry
filter itself delivered +0.0251 of p_tp.

We are aware that reading this table and then choosing the wide-stop corner would itself
be selection on the label. The grid remains a model input; we treat this table as a
measurement of *distance*, not as a trade selection.

### 5.5 Two secondary measurements

**Execution realism (L-C).** Of 757,424 stop touches, the price had already travelled past
the barrier by more than the risk engine's assumed 0.3-pip stop-slippage cap in **24%** of
cases (median overshoot 0.12 pips, p90 1.06, p99 14.59, max 2,503.7). We have not changed
the risk engine — this is recorded as an input for the integration phase — but a backtest
assuming the cap always holds is assuming something the tick history contradicts a quarter
of the time.

**Bars vs ticks.** Re-resolving the same grid using M1 high/low instead of ticks disagreed
with the tick-exact answer in **9 of 66,650 cells (0.01%)**. The theoretical argument for
tick resolution is correct, but at these barrier widths (minimum 0.5 ATR) its practical
effect is near zero. It would matter for tighter barriers.

**Mid vs trade price for the quantile target.** Measured as
`direction × (mid_target − trade_target)`, the difference is **0.021 ATR (EURUSD) to
0.105 ATR (XAUUSD, EURCHF)**. It ranks by *spread ÷ ATR*, not by spread — EURCHF has a
1.0-pip spread but only a 9.8-pip ATR.

---

## 6. Validation protocol

- **Purged K-fold**, 5 contiguous time blocks, symbols pooled into the same time folds.
- **Embargo** of 36 H1 bars (= horizon × 1.5) on both sides of each validation block.
- **Walk-forward anchored** as a second confirmation.
- **Holdout** = final 20% chronologically (2024-04-01 →), opened exactly once.
- **Calibration is a hard requirement**: any probability entering a decision must pass a
  reliability check. An uncalibrated probability feeding an EV gate makes the gate
  decorative.
- **Fill-aware**: trades that could not have filled within the cap do not count as trades.
- Feature screening is planned inside purged folds with permutation tests and
  Benjamini–Hochberg FDR at q = 0.10.

**What we do not currently do**, and know we do not:

- No **concurrency / sample-uniqueness weighting** for overlapping labels.
- No **sequential bootstrap**.
- No **meta-labelling** formulation (though `SETUP-v1` + ML is one step away from it).
- No **deflated Sharpe / PBO / CSCV**; our multiple-testing surface across research phases
  is not formally counted.
- Time bars only — no dollar, volume, or imbalance bars.
- No fractional differentiation; we enforce scale-free features by construction instead
  (log returns, ratios, ATR units, percentile ranks) with rolling normalisation.

---

## 7. The planned model architecture

Three layers, ten models:

| Layer | Question | Models |
|---|---|---|
| Understanding | what regime is the market in? | HMM, Transformer, LSTM, CNN |
| Decision | how good is this setup, which strategy? | XGBoost, PPO |
| Validation | is this trade +EV and executable? | Quantile NN, Barrier (3-class), EV, Fill |

Formal pipeline: quantile head → SL floor rule → barrier head → EV → P(fill) →
`EV_final = P(fill) × EV_signal` → thresholds → hand off to the risk engine.

Every model must beat a gradient-boosting baseline on purged CV to enter; failing that it
is recorded as a "lesson" and excluded. For the deep models, the intended route to
viability is **self-supervised pretraining** on unlabelled bars (next-bar direction,
masked-bar reconstruction, contrastive regime), walk-forward per fold, then fine-tuning
small heads on the trade labels. PPO must beat a contextual bandit baseline.

**Our own concern, stated plainly:** this is ten models against ~25,000 decision points.
The acceptance gate is honest, but the *expectation* embedded in the architecture may not
be.

---

## 8. The pivot we are considering

We recently concluded that our sample size is small **because of our own choices**, and
that we had been optimising within that constraint instead of attacking it:

| our choice | consequence |
|---|---|
| filter to 4.46% of bars | discarded 95.5% of candidate decision points |
| 12 symbols, all FX, from ~6 currencies | perhaps ~5 independent factors, not 12 |
| history starts 2016 | vendor has majors back to 2003 |
| single horizon | one supervision signal per point |

Proposed changes:

1. **Extend history to 2003.** Independent 24-bar blocks: ~2,060 → ~4,750 (×2.3). More
   importantly, the current window contains **no tail event at all** — no 2008, no January
   2015 CHF, no 2011. A system that has never seen a market break is about to be asked to
   manage risk through one.
2. **12 → ~28 instruments, chosen for independence** (metals, indices, energy, distant
   crosses) rather than more FX pairs. Independent factors ~5 → ~12.
3. **Stop hand-filtering; let the model learn the filter.** Label every valid H1 bar
   (~588,000 points). `SETUP-v1` becomes a feature and a baseline to beat, not a gate.
   This also removes the volatility-selection confound from feature screening.
4. **Two-level barrier resolution** to make (3) affordable: locate the touching bar using
   bar-level running extremes, then descend to ticks only within that one bar — justified
   by our own 0.01% bars-vs-ticks measurement. Roughly 100× cheaper per point, and
   validatable against the 1,308,025 tick-exact cells we already have.
5. **Reframe the objective from accuracy to ranking under capacity.** Positions overlap
   and the risk budget binds, so what matters is the EV of the top-k selected trades, not
   the mean lift over all candidates. A top decile at p_tp 0.55 on the 2.0/2.0 cell is
   +0.078 R per trade at ~300 trades/year.
6. **Add a cross-sectional target** — "which of the N instruments outperforms the basket"
   rather than "will this pair rise" — to cancel the dominant common factor. Timestamps
   are already aligned and the terminal-return label already exists.

Combined effect on effective N: we estimate ~5×, which would lower the detectable IC
threshold by ~2.3×.

---

## 9. Questions

**You are one of three independent reviewers.** All three receive this identical brief and
none of you sees another's answer before writing. That is deliberate: where three
practitioners independently converge, we will treat it as strong evidence; where you
diverge, that is where the real uncertainty lives and we will dig there. Please do not
hedge toward a consensus you cannot see.

### 9.0 If you answer nothing else, answer these three

These are deliberately forced-choice. "It depends" is a valid answer only if you then pick
one anyway and state the condition.

**A. One change.** If you could change exactly **one** thing about this programme — the
target, the horizon, the instrument set, the architecture, the validation, anything — what
would it be, and what do you expect it to be worth? Please also state: *what evidence would
change your mind about this?*

**B. First thirty days.** Concretely, what would you do in the next month if this were your
project? A sequence of specific work items, not principles. Assume one operator plus an AI
implementer, and that the data and measurement pipeline described above already exist.

**C. What to stop.** What in this programme should be **abandoned outright** — not
deferred, not deprioritised, but stopped? Practitioners rarely volunteer this and it is
usually the most valuable thing they know.

Please also rate your overall confidence in A (low / medium / high) and say what you would
need to see to raise it.

### 9.1 Detailed questions

Numbered so you can answer selectively. Please disagree freely.

**On the premise**

1. Is H1 directional barrier prediction on FX majors, at ~0.7 pip commission plus
   0.3–1.6 pip spreads, a viable edge source *at all* for an operator without
   colocation or order-book data? If your answer is no, what would you do with this data
   instead — and be specific about the horizon and the target.
2. Our barrier outcomes sit within 0.5–6 percentage points of geometric. Is that
   consistent with your experience of FX at this horizon, and does it tell us the
   conditional signal we are hunting is plausible or implausible?

**On labelling and target design**

3. Should this be a **meta-labelling** problem? `SETUP-v1` sets the side; a secondary model
   decides take/skip and size. We currently train a p_tp surface across the grid instead.
   Which formulation would you choose here, and why?
4. How badly does the absence of **sample-uniqueness weighting** bite at a 24-bar horizon
   with 4.46% sampling? Does dense labelling (proposal 3) make it critical rather than
   merely advisable?
5. Time bars vs **dollar / volume / imbalance bars**: given we hold the full tick history
   and can rebuild, is this worth the rebuild cost at H1-equivalent frequency?
6. For screening, is a continuous signed target (terminal move in ATR units) clearly
   preferable to the binary cell outcome, or does that trade power for relevance in a way
   that misleads?

**On sample size**

7. Of the four levers in §8 — history depth, instrument breadth, dense sampling,
   multi-horizon — which actually buy **effective** N and which are illusory? Our
   suspicion is that dense sampling buys much less than its 23× raw-count increase
   suggests, because consecutive points share 23/24 of their path.
8. Extending to 2003 imports pre-2010 microstructure (much wider spreads, lower
   algorithmic participation). Does the tail-event coverage justify the regime
   heterogeneity, or should the old period be used only for pretraining / robustness
   testing rather than for the trade labels?

**On architecture**

9. Ten models on ~25k labels. Which would you cut immediately, and what would you keep?
   Is the self-supervised pretraining route a sound way to buy deep-model capacity at this
   label budget, or is it a well-dressed way to overfit?
10. Is the cross-sectional reframing (§8.6) worth restructuring around, or a distraction
    from making the directional problem work?

**On validating that any of it is real**

11. We have purged CV, an embargo, and a one-shot holdout, but we do **not** count our
    multiple-testing surface across research phases and we have no deflated Sharpe / PBO.
    What is the minimum additional discipline you would insist on before believing a
    positive result?
12. What is the single most likely way this project produces a convincing but false
    positive? We would rather you name it now than discover it in production.

---

## 10. What we will do with your answer

We will discuss it, decide, and record the decision — including where we disagreed with
you and why — in the project's signed ledger. If your advice changes a pre-registered
rule, the old rule stays in the record as superseded, not deleted.

If you tell us the premise is wrong, we will treat that as the most useful possible
outcome, not as a setback.
