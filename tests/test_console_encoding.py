"""Output ya CLI isianguke inapoelekezwa kwenye pipe au faili.

`audit.bat` inaandika log kwa `Tee-Object`, yaani stdout ni PIPE. Windows
inapokuwa na locale ya cp1252, Python inachagua encoding hiyo kwa pipe — na
`→`, `≥`, `↔` hazipo humo. Amri ilikuwa inaanguka kwa `UnicodeEncodeError`
**baada ya kazi yote kumalizika**, ikipoteza ripoti ya mwisho.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RISKY = ("→", "≥", "↔", "≤")


def _run(module: str, *args: str, encoding: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": encoding}
    env.pop("PYTHONUTF8", None)
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=REPO,
        env=env,
        capture_output=True,   # stdout ni PIPE — ndipo tatizo lilipokuwa
    )


@pytest.mark.parametrize("module,args", [("src.data.cli", ("splits",))])
def test_output_haiangushi_amri_kwenye_cp1252(module, args):
    """Kizingiti halisi: `splits` inachapisha `→` kwenye kila fold."""
    result = _run(module, *args, encoding="cp1252")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert b"UnicodeEncodeError" not in result.stderr


def test_ripoti_bado_ina_herufi_zake_kwenye_utf8():
    """Kurekebisha kusiwe kwa kuondoa herufi — maandishi yabaki kama yalivyo."""
    result = _run("src.data.cli", "splits", encoding="utf-8")
    printed = result.stdout.decode("utf-8")
    assert "→" in printed and result.returncode == 0


def test_governance_cli_nayo_ina_kinga():
    result = _run("src.governance.cli", "pending", encoding="cp1252")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


def test_hakuna_herufi_hatari_kwenye_maandishi_ya_scripts():
    """Scripts za `.bat` hazipiti kwenye kinga ya Python — `echo` ni cmd."""
    for path in sorted((REPO / "scripts").glob("*.bat")):
        text = path.read_bytes().decode("utf-8")
        for line in text.splitlines():
            if line.strip().lower().startswith("echo"):
                bad = [c for c in RISKY if c in line]
                assert not bad, f"{path.name}: `echo` ina {bad} — cmd haitaionyesha"
