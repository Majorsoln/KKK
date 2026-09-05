"""Hatua ya kwanza ya utekelezaji — RCE CHECK (DOCTRINE §11.1, R12, R19).

Backtest **haihesabu** ruhusa, bajeti, wala ukubwa. Inaita RCE na kurekodi
jibu lake. Ni R12: RCE ndiyo mamlaka, na mamlaka isiyoitwa si mamlaka.

Kazi ya moduli hii ni ndogo kwa makusudi: kugeuza `TradeOrder` ya RCE kuwa
`Attempt` ya ledger, ikiwa na safu za ukaguzi zilizotajwa §11.2. Sehemu pekee
inayoongeza maana ni kutofautisha `NO_BUDGET` na `MIN_LOT_REJECT` — tofauti
ambayo RCE haiitoi kwa sababu haihitaji, lakini uchunguzi unaihitaji.
"""

from __future__ import annotations

from typing import Any

from src.rce.engine import MarketContext, Proposal, evaluate
from src.rce.sizing import REJECT_BELOW_MIN_LOT

from .ledger import MIN_LOT_REJECT, NO_BUDGET, PASS, Attempt


def classify(order, budget_value: float) -> str:
    """Jibu la RCE → tokeo la ledger.

    RCE inatoa `risk_below_min_lot` kwa hali MBILI tofauti:

    * bajeti imekwisha kabisa (drawdown imeila) → lots ni 0
    * bajeti ipo, lakini akaunti ni ndogo kwa symbol hii → lots ni 0.007

    Ya kwanza ni mfumo uliofungwa; ya pili ni ukubwa wa akaunti. Kuzichanganya
    kungeficha tofauti kati ya *"strategy imezidi hatari"* na *"akaunti ni ndogo
    mno kwa symbol hii"* — matibabu yake ni tofauti kabisa.
    """
    if order.approved:
        return PASS
    if order.reason == REJECT_BELOW_MIN_LOT:
        return NO_BUDGET if budget_value <= 0 else MIN_LOT_REJECT
    return order.reason


def check(cfg, proposal: Proposal, ctx: MarketContext, *, signal_time: Any,
          requested_price: float | None = None) -> Attempt:
    """Endesha RCE kwa signal moja, rudisha `Attempt` isiyo na hatua ya pili.

    Hatua ya pili (`EXECUTION`) inajazwa na engine ya path baada ya hii —
    ikiwa `attempt.approved` ni `True`. Signal isiyopita RCE **haifiki**
    utekelezaji, na `execution_outcome` yake inabaki `None`. Hilo si pengo;
    ni ukweli: haikuwahi kuwa order.
    """
    order = evaluate(cfg, proposal, ctx)

    budget_value = float(order.budget.budget) if order.budget is not None else 0.0
    risk = float(order.budget.risk_per_trade) if order.budget is not None else 0.0
    requested = float(order.sizing.lots_raw) if order.sizing is not None else 0.0

    return Attempt(
        signal_time=signal_time,
        symbol=proposal.symbol,
        direction=proposal.direction,
        requested_price=float(
            requested_price if requested_price is not None else proposal.entry
        ),
        rce_outcome=classify(order, budget_value),
        budget_at_signal=budget_value,
        risk_per_trade_at_signal=risk,
        requested_lots=requested,
        allowed_lots=float(order.lots),
        broker_min_lot=float(ctx.spec.volume_min),
        cost_pips=float(order.cost.cost_pips) if order.cost is not None else 0.0,
    )
