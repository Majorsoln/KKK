"""T1 — uendeshaji wa R0 juu ya mti wa L0 (DF-05, DF-06, RS-03).

`test_t1_l1_l2.py` inajaribu **sheria** moja moja. Hapa tunajaribu kile
kilichoshindikana T0 hadi tulipokimbiza kwenye data halisi: sheria zikiunganishwa
na partitions nyingi, njia za Hive, matoleo mawili ya schema, na cache ya
kuendelea baada ya kukatika.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.data.audit import (
    build_l2,
    build_session_calendar,
    compare_variants,
    run_quality_audit,
    select_partitions,
)
from src.data.session_calendar import KIND_FULL, SessionCalendar

# Siku nne za Agosti 2026: Jumatatu–Alhamisi. Siku ya 3 ya EURUSD imekatika.
DAYS = [date(2026, 8, 3), date(2026, 8, 4), date(2026, 8, 5), date(2026, 8, 6)]
FULL_MINUTES = 600  # 10:00 masaa ya session kwa siku ya kawaida ya jaribio


def _day_ticks(day: date, minutes: int, base: float, pip: float) -> pd.DataFrame:
    start = datetime(day.year, day.month, day.day, 7, 0, tzinfo=timezone.utc)
    stamps = pd.date_range(start, periods=minutes, freq="1min", tz="UTC")
    bid = pd.Series([base + (i % 50) * pip for i in range(minutes)])
    return pd.DataFrame(
        {
            "timestamp": stamps.astype("datetime64[us, UTC]"),
            "bid": bid.values,
            "ask": (bid + pip).values,
            "bid_vol": [1.0] * minutes,
            "ask_vol": [2.0] * minutes,
        }
    )


@pytest.fixture
def l0_tree(l0_root: Path) -> Path:
    """EURUSD (Toleo A, kwa siku) na XAUUSD (Toleo B, kwa mwezi)."""
    for day in DAYS:
        minutes = 300 if day == DAYS[2] else FULL_MINUTES  # siku moja imekatika
        frame = _day_ticks(day, minutes, 1.0900, 0.0001)
        path = (
            l0_root
            / "provenance=aggregator"
            / "symbol=EURUSD"
            / f"{day.year}"
            / f"{day.isoformat()}.parquet"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)

    monthly = pd.concat([_day_ticks(day, FULL_MINUTES, 2400.0, 0.01) for day in DAYS])
    b_frame = pd.DataFrame(
        {
            "ts": (monthly["timestamp"].astype("int64") // 1000).values,  # ms
            "bid": monthly["bid"].values,
            "ask": monthly["ask"].values,
            "bid_volume": monthly["bid_vol"].values,
            "ask_volume": monthly["ask_vol"].values,
        }
    )
    b_path = l0_root / "provenance=aggregator" / "symbol=XAUUSD" / "2026" / "2026-08.parquet"
    b_path.parent.mkdir(parents=True, exist_ok=True)
    b_frame.to_parquet(b_path, index=False)
    return l0_root


# ===========================================================================
# RS-03 — kalenda kutoka L0
# ===========================================================================


def test_kalenda_inasoma_partitions_za_matoleo_yote_mawili(cfg, l0_tree):
    build = build_session_calendar(cfg, l0_tree)
    assert build.partitions == 5  # EURUSD × 4 + XAUUSD × 1 (ya mwezi)
    assert sorted(build.calendar.days) == [d.isoformat() for d in DAYS]
    assert not build.failed


def test_kalenda_inatoa_matarajio_kwa_symbol_na_mwezi(cfg, l0_tree):
    """Matarajio ya coverage ni median ya symbol/mwezi, si namba ya kudhaniwa."""
    calendar = build_session_calendar(cfg, l0_tree).calendar
    assert calendar.expected_minutes("EURUSD", DAYS[0]) == FULL_MINUTES
    assert calendar.expected_minutes("XAUUSD", DAYS[0]) == FULL_MINUTES
    # Symbol isiyojulikana haina matarajio — 0 maana yake "haijahukumiwa".
    assert calendar.expected_minutes("GBPUSD", DAYS[0]) == 0


def test_kalenda_inahifadhiwa_na_kusomwa_bila_kupoteza_matarajio(cfg, l0_tree, tmp_path):
    calendar = build_session_calendar(cfg, l0_tree).calendar
    path = calendar.save(tmp_path / "session_calendar.json")
    reloaded = SessionCalendar.load(path)
    assert reloaded.expected_minutes("EURUSD", DAYS[0]) == FULL_MINUTES
    assert reloaded.kind_of(DAYS[0]) == KIND_FULL


def test_cache_inaruhusu_kuendelea_baada_ya_kukatika(cfg, l0_tree, tmp_path):
    cache = tmp_path / "scan.jsonl"
    first = build_session_calendar(cfg, l0_tree, cache_path=cache)
    second = build_session_calendar(cfg, l0_tree, cache_path=cache)
    assert first.reused == 0
    assert second.reused == second.partitions, "run ya pili haipaswi kusoma parquet tena"
    assert second.calendar.days.keys() == first.calendar.days.keys()


# ===========================================================================
# DF-05 — L1 juu ya mti mzima
# ===========================================================================


def test_l1_inanasa_siku_iliyokatika_kwa_kalenda_ya_data(cfg, l0_tree):
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["EURUSD"])
    failed = {Path(p.partition).stem for p in report.failed}
    assert failed == {DAYS[2].isoformat()}, "siku yenye nusu ya dakika PEKEE ndiyo inafeli"
    # Checks mbili huru zinaona kasoro ile ile kwa pande mbili: coverage inasema
    # "dakika zinakosekana", session inasema "siku imeishia mapema". Hiyo ndiyo
    # faida ya kuendesha checks ZOTE badala ya kusimama kwenye ya kwanza.
    assert report.reason_counts() == {"low_coverage": 1, "session_mismatch": 1}


def test_l1_hairuhusu_symbol_moja_kufelisha_nyingine(cfg, l0_tree):
    """XAUUSD haifanyi biashara saa za EURUSD — mipaka ni ya kila symbol."""
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["XAUUSD"])
    assert not report.failed, report.reason_counts()


def test_l1_bila_kalenda_hairuhusu_kupita_kwa_uwongo(cfg, l0_tree):
    """Bila kalenda, coverage HAIHUKUMU — na ripoti inasema hivyo wazi."""
    report = run_quality_audit(cfg, l0_tree, calendar=None, symbols=["EURUSD"])
    coverage = [c for p in report.partitions for c in p.checks if c.name == "coverage"]
    assert all("haijahukumiwa" in c.detail for c in coverage)


def test_cache_ya_l1_inatupwa_kalenda_ikibadilika(cfg, l0_tree, tmp_path):
    """Matokeo ya jana hayahukumu data kwa kalenda ya leo.

    Hii ndiyo hatari halisi ya kukimbiza symbols mbili leo na kumi na mbili
    kesho: bila alama ya hukumu, ripoti ingesema PASS kwa kalenda isiyokuwepo.
    """
    cache = tmp_path / "l1.jsonl"
    calendar = build_session_calendar(cfg, l0_tree, symbols=["EURUSD"]).calendar
    first = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["EURUSD"], cache_path=cache)

    lines_after_first = cache.read_text(encoding="utf-8").count("\n")
    run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["EURUSD"], cache_path=cache)
    assert cache.read_text(encoding="utf-8").count("\n") == lines_after_first, (
        "kalenda ile ile → hakuna kazi mpya"
    )

    pana = build_session_calendar(cfg, l0_tree).calendar  # symbols zote → kalenda mpya
    pana.symbol_months["EURUSD"]["2026-08"] = 1.0  # matarajio yamebadilika
    second = run_quality_audit(cfg, l0_tree, calendar=pana, symbols=["EURUSD"], cache_path=cache)
    assert cache.read_text(encoding="utf-8").count("\n") > lines_after_first, (
        "kalenda mpya → kila partition inahukumiwa upya"
    )
    assert "low_coverage" in first.reason_counts()
    assert "low_coverage" not in second.reason_counts(), (
        "matarajio mapya yamehukumu upya — si kurudia jibu la kalenda ya zamani"
    )


def test_threshold_study_inaonyesha_kizingiti_kingefelisha_ngapi(cfg, l0_tree):
    """Kizingiti kinatoka kwenye mgawanyo wa data, si mezani."""
    from src.data.quality import threshold_study

    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["EURUSD"])
    study = threshold_study(report.to_json())

    coverage = study["checks"]["coverage"]
    assert coverage["direction"] == "min"
    assert coverage["current_threshold"] == 0.995
    assert coverage["would_fail_now"] == 1
    assert coverage["min"] == 0.5, "siku iliyokatika ina nusu ya dakika"
    assert "EURUSD/2026" in coverage["top_offenders"]
    # Kizingiti kikilegezwa, idadi ya zinazofeli haiwezi kupanda — ndiyo maana
    # jedwali hili linaweza kutumika kuchagua kizingiti.
    candidates = sorted(coverage["candidates"], key=lambda c: c["threshold"])
    counts = [c["would_fail"] for c in candidates]
    assert counts == sorted(counts)


def test_ripoti_inapangwa_kwa_symbol_na_mwaka(cfg, l0_tree):
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar)
    assert set(report.by_symbol_year()) == {"EURUSD/2026", "XAUUSD/2026"}
    assert report.by_symbol_year()["XAUUSD/2026"]["rows"] == FULL_MINUTES * len(DAYS)


# ===========================================================================
# RS-03 — Toleo A ↔ Toleo B
# ===========================================================================


def test_matoleo_mawili_yanazalisha_schema_moja(cfg, l0_tree):
    summary = compare_variants(cfg, l0_tree)
    assert summary["canonical_schema_identical"] is True
    assert summary["variants"]["A"]["canonical_columns"] == summary["variants"]["B"]["canonical_columns"]
    assert summary["variants"]["B"]["precision"] == "ms"
    assert summary["variants"]["A"]["sample_stats"]["spread_p50_pips"] == pytest.approx(1.0, abs=0.01)


# ===========================================================================
# DF-06 — L2 kutoka L0
# ===========================================================================


def test_l2_inajengwa_kwa_tf_zote_na_bars_zinalingana(cfg, l0_tree, tmp_path):
    from src.data.bars import read_bars

    l2_root = tmp_path / "L2_bars"
    builds = build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["D1", "H4", "H1"])
    build = builds[0]
    assert build.ok, build.ohlc_violations
    assert build.rows["D1"] == len(DAYS)

    h1 = read_bars(l2_root, "EURUSD", "H1")
    d1 = read_bars(l2_root, "EURUSD", "D1")
    assert h1["n_ticks"].sum() == d1["n_ticks"].sum() == build.ticks


def test_l2_kwa_vipande_inatoa_matokeo_yale_yale(cfg, l0_tree, tmp_path):
    """Kukata kwenye mipaka ya SIKU hakubadilishi bar hata moja."""
    from src.data.bars import read_bars

    mkupuo = tmp_path / "moja"
    vipande = tmp_path / "nyingi"
    build_l2(cfg, l0_tree, mkupuo, symbols=["EURUSD"], timeframes=["D1", "H1"])
    build = build_l2(
        cfg,
        l0_tree,
        vipande,
        symbols=["EURUSD"],
        timeframes=["D1", "H1"],
        max_rows_per_chunk=1,  # kila partition ni kipande chake
    )[0]
    assert build.chunks > 1
    for tf in ("D1", "H1"):
        pd.testing.assert_frame_equal(
            read_bars(mkupuo, "EURUSD", tf), read_bars(vipande, "EURUSD", tf)
        )


def test_asof_inafanya_kazi_juu_ya_l2_iliyoandikwa(cfg, l0_tree, tmp_path):
    from src.data.asof import asof_snapshot, assert_no_future_bars
    from src.data.bars import read_bars

    l2_root = tmp_path / "L2_bars"
    build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["D1", "H1"])
    bars = {tf: read_bars(l2_root, "EURUSD", tf) for tf in ("D1", "H1")}

    t = pd.Timestamp("2026-08-04 10:00", tz="UTC")
    snapshot = asof_snapshot(bars, t)
    assert snapshot["D1"].name == pd.Timestamp("2026-08-03", tz="UTC"), "D1 ya JANA"
    assert snapshot["H1"].name == pd.Timestamp("2026-08-04 09:00", tz="UTC")
    assert_no_future_bars(bars, t)


# ===========================================================================
# Kuchagua partitions
# ===========================================================================


def test_kuchagua_kwa_symbol_na_provenance(cfg, l0_tree):
    assert len(select_partitions(cfg, l0_tree, ["EURUSD"])) == len(DAYS)
    assert len(select_partitions(cfg, l0_tree, provenance="aggregator")) == len(DAYS) + 1
    assert select_partitions(cfg, l0_tree, provenance="broker") == []
