"""T1 — uendeshaji wa R0 juu ya mti wa L0 (DF-05, DF-06, RS-03).

`test_t1_l1_l2.py` inajaribu **sheria** moja moja. Hapa tunajaribu kile
kilichoshindikana T0 hadi tulipokimbiza kwenye data halisi: sheria zikiunganishwa
na partitions nyingi, njia za Hive, matoleo mawili ya schema, na cache ya
kuendelea baada ya kukatika.
"""

from __future__ import annotations

import json
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
    for values in pana.symbol_expect["EURUSD"].values():  # matarajio yamebadilika
        values[0] = 1.0
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
    study = threshold_study(report.to_detail())

    coverage = study["checks"]["coverage"]
    assert coverage["direction"] == "min"
    # Kizingiti kinachoonyeshwa ni cha CONFIG, si namba iliyoandikwa hapa.
    # PD anabadilisha `min_coverage`; test isivunjike kwa uamuzi wake halali.
    assert coverage["current_threshold"] == cfg.get("quality.min_coverage")
    assert coverage["failing_now"] == 1
    assert coverage["min"] == 0.5, "siku iliyokatika ina nusu ya dakika"
    assert "EURUSD/2026" in coverage["top_offenders"]
    # Kizingiti kikilegezwa, idadi ya zinazofeli haiwezi kupanda — ndiyo maana
    # jedwali hili linaweza kutumika kuchagua kizingiti.
    candidates = sorted(coverage["candidates"], key=lambda c: c["threshold"])
    counts = [c["would_fail"] for c in candidates]
    assert counts == sorted(counts)

    # Ukaguzi usiofelisha chochote hauna cha kupangwa upya.
    assert study["checks"]["monotonicity"]["failing_now"] == 0
    assert study["checks"]["monotonicity"]["candidates"] == []


def test_threshold_study_inahesabu_kufeli_kutoka_kwenye_jibu_si_kwa_kizingiti(cfg, l0_tree):
    """`session_match` inapitisha hatua ya saa 1 (DST) ingawa inazidi uvumilivu.

    Kuhesabu upya kwa kizingiti kungeripoti kufeli kusikokuwepo kwenye ripoti.
    """
    from src.data.quality import CheckResult, PartitionQuality, QualityReport, threshold_study

    dst = PartitionQuality(partition="x/2026/a.parquet", symbol="EURUSD", provenance="aggregator")
    dst.checks = [
        CheckResult(
            name="session_match",
            passed=True,  # hatua ya DST — imepita
            value=60.04,
            threshold=15.0,
            detail="hatua ya saa 1 (DST), si hitilafu",
        )
    ]
    study = threshold_study(QualityReport(partitions=[dst]).to_detail())
    entry = study["checks"]["session_match"]
    assert entry["max"] == 60.04 and entry["current_threshold"] == 15.0
    assert entry["failing_now"] == 0, "thamani inazidi kizingiti, lakini ukaguzi umepita"


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


def test_ripoti_inabeba_vizingiti_vyote_na_wigo_wa_miaka(cfg, l0_tree):
    """R0 inaulizwa 'dhidi ya vizingiti vya data.yaml' — vyote lazima vionekane."""
    calendar = build_session_calendar(cfg, l0_tree).calendar
    payload = run_quality_audit(cfg, l0_tree, calendar=calendar).to_json()

    for key in ("min_coverage", "max_gap_seconds", "max_stale_seconds", "max_duplicate_frac"):
        assert key in payload["thresholds"], f"{key} haionekani kwenye ripoti"

    eurusd = payload["coverage_by_symbol"]["EURUSD"]
    assert eurusd["trading_days"] == len(DAYS)
    assert eurusd["min_years"] == 10
    assert eurusd["meets_min_years"] is False, "siku 4 si miaka 10 — ripoti iseme wazi"


# ===========================================================================
# R0 — aggregator ↔ broker (spec §2.2 sharti 2)
# ===========================================================================


