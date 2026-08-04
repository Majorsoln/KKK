"""§9 ya DATA_FEATURE_STANDARD — muundo wa research repo (NJE ya repo hii).

Repo hii ni engine ya uzalishaji (sheria ya README). Datasets, notebooks na runs
zinakaa kwenye storage tofauti; hapa tunaweka **muundo wake** tu, ili kila
tabaka lianze mahali palipotangazwa na hakuna dataset inayoishia "sehemu ya
kompyuta ya mtu".

Muundo (spec §9):

    research/
    ├── data/{L0_raw, L1_clean, L2_bars, L3_features, L4_labels, L5_datasets}
    ├── reports/{quality, screening, ablation, calibration}
    └── src/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

LAYOUT_DIRS: tuple[str, ...] = (
    "data",
    "data/L0_raw",
    "data/L1_clean",
    "data/L2_bars",
    "data/L3_features",
    "data/L4_labels",
    "data/L5_datasets",
    "reports",
    "reports/quality",
    "reports/screening",
    "reports/ablation",
    "reports/calibration",
    "src",
)

DIR_PURPOSE: dict[str, str] = {
    "data/L0_raw": "ticks bid+ask ghafi — immutable, append-only, SHA256 kwa kila partition (§2)",
    "data/L1_clean": "UTC, gaps, duplicates, sanity + quality_report.json (§3)",
    "data/L2_bars": "TF 7 zilizojengwa kutoka ticks + spread stats kwa kila bar (§4)",
    "data/L3_features": "features kwa dataset_id, as-of closed bar pekee (§6)",
    "data/L4_labels": "labels zilizotatuliwa kwa path ya ticks (§5)",
    "data/L5_datasets": "train/validation/holdout + manifest.json (§7, §8)",
    "reports/quality": "R0 — quality_report.json, kalenda ya sessions, ulinganisho A↔B",
    "reports/screening": "R2/R3 — IC/MI, permutation, FDR, clusters",
    "reports/ablation": "R7 — jedwali la ablation ya familia na TF",
    "reports/calibration": "R5 — reliability curves, ECE, Brier skill",
    "src": "code ya utafiti (haiingii repo ya engine — sheria 2 ya README)",
}

README_NAME = "README.md"


def _readme_text(root: Path) -> str:
    lines = [
        "# RESEARCH STORAGE — ELITEFX",
        "",
        "Muundo huu umewekwa na `src/data/research_layout.py` kwa spec §9 ya",
        "`docs/DATA_FEATURE_STANDARD.md`. Repo ya engine inapokea **models + namba",
        "zilizothibitishwa** pekee (sheria 2 ya README ya engine).",
        "",
        f"Mzizi: `{root}`",
        "",
        "## Folda",
        "",
        "| Folda | Yaliyomo |",
        "|---|---|",
    ]
    lines += [f"| `{name}/` | {purpose} |" for name, purpose in DIR_PURPOSE.items()]
    lines += [
        "",
        "## Sheria zisizovunjwa",
        "",
        "1. **L0 haibadilishwi.** Partition ikishaandikwa na kuhashiwa, badiliko lolote",
        "   ni ukiukaji wa DF-01. Data mpya = partition MPYA (append-only).",
        "2. **Provenance inaandikwa.** `provenance=broker` kwa feed ya broker,",
        "   `provenance=aggregator` kwa data ya kihistoria (spec §2.2).",
        "3. **Kila dataset ina `dataset_id` + manifest** (spec §8). Namba isiyo na",
        "   `dataset_id` hairudi kwenye engine.",
        "4. **HOLDOUT (2024-04-01 → 2026-04-30) na RESERVE (2026-05-01+)** zinakaa",
        "   kwenye eneo lenye ruhusa ya kusoma kwa job ya R8 pekee (§4.3 ya",
        "   IMPLEMENTATION_PLAN, lango G2). Utekelezaji wa ruhusa hizo ni kazi ya T1.",
        "",
    ]
    return "\n".join(lines)


@dataclass
class LayoutResult:
    root: str
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    readme: str | None = None

    def render(self) -> str:
        lines = [f"muundo wa research (§9): {self.root}"]
        for name in self.created:
            lines.append(f"  + {name}")
        for name in self.existing:
            lines.append(f"  = {name} (ilikuwepo)")
        if self.readme:
            lines.append(f"  README: {self.readme}")
        return "\n".join(lines)


def init_research_tree(root: str | Path, write_readme: bool = True) -> LayoutResult:
    """Simamisha muundo wa §9. Ni idempotent — haigusi kilichopo."""
    root = Path(root).expanduser()
    result = LayoutResult(root=str(root))
    root.mkdir(parents=True, exist_ok=True)
    for name in LAYOUT_DIRS:
        path = root / name
        if path.is_dir():
            result.existing.append(name)
        else:
            path.mkdir(parents=True, exist_ok=True)
            result.created.append(name)
    if write_readme:
        readme = root / README_NAME
        if not readme.exists():
            readme.write_text(_readme_text(root), encoding="utf-8")
        result.readme = str(readme)
    return result


def verify_research_tree(root: str | Path) -> list[str]:
    """Folda za §9 ambazo hazipo (tupu = muundo umekamilika)."""
    root = Path(root).expanduser()
    return [name for name in LAYOUT_DIRS if not (root / name).is_dir()]
