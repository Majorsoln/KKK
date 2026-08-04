"""§5 — VIABILITY GATE: checks 6 kwa MPANGILIO wake (RCE-10, RCE-11).

| # | Ukaguzi | REJECT reason |
|---|---|---|
| 1 | max open trades | `max_open_trades` |
| 2 | max correlated (makundi YOTE ya pair) | `max_correlated:<kundi>` |
| 3 | daily-loss brake (loss ≥ 0.75×base NA positions wazi) | `daily_loss_75pct_with_open` |
| 4 | total-DD | `max_total_dd` |
| 5 | max-spread | `max_spread` |
| 6 | news | `news_window` |

Mpangilio ni sehemu ya spec, si mapambo: check ya kwanza inayofeli ndiyo sababu
inayoandikwa, na checks zilizobaki **hazikimbii**. Kila REJECT inaandikwa na
**config-fingerprint** ili kesho ijulikane ilikataliwa kwa vigezo vipi.

**RCE-11 — DD inazuia entries MPYA pekee.** Check 4 inarudisha REJECT ya
pendekezo jipya. Module hii haina njia yoyote ya kufunga position iliyo wazi,
na haitakuwa nayo: kufunga positions ni nje ya mamlaka ya gate (§5 ya spec).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from .budget import AccountState, BudgetResult, compute_budget
from .config import RiskConfig

REASON_MAX_OPEN = "max_open_trades"
REASON_MAX_CORRELATED = "max_correlated"
REASON_DAILY_LOSS = "daily_loss_75pct_with_open"
REASON_MAX_TOTAL_DD = "max_total_dd"
REASON_MAX_SPREAD = "max_spread"
REASON_NEWS = "news_window"

CHECK_ORDER = (
    "max_open_trades",
    "max_correlated",
    "daily_loss_brake",
    "max_total_dd",
    "max_spread",
    "news",
)


@dataclass(frozen=True)
class GateInputs:
    """Hali ya soko na akaunti wakati wa uamuzi."""

    symbol: str
    spread_pips: float
    account: AccountState
    open_symbols: Sequence[str] = ()
    news_soon: bool = False


@dataclass(frozen=True)
class CheckOutcome:
    name: str
    passed: bool
    reason: str | None
    detail: dict[str, float | int | str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class GateResult:
    """Matokeo ya gate + rekodi tayari kwa log/dashboard."""

    passed: bool
    reason: str | None
    checks: list[CheckOutcome]
    fingerprint: str
    warnings: list[str] = field(default_factory=list)

    def to_log(self, symbol: str) -> dict[str, object]:
        """Rekodi ya §5: `lifecycle=REJECTED` + sababu + config-fingerprint."""
        return {
            "lifecycle": "APPROVED" if self.passed else "REJECTED",
            "symbol": symbol,
            "reason": self.reason,
            "config_fingerprint": self.fingerprint,
            "checks": [
                {"name": c.name, "passed": c.passed, "reason": c.reason, **c.detail}
                for c in self.checks
            ],
            "warnings": self.warnings,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


def _correlated_counts(symbol: str, open_symbols: Sequence[str], cfg: RiskConfig) -> dict[str, int]:
    """Idadi ya positions wazi kwenye KILA kundi linalomhusu symbol (§5 check 2)."""
    groups = cfg.correlation_groups
    counts: dict[str, int] = {}
    for group in cfg.groups_of(symbol):
        members = set(groups[group])
        counts[group] = sum(1 for open_symbol in open_symbols if open_symbol in members)
    return counts


def evaluate_gate(
    inputs: GateInputs,
    cfg: RiskConfig,
    budget: BudgetResult | None = None,
) -> GateResult:
    """Checks 6 kwa mpangilio wa §5. Ya kwanza inayofeli ndiyo sababu."""
    budget = budget or compute_budget(inputs.account, cfg)
    account = inputs.account
    checks: list[CheckOutcome] = []
    warnings: list[str] = []

    # 1 — max open trades
    passed = account.open_positions < cfg.max_open_trades
    checks.append(
        CheckOutcome(
            "max_open_trades",
            passed,
            None if passed else REASON_MAX_OPEN,
            {"open_positions": account.open_positions, "limit": cfg.max_open_trades},
        )
    )
    if not passed:
        return GateResult(False, REASON_MAX_OPEN, checks, cfg.fingerprint, warnings)

    # 2 — max correlated (makundi YOTE ya pair)
    counts = _correlated_counts(inputs.symbol, inputs.open_symbols, cfg)
    breached = [group for group, count in counts.items() if count >= cfg.max_correlated]
    passed = not breached
    reason = None if passed else f"{REASON_MAX_CORRELATED}:{sorted(breached)[0]}"
    checks.append(
        CheckOutcome(
            "max_correlated",
            passed,
            reason,
            {"limit": cfg.max_correlated, **{f"group:{g}": c for g, c in counts.items()}},
        )
    )
    if not passed:
        return GateResult(False, reason, checks, cfg.fingerprint, warnings)

    # 3 — daily-loss brake: loss ≥ frac × base NA positions wazi
    brake_level = cfg.daily_loss_stop_frac * budget.base
    tripped = account.today_loss >= brake_level and account.open_positions > 0
    checks.append(
        CheckOutcome(
            "daily_loss_brake",
            not tripped,
            None if not tripped else REASON_DAILY_LOSS,
            {
                "today_loss": account.today_loss,
                "brake_level": brake_level,
                "open_positions": account.open_positions,
            },
        )
    )
    if tripped:
        return GateResult(False, REASON_DAILY_LOSS, checks, cfg.fingerprint, warnings)

    # 4 — total-DD (inazuia entries MPYA pekee — RCE-11)
    passed = budget.total_drawdown < cfg.max_total_dd
    checks.append(
        CheckOutcome(
            "max_total_dd",
            passed,
            None if passed else REASON_MAX_TOTAL_DD,
            {"total_drawdown": budget.total_drawdown, "limit": cfg.max_total_dd},
        )
    )
    if not passed:
        return GateResult(False, REASON_MAX_TOTAL_DD, checks, cfg.fingerprint, warnings)

    # 5 — max-spread
    limits = cfg.max_spread
    limit = limits.get(inputs.symbol)
    if limit is None:
        # Spec §5 inataja `max_spread[symbol]`; symbol isiyo na kikomo kwenye config
        # haipewi kikomo cha kubuni — inaripotiwa kwa PD kama pengo la config.
        warnings.append(f"max_spread_unset:{inputs.symbol}")
        passed = True
        detail: dict[str, float | int | str | bool] = {"spread_pips": inputs.spread_pips}
    else:
        passed = inputs.spread_pips <= limit
        detail = {"spread_pips": inputs.spread_pips, "limit": limit}
    checks.append(
        CheckOutcome("max_spread", passed, None if passed else REASON_MAX_SPREAD, detail)
    )
    if not passed:
        return GateResult(False, REASON_MAX_SPREAD, checks, cfg.fingerprint, warnings)

    # 6 — news
    blocked = (not cfg.trade_news) and inputs.news_soon
    checks.append(
        CheckOutcome(
            "news",
            not blocked,
            None if not blocked else REASON_NEWS,
            {"trade_news": cfg.trade_news, "news_soon": inputs.news_soon},
        )
    )
    if blocked:
        return GateResult(False, REASON_NEWS, checks, cfg.fingerprint, warnings)

    return GateResult(True, None, checks, cfg.fingerprint, warnings)
