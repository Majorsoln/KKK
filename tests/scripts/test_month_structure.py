"""Kipimo cha muundo wa miezi — DOCTRINE §9.5, §2.

Kipimo kinachopima tofauti kati ya substrate mbili lazima kisiwe na upendeleo
chenyewe. Hasa `acf1`: ikirudisha thamani kwa mfululizo mfupi mno, tofauti
inayoonekana ingekuwa ya hesabu, si ya soko.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from month_structure import acf1  # noqa: E402


def _miezi(pips):
    return pd.DataFrame({"net_pips": list(pips)})


def test_mfululizo_wenye_misimu_una_acf1_CHANYA():
    """Misimu mirefu ya faida kisha ya hasara — ndicho kinachotafutwa."""
    x = [10.0] * 8 + [-10.0] * 8 + [10.0] * 8
    assert acf1(_miezi(x)) > 0.5


def test_mfululizo_unaobadilika_kila_mwezi_una_acf1_HASI():
    x = [10.0, -10.0] * 12
    assert acf1(_miezi(x)) < -0.5


def test_kelele_safi_ina_acf1_karibu_SIFURI():
    rng = np.random.default_rng(7)
    thamani = [acf1(_miezi(rng.normal(0, 50, 99))) for _ in range(40)]
    assert abs(float(np.mean(thamani))) < 0.10


def test_miezi_michache_mno_inarudisha_NaN():
    """Si sifuri: `0.0` ingesomeka kama 'hakuna mfululizo', jibu la kubuni."""
    for n in (0, 1, 2, 3):
        assert math.isnan(acf1(_miezi([1.0] * n)))
    assert not math.isnan(acf1(_miezi([1.0, -1.0, 1.0, -1.0])))


def test_mfululizo_usiobadilika_ni_NaN_si_sifuri():
    """Mtawanyiko sifuri: uhusiano haujafafanuliwa, haujapimwa kuwa sifuri."""
    assert math.isnan(acf1(_miezi([5.0] * 20)))


def test_NaN_zinaondolewa():
    safi = acf1(_miezi([10.0] * 6 + [-10.0] * 6))
    na_nan = acf1(_miezi([10.0] * 6 + [float("nan")] + [-10.0] * 6))
    assert not math.isnan(na_nan)
    assert abs(na_nan - safi) < 0.35


def test_acf1_HAITEGEMEI_kipimo_cha_thamani():
    """Pips au dola — mfululizo ni ule ule."""
    x = [3.0, -1.0, 4.0, -1.0, 5.0, -9.0, 2.0, 6.0]
    assert acf1(_miezi(x)) == pytest.approx(acf1(_miezi([v * 1000 for v in x])))
