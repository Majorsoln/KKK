"""Gharama kwa saa ya siku — DOCTRINE §8.3.

Calibration A ilionyesha spread ya mpaka wa D1 ni mara 1.6–4.4 ya ya H1 kwenye
symbols zote 12. Sababu ni **saa**, si timeframe. Tests hizi zinathibitisha
kwamba kipimo kinaikamata saa hiyo, na kwamba tz haidhaniwi.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.bars import build
from src.data.window import Stage, Window
from src.validation import cost_by_hour as CH

PIP = 0.0001
STAGE = Stage(
    window=Window(pd.Timestamp("2020-01-01", tz="UTC"), pd.Timestamp("2020-12-31", tz="UTC")),
    name="saa", purpose="gharama kwa saa",
)


def _ticks(*, siku=10, saa_pana: int | None = None, spread=1.0, pana=6.0):
    """Ticks za dakika kwa siku kadhaa; saa moja inaweza kuwa na spread pana."""
    stamps = pd.date_range("2020-06-01", periods=siku * 24 * 60, freq="1min", tz="UTC")
    mid = 1.10 + np.cumsum(np.random.default_rng(4).normal(0, 2e-5, len(stamps)))
    half = np.full(len(stamps), spread) * PIP / 2.0
    if saa_pana is not None:
        half[stamps.hour == saa_pana] = pana * PIP / 2.0
    return pd.DataFrame({"timestamp": stamps, "bid": mid - half, "ask": mid + half})


def _samples(ticks, tz="UTC") -> CH.HourSamples:
    bars = build(ticks, "H1", STAGE).bars
    out = CH.HourSamples(symbol="EURUSD", timeframe="H1", tz=tz, max_gap_seconds=3600)
    return out.add(ticks, bars)


def test_saa_yenye_spread_pana_inaonekana():
    """Jedwali la wastani wa saa 24 lingeificha kabisa."""
    rows = _samples(_ticks(saa_pana=22, spread=1.0, pana=6.0)).table()
    muhtasari = CH.summarise(rows)

    # Mpaka wa bar ya 21:00 unaangukia 22:00 — quote ya kujaza iko ndani ya saa pana.
    assert muhtasari["saa_mbaya"] == 22
    assert muhtasari["ukali"] > 3.0
    assert muhtasari["spread_mbaya"] == pytest.approx(6.0, abs=0.1)


def test_saa_zote_zikiwa_sawa_ukali_ni_karibu_MOJA():
    muhtasari = CH.summarise(_samples(_ticks()).table())
    assert muhtasari["ukali"] == pytest.approx(1.0, abs=0.01)


def test_kila_saa_ina_sampuli_zake():
    rows = _samples(_ticks(siku=5)).table()
    assert len(rows) == 24
    assert sum(r["n"] for r in rows) > 0
    assert all(r["n"] > 0 for r in rows)


def test_tz_inahamisha_saa_si_thamani():
    """Saa ya UTC 22 ni saa 0 Berlin (kiangazi). Spread ile ile, lebo tofauti."""
    ticks = _ticks(saa_pana=22, spread=1.0, pana=6.0)
    utc = CH.summarise(_samples(ticks, "UTC").table())
    berlin = CH.summarise(_samples(ticks, "Europe/Berlin").table())

    assert utc["saa_mbaya"] == 22 and berlin["saa_mbaya"] == 0
    assert berlin["spread_mbaya"] == pytest.approx(utc["spread_mbaya"], abs=1e-9)


def test_ukali_ndicho_kipimo_kinacholinganisha_tz_mbili():
    """Ukali hautegemei vipimo vya tz — ni uwiano ndani ya mgawanyo wake."""
    ticks = _ticks(saa_pana=22)
    utc = CH.summarise(_samples(ticks, "UTC").table())
    berlin = CH.summarise(_samples(ticks, "Europe/Berlin").table())
    # Data bandia haina DST inayohama, kwa hiyo tz zote mbili ni kali sawa.
    assert utc["ukali"] == pytest.approx(berlin["ukali"], rel=0.01)


def test_ripoti_inaweka_alama_kwenye_saa_mbaya():
    rows = _samples(_ticks(saa_pana=22, pana=6.0)).table()
    text = CH.render("EURUSD", rows, "UTC")
    mstari = [r for r in text.splitlines() if r.strip().startswith("22")]
    assert mstari and "<<" in mstari[0]


def test_sampuli_tupu_hazilipuki():
    assert CH.summarise([])["saa_mbaya"] is None
    assert "hakuna sampuli" in CH.render("EURUSD", [], "UTC")
