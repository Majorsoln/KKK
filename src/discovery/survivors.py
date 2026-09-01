"""Lango la sakafu ya kelele — DOCTRINE §9.2, §9.3, §13, R4, S1, S2.

Hapa ndipo sakafu iliyopimwa inakuwa **uamuzi**. Kila metric yenye sakafu yake
inalinganishwa; metric isiyo nayo inaripotiwa lakini haihukumu (§1.1).

---

**Kupita ni kuvuka MALANGO YOTE, si wastani wao.**

Malango sita si alama sita zinazoweza kuchanganywa. Kila moja inajibu swali
tofauti chini ya null ILE ILE: *je hii ingeweza kutokea kwa bahati?* Strategy
inayovuka mitano na kuanguka moja imeshaonyesha kuwa moja kati ya sifa zake
inaweza kuelezwa na bahati — na hakuna kiasi cha ubora kwenye tano nyingine
kinachofuta hilo.

Wastani ungeruhusu Sharpe kubwa mno kulipia drawdown mbaya. Lakini sakafu ya
Sharpe na ya drawdown zilipimwa **kando**, kila moja kwa ncha yake ya mgawanyo
wake. Kuzichanganya kungekuwa kuunda kipimo cha saba ambacho hakikuwahi
kupimwa.

---

**Kilichoanguka kinaandikwa, si kutupwa.**

`Verdict` inashika kila metric iliyoanguka pamoja na thamani yake na sakafu
iliyoikataa. Bila hivyo, swali *"kwa nini hakuna anayepita?"* lingehitaji run
nyingine ya saa nyingi ili kujibiwa — na §9.5 ilionyesha kuwa swali hilo
linakuja.

---

**S3 — Sharpe ya `variants_tested` HAIJATEKELEZWA hapa.**

§9.3 inadai Sharpe inayoripotiwa iwe **deflated** kwa idadi ya majaribio.
Ripoti hii inatoa Sharpe **ghafi** pamoja na `variants_tested`, na inasema hivyo
waziwazi. Deflation inakuja na §13.

Sababu ya kutoiingiza kimya: lango lenyewe (§9.2) tayari ni marekebisho ya
kutafuta mara nyingi, yaliyopimwa kwa data hii. Kuongeza deflation ya
kinadharia juu yake bila kuamua uhusiano wa mbili hizo kungekuwa kurekebisha
mara mbili kwa kiasi kisichojulikana.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Metrics zinazoripotiwa lakini HAZIHUKUMU — hazina sakafu (§1.1).
DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True)
class Verdict:
    """Uamuzi wa lango la §9 kwa mgombea MMOJA, pamoja na sababu zake."""

    candidate_id: str
    variant_hash: str
    values: dict[str, float]
    failed: tuple[str, ...] = ()
    diagnostics: dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.failed

    def render(self, floor=None) -> str:
        if self.passed:
            return f"{self.candidate_id}  MNUSURIKA"
        sehemu = []
        for jina in self.failed:
            thamani = self.values.get(jina, float("nan"))
            if floor is not None and jina in floor:
                e = floor.entries[jina]
                dai = ">" if e.higher_is == "better" else "<"
                sehemu.append(f"{jina} {thamani:,.4f} (dai {dai} {e.floor:,.4f})")
            else:
                sehemu.append(f"{jina} {thamani:,.4f}")
        return f"{self.candidate_id}  imeanguka: " + " · ".join(sehemu)

    def to_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id, "variant_hash": self.variant_hash,
            "passed": self.passed, "failed": list(self.failed),
            "values": self.values, "diagnostics": self.diagnostics,
        }


def screen(candidate_id: str, variant_hash: str, metrics, floor) -> Verdict:
    """Pima metrics dhidi ya kila sakafu iliyopo. Zote lazima zipite.

    Metric yenye sakafu ambayo **haipo** kwenye metrics ni kuanguka, si kuruka:
    kutokuwepo kwa kipimo si ushahidi wa kupita (§1.1).
    """
    zilizoanguka: list[str] = []
    thamani: dict[str, float] = {}
    diagnostic: dict[str, float] = {}

    for jina in floor.entries:
        thamani[jina] = float(metrics.get(jina, float("nan")))
        if not floor.gate(jina, metrics.get(jina)):
            zilizoanguka.append(jina)

    for jina, v in metrics.items():
        if jina not in floor.entries and isinstance(v, (int, float)):
            diagnostic[jina] = float(v)

    return Verdict(
        candidate_id=candidate_id, variant_hash=variant_hash,
        values=thamani, failed=tuple(zilizoanguka), diagnostics=diagnostic,
    )


@dataclass(frozen=True)
class Survivor:
    """Mgombea aliyevuka malango YOTE, pamoja na DNA yake (§13)."""

    verdict: Verdict
    strategy: Any
    economics: Any
    n_trades: int
    n_months: int

    def render(self) -> str:
        v = self.verdict.values
        return (
            f"{self.verdict.candidate_id}  {self.strategy.strategy_id}\n"
            f"      return/mwezi {v.get('net_account_return_month', float('nan')):>7.2%} · "
            f"pips/mwezi {v.get('net_pips_month', float('nan')):>9.2f} · "
            f"sharpe {v.get('sharpe', float('nan')):>5.2f} · "
            f"DD ${v.get('max_drawdown', float('nan')):>9.2f}\n"
            f"      trades {self.n_trades:,} kwenye miezi {self.n_months:,} · "
            f"{self.economics.render()}"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.to_json(),
            "strategy": self.strategy.to_json(),
            "economics": self.economics.to_json(),
            "n_trades": self.n_trades, "n_months": self.n_months,
        }


@dataclass
class Screening:
    """Matokeo ya kupima wagombea WOTE waliopita §8.4 dhidi ya sakafu."""

    survivors: list[Survivor] = field(default_factory=list)
    verdicts: list[Verdict] = field(default_factory=list)

    def add(self, verdict: Verdict, survivor: Survivor | None = None) -> None:
        self.verdicts.append(verdict)
        if survivor is not None:
            self.survivors.append(survivor)

    @property
    def n_screened(self) -> int:
        return len(self.verdicts)

    def by_failed_metric(self) -> dict[str, int]:
        """Lango lipi linakata zaidi. Ndilo swali la kwanza pale hakuna anayepita.

        Mgombea mmoja anaweza kuanguka kwa malango kadhaa; hesabu hii inaonyesha
        **lango kila moja limekata mangapi**, kwa hiyo jumla yake inaweza kuzidi
        idadi ya waliopimwa. Hiyo si kosa — ni jibu la swali lililoulizwa.
        """
        out: dict[str, int] = {}
        for v in self.verdicts:
            for jina in v.failed:
                out[jina] = out.get(jina, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    def render(self, floor=None) -> str:
        lines = [
            f"LANGO LA SAKAFU · waliopimwa {self.n_screened:,} · "
            f"walionusurika {len(self.survivors):,}"
        ]
        kata = self.by_failed_metric()
        if kata:
            lines.append("   lango lililokata:")
            for jina, n in kata.items():
                dai = ""
                if floor is not None and jina in floor:
                    e = floor.entries[jina]
                    ishara = ">" if e.higher_is == "better" else "<"
                    dai = f"  (dai {ishara} {e.floor:,.4f})"
                lines.append(f"      {jina:<28} {n:>6,}{dai}")
        for s in self.survivors:
            lines.append("   " + s.render())
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "n_screened": self.n_screened,
            "n_survivors": len(self.survivors),
            "by_failed_metric": self.by_failed_metric(),
            "survivors": [s.to_json() for s in self.survivors],
            "verdicts": [v.to_json() for v in self.verdicts],
        }
