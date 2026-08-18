# Reply to reviewer 2 — the full pool, and an error in your §2

**Date:** 2026-08-18 · **Re:** your response to the correction notice
**Status:** the Q5 measurement (sealed before your answer), one correction to your
arithmetic, one code audit answering your candidate (b), and the §2 measurement you asked
for.

---

## 0. The seal held

You wrote *"Stated before you run it, as you asked."* We had already run it — and sealed it
unsent, precisely so your pre-commitment would be uncontaminated. The measurement was
committed to our repository at `97c89fc` under the filename `ADDENDUM_EXPERT_2_SEALED.md`,
whose text begins *"Send only after reviewer 2 has answered question 5."* The ordering is
verifiable in git history rather than on our word.

So your pre-commitment stands as a genuine one, and we are answering it below.

---

## 1. Q5 — the full 12-symbol pool

| at `sl` 3.0 / `tp` 6.0 | 10-symbol (selected) | **12-symbol (full)** |
|---|---|---|
| `EV net` | +0.0081 | **−0.0109** |
| 90% CI | [−0.0138, +0.0278] | **[−0.0322, +0.0078]** |
| Šidák bound over 49 cells | −0.0332 | **−0.0507** |
| `t` | +0.64 | **−0.90** |
| `cost_R` | 0.0167 | 0.0186 |
| gross Sharpe (your convention) | 0.68 | **0.22** |
| cost drag | −0.46 | **−0.53** |
| **net Sharpe** | **+0.22** | **−0.31** |
| **cells with positive net EV** | 6 / 49 | **0 / 49** |

**No cell in the grid is positive on the unselected pool.** Best is `sl` 3.0 / `tp` 2.0 at
−0.0107 R. The selection was worth **+0.0190 R** — 2.3× the entire remaining point
estimate, larger than the labelling defect that preceded it (0.0124), and larger than the
setup-vs-control effect we called our best result (0.0056).

You said you would treat a negative full pool as dispositive for the hypothesis as
specified. We accept that reading, and we adopt your instruction on presentation: **the
full-pool number is the headline number**, and the 10-symbol figure appears from here on
only as a footnote quantifying what the selection was worth.

We also tested your own cost thesis to its limit rather than leaving it standing. At the
top Dukascopy tier you identified (0.15 pips round turn instead of 0.7):

> `commission_R` 0.0146 → 0.0031, `cost_R` 0.0186 → 0.0071
> ⇒ `EV net` **+0.0006 R**, Sharpe **0.02**, `t` **0.05**

At effectively zero commission the unselected pool still produces nothing. On unselected
data the "execution-cost result" reading is not available in any commission regime.

**Your items 2 and 3, and the `sl` optimum.** The per-symbol cost/gross decomposition — the
number you said you wanted most — and the setup-vs-control differential on the full 12 are
reported in §4 below; we built the tooling for both after reading your letter. On the
optimum: `sl` 3.0 best is −0.0107 and `sl` 4.0 best is −0.0111. That is a plateau, not a
peak, so your §6 qualification was right and understated. The monotone improvement along
`sl` (−0.2229 → −0.0107) is untouched, so the cost *mechanism* still shows clearly; only
its claimed interior maximum does not.

---

## 2. Your §2 optional-stopping gap is 0.030 ATR, not 0.070

Your identity is correct and it is the right test. Your arithmetic has one inconsistency,
and it doubles the anomaly.

You compare:

| your row | what it is net of |
|---|---|
| pure 24-bar time exit, **net** = −0.0062 ATR | spread **and commission** |
| best cell, **net + commission** = 0.0214 R = +0.064 ATR | spread only |

Our time-exit statistic is `terminal_atr − (spread_rt_pips + commission) ÷ atr_pips`
(`cli.py`, `cmd_exit_audit`) — commission is already deducted. Adding commission back to
the barrier side but not to the time-exit side compares a gross number against a net one.

Like-for-like, both fully net:

| | ATR |
|---|---|
| pure 24-bar time exit, net | **−0.0062** |
| best cell 3.0/6.0, net (+0.0081 R × 3.0) | **+0.0243** |
| **gap** | **0.0305** |

Both were measured on the same 10-symbol pool, so the comparison is otherwise clean.
(Adding commission to both sides gives +0.0338 vs +0.0642 — the same 0.030 gap, as it must.)

**We are not claiming this dissolves your point, and we want to be explicit about why.**
You called the gap ~2 SE against the time-exit SE of 0.0353. That comparison was never the
right one in either direction: the gap is a **paired** difference between two statistics
computed on largely the same trades, so its standard error is not the standard error of
either one and is very likely much smaller. Correcting the units halves the anomaly;
correcting the test probably makes what remains *more* significant, not less. Your identity
still demands an explanation, and we have not got one from arithmetic.

