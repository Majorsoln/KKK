"""RCE — mnyororo kamili wa spec (§ mchoro + §6), RCE-12.

```
1. BUDGET  (base → penalty → daily)
2. RISK/TRADE = budget ÷ max_open
3. COST_PIPS (spread + slip + comm + swap)
4. LOTS = risk ÷ ((SL + cost) × pipval)
5. VIABILITY GATE (checks 6)
```

**Hakuna signal queue (§5b, RCE-12).** `evaluate()` ni function safi: haihifadhi
pendekezo lolote, haina foleni, haina retry, na REJECT haina `retry_at` wala
njia ya kurudi. Setup ikiendelea kustahili bar inayofuata, KAIROS inatuma
**tathmini mpya** yenye bei mpya, spread mpya na gharama mpya — si ufufuo wa ile
ya zamani.

**Mamlaka (§UBORA ya spec):** RCE haiamui entry wala mwelekeo (hiyo ni Idara 3),
na haitoi hukumu ya ubora (EV/ratio). Inapokea pendekezo na kurudisha trade
tayari kufunguliwa au REJECT + sababu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

from .budget import AccountState, BudgetResult, compute_budget
from .config import RiskConfig
from .cost import CostBreakdown, CostRequest, RateLookup, compute_cost
from .gate import GateInputs, GateResult, evaluate_gate
from .lots import LotsResult, compute_lots
from .symbols import SymbolSpec, symbol_spec


@dataclass(frozen=True)
class Proposal:
    """Pendekezo kutoka Idara 3 (KAIROS-1) — RCE haiongezi wala kupunguza."""

    symbol: str
    direction: str
    entry: float
    sl_pips: float
    order_type: str
    entry_time: datetime
    tp_pips: float | None = None
    nights: float = 0.0
    dynamic_slippage_pips: float | None = None


@dataclass(frozen=True)
class Decision:
    """Jibu la RCE: trade tayari kufunguliwa, au REJECT + sababu."""

    approved: bool
    symbol: str
    direction: str
    lots: float
    risk_per_trade: float
    loss_at_sl: float
    reject_reason: str | None
    budget: BudgetResult
    cost: CostBreakdown | None
    lots_result: LotsResult | None
    gate: GateResult | None
    config_fingerprint: str
    warnings: list[str] = field(default_factory=list)

    @property
    def deviation_points(self) -> int | None:
        """`order.deviation` kwa POINTS (§3.2) — inatumwa na order."""
        return None if self.cost is None else self.cost.deviation_points

    def to_log(self) -> dict[str, object]:
        """Rekodi moja ya lifecycle (§5) — inayoenda log/dashboard."""
        record: dict[str, object] = {
            "lifecycle": "APPROVED" if self.approved else "REJECTED",
            "symbol": self.symbol,
            "direction": self.direction,
            "reason": self.reject_reason,
            "config_fingerprint": self.config_fingerprint,
            "budget": self.budget.to_log(),
            "warnings": self.warnings,
        }
        if self.cost is not None:
            record["cost"] = self.cost.to_log()
        if self.lots_result is not None:
            record["lots"] = self.lots_result.to_log()
        if self.gate is not None:
            record["gate"] = [
                {"name": c.name, "passed": c.passed, "reason": c.reason} for c in self.gate.checks
            ]
        return record


class RiskCostEngine:
    """Idara ya RISK & COST. Haina hali ya pendekezo — kila wito ni tathmini mpya."""

    def __init__(
        self,
        cfg: RiskConfig,
        rates: RateLookup = None,
        symbols: Mapping[str, SymbolSpec] | None = None,
    ) -> None:
        self.cfg = cfg
        self.rates = rates
        self._symbols = dict(symbols) if symbols else {}

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        """Sifa za broker: zilizotolewa moja kwa moja, au `broker_costs.yaml`."""
        if symbol in self._symbols:
            return self._symbols[symbol]
        return symbol_spec(self.cfg, symbol)

    def evaluate(
        self,
        proposal: Proposal,
        account: AccountState,
        spread_pips: float,
        open_symbols: Sequence[str] = (),
        news_soon: bool = False,
    ) -> Decision:
        """Mnyororo wa hatua 1–5. Hakuna athari ya kudumu popote (§5b)."""
        spec = self.symbol_spec(proposal.symbol)

        # 1–2: bajeti na risk kwa kila trade
        budget = compute_budget(account, self.cfg)

        # 3: gharama
        cost = compute_cost(
            CostRequest(
                symbol=spec,
                direction=proposal.direction,
                order_type=proposal.order_type,
                spread_pips=spread_pips,
                entry_time=proposal.entry_time,
                nights=proposal.nights,
                dynamic_slippage_pips=proposal.dynamic_slippage_pips,
            ),
            self.cfg,
            rates=self.rates,
        )

        # 4: lots
        lots = compute_lots(
            risk_per_trade=budget.risk_per_trade,
            sl_pips=proposal.sl_pips,
            cost=cost,
            symbol=spec,
        )
        if lots.rejected:
            return Decision(
                approved=False,
                symbol=proposal.symbol,
                direction=proposal.direction,
                lots=0.0,
                risk_per_trade=budget.risk_per_trade,
                loss_at_sl=0.0,
                reject_reason=lots.reason,
                budget=budget,
                cost=cost,
                lots_result=lots,
                gate=None,
                config_fingerprint=self.cfg.fingerprint,
            )

        # 5: viability gate
        gate = evaluate_gate(
            GateInputs(
                symbol=proposal.symbol,
                spread_pips=spread_pips,
                account=account,
                open_symbols=open_symbols,
                news_soon=news_soon,
            ),
            self.cfg,
            budget=budget,
        )
        return Decision(
            approved=gate.passed,
            symbol=proposal.symbol,
            direction=proposal.direction,
            lots=lots.lots if gate.passed else 0.0,
            risk_per_trade=budget.risk_per_trade,
            loss_at_sl=lots.loss_at_sl if gate.passed else 0.0,
            reject_reason=gate.reason,
            budget=budget,
            cost=cost,
            lots_result=lots,
            gate=gate,
            config_fingerprint=self.cfg.fingerprint,
            warnings=list(gate.warnings),
        )
