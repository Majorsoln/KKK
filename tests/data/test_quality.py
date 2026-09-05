"""Ukaguzi wa ubora wa ticks — DOCTRINE §4.3, R1.

Kila test hapa inaiga **njia moja ambayo data mbovu ingejionyesha kama faida**,
si kama kosa. Ndiyo sababu ukaguzi huu unaendeshwa kila upakiaji badala ya mara
moja: ukikosekana, hakuna kitu kingine kwenye pipeline kitakachoona tofauti.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.data import quality as q
from src.data import window as win


def _stage(cfg) -> win.Stage:
    return win.declare("ukaguzi", "§4.3", win.research_window(cfg), cfg=cfg)


def _ticks(n: int = 100, start: str = "2020-06-01 08:00", symbol: str = "EURUSD"):
    """Ticks safi za Jumatatu — msingi ambao kila test inauharibu kwa njia moja."""
    stamps = pd.date_range(start, periods=n, freq="1s", tz="UTC")
    frame = pd.DataFrame({
        "timestamp": stamps,
        "bid": np.full(n, 1.10000),
        "ask": np.full(n, 1.10012),
    })
    frame.attrs["symbol"] = symbol
    return frame


# ===========================================================================
# Msingi
# ===========================================================================


def test_ticks_safi_zinapita(cfg):
    report = q.check_ticks(_ticks(), _stage(cfg))
    assert report.passed and not report.fatal and not report.warnings
    assert report.n_ticks == 100


def test_ripoti_inachapisha_kila_ukaguzi(cfg):
    """R23 — hakuna ukaguzi unaokaa kimya, hata uliopita."""
    text = q.check_ticks(_ticks(), _stage(cfg)).render()
    for name in ("timezone", "mpangilio", "duplicates", "quotes_zilizovuka",
                 "bei_halali", "wikendi", "mpaka_wa_dirisha"):
        assert name in text
    assert "IMEPITA" in text


def test_frame_tupu_ni_FATAL(cfg):
    tupu = _ticks(0)
    report = q.check_ticks(tupu, _stage(cfg))
    assert not report.passed


# ===========================================================================
# Njia ambazo data mbovu ingejionyesha kama faida
# ===========================================================================


def test_quote_iliyovuka_ni_FATAL(cfg):
    """`bid > ask` inatoa spread HASI → gharama HASI → pesa ya bure.

    Ndiyo aina hatari zaidi ya data mbovu: haionekani kama kosa kwenye matokeo;
    inaonekana kama edge.
    """
    frame = _ticks()
    frame.loc[7, "bid"] = 1.10050          # juu ya ask
    report = q.check_ticks(frame, _stage(cfg))
    crossed = next(c for c in report.checks if c.name == "quotes_zilizovuka")
    assert not crossed.passed and crossed.severity == q.FATAL and crossed.count == 1
    assert not report.passed


def test_spread_hasi_ingeleta_gharama_hasi(cfg):
    """Uthibitisho wa kiuchumi wa test iliyotangulia, si wa kimuundo."""
    frame = _ticks()
    frame.loc[7, "bid"] = 1.10050
    spread = frame["ask"] - frame["bid"]
    assert (spread < 0).any(), "muundo wa test wenyewe umevunjika"
    assert not q.check_ticks(frame, _stage(cfg)).passed


def test_timestamps_zinazorudi_nyuma_ni_FATAL(cfg):
    frame = _ticks()
    frame.loc[50, "timestamp"] = frame.loc[10, "timestamp"]
    frame = frame.sort_index()
    report = q.check_ticks(frame, _stage(cfg))
    order = next(c for c in report.checks if c.name == "mpangilio")
    assert not order.passed and order.severity == q.FATAL


def test_duplicates_kamili_ni_FATAL(cfg):
    frame = pd.concat([_ticks(10), _ticks(10)], ignore_index=True)
    frame.attrs["symbol"] = "EURUSD"
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    report = q.check_ticks(frame, _stage(cfg))
    dup = next(c for c in report.checks if c.name == "duplicates")
    assert not dup.passed and dup.count == 10


def test_tick_yenye_bei_ya_sifuri_ni_FATAL(cfg):
    frame = _ticks()
    frame.loc[3, "ask"] = 0.0
    assert not q.check_ticks(frame, _stage(cfg)).passed


def test_timestamps_bila_timezone_ni_FATAL(cfg):
    """'Naive' inamaanisha kudhania timezone, na kudhania kunahamisha kila bar."""
    frame = _ticks()
    frame["timestamp"] = frame["timestamp"].dt.tz_localize(None)
    report = q.check_ticks(frame, _stage(cfg))
    tz = next(c for c in report.checks if c.name == "timezone")
    assert not tz.passed and tz.severity == q.FATAL


# ===========================================================================
# R18 — mpaka unakaguliwa hata baada ya clip()
# ===========================================================================


def test_tick_ya_holdout_ndani_ya_frame_ni_FATAL(cfg):
    """Ukaguzi haumtegemei mpigaji simu kukumbuka `clip()`.

    R18 ni muhimu mno kuachwa kwa nidhamu. Ikiwa frame ina tick ya 2025 na
    hatua ni ya utafiti, ukaguzi unasimamisha — hata kama kila kitu kingine
    ni safi.
    """
    frame = _ticks(5, start="2025-06-02 08:00")
    report = q.check_ticks(frame, _stage(cfg))
    mpaka = next(c for c in report.checks if c.name == "mpaka_wa_dirisha")
    assert not mpaka.passed and mpaka.severity == q.FATAL and mpaka.count == 5


def test_clip_kisha_ukaguzi_kunapita(cfg):
    """Njia sahihi: kata kwanza, kagua baadaye — na sasa hakuna FATAL."""
    stage = _stage(cfg)
    frame = pd.concat(
        [_ticks(5, "2020-06-01 08:00"), _ticks(5, "2025-06-02 08:00")],
        ignore_index=True,
    )
    frame.attrs["symbol"] = "EURUSD"
    report = q.check_ticks(win.clip(frame, stage), stage)
    assert report.passed and report.n_ticks == 5


# ===========================================================================
# Warnings — zinaripotiwa, hazizuii
# ===========================================================================


def test_tick_ya_jumamosi_ni_ONYO_si_FATAL(cfg):
    """Soko la FX limefungwa Jumamosi. Ni dalili ya timezone, si sababu ya kusimama."""
    frame = _ticks(5, start="2020-06-06 08:00")     # 2020-06-06 ni Jumamosi
    report = q.check_ticks(frame, _stage(cfg))
    wknd = next(c for c in report.checks if c.name == "wikendi")
    assert not wknd.passed and wknd.severity == q.WARN
    assert report.passed, "onyo halipaswi kusimamisha"


def test_spread_kubwa_ni_ONYO_ikiwa_kikomo_kimetolewa(cfg):
    frame = _ticks()
    frame.loc[9, "ask"] = 1.15000                    # ~500 pips
    report = q.check_ticks(frame, _stage(cfg), max_spread_pips=20.0, pip=0.0001)
    wide = next(c for c in report.checks if c.name == "spread_kubwa")
    assert not wide.passed and wide.severity == q.WARN and report.passed


def test_spread_haikaguliwi_bila_kikomo(cfg):
    """Bila `max_spread_pips`, hakuna ukaguzi wa kubuni — kimya ni bora kuliko kudhania."""
    names = [c.name for c in q.check_ticks(_ticks(), _stage(cfg)).checks]
    assert "spread_kubwa" not in names


def test_pengo_kubwa_kuliko_wikendi_ni_ONYO(cfg):
    frame = pd.concat(
        [_ticks(5, "2020-06-01 08:00"), _ticks(5, "2020-06-20 08:00")],
        ignore_index=True,
    )
    check = q.calendar_gaps(frame, _stage(cfg))
    assert not check.passed and check.severity == q.WARN and check.count == 1


def test_wikendi_ya_kawaida_si_pengo(cfg):
    """Saa ~50 za ukimya ni Ijumaa→Jumapili, si data iliyokosekana."""
    frame = pd.concat(
        [_ticks(3, "2020-06-05 20:00"), _ticks(3, "2020-06-07 21:00")],
        ignore_index=True,
    )
    assert q.calendar_gaps(frame, _stage(cfg)).passed


# ===========================================================================
# Ushahidi
# ===========================================================================


def test_ripoti_inaandikwa_ikiwa_na_dirisha_lililotangazwa(cfg, tmp_path):
    """§16.1: ushahidi unabeba {start, end, purpose}, si matokeo pekee."""
    import json

    stage = _stage(cfg)
    path = q.check_ticks(_ticks(), stage).write(tmp_path / "quality.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["start"] == "2016-01-04" and payload["end"] == "2024-03-31"
    assert payload["purpose"] == "§4.3"
    assert len(payload["checks"]) >= 7


def test_safu_zisizopo_zinasimamisha_mara_moja(cfg):
    with pytest.raises(q.QualityError, match="bid/ask"):
        q.check_ticks(pd.DataFrame({"timestamp": [], "close": []}), _stage(cfg))
