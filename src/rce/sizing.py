"""RCE-09 — lots (spec §4).

```
lots = risk_per_trade ÷ ((sl_pips + cost_pips) × pip_value_acct)
```

Gharama iko kwenye **denominator**: SL ikigongwa, hasara halisi (pamoja na
gharama zote) ni **HASA** `risk_per_trade`. Kisha lots inarekebishwa kwa
`volume_step`/`volume_min`/`volume_max` za broker; ikishuka chini ya
`volume_min` → **REJECT** ("risk ndogo kuliko lot ya chini").
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .cost import SymbolSpec

REJECT_BELOW_MIN_LOT = "risk_below_min_lot"


@dataclass(frozen=True)
class SizingResult:
    lots: float
    lots_raw: float
    risk_at_stop: float
    rejected: bool = False
    reason: str = ""

    def render(self) -> str:
        if self.rejected:
            return f"REJECT ({self.reason}) · lots_raw={self.lots_raw:.4f}"
        return (
            f"lots={self.lots:.2f} (raw {self.lots_raw:.4f}) · "
            f"hasara kwenye SL ≈ {self.risk_at_stop:.2f}"
        )


def _round_to_step(value: float, step: float) -> float:
    """Kushusha hadi `volume_step` ya broker — kamwe si kupandisha.

    Kupandisha kungeongeza hasara juu ya `risk_per_trade`, na hilo ndilo
    fomula ya §4 inalizuia.
    """
    if step <= 0:
        return value
    steps = math.floor(round(value / step, 9))
    return round(steps * step, 10)


def compute_lots(
    risk_per_trade: float,
    sl_pips: float,
    cost_pips: float,
    pip_value_acct: float,
    spec: SymbolSpec,
) -> SizingResult:
    """Lots kwa spec §4, zikiwa zimerekebishwa kwa mipaka ya broker."""
    if sl_pips <= 0:
        raise ValueError("`sl_pips` lazima iwe > 0 (SL floor ni S2 ya KAIROS-1)")
    if pip_value_acct <= 0:
        raise ValueError("`pip_value_acct` lazima iwe > 0 (spec §3.5)")

    denominator = (sl_pips + cost_pips) * pip_value_acct
    lots_raw = risk_per_trade / denominator if denominator > 0 else 0.0

    lots = _round_to_step(lots_raw, spec.volume_step)
    if spec.volume_max:
        lots = min(lots, spec.volume_max)

    if lots < spec.volume_min:
        return SizingResult(
            lots=0.0,
            lots_raw=lots_raw,
            risk_at_stop=0.0,
            rejected=True,
            reason=REJECT_BELOW_MIN_LOT,
        )
    return SizingResult(
        lots=lots,
        lots_raw=lots_raw,
        risk_at_stop=lots * (sl_pips + cost_pips) * pip_value_acct,
    )