---

## 3. Your candidate (b) — we audited the overshoot term. It is not double-counted

You listed the overshoot term as a specific candidate for a second accounting asymmetry:
*"the overshoot term being subtracted as a cost when it is already inside the realised
path."* It was the most plausible item on your list. We checked the code rather than
reasoning about it.

In `src/data/costs.py`:

* `realized_r()` sets the stop outcome to `−(1 + overshoot_R)` — so overshoot **is** inside
  the realised path, exactly as you suspected it should be.
* `ev_r_net = mean(realized_r) − commission_R`. Overshoot is **not** subtracted again.
* `cost_r_total = commission_R + P(stop)·E[overshoot | stop]` is a *reporting* quantity used
  for `n_max` and for the Sharpe decomposition. It is never subtracted from `ev_r_net`.

So `EV net` charges overshoot once, via the path. Our `μ_gross` = `EV net` + commission +
overshoot is a legitimate gross-of-both-frictions quantity, which is why your reconstruction
reproduced our table.

That closes one of your three candidates. Your other two — tie-resolution granularity and
a spread-convention mismatch between the time-exit test and the barrier labeller — are not
closed, and the term structure below is how we intend to catch either.

---

## 4. §2 — the drift term structure

You said you would not defend any further recommendation before seeing this, so we built it
rather than argue about it. Two new commands, both descriptions rather than selections, so
neither consumes trial budget:

* **`drift-curve`** — mean gross and net return from the trigger, in ATR, at horizons
  {3, 6, 12, 24, 48, 120, 240} H1 bars, no barriers, setup and control separately,
  year-block bootstrap CI, round-trip cost charged **once** (so the 1/√h-to-1/h effect you
  described is visible rather than assumed).

  It carries a reconciliation you specifically motivated: at `h` = 24 the bar-derived gross
  must equal the tick-derived `terminal_atr` recorded by the labeller. Two independent paths
  to the same number, one from H1 closes and one from the tick engine. The command prints
  both and warns on a one-bar offset. That check exists because you were right about what
  makes numbers checkable — this is us building the property in deliberately.

* **`cost-audit --by-symbol`** — your item 2, splitting a cell per symbol into `cost_R`,
  gross (`EV net` + `cost_R`), `EV net`, and mean spread-per-ATR, with the rank correlation
  between spread-per-ATR and gross. It reports separately which symbols are negative on
  `EV net` and which are negative on **gross**, because that is the distinction your Q5
  turns on: a symbol negative through `cost_R` can be excluded by a label-free rule; a
  symbol negative through gross cannot.

### 4.1 Before the table — we made your error, in the other direction

In §4 of our previous letter we told you *"the momentum trigger produces no measurable
24-hour drift."* The number behind it was **−0.0062 ATR, `t` −0.18** — which is **net** of
spread and commission. **Drift is a gross quantity.** We took a net number and drew a gross
conclusion, on the same day we corrected you for comparing a net figure against a gross one.
Retracted.

### 4.2 Drift exists. It was hidden behind the net figure.

Full 12-symbol pool, mean move from the trigger, no barriers, ATR units:

| `h` (bars) | gross | net | 90% CI net | control net | setup − control |
|---|---|---|---|---|---|
| 3 | +0.0189 | −0.0905 | [−0.1033, −0.0782] | −0.1477 | +0.0572 |
| 6 | +0.0328 | −0.0766 | [−0.0982, −0.0553] | −0.1635 | +0.0869 |
| 12 | +0.0501 | −0.0594 | [−0.1022, −0.0186] | −0.1586 | +0.0992 |
| **24** | **+0.0593** | −0.0501 | [−0.1355, +0.0253] | −0.1493 | **+0.0992** |
| 48 | −0.0546 | −0.1640 | [−0.3164, −0.0303] | −0.0806 | −0.0835 |
| 120 | −0.0497 | −0.1591 | [−0.3309, +0.0005] | −0.1004 | −0.0587 |
| 240 | **−0.2651** | −0.3746 | [−0.5841, −0.1885] | −0.1696 | −0.2049 |

The 10-symbol pool — the one on which the time-exit test was run — has the same shape,
larger: +0.0316 → +0.0521 → +0.0756 → **+0.0952** → −0.0027 → −0.0167 → −0.2188.

| gross at `h` = 24 | 12-symbol | 10-symbol |
|---|---|---|
| estimate | +0.0593 ATR | +0.0952 ATR |
| `t` on `N_eff` | +1.84 | **+2.63** |
| two-sided `p` | 0.066 | **0.0085** |

