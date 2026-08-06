"""RCE-10..RCE-12 — VIABILITY GATE (spec §5, §5b).

Ukaguzi **sita kwa mpangilio wake**; wa kwanza unaoshindwa ndio unaotoa sababu.
Kikikataliwa: **hakuna trade**, na rekodi ya `lifecycle=REJECTED` + sababu +
config-fingerprint inaandikwa.

Mambo mawili ya spec yanayotekelezwa hapa kwa uangalifu:

* **§5 check 4:** DD inazuia **entries mpya PEKEE** — HAKUNA kufunga positions
  zilizo wazi.
* **§5b:** signal iliyokataliwa **HAIWEKWI kwenye foleni** wala **HAIRUDIWI**.
  Kila bar ni tathmini mpya. Kwa hiyo module hii **haina** hali inayodumu:
  inapokea, inaamua, inasahau.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

# Sababu za REJECT — majina yale yale ya spec §5.
REJECT_MAX_OPEN = "max_open_trades"
REJECT_MAX_CORRELATED = "max_correlated"
REJECT_DAILY_LOSS = "daily_loss_75pct_with_open"
REJECT_MAX_TOTAL_DD = "max_total_dd"
REJECT_MAX_SPREAD = "max_spread"
REJECT_NEWS = "news_window"


@dataclass(frozen=True)
class GateContext:
    """Kila kitu gate inachohitaji. Vyote vinatoka broker/RCE, si model."""

    symbol: str
    open_positions: int
    open_symbols: Sequence[str] = field(default_factory=tuple)
    current_balance: float = 0.0
    today_loss: float = 0.0
    spread_pips: float = 0.0
    news_imminent: bool = False
    now: datetime | None = None


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    reason: str = ""
    config_fingerprint: str = ""
    checked_at: str = ""

    def render(self) -> str:
        return "PASS" if self.passed else f"REJECT ({self.reason})"

    def to_log(self) -> dict[str, Any]:
        """Rekodi ya `lifecycle` kwa dashboard (spec §5)."""
        return {
            "lifecycle": "PASS" if self.passed else "REJECTED",
            "reason": self.reason,
            "config_fingerprint": self.config_fingerprint,
            "checked_at": self.checked_at,
        }


def correlation_groups_of(symbol: str, groups: Mapping[str, Sequence[str]]) -> list[str]:
    """Makundi **YOTE** ambayo symbol imo (spec §5 check 2).

    Spec inasisitiza "makundi YOTE ya pair" — symbol moja inaweza kuwa kwenye
    makundi zaidi ya moja (mf. EURUSD iko `USD_group` na `EUR_group`), na kila
    moja lina kikomo chake.
    """
    return [name for name, members in groups.items() if symbol in members]


def _correlated_exposure(
    symbol: str,
    open_symbols: Sequence[str],
    groups: Mapping[str, Sequence[str]],
) -> tuple[str, int]:
    """Kundi lenye exposure kubwa zaidi kati ya makundi ya symbol, na idadi yake."""
    worst_group, worst_count = "", 0
    for group in correlation_groups_of(symbol, groups):
        members = set(groups[group])
        count = sum(1 for s in open_symbols if s in members)
        if count > worst_count:
            worst_group, worst_count = group, count
    return worst_group, worst_count


def evaluate_gate(cfg, ctx: GateContext) -> GateDecision:
    """Ukaguzi sita kwa mpangilio wa spec §5."""
    now = (ctx.now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    fingerprint = getattr(cfg, "config_hash", "")
    base = float(cfg.get("base_percentage")) * float(cfg.get("base_balance"))

    def _decide(passed: bool, reason: str = "") -> GateDecision:
        return GateDecision(
            passed=passed,
            reason=reason,
            config_fingerprint=fingerprint,
            checked_at=now.isoformat(timespec="seconds"),
        )

    # 1 — max open trades
    if ctx.open_positions >= int(cfg.get("max_open_trades")):
        return _decide(False, REJECT_MAX_OPEN)

    # 2 — max correlated (makundi YOTE ya pair)
    groups = cfg.get("correlation_groups", {}) or {}
    group, exposure = _correlated_exposure(ctx.symbol, ctx.open_symbols, groups)
    if exposure >= int(cfg.get("max_correlated")):
        return _decide(False, f"{REJECT_MAX_CORRELATED}:{group}")

    # 3 — daily-loss brake (hasara ya leo NA positions wazi)
    stop_frac = float(cfg.get("daily_loss_stop_frac"))
    if ctx.today_loss >= stop_frac * base and ctx.open_positions > 0:
        return _decide(False, REJECT_DAILY_LOSS)

    # 4 — total DD. Inazuia ENTRIES MPYA pekee; positions wazi hazifungwi.
    drawdown = float(cfg.get("base_balance")) - ctx.current_balance
    if drawdown >= float(cfg.get("max_total_dd")):
        return _decide(False, REJECT_MAX_TOTAL_DD)

    # 5 — max spread ya symbol
    max_spread = (cfg.get("max_spread", {}) or {}).get(ctx.symbol)
    if max_spread is not None and ctx.spread_pips > float(max_spread):
        return _decide(False, REJECT_MAX_SPREAD)

    # 6 — news
    if not bool(cfg.get("trade_news", True)) and ctx.news_imminent:
        return _decide(False, REJECT_NEWS)

    return _decide(True)