def test_ulinganisho_wa_provenance_unapima_siku_zinazopishana(cfg, l0_root):
    """Spread ya broker dhidi ya ya aggregator, siku ile ile, symbol ile ile."""
    from src.data.audit import compare_provenance

    day = DAYS[0]
    agg = _day_ticks(day, FULL_MINUTES, 1.0900, 0.0001)  # spread pip 1.0
    a_path = l0_root / "provenance=aggregator" / "symbol=EURUSD" / "2026" / f"{day}.parquet"
    a_path.parent.mkdir(parents=True, exist_ok=True)
    agg.to_parquet(a_path, index=False)

    brk = _day_ticks(day, FULL_MINUTES, 1.0900, 0.0001)
    brk["ask"] = brk["bid"] + 0.00016  # broker ni pana: pips 1.6
    b_path = l0_root / "provenance=broker" / "symbol=EURUSD" / f"date={day}" / "ticks.parquet"
    b_path.parent.mkdir(parents=True, exist_ok=True)
    brk.to_parquet(b_path, index=False)

    summary = compare_provenance(cfg, l0_root, symbols=["EURUSD"])
    assert summary["overlap_days"] == [day.isoformat()]
    assert summary["comparisons"] == 1
    row = summary["rows"][0]
    assert row["aggregator"]["spread_p50"] == pytest.approx(1.0, abs=0.01)
    assert row["broker"]["spread_p50"] == pytest.approx(1.6, abs=0.01)
    assert summary["spread_p50_ratio"]["median"] == pytest.approx(1.6, abs=0.02), (
        "broker ni ghali kwa 60% — EV iliyohesabiwa kwa data ya aggregator ni ya matumaini"
    )


def test_bila_siku_zinazopishana_ulinganisho_hausemi_umefanikiwa(cfg, l0_tree):
    from src.data.audit import compare_provenance

    summary = compare_provenance(cfg, l0_tree)
    assert summary["comparisons"] == 0 and summary["overlap_days"] == []


# ===========================================================================
# Kuchagua partitions
# ===========================================================================


def test_kuchagua_kwa_symbol_na_provenance(cfg, l0_tree):
    assert len(select_partitions(cfg, l0_tree, ["EURUSD"])) == len(DAYS)
    assert len(select_partitions(cfg, l0_tree, provenance="aggregator")) == len(DAYS) + 1
    assert select_partitions(cfg, l0_tree, provenance="broker") == []


def test_l2_inaendelea_ilipoishia_bila_kujenga_upya(cfg, l0_tree, tmp_path):
    """Kazi ya masaa lazima iweze kukatizwa. Symbol iliyokwisha inarukwa."""
    l2_root = tmp_path / "L2_bars"
    first = build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])[0]
    assert first.ticks > 0 and (l2_root / "_l2_state.json").is_file()

    second = build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])[0]
    assert second.reused, "hali imesomwa, si kujengwa upya"
    assert second.rows == first.rows and second.ticks == first.ticks


def test_l2_inajenga_upya_data_ya_l0_ikibadilika(cfg, l0_tree, tmp_path):
    """Bars za zamani hazibaki kimya baada ya L0 kuongezeka."""
    l2_root = tmp_path / "L2_bars"
    build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])

    mpya = date(2026, 8, 7)
    path = l0_tree / "provenance=aggregator" / "symbol=EURUSD" / "2026" / f"{mpya}.parquet"
    _day_ticks(mpya, FULL_MINUTES, 1.0900, 0.0001).to_parquet(path, index=False)

    rebuilt = build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])[0]
    assert rebuilt.rows["H1"] > 0
    from src.data.bars import read_bars

    bars = read_bars(l2_root, "EURUSD", "H1")
    assert mpya.isoformat() in {str(d.date()) for d in bars.index}, "siku mpya imeingia"


def test_no_resume_inajenga_upya_hata_ikiwa_ipo(cfg, l0_tree, tmp_path):
    l2_root = tmp_path / "L2_bars"
    build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])
    forced = build_l2(
        cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"], resume=False
    )[0]
    assert not forced.reused and forced.ticks > 0


