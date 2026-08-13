"""Bajeti ya majaribio — kikomo kinachotekelezwa na code, si nia njema.

Utawala wetu (`SIGNATURES.md`) unafanya maamuzi **yaonekane**. Mapitio ya nje
yaliweka kidole mahali sahihi:

> *"A ledger does not mathematically eliminate selection bias. It makes the
> selection auditable. Those are different things."*

Darasa la tatu la uvujaji — **uteuzi** (§4.3) — ndilo pekee lisilo na detector.
Purged CV hailishiki. Sentinel hailioni. Holdout inashikilia mara moja tu,
mwishoni, wakati tayari umeshachagua kile utakachokipeleka.

Hii ndiyo dawa: **bajeti ngumu ya idadi ya configs zinazoweza kupimwa dhidi ya
labels**, ikitokana na MinBTL (Bailey & López de Prado):

    N ≤ exp(SR*² · miaka ÷ 2)

Kwa `SR* = 0.7` na miaka 8.25: **configs 7**. Kwa maisha yote ya mradi.

Kanuni tano zinazoifanya isiwe mapambo:

1. **Ya mradi mzima, hairudishwi.** Per-phase reset ndiyo hasa multiple-testing
   surface tunayoifunga — ingekuwa loophole inayofanya utaratibu wote uwe bure.
2. **Inapungua kwa evaluation dhidi ya labels**, si kwa code iliyoandikwa.
   Kufikiri ni bure; kugusa outcome data ni gharama.
3. **Configs zinazohusiana zinapungua kwa cluster weight**, si moja kwa moja.
   Cells 25 za grid zilizoangaliwa ni clusters 2–3, si 25.
4. **Msamaha mmoja tu, uliosainiwa:** replication ya effect iliyochapishwa
   haipungui — kwa sharti kwamba matokeo yake **hayaruhusiwi** kutumika kwa
   strategy selection. Bila kifungu hicho, kila config ingeitwa "validation".
5. **Ikifika sifuri, CI inakataa.** Mradi unaisha kwa jibu ulilokuwa nalo.

Faili ni **la kuongezwa tu**, kama `SIGNATURES.md`, na linahakikiwa na commit
ya PD kwa njia ile ile.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

LEDGER = Path("docs/TRIAL_BUDGET.md")

# Aina za matumizi. `REPLICATION` pekee ndiyo isiyopunguza bajeti, na inabeba
# sharti gumu: matokeo yake hayaingii kwenye uteuzi wa strategy.
KINDS = ("EVALUATION", "REPLICATION")

_ROW = re.compile(r"^\|\s*(\d+)\s*\|(.+)$")


@dataclass
class Entry:
    number: int
    stamp: str
    config_id: str
    kind: str
    weight: float
    remaining: float
    reason: str

    def render(self) -> str:
        # `:.3f`, si `:g`. `%g` inakata hadi tarakimu 6, kwa hiyo bajeti
        # iliyotumika kabisa inasomeka tena ikiwa na mabaki ya 3.7e-6 — na
        # lango lisingewaka. Uzito ni idadi ya configs; tarakimu tatu zinatosha.
        return (
            f"| {self.number} | {self.stamp} | `{self.config_id}` | {self.kind} | "
            f"{self.weight:.3f} | {self.remaining:.3f} | {self.reason} |"
        )


@dataclass
class Budget:
    sr_target: float = 0.0
    years: float = 0.0
    total: float = 0.0
    entries: list[Entry] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def spent(self) -> float:
        return float(sum(e.weight for e in self.entries if e.kind == "EVALUATION"))

    @property
    def remaining(self) -> float:
        return float(self.total - self.spent)

    @property
    def exhausted(self) -> bool:
        """Imekwisha pale config nyingine hata moja haiwezi kumudika.

        Si `remaining <= 0`. Uzito mdogo kabisa unaowezekana ni config MOJA;
        bajeti ya 0.4 haiwezi kununua chochote, kwa hiyo ni sifuri kwa vitendo.
        Hii pia inaondoa unyeti kwa kelele ya float kwenye ukingo.
        """
        return self.remaining < 1.0

    def to_json(self) -> dict[str, Any]:
        return {
            "sr_target": self.sr_target,
            "years": self.years,
            "total": self.total,
            "spent": self.spent,
            "remaining": self.remaining,
            "exhausted": self.exhausted,
            "entries": [e.__dict__ for e in self.entries],
        }


def total_for(sr_target: float, years: float) -> float:
    """MinBTL — configs huru ngapi kabla matokeo hayajawa kelele."""
    from src.data.costs import config_budget

    return config_budget(sr_target, years)


def load(path: Path | None = None) -> Budget:
    target = Path(path or LEDGER)
    out = Budget()
    if not target.is_file():
        return out
    text = target.read_text(encoding="utf-8")

    # `SR\*` kwenye markdown inaandikwa ikiwa na backslash ya kutoroka —
    # regex lazima ikubali zote mbili, la sivyo kichwa halisi hakisomeki.
    head = re.search(r"SR\\?\*\s*[:=]\s*([0-9.]+).*?miaka\s*[:=]\s*([0-9.]+)", text, re.S)
    if head:
        out.sr_target = float(head.group(1))
        out.years = float(head.group(2))
        out.total = total_for(out.sr_target, out.years)

    for line in text.splitlines():
        match = _ROW.match(line.strip())
        if not match:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        kind = cells[3]
        if kind not in KINDS:
            out.problems.append(f"#{cells[0]}: aina `{kind}` haijulikani")
            continue
        out.entries.append(
            Entry(
                number=int(cells[0]),
                stamp=cells[1],
                config_id=cells[2].strip("`"),
                kind=kind,
                weight=float(cells[4]),
                remaining=float(cells[5]),
                reason=cells[6],
            )
        )
    return out


def spend(
    config_id: str,
    weight: float,
    reason: str,
    kind: str = "EVALUATION",
    path: Path | None = None,
) -> Entry:
    """Andika matumizi. Inakataa pale bajeti imekwisha.

    Kukataa ndiko kunakoifanya iwe bajeti. Onyo lisingezuia chochote — na
    mtekelezaji aliyechoka saa nne usiku angeliruka.
    """
    if kind not in KINDS:
        raise ValueError(f"aina `{kind}` haijulikani; chagua kati ya {KINDS}")
    if not reason or not any(ch.isalnum() for ch in reason):
        raise ValueError("sababu ya matumizi ni ya lazima — bila hiyo ledger ni orodha tupu")

    target = Path(path or LEDGER)
    budget = load(target)
    if budget.total <= 0:
        raise ValueError(
            f"{target} haina kichwa chenye SR* na miaka — bajeti haijatangazwa. "
            "Itangaze na PD aisaini KABLA ya evaluation ya kwanza."
        )
    if kind == "EVALUATION" and budget.remaining < weight:
        raise ValueError(
            f"bajeti imekwisha: imebaki {budget.remaining:g}, inaombwa {weight:g}. "
            "Mradi unaisha kwa jibu ulilonalo — hiyo ndiyo maana ya bajeti."
        )

    entry = Entry(
        number=len(budget.entries) + 1,
        stamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        config_id=config_id,
        kind=kind,
        weight=float(weight),
        remaining=budget.remaining - (weight if kind == "EVALUATION" else 0.0),
        reason=reason.strip(),
    )
    with target.open("a", encoding="utf-8") as handle:
        handle.write(entry.render() + "\n")
    return entry


def guard(path: Path | None = None) -> None:
    """Inaitwa na kila amri inayotathmini dhidi ya labels. Inainua kama imekwisha."""
    budget = load(path)
    if budget.total > 0 and budget.exhausted:
        raise RuntimeError(
            f"bajeti ya majaribio imekwisha ({budget.spent:g}/{budget.total:.1f}). "
            "Hakuna evaluation nyingine dhidi ya labels inayoruhusiwa."
        )


def cluster_weight(configs: Iterable[str], clusters: dict[str, str]) -> float:
    """Uzito wa kundi la configs zinazohusiana — clusters, si idadi.

    Cells 25 za grid zilizoangaliwa kwenye jedwali moja la EV si trials 25 huru;
    ni narrow/mid/wide. Kuzihesabu 25 kungemaliza bajeti mara tatu kwa kitu
    kimoja.
    """
    seen = {clusters.get(config, config) for config in configs}
    return float(len(seen))


def render_header(sr_target: float, years: float) -> str:
    total = total_for(sr_target, years)
    return (
        "# BAJETI YA MAJARIBIO — kikomo kinachotekelezwa na code\n\n"
        f"**SR\\* : {sr_target}**  ·  **miaka : {years}**  ·  "
        f"**bajeti : {total:.1f} configs**\n\n"
        "> MinBTL (Bailey & López de Prado): `N ≤ exp(SR*² · miaka ÷ 2)`.\n"
        "> Bajeti si mali ya dataset pekee — ni **function ya kile unachotarajia\n"
        "> kupata**. SR\\* ya juu inatoa bajeti kubwa kwa sababu ni ahadi kubwa.\n\n"
        "> **Ya mradi mzima. Hairudishwi.** Per-phase reset ndiyo hasa\n"
        "> multiple-testing surface tunayoifunga.\n\n"
        "> `REPLICATION` haipunguzi bajeti — **kwa sharti** kwamba matokeo yake\n"
        "> hayaruhusiwi kutumika kwa uteuzi wa strategy. Bila sharti hilo, kila\n"
        "> config ingeitwa \"validation\".\n\n"
        "| # | Tarehe (UTC) | Config | Aina | Uzito | Imebaki | Sababu |\n"
        "|---|---|---|---|---|---|---|\n"
    )
