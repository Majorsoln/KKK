"""RCE end-to-end: pendekezo la KAIROS-1 → trade tayari, au REJECT + sababu.

```
Idara 3 (model) ──► pendekezo: symbol, dir, entry, SL, TP
                         │
                    ┌────▼──────────────────────────────────┐
                    │ 1. BUDGET  (base → penalty → daily)    │
                    │ 2. RISK/TRADE = budget ÷ max_open      │
                    │ 3. COST_PIPS (spread+slip+comm+swap)   │
                    │ 4. LOTS = risk ÷ ((SL+cost) × pipval)  │
                    │ 5. VIABILITY GATE (checks 6)           │
                    └────┬───────────────────────────────────┘
              PASS ──────┴────── REJECT + sababu → log/dashboard
```

Mgawanyo wa mamlaka (§4.3 ya KAIROS_1_STANDARD) unatekelezwa kwa muundo:
`Proposal` ina entry/SL/TP/EV (**model inaamua**) na haina lots wala ruhusa;
`TradeOrder` ina lots + deviation (**RCE inaamua**) na hairudi kubadilisha
entry wala mwelekeo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .budget import AccountState, BudgetResult, compute_budget
from .cost import (
    CostBreakdown,
    SymbolSpec,
    commission_pips,
    order_deviation_points,
    slippage_cap_pips,
    spread_effective,
    swap_pips,
)
from .gate import GateContext, GateDecision, evaluate_gate
from .sizing import SizingResult, compute_lots


@dataclass(frozen=True)
class Proposal:
    """Pendekezo la KAIROS-1 (§4.1). RCE **haibadilishi** kilichomo hapa."""

    symbol: str
    direction: str  # BUY / SELL
    entry: float
    sl_pips: float
    tp_pips: float
    order_type: str = "market"  # market / stop / limit
    ev_signal: float | None = None
    ev_final: float | None = None
    p_tp_first: float | None = None
    p_fill: float | None = None
    quality: str | None = None
    strategy: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class MarketContext:
    """Muktadha wa soko/akaunti wakati wa uamuzi. Vyote vinatoka broker."""

    account: AccountState
    spec: SymbolSpec
    h1_spreads: list[float]
    m5_spreads: list[float]
    pip_value_acct: float
    commission_round_turn: float
    open_symbols: tuple[str, ...] = ()
    nights: float = 0.0
    triple_nights: float = 0.0
    m5_slippage_estimate: float | None = None
    news_imminent: bool = False
    now: datetime | None = None


@dataclass(frozen=True)
class TradeOrder:
    """Trade tayari kufunguliwa — au REJECT yenye sababu."""

    proposal: Proposal
    approved: bool
    reason: str = ""
    lots: float = 0.0
    deviation_points: int = 0
    budget: BudgetResult | None = None
    cost: CostBreakdown | None = None
    sizing: SizingResult | None = None
    gate: GateDecision | None = None

    def render(self) -> str:
        if not self.approved:
            return f"REJECT {self.proposal.symbol} ({self.reason})"
        return (
            f"PASS {self.proposal.symbol} {self.proposal.direction} "
            f"lots={self.lots:.2f} deviation={self.deviation_points}pt · "
            f"{self.cost.render() if self.cost else ''}"
        )

    def to_log(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": self.proposal.symbol,
            "direction": self.proposal.direction,
            "approved": self.approved,
            "reason": self.reason,
            "lots": self.lots,
        }
        if self.gate is not None:
            payload.update(self.gate.to_log())
        if self.cost is not None:
            payload["cost_pips"] = self.cost.cost_pips
        return payload


def evaluate(cfg, proposal: Proposal, ctx: MarketContext) -> TradeOrder:
    """Hatua tano za §0 kwa mpangilio wake.

    **`cost_pips` inahesabiwa MARA MOJA hapa** na inatumika kwa sizing. Ni namba
    ile ile inayorudishwa kwa model kama muktadha (§4.2 ya KAIROS-1) — chanzo
    kimoja, matumizi mawili, hakuna kutofautiana.
    """
    budget = compute_budget(cfg, ctx.account)

    spread = spread_effective(ctx.h1_spreads, ctx.m5_spreads, cfg)
    slippage = slippage_cap_pips(proposal.order_type, cfg, ctx.m5_slippage_estimate)
    cost = CostBreakdown(
        spread_pips=spread,
        slippage_pips=slippage,
        commission_pips=commission_pips(ctx.commission_round_turn, ctx.pip_value_acct),
        swap_pips=(
            swap_pips(
                proposal.direction,
                ctx.spec,
                ctx.nights,
                ctx.pip_value_acct,
                ctx.triple_nights,
            )
            if ctx.nights > 0
            else 0.0
        ),
    )

    sizing = compute_lots(
        risk_per_trade=budget.risk_per_trade,
        sl_pips=proposal.sl_pips,
        cost_pips=cost.cost_pips,
        pip_value_acct=ctx.pip_value_acct,
        spec=ctx.spec,
    )

    gate = evaluate_gate(
        cfg,
        GateContext(
            symbol=proposal.symbol,
            open_positions=ctx.account.open_positions,
            open_symbols=ctx.open_symbols,
            current_balance=ctx.account.current_balance,
            today_loss=ctx.account.today_loss,
            spread_pips=spread,
            news_imminent=ctx.news_imminent,
            now=ctx.now,
        ),
    )

    if sizing.rejected:
        return TradeOrder(
            proposal=proposal,
            approved=False,
            reason=sizing.reason,
            budget=budget,
            cost=cost,
            sizing=sizing,
            gate=gate,
        )
    if not gate.passed:
        return TradeOrder(
            proposal=proposal,
            approved=False,
            reason=gate.reason,
            budget=budget,
            cost=cost,
            sizing=sizing,
            gate=gate,
        )

    return TradeOrder(
        proposal=proposal,
        approved=True,
        lots=sizing.lots,
        deviation_points=order_deviation_points(slippage, proposal.symbol, ctx.spec.point),
        budget=budget,
        cost=cost,
        sizing=sizing,
        gate=gate,
    )


def cost_context_for_model(cfg, ctx: MarketContext, order_type: str = "market") -> dict[str, float]:
    """RCE → KAIROS-1 (§4.2): `cost_pips` + spread ya sasa + slots zilizobaki.

    Model **haihesabu** gharama yake; inapokea hii. Ni namba ile ile
    inayotumika kwenye sizing — ndiyo maana function hii iko hapa, si kwa model.
    """
    spread = spread_effective(ctx.h1_spreads, ctx.m5_spreads, cfg)
    slippage = slippage_cap_pips(order_type, cfg, ctx.m5_slippage_estimate)
    cost = CostBreakdown(
        spread_pips=spread,
        slippage_pips=slippage,
        commission_pips=commission_pips(ctx.commission_round_turn, ctx.pip_value_acct),
        swap_pips=0.0,
    )
    budget = compute_budget(cfg, ctx.account)
    return {
        "cost_pips": cost.cost_pips,
        "spread_pips": spread,
        "budget": budget.budget,
        "risk_per_trade": budget.risk_per_trade,
        "slots_remaining": max(
            0, int(cfg.get("max_open_trades")) - ctx.account.open_positions
        ),
    }
