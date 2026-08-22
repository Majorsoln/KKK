"""Kupakia L0 — DOCTRINE §4.1, R18.

Kasoro za loader hazionekani kama makosa; zinaonekana kama jedwali. Faili
zilizowekwa chini ya symbol isiyo sahihi bado zinapimwa, zinaripotiwa, na
zinaonekana za kawaida kabisa. Kwa hiyo tests hizi zinalinda hatua tatu:

* **kutambua symbol** — kwa sarafu halisi, si kwa umbo la herufi sita
* **normalize** — Toleo A na B zinatoa schema MOJA
* **mpaka** — `clip` inatumika kabla ya row yoyote kutoka (R18)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import load as L
from src.data.window import Stage, Window

STAGE = Stage(
    window=Window(pd.Timestamp("2020-01-01").date(), pd.Timestamp("2020-12-31").date()),
    name="test", purpose="kupima loader",
)


def _frame(start="2020-01-01", n=2_000, *, toleo="A", freq="5min", px=1.10):
    stamps = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    mid = px + np.cumsum(np.random.default_rng(3).normal(0, 1e-5, n))
    half = 0.6e-4
    if toleo == "A":
        return pd.DataFrame({"timestamp": stamps, "bid": mid - half, "ask": mid + half,
                             "bid_vol": 1.0, "ask_vol": 1.0})
    return pd.DataFrame({"ts": stamps, "bid": mid - half, "ask": mid + half,
                         "bid_volume": 1.0, "ask_volume": 1.0})


def _tree(root, layout="hive", symbols=("EURUSD",), months=2, toleo="A"):
    for symbol in symbols:
        for i in range(months):
            start = pd.Timestamp("2020-01-01") + pd.DateOffset(months=i)
            if layout == "hive":
                out = root / f"symbol={symbol}" / f"{start:%Y-%m}"
                name = "part-0.parquet"
            elif layout == "flat":
                out = root
                name = f"{symbol.lower()}_{start:%Y_%m}.parquet"
            else:
                out = root / symbol / f"{start:%Y}"
                name = f"{start:%m}.parquet"
            out.mkdir(parents=True, exist_ok=True)
            _frame(start=start, toleo=toleo).to_parquet(out / name, index=False)
    return root


# ===========================================================================
# Kutambua symbol
# ===========================================================================


@pytest.mark.parametrize("layout", ("hive", "flat", "nested"))
def test_muundo_wa_folda_unatafutwa_hauhaniwi(tmp_path, layout):
    inv = L.discover(_tree(tmp_path, layout))
    assert inv.symbols == ["EURUSD"]
    assert len(inv.partitions) == 2


def test_neno_SYMBOL_si_symbol(tmp_path):
    """`symbol=EURUSD` ina herufi sita kubwa mbili. Moja tu ni pair.

    Bila ukaguzi wa sarafu, kila partition ingewekwa chini ya symbol iitwayo
    "SYMBOL", na calibration ingeripoti cell moja yenye pairs zote ndani yake.
    """
    inv = L.discover(_tree(tmp_path, "hive"))
    assert "SYMBOL" not in inv.symbols
    assert inv.symbols == ["EURUSD"]


def test_folda_isiyo_na_pair_haitambuliki(tmp_path):
    out = tmp_path / "MARKET" / "TICKDA"
    out.mkdir(parents=True)
    _frame().to_parquet(out / "x.parquet", index=False)
    inv = L.discover(tmp_path)
    assert inv.partitions == [] and len(inv.isiyotambulika) == 1
    assert "HAIJATAMBULIKA" in inv.render()


def test_symbols_nyingi_zinatenganishwa(tmp_path):
    inv = L.discover(_tree(tmp_path, "hive", symbols=("EURUSD", "USDJPY", "XAUUSD")))
    assert inv.symbols == ["EURUSD", "USDJPY", "XAUUSD"]
    assert len(inv.of("USDJPY")) == 2


def test_kuchuja_kwa_symbols(tmp_path):
    inv = L.discover(_tree(tmp_path, "hive", symbols=("EURUSD", "USDJPY")),
                     symbols=["EURUSD"])
    assert inv.symbols == ["EURUSD"]


def test_root_isiyopo_inalipuka(tmp_path):
    with pytest.raises(L.LoadError, match="root"):
        L.discover(tmp_path / "hakuna")


# ===========================================================================
# Normalize — toleo mbili, schema moja
# ===========================================================================


@pytest.mark.parametrize("toleo", ("A", "B"))
def test_matoleo_yote_yanatoa_schema_ILE_ILE(toleo):
    out = L.normalize(_frame(toleo=toleo))
    assert list(out.columns)[:5] == ["timestamp", "bid", "ask", "bid_vol", "ask_vol"]
    assert str(out["timestamp"].dt.tz) == "UTC"


def test_muda_bila_tz_unachukuliwa_kuwa_UTC():
    frame = _frame()
    frame["timestamp"] = frame["timestamp"].dt.tz_localize(None)
    assert str(L.normalize(frame)["timestamp"].dt.tz) == "UTC"


def test_frame_bila_safu_ya_muda_inalipuka():
    with pytest.raises(L.LoadError, match="muda"):
        L.normalize(pd.DataFrame({"bid": [1.0], "ask": [1.1]}))


def test_frame_bila_ask_inalipuka():
    with pytest.raises(L.LoadError, match="ask"):
        L.normalize(pd.DataFrame({"timestamp": [pd.Timestamp("2020-01-01")], "bid": [1.0]}))


# ===========================================================================
# Mpaka (R18) na ubora (§4.3)
# ===========================================================================


def test_clip_inatumika_kabla_ya_row_kutoka(tmp_path):
    """Row ya nje ya dirisha haifiki kwa mpigaji simu — si baada, ni kabla."""
    root = tmp_path / "l0"
    out = root / "symbol=EURUSD" / "2019-12"
    out.mkdir(parents=True)
    nje = _frame(start="2019-12-01", n=500)
    ndani = _frame(start="2020-01-01", n=500)
    pd.concat([nje, ndani], ignore_index=True).to_parquet(out / "p.parquet", index=False)

    frame, _ = L.load_ticks(L.discover(root), "EURUSD", STAGE, pip=1e-4)
    assert frame["timestamp"].min() >= pd.Timestamp("2020-01-01", tz="UTC")
    assert len(frame) == 500


def test_symbol_isiyo_na_partition_inalipuka(tmp_path):
    with pytest.raises(L.LoadError, match="hakuna partition"):
        L.load_ticks(L.discover(_tree(tmp_path)), "GBPUSD", STAGE)


def test_ripoti_ya_ubora_inarudishwa(tmp_path):
    _, report = L.load_ticks(L.discover(_tree(tmp_path)), "EURUSD", STAGE, pip=1e-4)
    assert report.n_ticks > 0
    assert report.symbol == "EURUSD"


def test_ubora_ukishindwa_kwa_strict_inalipuka(tmp_path):
    from src.data.quality import QualityError

    root = tmp_path / "l0"
    out = root / "symbol=EURUSD" / "2020-01"
    out.mkdir(parents=True)
    frame = _frame()
    frame.loc[10, "bid"] = frame.loc[10, "ask"] + 0.01     # quote iliyovuka
    frame.to_parquet(out / "p.parquet", index=False)

    with pytest.raises(QualityError):
        L.load_ticks(L.discover(root), "EURUSD", STAGE, pip=1e-4, strict=True)


# ===========================================================================
# Mwezi kwa mwezi
# ===========================================================================


def test_miezi_inatolewa_kando(tmp_path):
    """Miaka 10 ya ticks haiingii kwenye kumbukumbu; mwezi mmoja unaingia."""
    inv = L.discover(_tree(tmp_path, "hive", months=4))
    miezi = [label for label, _, _ in L.iter_months(inv, "EURUSD", STAGE, pip=1e-4)]
    assert miezi == ["2020-01", "2020-02", "2020-03", "2020-04"]


def test_kila_mwezi_umekatwa_na_kukaguliwa(tmp_path):
    inv = L.discover(_tree(tmp_path, "hive", months=3))
    for _, chunk, report in L.iter_months(inv, "EURUSD", STAGE, pip=1e-4):
        assert chunk["timestamp"].is_monotonic_increasing
        assert report.n_ticks == len(chunk)


def test_miezi_ya_nje_ya_dirisha_hazitolewi(tmp_path):
    root = tmp_path / "l0"
    for label in ("2019-11", "2020-01"):
        out = root / "symbol=EURUSD" / label
        out.mkdir(parents=True)
        _frame(start=f"{label}-01").to_parquet(out / "p.parquet", index=False)

    miezi = [label for label, _, _ in
             L.iter_months(L.discover(root), "EURUSD", STAGE, pip=1e-4)]
    assert miezi == ["2020-01"]
