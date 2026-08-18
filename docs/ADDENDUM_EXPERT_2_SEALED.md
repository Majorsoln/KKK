# Addendum to reviewer 2 — SEALED until Q5 is answered

**Measured:** 2026-08-18 · **Send only after** reviewer 2 has answered question 5 of
`FOLLOWUP_EXPERT_2.md`.

> **Why this is sealed.** In Q5 we asked him to pre-commit to a reading — *"what number
> would you want to see, and what would you conclude if the full pool is negative at the
> best cell? We would rather pre-commit to your reading than choose it afterwards."*
> Sending him the answer before he commits destroys the only thing that question was for.
> The measurement is timestamped and pushed so the order is verifiable.

---

## What we measured

You identified the EURCHF/EURGBP exclusion as the largest uncharged selection in the
brief — it moved the pool from −0.0163 to +0.0039, after which we reported the entire
49-cell EV grid on the survivors. We agreed and said we would re-measure the full
12-symbol pool on the corrected labels. We have.

One command, no trial budget consumed (`cost-audit` is a population statistic over
already-built labels, not a selection step):

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

**No cell in the grid is positive on the unselected pool.** The best is `sl` 3.0 / `tp` 2.0
at −0.0107 R.

The selection was worth **+0.0190 R**. That is 2.3× the entire remaining point estimate,
larger than the labelling defect it survived (0.0124), and larger than the setup-vs-control
effect we called our best result (0.0056). You were right, and you under-stated it.

---

## What this does to the two of us

**To our claim.** The positive region of the grid was an artefact of the exclusion.
We had already reported that no cell survives multiple-comparison correction; we now have
to report something worse — that on data we did not choose, no cell is positive at all.

**To your claim.** Your forced choice C rests on *"the negative result is not
established"*, supported by a 1.02 gross Sharpe being taxed 45% by commission. On the
unselected pool the gross Sharpe is **0.22** and cost is **240%** of it.

We tested your own argument to its limit rather than waiting for you to. Taking the top
Dukascopy tier you identified (0.15 pips round turn instead of 0.7):

> `commission_R` 0.0146 → 0.0031, `cost_R` 0.0186 → 0.0071
> ⇒ `EV net` **+0.0006 R**, Sharpe **0.02**, `t` **0.05**

**At effectively zero commission the unselected pool still produces nothing.** That is the
cleanest available test of "execution-cost result" versus "no-edge result", it is run on
your numbers and your reasoning, and on unselected data it comes back "no edge".

Two things we want to be fair about:

1. Your qualification in §6 — that the `sl` 3.0 interior optimum is structural *in our
   assumed commission* — holds, and the full pool weakens the optimum further: `sl` 3.0
   best is −0.0107 and `sl` 4.0 best is −0.0111. That is a plateau, not a peak. The
   monotone improvement along `sl` (−0.2229 → −0.0107) is unaffected, so the cost
   mechanism itself still shows clearly. Only its claimed interior maximum does not.
2. Your Q5 remedy is still the right one and we have not yet done it. Excluding two
   symbols after seeing their EV is cherry-picking; excluding or down-weighting them by a
   **pre-declared rule on label-free characteristics** — spread-per-daily-move, a
   volatility floor — is not. We will declare such a rule before measuring it and let it
   fall where it falls, including if it leaves EURCHF in. Until then the number we report
   is −0.0109, not +0.0081.

---

## Revised questions

These replace questions 1 and 5 of the original letter. The others stand.

**1′.** Does `t` = −0.90 on unselected data establish the negative result, on your own
criterion? If not, what would?

**5′.** You proposed continuous weighting on a pre-registered characteristic as the
principled alternative to a whitelist. Given that the unselected pool is negative
everywhere, is that still a research direction, or is it now only a way of documenting
how the earlier number was produced?

**7 (new).** Your worklist put commission verification first because it "changes the
*shape* of the EV surface". On the full pool, zero commission moves `t` from −0.90 to
+0.05. Does commission verification remain item 1, or does it drop below establishing
which universe the strategy is measured on?