def test_adopt_inaokoa_bars_zilizopo_bila_kujenga_upya(cfg, l0_tree, tmp_path):
    """Bars za toleo lisilo na hali zisijengwe upya bure (saa 5-8)."""
    from src.data.audit import adopt_existing_l2

    l2_root = tmp_path / "L2_bars"
    tfs = ["D1", "H1"]
    build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=tfs)
    (l2_root / "_l2_state.json").unlink()          # kama toleo la zamani

    adopted = adopt_existing_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=tfs)
    assert adopted == ["EURUSD"]
    again = build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=tfs)[0]
    assert again.reused, "haijajengwa upya — imesomwa kutoka kwenye hali"
    assert again.rows["H1"] > 0


def test_adopt_hairuki_symbol_yenye_tf_pungufu(cfg, l0_tree, tmp_path):
    """Symbol iliyokatizwa katikati ina TF pungufu — lazima ijengwe upya."""
    from src.data.audit import adopt_existing_l2

    l2_root = tmp_path / "L2_bars"
    tfs = ["D1", "H1"]
    build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=tfs)
    (l2_root / "_l2_state.json").unlink()
    (l2_root / "symbol=EURUSD" / "tf=H1" / "bars.parquet").unlink()

    assert adopt_existing_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=tfs) == []


def test_kizingiti_kisichohusu_bars_hakifuti_l2(cfg, l0_tree, tmp_path):
    """Kubadilisha `quality` au `setups` HAKUPASWI kudai ujenzi wa saa 5-8."""
    l2_root = tmp_path / "L2_bars"
    build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])

    cfg.raw["quality"]["min_coverage"] = 0.9
    cfg.raw.setdefault("setups", {})["target_rate"] = 0.07
    again = build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])[0]
    assert again.reused, "L2 haitegemei vizingiti hivyo"

    cfg.raw["bars"]["build_from"] = "kitu_kingine"   # HII inahusu bars
    rebuilt = build_l2(cfg, l0_tree, l2_root, symbols=["EURUSD"], timeframes=["H1"])[0]
    assert not rebuilt.reused, "mabadiliko ya `bars` yanajenga upya"


def test_r0_summary_inasoma_ripoti_bila_kuhesabu_upya(cfg, l0_tree, tmp_path, capsys):
    """Ushahidi wa sahihi ya T1: vigezo vyote kwenye jedwali moja."""
    from src.data.cli import main

    out_dir = tmp_path / "quality"
    calendar_build = build_session_calendar(cfg, l0_tree)
    calendar_build.calendar.save(out_dir / "session_calendar.json")
    (out_dir / "calendar_vs_assumed.json").write_text(
        __import__("json").dumps({**calendar_build.comparison, "by_variant": calendar_build.by_variant}),
        encoding="utf-8",
    )
    run_quality_audit(cfg, l0_tree, calendar=calendar_build.calendar).save(
        out_dir / "quality_report.json"
    )

    rc = main(["r0-summary", "--out-dir", str(out_dir)])
    printed = capsys.readouterr().out
    assert "R0 — DATA AUDIT" in printed
    assert "siku zilizotarajiwa bila data" in printed
    assert "miaka ≥ min_years" in printed
    assert rc == 1, "siku 4 si miaka 10 — inahitaji uamuzi wa PD"


def test_r0_summary_inakataa_bila_ripoti(cfg, tmp_path, capsys):
    from src.data.cli import main

    assert main(["r0-summary", "--out-dir", str(tmp_path / "hakuna")]) == 2


# ===========================================================================
# Kitengo cha hukumu ni SIKU, si faili (PD 2026-08-08)
# ===========================================================================


