"""Sifa ya symbol — malango matatu ya §6 (uamuzi wa PD 2026-09-07).

> Si "symbol zote kwenye familia zote". Kila symbol inaingia kwenye familia
> inayoifaa — na "inayoifaa" ni kitu kinachopimwa KABLA, si kinachochaguliwa
> baada.

```
6.1  sababu     mekanizimu unahusika na symbol hii?      (imeandikwa)
6.2  gharama    gharama_RT ≤ 8% × σ(dirisha)             (imepimwa)
6.3  mzunguko   n ≥ (t*/s)²                              (imehesabiwa)
```

Yote matatu lazima yapite. Symbol iliyokataliwa **haiingii kwenye hesabu ya
majaribio wala kwenye pooling** — kwa hiyo kuikataa hakugharimu α, na kuiingiza
kunagharimu. Ndiyo maana uamuzi unafanywa kabla ya kuona `p` yoyote.

---

**Kwa nini 8%.** Kwa ishara yenye utabirikaji halisi wa FX, uwiano wa ishara
kwa kelele kwa tukio ni mdogo: `μ/σ` ya utaratibu wa 0.05–0.15. Edge ya jumla
ni sehemu ndogo ya `σ` ya dirisha. Gharama inayokula zaidi ya 8% ya `σ`
inakula sehemu kubwa ya edge inayowezekana kabla ya kipimo chochote kuanza —
si kwamba haiwezekani kushinda, ni kwamba **hatuwezi kuipima** kwa sampuli
tuliyo nayo.

**Kwa nini `n ≥ (t*/s)²`.** `t = s·√n` kwa Sharpe-kwa-tukio `s`. Kufikia
`t*` kunahitaji `n ≥ (t*/s)²`. Lango hili linazuia kitu kimoja: kuendesha
familia ambayo, hata kama mekanizimu ni wa kweli kabisa kwa ukubwa
uliotangazwa, **haiwezi kufikia kizingiti** kwa matukio iliyo nayo. Kufeli
hapa si "hakuna edge" — ni "hakuna jibu", na jibu ndilo lengo (§12).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

# §6.2 — gharama kama sehemu ya σ ya dirisha la kushikilia.
COST_BUDGET = 0.08

# §9 — majaribio 8 kwenye α = 0.020 → 0.0025 → z ≈ 2.81.
Z_STAR = 2.81


class QualifyError(RuntimeError):
    """Lango haliwezi kupimwa kama lilivyoombwa."""


@dataclass(frozen=True)
class Gate:
    """Lango moja, na namba iliyolipitisha au kulikataa."""

    name: str
    passed: bool
    measured: float
    limit: float
    note: str = ""

    def render(self) -> str:
        alama = "PITA" if self.passed else "KATAA"
        return (f"   {alama:<5} {self.name:<12} "
                f"{self.measured:>10.4g} dhidi ya {self.limit:<10.4g} {self.note}")

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed,
                "measured": self.measured, "limit": self.limit, "note": self.note}


@dataclass(frozen=True)
class Qualification:
    """Jibu la `(familia, symbol)` — ndani au nje, pamoja na sababu."""

    family: str
    symbol: str
    gates: tuple[Gate, ...]

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.gates)

    @property
    def failed(self) -> list[str]:
        return [g.name for g in self.gates if not g.passed]

    def render(self) -> str:
        kichwa = (f"{self.family} × {self.symbol}: "
                  f"{'INAINGIA' if self.passed else 'HAIINGII'}")
        if not self.passed:
            kichwa += f" (imekwama: {', '.join(self.failed)})"
        return "\n".join([kichwa] + [g.render() for g in self.gates])

    def to_json(self) -> dict[str, Any]:
        return {"family": self.family, "symbol": self.symbol,
                "passed": self.passed, "failed": self.failed,
                "gates": [g.to_json() for g in self.gates]}


def required_events(sharpe_per_event: float, *, z_star: float = Z_STAR) -> int:
    """`(t*/s)²` — matukio machache kabisa yanayoweza kufikia kizingiti."""
    if sharpe_per_event <= 0:
        raise QualifyError(
            f"Sharpe-kwa-tukio ni {sharpe_per_event}; lango la mzunguko "
            f"halina maana kwa familia isiyotangaza edge chanya"
        )
    return math.ceil((z_star / sharpe_per_event) ** 2)


def qualify(
    family: str,
    symbol: str,
    *,
    mechanism_ok: bool,
    mechanism_note: str,
    cost_pips: float,
    sigma_pips: float,
    n_events: int,
    sharpe_per_event: float,
    cost_budget: float = COST_BUDGET,
    z_star: float = Z_STAR,
) -> Qualification:
    """Malango matatu ya §6, kwa namba **zilizopimwa**.

    `cost_pips` ni gharama ya round-turn kutoka RCE (spread + commission +
    slippage + swap). `sigma_pips` ni mtawanyiko wa mwendo wa **dirisha la
    kushikilia**, si wa siku — dirisha la saa 4 lina `σ` ndogo kuliko la saa
    24, na kutumia ya siku kungefanya kila symbol ipite kimya.
    """
    if sigma_pips <= 0:
        raise QualifyError(
            f"{family}×{symbol}: σ ya dirisha ni {sigma_pips}. Lango la "
            f"gharama linaigawanya; bila kipimo halisi hakuna uamuzi"
        )
    if cost_pips < 0:
        raise QualifyError(f"{family}×{symbol}: gharama hasi ({cost_pips})")
    if n_events < 0:
        raise QualifyError(f"{family}×{symbol}: matukio hasi ({n_events})")

    uwiano = cost_pips / sigma_pips
    lazima = required_events(sharpe_per_event, z_star=z_star)

    gates = (
        Gate(name="sababu", passed=bool(mechanism_ok),
             measured=1.0 if mechanism_ok else 0.0, limit=1.0,
             note=mechanism_note),
        Gate(name="gharama", passed=uwiano <= cost_budget,
             measured=uwiano, limit=cost_budget,
             note=f"gharama {cost_pips:.2f}p · σ {sigma_pips:.2f}p"),
        Gate(name="mzunguko", passed=n_events >= lazima,
             measured=float(n_events), limit=float(lazima),
             note=f"s {sharpe_per_event:.4f} · t* {z_star}"),
    )
    return Qualification(family=family, symbol=symbol, gates=gates)


def table(qualifications: Sequence[Qualification]) -> str:
    """Jedwali la sifa: familia × symbols → ndani/nje (§6)."""
    mistari = [f"{'familia':<8} {'symbol':<10} {'jibu':<10} sababu"]
    mistari.append("-" * 60)
    for q in sorted(qualifications, key=lambda x: (x.family, x.symbol)):
        jibu = "INAINGIA" if q.passed else "HAIINGII"
        mistari.append(f"{q.family:<8} {q.symbol:<10} {jibu:<10} "
                       f"{', '.join(q.failed) if q.failed else '—'}")
    return "\n".join(mistari)


__all__ = ["COST_BUDGET", "Z_STAR", "QualifyError", "Gate", "Qualification",
           "required_events", "qualify", "table"]
