"""§3.2 — FILL RATE: kipimo cha lazima cha cap (RCE-05).

```
fill_rate = orders zilizojaza ÷ orders zilizotumwa
KAMA fill_rate < fill_rate_min  →  ONYO: "cap ni ngumu; strategy inatofautiana na utafiti"
```

Hii ni **kipimo, si model** (spec §3.2). Kila fill inarekodi `requested_px`,
`fill_px`, slippage halisi na hali ya kujaza — malighafi ile ile inayolisha
calibration ya P(fill) ya T7 (RS-12) na ulinganisho wa provenance.

Hatua mbili zilizoandikwa kwenye spec zinapotokea ONYO:
(a) legeza cap **NA** rekodi kwamba dhana ya gharama imebadilika (namba za
    utafiti zinahitaji kupimwa upya);
(b) acha strategy hiyo kwa broker huyu.
RCE **hairuhusiwi** kuchagua kati yao yenyewe — uamuzi ni wa PD.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import RiskConfig

ACTION_A = "legeza cap NA rekodi kwamba dhana ya gharama imebadilika (utafiti unapimwa upya)"
ACTION_B = "acha strategy hii kwa broker huyu"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class FillRecord:
    """Rekodi ya order moja iliyotumwa (ijazwe au isijazwe)."""

    symbol: str
    direction: str
    order_type: str
    requested_px: float
    filled: bool
    cap_pips: float
    fill_px: float | None = None
    slippage_pips: float | None = None
    at: str = field(default_factory=_utcnow_iso)

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FillRateStatus:
    sent: int
    filled: int
    fill_rate: float | None
    threshold: float
    warning: str | None
    actions: tuple[str, str] = (ACTION_A, ACTION_B)

    @property
    def ok(self) -> bool:
        return self.warning is None


class FillTracker:
    """Inahesabu fill_rate na kutoa ONYO ikishuka chini ya `fill_rate_min`."""

    def __init__(self, cfg: RiskConfig, log_path: str | Path | None = None) -> None:
        self.cfg = cfg
        self.log_path = Path(log_path) if log_path else None
        self.records: list[FillRecord] = []

    # ---------- kurekodi ----------

    def record(
        self,
        symbol: str,
        direction: str,
        order_type: str,
        requested_px: float,
        cap_pips: float,
        filled: bool,
        fill_px: float | None = None,
        pip_size: float | None = None,
    ) -> FillRecord:
        """Rekodi order moja; slippage halisi inahesabiwa pale fill ipo."""
        slippage = None
        if filled and fill_px is not None and pip_size:
            slippage = abs(fill_px - requested_px) / pip_size
        record = FillRecord(
            symbol=symbol,
            direction=direction,
            order_type=order_type,
            requested_px=requested_px,
            filled=filled,
            cap_pips=cap_pips,
            fill_px=fill_px,
            slippage_pips=slippage,
        )
        self.records.append(record)
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record.to_json()) + "\n")
        return record

    # ---------- kipimo ----------

    @property
    def sent(self) -> int:
        return len(self.records)

    @property
    def filled(self) -> int:
        return sum(1 for record in self.records if record.filled)

    def fill_rate(self, symbol: str | None = None) -> float | None:
        """`fill_rate = zilizojaza ÷ zilizotumwa`. Bila orders → None."""
        records = [r for r in self.records if symbol is None or r.symbol == symbol]
        if not records:
            return None
        return sum(1 for r in records if r.filled) / len(records)

    def status(self, symbol: str | None = None) -> FillRateStatus:
        """Hali ya kipimo + ONYO la §3.2 ikiwa cap ni ngumu kupita kiasi."""
        records = [r for r in self.records if symbol is None or r.symbol == symbol]
        rate = self.fill_rate(symbol)
        threshold = self.cfg.fill_rate_min
        warning = None
        if rate is not None and rate < threshold:
            scope = symbol or "jumla"
            warning = (
                f"ONYO ({scope}): fill_rate {rate:.2f} < {threshold:.2f} — "
                "cap ni ngumu; strategy inatofautiana na utafiti"
            )
        return FillRateStatus(
            sent=len(records),
            filled=sum(1 for r in records if r.filled),
            fill_rate=rate,
            threshold=threshold,
            warning=warning,
        )
