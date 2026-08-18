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

> **[RESULTS PENDING — the two runs go here before this letter is sent.]**

We will report what the table says, including if it says the dispersion is mostly `cost_R`
dispersion — which, as you noted, would mean §2.4 is our cost finding in another coordinate
system rather than a separate cross-sectional result. We would rather publish that than
keep §2.4 as an asset.

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