def test_siku_moja_mbaya_haitupi_mwezi_mzima(cfg, l0_root):
    """Toleo B ni partition ya MWEZI. Siku 1 mbaya isipoteze siku 22 nzuri.

    Hii ndiyo kasoro iliyofanya EURCHF/GBPJPY/XAUUSD kufeli 12 KWA MWAKA —
    yaani partitions zao ZOTE — kwenye kipimo cha kwanza cha data halisi.
    """
    days = [date(2026, 8, d) for d in (3, 4, 5, 6, 7)]
    frames = []
    for day in days:
        # 300/600: fupi ya kutosha kufeli coverage, ndefu ya kutosha kubaki
        # `full` (chini ya 0.25 x median ingekuwa `partial`, yaani sikukuu).
        minutes = 300 if day == days[2] else FULL_MINUTES
        frames.append(_day_ticks(day, minutes, 2400.0, 0.01))
    monthly = pd.concat(frames)
    b_frame = pd.DataFrame(
        {
            "ts": (monthly["timestamp"].astype("int64") // 1000).values,
            "bid": monthly["bid"].values,
            "ask": monthly["ask"].values,
            "bid_volume": monthly["bid_vol"].values,
            "ask_volume": monthly["ask_vol"].values,
        }
    )
    path = l0_root / "provenance=aggregator" / "symbol=XAUUSD" / "2026" / "2026-08.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    b_frame.to_parquet(path, index=False)

    calendar = build_session_calendar(cfg, l0_root).calendar
    report = run_quality_audit(cfg, l0_root, calendar=calendar, symbols=["XAUUSD"])

    part = report.partitions[0]
    assert len(part.days) == len(days), "partition ya mwezi inahukumiwa siku kwa siku"
    assert len(part.failed_days) == 1, "siku MOJA pekee ndiyo mbaya"
    assert part.usable_days == [d.isoformat() for d in days if d != days[2]]

    assert report.total_days == len(days)
    assert report.failed_days == 1
    assert report.excluded_days() == {"XAUUSD": [days[2].isoformat()]}


# ===========================================================================
# Siku moja kwenye partitions mbili (PD 2026-08-09)
# ===========================================================================


def _b_partition(root: Path, symbol: str, name: str, frame: pd.DataFrame) -> Path:
    path = root / "provenance=aggregator" / f"symbol={symbol}" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "ts": (frame["timestamp"].astype("int64") // 1000).values,
            "bid": frame["bid"].values,
            "ask": frame["ask"].values,
            "bid_volume": frame["bid_vol"].values,
            "ask_volume": frame["ask_vol"].values,
        }
    ).to_parquet(path, index=False)
    return path


def _split_day_tree(root: Path) -> Path:
    """Toleo B halikati mwezi usiku wa manane bali **saa 05:00 UTC**.

    Kwa hiyo tarehe 1 iko nusu kwenye faili ya mwezi uliopita (00:00–04:59)
    na nusu kwenye ya mwezi huu (05:00–23:59). Hivi ndivyo data halisi ilivyo.
    """
    def ticks(start: datetime, minutes: int) -> pd.DataFrame:
        stamps = pd.date_range(start, periods=minutes, freq="1min", tz="UTC")
        bid = pd.Series([2400.0 + (i % 50) * 0.01 for i in range(minutes)])
        return pd.DataFrame(
            {
                "timestamp": stamps.astype("datetime64[us, UTC]"),
                "bid": bid.values,
                "ask": (bid + 0.01).values,
                "bid_vol": [1.0] * minutes,
                "ask_vol": [2.0] * minutes,
            }
        )

    # Julai: siku kamili ya 07-31, kisha mkia wa 08-01 hadi 04:59.
    julai = pd.concat(
        [
            ticks(datetime(2026, 7, 31, 0, 0, tzinfo=timezone.utc), 1440),
            ticks(datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc), 300),
        ]
    )
    # Agosti: kichwa cha 08-01 kuanzia 05:00, kisha siku kamili ya 08-02.
    agosti = pd.concat(
        [
            ticks(datetime(2026, 8, 1, 5, 0, tzinfo=timezone.utc), 1140),
            ticks(datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc), 1440),
        ]
    )
    _b_partition(root, "XAUUSD", "2026-07.parquet", julai)
    _b_partition(root, "XAUUSD", "2026-08.parquet", agosti)
    return root


