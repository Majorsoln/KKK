"""§4 — LOTS (RCE-09).

```
lots = risk_per_trade ÷ ((sl_pips + cost_pips) × pip_value_acct)
```

Gharama iko kwenye **denominator**: SL ikigongwa, hasara halisi (pamoja na
gharama zote) ni HASA `risk_per_trade`. Kisha lots inarekebishwa kwa
`volume_step`/`volume_min`/`volume_max` za broker; ikishuka chini ya
`volume_min` → **REJECT** ("risk ndogo kuliko lot ya chini").

Kuzungusha ni **kwenda CHINI** (floor) kwa volume_step: kuzungusha juu
kungevunja ahadi ya §4 kwa kupitisha hasara juu ya `risk_per_trade`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .cost import CostBreakdown
from .symbols import SymbolSpec

REASON_BELOW_VOLUME_MIN = "below_volume_min"
REASON_BAD_DENOMINATOR = "non_positive_denominator"


@dataclass(frozen=True)
class LotsResult:
    """Ukubwa wa position + ushahidi wa hesabu (kwa log)."""

    lots_raw: float
    lots: float
    rejected: bool
    reason: str | None
    loss_at_sl: float
    denominator: float
    capped_at_volume_max: bool = False

    def to_log(self) -> dict[str, float | str | bool | None]:
        return {
            "lots_raw": round(self.lots_raw, 4),
            "lots": self.lots,
            "loss_at_sl": round(self.loss_at_sl, 2),
            "rejected": self.rejected,
            "reason": self.reason,
            "capped_at_volume_max": self.capped_at_volume_max,
        }


def _floor_to_step(value: float, step: float) -> float:
    steps = math.floor(round(value / step, 9))
    return round(steps * step, 10)


def compute_lots(
    risk_per_trade: float,
    sl_pips: float,
    cost: CostBreakdown,
    symbol: SymbolSpec,
) -> LotsResult:
    """Lots kwa fomula ya §4 + marekebisho ya volume ya broker."""
    if sl_pips <= 0:
        raise ValueError("sl_pips lazima iwe > 0 (SL floor ni kazi ya KAIROS-1 §2)")

    denominator = (sl_pips + cost.cost_pips) * cost.pip_value_acct
    if denominator <= 0:
        return LotsResult(
            lots_raw=0.0,
            lots=0.0,
            rejected=True,
            reason=REASON_BAD_DENOMINATOR,
            loss_at_sl=0.0,
            denominator=denominator,
        )

    lots_raw = risk_per_trade / denominator
    capped = False
    if lots_raw > symbol.volume_max:
        lots = symbol.volume_max
        capped = True
    else:
        lots = _floor_to_step(lots_raw, symbol.volume_step)

    if lots < symbol.volume_min:
        return LotsResult(
            lots_raw=lots_raw,
            lots=0.0,
            rejected=True,
            reason=REASON_BELOW_VOLUME_MIN,
            loss_at_sl=0.0,
            denominator=denominator,
            capped_at_volume_max=capped,
        )

    return LotsResult(
        lots_raw=lots_raw,
        lots=lots,
        rejected=False,
        reason=None,
        loss_at_sl=lots * denominator,
        denominator=denominator,
        capped_at_volume_max=capped,
    )
