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

Percentile peke yake haitoshi kupanga symbols: `3/3` na `6/6` zote ni 100%,
lakini ya kwanza ina nafasi ya **25%** ya kutokea kwa bahati na ya pili **14%**.
`p_value` = `(n − k + 1) ÷ (n + 1)` inajumuisha vyote viwili, na ndiyo
inayotumika kupanga.

---

**§9.1 inarudi kwenye ngazi ya symbols.**

Kadri unavyopima symbols nyingi, ndivyo bora kati yao inavyoonekana nzuri hata
kama hakuna hata moja yenye muundo. Symbols 12 zikipimwa, **matarajio ya
kupata moja yenye `p = 0.14` kwa bahati ni 1.7**. Symbol moja hiyo si ugunduzi;
ni kile null inachokitoa.

`expected_by_chance()` inahesabu hilo, na scan inaripoti daima. Kuchuja bila
namba hiyo ni kufanya §9.1 mara ya pili baada ya kujenga mfumo mzima wa
kuiepuka.
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
    def p_value(self) -> float:
        """Nafasi ya kupata cheo hiki — au bora zaidi — kwa BAHATI.

        Chini ya null, data halisi ni mojawapo ya `n+1` zinazoweza kupangwa kwa
        mpangilio wowote. Ikizidi `k` kati ya `n`, nafasi ya kufika hapo au juu
        zaidi ni `(n − k + 1) ÷ (n + 1)`.

        **Hii ndiyo namba ya kupanga symbols, si percentile.** Percentile
        peke yake inasema `3/3` na `6/6` ni sawa — zote 100% — wakati ya kwanza
        ina nafasi ya 25% ya kutokea kwa bahati na ya pili 14%. Ushahidi si
        kile kilichoonekana pekee; ni pamoja na ni mara ngapi ungeweza
        kuonekana bila kuwepo.
        """
        b = self.thamani_bandia
        h = self.halisi.mamlaka
        if not b or h != h:
            return float("nan")
        k = sum(1 for x in b if x < h)
        return (len(b) - k + 1) / (len(b) + 1)

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

    def percentile_ya(self, jina: str) -> float:
        """Percentile ya metric YOYOTE, si ya mamlaka pekee.

        Hukumu inatoka kwa `MAMLAKA` (R17), lakini vipimo vingine vinaeleza
        **aina** ya tofauti. GBPUSD (§9.8) ilizidi surrogate zote kwenye
        `net_account_return_month` mara mbili, wakati `sharpe` haikurudia na
        `max_drawdown` ilikuwa mbaya mara 7 — yaani tofauti iko kwenye faida
        ghafi, si kwenye ubora. Bila percentile kwa kila metric, tofauti hiyo
        ingehitaji kuhesabiwa kwa mkono.

        `max_drawdown` ni `WORSE`: percentile inahesabu surrogate zilizo na DD
        KUBWA kuliko halisi, ili "juu" imaanishe "bora" kwa vipimo vyote.
        """
        chini_ni_bora = jina == "max_drawdown"
        b = [r.metrics.get(jina, float("nan")) for r in self.bandia]
        b = [x for x in b if x == x]
        h = self.halisi.metrics.get(jina, float("nan"))
        if not b or h != h:
            return float("nan")
        bora = sum(1 for x in b if (x > h) is chini_ni_bora)
        return bora / len(b)

    def kwa_kila_metric(self) -> dict[str, float]:
        """Percentile ya kila metric — TAARIFA inayoeleza aina ya tofauti."""
        return {jina: self.percentile_ya(jina) for jina in VIPIMO}

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
            f"{int(pct * len(b))}/{len(b)} = {pct:.0%}  "
            f"(p = {self.p_value:.3f})",
            f"   {UJUMBE[self.hukumu]}",
        ]
        # Vipimo vingine kwa percentile pia: vinaeleza AINA ya tofauti, si
        # kuihukumu. Sharpe ikiwa chini wakati faida iko juu inamaanisha
        # tofauti iko kwenye faida ghafi, si kwenye ubora (§9.8).
        nyingine = [(k, v) for k, v in self.kwa_kila_metric().items()
                    if k != MAMLAKA and v == v]
        if nyingine:
            lines.append("   vipimo vingine (percentile): " + " · ".join(
                f"{k.replace('_month', '').replace('_fraction', '')} {v:.0%}"
                for k, v in nyingine))
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "timeframe": self.timeframe,
            "n_bars": self.n_bars, "n_candidates": self.n_candidates,
            "seed": self.seed,
            "halisi": self.halisi.to_json(),
            "bandia": [r.to_json() for r in self.bandia],
            "percentile": self.percentile, "azimio": self.azimio,
            "p_value": self.p_value, "uwiano": self.uwiano(),
            "percentile_kwa_metric": self.kwa_kila_metric(),
            "hukumu": self.hukumu,
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
    """Symbols zilizopangwa kwa `p_value` — ndogo kwanza.

    Kupanga kwa percentile peke yake kunaweka `3/3` (p = 0.25) juu ya `6/6`
    (p = 0.14) pale zote mbili zinaonyesha 100% — na hiyo ni kupendelea
    ushahidi dhaifu. `p_value` inajumuisha vyote viwili kwenye namba moja.

    `NaN` (bila ulinganisho) zinaenda mwisho: symbol isiyoweza kupimwa si
    symbol iliyofeli, lakini pia si mahali pa kuanzia.
    """
    def ufunguo(c: Comparison):
        p = c.p_value
        return (0 if p == p else 1, p if p == p else 0.0)

    return sorted(comparisons, key=ufunguo)


def expected_by_chance(comparisons, p_kikomo: float | None = None) -> float:
    """Symbols ngapi zingefika `p ≤ kikomo` kwa BAHATI, zikipimwa zote.

    §9.1 kwenye ngazi ya symbols: kadri unavyopima symbols nyingi, ndivyo bora
    kati yao inavyoonekana nzuri hata kama hakuna hata moja yenye muundo.
    Symbol moja yenye `p = 0.14` kati ya 12 zilizopimwa **si ugunduzi** — ni
    matarajio.
    """
    zenye = [c for c in comparisons if c.p_value == c.p_value]
    if not zenye:
        return float("nan")
    kikomo = p_kikomo if p_kikomo is not None else min(c.p_value for c in zenye)
    return len(zenye) * kikomo


def render_table(comparisons) -> str:
    """Jedwali moja la symbols zote — ndilo linaloamua wapi pa kutafuta."""
    lines = [
        f"{'symbol':<9} {'TF':<4} {'halisi':>9} {'bandia kati':>12} "
        f"{'imezidi':>9} {'p':>7}  hukumu",
    ]
    for c in rank(comparisons):
        pct = c.percentile
        b = c.thamani_bandia
        kati = b[len(b) // 2] if b else float("nan")
        pct_str = (f"{int(pct * c.n_bandia)}/{c.n_bandia}" if pct == pct else "—")
        p = c.p_value
        azimio_str = f"{p:.3f}" if p == p else "—"
        h = c.halisi.mamlaka
        h_str = f"{h:.4f}" if h == h else "—"
        kati_str = f"{kati:.4f}" if kati == kati else "—"
        lines.append(
            f"{c.symbol:<9} {c.timeframe:<4} {h_str:>9} "
            f"{kati_str:>12} {pct_str:>9} {azimio_str:>7}  {c.hukumu}"
        )
    return "\n".join(lines)
