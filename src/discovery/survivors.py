"""Lango la sakafu ya kelele — DOCTRINE §9.2, §9.3, §13, R4, S1, S2.

Hapa ndipo sakafu iliyopimwa inakuwa **uamuzi**. Kila metric yenye sakafu yake
inalinganishwa; metric isiyo nayo inaripotiwa lakini haihukumu (§1.1).

---

**Kupita ni kuvuka kwenye KILA mwelekeo, si wastani wao.**

Malango sita si alama sita zinazoweza kuchanganywa. Kila moja inajibu swali
tofauti chini ya null ILE ILE: *je hii ingeweza kutokea kwa bahati?* Strategy
inayovuka mitano na kuanguka moja imeshaonyesha kuwa moja kati ya sifa zake
inaweza kuelezwa na bahati — na hakuna kiasi cha ubora kwenye tano nyingine
kinachofuta hilo.

Wastani ungeruhusu Sharpe kubwa mno kulipia drawdown mbaya. Lango la §9.9 ni
`T = min(u)` — kinyume kabisa cha wastani: mgombea ana thamani ya mwelekeo wake
**dhaifu zaidi**, na hakuna metric inayoweza kujificha nyuma ya nyingine.

Kilichobadilika 2026-09-05 si sharti hilo; ni **mahali kizingiti kinapopimwa**.
Kudai kila sakafu ya `p95` peke yake, zote kwa wakati mmoja, kulitumia uangalifu
wa §9.2 mara tano kimya — na kipimo kilionyesha washindi 150 wa null wakipita
`0/150` dhidi ya sakafu waliyoijenga wenyewe. Sasa uangalifu unatumika mara moja
juu ya `T`, na kiwango cha null kinachopita kinapimwa na kuandikwa. Sakafu za
`entries` zinabaki kama **maelezo** ya kila mwelekeo peke yake (§9.5, §9.2), si
kama malango yanayozidishwa.

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
    # §9.9 — nafasi ya kila metric ndani ya null, na dhaifu kati yake.
    u: dict[str, float] = field(default_factory=dict)
    t: float = float("nan")
    joint_floor: float = float("nan")
    # Metrics zilizo chini ya sakafu YAKE mwenyewe ingawa mgombea amepita lango
    # la pamoja. Haziamui — zinaandikwa ili tofauti kati ya kanuni mbili ionekane
    # badala ya kudhaniwa.
    below_own_floor: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.failed

    @property
    def joint(self) -> bool:
        """Je uamuzi umetokana na lango la §9.9 au mkusanyiko wa §9.2 wa zamani."""
        return bool(self.u)

    def render(self, floor=None) -> str:
        if self.passed:
            ziada = ""
            if self.joint:
                ziada = f"  ·  T {self.t:.4f} (dai > {self.joint_floor:.4f})"
                if self.below_own_floor:
                    ziada += ("  ·  chini ya sakafu yake: "
                              + ", ".join(self.below_own_floor))
            return f"{self.candidate_id}  MNUSURIKA{ziada}"
        sehemu = []
        for jina in self.failed:
            thamani = self.values.get(jina, float("nan"))
            if self.joint:
                sehemu.append(f"{jina} {thamani:,.4f} "
                              f"(u {self.u.get(jina, float('nan')):.4f})")
            elif floor is not None and jina in floor:
                e = floor.entries[jina]
                dai = ">" if e.higher_is == "better" else "<"
                sehemu.append(f"{jina} {thamani:,.4f} (dai {dai} {e.floor:,.4f})")
            else:
                sehemu.append(f"{jina} {thamani:,.4f}")
        kichwa = f"{self.candidate_id}  imeanguka"
        if self.joint:
            kichwa += f" (T {self.t:.4f} ≤ {self.joint_floor:.4f})"
        return kichwa + ": " + " · ".join(sehemu)

    def to_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id, "variant_hash": self.variant_hash,
            "passed": self.passed, "failed": list(self.failed),
            "values": self.values, "diagnostics": self.diagnostics,
            "u": self.u, "t": self.t, "joint_floor": self.joint_floor,
            "below_own_floor": list(self.below_own_floor),
        }


def screen(candidate_id: str, variant_hash: str, metrics, floor) -> Verdict:
    """Pima metrics dhidi ya sakafu. Kila mwelekeo lazima uvuke.

    Metric yenye sakafu ambayo **haipo** kwenye metrics ni kuanguka, si kuruka:
    kutokuwepo kwa kipimo si ushahidi wa kupita (§1.1). `u_stat` inarudisha
    `0.0` kwa thamani isiyohesabika, kwa hiyo sheria ile ile inashikilia chini
    ya kanuni zote mbili.

    Jedwali lisilo na lango la pamoja (lililoandikwa kabla ya §9.9) linahukumiwa
    kwa kanuni ya zamani — si kwa kudhani, bali kwa sababu `u` hazipo. `Verdict.joint`
    inasema kanuni ipi ilitumika, na ripoti inaichapisha.
    """
    thamani: dict[str, float] = {}
    diagnostic: dict[str, float] = {}

    for jina in floor.entries:
        thamani[jina] = float(metrics.get(jina, float("nan")))
    for jina, v in metrics.items():
        if jina not in floor.entries and isinstance(v, (int, float)):
            diagnostic[jina] = float(v)

    lango = getattr(floor, "joint", None)
    if lango is None:
        zilizoanguka = [j for j in floor.entries
                        if not floor.gate(j, metrics.get(j))]
        return Verdict(
            candidate_id=candidate_id, variant_hash=variant_hash,
            values=thamani, failed=tuple(zilizoanguka), diagnostics=diagnostic,
        )

    u = lango.u(metrics)
    zilizoanguka = lango.failed(metrics)
    # Tofauti kati ya kanuni mbili ina maana kwa ALIYEPITA pekee: ndipo §9.9
    # inaruhusu kitu ambacho mkusanyiko wa §9.2 ungekataa, na hicho ndicho
    # kinachopaswa kuonekana.
    chini = () if zilizoanguka else tuple(
        j for j in floor.entries if not floor.gate(j, metrics.get(j)))
    return Verdict(
        candidate_id=candidate_id, variant_hash=variant_hash,
        values=thamani, failed=zilizoanguka, diagnostics=diagnostic,
        u=u, t=min(u.values()) if u else 0.0, joint_floor=lango.floor,
        below_own_floor=chini,
    )


@dataclass(frozen=True)
class Survivor:
    """Mgombea aliyevuka kwenye KILA mwelekeo, pamoja na DNA yake (§13)."""

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

    @property
    def ni_ya_pamoja(self) -> bool:
        return bool(self.verdicts) and self.verdicts[0].joint

    def render(self, floor=None) -> str:
        kanuni = "§9.9 lango la pamoja" if self.ni_ya_pamoja else "§9.2 kila sakafu"
        lines = [
            f"LANGO LA SAKAFU · waliopimwa {self.n_screened:,} · "
            f"walionusurika {len(self.survivors):,}   [{kanuni}]"
        ]
        if self.ni_ya_pamoja:
            v = self.verdicts[0]
            lines.append(f"   T lazima izidi {v.joint_floor:.4f}")
        kata = self.by_failed_metric()
        if kata:
            lines.append("   mwelekeo uliokata:")
            for jina, n in kata.items():
                dai = ""
                if floor is not None and jina in floor and not self.ni_ya_pamoja:
                    e = floor.entries[jina]
                    ishara = ">" if e.higher_is == "better" else "<"
                    dai = f"  (dai {ishara} {e.floor:,.4f})"
                lines.append(f"      {jina:<28} {n:>6,}{dai}")
        # Tofauti kati ya kanuni mbili, ikiwepo — si kudhaniwa, ni kuandikwa.
        chini: dict[str, int] = {}
        for v in self.verdicts:
            for jina in v.below_own_floor:
                chini[jina] = chini.get(jina, 0) + 1
        if chini:
            lines.append("   walionusurika lakini chini ya sakafu ya metric YAKE "
                         "(§9.2, haiamui):")
            for jina, n in sorted(chini.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"      {jina:<28} {n:>6,}")
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
