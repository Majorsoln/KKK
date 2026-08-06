"""RCE-01/RCE-02 — bajeti ya siku na risk kwa kila trade (spec §2).

```
base           = base_percentage × base_balance
penalty        = penalty_factor × max(0, base_balance − current_balance)
budget         = base − penalty + win_factor×today_profit − loss_factor×today_loss
risk_per_trade = budget ÷ max_open_trades
```

Sheria za spec zinazotekelezwa hapa:

* `base_balance` ni **rejea isiyobadilika** (config), si salio la sasa;
* `current_balance` ni **halisi kutoka akaunti**;
* `penalty` inategemea **DD ya jumla tangu mwanzo**, si ya jana pekee, na
  **hairesetiwi**;
* `today_profit`/`today_loss` **zinareset 00:00 CE(S)T** (`day_reset_tz`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class AccountState:
    """Hali ya akaunti wakati wa uamuzi. Zote zinatoka broker, si makadirio."""

    current_balance: float
    today_profit: float = 0.0  # faida ya leo (chanya)
    today_loss: float = 0.0  # hasara ya leo (chanya — ukubwa wake)
    open_positions: int = 0


@dataclass(frozen=True)
class BudgetResult:
    base: float
    penalty: float
    budget: float
    risk_per_trade: float

    def render(self) -> str:
        return (
            f"base={self.base:.2f} penalty={self.penalty:.2f} "
            f"budget={self.budget:.2f} risk/trade={self.risk_per_trade:.2f}"
        )


def trading_day(now: datetime, day_reset_tz: str) -> date:
    """Siku ya bajeti kwa `day_reset_tz` (spec §2: reset 00:00 CE(S)T).

    Muda unaingia UTC (kanuni ya §2 ya DATA_FEATURE_STANDARD) na unabadilishwa
    hapa — sehemu MOJA inayojua timezone ya reset.
    """
    moment = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(day_reset_tz)).date()


def compute_budget(cfg, state: AccountState) -> BudgetResult:
    """Bajeti ya siku + risk kwa kila trade (spec §2)."""
    base_balance = float(cfg.get("base_balance"))
    base = float(cfg.get("base_percentage")) * base_balance
    penalty = float(cfg.get("penalty_factor")) * max(0.0, base_balance - state.current_balance)
    budget = (
        base
        - penalty
        + float(cfg.get("win_factor")) * state.today_profit
        - float(cfg.get("loss_factor")) * state.today_loss
    )
    max_open = int(cfg.get("max_open_trades"))
    return BudgetResult(
        base=base,
        penalty=penalty,
        budget=budget,
        risk_per_trade=budget / max_open if max_open else 0.0,
    )
