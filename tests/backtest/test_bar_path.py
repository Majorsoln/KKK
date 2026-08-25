"""Njia ya bei kutoka bars — DOCTRINE §9.2, §11, R12.

Substrate ya hatua ya kutafuta. Ikiwa na kasoro, sakafu ya kelele inapima
utafutaji ambao si ule utakaoendeshwa — na §9 nzima inasimama juu yake.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest import bar_path as BP
from src.backtest.execution import FILL, SL, TP, ExecSpec, execute

PIP = 0.0001


def _bars(n=6, *, o=1.10, spread_pips=1.0, high=None, low=None, close=None,
          freq="1h", start="2020-06-01"):
    index = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    opens = np.full(n, o, dtype=float)
    return pd.DataFrame({
        "open": opens,
        "high": np.full(n, o + 0.0050 if high is None else high, dtype=float),
        "low": np.full(n, o - 0.0050 if low is None else low, dtype=float),
        "close": np.full(n, o if close is None else close, dtype=float),
        "spread_p50": np.full(n, float(spread_pips)),
    }, index=index)


# ===========================================================================
# Umbo
# ===========================================================================


def test_kila_bar_inatoa_quotes_NNE():
    njia = BP.to_path(_bars(6), "H1", symbol="EURUSD", direction="BUY")
    assert len(njia) == 6 * 4
    assert list(njia.columns) == ["timestamp", "bid", "ask"]


def test_quote_ya_kwanza_iko_MWANZONI_KAMILI_wa_bar():
    """Signal ya bar `i` ni mwisho wake = mwanzo wa `i+1` (R11).

    Ikikosa quote hapo, fill ingecheleweshwa robo ya bar bila sababu.
    """
    bars = _bars(3)
    njia = BP.to_path(bars, "H1", symbol="EURUSD", direction="BUY")
    assert njia["timestamp"].iloc[0] == bars.index[0]
    assert njia["timestamp"].iloc[4] == bars.index[1]


def test_quote_ya_mwisho_ya_bar_HAIGONGANI_na_bar_inayofuata():
    bars = _bars(3)
    njia = BP.to_path(bars, "H1", symbol="EURUSD", direction="BUY")
    assert njia["timestamp"].iloc[3] < njia["timestamp"].iloc[4]


def test_nyakati_zinapanda():
    njia = BP.to_path(_bars(20), "H1", symbol="EURUSD", direction="BUY")
    t = njia["timestamp"]
    assert (t.diff().dropna() > pd.Timedelta(0)).all()


def test_D1_inatumia_urefu_wa_SIKU_si_saa():
    bars = _bars(3, freq="1D")
    njia = BP.to_path(bars, "D1", symbol="EURUSD", direction="BUY")
    assert njia["timestamp"].iloc[4] - njia["timestamp"].iloc[0] == pd.Timedelta(days=1)


# ===========================================================================
# UBAYA KWANZA — ndilo chaguo lenye uzito
# ===========================================================================


def test_BUY_inaona_LOW_kabla_ya_HIGH():
    njia = BP.to_path(_bars(1), "H1", symbol="EURUSD", direction="BUY")
    mid = (njia["bid"] + njia["ask"]) / 2.0
    assert mid.iloc[1] < mid.iloc[2], "BUY: `low` lazima itangulie `high`"


def test_SELL_inaona_HIGH_kabla_ya_LOW():
    njia = BP.to_path(_bars(1), "H1", symbol="EURUSD", direction="SELL")
    mid = (njia["bid"] + njia["ask"]) / 2.0
    assert mid.iloc[1] > mid.iloc[2], "SELL: `high` lazima itangulie `low`"


def test_bar_inayogusa_SL_na_TP_inatoa_SL_kwa_pande_ZOTE_MBILI():
    """Ndio sababu `direction` ni parameter.

    Mpangilio mmoja kwa pande zote ungefanya upande mmoja upate SL na mwingine
    TP kwenye bar ILE ILE — upendeleo wa uwakilishi, si wa soko, na
    hauonekani kwenye kipimo chochote.
    """
    bars = _bars(4, spread_pips=0.2)

    for upande in ("BUY", "SELL"):
        njia = BP.to_path(bars, "H1", symbol="EURUSD", direction=upande)
        muda = njia["timestamp"].iloc[0]
        bei = float(njia["ask" if upande == "BUY" else "bid"].iloc[0])
        spec = ExecSpec(symbol="EURUSD", direction=upande, sl_pips=20.0,
                        tp_pips=20.0, deviation_pips=1.0, commission_pips=0.0,
                        time_stop_minutes=180)
        out = execute(njia, spec, signal_time=muda, requested_price=bei)
        assert out.outcome == FILL and out.exit_reason == SL, upande


def test_TP_inapatikana_pale_bar_HAIGUSI_SL():
    bars = _bars(4, high=1.1080, low=1.0999, spread_pips=0.2)
    njia = BP.to_path(bars, "H1", symbol="EURUSD", direction="BUY")
    muda = njia["timestamp"].iloc[0]
    spec = ExecSpec(symbol="EURUSD", direction="BUY", sl_pips=30.0, tp_pips=40.0,
                    deviation_pips=1.0, commission_pips=0.0, time_stop_minutes=180)
    out = execute(njia, spec, signal_time=muda,
                  requested_price=float(njia["ask"].iloc[0]))
    assert out.exit_reason == TP


# ===========================================================================
# Spread — gharama haiwezi kutoweka
# ===========================================================================


def test_spread_inatoka_kwenye_bar_na_ni_ya_PIPS():
    njia = BP.to_path(_bars(2, spread_pips=1.4), "H1", symbol="EURUSD",
                      direction="BUY")
    upana = (njia["ask"] - njia["bid"]) / PIP
    assert upana.round(9).eq(1.4).all()


def test_JPY_inatumia_pip_yake():
    bars = _bars(2, o=110.0, high=110.5, low=109.5, close=110.0, spread_pips=1.4)
    njia = BP.to_path(bars, "H1", symbol="USDJPY", direction="BUY")
    upana = (njia["ask"] - njia["bid"]) / 0.01
    assert upana.round(6).eq(1.4).all()


def test_bar_yenye_spread_isiyojulikana_inatolewa():
    bars = _bars(4)
    bars.loc[bars.index[1], "spread_p50"] = np.nan
    njia = BP.to_path(bars, "H1", symbol="EURUSD", direction="BUY")
    assert len(njia) == 3 * 4


def test_spreads_za_RCE_zinatoka_kwenye_bars_ZILE_ZILE():
    """Orodha bandia ingezima lango la `max_spread` la RCE kimya."""
    bars = _bars(5, spread_pips=2.0)
    bars.loc[bars.index[0], "spread_p50"] = np.nan
    assert BP.spreads_for_rce(bars) == [2.0] * 4


# ===========================================================================
# Mikataba
# ===========================================================================


def test_bila_safu_ya_spread_inalipuka():
    bars = _bars(3).drop(columns=["spread_p50"])
    with pytest.raises(BP.BarPathError, match="spread"):
        BP.to_path(bars, "H1", symbol="EURUSD", direction="BUY")


def test_bila_OHLC_inalipuka():
    with pytest.raises(BP.BarPathError, match="OHLC"):
        BP.to_path(pd.DataFrame({"close": [1.1]}), "H1", symbol="EURUSD",
                   direction="BUY")


def test_bars_tupu_zinalipuka():
    with pytest.raises(BP.BarPathError, match="hakuna bars"):
        BP.to_path(_bars(0), "H1", symbol="EURUSD", direction="BUY")


def test_direction_isiyojulikana_inalipuka():
    with pytest.raises(BP.BarPathError, match="BUY/SELL"):
        BP.to_path(_bars(3), "H1", symbol="EURUSD", direction="LONG")


def test_spread_ZOTE_zisipojulikana_inalipuka():
    bars = _bars(3)
    bars["spread_p50"] = np.nan
    with pytest.raises(BP.BarPathError, match="hakuna bar"):
        BP.to_path(bars, "H1", symbol="EURUSD", direction="BUY")
