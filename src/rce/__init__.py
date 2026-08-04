"""RISK & COST ENGINE (RCE) — utekelezaji wa `docs/RISK_COST_ENGINE.md` KAMA ILIVYO.

Mtiririko wa idara hii (§ mchoro wa spec):

    pendekezo la model → 1. BUDGET → 2. RISK/TRADE → 3. COST_PIPS
                       → 4. LOTS → 5. VIABILITY GATE → PASS | REJECT + sababu

Sheria za idara:

* **Hakuna kigezo cha maamuzi kwenye code.** Kila namba inatoka `config/risk.yaml`
  (au `config/broker_costs.yaml` kwa namba za broker). Lango G10.
* **RCE haigundui ubora.** EV, ratio na uteuzi wa setup ni vya Idara 3 (KAIROS-1);
  RCE inatekeleza tu.
* **Hakuna signal queue** (§5b). Signal iliyokataliwa haihifadhiwi popote.
"""

__all__ = ["budget", "config", "cost", "engine", "fills", "gate", "lots", "symbols"]
