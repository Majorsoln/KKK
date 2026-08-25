"""Checkpoint ya Calibration B — DOCTRINE §9.2, R5.

Run ya kweli ni masaa mengi. Bila checkpoint, mashine inayozimika saa ya 40
inapoteza zote — na si muda pekee, ni **ushahidi** ambao R5 inaudai.

Hatari kubwa zaidi si kupoteza, ni **kuchanganya**: kuendelea kwenye run yenye
vigezo tofauti kungetoa jedwali lenye replicates za `K=200` na za `K=1000`
pamoja, na `variants_tested` isingesema ukweli kuhusu utafutaji wowote. Hilo
lisingeonekana kwenye faili ya mwisho — namba zote zingeonekana halali.
"""

from __future__ import annotations

import json

import pytest

from src.validation import noise_floor as NF
from src.validation import surrogates as S


def _matokeo(x: float) -> dict:
    return {"sharpe": x, "net_pips_month": x * 10.0, NF.VARIANTS_KEY: 20}


# ===========================================================================
# Kuhifadhi na kurudisha
# ===========================================================================


def test_iliyohifadhiwa_inarudishwa(tmp_path):
    ck = NF.Checkpoint.open(tmp_path / "c.jsonl", "alama-1")
    ck.put(S.BLOCK, 0, _matokeo(1.5))
    assert ck.get(S.BLOCK, 0) == _matokeo(1.5)
    assert ck.get(S.BLOCK, 1) is None


def test_inasomeka_baada_ya_kufunguliwa_upya(tmp_path):
    njia = tmp_path / "c.jsonl"
    kwanza = NF.Checkpoint.open(njia, "alama-1")
    kwanza.put(S.BLOCK, 0, _matokeo(1.5))
    kwanza.put(S.REGIME, 3, _matokeo(2.5))

    pili = NF.Checkpoint.open(njia, "alama-1")
    assert len(pili) == 2
    assert pili.get(S.REGIME, 3)["sharpe"] == 2.5


def test_kila_replicate_inaandikwa_MARA_MOJA_inapokamilika(tmp_path):
    """Kuandika mwishoni kungepoteza kila kitu mashine ikizimika katikati."""
    njia = tmp_path / "c.jsonl"
    ck = NF.Checkpoint.open(njia, "alama-1")
    ck.put(S.BLOCK, 0, _matokeo(1.0))
    # Bila kufunga wala kumaliza — faili tayari ina row.
    mistari = njia.read_text(encoding="utf-8").splitlines()
    assert len(mistari) == 2                      # kichwa + row moja


# ===========================================================================
# Fingerprint — kinga dhidi ya kuchanganya
# ===========================================================================


def test_vigezo_tofauti_vinaanza_UPYA_badala_ya_kuchanganya(tmp_path):
    njia = tmp_path / "c.jsonl"
    kwanza = NF.Checkpoint.open(njia, "K=200")
    kwanza.put(S.BLOCK, 0, _matokeo(1.5))

    pili = NF.Checkpoint.open(njia, "K=1000")
    assert len(pili) == 0, "replicate ya vigezo vingine imerudishwa"
    assert pili.get(S.BLOCK, 0) is None


def test_mabadiliko_yanaelezwa_si_kufanyika_kimya(tmp_path):
    njia = tmp_path / "c.jsonl"
    NF.Checkpoint.open(njia, "K=200").put(S.BLOCK, 0, _matokeo(1.5))

    maneno: list[str] = []
    NF.Checkpoint.open(njia, "K=1000", progress=maneno.append)
    assert any("TOFAUTI" in m for m in maneno)
    assert any("K=200" in m and "K=1000" in m for m in maneno)


