# Follow-up to reviewer 2 — the foundation of your central argument has moved

**Date:** 2026-08-18 · **Re:** your adversarial review of External Review Brief #2 (2026-08-17)
**Status:** correction notice + six questions. Your methodological findings are not in dispute.

---

## 0. Why you are hearing from us again

Your review made us re-derive `σ_R` from our own reported SE and `N_eff`, because we had
never assembled our numbers into a Sharpe and you had. Doing that derivation is what
exposed a defect in our labeller.

**The defect was ours, it inflated every EV number we gave you, and your reconstruction
was faithful to numbers that were wrong.**

We are telling you before you see anything else, because the single sentence your forced
choice rests on — *"You already have a 1.0 gross Sharpe and you are paying 45% of it in
commission. That is not a 'no edge' result. That is an execution-cost result."* — is the
part most affected.

---

## 1. The defect

Our triple-barrier labeller resolves take-profit and stop-loss on the **trade path** — a
long enters at the ask and exits at the bid, so the round-trip spread is inside the
realised outcome. That was correct.

But the **timeout** class computed its return **mid-to-mid**. A trade that reached neither
barrier within the 24-bar horizon was credited with the mid-price move and never charged
the spread it would actually have paid to enter and exit.

The three outcome classes were therefore not measured on the same basis. The bias is
one-directional (it can only flatter), and it scales with the timeout share — which at the
wide cells we were championing exceeds 60%.

Fixed at source (`LABEL_SCHEMA_VERSION` 2 → 3; the timeout return now comes from a
trade-path terminal price). All 25,314 decision points were relabelled across all 49 cells
and every number below is re-measured, not adjusted.

Before rebuilding we wrote an audit that predicted the effect analytically from the
existing labels. It predicted +0.0081 at the best cell and 6 surviving positive cells. The
rebuild returned exactly that. We mention this only because it means the correction is
understood, not merely observed.

---

## 2. Your reconstruction, rebuilt

Your model reproduced our figures exactly, so we have rebuilt it rather than replaced it.
Everything below uses **your** convention: gross = net + commission + overshoot.

| | you had | corrected |
|---|---|---|
| SE | 0.0127 | **0.0126** |
| `σ_R` (derived) | 1.28 | **1.275** |
| `cost_R` (commission 0.0133 + overshoot 0.0034) | 0.0167 | **0.0167** |
| net EV per trade | +0.0205 | **+0.0081** |
| gross EV per trade | +0.0372 | **+0.0248** |
| `t` over 8.25 y | 1.62 | **0.64** |

Your annual decomposition, same `n` = 3,068 and same annual σ = 111.9 R:

| annual, in R | you had | corrected |
|---|---|---|
| gross return | 114.1 | **76.1** |
| commission + overshoot | −51.2 | **−51.2** |
| net | 62.9 | **24.9** |
| **gross Sharpe** | **1.02** | **0.68** |
| **cost drag** | **−0.46** | **−0.46** |
| **net Sharpe** | **0.56** | **0.22** |
| cost as share of gross | 45% | **67%** |

Three things we want to be precise about, because they cut in different directions:

1. **Your dispersion estimate is untouched.** SE moved 0.0127 → 0.0126 and `σ_R` stays at
   1.275. Your derivation of `σ_R` from our own published figures was correct and remains
   correct.
2. **Your cost estimate is untouched.** The drag is −0.46 in both columns. The defect was
   in the return, not in the cost. Nothing you said about cost has been weakened by this.
3. **What fell is the gross.** 1.02 → 0.68, a 33% reduction. Commission is now **67%** of
   gross Sharpe rather than 45% — so in *ratio* terms your execution-cost thesis got
   stronger, while in *level* terms the thing being taxed got much smaller.

(If gross is defined as net + commission only, leaving overshoot inside the realised path
where we think it belongs, the corrected figures are gross 0.59, drag −0.36, net 0.22,
commission 62% of gross. We use your convention above so the comparison is like-for-like.)

**The corrected best cell** (`sl` 3.0 / `tp` 6.0, still the argmax of 49):

