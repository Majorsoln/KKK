"""Malango G11 na G12 — mipaka ya repo baada ya `research/` kuingia ndani (§9).

`research/` iko ndani ya repo (uamuzi wa PD 2026-08-04). Sheria mbili za README
zilizokuwa zinalindwa na folda kuwa NJE sasa zinalindwa hapa:

    G11  data ya utafiti HAIINGII git  — hakuna parquet, hakuna kitu chini ya
         `research/data/`, hakuna faili kubwa iliyo-track.
    G12  engine HAIRUDII code ya utafiti — `src/` hairuhusiwi ku-import
         `research.src` (sheria 1 ya README: engine inatumia namba
         zilizothibitishwa, hairudii hesabu).

Tests hizi zinakimbia kwa `pytest` ya kawaida — mlinzi hayuko CI pekee.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# Kikomo cha faili iliyo-track. Code/docs/reports ni KB; kitu chochote juu ya hapa
# ni dalili ya data iliyoingia kwa bahati mbaya.
MAX_TRACKED_BYTES = 5 * 1024 * 1024  # 5 MB

DATA_SUFFIXES = {".parquet", ".feather", ".arrow", ".h5", ".hdf5", ".pkl", ".npy", ".npz"}


def _git_tracked_files() -> list[str]:
    """Faili zote zilizo-track na git. Bila git/checkout → skip."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"git haipatikani hapa: {exc}")
    return [name for name in out.stdout.decode("utf-8", "replace").split("\0") if name]


# ---------------------------------------------------------------------------
# G11 — data haiingii git
# ---------------------------------------------------------------------------


def test_g11_hakuna_faili_ya_data_iliyotrackiwa() -> None:
    """Parquet (na wenzake) hawaingii git — data inakaa `research/data/` pekee."""
    tracked = _git_tracked_files()
    offenders = [name for name in tracked if Path(name).suffix.lower() in DATA_SUFFIXES]
    assert not offenders, (
        "UKIUKAJI WA G11: faili za data zimeingia git — "
        f"{offenders[:10]}. Data inakaa `research/data/` (haipushwi, §9)."
    )


def test_g11_hakuna_kitu_chini_ya_research_data() -> None:
    """`research/data/` ni ignore ya folda — hakuna njia yoyote yake inayotrackiwa."""
    tracked = _git_tracked_files()
    offenders = [name for name in tracked if name.startswith("research/data/")]
    assert not offenders, (
        "UKIUKAJI WA G11: `research/data/` haipushwi kamwe — "
        f"zimeingia: {offenders[:10]}"
    )


def test_g11_hakuna_faili_kubwa_iliyotrackiwa() -> None:
    """Faili iliyo-track > 5MB ni dalili ya data, si code/report."""
    tracked = _git_tracked_files()
    offenders: list[tuple[str, int]] = []
    for name in tracked:
        path = REPO / name
        if not path.is_file():  # imefutwa kwenye working tree — si suala la lango hili
            continue
        size = path.stat().st_size
        if size > MAX_TRACKED_BYTES:
            offenders.append((name, size))
    assert not offenders, (
        "UKIUKAJI WA G11: faili kubwa zimeingia git — "
        f"{[(n, f'{s / 1_048_576:.1f}MB') for n, s in offenders]}"
    )


def test_g11_gitignore_inazuia_research_data() -> None:
    """Sheria yenyewe ipo, na ni ya FOLDA (git isiingie ndani ya GB 31)."""
    text = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "research/data/" in text, ".gitignore lazima izuie `research/data/` (§9, G11)"


# ---------------------------------------------------------------------------
# G12 — engine hairudii code ya utafiti (sheria 1 ya README)
# ---------------------------------------------------------------------------

_RESEARCH_IMPORT = re.compile(
    r"^\s*(?:from\s+research(?:\.\w+)*\s+import\b|import\s+research(?:\.\w+)*)",
    re.MULTILINE,
)


def test_g12_engine_haiimport_code_ya_utafiti() -> None:
    """`src/` (engine) hairuhusiwi kutegemea `research/src/`.

    Engine inatumia **namba zilizothibitishwa** (attestation), hairudii hesabu za
    utafiti. Zikiunganishwa, siku moja zitatofautiana na kilichothibitishwa (GIGO).
    """
    offenders: list[str] = []
    for path in sorted((REPO / "src").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if _RESEARCH_IMPORT.search(text):
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, (
        "UKIUKAJI WA G12: engine ina-import code ya utafiti — "
        f"{offenders}. Sheria 1 ya README: engine HAIRUDII hesabu za utafiti; "
        "inapokea namba zilizothibitishwa pekee."
    )


def test_g12_research_src_haiko_kwenye_packages_za_engine() -> None:
    """`research.src` haipaswi kufungashwa na engine (pyproject packages)."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert "research" not in text.split("[tool.setuptools]")[-1].split("[tool.pytest")[0], (
        "UKIUKAJI WA G12: `research` haipaswi kuwa package ya engine kwenye pyproject.toml"
    )


# ---------------------------------------------------------------------------
# G13 — sifa za mashine haziingii git
# ---------------------------------------------------------------------------


def test_g13_hakuna_env_local_iliyotrackiwa() -> None:
    """`scripts/env.local.bat` ina nywila ya MT5 — haipushwi kamwe."""
    tracked = _git_tracked_files()
    offenders = [n for n in tracked if n.endswith(".local.bat") or "env.local" in n]
    assert not offenders, f"UKIUKAJI WA G13: sifa za mashine zimeingia git — {offenders}"


def test_g13_env_example_haina_thamani() -> None:
    """Template inapushwa, lakini ikiwa TUPU — mtu asisahau na kuacha nywila humo."""
    text = (REPO / "scripts" / "env.example.bat").read_text(encoding="utf-8")
    for key in ("ELITEFX_MT5_LOGIN", "ELITEFX_MT5_PASSWORD", "ELITEFX_MT5_SERVER"):
        line = next(ln for ln in text.splitlines() if ln.startswith(f"set {key}="))
        assert line.strip() == f"set {key}=", f"{key} ina thamani kwenye template: {line!r}"