def test_siku_iliyogawanywa_kwenye_faili_mbili_inahukumiwa_kama_moja(cfg, l0_root):
    """Vipande viwili vya tarehe 1 vinaunganishwa kabla ya kuhukumiwa.

    Kipimo halisi cha 2026-08-09 kilionyesha EURCHF ikitoa mistari MIWILI kwa
    tarehe ile ile: kimoja `close ±1140 min`, kingine `open ±300 min`.
    `1140 + 300 = 1440` — siku moja kamili, iliyokatwa saa 05:00 UTC.
    """
    _split_day_tree(l0_root)
    calendar = build_session_calendar(cfg, l0_root).calendar
    report = run_quality_audit(cfg, l0_root, calendar=calendar, symbols=["XAUUSD"])

    siku = [d for part in report.partitions for d in part.days]
    tarehe = [d.day for d in siku]
    assert tarehe.count("2026-08-01") == 1, "tarehe 1 inaonekana MARA MOJA, si mbili"
    assert report.split_days_merged == 1

    moja = next(d for d in siku if d.day == "2026-08-01")
    assert moja.observed_minutes == 1440, "dakika za vipande vyote viwili"
    assert moja.first_ts.startswith("2026-08-01T00:00")
    assert moja.last_ts.startswith("2026-08-01T23:59")
    assert "low_coverage" not in moja.fail_reasons
    assert "session_mismatch" not in moja.fail_reasons


def test_bila_kuunganisha_kila_kipande_kingefeli(cfg, l0_root):
    """Uthibitisho kwamba kasoro ilikuwa ya KWELI, si ya kubuni.

    Hii ndiyo iliyokuwa ikitupa tarehe 1 ya KILA MWEZI kwa symbols zote tatu
    za Toleo B — siku ~380 za biashara halisi, kwa kasoro ya kipimo.
    """
    from src.data.quality import check_partition

    _split_day_tree(l0_root)
    calendar = build_session_calendar(cfg, l0_root).calendar
    julai = l0_root / "provenance=aggregator" / "symbol=XAUUSD" / "2026-07.parquet"
    agosti = l0_root / "provenance=aggregator" / "symbol=XAUUSD" / "2026-08.parquet"

    mkia = next(d for d in check_partition(julai, cfg, calendar=calendar).days
                if d.day == "2026-08-01")
    kichwa = next(d for d in check_partition(agosti, cfg, calendar=calendar).days
                  if d.day == "2026-08-01")
    assert not mkia.passed and not kichwa.passed
    assert mkia.observed_minutes + kichwa.observed_minutes == 1440


def test_kuunganisha_kunavumilia_precision_mbili_kwenye_siku_moja(cfg, l0_root):
    """`isoformat()` inaacha sehemu ya sekunde ikiwa ni sifuri.

    Tick ya `00:00:00.070000` na ya `23:59:54` zinatoa maumbo MAWILI tofauti.
    Data ya majaribio ilikuwa na precision moja kila wakati, kwa hiyo hii
    ilipita tests zote na kufeli kwenye data halisi:

        ValueError: time data "2016-02-01T23:59:54+00:00" doesn't match
        format "%Y-%m-%dT%H:%M:%S.%f%z"
    """
    def kipande(start: datetime, minutes: int, offset_us: int) -> pd.DataFrame:
        stamps = pd.date_range(start, periods=minutes, freq="1min", tz="UTC") + pd.Timedelta(
            microseconds=offset_us
        )
        bid = pd.Series([2400.0 + (i % 50) * 0.01 for i in range(minutes)])
        return pd.DataFrame(
            {
                "timestamp": stamps.astype("datetime64[us, UTC]"),
                "bid": bid.values,
                "ask": (bid + 0.01).values,
                "bid_vol": [1.0] * minutes,
                "ask_vol": [2.0] * minutes,
            }
        )

    # Mkia una µs (70000); kichwa hakina — hasa kama data halisi ilivyo.
    julai = pd.concat(
        [
            kipande(datetime(2026, 7, 31, 0, 0, tzinfo=timezone.utc), 1440, 0),
            kipande(datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc), 300, 70000),
        ]
    )
    agosti = pd.concat(
        [
            kipande(datetime(2026, 8, 1, 5, 0, tzinfo=timezone.utc), 1140, 0),
            kipande(datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc), 1440, 0),
        ]
    )
    _b_partition(l0_root, "XAUUSD", "2026-07.parquet", julai)
    _b_partition(l0_root, "XAUUSD", "2026-08.parquet", agosti)

    calendar = build_session_calendar(cfg, l0_root).calendar
    report = run_quality_audit(cfg, l0_root, calendar=calendar, symbols=["XAUUSD"])

    assert report.split_days_merged == 1
    moja = next(
        d for part in report.partitions for d in part.days if d.day == "2026-08-01"
    )
    assert "." in moja.first_ts and moja.last_ts.endswith("+00:00")
    assert [c.name for c in moja.checks].count("session_match") == 1


