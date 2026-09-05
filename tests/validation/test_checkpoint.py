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
    yote = "\n".join(maneno)
    assert "TOFAUTI" in yote
    assert "K=200" in yote and "K=1000" in yote


def test_kilichobadilika_PEKEE_kinaonyeshwa():
    """Kuchapisha JSON mbili ndefu kunaficha kilichobadilika ndani ya kilichobaki.

    Fingerprint halisi ni ndefu (spec nzima + hash ya code); mtumiaji anahitaji
    kujua kigezo KIPI kimebadilika, si kulinganisha mistari miwili kwa macho.
    """
    zamani = json.dumps({"code": "aaaa", "n_bars": 50_161, "replicates": 50},
                        sort_keys=True)
    sasa = json.dumps({"code": "bbbb", "n_bars": 50_161, "replicates": 50},
                      sort_keys=True)
    mistari = NF._tofauti(zamani, sasa)
    assert mistari == ["code: aaaa → bbbb"]


def test_fingerprint_isiyo_JSON_bado_inaelezwa():
    mistari = NF._tofauti("alama-1", "alama-2")
    assert any("alama-1" in m for m in mistari)
    assert any("alama-2" in m for m in mistari)


def test_thamani_ndefu_inakatwa():
    zamani = json.dumps({"spec": "x" * 200}, sort_keys=True)
    sasa = json.dumps({"spec": "y" * 200}, sort_keys=True)
    mistari = NF._tofauti(zamani, sasa)
    assert len(mistari) == 1 and "…" in mistari[0] and len(mistari[0]) < 200


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


# ===========================================================================
# Fingerprint lazima ishike CODE, si vigezo pekee (2026-08-26)
# ===========================================================================


def test_code_fingerprint_inabadilika_code_ikibadilika(tmp_path):
    """Kasoro iliyopoteza run nzima ya pili.

    Vigezo (`K`, `seed`, bars) havikubadilika lakini code ilikuwa imerekebishwa.
    Checkpoint ilirudisha replicates za code ya ZAMANI, run ikawa ni kucheza
    tena matokeo yale yale, na jedwali lililotoka lilionekana halali kabisa.
    """
    mizizi = tmp_path / "src"
    (mizizi / "pkg").mkdir(parents=True)
    faili = mizizi / "pkg" / "moduli.py"
    faili.write_text("X = 1\n", encoding="utf-8")

    kabla = NF.code_fingerprint(mizizi)
    faili.write_text("X = 2\n", encoding="utf-8")
    baada = NF.code_fingerprint(mizizi)
    assert kabla != baada

    faili.write_text("X = 1\n", encoding="utf-8")
    assert NF.code_fingerprint(mizizi) == kabla


def test_code_fingerprint_inashika_config_pia(tmp_path):
    """Kigezo cha `risk.yaml` kinabadilisha matokeo kama code inavyofanya."""
    mizizi = tmp_path / "config"
    mizizi.mkdir()
    cfg = mizizi / "risk.yaml"
    cfg.write_text("max_open_trades: 7\n", encoding="utf-8")

    kabla = NF.code_fingerprint(mizizi)
    cfg.write_text("max_open_trades: 3\n", encoding="utf-8")
    assert NF.code_fingerprint(mizizi) != kabla


def test_code_fingerprint_inapuuza_faili_zisizo_za_code(tmp_path):
    mizizi = tmp_path / "src"
    mizizi.mkdir()
    (mizizi / "a.py").write_text("X = 1\n", encoding="utf-8")

    kabla = NF.code_fingerprint(mizizi)
    (mizizi / "kumbukumbu.log").write_text("x" * 500, encoding="utf-8")
    (mizizi / "__pycache__").mkdir()
    assert NF.code_fingerprint(mizizi) == kabla


def test_checkpoint_ya_code_ya_zamani_inaanza_UPYA(tmp_path):
    """Ndio mwisho unaotakiwa: si kurudisha, ni kuanza upya."""
    njia = tmp_path / "c.jsonl"
    NF.Checkpoint.open(njia, "code=A").put(S.BLOCK, 0, _matokeo(1.5))

    maneno: list[str] = []
    tena = NF.Checkpoint.open(njia, "code=B", progress=maneno.append)
    assert len(tena) == 0
    assert any("TOFAUTI" in m for m in maneno)
