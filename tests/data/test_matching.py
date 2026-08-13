"""T3 hatua 2 — kutenganisha utabiri na uteuzi wa mazingira.

Kila test hapa inauliza swali moja: **je jaribio linaweza kusema "artefact"
pale ilipo artefact?** Jaribio linaloweza kusema "halisi" pekee si jaribio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.matching import build_strata, matched_effect, quantile_bin


def _frame(
    n: int = 4000,
    effect: float = 0.0,
    confound: float = 0.0,
    seed: int = 0,
) -> pd.DataFrame:
    """Setups na controls zenye mgawanyo TOFAUTI wa ATR — kama data halisi.

    `effect`   — makali ya kweli ya kichujio (huru na mazingira)
    `confound` — kiasi ambacho ATR ya juu peke yake inainua matokeo
    """
    rng = np.random.RandomState(seed)
    half = n // 2
    # Setups zinapendelea ATR ya juu kwa MUUNDO (min_atr_mult 2.5).
    atr_setup = rng.uniform(0.5, 1.0, half)
    atr_control = rng.uniform(0.0, 1.0, half)
    atr = np.concatenate([atr_setup, atr_control])
    is_setup = np.array([True] * half + [False] * half)

    r = confound * atr + effect * is_setup + rng.normal(0, 0.05, n)
    stamps = pd.to_datetime("2018-01-01", utc=True) + pd.to_timedelta(
        rng.randint(0, 365 * 5, n), unit="D"
    )
    return pd.DataFrame(
        {
            "symbol": rng.choice(["EURUSD", "GBPUSD"], n),
            "decision_time": stamps,
            "atr_pips": 10.0 + 20.0 * atr,
            "spread_entry_pips": rng.uniform(0.5, 1.5, n),
            "is_setup": is_setup,
            "is_control": ~is_setup,
            "r_net": r,
        }
    )


def test_quantile_bin_inagawanya_sawasawa():
    values = pd.Series(np.arange(1000, dtype=float))
    bins = quantile_bin(values, 5, "b")
    counts = bins.value_counts()
    assert len(counts) == 5
    assert counts.min() >= 190 and counts.max() <= 210


def test_quantile_bin_inashika_nan_bila_kuanguka():
    values = pd.Series([1.0, 2.0, np.nan, 4.0])
    assert (quantile_bin(values, 2, "b") == "NA").sum() == 1


def test_uteuzi_safi_unagunduliwa_kama_artefact():
    """Kichujio kisicho na makali, kikichagua ATR ya juu tu → ARTEFACT.

    Hii ndiyo kesi inayoogopwa: tofauti ghafi inaonekana, lakini inatoweka
    ndani ya strata. Jaribio lisiloweza kuiona si jaribio.
    """
    frame = build_strata(_frame(effect=0.0, confound=0.4, seed=1))
    result = matched_effect(frame, n_boot=0)
    assert result.raw_diff > 0.05, "confound lazima ionekane kwenye tofauti ghafi"
    assert abs(result.matched_diff) < 0.2 * result.raw_diff, "ndani ya strata lazima itoweke"


def test_makali_halisi_yanabaki_ndani_ya_strata():
    """Kichujio chenye makali ya kweli kinabaki hata baada ya kudhibiti ATR."""
    frame = build_strata(_frame(effect=0.10, confound=0.0, seed=2))
    result = matched_effect(frame, n_boot=0)
    assert result.matched_diff == pytest.approx(0.10, abs=0.02)


def test_mchanganyiko_unagawanywa_kwa_uwiano():
    """Nusu makali, nusu uteuzi → tofauti ndani ya strata ni nusu ya ghafi."""
    frame = build_strata(_frame(effect=0.10, confound=0.4, seed=3))
    result = matched_effect(frame, n_boot=0)
    assert result.raw_diff > result.matched_diff
    assert result.matched_diff == pytest.approx(0.10, abs=0.03)


def test_common_support_inaripotiwa_si_kufichwa():
    """Setups zisizo na control inayolingana ni MATOKEO, si kikwazo kimya.

    Gate ya momentum inafanya setups ziwe na |impulse| >= 2.5 ATR daima.
    Common support ikiwa ndogo, athari haiwezi kutenganishwa na masharti
    yanayoifafanua — na hilo lazima lisemwe.
    """
    frame = _frame(n=2000, seed=4)
    # Setups zote kwenye ATR ya juu kabisa; controls zote chini — hakuna mwingiliano.
    frame.loc[frame["is_setup"], "atr_pips"] = 100.0
    frame.loc[~frame["is_setup"], "atr_pips"] = 5.0
    result = matched_effect(build_strata(frame), n_boot=0)
    assert result.support_frac == 0.0
    assert any("haiwezi kutenganishwa" in n for n in result.notes)
    assert not np.isfinite(result.matched_diff)


def test_ci_inatoka_block_bootstrap_ya_mwaka():
    """Resampling ya rows moja moja ingedhania uhuru usiokuwepo."""
    frame = build_strata(_frame(n=3000, effect=0.10, confound=0.2, seed=5))
    result = matched_effect(frame, n_boot=60)
    assert np.isfinite(result.ci_low) and np.isfinite(result.ci_high)
    assert result.ci_low < result.matched_diff < result.ci_high


def test_strata_zinajengwa_kwa_data_yote_si_kwa_kundi():
    """Bins zilizohesabiwa kwa kila kundi peke yake si bins zinazolingana."""
    frame = build_strata(_frame(n=1000, seed=6))
    for column in ("atr_bin", "spread_bin", "session", "year"):
        assert column in frame.columns
    # Bin ile ile lazima imaanishe kiwango kile kile cha ATR kwa makundi yote.
    for name, chunk in frame.groupby("atr_bin"):
        if name == "NA" or len(chunk) < 20:
            continue
        span = chunk["atr_pips"].max() - chunk["atr_pips"].min()
        assert span <= frame["atr_pips"].max() - frame["atr_pips"].min()