**Your identity is satisfied, and the answer is your branch (a): real drift.** No second
accounting asymmetry is needed to explain the gap. The barriers were not manufacturing
return; they were capturing something that was there. Your prior on a second defect was
reasonable and it did not pay out.

The reconciliation check passed exactly: at `h` = 24 the H1-close path gives +0.0266 ATR
and the tick path gives +0.0266 ATR, difference 0.0000, while the one-bar-offset
alternative differs by 0.0150. The bar convention is established by data rather than
assumed.

### 4.3 But the drift is smaller than the cost, and that is the whole verdict

| | 12-symbol | 10-symbol |
|---|---|---|
| gross drift over 24 bars | +0.0593 ATR | +0.0952 ATR |
| round-trip cost | 0.1094 ATR | 0.1013 ATR |
| **cost ÷ gross** | **1.84×** | **1.06×** |

On the pool we did not choose, cost is **1.84× the entire edge that exists**. On the pool
we chose, it is 1.06× — we miss by 6% of the cost.

This is a sharper statement than "no edge", and it is the one we will publish:

> There is real momentum continuation of roughly **0.06–0.10 ATR over 24 hours**. The
> round-trip cost of taking it at retail is **0.10–0.11 ATR**. We lose by the width of the
> spread.

### 4.4 The cost split — and 60% of it is not commission

`drift-curve` charges spread explicitly, unlike the grid where spread hides inside the
path. Split at `h` = 24, full pool:

| | ATR | share |
|---|---|---|
| round-trip spread | **0.0656** | **60%** |
| commission (0.7 pips) | 0.0438 | 40% |
| total | 0.1094 | |

Checked independently: `commission_R` at `sl` 3.0 is 0.0146, and 0.0146 × 3.0 = 0.0438,
which equals 0.1094 − 0.0656 to the digit. Two unrelated paths, same number.

**This displaces your worklist item 1.** You put commission verification first because it
changes the shape of the EV surface. It does — but commission is 40% of the cost, and the
part we cannot buy down with capital is the larger part. At your top tier (0.15 pips):

| | new cost | gross | net |
|---|---|---|---|
| 12-symbol | 0.0750 | +0.0593 | **−0.0157 ATR** |
| 10-symbol | 0.0733 | +0.0952 | +0.0219 ATR |

**At near-zero commission the unselected pool is still negative.** The commission lever
cannot close the gap alone. We will still verify the tier, because a wrong constant is a
wrong constant, but it is no longer the item that decides anything.

### 4.5 Your Q8 horizon proposal is not merely dead — the sign flips

You called doctrine item 8 possibly our most expensive commitment and proposed ~10 days.
Ten days is `h` = 240:

* gross is still **rising** at `h` = 24 (0.0756 → 0.0952)
* it has collapsed by `h` = 48 (−0.0027)
* at `h` = 240 it is **−0.2188** (10-symbol) / **−0.2651** (12-symbol)
* setup-minus-control peaks at `h` = 24 (+0.0992 / +0.1123) and **turns negative** at 48

The peak lies somewhere in [24, 48). We fixed 24 before measuring anything and landed near
it. You had flagged this branch yourself — *"if drift is front-loaded, the correct move is a
shorter horizon... I would then be wrong in the opposite direction."* The drift is not
front-loaded (it builds monotonically to 24), but it fully reverses afterwards, and the
practical conclusion is the one you named: not longer.

One honesty note on our own table: at long horizons the windows overlap heavily (points
every ~8 bars, a 240-bar window), so the independent sample is far smaller than raw `n` and
the `t` values in the 48–240 rows are inflated. The direction is clear; the magnitudes are
not as certain as the column suggests.

### 4.6 Your Q5 item 2 — the exclusion was not a cost rule

You named the one way the exclusion stays honest: if the two symbols' negativity is
explained by `cost_R` rather than by gross.

| symbol | `cost_R` | **gross** | `EV net` | spread/ATR |
|---|---|---|---|---|
| USDJPY | 0.0176 | **+0.0913** | +0.0737 | 0.0252 |
| GBPJPY | 0.0145 | **+0.0705** | +0.0560 | 0.0648 |
| EURJPY | 0.0152 | **+0.0600** | +0.0447 | 0.0373 |
| GBPUSD | 0.0151 | +0.0394 | +0.0242 | 0.0447 |
| USDCAD | 0.0173 | +0.0168 | −0.0005 | 0.0688 |
| USDCHF | 0.0215 | +0.0097 | −0.0118 | 0.0842 |
| XAUUSD | 0.0040 | +0.0069 | +0.0029 | 0.1047 |
| AUDUSD | 0.0194 | −0.0121 | −0.0315 | 0.0803 |
| NZDUSD | 0.0227 | −0.0157 | −0.0384 | 0.0949 |
| EURUSD | 0.0177 | −0.0169 | −0.0346 | 0.0218 |
| **EURCHF** | 0.0342 | **−0.0817** | −0.1160 | 0.0993 |
| **EURGBP** | 0.0251 | **−0.0839** | −0.1090 | 0.0809 |

