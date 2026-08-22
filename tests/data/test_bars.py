"""Bar Builder — DOCTRINE §4.1, R1.

Sheria mbili zinazolindwa hapa ni za uvujaji, si za urahisi:

* bar isiyofungwa haitolewi — vinginevyo feature ingejengwa kwa data ambayo
  live isingekuwa nayo bado
* bar tupu haitengenezwi — kujaza mbele kungetengeneza bei isiyowahi kuwepo,
  na bei hiyo ingeonekana inayoweza kutradiwa

Zilizobaki zinathibitisha kwamba aggregation yenyewe ni sahihi: OHLC, spread,
na mipaka ya DST.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import bars as B
from src.data import window as win


def _stage(cfg) -> win.Stage:
    return win.declare("bars", "§4.1", win.research_window(cfg), cfg=cfg)


def _ticks(start: str, n: int, freq: str = "1min", *, bid=1.10000, spread=0.00012,
           symbol="EURUSD"):
    stamps = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    frame = pd.DataFrame({
        "timestamp": stamps,
        "bid": np.full(n, bid),
        "ask": np.full(n, bid + spread),
    })
    frame.attrs["symbol"] = symbol
    return frame


# ===========================================================================
# R1 — bar isiyofungwa haitolewi
# ===========================================================================


def test_bar_ya_mwisho_isiyofungwa_inaachwa(cfg):
    """Ticks 90 za dakika = saa 1.5. H1 inatoa bar MOJA, si mbili.

    Bar ya 01:00 ina dakika 30 pekee. Ikitolewa, `close` yake ingekuwa bei ya
    01:29 ikiitwa bei ya mwisho ya saa — taarifa ambayo live haingekuwa nayo
    hadi 02:00.
    """
    out = B.build(_ticks("2020-06-01 00:00", 90), "H1", _stage(cfg))
    assert out.n_bars_out == 1
    assert out.dropped_open_bar is True
    assert out.bars.index[0] == pd.Timestamp("2020-06-01 00:00", tz="UTC")


def test_bar_inafungwa_pale_tick_ya_baada_ya_mwisho_inapoonekana(cfg):
    """Ushahidi wa kufungwa ni tick kwa muda `≥ mwisho`, si kudhania."""
    out = B.build(_ticks("2020-06-01 00:00", 61), "H1", _stage(cfg))
    assert out.n_bars_out == 1 and out.dropped_open_bar is True

    # Tick moja ya ziada kwa 01:01 haifungui bar ya 01:00 — bado ni ya nusu.
    out2 = B.build(_ticks("2020-06-01 00:00", 62), "H1", _stage(cfg))
    assert out2.n_bars_out == 1


def test_bar_moja_pekee_bila_ushahidi_wa_kufungwa_inatoa_sifuri(cfg):
    """Dataset ya dakika 10 haitoi bar ya H1 hata moja. Ni sahihi."""
    out = B.build(_ticks("2020-06-01 00:00", 10), "H1", _stage(cfg))
    assert out.n_bars_out == 0 and out.dropped_open_bar is True


# ===========================================================================
# Bar tupu haitengenezwi
# ===========================================================================


def test_wikendi_haipati_bars(cfg):
    """Ijumaa → Jumatatu: hakuna bar ya Jumamosi wala Jumapili.

    Kujaza mbele kungetoa bars mbili zenye bei ile ile ya Ijumaa, na strategy
    ingeweza "kutrade" mwishoni mwa wiki kwenye backtest.
    """
    ijumaa = _ticks("2020-06-05 00:00", 60 * 24, freq="1min")     # Ijumaa nzima
    jumatatu = _ticks("2020-06-08 00:00", 60 * 3, freq="1min")    # Jumatatu asubuhi
    frame = pd.concat([ijumaa, jumatatu], ignore_index=True)
    frame.attrs["symbol"] = "EURUSD"

    out = B.build(frame, "H1", _stage(cfg))
    siku = sorted({ts.date().isoweekday() for ts in out.bars.index})
    assert 6 not in siku and 7 not in siku, "wikendi imepata bars"


def test_pengo_la_saa_halijazwi(cfg):
    """Ticks za 00:00–01:00 na 04:00–05:00. Saa 02:00 na 03:00 HAZIPATI bars.

    Jaribio ni juu ya UWEPO, si juu ya idadi: bar ya kujaza ingekuwa na bei ya
    01:00 ikiitwa bei ya 02:00, na strategy ingeweza kuitrade.
    """
    frame = pd.concat(
        [_ticks("2020-06-01 00:00", 61), _ticks("2020-06-01 04:00", 61)],
        ignore_index=True,
    )
    frame.attrs["symbol"] = "EURUSD"
    out = B.build(frame, "H1", _stage(cfg))

    saa = {ts.hour for ts in out.bars.index}
    assert {0, 1, 4} <= saa, "bars zenye ticks hazipo"
    assert 2 not in saa and 3 not in saa, "pengo limejazwa kwa bei isiyowahi kuwepo"


# ===========================================================================
# Aggregation ni sahihi
# ===========================================================================


def test_ohlc_inatoka_MID_si_bid_wala_ask(cfg):
    frame = _ticks("2020-06-01 00:00", 61, bid=1.10000, spread=0.00012)
    out = B.build(frame, "H1", _stage(cfg))
    assert out.bars["open"].iloc[0] == pytest.approx(1.10006)   # mid


def test_ohlc_invariant_inashikilia(cfg):
    rng = np.random.RandomState(11)
    n = 60 * 5
    stamps = pd.date_range("2020-06-01 00:00", periods=n, freq="1min", tz="UTC")
    bid = 1.10 + np.cumsum(rng.normal(0, 1e-5, n))
    frame = pd.DataFrame({"timestamp": stamps, "bid": bid, "ask": bid + 0.00012})
    frame.attrs["symbol"] = "EURUSD"
    out = B.build(frame, "H1", _stage(cfg))
    ok, bad = B.check_ohlc(out.bars)
    assert ok and bad == 0


def test_check_ohlc_inagundua_aggregation_iliyovunjika():
    """Ikivunjika, kila feature inayotokana nayo ni ya uongo kimya kimya."""
    mbovu = pd.DataFrame(
        {"open": [1.10], "high": [1.09], "low": [1.11], "close": [1.10]}
    )
    ok, bad = B.check_ohlc(mbovu)
    assert not ok and bad == 1


def test_takwimu_za_spread_zinahifadhiwa(cfg):
    """RCE §3.1 inahitaji `p95` ya spread kwa kila bar — si wastani pekee."""
    n = 61
    stamps = pd.date_range("2020-06-01 00:00", periods=n, freq="1min", tz="UTC")
    spread = np.full(n, 0.00010)
    spread[30] = 0.00100                       # spike moja ndani ya bar
    frame = pd.DataFrame({"timestamp": stamps, "bid": 1.10, "ask": 1.10 + spread})
    frame.attrs["symbol"] = "EURUSD"

    row = B.build(frame, "H1", _stage(cfg)).bars.iloc[0]
    # PIPS, si bei: 0.00010 ni pip 1.0 kwa EURUSD.
    assert row["spread_p50"] == pytest.approx(1.0)
    assert row["spread_max"] == pytest.approx(10.0)
    assert row["spread_p50"] < row["spread_max"], "spike imefichwa na median"
    assert row["n_ticks"] == 60


def test_spread_iko_kwa_PIPS_si_kwa_bei(cfg):
    """Kila anayeitumia anaidai kwa pips: RCE, `max_spread`, `cost_pips`.

    Ikitolewa kwa bei, kila mmoja anapokea namba ndogo mara 10,000 na hakuna
    anayelipuka — RCE ingeripoti spread 0.00 pips, lots zingekuwa kubwa mno, na
    EV ingekuwa ya bandia bila kosa kuonekana popote.
    """
    stamps = pd.date_range("2020-06-01 00:00", periods=61, freq="1min", tz="UTC")

    eur = pd.DataFrame({"timestamp": stamps, "bid": 1.10, "ask": 1.10 + 0.00012})
    eur.attrs["symbol"] = "EURUSD"
    jpy = pd.DataFrame({"timestamp": stamps, "bid": 110.0, "ask": 110.0 + 0.012})
    jpy.attrs["symbol"] = "USDJPY"

    stage = _stage(cfg)
    assert B.build(eur, "H1", stage).bars.iloc[0]["spread_mean"] == pytest.approx(1.2)
    assert B.build(jpy, "H1", stage).bars.iloc[0]["spread_mean"] == pytest.approx(1.2)


def test_n_m1_bars_ni_dakika_zenye_shughuli(cfg):
    """Kipimo cha ukwasi kinachotoka kwenye data yetu, si kwa broker (§4.2)."""
    stamps = pd.to_datetime(
        ["2020-06-01 00:00:01", "2020-06-01 00:00:02", "2020-06-01 00:05:00",
         "2020-06-01 01:00:00"], utc=True
    )
    frame = pd.DataFrame({"timestamp": stamps, "bid": 1.10, "ask": 1.10012})
    frame.attrs["symbol"] = "EURUSD"
    row = B.build(frame, "H1", _stage(cfg)).bars.iloc[0]
    assert row["n_ticks"] == 3 and row["n_m1_bars"] == 2


# ===========================================================================
# Mipaka ya TF
# ===========================================================================


@pytest.mark.parametrize("tf,dakika", [("M5", 5), ("M15", 15), ("M30", 30),
                                       ("H1", 60), ("H2", 120), ("H4", 240)])
def test_kila_tf_ina_urefu_wake(cfg, tf, dakika):
    n = dakika * 3 + 1
    out = B.build(_ticks("2020-06-01 00:00", n), tf, _stage(cfg))
    assert out.n_bars_out == 3
    assert (out.bars.index[1] - out.bars.index[0]) == pd.Timedelta(minutes=dakika)


def test_tf_isiyojulikana_inakataliwa(cfg):
    with pytest.raises(B.BarError, match="TF isiyojulikana"):
        B.build(_ticks("2020-06-01 00:00", 10), "M7", _stage(cfg))


def test_bars_zinadai_bid_na_ask(cfg):
    """OHLC pekee haiwezi kuwa ingizo — §4.1."""
    frame = pd.DataFrame({"timestamp": pd.to_datetime(["2020-06-01"], utc=True),
                          "close": [1.10]})
    with pytest.raises(B.BarError, match="bid/ask"):
        B.build(frame, "H1", _stage(cfg))


# ===========================================================================
# D1 — mpaka ni siku ya BROKER, na DST haiuvunji
# ===========================================================================


def test_d1_inatumia_siku_ya_broker_si_ya_utc(cfg):
    """Berlin ni UTC+2 kiangazi, kwa hiyo siku inaanza 22:00 UTC ya jana."""
    frame = _ticks("2020-06-01 00:00", 60 * 30, freq="1min")
    out = B.build(frame, "D1", _stage(cfg), day_tz="Europe/Berlin")
    assert out.bars.index[0] == pd.Timestamp("2020-05-31 22:00", tz="UTC")


def test_d1_ya_utc_inaanza_saa_sita_usiku(cfg):
    frame = _ticks("2020-06-01 00:00", 60 * 30, freq="1min")
    out = B.build(frame, "D1", _stage(cfg), day_tz="UTC")
    assert out.bars.index[0] == pd.Timestamp("2020-06-01 00:00", tz="UTC")


def test_siku_ya_dst_ina_urefu_wake_halisi(cfg):
    """2020-10-25: Berlin inarudi UTC+1. Siku hiyo ina saa 25, si 24.

    Kutumia `+1 day` kungehesabu bar kuwa imefungwa saa MOJA kabla ya ukweli —
    mara mbili kwa mwaka, kimya kimya.
    """
    ends = B.bar_ends(
        pd.DatetimeIndex([pd.Timestamp("2020-10-24 22:00", tz="UTC")]),
        "D1", "Europe/Berlin",
    )
    urefu = ends[0] - pd.Timestamp("2020-10-24 22:00", tz="UTC")
    assert urefu == pd.Timedelta(hours=25)


def test_frame_tupu_inatoa_bars_sifuri(cfg):
    tupu = _ticks("2020-06-01", 0)
    out = B.build(tupu, "H1", _stage(cfg))
    assert out.n_bars_out == 0 and not out.dropped_open_bar
