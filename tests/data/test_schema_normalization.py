"""DF-02 — normalization ya Toleo A/B kuwa schema MOJA.

Spec: `docs/DATA_FEATURE_STANDARD.md` §2.1
Rejista: DF-02 (UT kwa matoleo yote 2), DF-01 (L0 haibadilishwi)
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.hashing import sha256_file
from src.data.schema import (
    CANONICAL_COLUMNS,
    SchemaError,
    detect_variant,
    normalize_frame,
    read_partition,
    variant_for,
    variant_specs,
)
from tests.conftest import variant_a_frame, variant_b_frame


def test_config_inatangaza_matoleo_mawili_ya_spec_2_1(cfg):
    """Spec §2.1: matoleo MAWILI — A (µs, symbols 9) na B (ms, symbols 3)."""
    specs = variant_specs(cfg)
    assert set(specs) == {"A", "B"}
    assert specs["A"].columns == CANONICAL_COLUMNS
    assert specs["A"].precision == "us"
    assert specs["B"].columns == ("ts", "bid", "ask", "bid_volume", "ask_volume")
    assert specs["B"].precision == "ms"
    assert set(specs["B"].symbols) == {"EURCHF", "GBPJPY", "XAUUSD"}


def test_symbols_kumi_na_mbili_zina_toleo_lililotangazwa(cfg):
    """Exit criteria ya T0: symbols 12 zinasomeka kwa schema moja."""
    assert len(cfg.symbols) == 12
    variants = {symbol: cfg.variant_of_symbol(symbol) for symbol in cfg.symbols}
    assert set(variants.values()) == {"A", "B"}
    assert {s for s, v in variants.items() if v == "B"} == {"EURCHF", "GBPJPY", "XAUUSD"}
    assert len([s for s, v in variants.items() if v == "A"]) == 9


def test_toleo_a_linatambuliwa_na_kubaki_schema_ya_kawaida(cfg):
    frame = variant_a_frame()
    assert detect_variant(list(frame.columns), cfg).name == "A"
    out = normalize_frame(frame, cfg, symbol="EURUSD")
    assert tuple(out.columns) == CANONICAL_COLUMNS
    assert str(out["timestamp"].dtype) == "datetime64[us, UTC]"
    assert out.attrs["schema_variant"] == "A"


def test_toleo_b_ms_linapanda_kuwa_us_bila_kupoteza_thamani(cfg):
    """Toleo B ni ms; schema ya kawaida ni µs — upandishaji ni sahihi kabisa."""
    out = normalize_frame(variant_b_frame(), cfg, symbol="XAUUSD")
    assert tuple(out.columns) == CANONICAL_COLUMNS
    assert str(out["timestamp"].dtype) == "datetime64[us, UTC]"
    assert (out["timestamp"].dt.microsecond % 1000 == 0).all()
    assert out.attrs["schema_variant"] == "B"
    assert out.attrs["source_precision"] == "ms"


def test_matoleo_yote_mawili_yanatoa_schema_MOJA_inayolingana(cfg):
    """Kipimo cha msingi cha DF-02: A na B zenye ticks zile zile → frame ile ile."""
    from_a = normalize_frame(variant_a_frame(), cfg, symbol="EURUSD")
    from_b = normalize_frame(variant_b_frame(), cfg, symbol="XAUUSD")
    pd.testing.assert_frame_equal(from_a, from_b, check_exact=True)


def test_dtypes_za_schema_ya_kawaida_ni_thabiti(cfg):
    out = normalize_frame(variant_b_frame(), cfg, symbol="GBPJPY")
    assert [str(dtype) for dtype in out.dtypes] == [
        "datetime64[us, UTC]",
        "float64",
        "float64",
        "float64",
        "float64",
    ]


def test_normalization_hairekebishi_wala_haipangi_upya_rows(cfg):
    """Sheria: hii ni rename + cast pekee. Usafi wa data ni kazi ya L1 (§3, T1)."""
    frame = variant_a_frame()
    shuffled = frame.iloc[[3, 0, 5, 1, 4, 2]].reset_index(drop=True)
    out = normalize_frame(shuffled, cfg, symbol="EURUSD")
    assert list(out["bid"]) == list(shuffled["bid"])
    assert not out["timestamp"].is_monotonic_increasing  # L1 ndiyo itakayolisema hili


def test_columns_za_ziada_zinaruhusiwa_lakini_hazitoki_kwenye_schema(cfg):
    """Partition ya broker inabeba `flags`/`volume_real`; schema ya kawaida haibadiliki."""
    frame = variant_a_frame()
    frame["flags"] = 6
    frame["volume_real"] = 1.0
    out = normalize_frame(frame, cfg, symbol="EURUSD")
    assert tuple(out.columns) == CANONICAL_COLUMNS
    kept = normalize_frame(frame, cfg, symbol="EURUSD", keep_extra_columns=True)
    assert list(kept.columns) == list(CANONICAL_COLUMNS) + ["flags", "volume_real"]


def test_toleo_lisilojulikana_linakataliwa(cfg):
    frame = variant_a_frame().rename(columns={"bid": "b", "ask": "a"})
    with pytest.raises(SchemaError):
        normalize_frame(frame, cfg, symbol="EURUSD")


def test_symbol_yenye_toleo_lisilotarajiwa_inasimamisha_kazi(cfg):
    """XAUUSD ni Toleo B kwa config; ikija kwa Toleo A, chanzo kimebadilika."""
    with pytest.raises(SchemaError, match="Toleo B"):
        variant_for(list(variant_a_frame().columns), cfg, symbol="XAUUSD")


def test_partition_ya_broker_ya_symbol_ya_toleo_b_inasomeka(cfg, l0_root, tmp_path):
    """Orodha ya `schema_variants[*].symbols` inaelezea data ya AGGREGATOR pekee.

    Recorder inaandika symbols zote kwa schema ya kawaida; XAUUSD ya broker
    haipaswi kukataliwa kwa sababu XAUUSD ya aggregator ni Toleo B.
    """
    from src.data.schema import read_partition

    path = l0_root / "provenance=broker" / "symbol=XAUUSD" / "date=2026-08-03" / "ticks.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(path, index=False)

    frame = read_partition(path, cfg)
    assert tuple(frame.columns) == CANONICAL_COLUMNS
    assert frame.attrs["schema_variant"] == "A"


def test_partition_ya_aggregator_yenye_toleo_lisilotarajiwa_bado_inakataliwa(cfg, l0_root):
    """Ulinzi unabaki pale unapohitajika: chanzo cha aggregator kikibadilika → SIMAMA."""
    from src.data.schema import read_partition

    path = l0_root / "provenance=aggregator" / "symbol=XAUUSD" / "2026" / "2026-08.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(path, index=False)
    with pytest.raises(SchemaError, match="Toleo B"):
        read_partition(path, cfg)


def test_kusoma_partition_hakubadilishi_faili_la_l0(cfg, aggregator_partitions):
    """DF-01/§2: L0 ni immutable — kusoma + normalize hakuachi alama yoyote."""
    for path in aggregator_partitions.values():
        before = sha256_file(path)
        frame = read_partition(path, cfg)
        assert tuple(frame.columns) == CANONICAL_COLUMNS
        assert sha256_file(path) == before


def test_partition_ya_toleo_b_inasomeka_kwa_schema_moja(cfg, aggregator_partitions):
    from_a = read_partition(aggregator_partitions["A"], cfg)
    from_b = read_partition(aggregator_partitions["B"], cfg)
    pd.testing.assert_frame_equal(from_a, from_b, check_exact=True)