def test_vyanzo_viwili_vya_siku_moja_havichanganywi(cfg, l0_root):
    """Aggregator na broker wenye siku ile ile ni vipimo VIWILI HURU.

    Si nusu mbili za siku moja. Kuviunganisha kungejumlisha dakika za vyanzo
    viwili — alama yake ilikuwa `coverage max = 2.0084` kwenye data halisi —
    kungefuta kimoja kwenye ripoti, na kungeondoa uwezekano wa
    kuvilinganisha, ambao ndio msingi wa swali kubwa la R0 (§2.2).
    """
    def siku(day: date) -> pd.DataFrame:
        stamps = pd.date_range(
            datetime(day.year, day.month, day.day, tzinfo=timezone.utc),
            periods=1440,
            freq="1min",
            tz="UTC",
        )
        bid = pd.Series([2400.0 + (i % 50) * 0.01 for i in range(1440)])
        return pd.DataFrame(
            {
                "timestamp": stamps.astype("datetime64[us, UTC]"),
                "bid": bid.values,
                "ask": (bid + 0.01).values,
                "bid_vol": [1.0] * 1440,
                "ask_vol": [2.0] * 1440,
            }
        )

    pamoja = pd.concat([siku(date(2026, 8, d)) for d in (3, 4)])
    for chanzo in ("aggregator", "broker"):
        path = l0_root / f"provenance={chanzo}" / "symbol=XAUUSD" / "2026-08.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "ts": (pamoja["timestamp"].astype("int64") // 1000).values,
                "bid": pamoja["bid"].values,
                "ask": pamoja["ask"].values,
                "bid_volume": pamoja["bid_vol"].values,
                "ask_volume": pamoja["ask_vol"].values,
            }
        ).to_parquet(path, index=False)

    calendar = build_session_calendar(cfg, l0_root).calendar
    report = run_quality_audit(cfg, l0_root, calendar=calendar, symbols=["XAUUSD"])

    assert report.split_days_merged == 0, "vyanzo viwili si vipande viwili"
    assert report.total_days == 4, "siku 2 x vyanzo 2 — zote zinabaki"
    kwa_siku = [d for part in report.partitions for d in part.days if d.day == "2026-08-03"]
    assert len(kwa_siku) == 2
    for d in kwa_siku:
        assert d.observed_minutes == 1440, "dakika HAZIJAJUMLISHWA kati ya vyanzo"


def test_siku_isiyogawanywa_haiguswi(cfg, l0_tree):
    """Toleo A linaandika kwa SIKU — hakuna cha kuunganisha, na hakuna kinachobadilika."""
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["EURUSD"])

    assert report.split_days_merged == 0
    assert report.total_days == len(DAYS)
    assert report.excluded_days() == {"EURUSD": [DAYS[2].isoformat()]}


# ===========================================================================
# Kutolewa nje kwa UAMUZI ULIOANDIKWA, si kwa check (PD 2026-08-09)
# ===========================================================================


def _excluded_range(**kwargs) -> dict:
    entry = {
        "symbols": ["XAUUSD"],
        "from": "2026-08-04",
        "to": "2026-08-05",
        "reason": "chanzo kilipungua saa 2 kwa siku",
    }
    entry.update(kwargs)
    return entry


def test_kipindi_kilichoondolewa_hakihukumiwi_na_sababu_inasafiri(cfg, l0_tree):
    """Siku ndani ya kipindi haipimwi hata kidogo; sababu ya PD inabaki nayo.

    Sababu ni sehemu ya deliverable: mtu atakayeona namba za T2 lazima aone
    pia kilichotolewa na KWA NINI, bila kufungua git log.
    """
    from src.data.quality import FAIL_EXCLUDED_BY_PD

    cfg.raw["quality"]["excluded_ranges"] = [_excluded_range()]
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["XAUUSD"])

    part = report.partitions[0]
    blocked = {d.day: d for d in part.days if not d.passed}
    assert set(blocked) == {"2026-08-04", "2026-08-05"}
    for day in blocked.values():
        assert [c.name for c in day.checks] == ["excluded"], "hakuna check inayoendeshwa"
        assert day.fail_reasons == [FAIL_EXCLUDED_BY_PD]
        assert day.checks[0].detail == "chanzo kilipungua saa 2 kwa siku"

    assert part.usable_days == ["2026-08-03", "2026-08-06"]
    assert report.reason_counts()[FAIL_EXCLUDED_BY_PD] == 2


