"""Kipimo cha TF — DOCTRINE §9.1, §8.4, R5.

Kipimo kinacholinganisha TF mbili lazima kijenge bars **kwa njia ile ile** kwa
zote. `bars_za_TF_zote` inasoma ticks mara moja badala ya mara tatu — faida ya
muda, lakini pia hatari: mabadiliko yoyote kwenye jinsi bars zinavyounganishwa
yangefanya TF moja isilingane na nyingine bila kuonekana, na ulinganisho mzima
ungekuwa wa vitu viwili tofauti.

Kwa hiyo dai kuu hapa ni **usawa**: TF moja kutoka njia ya haraka lazima iwe
sawa KABISA na TF ileile kutoka njia ya polepole.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from src.data import bars as B  # noqa: E402
from src.data import window as win  # noqa: E402

from tf_probe import _q, bars_za_TF_zote  # noqa: E402


def _ticks(start, n, symbol="GBPUSD"):
    stamps = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    rng = np.random.default_rng(len(start) + n)
    bid = 1.30 + np.cumsum(rng.normal(0, 2e-5, n))
    frame = pd.DataFrame({"timestamp": stamps, "bid": bid,
                          "ask": bid + 0.00012})
    frame.attrs["symbol"] = symbol
    return frame


class _Inv:
    """`iter_months` haitumii `inv` hapa — miezi inatolewa moja kwa moja."""


def _panda(monkeypatch, miezi):
    import tf_probe

    def bandia(inv, symbol, stage, **kw):
        for label, chunk in miezi:
            yield label, chunk, type("R", (), {"warnings": []})()

    monkeypatch.setattr(tf_probe, "iter_months", bandia)


@pytest.fixture
def miezi():
    return [("2020-01", _ticks("2020-01-01 00:00", 44_640)),
            ("2020-02", _ticks("2020-02-01 00:00", 41_760))]


def test_TF_moja_inalingana_na_kujenga_peke_yake(monkeypatch, miezi, cfg, capsys):
    """Dai kuu: njia ya haraka haibadilishi bars hata kidogo."""
    _panda(monkeypatch, miezi)
    stage = win.declare("t", "§9.1", win.research_window(cfg), cfg=cfg)

    kwa_tf, n_ticks = bars_za_TF_zote(
        _Inv(), "GBPUSD", ["H1", "M15"], stage,
        day_tz="UTC", months=0, pip=0.0001)
    capsys.readouterr()

    for tf in ("H1", "M15"):
        vipande = [B.build(chunk, tf, stage, day_tz="UTC").bars
                   for _, chunk in miezi]
        peke = pd.concat(vipande).sort_index()
        peke = peke[~peke.index.duplicated(keep="first")]
        pd.testing.assert_frame_equal(kwa_tf[tf], peke, check_like=False)

    assert n_ticks == sum(len(c) for _, c in miezi)


def test_TF_ndogo_ina_bars_NYINGI_zaidi(monkeypatch, miezi, cfg, capsys):
    _panda(monkeypatch, miezi)
    stage = win.declare("t", "§9.1", win.research_window(cfg), cfg=cfg)
    kwa_tf, _ = bars_za_TF_zote(_Inv(), "GBPUSD", ["H1", "M30", "M15"], stage,
                                day_tz="UTC", months=0, pip=0.0001)
    capsys.readouterr()
    assert len(kwa_tf["M15"]) > len(kwa_tf["M30"]) > len(kwa_tf["H1"])
    # M15 ni robo ya saa — uwiano unapaswa kuwa karibu na 4.
    assert 3.5 < len(kwa_tf["M15"]) / len(kwa_tf["H1"]) < 4.5


def test_ticks_zinasomwa_MARA_MOJA(monkeypatch, miezi, cfg, capsys):
    """Ndiyo sababu ya moduli hii kuwepo."""
    import tf_probe

    mara = {"n": 0}

    def bandia(inv, symbol, stage, **kw):
        mara["n"] += 1
        for label, chunk in miezi:
            yield label, chunk, type("R", (), {"warnings": []})()

    monkeypatch.setattr(tf_probe, "iter_months", bandia)
    stage = win.declare("t", "§9.1", win.research_window(cfg), cfg=cfg)
    bars_za_TF_zote(_Inv(), "GBPUSD", ["H1", "M30", "M15"], stage,
                    day_tz="UTC", months=0, pip=0.0001)
    capsys.readouterr()
    assert mara["n"] == 1


def test_months_inakata_kusoma(monkeypatch, miezi, cfg, capsys):
    _panda(monkeypatch, miezi)
    stage = win.declare("t", "§9.1", win.research_window(cfg), cfg=cfg)
    moja, n1 = bars_za_TF_zote(_Inv(), "GBPUSD", ["H1"], stage,
                               day_tz="UTC", months=1, pip=0.0001)
    zote, n2 = bars_za_TF_zote(_Inv(), "GBPUSD", ["H1"], stage,
                               day_tz="UTC", months=0, pip=0.0001)
    capsys.readouterr()
    assert len(moja["H1"]) < len(zote["H1"])
    assert n1 == len(miezi[0][1]) and n2 > n1


def test_TF_isiyo_na_bars_inalipuka(monkeypatch, cfg, capsys):
    """Kurudisha frame tupu kungefanya wastani wote uwe `NaN` kimya."""
    _panda(monkeypatch, [("2020-01", _ticks("2020-01-01 00:00", 0)[:0])])
    stage = win.declare("t", "§9.1", win.research_window(cfg), cfg=cfg)
    with pytest.raises(SystemExit, match="hakuna bars"):
        bars_za_TF_zote(_Inv(), "GBPUSD", ["H1"], stage,
                        day_tz="UTC", months=0, pip=0.0001)
    capsys.readouterr()


# ===========================================================================
# `_q` — wastani, si kilele (§9.1)
# ===========================================================================


def test_q_inaondoa_NaN():
    assert _q([1.0, float("nan"), 3.0], 0.5) == pytest.approx(2.0)


def test_q_ya_orodha_tupu_ni_NaN_si_sifuri():
    import math

    assert math.isnan(_q([], 0.5))
    assert math.isnan(_q([float("nan")], 0.5))