> EV net **+0.0081 R**, 90% CI **[−0.0138, +0.0278]**, `t` = **0.64**.
> Šidák lower bound over 49 cells: **−0.0332**.
> Positive cells: **6 of 49**, down from 13. The cell we had signed, `2.0/3.0`, is now
> **negative** (−0.0029).

**What survived the correction, in case it matters to you:**

* The interior maximum in stop width at `sl` 3.0 is still the peak in 5 of 5 rows. Your
  §6 qualification of it — that its *location* is a function of an unverified commission
  constant — we accept, and it is untouched by this fix.
* The setup-vs-control differential is **+0.0560 R**, versus +0.0556 R before the fix.
  The defect taxed setup and control identically, so the one result you called our best
  measured result is unaffected. Your Q2 statement that the entry rule carries us "the
  entire distance from hopeless to breakeven" still holds in relative terms. What has
  changed is where breakeven sits.

---

## 3. What your review did to itself, item by item

We separate this deliberately, because most of your review does not depend on our numbers
at all, and we do not want a correction notice read as a rebuttal.

**Unaffected — these are arguments, not measurements, and we have accepted all of them:**

* Net Sharpe is monotonically increasing in `n` while net per-trade EV > 0. There is no
  `n_max`. κ was an accounting preference wearing the costume of an economic constraint.
  This was our error and it was load-bearing.
* The 1/√f rule for any proposed filter. We have adopted it as the standing bar.
* `t = SR·√T`, and the consequence that MinBTL's denominator should be a participation
  ratio rather than a raw cell count.
* §3.1 marked temporal expansion as blocked by §2.4. It is not; §2.4 blocks *instrument*
  expansion only. That was a straightforward error on our side.
* Gating on a model's calibrated probability rather than on realised money was a design
  error. So was collapsing 10⁴ observations into 12 Spearman points.
* All four of your objections to SETUP-v2, in particular the second — that `N_eff` for a
  slow regime variable is a count of independent episodes, not of trades inside them. We
  have shelved SETUP-v2 rather than answer it, because we do not think we can.
* Your reading of the Dukascopy commission schedule, including that the MT5 add-on makes
  our 0.7 pips mildly optimistic rather than pessimistic. Verification against the live
  statement is our next action, not a research item.

**Affected — these rest on the inflated numbers:**

* *"You already have a 1.0 gross Sharpe."* We have 0.68.
* *"That is not a 'no edge' result. That is an execution-cost result."* At `t` = 0.64 we
  are no longer confident this distinction is available to us.
* *"Your point estimate is a 0.56 net Sharpe … a costed result at the edge of
  detectability."* 0.22 is not at the edge of detectability. It is **32% of** the
  detection floor of our own sample (2/√8.25 = 0.696). Reaching `t` = 2 at SR 0.22
  requires **T ≈ 80 years**.
* *"Under the current doctrine, no achievable improvement can register as a pass."* This
  was your strongest argument for C, and it now needs re-testing against a different
  starting point.

**Affected quantitatively — your worklist item 3, the temporal lever:**

You called extending the sample backwards the largest single lever, and you were right
that we had wrongly marked it blocked. But on corrected numbers it no longer reaches the
bar on its own:

| | `t` |
|---|---|
| now, T = 8.25 | 0.64 |
| extend to ~2007, T = 17.5 (your factor 2.1) | **0.93** |
| extend to ~2003, T = 23 | **1.07** |

Stacked with your top-tier commission scenario (0.15 pips round turn ⇒ `cost_R` 0.0167 →
0.0063, EV → 0.0186, SR → 0.51):

| | `t` |
|---|---|
| top tier alone, T = 8.25 | 1.47 |
| top tier **+** T = 17.5 | **2.14** |
| worst case instead (0.75 pips with MT5 add-on), T = 8.25 | 0.57 |

So a path to `t` ≈ 2 still exists inside your own framework, but it now requires **both**
levers, one of which is a capital-and-volume outcome rather than a research outcome — and
the volume that buys the top tier is volume this strategy would have to earn first.

---

## 4. A new measurement that bears on your Q8

You proposed a longer horizon on the grounds that cost drag on Sharpe scales as
1/√horizon, and called doctrine item 8 (the fixed 24-bar horizon) possibly our most
expensive commitment. We had also been telling ourselves a story that the barriers were
taxing the edge.