**Both are negative on gross, not on cost.** Their `cost_R` is above average but nowhere
near enough to account for −0.08. The exclusion cannot be rewritten as a label-free cost
rule. It was outcome selection, the escape route is closed, and we are not taking it.

**Your corollary does not hold, and we report that against our own interest in the other
direction.** You warned that if the 0.196 R dispersion were mostly `cost_R` dispersion,
§2.4 would be the cost finding in another coordinate system:

* `sd(gross)` = **0.0545**, `sd(cost_R)` = **0.0072** — a ratio of **7.6×**

The dispersion is genuinely in gross. But the per-symbol standard error is **0.0438**
(`σ_R` 1.275 over `N_eff` ≈ 848 per symbol), so under a null of identical true gross the
expected spread across 12 symbols is 0.0438 against the 0.0545 observed:
`χ²(11)` = 17.0, **`p` = 0.11**.

So: not a cost artefact, and also not established. Both halves belong in the record.

---

## 5. On your revised choice

We accept the structure of your answer and note where it lands relative to reviewer 1, who
independently chose **A** (attack the effect size, horizon first). We are reconciling the
two after this exchange, not before, and will send you the reconciliation.

Three things we want on the record now:

1. **You are right that C is a completed action, not an option.** We had not seen that. The
   six items were presented as "what we are doing regardless" and that is precisely what
   makes them not a choice.
2. **We accept the write-up as a deliverable rather than a consolation.** A clean negative
   on H1 momentum-impulse continuation on FX majors at retail cost — with a measured
   execution-cost constant, a documented labelling defect found by reconstruction, and now a
   documented selection worth more than the effect it was hiding — is what four phases
   actually produced.
3. **The cost constant is the asset.** Your framing of 0.46 Sharpe at 24-bar H1 retail FX as
   a hypothesis screen applied on paper before building anything is the single most useful
   sentence either reviewer has written to us, and it is now the first gate in our
   research plan rather than a result buried in a report.

One thing we will not do yet: choose the next hypothesis. You gated D on the term structure
and we agree with the gating.

---

## 6. What we retract, since you did

Symmetry is cheap and we owe it.

* **"The interior maximum in stop width at 3.0 ATR is structural."** Retracted as stated.
  It is a plateau across `sl` 3.0–4.0 on the full pool, and its location depends on an
  unverified commission constant. What survives is the monotone `sl` gradient.
* **"Whatever small edge exists is produced by the barriers, not despite them."** Withdrawn
  as over-stated. It rests on the 0.030 ATR gap, which is exactly the quantity your §2 says
  we have not yet explained. We should not have asserted a mechanism for it while calling
  the same gap unexplained.
* **The 10-symbol pool as the reporting basis.** Retracted entirely, per §1.
* **"The momentum trigger produces no measurable 24-hour drift."** Retracted, per §4.1.
  It was a net figure carrying a gross claim.

---

## 7. What your gate returned — neither branch, and a third

You gated D on the term structure and named two outcomes. It returned a third.

* **Not a second accounting asymmetry.** So D does not collapse to E on that ground.
* **Not front-loaded drift.** It builds monotonically to `h` = 24 — the opposite of
  front-loaded — so "shorter horizon with tighter targets" is not what the shape implies.
* **What it is: back-loaded drift inside 24 hours that fully reverses afterwards, and is
  smaller than the round-trip cost of taking it.**

That leaves us with a hypothesis that was **correct and unprofitable**, which is a
different object from a hypothesis that was wrong. The four phases did not fail to find
momentum continuation. They found it, measured it at 0.06–0.10 ATR over 24 hours, and
established that the retail execution cost of 0.10–0.11 ATR exceeds it — with 60% of that
cost being spread, which no amount of capital or volume buys down.

We think that is the paper, and it is a better one than the negative you and we were both
expecting a week ago. Two of its three central numbers were found by reconstructing a
quantity someone else had assembled — your `σ_R`, then your optional-stopping identity.
We are building the next thing with that property deliberately designed in, which is the
one recommendation of yours we would keep even if every other item on your worklist turned
out wrong.

Our remaining question is the one your own framework now poses and neither of us has
answered: **given a measured edge of 0.06–0.10 ATR and a spread floor of 0.066 ATR, is
there any instrument class reachable from here where the ratio inverts** — or is the
correct conclusion that this edge is real, known, and priced exactly at the level that
makes it unavailable to us?
