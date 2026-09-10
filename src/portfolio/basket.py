"""Kikapu — kitengo cha nia ya kiuchumi, si leg — DOCTRINE §4, §6.

F1 inatoa **legs sita zilizosawazishwa kwa cross-section**: nafasi zinaundwa
ili jumla ya mwelekeo wa dola iwe karibu sifuri. Ni bet ya **uwiano** kati ya
sarafu, si bet ya mwelekeo wa dola.

Kwa hiyo leg moja ikikataliwa, iliyobaki **si F1 iliyopunguzwa** — ni strategy
nyingine, yenye mwelekeo wa dola usiokusudiwa. Na ikiwa leg inayokataliwa
inategemea kile kingine kilichofunguliwa kwenye akaunti, basi P&L ya F1
inakuwa **function ya vitu vingine visivyohusiana nayo**. Hilo linaharibu
uthibitisho kabisa.

Kipimo kilichoonyesha hilo (2026-09-07): leg dhaifu kuliko zote ilikataliwa
**99/99**, ikijilimbikizia kikapu kwenye ishara kali kuliko muundo unavyodai.

---

**Kikapu ni cha yote-au-hakuna.** Leg moja ikikataliwa, kikapu kizima
kinasimama. Gharama ni tukio zima; faida ni kwamba kile kinachopimwa ndicho
kilichotangazwa.

Hii inahitajika hata bila mgongano wa familia: `max_spread` ina kikomo kwa
EURUSD, GBPUSD, USDJPY na USDCHF, na spread inapanuka kwenye fix. Leg inaweza
kukataliwa **peke yake**, siku ambayo hakuna familia nyingine inayoendesha.

---

**`planned_exit_at` ni ya lazima.** Muundo mzima (§4.1) ni kutoka kwa **saa**:
sababu ya kiuchumi ina umri unaojulikana. Stop ni bima (§4.2), si mkakati.
Kutoka kwa saa hakupaswi kutegemea stop, na position isiyofungwa kwa wakati
wake ni **kasoro ya utekelezaji**, si tabia ya strategy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Sequence

from .regime import NORMAL, REGIMES

BUY = "BUY"
SELL = "SELL"


class BasketError(RuntimeError):
    """Kikapu hakiwezi kujengwa kama kilivyoombwa."""


@dataclass(frozen=True)
class Leg:
    """Mguu mmoja. `weight` ina ishara — ndiyo inayobeba mwelekeo."""

    symbol: str
    side: str
    sl_pips: float
    weight: float = 1.0
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.side.upper() not in (BUY, SELL):
            raise BasketError(f"upande si halali: {self.side!r}")
        if self.sl_pips <= 0:
            raise BasketError(
                f"`sl_pips` ni {self.sl_pips}; RCE inaigawanya, na lots "
                f"haziwezi kupatikana bila stop (§5)"
            )
        if not 0.0 < abs(self.weight) <= 1.0:
            raise BasketError(f"`weight` ni {self.weight}; inatakiwa 0 < |w| ≤ 1")

    @property
    def strength(self) -> float:
        return abs(self.weight)


@dataclass(frozen=True)
class Basket:
    """Nia moja ya kiuchumi, ikiwa na legs zake zote."""

    family: str
    basket_id: str
    legs: tuple[Leg, ...]
    entry_at: datetime
    planned_exit_at: datetime
    priority: int
    atomic: bool = True
    eligible_regimes: tuple[str, ...] = (NORMAL,)

    def __post_init__(self) -> None:
        if not self.legs:
            raise BasketError(f"{self.basket_id}: kikapu hakina leg hata moja")
        if self.planned_exit_at <= self.entry_at:
            raise BasketError(
                f"{self.basket_id}: `planned_exit_at` si baada ya `entry_at` — "
                f"§4.1 inadai kutoka kwa SAA, na saa lazima iwe ya mbeleni"
            )
        mbaya = set(self.eligible_regimes) - set(REGIMES)
        if mbaya:
            raise BasketError(f"regime hazijulikani: {sorted(mbaya)}")
        if not self.eligible_regimes:
            raise BasketError(
                f"{self.basket_id}: hakuna regime iliyotangazwa — familia "
                f"isiyotangaza haiendeshwi, na kimya si tangazo"
            )
        marudio = [s for s in self.symbols if self.symbols.count(s) > 1]
        if marudio:
            raise BasketError(
                f"{self.basket_id}: symbol imerudiwa ndani ya kikapu kimoja: "
                f"{sorted(set(marudio))}"
            )

    @property
    def symbols(self) -> list[str]:
        return [leg.symbol for leg in self.legs]

    @property
    def gross_weight(self) -> float:
        return sum(abs(leg.weight) for leg in self.legs)

    @property
    def net_weight(self) -> float:
        """Karibu sifuri kwa kikapu kilichosawazishwa. Inaripotiwa, si kudhaniwa."""
        return sum(leg.weight for leg in self.legs)

    def inastahili(self, regime: str) -> bool:
        return regime in self.eligible_regimes

    def render(self) -> str:
        aina = "atomiki" if self.atomic else "legs huru"
        return (f"{self.family}/{self.basket_id} · legs {len(self.legs)} ({aina}) · "
                f"{self.entry_at:%Y-%m-%d %H:%M}→{self.planned_exit_at:%H:%M} · "
                f"net {self.net_weight:+.3f} gross {self.gross_weight:.3f}")

    def to_json(self) -> dict[str, Any]:
        return {
            "family": self.family, "basket_id": self.basket_id,
            "priority": self.priority, "atomic": self.atomic,
            "eligible_regimes": list(self.eligible_regimes),
            "entry_at": self.entry_at.isoformat(),
            "planned_exit_at": self.planned_exit_at.isoformat(),
            "legs": [{"symbol": l.symbol, "side": l.side.upper(),
                      "sl_pips": l.sl_pips, "weight": l.weight}
                     for l in self.legs],
        }


# Toleo la sera ya uamuzi. **Kubadilika kwake ni mabadiliko ya strategy.**
# Inaingia kwenye hash ya portfolio ili sera mbili zisije zikaonekana moja.
ARBITRATION_POLICY_VERSION = "1.0.0"


def portfolio_hash(baskets: Sequence[Basket], *, regime: str,
                   rce_fingerprint: str = "") -> str:
    """Alama ya portfolio nzima pamoja na sera iliyoiunda.

    Kubadilisha kipaumbele cha familia, au atomiki ya kikapu, ni **uamuzi wa
    kujenga portfolio** — na uamuzi huo unabadilisha strategy inayopimwa.
    Bila alama hii, mabadiliko hayo yangeonekana kama matokeo tofauti ya soko.
    """
    payload = json.dumps({
        "policy": ARBITRATION_POLICY_VERSION,
        "regime": regime,
        "rce": rce_fingerprint,
        "baskets": [b.to_json() for b in
                    sorted(baskets, key=lambda x: (x.priority, x.basket_id))],
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def stale(positions: Iterable[Any], now: datetime) -> list[Any]:
    """Positions zilizopita `planned_exit_at` na bado ziko wazi.

    §4.1 — kutoka ni kwa saa. Position iliyobaki si tabia ya strategy; ni
    **kasoro ya utekelezaji**. Ikiachwa, inakula nafasi ya correlation ya
    kesho na kuchafua tathmini ya familia isiyohusiana nayo.

    Kwenye backtest hii lazima iwe **tupu daima**. Kwenye live ni kengele.
    """
    return [p for p in positions
            if getattr(p, "planned_exit_at", None) is not None
            and p.planned_exit_at <= now]


__all__ = ["BUY", "SELL", "BasketError", "Leg", "Basket",
           "ARBITRATION_POLICY_VERSION", "portfolio_hash", "stale"]
