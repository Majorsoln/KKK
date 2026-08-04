"""§2 — BAJETI YA SIKU (RCE-01, RCE-02).

```
base      = base_percentage × base_balance                    # inaanza 00:00 CE(S)T
penalty   = penalty_factor × max(0, base_balance − current_balance)
budget    = base − penalty + win_factor×today_profit − loss_factor×today_loss
risk_per_trade = budget ÷ max_open_trades
```

Mambo mawili ambayo spec inasisitiza na code hii inayatekeleza kama yalivyo:

* `base_balance` ni **rejea isiyobadilika** ya config — si salio la sasa. Kwa
  hiyo `penalty` inafuata **DD ya jumla tangu mwanzo**, si ya jana pekee, na
  **hairesetiwi** siku inapoanza.
* `today_profit` na `today_loss` ni vihesabu **viwili tofauti** vinavyoreset
  00:00 kwenye `day_reset_tz` — havijumlishwi kuwa namba moja. Safu ya 4 ya
  jedwali la §2 (leo −$150 kisha +$100) ndiyo inayothibitisha hilo:
  budget = 400 − 125 − 150 + 50 = 175, si 400 − 125 − 50.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from .config import RiskConfig


@dataclass(frozen=True)
class AccountState:
    """Hali halisi ya akaunti (kutoka MT5/broker), si makadirio."""

    current_balance: float
    today_profit: float = 0.0
    today_loss: float = 0.0  # thamani CHANYA = hasara ya leo
    open_positions: int = 0

    def __post_init__(self) -> None:
        if self.today_profit < 0 or self.today_loss < 0:
            raise ValueError(
                "today_profit/today_loss zinahifadhiwa kama thamani chanya — "
                "ni vihesabu viwili tofauti (spec §2)"
            )
        if self.open_positions < 0:
            raise ValueError("open_positions haiwezi kuwa hasi")


@dataclass(frozen=True)
class BudgetResult:
    """Matokeo ya §2 pamoja na vipande vyake (kwa log na dashboard)."""

    base: float
    penalty: float
    total_drawdown: float
    budget: float
    risk_per_trade: float

    def to_log(self) -> dict[str, float]:
        return {
            "base": round(self.base, 2),
            "penalty": round(self.penalty, 2),
            "total_drawdown": round(self.total_drawdown, 2),
            "budget": round(self.budget, 2),
            "risk_per_trade": round(self.risk_per_trade, 2),
        }


def compute_budget(account: AccountState, cfg: RiskConfig) -> BudgetResult:
    """Bajeti ya siku na risk kwa kila trade (§2)."""
    base = cfg.base_percentage * cfg.base_balance
    total_dd = max(0.0, cfg.base_balance - account.current_balance)
    penalty = cfg.penalty_factor * total_dd
    budget = (
        base
        - penalty
        + cfg.win_factor * account.today_profit
        - cfg.loss_factor * account.today_loss
    )
    return BudgetResult(
        base=base,
        penalty=penalty,
        total_drawdown=total_dd,
        budget=budget,
        risk_per_trade=budget / cfg.max_open_trades,
    )


# --------------------------------------------------------------------------
# RCE-02 — reset ya 00:00 kwenye day_reset_tz
# --------------------------------------------------------------------------


def trading_day(moment: datetime, cfg: RiskConfig) -> date:
    """Siku ya biashara ya wakati fulani, kwa saa za `day_reset_tz` (00:00 CE(S)T)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo(cfg.day_reset_tz)).date()


class DayCounters:
    """Vihesabu vya leo vinavyoreset 00:00 CE(S)T (spec §2).

    `penalty` haitegemei darasa hili kwa makusudi: inafuata DD ya jumla, kwa
    hiyo haipati reset ya siku (spec §2: "`penalty` **hairesetiwi**").
    """

    def __init__(self, cfg: RiskConfig, now: datetime) -> None:
        self.cfg = cfg
        self.day = trading_day(now, cfg)
        self.today_profit = 0.0
        self.today_loss = 0.0

    def roll_to(self, now: datetime) -> bool:
        """Hamia siku mpya ikiwa 00:00 imepita. Inarudisha True ikiwa imereset."""
        current = trading_day(now, self.cfg)
        if current == self.day:
            return False
        self.day = current
        self.today_profit = 0.0
        self.today_loss = 0.0
        return True

    def record_closed_trade(self, pnl: float, now: datetime) -> None:
        """Rekodi matokeo ya trade iliyofungwa kwenye kihesabu chake."""
        self.roll_to(now)
        if pnl >= 0:
            self.today_profit += pnl
        else:
            self.today_loss += -pnl

    def apply_to(self, account: AccountState) -> AccountState:
        return replace(account, today_profit=self.today_profit, today_loss=self.today_loss)
