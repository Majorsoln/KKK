"""Ledger ya majaribio — DOCTRINE §11.1–§11.3, R13, R14, R19.

Signal si trade. Kati yao kuna hatua **mbili**, na kila moja inaweza kusimamisha
kwa sababu tofauti kabisa:

```
SIGNAL → [ RCE CHECK ] → [ EXECUTION ] → trade
             │                 │
      NO_BUDGET · MIN_LOT   NO_FILL
      max_open · correlated
      daily_loss · max_dd
      max_spread · news
```

`NO_BUDGET` inasema *"hatukuruhusiwa kujaribu"*. `NO_FILL` inasema *"tuliruhusiwa,
lakini soko lilihama."* Zikichanganywa kuwa "hakuna trade", swali muhimu zaidi la
uchunguzi halijibiki:

> Strategy ilikufa kwa kukosa edge, au kwa RCE kuzuia hatari?

Kwa hiyo rekodi ni **kwa kila jaribio**, si kwa kila trade — na jaribio
lililokataliwa lina taarifa nyingi kama lililofanikiwa.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Matokeo ya hatua ya KWANZA — RCE CHECK
# --------------------------------------------------------------------------

PASS = "PASS"

# Mbili hizi ni za Doctrine, si za RCE. RCE haina reject reason inayoitwa
# `NO_BUDGET`: budget ikiisha, lots zinakuwa 0 na RCE inatoa
# `risk_below_min_lot` (`sizing.py`). Tofauti inatoka kwenye `budget_at_signal`,
# na ipo kwa sababu maana zake ni tofauti kabisa:
#
#   NO_BUDGET      — mfumo umefungwa. Drawdown imekula bajeti yote.
#   MIN_LOT_REJECT — bajeti ipo, lakini ni ndogo kuliko lot ya chini ya broker.
#
# Ya kwanza ni hali ya akaunti; ya pili ni ukubwa wa akaunti dhidi ya symbol.
NO_BUDGET = "NO_BUDGET"
MIN_LOT_REJECT = "MIN_LOT_REJECT"

# Matokeo ya hatua ya PILI — EXECUTION
FILL = "FILL"
NO_FILL = "NO_FILL"


@dataclass(frozen=True)
class Attempt:
    """Row moja kwa kila **signal**, si kwa kila trade.

    Signal iliyokataliwa ina safu zile zile za ukaguzi na iliyofanikiwa. Bila
    hivyo, `NO_BUDGET` ni hesabu tupu badala ya uamuzi unaoweza kutolewa upya.
    """

    # ---- signal ----
    signal_time: Any
    symbol: str
    direction: str
    requested_price: float

    # ---- hatua 1: RCE CHECK ----
    rce_outcome: str
    budget_at_signal: float
    risk_per_trade_at_signal: float
    requested_lots: float
    allowed_lots: float
    broker_min_lot: float
    cost_pips: float = 0.0

    # ---- hatua 2: EXECUTION (tu ikiwa rce_outcome == PASS) ----
    execution_outcome: str | None = None
    reject_reason: str = ""
    fill_price: float | None = None
    slippage_pips: float | None = None

    @property
    def approved(self) -> bool:
        return self.rce_outcome == PASS

    @property
    def filled(self) -> bool:
        return self.execution_outcome == FILL

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["signal_time"] = str(self.signal_time)
        return payload


@dataclass
class Ledger:
    """Majaribio yote ya run moja, pamoja na viwango vyake."""

    attempts: list[Attempt] = field(default_factory=list)

    def add(self, attempt: Attempt) -> Attempt:
        self.attempts.append(attempt)
        return attempt

    def extend(self, many: Iterable[Attempt]) -> None:
        self.attempts.extend(many)

    # ---------------- viwango ----------------
    #
    # Vitatu, na havichanganywi. Kila kimoja kina denominator TOFAUTI, na
    # kuchanganya denominator ndiyo namna rahisi zaidi ya kupata namba
    # inayoonekana nzuri bila kuwa nzuri.

    @property
    def n_signals(self) -> int:
        """Kila kitu strategy ilichokitaka."""
        return len(self.attempts)

    @property
    def n_approved(self) -> int:
        """Zilizopita RCE — yaani orders zilizoombwa kweli."""
        return sum(1 for a in self.attempts if a.approved)

    @property
    def n_filled(self) -> int:
        return sum(1 for a in self.attempts if a.filled)

    @property
    def approval_rate(self) -> float:
        """`PASS ÷ signals` — ni RCE ilizuia kiasi gani."""
        return self.n_approved / self.n_signals if self.n_signals else float("nan")

    @property
    def fill_rate(self) -> float:
        """`FILL ÷ orders ZILIZOOMBWA` — §11.3.

        Denominator ni zilizopita RCE, si signals zote. Signal iliyokataliwa na
        RCE **haikuwahi kuwa order**, kwa hiyo kuiweka kwenye denominator
        ingeshusha `fill_rate` kwa sababu isiyo ya utekelezaji — na hapo kipimo
        kingekuwa kikipima kitu kingine kuliko jina lake.
        """
        return self.n_filled / self.n_approved if self.n_approved else float("nan")

    def by_outcome(self) -> dict[str, int]:
        """Mgawanyo kamili. Jumla yake ni `n_signals`, daima."""
        out: dict[str, int] = {}
        for a in self.attempts:
            key = a.rce_outcome if not a.approved else (a.execution_outcome or "?")
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    # ---------------- kuripoti ----------------

    def render(self) -> str:
        lines = [
            f"MAJARIBIO {self.n_signals:,} · yaliyopita RCE {self.n_approved:,} "
            f"({self.approval_rate:.1%}) · yaliyojazwa {self.n_filled:,} "
            f"(fill_rate {self.fill_rate:.1%})"
        ]
        for key, n in self.by_outcome().items():
            lines.append(f"   {key:<28} {n:>7,}  {n / self.n_signals:>6.1%}")
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "n_signals": self.n_signals,
            "n_approved": self.n_approved,
            "n_filled": self.n_filled,
            "approval_rate": self.approval_rate,
            "fill_rate": self.fill_rate,
            "by_outcome": self.by_outcome(),
            "attempts": [a.to_json() for a in self.attempts],
        }

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), indent=2, default=str) + "\n",
            encoding="utf-8", newline="\n",
        )
        return path
