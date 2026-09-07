"""Proposals za wakati mmoja — DOCTRINE §11, R12.

`evaluate_gate` ya RCE haina hali: inapewa `open_positions` na `open_symbols`
za sasa, na inaamua. Ni sahihi.

Lakini familia zetu zinatoa proposals **kadhaa kwa timestamp moja**. F1 inaingia
kwenye majors sita kwa dakika ile ile. `max_open_trades = 7` na
`max_correlated = 3` zinamaanisha baadhi zitakataliwa — na **zipi** inategemea
nani amefika kwanza.

```
mpangilio A: EURUSD ✓ GBPUSD ✓ AUDUSD ✓ NZDUSD ✗ (USD_group imejaa)
mpangilio B: NZDUSD ✓ AUDUSD ✓ GBPUSD ✓ EURUSD ✗
```

Backtest ile ile, jibu tofauti. Na kwa kuwa mpangilio unatokana na jinsi
orodha ilivyojengwa kwenye kumbukumbu, si kwa kitu chochote cha soko, hilo ni
**matokeo yasiyoweza kuzalishwa upya** — na hakuna kinachoonyesha.

---

**Suluhisho si kubadilisha RCE.** RCE ni mamlaka ya ruhusa (R12) na haina
kasoro hapa. Suluhisho ni **mpangilio uliotangazwa** kwa anayeiendesha:

```
1. nguvu ya ishara ikishuka        — nafasi chache zikipatikana, bora kwanza
2. symbol kwa herufi               — kuvunja sare
3. jina la familia                 — kuvunja sare iliyobaki
```

Sheria hii inaandikwa kwenye ledger kama sehemu ya ufafanuzi wa run. Ni
uamuzi wa kiuchumi (chukua ishara bora nafasi zikiwa chache), si wa kiufundi,
kwa hiyo lazima itangazwe — vinginevyo ingekuwa parameter iliyofichwa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


class BatchError(RuntimeError):
    """Kundi la proposals haliwezi kuchakatwa kama lilivyoombwa."""


@dataclass(frozen=True)
class Proposal:
    """Ombi la kuingia, kabla ya RCE kuamua chochote."""

    symbol: str
    side: str
    strength: float                 # `f(ishara)` ∈ [0, 1] — §5.1
    family: str
    sl_pips: float
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.strength <= 1.0:
            raise BatchError(
                f"`strength` ni {self.strength}; §5.1 inadai [0,1] — nguvu "
                f"inapunguza HATARI, si lots moja kwa moja"
            )
        if self.sl_pips <= 0:
            raise BatchError(
                f"`sl_pips` ni {self.sl_pips}; RCE inaigawanya, na lots "
                f"haziwezi kupatikana bila stop (§5)"
            )


@dataclass(frozen=True)
class Admission:
    """Uamuzi kwa proposal moja, pamoja na hali ilipofika."""

    proposal: Proposal
    accepted: bool
    reason: str = ""
    open_before: int = 0

    def render(self) -> str:
        alama = "✓" if self.accepted else f"✗ {self.reason}"
        return (f"{self.proposal.family}/{self.proposal.symbol} "
                f"{self.proposal.side} {alama}")


# Ufunguo wa mpangilio uliotangazwa. Umeandikwa hapa MARA MOJA ili usije
# ukabadilika kimya kwenye familia moja.
def _ufunguo(p: Proposal) -> tuple[float, str, str]:
    return (-p.strength, p.symbol, p.family)


def panga(proposals: Sequence[Proposal]) -> list[Proposal]:
    """Mpangilio uliotangazwa. **Hauna nasibu na hautegemei mpangilio wa kuingia.**"""
    return sorted(proposals, key=_ufunguo)


def admit(
    proposals: Sequence[Proposal],
    *,
    gate: Callable[..., Any],
    cfg,
    open_symbols: Sequence[str] = (),
    context: dict[str, Any] | None = None,
) -> list[Admission]:
    """Pitisha kundi kupitia RCE kwa mpangilio uliotangazwa.

    `gate` ni `rce.gate.evaluate_gate` (au kitu chenye sahihi ile ile).
    Inaitwa mara moja kwa kila proposal, hali ikisasishwa kwa iliyokubaliwa —
    ndivyo RCE inavyofanya kazi kwa vitendo.

    Matokeo yanarudishwa kwa **mpangilio uliotangazwa**, si wa kuingia, ili
    ripoti nayo isitegemee jinsi orodha ilivyojengwa.
    """
    from src.rce.gate import GateContext

    ziada = dict(context or {})
    wazi = list(open_symbols)
    out: list[Admission] = []

    for p in panga(proposals):
        ctx = GateContext(
            symbol=p.symbol,
            open_positions=len(wazi),
            open_symbols=tuple(wazi),
            **ziada,
        )
        uamuzi = gate(cfg, ctx)
        if uamuzi.passed:
            wazi.append(p.symbol)
        out.append(Admission(
            proposal=p,
            accepted=bool(uamuzi.passed),
            reason=str(uamuzi.reason),
            open_before=len(wazi) - (1 if uamuzi.passed else 0),
        ))
    return out


def waliokubaliwa(admissions: Sequence[Admission]) -> list[Proposal]:
    return [a.proposal for a in admissions if a.accepted]


__all__ = ["BatchError", "Proposal", "Admission", "panga", "admit",
           "waliokubaliwa"]
