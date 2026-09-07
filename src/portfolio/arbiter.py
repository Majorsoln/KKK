"""Safu ya uamuzi wa portfolio — DOCTRINE §6, R12.

**RCE haiguswi na haijui chochote kuhusu familia.** Safu hii iko JUU yake:

```
familia → vikapu → uamuzi wa portfolio → RCE → utekelezaji
```

Kazi yake si ruhusa ya hatari — hiyo ni ya RCE peke yake. Kazi yake ni
kugeuza **nia zinazoshindana kuwa portfolio MOJA inayotabirika**.

---

**Kitengo cha uamuzi ni KIKAPU, si leg.**

Kipimo cha 2026-09-07 kilionyesha kwa nini. Kupanga legs kwa nguvu ya ishara
kunaondoa utegemezi wa mpangilio wa kuwasili — lakini kunazalisha tatizo
kubwa zaidi: leg dhaifu kuliko zote inakataliwa **99/99**, na kikapu
kinachopimwa kinajilimbikizia ishara kali kuliko kilichotangazwa.

Suluhisho si mvunja-sare bora. Ni **kutopanga legs hata kidogo**. Vikapu
vinashindana vikiwa vizima:

```
1. regime ya kalenda    — familia isiyostahili leo haiendeshwi
2. kipaumbele kilichotangazwa
3. kikapu kizima kinaingia au kinakataliwa kizima
```

Kipaumbele kinatangazwa **kabla ya kuona matokeo**. F1 iko juu ya F0 si kwa
sababu ina faida zaidi — haijulikani — bali kwa sababu ina **matukio 99**
wakati F0 ina 4,302. Nafasi ya F1 haiwezi kubadilishwa; ya F0 inaweza.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Sequence

from .basket import Basket, portfolio_hash
from .regime import NORMAL

# Sababu za kukataa. Zinaandikwa kwenye ledger; hakuna "imekataliwa" bila moja.
REJECT_REGIME = "regime"
REJECT_ATOMIC = "atomic_leg_rejected"
REJECT_DUPLICATE = "symbol_already_held"


@dataclass(frozen=True)
class BasketVerdict:
    """Uamuzi kwa kikapu kizima, pamoja na ushahidi wake."""

    basket: Basket
    admitted: bool
    reason: str = ""
    failing_symbol: str = ""

    def render(self) -> str:
        if self.admitted:
            return f"{self.basket.family}/{self.basket.basket_id}  ✓ legs {len(self.basket.legs)}"
        wapi = f" ({self.failing_symbol})" if self.failing_symbol else ""
        return (f"{self.basket.family}/{self.basket.basket_id}  ✗ "
                f"{self.reason}{wapi} — kikapu KIZIMA kimesimama")

    def to_json(self) -> dict[str, Any]:
        return {"basket_id": self.basket.basket_id, "family": self.basket.family,
                "admitted": self.admitted, "reason": self.reason,
                "failing_symbol": self.failing_symbol,
                "n_legs": len(self.basket.legs)}


@dataclass
class Arbitration:
    """Matokeo ya uamuzi mmoja wa portfolio."""

    verdicts: list[BasketVerdict] = field(default_factory=list)
    regime: str = NORMAL
    hash: str = ""

    @property
    def admitted(self) -> list[Basket]:
        return [v.basket for v in self.verdicts if v.admitted]

    @property
    def symbols(self) -> list[str]:
        return [s for b in self.admitted for s in b.symbols]

    def render(self) -> str:
        lines = [f"PORTFOLIO · regime {self.regime} · hash {self.hash[:12]} · "
                 f"vikapu {len(self.admitted)}/{len(self.verdicts)}"]
        lines += ["   " + v.render() for v in self.verdicts]
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {"regime": self.regime, "hash": self.hash,
                "n_admitted": len(self.admitted),
                "verdicts": [v.to_json() for v in self.verdicts]}


def arbitrate(
    baskets: Sequence[Basket],
    *,
    gate: Callable[..., Any],
    cfg,
    regime: str = NORMAL,
    open_symbols: Sequence[str] = (),
    context: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> Arbitration:
    """Vikapu vinavyoshindana → portfolio moja inayotabirika.

    Kwa kila kikapu, kwa mpangilio wa kipaumbele:

    1. **Regime** — kisichostahili leo hakiendeshwi
    2. **Marudio** — symbol iliyoshikwa tayari inasimamisha kikapu; netting
       haijajengwa, na kufungua symbol ileile mara mbili ni kuhesabu hatari
       moja mara mbili
    3. **RCE** — legs zote zinapimwa. **Moja ikikataliwa, kikapu kizima
       kinasimama** ikiwa ni atomiki

    `gate` ni `rce.gate.evaluate_gate`. Haipewi maarifa yoyote ya familia.
    """
    from src.rce.gate import GateContext

    ziada = dict(context or {})
    wazi = list(open_symbols)
    out = Arbitration(
        regime=regime,
        hash=portfolio_hash(baskets, regime=regime,
                            rce_fingerprint=str(getattr(cfg, "config_hash", ""))),
    )

    # Kipaumbele kilichotangazwa; `basket_id` ni mvunja-sare wa uhakika pekee.
    for basket in sorted(baskets, key=lambda b: (b.priority, b.basket_id)):
        if not basket.inastahili(regime):
            out.verdicts.append(BasketVerdict(basket, False, REJECT_REGIME))
            continue

        marudio = [s for s in basket.symbols if s in wazi]
        if marudio:
            out.verdicts.append(BasketVerdict(
                basket, False, REJECT_DUPLICATE, failing_symbol=sorted(marudio)[0]))
            continue

        # Legs zinapimwa dhidi ya hali INAYOKUA — ndivyo RCE inavyofanya kazi.
        # Zinapimwa kwa mpangilio wa herufi ili jaribio liwe la kuzalishika;
        # mpangilio hauathiri jibu kwa kikapu atomiki, kwa sababu jibu ni
        # la kikapu kizima.
        jaribio = list(wazi)
        imeshindwa = ""
        sababu = ""
        for leg in sorted(basket.legs, key=lambda l: l.symbol):
            uamuzi = gate(cfg, GateContext(symbol=leg.symbol,
                                           open_positions=len(jaribio),
                                           open_symbols=tuple(jaribio),
                                           now=now, **ziada))
            if not uamuzi.passed:
                imeshindwa, sababu = leg.symbol, str(uamuzi.reason)
                break
            jaribio.append(leg.symbol)

        if imeshindwa and basket.atomic:
            out.verdicts.append(BasketVerdict(
                basket, False, f"{REJECT_ATOMIC}:{sababu}",
                failing_symbol=imeshindwa))
            continue
        if imeshindwa:
            # Kikapu kisicho atomiki: legs zilizopita zinabaki. Hakuna familia
            # ya mzunguko wa kwanza inayotumia hili, na ndiyo maana ni lazima
            # kutangazwa waziwazi (`atomic=False`) badala ya kuwa chaguo-msingi.
            out.verdicts.append(BasketVerdict(basket, True, f"partial:{sababu}",
                                              failing_symbol=imeshindwa))
            wazi = jaribio
            continue

        wazi = jaribio
        out.verdicts.append(BasketVerdict(basket, True))

    return out


__all__ = ["REJECT_REGIME", "REJECT_ATOMIC", "REJECT_DUPLICATE",
           "BasketVerdict", "Arbitration", "arbitrate"]