def test_mstari_uliokatika_unarukwa_si_kulipuka(tmp_path):
    """Mashine ikizimika katikati ya kuandika, row ya mwisho inakatika.

    Kuilipukia kungefanya checkpoint iwe kizuizi badala ya kinga; replicate hiyo
    ina seed ile ile, kwa hiyo kuiendesha upya kunatoa jibu lile lile.
    """
    njia = tmp_path / "c.jsonl"
    ck = NF.Checkpoint.open(njia, "alama-1")
    ck.put(S.BLOCK, 0, _matokeo(1.5))
    with njia.open("a", encoding="utf-8") as fh:
        fh.write('{"family": "block_resa')          # imekatika

    tena = NF.Checkpoint.open(njia, "alama-1")
    assert len(tena) == 1 and tena.get(S.BLOCK, 0)["sharpe"] == 1.5


# ===========================================================================
# `calibrate()` inaitumia
# ===========================================================================


def _frame(n=400, seed=2):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    index = pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC")
    close = 1.10 + np.cumsum(rng.normal(0, 3e-4, n))
    return pd.DataFrame({
        "open": close, "high": close + 5e-4, "low": close - 5e-4, "close": close,
        "spread_p50": 1.0,
    }, index=index)


def test_calibrate_HAIENDESHI_UPYA_iliyohifadhiwa(tmp_path):
    frame = _frame()
    ck = NF.Checkpoint.open(tmp_path / "c.jsonl", "alama-1")

    mara = {"n": 0}

    def pipeline(_sur):
        mara["n"] += 1
        return _matokeo(1.0 + mara["n"] * 0.01)

    NF.calibrate(frame, pipeline, n_replicates=NF.MIN_REPLICATES, seed=1,
                 checkpoint=ck, progress=None)
    kwanza = mara["n"]
    assert kwanza == NF.MIN_REPLICATES * len(S.FAMILIES)

    # Run ya pili juu ya checkpoint ile ile: hakuna inayoendeshwa tena.
    NF.calibrate(frame, pipeline, n_replicates=NF.MIN_REPLICATES, seed=1,
                 checkpoint=ck, progress=None)
    assert mara["n"] == kwanza, "replicate imeendeshwa upya ingawa ipo"


def test_kuendelea_kunatoa_jedwali_LILE_LILE(tmp_path):
    """Ndilo dai zima: kukatika hakubadilishi jibu."""
    frame = _frame()

    def pipeline(sur):
        import numpy as np

        return _matokeo(float(np.asarray(sur["close"]).std() * 1000))

    kamili = NF.calibrate(frame, pipeline, n_replicates=NF.MIN_REPLICATES,
                          seed=7, progress=None)

    ck = NF.Checkpoint.open(tmp_path / "c.jsonl", "alama-1")
    kwa_vipande = NF.calibrate(frame, pipeline, n_replicates=NF.MIN_REPLICATES,
                               seed=7, checkpoint=ck, progress=None)
    tena = NF.calibrate(frame, pipeline, n_replicates=NF.MIN_REPLICATES,
                        seed=7, checkpoint=ck, progress=None)

    for jedwali in (kwa_vipande, tena):
        assert set(jedwali.entries) == set(kamili.entries)
        for jina, e in kamili.entries.items():
            assert jedwali.entries[jina].floor == pytest.approx(e.floor)


def test_matokeo_yaliyohifadhiwa_bado_yanakaguliwa(tmp_path):
    """Checkpoint si njia ya kuzunguka `_check_result`.

    Faili iliyoharibiwa kwa mkono isingeweza kuingiza `variants_tested = 1`
    kwenye jedwali kwa mlango wa nyuma.
    """
    njia = tmp_path / "c.jsonl"
    ck = NF.Checkpoint.open(njia, "alama-1")
    with njia.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "family": S.BLOCK, "rep": 0,
            "result": {"sharpe": 9.0, NF.VARIANTS_KEY: 1},
        }) + "\n")
    ck = NF.Checkpoint.open(njia, "alama-1")

    with pytest.raises(NF.CalibrationError, match="variants_tested"):
        NF.calibrate(_frame(), lambda _s: _matokeo(1.0),
                     n_replicates=NF.MIN_REPLICATES, seed=1,
                     checkpoint=ck, progress=None)