def test_siku_nje_ya_kipindi_inahukumiwa_kama_kawaida(cfg, l0_tree):
    """Kifungu ni cha KIPINDI, si swichi ya symbol nzima."""
    cfg.raw["quality"]["excluded_ranges"] = [_excluded_range(to="2026-08-04")]
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["XAUUSD"])

    days = {d.day: d for d in report.partitions[0].days}
    assert days["2026-08-04"].fail_reasons == ["excluded_by_pd"]
    assert days["2026-08-05"].passed, "siku ya nje ya kipindi bado inapimwa kwa checks"
    assert [c.name for c in days["2026-08-05"].checks] != ["excluded"]


def test_symbol_isiyotajwa_haiguswi(cfg, l0_tree):
    """EURUSD ni Toleo A; kasoro ya chanzo cha Toleo B haihusiani nayo."""
    cfg.raw["quality"]["excluded_ranges"] = [_excluded_range()]
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["EURUSD"])

    reasons = report.reason_counts()
    assert "excluded_by_pd" not in reasons
    # Siku ya 3 bado inafeli kwa coverage — checks hazijazimwa kwa bahati mbaya.
    assert report.excluded_days() == {"EURUSD": [DAYS[2].isoformat()]}


def test_kizingiti_hakiwezi_kurudisha_siku_iliyoondolewa_na_pd(cfg, l0_tree):
    """`--what-if` ni ya VIZINGITI. Uamuzi wa PD hauwezi kulegezwa kwa kizingiti.

    Kama siku ya PD ingehesabiwa `recovered`, jedwali lingemshauri PD kulegeza
    coverage ili kurudisha siku ambazo yeye mwenyewe alizuia — ushauri wa uwongo.
    """
    from src.data.quality import what_if

    cfg.raw["quality"]["excluded_ranges"] = [_excluded_range()]
    calendar = build_session_calendar(cfg, l0_tree).calendar
    detail = run_quality_audit(cfg, l0_tree, calendar=calendar, symbols=["XAUUSD"]).to_detail()

    study = what_if(detail, {"coverage": 0.0, "gap_seconds": 1e9, "session_match": 1e9})
    assert study["failing_after"] == 2, "siku mbili za PD zinabaki zimefeli"
    assert study["recovered"] == 0


def test_kifungu_bila_symbols_kinahusu_zote(cfg, l0_tree):
    """Kukatika kwa chanzo kunaweza kugusa symbols zote — orodha tupu = zote."""
    cfg.raw["quality"]["excluded_ranges"] = [_excluded_range(symbols=[])]
    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar)

    assert report.reason_counts()["excluded_by_pd"] == 4  # symbols 2 x siku 2


def test_config_ya_repo_inabeba_kipindi_cha_2023_cha_toleo_b(cfg):
    """Kipimo cha data halisi kikaingia config, si kwenye kumbukumbu ya mtu."""
    from src.data.quality import excluded_reason

    for symbol in ("EURCHF", "GBPJPY", "XAUUSD"):
        reason = excluded_reason(cfg, symbol, date(2023, 6, 15))
        assert "Toleo B" in reason and "2023" in reason
        assert excluded_reason(cfg, symbol, date(2024, 6, 15)) == ""
    assert excluded_reason(cfg, "EURUSD", date(2023, 6, 15)) == ""


