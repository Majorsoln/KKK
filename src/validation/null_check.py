"""Je null ni sahihi? — DOCTRINE §9.2, §9.7, R15.

Sakafu ya kelele inasimama juu ya dhana moja: data bandia ina **ugumu ule ule**
wa soko halisi, ikiwa imeondolewa utabirikaji pekee. Kipimo hiki ndicho
kinachoipima, na §9.7 kinaonyesha kwa nini si cha hiari — Calibration B ya
kwanza ilitumia saa 30 kupima sakafu ya soko lisilokuwepo.

---

**Muundo: generator ILE ILE, data TOFAUTI.**

```
seed ile ile ya generator  →  wagombea WALE WALE
                              ├── juu ya bars HALISI
                              └── juu ya surrogate za bars zile zile
```

Wagombea wakiwa wale wale, tofauti yoyote ya matokeo inatoka kwenye **data
pekee**.

---

**Hukumu ni PERCENTILE, si uwiano dhidi ya kizingiti.**

Uwiano wa wastani (`bandia ÷ halisi`) unahitaji mstari — "1.5× ni kubwa mno" —
ambao ni namba isiyopimwa, na §2 inaikataa. Percentile haihitaji chochote:

```
surrogate ngapi zilishindwa na data halisi?

   ~50%   halisi ni ya kawaida chini ya null. Null ni sahihi, LAKINI soko
          halionyeshi muundo unaozidi kelele kwa nafasi hii ya kutafuta.
   100%   soko lina muundo ambao null haina — ndicho kinachotafutwa.
     0%   null ni RAHISI kuliko soko. Sakafu ingekuwa juu kupita kiasi.
```

Azimio ni `1/(n+1)` kwa surrogate `n`. Kwa surrogate 3, "100%" ina nafasi ya
25% ya kutokea kwa bahati — si ushahidi, ni dokezo. Idadi inaripotiwa daima
pamoja na jibu, kwa sababu jibu bila azimio lake si jibu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import noise_floor as NF
from . import surrogates as S

# Metric yenye mamlaka (R17, §1.2) ndiyo inayoamua hukumu; nyingine ni taarifa.
MAMLAKA = "net_account_return_month"

VIPIMO = (MAMLAKA, "net_pips_month", "sharpe", "profitable_month_fraction",
          "profit_factor", "max_drawdown")

RAHISI = "bandia_ni_rahisi"
MUUNDO = "halisi_ina_muundo"
HAITOFAUTIKI = "haitofautiki"
HAKUNA = "hakuna_ulinganisho"


@dataclass(frozen=True)
class Run:
    """Utafutaji mmoja: juu ya data halisi au juu ya surrogate moja."""

    jina: str
    n_passed: int
    metrics: dict[str, float]
    seconds: float = 0.0

    @property
    def mamlaka(self) -> float:
        return float(self.metrics.get(MAMLAKA, float("nan")))

    def render(self) -> str:
        m = self.metrics
        return (
            f"{self.jina:<26} walipita §8.4 {self.n_passed:>4} · "
            f"return/mwezi {m.get(MAMLAKA, float('nan')):>8.4f} · "
            f"pips/mwezi {m.get('net_pips_month', float('nan')):>9.1f} · "
            f"sharpe {m.get('sharpe', float('nan')):>7.2f}  ({self.seconds:.0f}s)"
        )

    def to_json(self) -> dict[str, Any]:
        return {"jina": self.jina, "n_passed": self.n_passed,
                "metrics": self.metrics, "seconds": self.seconds}


@dataclass
class Comparison:
    """Data halisi dhidi ya surrogate zake, kwa symbol MOJA."""

    symbol: str
    timeframe: str
    n_bars: int
    n_candidates: int
    seed: int
    halisi: Run
    bandia: list[Run] = field(default_factory=list)

    # ---------------- hukumu ----------------

    @property
    def thamani_bandia(self) -> list[float]:
        """Metric yenye mamlaka ya kila surrogate iliyotoa mshindi, ikipangwa."""
        return sorted(r.mamlaka for r in self.bandia if r.mamlaka == r.mamlaka)

    @property
    def n_bandia(self) -> int:
        return len(self.thamani_bandia)

    @property
    def percentile(self) -> float:
        """Sehemu ya surrogate zilizoshindwa na data halisi. `NaN` bila kulinganishika."""
        b = self.thamani_bandia
        h = self.halisi.mamlaka
        if not b or h != h:
            return float("nan")
        return sum(1 for x in b if x < h) / len(b)

    @property
    def azimio(self) -> float:
        """Tofauti ndogo kuliko hii haiwezi kuonekana kwa surrogate zilizopo."""
        return 1.0 / (self.n_bandia + 1) if self.n_bandia else float("nan")

    @property
    def hukumu(self) -> str:
        pct = self.percentile
        if pct != pct:
            return HAKUNA
        if pct <= self.azimio:
            return RAHISI
        if pct >= 1.0 - self.azimio:
            return MUUNDO
        return HAITOFAUTIKI

    def uwiano(self) -> dict[str, float]:
        """`bandia (kati) ÷ halisi` kwa kila metric — TAARIFA, si hukumu."""
        out: dict[str, float] = {}
        for jina in VIPIMO:
            b = sorted(r.metrics.get(jina, float("nan")) for r in self.bandia
                       if r.metrics.get(jina, float("nan"))
                       == r.metrics.get(jina, float("nan")))
            h = self.halisi.metrics.get(jina, float("nan"))
            if not b or h != h or h == 0.0:
                continue
            out[jina] = b[len(b) // 2] / h
        return out

    # ---------------- kuripoti ----------------

    def render(self) -> str:
        lines = [self.halisi.render()] + [r.render() for r in self.bandia]
        pct = self.percentile
        if pct != pct:
            lines.append(
                f"   HAKUNA ULINGANISHO · washindi: halisi "
                f"{self.halisi.n_passed}, bandia {self.n_bandia}"
            )
            return "\n".join(lines)

        b = self.thamani_bandia
        lines += [
            f"   surrogate: {' · '.join(f'{x:.4f}' for x in b)}",
            f"   halisi:    {self.halisi.mamlaka:.4f}  →  imezidi "
            f"{int(pct * len(b))}/{len(b)} = {pct:.0%}  (azimio ±{self.azimio:.0%})",
            f"   {UJUMBE[self.hukumu]}",
        ]
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "timeframe": self.timeframe,
            "n_bars": self.n_bars, "n_candidates": self.n_candidates,
            "seed": self.seed,
            "halisi": self.halisi.to_json(),
            "bandia": [r.to_json() for r in self.bandia],
            "percentile": self.percentile, "azimio": self.azimio,
            "uwiano": self.uwiano(), "hukumu": self.hukumu,
        }


UJUMBE = {
    RAHISI: ("NULL NI RAHISI KULIKO SOKO — sakafu ingekuwa juu kupita kiasi "
             "(§9.7)"),
    MUUNDO: "SOKO LINA MUUNDO AMBAO NULL HAINA — ndicho kinachotafutwa",
    HAITOFAUTIKI: ("HAITOFAUTIKI — halisi iko NDANI ya mgawanyo wa surrogate; "
                   "hakuna muundo unaozidi kelele"),
    HAKUNA: "HAKUNA ULINGANISHO — upande usio na mshindi hauwezi kulinganishwa",
}


# ===========================================================================
# Kipimo
# ===========================================================================


def compare(bars, spec, *, cfg_risk, seed: int, n_surrogate_seeds: int = 2,
            families=S.FAMILIES, starting_balance: float = 10_000.0,
            run_search: Callable | None = None,
            progress: Callable[[str], None] | None = None) -> Comparison:
    """Endesha wagombea WALE WALE juu ya bars halisi na juu ya surrogate zake.

    `run_search` ni kwa ajili ya tests pekee — inaruhusu kubadilisha utafutaji
    halisi na wa bandia bila kuendesha pipeline nzima.
    """
    import time

    from src.discovery import pipeline as P

    tafuta = run_search or (
        lambda frame: P.search(frame, spec, cfg_risk=cfg_risk, seed=seed,
                               starting_balance=starting_balance))

    def moja(frame, jina: str) -> Run:
        t0 = time.time()
        out = tafuta(frame)
        m = out.metrics()
        r = Run(jina=jina, n_passed=out.n_passed_economics,
                metrics={k: float(m.get(k, float("nan"))) for k in VIPIMO},
                seconds=time.time() - t0)
        if progress:
            progress("   " + r.render())
        return r

    halisi = moja(bars, "HALISI")

    bandia: list[Run] = []
    for fam in families:
        for i in range(max(1, n_surrogate_seeds)):
            sur = S.make(bars, fam, seed=NF._seed_of(seed, fam, i))
            bandia.append(moja(sur.frame, f"{fam} #{i}"))

    return Comparison(
        symbol=spec.symbol, timeframe=spec.timeframe, n_bars=int(len(bars)),
        n_candidates=spec.n_candidates, seed=seed, halisi=halisi, bandia=bandia,
    )


def rank(comparisons) -> list[Comparison]:
    """Symbols zilizopangwa kwa percentile — ya juu kwanza.

    `NaN` (bila ulinganisho) zinaenda mwisho: symbol isiyoweza kupimwa si
    symbol iliyofeli, lakini pia si mahali pa kuanzia.
    """
    def ufunguo(c: Comparison):
        pct = c.percentile
        return (0 if pct == pct else 1, -(pct if pct == pct else 0.0))

    return sorted(comparisons, key=ufunguo)


def render_table(comparisons) -> str:
    """Jedwali moja la symbols zote — ndilo linaloamua wapi pa kutafuta."""
    lines = [
        f"{'symbol':<9} {'TF':<4} {'halisi':>9} {'bandia kati':>12} "
        f"{'percentile':>11} {'azimio':>7}  hukumu",
    ]
    for c in rank(comparisons):
        pct = c.percentile
        b = c.thamani_bandia
        kati = b[len(b) // 2] if b else float("nan")
        pct_str = f"{pct:.0%}" if pct == pct else "—"
        azimio_str = f"±{c.azimio:.0%}" if c.azimio == c.azimio else "—"
        h = c.halisi.mamlaka
        h_str = f"{h:.4f}" if h == h else "—"
        kati_str = f"{kati:.4f}" if kati == kati else "—"
        lines.append(
            f"{c.symbol:<9} {c.timeframe:<4} {h_str:>9} "
            f"{kati_str:>12} {pct_str:>11} {azimio_str:>7}  {c.hukumu}"
        )
    return "\n".join(lines)
