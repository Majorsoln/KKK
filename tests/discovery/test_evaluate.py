"""Kutathmini strategy — DOCTRINE §10.2, §5, R11.

Mtego mkuu ni `NaN`. Kwenye pandas `NaN > 5` ni `False`, ambayo inaonekana
salama — lakini `NOT(NaN < 5)` ni `True`. Sharti lililokanushwa lingewaka
wakati wa warmup, na strategy ingeanza kutrade kabla haijajua chochote.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.discovery import evaluate as E
from src.strategies.dna import (
    AND, ATR_MULT, CROSS_ABOVE, CROSS_BELOW, OR, Condition, ConditionSet, Strategy,
)


def _features(n=50, **cols):
    index = pd.date_range("2020-06-01", periods=n, freq="1h", tz="UTC")
    frame = pd.DataFrame(index=index)
    for jina, thamani in cols.items():
        frame[jina] = thamani
    return frame


def _strategy(entry, **kw) -> Strategy:
    base = dict(
        symbol="EURUSD", direction="BUY", entry=entry,
        sl_type=ATR_MULT, sl_param=1.5, tp_type=ATR_MULT, tp_param=3.0,
        time_stop_bars=24,
    )
    base.update(kw)
    return Strategy(**base)


# ===========================================================================
# NaN — mtego mkuu
# ===========================================================================


def test_NaN_haitoi_signal_hata_sharti_likiwa_LIMEKANUSHWA():
    """`NOT(NaN < 5)` ni `True` kwenye pandas. Hapa lazima iwe 'hakuna signal'.

    Bila hivyo, strategy ingewaka kwa kila bar ya warmup — kabla `EMA_200`
    haijajulikana hata kidogo.
    """
    feats = _features(10, RSI_14=[np.nan] * 5 + [10.0] * 5)
    seti = ConditionSet((Condition("RSI_14", "<", 50.0, negate=True),))
    out = E.evaluate_set(seti, feats)

    assert not out.iloc[:5].any(), "NaN imetoa signal kupitia NOT"
    assert not out.iloc[5:].any(), "RSI 10 < 50, NOT inapaswa kuwa False"


def test_NaN_haitoi_signal_kwa_sharti_la_kawaida():
    feats = _features(10, RSI_14=[np.nan] * 5 + [80.0] * 5)
    seti = ConditionSet((Condition("RSI_14", ">", 70.0),))
    out = E.evaluate_set(seti, feats)
    assert not out.iloc[:5].any() and out.iloc[5:].all()


def test_NaN_kwenye_feature_MOJA_inazima_seti_NZIMA():
    """`nan_policy: invalidate` — si kujaza, si kupuuza."""
    feats = _features(10, RSI_14=80.0, ADX_14=[np.nan] * 5 + [30.0] * 5)
    seti = ConditionSet((Condition("RSI_14", ">", 70.0),
                         Condition("ADX_14", ">", 25.0)), logic=OR)
    out = E.evaluate_set(seti, feats)
    assert not out.iloc[:5].any(), "OR imepita ingawa feature moja haijulikani"
    assert out.iloc[5:].all()


def test_valid_mask_inahesabu_bars_zinazoweza_kutathminiwa():
    feats = _features(10, RSI_14=[np.nan] * 3 + [50.0] * 7)
    seti = ConditionSet((Condition("RSI_14", ">", 40.0),))
    assert int(E.valid_mask(seti, feats).sum()) == 7


# ===========================================================================
# Logic
# ===========================================================================


def test_AND_inadai_masharti_YOTE():
    feats = _features(4, RSI_14=[80.0, 80.0, 10.0, 10.0], ADX_14=[30.0, 10.0, 30.0, 10.0])
    seti = ConditionSet((Condition("RSI_14", ">", 70.0),
                         Condition("ADX_14", ">", 25.0)), logic=AND)
    assert list(E.evaluate_set(seti, feats)) == [True, False, False, False]


def test_OR_inadai_MOJA():
    feats = _features(4, RSI_14=[80.0, 80.0, 10.0, 10.0], ADX_14=[30.0, 10.0, 30.0, 10.0])
    seti = ConditionSet((Condition("RSI_14", ">", 70.0),
                         Condition("ADX_14", ">", 25.0)), logic=OR)
    assert list(E.evaluate_set(seti, feats)) == [True, True, True, False]


def test_NOT_inageuza():
    feats = _features(3, RSI_14=[80.0, 50.0, 10.0])
    seti = ConditionSet((Condition("RSI_14", ">", 70.0, negate=True),))
    assert list(E.evaluate_set(seti, feats)) == [False, True, True]


def test_seti_tupu_ni_daima_kweli_pale_features_zinajulikana():
    feats = _features(5, RSI_14=50.0)
    assert E.evaluate_set(ConditionSet(), feats).all()


# ===========================================================================
# Cross — inahitaji bar iliyotangulia
# ===========================================================================


def test_cross_above_inawaka_MARA_MOJA_kwenye_kuvuka():
    feats = _features(5, EMA_20=[1.0, 1.0, 3.0, 4.0, 5.0], EMA_50=[2.0, 2.0, 2.0, 2.0, 2.0])
    seti = ConditionSet((Condition("EMA_20", CROSS_ABOVE, "EMA_50"),))
    assert list(E.evaluate_set(seti, feats)) == [False, False, True, False, False]


def test_cross_below_ni_kinyume():
    feats = _features(4, EMA_20=[3.0, 3.0, 1.0, 0.5], EMA_50=[2.0, 2.0, 2.0, 2.0])
    seti = ConditionSet((Condition("EMA_20", CROSS_BELOW, "EMA_50"),))
    assert list(E.evaluate_set(seti, feats)) == [False, False, True, False]


def test_cross_ya_bar_ya_kwanza_HAIWAKI():
    """Hakuna bar iliyotangulia, kwa hiyo hakuna kuvuka kunakojulikana."""
    feats = _features(3, EMA_20=[5.0, 5.0, 5.0], EMA_50=[2.0, 2.0, 2.0])
    seti = ConditionSet((Condition("EMA_20", CROSS_ABOVE, "EMA_50"),))
    assert not E.evaluate_set(seti, feats).iloc[0]


def test_kulinganisha_feature_na_feature():
    feats = _features(3, EMA_20=[1.0, 3.0, 5.0], EMA_50=[2.0, 2.0, 2.0])
    seti = ConditionSet((Condition("EMA_20", ">", "EMA_50"),))
    assert list(E.evaluate_set(seti, feats)) == [False, True, True]


# ===========================================================================
# Signals — muda ni MWISHO wa bar (R11)
# ===========================================================================


def test_muda_wa_signal_ni_MWISHO_wa_bar_si_mwanzo():
    """Kutumia index moja kwa moja kungeweka uamuzi saa moja kabla ya taarifa."""
    feats = _features(3, RSI_14=[80.0, 10.0, 80.0])
    s = _strategy(ConditionSet((Condition("RSI_14", ">", 70.0),)))
    out = E.signals(s, feats, timeframe="H1")

    assert out.n_signals == 2
    assert list(out.times) == [feats.index[0] + pd.Timedelta(hours=1),
                               feats.index[2] + pd.Timedelta(hours=1)]


def test_signal_rate_inatumia_bars_HALALI_kama_denominator():
    """Bars za warmup hazikuwahi kuwa nafasi ya kutrade."""
    feats = _features(10, RSI_14=[np.nan] * 5 + [80.0] * 5)
    s = _strategy(ConditionSet((Condition("RSI_14", ">", 70.0),)))
    out = E.signals(s, feats, timeframe="H1")

    assert out.n_bars == 10 and out.n_valid == 5 and out.n_signals == 5
    assert out.signal_rate == pytest.approx(1.0)


def test_signals_zinajielezea():
    feats = _features(5, RSI_14=80.0)
    s = _strategy(ConditionSet((Condition("RSI_14", ">", 70.0),)))
    out = E.signals(s, feats, timeframe="H1")
    assert s.strategy_id in out.render()
    assert out.to_json()["n_signals"] == 5


# ===========================================================================
# Exit
# ===========================================================================


def test_exit_bila_sheria_inatoa_nyakati_TUPU():
    """SL/TP/time_stop ziko kwenye path ya ticks — hizi ni za ziada."""
    feats = _features(5, RSI_14=80.0)
    s = _strategy(ConditionSet((Condition("RSI_14", ">", 70.0),)))
    assert len(E.exit_signals(s, feats, timeframe="H1")) == 0


def test_exit_yenye_sheria_inatoa_nyakati():
    feats = _features(4, RSI_14=[80.0, 20.0, 80.0, 20.0])
    s = _strategy(ConditionSet((Condition("RSI_14", ">", 70.0),)),
                  exit=ConditionSet((Condition("RSI_14", "<", 30.0),)))
    assert len(E.exit_signals(s, feats, timeframe="H1")) == 2


# ===========================================================================
# Mikataba
# ===========================================================================


def test_feature_isiyopo_inalipuka():
    feats = _features(3, RSI_14=50.0)
    seti = ConditionSet((Condition("ADX_14", ">", 25.0),))
    with pytest.raises(E.EvaluateError, match="ADX_14"):
        E.evaluate_set(seti, feats)


def test_features_tupu_zinalipuka():
    s = _strategy(ConditionSet((Condition("RSI_14", ">", 70.0),)))
    with pytest.raises(E.EvaluateError, match="hakuna features"):
        E.signals(s, _features(0, RSI_14=[]), timeframe="H1")


# ===========================================================================
# Entry isiyochagua chochote si strategy
# ===========================================================================


def test_isiyowaka_kabisa_ni_NO_SIGNALS():
    feats = _features(10, RSI_14=10.0)
    s = _strategy(ConditionSet((Condition("RSI_14", ">", 70.0),)))
    out = E.signals(s, feats, timeframe="H1")
    assert out.n_signals == 0 and out.degenerate == E.NO_SIGNALS


def test_inayowaka_kila_bar_ni_ALWAYS_IN():
    """Tautolojia `A > x OR A < x` ni kweli kila mahali — si sheria ya kuingia."""
    feats = _features(10, close_pos_in_range=np.linspace(0.2, 0.9, 10))
    seti = ConditionSet((Condition("close_pos_in_range", ">", 0.1),
                         Condition("close_pos_in_range", "<", 0.1)), logic=OR)
    out = E.signals(_strategy(seti), feats, timeframe="H1")
    assert out.signal_rate == pytest.approx(1.0)
    assert out.degenerate == E.ALWAYS_IN


def test_kizingiti_nje_ya_masafa_ya_data_pia_ni_ALWAYS_IN():
    """`return_1 < 0.005` pale returns ni ±0.0001 huchagua kila kitu."""
    feats = _features(10, return_1=np.linspace(-1e-4, 1e-4, 10))
    out = E.signals(_strategy(ConditionSet((Condition("return_1", "<", 0.005),))),
                    feats, timeframe="H1")
    assert out.degenerate == E.ALWAYS_IN


def test_bars_zote_zikiwa_warmup_ni_NO_VALID_BARS():
    feats = _features(5, RSI_14=[np.nan] * 5)
    out = E.signals(_strategy(ConditionSet((Condition("RSI_14", ">", 70.0),))),
                    feats, timeframe="H1")
    assert out.degenerate == E.NO_VALID_BARS


def test_strategy_yenye_uteuzi_HAINA_alama():
    feats = _features(10, RSI_14=[80.0, 10.0] * 5)
    out = E.signals(_strategy(ConditionSet((Condition("RSI_14", ">", 70.0),))),
                    feats, timeframe="H1")
    assert out.signal_rate == pytest.approx(0.5)
    assert out.degenerate == ""


def test_hakuna_kizingiti_cha_kati_kilichobuniwa():
    """§2 — kiwango cha kati ni TAARIFA kwa §13, si lango.

    Kizingiti kama "chini ya 1%" kingekuwa constant isiyopimwa.
    """
    feats = _features(1000, RSI_14=[80.0] + [10.0] * 999)
    out = E.signals(_strategy(ConditionSet((Condition("RSI_14", ">", 70.0),))),
                    feats, timeframe="H1")
    assert out.signal_rate == pytest.approx(0.001)
    assert out.degenerate == "", "kiwango cha 0.1% kimekataliwa kama lango"
