"""DF-14 — L5 splits: purged K-fold + embargo + HOLDOUT GUARD (spec §7).

```
Purged K-fold + embargo:
   embargo = horizon × 1.5          (labels zinapishana; bila purge, CV ni ya uongo)
Walk-forward anchored kwa uthibitisho wa mfuatano wa wakati.
HOLDOUT = 20% ya mwisho kwa mfuatano wa wakati — INAFUNGULIWA MARA MOJA, R8.
```

Mipaka **yote** inatoka `config/data.yaml` (§splits) — hakuna tarehe kwenye
code. Ndiyo maana `SplitPlan.from_config` ndiyo njia pekee ya kuizalisha.

**Lango G2 (holdout guard):** `assert_trainval_only()` inasimamisha kazi yoyote
ya R0–R7 inayogusa kipindi cha holdout au RESERVE. Kufungua holdout ni tukio la
PD, mara moja, R8 — na `open_holdout()` inahitaji sababu iliyoandikwa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Sequence

import pandas as pd


class HoldoutViolation(RuntimeError):
    """Kazi ya R0–R7 imegusa holdout/RESERVE. Mzunguko ungebatilika (§R8)."""


@dataclass(frozen=True)
class Fold:
    """Fold moja ya wakati: validation ni block; train ni kilichobaki, kimepurgwa."""

    index: int
    val_start: date
    val_end: date
    train_ranges: tuple[tuple[date, date], ...]

    def render(self) -> str:
        blocks = " · ".join(f"{a}→{b}" for a, b in self.train_ranges)
        return f"F{self.index}: val {self.val_start}→{self.val_end} | train {blocks}"


@dataclass(frozen=True)
class SplitPlan:
    """Mpango kamili wa splits — vyote vinatoka config (§7 + DATA_SPLIT_PLAN)."""

    data_start: date
    data_end: date
    trainval_end: date
    holdout_start: date
    fold_boundaries: tuple[date, ...]
    embargo_bars: int
    horizon_bars: int
    decision_tf_minutes: int = 60
    future_reserve_start: date | None = None

    # ---------- ujenzi ----------

    @classmethod
    def from_config(cls, cfg) -> "SplitPlan":
        if bool(cfg.get("splits.random_split", False)):
            raise ValueError(
                "`splits.random_split` ni `true` — spec §7 inasema random split "
                "kwenye data ya soko ni UVUJAJI. Kamwe."
            )
        horizon = int(cfg.get("labels.horizon_bars"))
        embargo_mult = float(cfg.get("splits.embargo_mult"))
        reserve = str(cfg.get("splits.future_reserve", "") or "").rstrip("+")
        return cls(
            data_start=_as_date(cfg.get("splits.data_start")),
            data_end=_as_date(cfg.get("splits.data_end")),
            trainval_end=_as_date(cfg.get("splits.trainval_end")),
            holdout_start=_as_date(cfg.get("splits.holdout_start")),
            fold_boundaries=tuple(
                _as_date(d) for d in cfg.get("splits.fold_boundaries", []) or []
            ),
            embargo_bars=int(round(horizon * embargo_mult)),
            horizon_bars=horizon,
            future_reserve_start=_as_date(reserve) if reserve else None,
        )

    # ---------- mipaka ----------

    @property
    def embargo_delta(self) -> timedelta:
        """Embargo kwa **bars**, si saa za ukuta (wikendi si embargo)."""
        return timedelta(minutes=self.embargo_bars * self.decision_tf_minutes)

    @property
    def purge_days(self) -> timedelta:
        """Embargo ikigeuzwa kuwa siku — **kwa kupandisha juu**, si kukata.

        Bars 36 za H1 = saa 36 = siku 1.5. Kukata chini kungetoa siku 1 na
        kuacha nusu ya embargo bila kufanya kazi; kupandisha kunatoa siku 2.
        Kosa la upande wa tahadhari ni kupoteza siku moja ya training; kosa la
        upande mwingine ni CV inayodanganya (§7).
        """
        minutes = self.embargo_bars * self.decision_tf_minutes
        return timedelta(days=max(1, -(-minutes // (60 * 24))))

    def is_holdout(self, day: date) -> bool:
        return day >= self.holdout_start

    def is_reserve(self, day: date) -> bool:
        return self.future_reserve_start is not None and day >= self.future_reserve_start

    def is_trainval(self, day: date) -> bool:
        return self.data_start <= day <= self.trainval_end

    # ---------- folds ----------

    def folds(self) -> list[Fold]:
        """Folds tano za muda zinazofuatana (DATA_SPLIT_PLAN §2), zikiwa zimepurgwa."""
        edges = [self.data_start, *self.fold_boundaries, self.trainval_end]
        blocks = [
            (edges[i] if i == 0 else edges[i] + timedelta(days=1), edges[i + 1])
            for i in range(len(edges) - 1)
        ]
        gap = self.purge_days
        out: list[Fold] = []
        for index, (val_start, val_end) in enumerate(blocks, start=1):
            ranges: list[tuple[date, date]] = []
            for other_start, other_end in blocks:
                if (other_start, other_end) == (val_start, val_end):
                    continue
                # PURGE: train inasimama `gap` kabla ya validation na inaanza
                # `gap` baada yake — labels zinapishana kwa horizon (§7).
                if other_end < val_start:
                    ranges.append((other_start, min(other_end, val_start - gap)))
                else:
                    ranges.append((max(other_start, val_end + gap), other_end))
            out.append(
                Fold(
                    index=index,
                    val_start=val_start,
                    val_end=val_end,
                    train_ranges=tuple((a, b) for a, b in ranges if a <= b),
                )
            )
        return out

    def walk_forward(self) -> list[Fold]:
        """Anchored walk-forward: train inaanzia mwanzo na kupanuka (§7)."""
        blocks = [(f.val_start, f.val_end) for f in self.folds()]
        gap = self.purge_days
        out: list[Fold] = []
        for index in range(1, len(blocks)):
            val_start, val_end = blocks[index]
            out.append(
                Fold(
                    index=index + 1,
                    val_start=val_start,
                    val_end=val_end,
                    train_ranges=((self.data_start, val_start - gap),),
                )
            )
        return out

    # ---------- lango G2 ----------

    def assert_trainval_only(self, days: Iterable[date], purpose: str) -> None:
        """G2 — kazi ya R0–R7 haiguswi holdout wala RESERVE.

        Ikiguswa, mzunguko mzima ungekuwa batili na **hakuna njia ya
        kuurekebisha** (§R8). Kwa hiyo ni hitilafu, si onyo.
        """
        offenders = sorted({d for d in days if self.is_holdout(d) or self.is_reserve(d)})
        if offenders:
            raise HoldoutViolation(
                f"UKIUKAJI WA G2: `{purpose}` imegusa siku {offenders[:5]}"
                f"{'...' if len(offenders) > 5 else ''} zilizo ndani ya HOLDOUT "
                f"(kuanzia {self.holdout_start}) au RESERVE. Awamu R0–R7 zinatumia "
                "TRAIN/VALIDATION pekee (§7, DATA_SPLIT_PLAN §3)."
            )

    def open_holdout(self, reason: str, authorised_by: str) -> dict[str, str]:
        """R8 pekee — kufungua holdout ni tukio linaloandikwa, si flag ya kimya."""
        if not reason.strip() or not authorised_by.strip():
            raise HoldoutViolation(
                "kufungua holdout kunahitaji `reason` na `authorised_by` "
                "(§R8: mara MOJA, vigezo vimeandikwa KABLA)"
            )
        return {
            "event": "holdout_opened",
            "holdout_start": self.holdout_start.isoformat(),
            "data_end": self.data_end.isoformat(),
            "reason": reason,
            "authorised_by": authorised_by,
        }

    def render(self) -> str:
        lines = [
            f"TRAIN+VAL {self.data_start} → {self.trainval_end}",
            f"HOLDOUT   {self.holdout_start} → {self.data_end}  (R8 pekee)",
            f"embargo   bars {self.embargo_bars} (horizon {self.horizon_bars} × mult)",
        ]
        lines += [f"  {f.render()}" for f in self.folds()]
        if self.future_reserve_start:
            lines.append(f"RESERVE   {self.future_reserve_start}+  (haionwi sasa)")
        return "\n".join(lines)


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def days_of(timestamps: Sequence[pd.Timestamp] | pd.DatetimeIndex) -> list[date]:
    """Siku za kipekee kutoka timestamps — ingizo la `assert_trainval_only`."""
    index = pd.DatetimeIndex(timestamps)
    return sorted({ts.date() for ts in index})
