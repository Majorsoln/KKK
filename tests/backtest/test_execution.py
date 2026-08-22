"""Hatua ya pili ya utekelezaji — DOCTRINE §11.1–§11.4, R13.

Tests hizi zinapima mambo manne ambayo, yakikosewa, hayajionyeshi kama makosa
bali kama matokeo:

* `NO_FILL` — order isiyojazwa ikihesabiwa kama trade
* njia ya trade — spread ikitozwa mara mbili, au isipotozwa kabisa
* `UNRESOLVED` — trade isiyofika mwisho ikihesabiwa kama `TIME_STOP`
* `MFE/MAE` — zikipimwa baada ya kutoka badala ya hadi kutoka
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest import execution as X
from src.backtest.ledger import FILL, NO_FILL

T0 = pd.Timestamp("2020-06-01 09:00", tz="UTC")
PIP = 0.0001


def _spec(**kw) -> X.ExecSpec:
    base = dict(symbol="EURUSD", direction="BUY", sl_pips=30.0, tp_pips=60.0,
                deviation_pips=0.3, commission_pips=0.7, time_stop_minutes=24 * 60)
    base.update(kw)
    return X.ExecSpec(**base)


def _ticks(mids, *, start=T0, freq="1min", spread_pips=1.2):
    """Ticks kutoka mfululizo wa mid, kwa spread thabiti."""
    mids = np.asarray(mids, dtype=float)
    half = spread_pips * PIP / 2.0
    return pd.DataFrame({
        "timestamp": pd.date_range(start, periods=len(mids), freq=freq, tz="UTC"),
        "bid": mids - half,
        "ask": mids + half,
    })


def _run(mids, spec=None, *, requested=None, **kw):
    spec = spec or _spec()
    ticks = _ticks(mids, **kw)
    req = requested if requested is not None else float(ticks["ask"].iloc[0])
    return X.execute(ticks, spec, signal_time=T0, requested_price=req)


# ===========================================================================
# FILL dhidi ya NO_FILL
# ===========================================================================


def test_bei_ikihama_zaidi_ya_cap_HAIJAZI(cfg_risk):
    """RCE §3.2: order inayozidi `deviation` HAIJAZI badala ya kujaza vibaya."""
    mids = [1.10000] * 5
    ticks = _ticks(mids)
    # Omba bei ya chini sana kuliko ask halisi → slippage kubwa
    out = X.execute(ticks, _spec(deviation_pips=0.3), signal_time=T0,
                    requested_price=float(ticks["ask"].iloc[0]) - 5 * PIP)
    assert out.outcome == NO_FILL
    assert out.reject_reason == X.SLIPPAGE_CAP
    assert out.fill_slippage_pips == pytest.approx(5.0, abs=1e-6)


def test_slippage_ndani_ya_cap_INAJAZA():
    ticks = _ticks([1.10000] * 5)
    out = X.execute(ticks, _spec(deviation_pips=0.5), signal_time=T0,
                    requested_price=float(ticks["ask"].iloc[0]) - 0.3 * PIP)
    assert out.outcome == FILL and out.fill_slippage_pips == pytest.approx(0.3, abs=1e-6)


def test_slippage_inayotufaidi_haizuii_fill():
    """Bei ikiwa BORA kuliko iliyoombwa, hakuna sababu ya kukataa."""
    ticks = _ticks([1.10000] * 5)
    out = X.execute(ticks, _spec(), signal_time=T0,
                    requested_price=float(ticks["ask"].iloc[0]) + 2 * PIP)
    assert out.outcome == FILL and out.fill_slippage_pips < 0


def test_hakuna_ticks_baada_ya_signal_ni_NO_FILL():
    ticks = _ticks([1.10] * 3, start=T0 - pd.Timedelta(hours=2))
    out = X.execute(ticks, _spec(), signal_time=T0, requested_price=1.10)
    assert out.outcome == NO_FILL and out.reject_reason == X.NO_TICKS


# ===========================================================================
# Njia ya TRADE — spread iko ndani, haitozwi mara mbili
# ===========================================================================


def test_buy_inaingia_kwa_ASK_na_kutoka_kwa_BID():
    ticks = _ticks([1.10000, 1.10700])
    out = X.execute(ticks, _spec(tp_pips=60.0), signal_time=T0,
                    requested_price=float(ticks["ask"].iloc[0]))
    assert out.entry_price == pytest.approx(float(ticks["ask"].iloc[0]))
    assert out.exit_price == pytest.approx(float(ticks["bid"].iloc[1]))


def test_spread_haitozwi_MARA_MBILI():
    """Trade ya kwenda-kurudi bila mwendo wa mid inapoteza spread MOJA, si mbili.

    Mid haibadiliki hata kidogo. Hasara pekee inapaswa kuwa round-trip spread
    (pips 1.2) pamoja na commission (0.7) — jumla 1.9. Spread ikitozwa tena
    kando, ingekuwa 3.1, na kila strategy ingeonekana mbaya kwa kiasi ambacho
    hakuna mtu angekigundua kwenye jumla.
    """
    out = _run([1.10000] * 10, _spec(time_stop_minutes=5), spread_pips=1.2)
    assert out.exit_reason == X.TIME_STOP
    assert out.gross_pips == pytest.approx(-1.2, abs=1e-6)
    assert out.net_pips == pytest.approx(-1.9, abs=1e-6)


def test_njia_mbili_zinatoa_namba_ILE_ILE(cfg_risk):
    """§11.4 / R7 — uhakiki uliojengwa ndani, si test ya nje."""
    rng = np.random.RandomState(3)
    mids = 1.10 + np.cumsum(rng.normal(0, 3e-5, 200))
    out = _run(mids, _spec(time_stop_minutes=90))
    assert out.outcome == FILL
    assert out.reconciliation_error < 1e-9, (
        "njia ya trade na ya mid hazitoi net ile ile — mojawapo ina kasoro"
    )


def test_commission_inatozwa_MARA_MOJA():
    out = _run([1.10000] * 10, _spec(time_stop_minutes=5, commission_pips=0.7))
    assert out.commission_pips == pytest.approx(0.7)
    assert out.net_pips == pytest.approx(out.gross_pips - 0.7, abs=1e-9)


def test_swap_inatozwa_kwa_kila_usiku():
    """Trade inayovuka mipaka miwili ya siku inalipa swap mbili."""
    mids = [1.10000] * (60 * 24 * 2 + 10)
    out = _run(mids, _spec(time_stop_minutes=60 * 24 * 2, swap_pips_per_night=-0.5))
    assert out.swap_pips == pytest.approx(-1.0, abs=1e-9)
    assert out.net_pips == pytest.approx(
        out.gross_pips - out.commission_pips - out.swap_pips, abs=1e-9
    )


# ===========================================================================
# Barriers
# ===========================================================================


def test_tp_inagusa_kwanza():
    out = _run([1.10000, 1.10030, 1.10700], _spec(tp_pips=60.0, sl_pips=30.0))
    assert out.exit_reason == X.TP and out.gross_pips > 0


def test_sl_inagusa_kwanza():
    out = _run([1.10000, 1.09970, 1.09600], _spec(tp_pips=60.0, sl_pips=30.0))
    assert out.exit_reason == X.SL and out.gross_pips < 0


def test_tick_moja_haiwezi_kugusa_barriers_ZOTE_MBILI():
    """BUY inatoka kwa `bid`; TP iko juu na SL chini ya bei ILE ILE.

    Kwa hiyo hakuna utata wa 'nani kwanza' kwenye kiwango cha tick — tofauti na
    bars, ambapo `high` na `low` za bar moja zinaweza kugusa zote mbili.
    """
    spec = _spec(tp_pips=10.0, sl_pips=10.0)
    out = _run([1.10000, 1.10200], spec)
    assert out.exit_reason in (X.TP, X.SL)
    assert out.exit_reason == X.TP


def test_time_stop_inatumika_ikiwa_hakuna_barrier(cfg_risk):
    out = _run([1.10000] * 200, _spec(time_stop_minutes=60))
    assert out.exit_reason == X.TIME_STOP
    assert out.holding_minutes == pytest.approx(60.0, abs=1.0)


def test_sell_inageuza_pande_zote():
    ticks = _ticks([1.10000, 1.09300])
    spec = _spec(direction="SELL", tp_pips=60.0)
    out = X.execute(ticks, spec, signal_time=T0,
                    requested_price=float(ticks["bid"].iloc[0]))
    assert out.entry_price == pytest.approx(float(ticks["bid"].iloc[0]))
    assert out.exit_price == pytest.approx(float(ticks["ask"].iloc[1]))
    assert out.exit_reason == X.TP and out.gross_pips > 0


# ===========================================================================
# UNRESOLVED — trade isiyofika mwisho haihesabiki
# ===========================================================================


def test_data_ikiisha_kabla_ya_kutoka_ni_UNRESOLVED():
    """Si `TIME_STOP` na si hasara. Ni kama bar isiyofungwa: haijatokea bado.

    Ikihesabiwa kama `TIME_STOP`, kila run ingepata trade ya ziada mwishoni
    yenye tokeo la kubuni.
    """
    out = _run([1.10000] * 5, _spec(time_stop_minutes=24 * 60))
    assert out.exit_reason == X.UNRESOLVED
    assert not out.resolved


def test_trade_iliyofika_mwisho_ni_resolved():
    out = _run([1.10000, 1.10700], _spec(tp_pips=60.0))
    assert out.resolved and out.exit_reason == X.TP


# ===========================================================================
# MFE / MAE
# ===========================================================================


def test_mfe_na_mae_zinapimwa_HADI_kutoka_si_baada():
    """Mwendo baada ya kutoka hauhusiki — hatukuwa ndani ya soko.

    Bei inapanda +40 pips, inashuka hadi SL, kisha inapanda +300. MFE ni 40,
    si 300.
    """
    mids = [1.10000, 1.10400, 1.09970, 1.09600, 1.13000]
    out = _run(mids, _spec(sl_pips=30.0, tp_pips=200.0))
    assert out.exit_reason == X.SL
    assert out.mfe_pips == pytest.approx(40.0 - 1.2, abs=0.2)
    assert out.mfe_pips < 100, "mwendo wa baada ya kutoka umeingia kwenye MFE"


def test_mae_ni_hasi_au_sifuri():
    out = _run([1.10000, 1.09950, 1.10700], _spec(tp_pips=60.0))
    assert out.mae_pips < 0 and out.mfe_pips > 0


def test_n_ticks_ni_za_ndani_ya_trade_pekee():
    out = _run([1.10000, 1.10030, 1.10700] + [1.20] * 50, _spec(tp_pips=60.0))
    assert out.n_ticks == 3


# ===========================================================================
# Mikataba
# ===========================================================================


def test_ticks_zinadai_bid_na_ask():
    frame = pd.DataFrame({"timestamp": [T0], "close": [1.10]})
    with pytest.raises(X.ExecutionError, match="bid/ask"):
        X.execute(frame, _spec(), signal_time=T0, requested_price=1.10)


def test_pip_ya_jpy_ni_kubwa_mara_mia():
    assert _spec(symbol="USDJPY").pip == pytest.approx(0.01)
    assert _spec(symbol="EURUSD").pip == pytest.approx(0.0001)
