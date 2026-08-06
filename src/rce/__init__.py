"""IDARA 1+2 — RISK & COST ENGINE (spec: docs/RISK_COST_ENGINE.md).

RCE inapokea **pendekezo** kutoka Idara 3 (KAIROS-1) na inatoa **trade tayari
kufunguliwa** au **REJECT + sababu**. Haiamui entry wala mwelekeo; model haiamui
ukubwa wala ruhusa (§4.3 ya KAIROS_1_STANDARD).

    budget -> risk/trade -> cost_pips -> lots -> viability gate

Kanuni mbili za module hii:

* **Spec HAIBADILIKI.** Kila formula hapa inatoka `docs/RISK_COST_ENGINE.md`
  neno kwa neno, na kila moja ina golden test yenye namba za spec yenyewe.
* **Hakuna kigezo kwenye code.** Vyote vinatoka `config/risk.yaml` na
  `config/broker_costs.yaml` (lango G10).
"""

from .budget import AccountState, BudgetResult, compute_budget
from .cost import CostBreakdown, compute_cost_pips, pip_size, spread_effective
from .gate import GateDecision, evaluate_gate
from .sizing import SizingResult, compute_lots

__all__ = [
    "AccountState",
    "BudgetResult",
    "compute_budget",
    "CostBreakdown",
    "compute_cost_pips",
    "pip_size",
    "spread_effective",
    "GateDecision",
    "evaluate_gate",
    "SizingResult",
    "compute_lots",
]