def test_kipindi_kinabadilisha_config_hash(cfg, tmp_path):
    """Kilichotolewa nje ni sehemu ya `dataset_id`, si mpangilio wa mtumiaji.

    Kubadilisha kipindi KUNALAZIMU `check-l1` kuendeshwa upya (cache inajitupa
    kwa `config_hash`) na kunabadilisha `dataset_id` ya kila kitu kinachofuata.
    Hilo ndilo linalofanya uamuzi wa PD uwe wa kudumu badala ya wa dakika.
    """
    from src.data.config import load_config

    env = dict(cfg.env)
    text = cfg.path.read_text(encoding="utf-8")
    assert "excluded_ranges:" in text

    other = tmp_path / "data.yaml"
    other.write_text(text.replace('to:      "2023-12-31"', 'to:      "2023-06-30"'), "utf-8")
    assert load_config(other, env=env).config_hash != cfg.config_hash


def test_kizingiti_kinaweza_kuwa_cha_kila_symbol(cfg):
    """Dhahabu ina mapumziko ya kila siku; EURUSD haina."""
    from src.data.quality import _per_symbol

    cfg.raw["quality"]["max_gap_seconds"] = {"default": 3600, "XAUUSD": 5400}
    assert _per_symbol(cfg, "quality.max_gap_seconds", "XAUUSD", 3600) == 5400
    assert _per_symbol(cfg, "quality.max_gap_seconds", "EURUSD", 3600) == 3600

    cfg.raw["quality"]["max_gap_seconds"] = 900       # namba moja bado inakubalika
    assert _per_symbol(cfg, "quality.max_gap_seconds", "XAUUSD", 3600) == 900


def test_what_if_inakataa_ripoti_ya_muundo_wa_zamani(cfg, l0_tree):
    """Ripoti ya zamani haina `days` — `what_if` ingehesabu siku 0 KIMYA."""
    from src.data.quality import what_if

    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar).to_detail()
    from src.data.quality import CHECK_SCHEMA_VERSION

    assert report["schema"] == CHECK_SCHEMA_VERSION, "ripoti inapigwa chapa toleo la CODE"
    assert what_if(report, {"coverage": 0.9})["days"] > 0

    zamani = {**report, "schema": 1}
    with pytest.raises(ValueError, match="muundo wa zamani"):
        what_if(zamani, {"coverage": 0.9})


def test_ripoti_ya_code_ya_zamani_inatambulika(cfg, l0_tree, tmp_path, capsys):
    """Ripoti ya code ya zamani inaonekana SAWA KABISA na ya mpya.

    Namba ni halali, jedwali ni kamili, na hakuna kinachotofautiana kwa macho.
    2026-08-09 hilo lilipoteza saa nane: `audit.bat` iliendeshwa kabla ya
    `git pull`, matokeo yakawa ya code ya zamani, na `r0-summary` ikayaonyesha
    kama kawaida. Chapa ya toleo + onyo ndizo zinazofanya hilo lionekane.
    """
    from src.data.cli import main
    from src.data.quality import (
        CHECK_SCHEMA_VERSION,
        render_threshold_study,
        schema_warning,
        threshold_study,
    )

    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar)
    assert schema_warning(report.to_json()) == "", "ripoti ya sasa hailalamiki"

    zamani = {**report.to_json(), "schema": CHECK_SCHEMA_VERSION - 1}
    onyo = schema_warning(zamani)
    assert "muundo" in onyo and "audit.bat" in onyo

    out_dir = tmp_path / "ripoti"
    out_dir.mkdir()
    (out_dir / "quality_report.json").write_text(json.dumps(zamani), encoding="utf-8")
    main(["r0-summary", "--out-dir", str(out_dir)])
    assert "ONYO" in capsys.readouterr().err, "onyo linatoka KABLA ya namba"

    study = threshold_study({**report.to_detail(), "schema": CHECK_SCHEMA_VERSION - 1})
    assert study["legacy"] is False, "si muundo wa hukumu-kwa-faili"
    assert "ONYO" in render_threshold_study(study)


def test_threshold_study_inaonya_ripoti_ya_zamani(cfg, l0_tree):
    from src.data.quality import render_threshold_study, threshold_study

    calendar = build_session_calendar(cfg, l0_tree).calendar
    report = run_quality_audit(cfg, l0_tree, calendar=calendar).to_detail()
    assert threshold_study(report)["unit"] == "siku"

    zamani = threshold_study({**report, "schema": 1})
    assert zamani["legacy"] is True
    assert "muundo wa zamani" in render_threshold_study(zamani)
