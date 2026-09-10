"""Curve ya P&L ya portfolio kwa siku, katika vipimo vya R — DOCTRINE §7.2.

**Kitengo cha uchambuzi si trade. Ni siku ya portfolio.**

Toleo la kwanza lilipima t-statistic juu ya trades zilizokusanywa. Kwa hiyo
trades 33 zilizojilimbikiza kwenye miezi 2 zilihesabiwa kama uchunguzi 33,
wakati zilikuwa 2 hadi 6. Kila `p-value` ikawa anti-conservative kwa kiasi cha
`√(33/4) ≈ 2.9`.

Curve ya siku inaondoa kosa hilo kabisa:

* trades za siku moja zinajumlishwa kuwa **nambari moja**
* uhusiano kati ya symbols unashughulikiwa **kienyewe** — legs sita za F1
  zinakuwa siku moja, si uchunguzi sita
* block bootstrap juu ya mfululizo huu inashughulikia kujilimbikiza kwa muda

---

**Siku ni ya soko, si ya kalenda.** Mpaka ni **17:00 America/New_York** — ndipo
rollover inapotokea. Kutumia 00:00 UTC kungegawa siku katikati ya saa yenye
ukwasi mdogo kuliko zote.

---

**Siku HAI zinaripotiwa kando.** F1 inatrade mara moja kwa mwezi; curve yake ni
sifuri kwa siku 2,100 kati ya 2,151. Kusoma bootstrap kana kwamba ina uchunguzi
2,151 kungekuwa kudai nguvu isiyokuwepo. `n_active` inaandikwa kila mahali
`n` inapoandikwa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Sequence

from src.events.clock import siku_ya_soko


class CurveError(RuntimeError):
    """Curve haiwezi kujengwa kama ilivyoombwa."""


@dataclass(frozen=True)
class Curve:
    """Mfululizo wa R kwa siku, pamoja na ushahidi wa jinsi ulivyojengwa."""

    days: tuple[date, ...]
    r: tuple[float, ...]
    n_trades: tuple[int, ...]

    def __post_init__(self) -> None:
        if not (len(self.days) == len(self.r) == len(self.n_trades)):
            raise CurveError("urefu hautoshani")

    @property
    def n(self) -> int:
        """Siku zote za dirisha, ikiwa ni pamoja na zisizo na trade."""
        return len(self.days)

    @property
    def n_active(self) -> int:
        """Siku zenye trade. **Ndiyo ushahidi halisi**, si `n`."""
        return sum(1 for k in self.n_trades if k > 0)

    @property
    def total_r(self) -> float:
        return sum(self.r)

    @property
    def n_trades_total(self) -> int:
        return sum(self.n_trades)

    def values(self):
        import numpy as np

        return np.asarray(self.r, dtype=float)

    def active_values(self):
        """R za siku HAI pekee.

        Bootstrap inaendeshwa juu ya mfululizo **kamili** (sifuri zikiwemo), kwa
        sababu muundo wa muda ni sehemu ya kile kinachopimwa. Hii ni ya
        kuripoti na kuchunguza, si ya mtihani.
        """
        import numpy as np

        return np.asarray([x for x, k in zip(self.r, self.n_trades) if k > 0],
                          dtype=float)

    def render(self) -> str:
        return (f"CURVE · siku {self.n:,} (hai {self.n_active:,}) · "
                f"trades {self.n_trades_total:,} · R jumla {self.total_r:+.3f}")

    def to_json(self) -> dict[str, Any]:
        return {"n": self.n, "n_active": self.n_active,
                "n_trades": self.n_trades_total, "total_r": self.total_r,
                "days": [str(d) for d in self.days], "r": list(self.r)}


def daily_r(trades: Iterable[Any], *, days: Sequence[date] | None = None) -> Curve:
    """Trades → R kwa kila siku ya soko.

    R inaandikwa siku ya **kutoka**, si ya kuingia: ndipo P&L inapotimia.

    `days` ni dirisha kamili la utafiti. Ikitolewa, curve inapangwa juu yake na
    siku zisizo na trade zinajazwa **sifuri** — mwezi usio na trade ni mwezi
    wenye matokeo ya sifuri, si mwezi usiokuwepo (§ engine, 2026-08-26).
    """
    kwa_siku: dict[date, float] = {}
    hesabu: dict[date, int] = {}

    for t in trades:
        d = siku_ya_soko(t.exit_at)
        kwa_siku[d] = kwa_siku.get(d, 0.0) + float(t.r)
        hesabu[d] = hesabu.get(d, 0) + 1

    if days is None:
        mpangilio = sorted(kwa_siku)
    else:
        mpangilio = sorted(set(days) | set(kwa_siku))
        nje = sorted(set(kwa_siku) - set(days))
        if nje:
            raise CurveError(
                f"trades {len(nje)} ziko NJE ya dirisha lililotangazwa "
                f"({nje[0]} … {nje[-1]}) — R18 inadai kila hatua itangaze dirisha lake"
            )

    return Curve(
        days=tuple(mpangilio),
        r=tuple(kwa_siku.get(d, 0.0) for d in mpangilio),
        n_trades=tuple(hesabu.get(d, 0) for d in mpangilio),
    )


def combine(curves: Sequence[Curve]) -> Curve:
    """Curves za familia kadhaa → curve moja ya portfolio.

    Ni **kujumlisha kwa siku**, si kuunganisha. Familia mbili zinazotrade siku
    moja zinatoa nambari moja, kwa sababu ni siku moja ya portfolio.
    """
    if not curves:
        raise CurveError("hakuna curve ya kuunganisha")

    kwa_siku: dict[date, float] = {}
    hesabu: dict[date, int] = {}
    for c in curves:
        for d, x, k in zip(c.days, c.r, c.n_trades):
            kwa_siku[d] = kwa_siku.get(d, 0.0) + x
            hesabu[d] = hesabu.get(d, 0) + k

    mpangilio = sorted(kwa_siku)
    return Curve(days=tuple(mpangilio),
                 r=tuple(kwa_siku[d] for d in mpangilio),
                 n_trades=tuple(hesabu[d] for d in mpangilio))


__all__ = ["CurveError", "Curve", "daily_r", "combine"]