With the corrected accounting we measured the **pure time exit**: no barriers at all,
enter on the trigger, close at the 24-bar horizon, spread and commission charged.

> **−0.0062 ATR, SE 0.0353, `t` = −0.18.**

Indistinguishable from zero. The momentum trigger produces no measurable 24-hour drift.
Whatever small positive EV exists in the grid is produced **by the barrier geometry**, not
despite it — which also refutes the story we had been telling ourselves, and we have
retracted it internally.

This is the measurement we would most like you to react to, because the 1/√horizon
argument prices the *cost* of a longer horizon correctly but presumes there is drift to
capture at the longer horizon. At 24 hours there is none.

---

## 5. Six questions

1. **Does `t` = 0.64 change your forced choice?** You chose C — change the protocol, not
   the strategy — explicitly *because "the negative result is not established"*. Your
   supporting bullets were a 0.56 net Sharpe and a 1.02 gross. At 0.22 and 0.68, with the
   point estimate at less than a third of the sample's own detection floor, does the
   negative result become established, or is your C independent of the level?

2. **Does your §1(b) argument survive the correction, or change shape?** You showed our
   SR* target (0.7) equals our detection floor (0.696), and said this dissolves §3. On
   corrected numbers the binding fact is different: the *measured* value is 0.22, far
   below any floor we could set. Is the diagnosis now "the target was set at the floor",
   or "the sample cannot distinguish 0.22 from 0, and no target choice repairs that"?

3. **Does the stacking requirement change your ranking?** Neither temporal expansion
   (`t` → 0.93–1.07) nor the top commission tier (`t` → 1.47) reaches 2 alone. Together
   they do (2.14). Is a plan whose viability requires two independent levers, one of them
   circular in capital, still worth the protocol overhaul C implies?

4. **Does a zero 24-hour drift kill the longer-horizon direction, or is it orthogonal?**
   Your Q8 item 1 assumed drift exists and only cost stood in the way. Our measurement
   says the 24-hour drift after the trigger is zero. Would you still propose a ~10-day
   horizon, and if so, on what independent reason to believe drift appears at 10 days
   that is absent at 24 hours?

5. **You called the largest uncharged selection in the document the EURCHF/EURGBP
   exclusion** — it moved the pool from −0.0163 to +0.0039, and we then reported the whole
   grid on the survivors. We agree and we are going to re-measure the full 12-symbol pool
   at the corrected labels. Before we do: what number would you want to see, and what
   would you conclude if the full pool is negative at the best cell? We would rather
   pre-commit to your reading than choose it afterwards.

6. **What in your review would you now retract?** We are asking directly because you
   asked us for the same thing and we did it. Specifically: do you want to revise
   *"That is not a 'no edge' result. That is an execution-cost result."*

---

## 6. What we are doing regardless of your answer

These are not conditional on the review; they are your worklist items we accept outright.

1. Verify the actual commission tier from the live statement, including the MT5 add-on
   and the currency-conversion fee we had not modelled at all.
2. Replace "49" in the Šidák denominator with the participation ratio of the eigenspectrum
   of per-year cell EVs.
3. Re-measure the full 12-symbol pool at the corrected labels, so the outcome-selected
   10-symbol pool is charged rather than assumed.
4. Retire κ. The standing rule is net EV > 0 plus 1/√f for any filter.
5. Audit Dukascopy tick depth per symbol pre-2016, with era-specific cost constants.
6. Re-run the cross-section as one panel regression on label-free characteristics rather
   than 12 per-symbol tests.

The holdout (2024-04-01 → 2026-04-30) remains untouched. We independently computed its
SE at ≈0.025 before reading your Q7 and reached your conclusion — it cannot confirm an
effect of this size — so your redirection of it toward cost and microstructure stability
is accepted rather than debated.

---

*One last note, offered without a question attached. You said our placebo phase was the
best work in the brief because we published a result against our own interest. The defect
in §1 was found by taking your `σ_R` derivation seriously enough to reproduce it. Both of
those are the same mechanism, and it is the reason we asked for adversarial review rather
than validation.*
