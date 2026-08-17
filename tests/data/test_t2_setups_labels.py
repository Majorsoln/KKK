"""T2 — SETUP-v1 (DF-20) na labels za L4 (DF-09/10/11/21, K1-07).

Somo la T1 limeingia hapa moja kwa moja: data ya majaribio iliyo SAFI KUPITA
KIASI inaficha kasoro hadi data halisi. Kwa hiyo kesi hizi zinabeba kwa
makusudi vitu vilivyotuumiza: gaps, spread inayoingia kwenye path, mipaka ya
dirisha, na mali ya prefix (uamuzi wa `t` usibadilike data ya baadaye
ikibadilika).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.indicators import atr, rolling_pct_rank
from src.data.labels import (
    SL_FIRST,
    TIMEOUT,
    TP_FIRST,
    fill_probe,
    quality_bucket,
    r_net,
    resolve_point,
)
from src.data.setups import detect_setups

T0 = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


# ===========================================================================
# Viashiria (§6.1 sheria 6 na 7)
# ===========================================================================


def _bars(n: int, seed: int = 0, spread: float = 1.0) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    close = 1.10 + np.cumsum(rng.normal(0, 0.0005, n))
    noise = np.abs(rng.normal(0, 0.0003, n))
    frame = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.0004 + noise,
            "low": close - 0.0004 - noise,
            "close": close,
            "spread_p50": spread,
            "is_valid": True,
        },
        index=pd.date_range("2026-01-05", periods=n, freq="1h", tz="UTC"),
    )
    frame.index.name = "timestamp"
    return frame


def test_atr_haina_thamani_kabla_dirisha_halijajaa():
    """Sheria ya 7: NaN ni NaN — si sifuri, si high-low ya bar ya kwanza."""
    bars = _bars(30)
    series = atr(bars, period=14)
    assert series.iloc[:14].isna().all(), "bars za mwanzo hazina ATR"
    assert series.iloc[14:].notna().all()
    assert (series.dropna() > 0).all()


def test_pct_rank_inatumia_historia_yake_pekee():
    """Global rank ni uvujaji (§6.1 sheria 2) — kila kipimo ni dhidi ya NYUMA yake."""
    series = pd.Series(np.arange(100, dtype=float))
    rank = rolling_pct_rank(series, window=10)
    # Mfululizo unaopanda daima: kila thamani ni kubwa kuliko dirisha lake lote.
    assert rank.iloc[20:].round(6).eq(1.0).all()
    assert rank.iloc[:9].isna().all()


# ===========================================================================
# DF-20 — SETUP-v1
# ===========================================================================


@pytest.fixture
def setup_cfg(cfg):
    # Madirisha ya majaribio: madogo, la sivyo kila test inahitaji bars 3,000+.
    cfg.raw["setups"]["spread_median_window_bars"] = 100
    cfg.raw["setups"]["atr_band_window_months"] = 1
    return cfg


def test_setup_ni_muunganiko_wa_gates_tatu(setup_cfg):
    """`is_setup` = eligible NA gates zote tatu — hakuna njia ya mkato."""
    bars = _bars(900)
    result = detect_setups(setup_cfg, bars, "EURUSD")
    f = result.frame
    manual = f["eligible"] & f["spread_ok"] & f["atr_ok"] & f["trigger_ok"]
    assert (f["is_setup"] == manual).all()
    assert result.stats["setups"] == int(manual.sum())


def test_spread_gate_inakataa_bar_ghali(setup_cfg):
    """Soko lisilolipika si setup — bar yenye spread mara 10 inakataliwa."""
    bars = _bars(900)
    ghali = bars.index[700]
    bars.loc[ghali, "spread_p50"] = 10.0
    result = detect_setups(setup_cfg, bars, "EURUSD")
    assert not result.frame.loc[ghali, "spread_ok"]
    assert not result.frame.loc[ghali, "is_setup"]


def test_trigger_inakamata_impulse_na_mwelekeo_wake(setup_cfg):
    """|close − close[4]| ≥ ATR → trigger; ishara ya mwendo ndiyo mwelekeo."""
    bars = _bars(900)
    # Panda kwa nguvu bars 4 mfululizo kuanzia 800 — bila kuvimbisha ranges
    # (ATR isipande, la sivyo band inaikataa kwa sababu nyingine).
    jump = bars["close"].diff().abs().mean() * 4
    for i in range(801, 805):
        lift = jump * (i - 800)
        for col in ("open", "high", "low", "close"):
            bars.iloc[i, bars.columns.get_loc(col)] += lift
    result = detect_setups(setup_cfg, bars, "EURUSD")
    row = result.frame.iloc[804]
    assert row["trigger_ok"], f"impulse_atr={row['impulse_atr']:.2f}"
    assert row["direction"] == 1, "mwendo wa juu → BUY"


def test_uamuzi_wa_jana_haubadiliki_kwa_data_ya_leo(setup_cfg):
    """Mali ya PREFIX — hii ndiyo kinga ya §4.3 dhidi ya uvujaji wa uchaguzi.

    Bars 600 za kwanza zikihukumiwa peke yake au ndani ya 900, majibu ni
    YALE YALE. Kama yangebadilika, sheria ya setup ingekuwa inasoma baadaye —
    na sentinel ya §4.2 ingelia. Hapa tunathibitisha bila kusubiri sentinel.
    """
    bars = _bars(900)
    full = detect_setups(setup_cfg, bars, "EURUSD").frame.iloc[:600]
    prefix = detect_setups(setup_cfg, bars.iloc[:600], "EURUSD").frame
    for col in ("is_setup", "is_control", "direction", "eligible"):
        pd.testing.assert_series_equal(full[col], prefix[col], check_names=False)


def test_control_inazalishika_upya_na_haigusi_setups(setup_cfg):
    """Control ni hash ya (seed, symbol, muda) — si bahati ya mpangilio."""
    bars = _bars(900)
    first = detect_setups(setup_cfg, bars, "EURUSD").frame
    second = detect_setups(setup_cfg, bars, "EURUSD").frame
    pd.testing.assert_series_equal(first["is_control"], second["is_control"])

    assert not (first["is_setup"] & first["is_control"]).any(), "control ni ZISIZO setup"
    # Sehemu inatoka CONFIG, si namba iliyoandikwa hapa: PD anaituna (kabla
    # ya labels), na test isivunjike kwa uamuzi wake halali.
    target = float(setup_cfg.get("setups.control_sample_frac"))
    eligible_non_setup = (first["eligible"] & ~first["is_setup"]).sum()
    frac = first["is_control"].sum() / eligible_non_setup
    assert abs(frac - target) < 0.6 * target, f"control frac={frac:.3f} vs lengo {target}"

    # Symbol tofauti → chaguo tofauti (seed ile ile haitoi ulinganifu wa uwongo).
    other = detect_setups(setup_cfg, bars, "XAUUSD").frame
    assert not first["is_control"].equals(other["is_control"])


def test_decision_time_ni_close_ya_bar(setup_cfg):
    """As-of (§4.1): uamuzi unafanyika bar INAPOFUNGWA — open + saa 1 kwa H1."""
    bars = _bars(900)
    frame = detect_setups(setup_cfg, bars, "EURUSD").frame
    assert (frame["decision_time"] == frame.index + pd.Timedelta(hours=1)).all()


# ===========================================================================
# DF-09/10/21 — barrier grid kwa path ya ticks
# ===========================================================================


def _ticks(seconds: int, bid_path, spread: float = 0.0002) -> pd.DataFrame:
    stamps = pd.date_range(T0, periods=seconds, freq="1s", tz="UTC")
    bid = np.asarray(bid_path, dtype=float)
    assert len(bid) == seconds
    return pd.DataFrame(
        {
            "timestamp": stamps.astype("datetime64[us, UTC]"),
            "bid": bid,
            "ask": bid + spread,
            "bid_vol": 1.0,
            "ask_vol": 1.0,
        }
    )


HORIZON = pd.Timestamp(T0) + pd.Timedelta(hours=24)
GRID_SL = [0.5, 1.0]
GRID_TP = [0.5, 1.0]
ATR = 0.0010


def test_tp_inayoguswa_kwanza_inatoa_darasa_1():
    bid = np.linspace(1.1000, 1.1030, 600)  # inapanda tu — SL haiguswi kamwe
    point = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, 1, ATR, GRID_SL, GRID_TP)
    assert point is not None
    assert all(c.outcome == TP_FIRST for c in point.cells)
    # TP ya karibu inaguswa KABLA ya ya mbali — mpangilio wa touch una maana.
    close_tp = next(c for c in point.cells if c.tp_atr == 0.5)
    far_tp = next(c for c in point.cells if c.tp_atr == 1.0)
    assert close_tp.touch_index < far_tp.touch_index


def test_sl_inapimwa_kwa_bei_ya_kufungia_si_mid():
    """Spread imo NDANI ya label (DF-21). BUY inafunga kwa BID.

    Path ambapo MID haigusi SL lakini BID inaigusa: mid-based labeler
    angesema hakuna touch — na live ungekuwa umesimamishwa.
    """
    entry_ask = 1.1002  # bid 1.1000 + spread 2 pips
    sl_price = entry_ask - 0.5 * ATR  # 1.0997
    bid = np.full(600, 1.1000)
    bid[100:] = sl_price  # bid inagusa SL; mid = 1.0998 > entry_mid − 0.5×ATR=1.0996
    point = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, 1, ATR, [0.5], [3.0])
    cell = point.cells[0]
    assert cell.outcome == SL_FIRST
    assert cell.touch_index == 100
    mid_sl = point.entry_mid - 0.5 * ATR
    assert ((bid + 0.0002 + bid) / 2 > mid_sl).all(), "kwa MID, SL haikuguswa — ndiyo hoja"


def test_gap_honest_touch_kwenye_bei_ya_kwanza_baada_ya_gap():
    """Gap ikiruka SL, label inasoma touch pale bei ilipotua — si pale SL ilipo."""
    bid = np.full(600, 1.1000)
    bid[300:] = 1.0950  # gap kubwa chini — inaruka SL zote
    point = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, 1, ATR, GRID_SL, [3.0])
    for cell in point.cells:
        assert cell.outcome == SL_FIRST
        assert cell.touch_index == 300, "touch ni tick ya KWANZA baada ya gap"
        assert not cell.tie_break, "SL na TP ziko pande mbili — tick moja haiwezi zote (§5.2)"


def test_timeout_ni_darasa_lenye_terminal_return():
    """Timeout haitupwi kimya (§5.5) — inabeba E[R|timeout] ya cell yake."""
    bid = np.full(600, 1.1000)
    bid += np.linspace(0, 0.0002, 600)  # mwendo mdogo — hakuna barrier inayoguswa
    point = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, 1, ATR, [1.0, 2.0], [3.0])
    for cell in point.cells:
        assert cell.outcome == TIMEOUT
        assert cell.timeout_return_r == pytest.approx(point.terminal_atr / cell.sl_atr)
    # R units: sl kubwa mara mbili → R ndogo mara mbili kwa mwendo ule ule.
    r1, r2 = (c.timeout_return_r for c in point.cells)
    assert r1 == pytest.approx(2 * r2)


def test_sell_ni_kioo_cha_buy():
    """SELL: entry kwa BID, kufunga kwa ASK, TP chini."""
    bid = np.linspace(1.1000, 1.0970, 600)  # inashuka — SELL inashinda
    point = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, -1, ATR, [1.0], [1.0])
    assert point.entry_trade == pytest.approx(1.1000)  # bid, si ask
    assert point.cells[0].outcome == TP_FIRST
    assert point.terminal_atr > 0, "trade ya SELL kwenye soko linaloshuka INASHINDA"


def test_quantile_inatumia_mid_bila_mwelekeo():
    """L-A ni kipimo cha MWENDO WA SOKO (§5.1) — mid, na haigeuki na direction."""
    bid = np.linspace(1.1000, 1.1020, 600)
    buy = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, 1, ATR, [1.0], [1.0])
    sell = resolve_point(_ticks(600, bid), pd.Timestamp(T0), HORIZON, -1, ATR, [1.0], [1.0])
    assert buy.quantile_y == pytest.approx(sell.quantile_y), "L-A haina upande"
    expected = np.log(buy.terminal_mid / buy.entry_mid) / (ATR / buy.entry_mid)
    assert buy.quantile_y == pytest.approx(expected)
    # terminal_atr NDIYO yenye ishara ya trade.
    assert buy.terminal_atr > 0 and sell.terminal_atr < 0


def test_ticks_kabla_ya_uamuzi_haziingii():
    """Label inayosoma kabla ya `t` ni uvujaji — dirisha linaanzia decision_time."""
    bid = np.full(600, 1.1000)
    bid[:50] = 1.0900  # kabla ya t: bei ya chini kabisa — ingegusa SL zote
    start = pd.Timestamp(T0) + pd.Timedelta(seconds=50)
    point = resolve_point(_ticks(600, bid), start, HORIZON, 1, ATR, [1.0], [3.0])
    assert point.cells[0].outcome == TIMEOUT, "historia ya kabla ya t haihusiki"
    assert point.ticks_seen == 550


def test_dirisha_tupu_linarudisha_none():
    bid = np.full(60, 1.1000)
    late = pd.Timestamp(T0) + pd.Timedelta(hours=5)
    assert resolve_point(_ticks(60, bid), late, late + pd.Timedelta(hours=1), 1, ATR, [1], [1]) is None


# ===========================================================================
# K1-07 — L-C fill bootstrap
# ===========================================================================


def test_stop_ya_gap_inavuka_cap_hairuhusiwi():
    """Gap-honest kwenye fill pia: slippage halisi inarekodiwa, cap inaamua."""
    bid = np.full(100, 1.1000)
    bid[40:] = 1.1030  # gap juu kupita stop
    ticks = _ticks(100, bid)
    probe = fill_probe(ticks, side=1, order_type="stop", price=1.1010, cap_pips=3.0, pip=0.0001)
    assert not probe.filled, "slippage ya pips 22 > cap 3"
    assert probe.slippage_pips == pytest.approx(22.0)  # ask 1.1032 − 1.1010

    ndogo = fill_probe(ticks, side=1, order_type="stop", price=1.1031, cap_pips=3.0, pip=0.0001)
    assert ndogo.filled and ndogo.slippage_pips == pytest.approx(1.0)


def test_limit_inajazwa_bei_ikifika():
    bid = np.linspace(1.1000, 1.0990, 100)
    probe = fill_probe(_ticks(100, bid), side=1, order_type="limit", price=1.0995, cap_pips=3.0, pip=0.0001)
    assert probe.filled and probe.slippage_pips <= 0, "limit haina slippage chanya"


def test_market_ni_prior_si_path():
    """§5.3: latency ya live haikisiki kwa historia — prior + calibration."""
    probe = fill_probe(_ticks(10, np.full(10, 1.1)), 1, "market", 1.1, 3.0, 0.0001)
    assert probe.filled and probe.source == "prior"


# ===========================================================================
# L-D — quality buckets
# ===========================================================================


def test_r_net_inatoa_gharama_kwenye_r():
    assert r_net(TP_FIRST, tp_atr=2.0, sl_atr=1.0, cost_pips=2.0, sl_pips=10.0) == pytest.approx(1.8)
    assert r_net(SL_FIRST, tp_atr=2.0, sl_atr=1.0, cost_pips=2.0, sl_pips=10.0) == pytest.approx(-1.2)


def test_buckets_zinatoka_config(cfg):
    thresholds = cfg.get("labels.quality_buckets")
    assert quality_bucket(2.0, thresholds) == "A+"
    assert quality_bucket(1.0, thresholds) == "A"
    assert quality_bucket(0.5, thresholds) == "B"
    assert quality_bucket(0.1, thresholds) == "reject"


# ===========================================================================
# CLI — detect-setups (mzunguko mzima juu ya L2 ndogo)
# ===========================================================================


def test_detect_setups_inaandika_ushahidi_wa_pre_registration(cfg, tmp_path, monkeypatch):
    """Kabla ya sahihi ya DF-20, PD anahitaji RATE kwenye faili — si hadithi.

    L2 ya siku 4 haitoshi kwa madirisha ya kweli (bars 528+), kwa hiyo setups
    ni 0 na ONYO la rate linarudi (exit 1) — lakini muundo mzima unathibitishwa:
    parquet ya kila symbol, `in_holdout` (G2), na summary yenye kila kitambulisho.
    """
    import json as _json

    from src.data.audit import build_l2
    from src.data.cli import main

    # CLI inasoma env halisi (ndivyo PD anavyoiendesha); hapa inaelekezwa
    # kwenye storage ya muda ya fixture — bila kugusa mashine ya mtu.
    for key, value in cfg.env.items():
        monkeypatch.setenv(key, value)

    frames = [_day_ticks_for_l2(d) for d in range(3, 7)]
    root = tmp_path / "L0"
    path = root / "provenance=aggregator" / "symbol=EURUSD" / "2026"
    path.mkdir(parents=True)
    for i, frame in enumerate(frames):
        frame.to_parquet(path / f"2026-08-0{i + 3}.parquet", index=False)
    build_l2(cfg, root, cfg.l2_root, symbols=["EURUSD"])

    rc = main(["detect-setups", "--symbols", "EURUSD"])
    assert rc in (0, 1)

    setups_path = (
        cfg.research_root / "data" / "L4_labels" / "setups" / "symbol=EURUSD" / "setups.parquet"
    )
    assert setups_path.is_file()
    frame = pd.read_parquet(setups_path)
    assert {"is_setup", "is_control", "direction", "in_holdout", "decision_time"} <= set(frame.columns)
    # 2026-08 iko BAADA ya holdout_start (2024-04-01) — kila decision point
    # hapa imetengwa na training (G2). Mjenzi wa labels ataikataa.
    assert frame["in_holdout"].all()

    summary = _json.loads(
        (cfg.path_of("storage.reports_root") / "r1" / "setup_rates.json").read_text(encoding="utf-8")
    )
    assert summary["rule_id"] == "SETUP-v1"
    assert summary["config_hash"] and summary["code_rev"]
    assert "EURUSD" in summary["per_symbol"]


def _day_ticks_for_l2(day: int, month: int = 8, year: int = 2026) -> pd.DataFrame:
    stamps = pd.date_range(
        datetime(year, month, day, 0, 0, tzinfo=timezone.utc), periods=1440, freq="1min", tz="UTC"
    )
    bid = pd.Series([1.10 + (i % 60) * 0.0001 for i in range(1440)])
    return pd.DataFrame(
        {
            "timestamp": stamps.astype("datetime64[us, UTC]"),
            "bid": bid.values,
            "ask": (bid + 0.0001).values,
            "bid_vol": [1.0] * 1440,
            "ask_vol": [2.0] * 1440,
        }
    )


def test_rate_inahesabiwa_kwa_train_val_pekee(cfg, tmp_path, monkeypatch):
    """Numerator na denominator lazima ziwe za DIRISHA MOJA.

    Kipimo cha kwanza kilitoa setups bila holdout lakini eligible NAYO —
    holdout ni ~miaka 2 kati ya 10.6, kwa hiyo rate iliyoripotiwa ilikuwa
    imeshushwa kwa ~20% kimya. Namba iliyo sahihi kwa nusu ni namba mbaya.
    """
    import json as _json

    from src.data.audit import build_l2
    from src.data.cli import main

    for key, value in cfg.env.items():
        monkeypatch.setenv(key, value)

    # Siku 2 kabla ya holdout_start (2024-04-01) na 2 baada yake.
    root = tmp_path / "L0"
    path = root / "provenance=aggregator" / "symbol=EURUSD" / "2024"
    path.mkdir(parents=True)
    for month, day in ((3, 26), (3, 27), (4, 2), (4, 3)):
        frame = _day_ticks_for_l2(day, month=month, year=2024)
        frame.to_parquet(path / f"2024-{month:02d}-{day:02d}.parquet", index=False)
    build_l2(cfg, root, cfg.l2_root, symbols=["EURUSD"])
    main(["detect-setups", "--symbols", "EURUSD"])

    summary = _json.loads(
        (cfg.path_of("storage.reports_root") / "r1" / "setup_rates.json").read_text(encoding="utf-8")
    )
    tv = summary["per_symbol"]["EURUSD"]["train_val"]
    setups_path = (
        cfg.research_root / "data" / "L4_labels" / "setups" / "symbol=EURUSD" / "setups.parquet"
    )
    frame = pd.read_parquet(setups_path)
    train = frame[~frame["in_holdout"]]

    assert tv["eligible"] == int(train["eligible"].sum()), "denominator ni TRAIN+VAL"
    assert tv["setups"] == int(train["is_setup"].sum()), "numerator ni TRAIN+VAL"
    assert frame["in_holdout"].any() and (~frame["in_holdout"]).any(), "sampuli ina pande zote"
    assert summary["pooled_setups_train_val"] == tv["setups"]
    assert set(summary["gate_rejects_train_val"]) == {
        "fail_spread",
        "fail_atr_band",
        "fail_trigger",
    }


def test_sweep_inaonyesha_rate_kwa_kila_kizingiti(setup_cfg):
    """Kutuna kunahitaji kuona mgawanyo — utaratibu ule ule wa `quality-stats`."""
    from src.data.setups import sweep_trigger

    from src.data.setups import detect_setups

    bars = _bars(900)
    configured = float(setup_cfg.get("setups.trigger.min_atr_mult"))
    rows = sweep_trigger(setup_cfg, bars, "EURUSD", [0.5, 1.0, configured, 3.5])
    rates = [r["rate"] for r in rows]
    assert rates == sorted(rates, reverse=True), "kizingiti kikipanda, rate inashuka"

    # Sweep kwenye kizingiti cha CONFIG lazima itoe jibu lile lile la
    # `detect_setups` — chanzo kimoja, si hesabu mbili zinazoweza kutofautiana.
    baseline = detect_setups(setup_cfg, bars, "EURUSD")
    at_config = next(r for r in rows if r["min_atr_mult"] == configured)
    assert at_config["setups"] == baseline.stats["setups"]


def test_siku_iliyofeli_r0_haiwi_decision_point(setup_cfg):
    """§3 `fail_action: exclude` — hukumu ya R0 lazima ifike kwenye setups.

    Bila kiungo hiki, siku 912 alizoziondoa PD (2023 ya Toleo B) na kila siku
    iliyofeli checks zingeingia kwenye decision points KIMYA, na uamuzi
    ulioandikwa ungekuwa bure. Ushahidi kwamba haukuwepo: EURCHF ilikuwa na
    bars ZAIDI ya EURUSD, ingawa mwaka mzima wa 2023 ulikuwa umeondolewa.
    """
    # Kizingiti cha uzalishaji (2.5) hakitoi setup kwenye random walk ya
    # majaribio; legeza ili kuwe na kitu cha kupotea.
    setup_cfg.raw["setups"]["trigger"]["min_atr_mult"] = 1.0
    bars = _bars(900)
    bila = detect_setups(setup_cfg, bars, "EURUSD").frame
    siku_mbaya = sorted({str(d.date()) for d in bila.index[400:600]})
    na = detect_setups(setup_cfg, bars, "EURUSD", excluded_days=set(siku_mbaya)).frame

    assert na["day_excluded"].sum() > 0
    assert not (na["day_excluded"] & na["eligible"]).any(), "siku iliyofeli si eligible"
    assert not (na["day_excluded"] & na["is_setup"]).any()
    assert not (na["day_excluded"] & na["is_control"]).any(), "wala control"
    assert na["is_setup"].sum() < bila["is_setup"].sum(), "setups zinapungua"

    # Bars ZINABAKI kama historia (§3 sera ya NaN): ATR haitobolewi shimo.
    pd.testing.assert_series_equal(bila["atr"], na["atr"])


def test_hukumu_ni_ya_siku_ya_decision_time(setup_cfg):
    """Bar ya 23:00 inafunga 00:00 — inahukumiwa kwa siku INAYOFUNGA."""
    bars = _bars(900)
    frame = detect_setups(setup_cfg, bars, "EURUSD", excluded_days={"2026-01-10"}).frame
    zilizozuiwa = frame[frame["day_excluded"]]
    assert (zilizozuiwa["decision_time"].dt.strftime("%Y-%m-%d") == "2026-01-10").all()
    # Bar ya 23:00 ya tarehe 9 inafunga 00:00 ya tarehe 10 → inazuiwa.
    assert any(stamp.hour == 23 and stamp.day == 9 for stamp in zilizozuiwa.index)


def test_load_excluded_days_inasoma_ripoti_ya_r0(tmp_path):
    import json as _json

    from src.data.setups import load_excluded_days

    path = tmp_path / "quality_report.json"
    path.write_text(
        _json.dumps({"excluded_days": {"eurchf": ["2023-06-01", "2023-06-02"]}}), encoding="utf-8"
    )
    loaded = load_excluded_days(path)
    assert loaded == {"EURCHF": {"2023-06-01", "2023-06-02"}}, "symbol inakuwa herufi kubwa"
    assert load_excluded_days(tmp_path / "haipo.json") == {}


# ===========================================================================
# Mjenzi wa labels — kazi ya masaa (DF-09/10/11)
# ===========================================================================


def _l0_tree_for_labels(root, days: int = 30, start_day: int = 5) -> None:
    """Siku `days` za ticks za dakika, kuanzia 2024-01-05 (kabla ya holdout)."""
    base = root / "provenance=aggregator" / "symbol=EURUSD" / "2024"
    base.mkdir(parents=True, exist_ok=True)
    price = 1.1000
    for offset in range(days):
        day = datetime(2024, 1, start_day, tzinfo=timezone.utc) + pd.Timedelta(days=offset)
        stamps = pd.date_range(day, periods=1440, freq="1min", tz="UTC")
        rng = np.random.RandomState(offset)
        bid = price + np.cumsum(rng.normal(0, 0.00012, 1440))
        price = float(bid[-1])
        pd.DataFrame(
            {
                "timestamp": stamps.astype("datetime64[us, UTC]"),
                "bid": bid,
                "ask": bid + 0.0001,
                "bid_vol": 1.0,
                "ask_vol": 2.0,
            }
        ).to_parquet(base / f"{day:%Y-%m-%d}.parquet", index=False)


def test_horizon_ni_bars_si_masaa():
    """Ijumaa jioni, bars 24 zinavuka wikendi — dirisha ni siku 3, si saa 24.

    Kwa `timedelta(hours=24)` tungeishia Jumamosi, soko limefungwa, na label
    ingesoma `timeout` kwa sababu ya KALENDA badala ya soko.
    """
    from src.data.label_build import horizon_ends

    ijumaa = pd.date_range("2024-01-05 12:00", periods=4, freq="1h", tz="UTC")
    jumatatu = pd.date_range("2024-01-08 00:00", periods=30, freq="1h", tz="UTC")
    decision = pd.Series(ijumaa.append(jumatatu))
    ends = horizon_ends(decision, 24)

    assert ends.iloc[0] - decision.iloc[0] > pd.Timedelta(hours=24), "wikendi imo ndani"
    assert ends.iloc[-1] is pd.NaT or pd.isna(ends.iloc[-1]), "bars za mwisho hazina horizon"


def test_mjenzi_unatoa_points_na_barriers(cfg, tmp_path, monkeypatch):
    """Mzunguko mzima: setups → ticks → grid NZIMA kwa kila point.

    Idadi ya cells inatoka **config**, si namba iliyopigwa kwenye test. Grid
    ilipopanuliwa 5×5 → 7×7 (T5, 2026-08-17), `* 25` iliyopigwa hapa ilifeli —
    na ilikuwa ikithibitisha config ya jana, si mkataba wa mjenzi.
    """
    from src.data.audit import build_l2
    from src.data.cli import main
    from src.data.setups import detect_setups

    for key, value in cfg.env.items():
        monkeypatch.setenv(key, value)
    cfg.raw["setups"]["spread_median_window_bars"] = 48
    cfg.raw["setups"]["atr_band_window_months"] = 1
    cfg.raw["setups"]["trigger"]["min_atr_mult"] = 0.5
    cfg.raw["labels"]["horizon_bars"] = 6

    root = cfg.l0_root
    _l0_tree_for_labels(root)
    build_l2(cfg, root, cfg.l2_root, symbols=["EURUSD"])

    from src.data.bars import read_bars

    result = detect_setups(cfg, read_bars(cfg.l2_root, "EURUSD", "H1"), "EURUSD")
    out = cfg.research_root / "data" / "L4_labels" / "setups" / "symbol=EURUSD"
    out.mkdir(parents=True, exist_ok=True)
    result.frame.to_parquet(out / "setups.parquet")
    assert result.frame["is_setup"].sum() > 0, "sampuli haina setup — test isingepima kitu"

    monkeypatch.setattr("src.data.cli._load", lambda args: cfg)
    assert main(["build-labels", "--symbols", "EURUSD", "--skip-signature-check"]) in (0, 1)

    labels = cfg.research_root / "data" / "L4_labels" / "labels" / "symbol=EURUSD"
    points = pd.read_parquet(labels / "points-2024.parquet")
    barriers = pd.read_parquet(labels / "barriers-2024.parquet")

    assert len(points) > 0
    n_cells = len(cfg.get("labels.barrier.sl_atr")) * len(cfg.get("labels.barrier.tp_atr"))
    assert len(barriers) == len(points) * n_cells, f"grid nzima ({n_cells}) kwa KILA point"
    assert set(barriers["outcome"]) <= {TP_FIRST, SL_FIRST, TIMEOUT}
    assert (points["direction"].isin([1, -1])).all()
    assert (points["is_setup"] | points["is_control"]).all()
    # Malighafi ya L-D ipo, lakini GHARAMA haipo — RCE ndiyo mamlaka (§6.2 F6).
    assert {"spread_entry_pips", "atr_pips"} <= set(points.columns)
    assert "sl_pips" in barriers.columns
    assert not any("cost" in c or "r_net" in c for c in barriers.columns)
    # Toleo la 2: malighafi ya vipimo vitatu vya R1 (§5.1, §5.3, M1-vs-tick).
    assert {"terminal_trade", "quantile_y_trade", "spread_exit_pips"} <= set(points.columns)
    assert "touch_past_pips" in barriers.columns
    resolved = barriers[barriers["outcome"] != TIMEOUT]
    assert resolved["touch_past_pips"].notna().all()
    assert (resolved["touch_past_pips"] >= 0).all(), "umbali wa kupita barrier hasi hauwezekani"

    # R1 juu ya kile kile kilichoandikwa — bila kugusa ticks tena.
    rc = main(["r1-summary", "--symbols", "EURUSD"])
    summary = json.loads(
        (cfg.path_of("storage.reports_root") / "r1" / "r1_summary.json").read_text("utf-8")
    )
    assert summary["totals"]["cells"] == len(barriers)
    assert summary["base_rates"], "R1 bila base rates si R1"
    assert len(summary["base_rates"]) == n_cells, "cell moja moja ya grid, si wastani mmoja"
    assert summary["setup_vs_control"]["setup"]["cells"] > 0
    assert summary["setup_vs_control"]["control"]["cells"] > 0
    # Jiometri: kila cell iko chini ya sl/(sl+tp) — spread iko ndani ya path.
    #
    # Ni dai la KITAKWIMU, si la hakika: cell yenye resolutions chache inaweza
    # kuizidi kwa bahati. Grid ilipopanuliwa hadi `sl 4.0 / tp 0.5` (jiometri
    # 0.889), cells za pembeni zilipata resolutions kadhaa pekee kwenye sampuli
    # hii ndogo, na `diff` ikawa chanya kwa kelele. Kizingiti ni kile kile cha
    # `min_labels_per_cell` — dai linalopimwa pale linapopimika (T5, 2026-08-17).
    kubwa = [
        row for row in summary["base_rates"]
        if row["geometry_reliable"] and (row["n_tp"] + row["n_sl"]) >= 30
    ]
    for row in kubwa:
        assert row["diff"] <= 2.0 * row["se"], (
            f"cell {row['sl_atr']}/{row['tp_atr']}: p_tp {row['p_tp']:.3f} "
            f"iko juu ya jiometri {row['geometry']:.3f} kwa zaidi ya 2 SE"
        )
    # Cells zisizoaminika lazima ziwe zimetajwa, si kunyamazwa.
    zisizoaminika = [r for r in summary["base_rates"] if not r["geometry_reliable"]]
    for row in zisizoaminika:
        assert row["geometry_bias"] in {"none", "tp", "sl"}
    assert rc in (0, 1)
    assert (rc == 0) == (not summary["problems"])


def test_mjenzi_hauna_ruhusa_bila_sahihi_ya_df20(cfg, tmp_path, monkeypatch):
    """§4.3 sheria 5: R1 haianzi kabla PD hajasaini sheria ya setup."""
    from src.data.cli import main

    for key, value in cfg.env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("src.data.cli._load", lambda args: cfg)
    monkeypatch.setattr("src.governance.signatures.load", lambda *a, **k: [])

    assert main(["build-labels", "--symbols", "EURUSD"]) == 2


def test_holdout_haiingii_kwenye_labels(cfg):
    """G2 — ukaguzi wa PILI kwenye mpaka wenyewe, si kwenye alama pekee."""
    from datetime import date as _date

    from src.data.label_build import holdout_guard

    stamps = pd.to_datetime(
        ["2024-03-30", "2024-03-31", "2024-04-01", "2024-04-02"], utc=True
    )
    frame = pd.DataFrame({"decision_time": stamps})
    kept = holdout_guard(frame, _date(2024, 4, 1))
    assert list(kept["decision_time"].dt.strftime("%Y-%m-%d")) == ["2024-03-30", "2024-03-31"]


def test_kuendelea_hakujengi_upya_mwaka_uliokwisha(cfg, tmp_path, monkeypatch):
    """Kazi ya masaa ikikatika, inaendelea ilipoishia — si kuanza upya."""
    from src.data.audit import build_l2
    from src.data.cli import main
    from src.data.label_build import load_state
    from src.data.setups import detect_setups

    for key, value in cfg.env.items():
        monkeypatch.setenv(key, value)
    cfg.raw["setups"]["spread_median_window_bars"] = 48
    cfg.raw["setups"]["atr_band_window_months"] = 1
    cfg.raw["setups"]["trigger"]["min_atr_mult"] = 0.5
    cfg.raw["labels"]["horizon_bars"] = 6

    root = cfg.l0_root
    _l0_tree_for_labels(root, days=20)
    build_l2(cfg, root, cfg.l2_root, symbols=["EURUSD"])
    from src.data.bars import read_bars

    out = cfg.research_root / "data" / "L4_labels" / "setups" / "symbol=EURUSD"
    out.mkdir(parents=True, exist_ok=True)
    detect_setups(cfg, read_bars(cfg.l2_root, "EURUSD", "H1"), "EURUSD").frame.to_parquet(
        out / "setups.parquet"
    )
    monkeypatch.setattr("src.data.cli._load", lambda args: cfg)

    main(["build-labels", "--symbols", "EURUSD", "--skip-signature-check"])
    labels = cfg.research_root / "data" / "L4_labels" / "labels"
    state = load_state(labels / "_label_state.json")
    assert "EURUSD/2024" in state["done"]
    assert state["config_hash"] == cfg.config_hash

    stamp = (labels / "symbol=EURUSD" / "points-2024.parquet").stat().st_mtime_ns
    main(["build-labels", "--symbols", "EURUSD", "--skip-signature-check"])
    after = (labels / "symbol=EURUSD" / "points-2024.parquet").stat().st_mtime_ns
    assert after == stamp, "mwaka uliokwisha haujengwi upya"


def test_buffer_inatupa_kilichopita(cfg, tmp_path):
    """Bila `trim`, buffer ingekua hadi L0 nzima — GB, si MB."""
    from src.data.audit import select_partitions
    from src.data.label_build import TickWindow

    root = tmp_path / "L0"
    _l0_tree_for_labels(root, days=6)
    window = TickWindow(cfg, select_partitions(cfg, root, ["EURUSD"]))

    window.ensure(pd.Timestamp("2024-01-09", tz="UTC"))
    kubwa = window.rows
    assert kubwa > 0 and window.partitions_read >= 4

    window.trim(pd.Timestamp("2024-01-09", tz="UTC"))
    assert window.rows < kubwa, "frames zilizoisha zimetupwa"
    # Kusoma hakurudi nyuma: partitions zilizosomwa hazisomwi tena.
    before = window.partitions_read
    window.ensure(pd.Timestamp("2024-01-09", tz="UTC"))
    assert window.partitions_read == before


def test_ensure_inasimama_ikishafunika_haisomi_l0_nzima(cfg, tmp_path):
    """Kasoro iliyofungua `MemoryError`: ticks milioni 289 kwenye buffer.

    `last_stamp` ilikuwa ikisasishwa BAADA ya kitanzi, kwa hiyo sharti la
    `ensure` halikubadilika kamwe na kitanzi kilisoma kila partition ya symbol
    nzima. Test hii inashikilia kile ambacho `MemoryError` iliniambia.
    """
    from src.data.audit import select_partitions
    from src.data.label_build import TickWindow

    root = cfg.l0_root
    _l0_tree_for_labels(root, days=20)
    paths = select_partitions(cfg, root, ["EURUSD"])
    assert len(paths) == 20

    window = TickWindow(cfg, paths)
    window.ensure(pd.Timestamp("2024-01-06 12:00", tz="UTC"))
    assert window.partitions_read <= 3, f"ilisoma {window.partitions_read} kati ya 20"
    assert window.last_stamp > 0, "`last_stamp` inasasishwa ndani ya kitanzi"


def test_seek_inaruka_partitions_bila_kuzisoma(cfg, tmp_path):
    """Decision point ya kwanza iko miezi ~6 ndani — kuzisoma ni kupoteza muda."""
    from src.data.audit import select_partitions
    from src.data.label_build import TickWindow, _partition_end

    root = cfg.l0_root
    _l0_tree_for_labels(root, days=20)
    window = TickWindow(cfg, select_partitions(cfg, root, ["EURUSD"]))

    window.seek(pd.Timestamp("2024-01-18", tz="UTC"))
    assert window.partitions_skipped > 5
    assert window.partitions_read == 0, "kuruka HAKUSOMI parquet"

    window.ensure(pd.Timestamp("2024-01-19", tz="UTC"))
    stamps, _, _ = window.arrays()
    assert len(stamps) > 0

    # Kadirio la njia ni la JUU — bora kusoma isiyohitajika kuliko kuruka
    # inayohitajika. Faili ya siku inaisha ndani ya siku 3 za kadirio lake.
    daily = _partition_end(Path("provenance=aggregator/symbol=EURUSD/year=2024/month=01/day=15/ticks.parquet"))
    assert daily is not None and daily >= pd.Timestamp("2024-01-16", tz="UTC")
    monthly = _partition_end(Path("provenance=aggregator/symbol=XAUUSD/year=2020/month=03/ticks-2020-03.parquet"))
    assert monthly is not None and monthly >= pd.Timestamp("2020-04-01", tz="UTC")


def test_grid_mpya_ni_superset_ya_ya_awali(cfg):
    """Cells 25 za awali lazima zibaki ndani ya 49 — hakuna ushahidi unaopotea.

    `research/data/` haipushwi (G11), kwa hiyo labels za awali zipo kwenye disk
    ya PD pekee, na `build-labels` inaziandika juu. Kama grid mpya ingekuwa
    imebadilisha thamani badala ya kuziongeza, matokeo ya T2/T3 yasingeweza
    kuthibitishwa tena.

    Kwa sababu ni superset, cell `2.0/3.0` inarudi — na inakuwa **ukaguzi wa
    regression**: `EV net` yake ikitofautiana na +0.0039 iliyorekodiwa, kitu
    kimeharibika kwenye ujenzi, si kwenye nadharia.
    """
    sl = [float(x) for x in cfg.get("labels.barrier.sl_atr")]
    tp = [float(x) for x in cfg.get("labels.barrier.tp_atr")]

    awali_sl = {0.5, 0.75, 1.0, 1.5, 2.0}
    awali_tp = {0.5, 1.0, 1.5, 2.0, 3.0}
    assert awali_sl <= set(sl), f"sl zilizopotea: {awali_sl - set(sl)}"
    assert awali_tp <= set(tp), f"tp zilizopotea: {awali_tp - set(tp)}"
    assert 2.0 in sl and 3.0 in tp, "cell iliyosainiwa 2.0/3.0 lazima ibaki"
    # Grid iliyopanuliwa PEKEE — mpangilio unaopanda, bila kurudia.
    assert sl == sorted(set(sl)) and tp == sorted(set(tp))
