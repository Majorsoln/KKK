"""Backtest Engine — DOCTRINE §11, §1.2, R12, R17, R19.

Kipimo muhimu zaidi hapa ni **§1.2**: seti ile ile ya trades inatoa pesa tofauti
kutegemea mpangilio, kwa sababu RCE inasizisha kwa hali ya akaunti ya wakati
huo. Engine isiyoonyesha hilo ingekuwa inahesabu `net_account_return_month`
ambayo haiwezi kutokea.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest import engine as B
from src.backtest.ledger import FILL, PASS
from src.rce.cost import SymbolSpec
from src.rce.gate import REJECT_MAX_CORRELATED, REJECT_MAX_OPEN
from src.strategies.dna import ATR_MULT, FIXED_PIPS, Condition, ConditionSet, Strategy

PIP = 0.0001
T0 = pd.Timestamp("2020-06-01 00:00", tz="UTC")

SPEC = SymbolSpec(symbol="EURUSD", point=0.00001, contract_size=100_000,
                  volume_min=0.01, volume_step=0.01, volume_max=50.0)


def _broker(**kw) -> B.BrokerFacts:
    base = dict(spec=SPEC, pip_value_acct=10.0, commission_round_turn=7.0)
    base.update(kw)
    return B.BrokerFacts(**base)


def _ticks(mids, *, spread_pips=1.0, freq="1min"):
    mids = np.asarray(mids, dtype=float)
    half = spread_pips * PIP / 2.0
    return pd.DataFrame({
        "timestamp": pd.date_range(T0, periods=len(mids), freq=freq, tz="UTC"),
        "bid": mids - half, "ask": mids + half,
    })


def _features(n, *, waka, atr_pips=20.0, freq="1h", spread_pips=1.0):
    """Features za bandia: `waka` ni orodha ya bool kwa kila bar.

    `spread_p50`/`spread_p95` si mapambo: engine inakataa kuendesha bila spread
    (§2 — hakuna namba ya kubuni inayoingia kwa RCE), na thamani hapa inalingana
    na `_ticks(spread_pips=1.0)`.
    """
    index = pd.date_range(T0, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {"SIGNAL": np.where(np.asarray(waka, dtype=bool), 1.0, 0.0),
         "ATR_pips": float(atr_pips),
         "spread_p50": float(spread_pips),
         "spread_p95": float(spread_pips)},
        index=index,
    )


def _strategy(**kw) -> Strategy:
    base = dict(
        symbol="EURUSD", direction="BUY",
        entry=ConditionSet((Condition("SIGNAL", ">", 0.5),)),
        sl_type=FIXED_PIPS, sl_param=20.0,
        tp_type=FIXED_PIPS, tp_param=40.0,
        time_stop_bars=2,
    )
    base.update(kw)
    return Strategy(**base)


SLOT = 120          # dakika kwa kila trade — bars 2, sawa na `time_stop_bars`


def _mfululizo(matokeo: list[float]):
    """Bei inayotoa TP au SL kwa mpangilio ulioombwa.

    `+1` = TP (+45 pips), `−1` = SL (−25 pips). Mwendo unafanyika **taratibu**
    kwa dakika 10, si kwa tick moja: mruko wa ghafla kwenye tick ya kujaza
    ungezidi `deviation` na kutoa `NO_FILL`, na hapo test ingekuwa inapima
    slippage badala ya mpangilio.

    Kila trade ina nafasi yake ya dakika 120, kwa hiyo hazipishani na kila moja
    ina muda wa kufika mwisho ndani ya `time_stop`.

    Dakika 60 za mwanzo ni kabla ya signal ya kwanza: bar 0 inaishia dakika ya
    60 (R11 — uamuzi ni MWISHO wa bar), kwa hiyo nafasi ya trade `k` inaanza
    dakika `60 + 120k`.
    """
    njia = [1.10000] * 60                                   # kabla ya signal ya kwanza
    mid = 1.10000
    for tokeo in matokeo:
        lengo = mid + (45 if tokeo > 0 else -25) * PIP
        njia += [mid] * 5                                   # tulivu wakati wa kujaza
        njia += list(np.linspace(mid, lengo, 10))           # mwendo taratibu
        njia += [lengo] * (SLOT - 15)
        mid = lengo
    njia += [mid] * SLOT                                    # nafasi ya kufika mwisho
    return njia


# ===========================================================================
# §1.2 — pesa inategemea MPANGILIO, pips hazitegemei
# ===========================================================================


def _endesha(mpangilio, cfg_risk, *, balance=10_000.0):
    n = len(mpangilio)
    mids = _mfululizo(mpangilio)
    ticks = _ticks(mids)
    bars = (len(mids) // 60) + 1
    waka = [(i % 2 == 0) and (i // 2) < n for i in range(bars)]
    feats = _features(bars, waka=waka)
    return B.run(_strategy(), feats, ticks, cfg_risk=cfg_risk, broker=_broker(),
                 timeframe="H1", starting_balance=balance)


def test_pips_HAZITEGEMEI_mpangilio(cfg_risk):
    """Seti ile ile ya matokeo inatoa pips zile zile, mpangilio wowote."""
    kwanza = _endesha([-1, -1, -1, 1, 1], cfg_risk)
    pili = _endesha([1, 1, -1, -1, -1], cfg_risk)

    assert kwanza.n_trades == pili.n_trades == 5
    assert kwanza.total_pips == pytest.approx(pili.total_pips, abs=1e-6)


def test_pesa_INATEGEMEA_mpangilio(cfg_risk):
    """Ndicho kiini cha §1.2, na sababu ya engine kuwa ya mfuatano.

    Hasara zikija kwanza, DD inakula budget, lots zinapungua, na faida
    inayofuata inakuja kwa ukubwa mdogo. Faida zikija kwanza, kinyume chake.
    """
    hasara_kwanza = _endesha([-1, -1, -1, 1, 1], cfg_risk)
    faida_kwanza = _endesha([1, 1, -1, -1, -1], cfg_risk)

    assert hasara_kwanza.total_account != pytest.approx(
        faida_kwanza.total_account, abs=1e-6
    ), "pesa haitegemei mpangilio — RCE haisizishi kwa hali ya akaunti"
    assert faida_kwanza.total_account > hasara_kwanza.total_account


def test_lots_zinapungua_baada_ya_hasara(cfg_risk):
    """`DD ↑ → budget ↓ → risk_per_trade ↓ → lots ↓`."""
    out = _endesha([-1, -1, -1, -1], cfg_risk)
    lots = [t.lots for t in out.trades]
    assert lots[-1] < lots[0], f"lots hazikupungua: {lots}"


def test_path_dependence_inaonekana_kwenye_vipimo(cfg_risk):
    out = _endesha([1, -1], cfg_risk)
    assert "path_dependence" in out.metrics()


# ===========================================================================
# R19 — hatua mbili
# ===========================================================================


def test_signal_iliyokataliwa_na_RCE_haifiki_utekelezaji(cfg_risk):
    """Bajeti ikiisha, signal inaandikwa lakini haiendi kwenye path ya ticks."""
    out = _endesha([-1, -1, -1], cfg_risk, balance=9_150.0)
    mgawanyo = out.ledger.by_outcome()
    assert out.ledger.n_signals > out.ledger.n_approved
    assert any(k != FILL for k in mgawanyo)


def test_kila_signal_ina_row_kwenye_ledger(cfg_risk):
    out = _endesha([1, 1, 1], cfg_risk)
    assert sum(out.ledger.by_outcome().values()) == out.ledger.n_signals
    assert out.ledger.n_signals > 0


def test_max_open_inaamuliwa_na_RCE_si_na_engine(cfg_risk):
    """Signals nyingi zinazopishana — RCE ndiyo inayosimamisha (R12).

    Sheria ipi kati ya `max_open_trades` na `max_correlated` inawaka kwanza ni
    ya RCE, si yangu: hapa zote ni EURUSD, kwa hiyo `max_correlated` ya kundi la
    USD inafika kwanza. Kudai jina moja mahususi kungekuwa kunakili mpangilio wa
    ndani wa RCE kwenye test ya engine — na hilo ndilo R12 inalokataza.
    """
    mids = [1.10000] * (60 * 40)
    feats = _features(30, waka=[True] * 30, atr_pips=20.0)
    out = B.run(_strategy(time_stop_bars=20), feats, _ticks(mids),
                cfg_risk=cfg_risk, broker=_broker(), timeframe="H1")

    mgawanyo = out.ledger.by_outcome()
    zilizosimamishwa = [k for k in mgawanyo
                        if k == REJECT_MAX_OPEN or k.startswith(REJECT_MAX_CORRELATED)]
    assert zilizosimamishwa, f"hakuna signal iliyosimamishwa kwa kupishana: {mgawanyo}"
    assert sum(mgawanyo[k] for k in zilizosimamishwa) > 0


def test_bila_spread_engine_INAKATAA_kuendesha(cfg_risk):
    """§2 — spread ya kubuni ni constant isiyopimwa, na madhara hayaonekani.

    RCE ingehesabu gharama ndogo kuliko halisi, lots zingekuwa kubwa kuliko
    zinazoruhusiwa, na `net_account_return_month` ingekuwa ya soko lisilokuwepo.
    Hakuna metric ingesema kwa nini — kwa hiyo lazima ilipuke hapa.
    """
    feats = _features(6, waka=[True] + [False] * 5).drop(
        columns=["spread_p50", "spread_p95"])
    with pytest.raises(B.BacktestError, match="spread_p50"):
        B.run(_strategy(), feats, _ticks(_mfululizo([1])), cfg_risk=cfg_risk,
              broker=_broker(), timeframe="H1")


def test_spread_ya_RCE_ni_ya_DIRISHA_si_ya_run_nzima(cfg_risk):
    """Spread ikipanda katikati, gharama ya RCE lazima ipande nayo.

    Orodha moja isiyobadilika ingefanya `max_spread` isiwake kamwe na gharama
    isiwe na uhusiano na soko.
    """
    feats = _features(12, waka=[i % 2 == 0 for i in range(12)])
    feats.iloc[6:, feats.columns.get_loc("spread_p50")] = 8.0
    feats.iloc[6:, feats.columns.get_loc("spread_p95")] = 8.0

    out = B.run(_strategy(), feats, _ticks(_mfululizo([1] * 6)),
                cfg_risk=cfg_risk, broker=_broker(), timeframe="H1")
    gharama = [a.cost_pips for a in out.ledger.attempts]
    assert gharama[-1] > gharama[0], f"gharama haikubadilika na spread: {gharama}"


# ===========================================================================
# Equity na mpangilio wa kufungwa
# ===========================================================================


def test_equity_inapangwa_kwa_muda_wa_KUFUNGWA(cfg_risk):
    out = _endesha([1, -1, 1], cfg_risk)
    nyakati = list(out.equity().index)
    assert nyakati == sorted(nyakati)


def test_balance_ya_mwisho_ni_mwanzo_pamoja_na_faida(cfg_risk):
    out = _endesha([1, -1, 1], cfg_risk)
    assert out.trades[-1].balance_after == pytest.approx(
        out.starting_balance + out.total_account, abs=1e-6
    )


def test_max_drawdown_ni_chanya_na_inatoka_kwenye_kilele(cfg_risk):
    out = _endesha([1, -1, -1, -1], cfg_risk)
    dd = out.max_drawdown()
    assert dd > 0
    eq = np.concatenate([[out.starting_balance],
                         out.equity().to_numpy(dtype=float)])
    assert dd == pytest.approx((np.maximum.accumulate(eq) - eq).max())


# ===========================================================================
# Vipimo vya mwezi (R8)
# ===========================================================================


def test_monthly_inajumlisha_trades_zote(cfg_risk):
    out = _endesha([1, -1, 1, -1], cfg_risk)
    kwa_mwezi = out.monthly()
    assert kwa_mwezi["n_trades"].sum() == out.n_trades
    assert kwa_mwezi["net_pips"].sum() == pytest.approx(out.total_pips, abs=1e-6)


def test_bila_trades_vipimo_ni_nan_si_sifuri(cfg_risk):
    """`0/0` si `0.0`. Kipimo kisichoweza kuhesabiwa hakidanganyi."""
    import math

    feats = _features(10, waka=[False] * 10)
    out = B.run(_strategy(), feats, _ticks([1.10] * 600), cfg_risk=cfg_risk,
                broker=_broker(), timeframe="H1")
    m = out.metrics()
    assert out.n_trades == 0
    assert math.isnan(m["net_pips_month"]) and math.isnan(m["sharpe"])


def test_metrics_zina_PRIMARY_mbili_za_1_2(cfg_risk):
    m = _endesha([1, -1], cfg_risk).metrics()
    assert "net_pips_month" in m and "net_account_return_month" in m


# ===========================================================================
# SL/TP kwa ATR na `rr`
# ===========================================================================


def test_atr_mult_inatumia_ATR_ya_bar_husika(cfg_risk):
    feats = _features(6, waka=[True] + [False] * 5, atr_pips=30.0)
    out = B.run(_strategy(sl_type=ATR_MULT, sl_param=2.0, tp_type=ATR_MULT,
                          tp_param=4.0),
                feats, _ticks(_mfululizo([1])), cfg_risk=cfg_risk,
                broker=_broker(), timeframe="H1")
    assert out.ledger.n_signals == 1
    # SL = 2 × 30 = 60 pips; TP = 4 × 30 = 120.
    assert out.ledger.attempts[0].rce_outcome in (PASS, "max_spread")


def test_ATR_isiyojulikana_haitoi_trade(cfg_risk):
    """Bar ya warmup haina ATR — hakuna SL, kwa hiyo hakuna trade."""
    feats = _features(4, waka=[True] * 4)
    feats["ATR_pips"] = np.nan
    out = B.run(_strategy(sl_type=ATR_MULT, sl_param=1.5, tp_type=ATR_MULT,
                          tp_param=3.0),
                feats, _ticks([1.10] * 400), cfg_risk=cfg_risk,
                broker=_broker(), timeframe="H1")
    assert out.n_trades == 0 and out.ledger.n_signals == 0


def test_rr_inategemea_SL(cfg_risk):
    from src.backtest.engine import _kwa_pips

    sl = _kwa_pips("fixed_pips", 20.0, float("nan"), None)
    assert _kwa_pips("rr", 2.0, float("nan"), sl) == pytest.approx(40.0)


# ===========================================================================
# `_slice` ni ya kasi, si ya tabia
# ===========================================================================


def test_kukata_ticks_HAKUBADILISHI_matokeo(cfg_risk):
    """Bila kukata, kila trade ingetembea hadi mwisho: `O(n²)` kwa run nzima.

    Lakini kasi isiyo na gharama ya tabia ni sharti, si tumaini.
    """
    from src.backtest.execution import ExecSpec, execute

    mids = _mfululizo([1, -1, 1])
    ticks = _ticks(mids)
    stamps = pd.DatetimeIndex(pd.to_datetime(ticks["timestamp"], utc=True)).as_unit("ns")
    stamps_ns = stamps.view("int64")
    muda = stamps[100]

    spec = ExecSpec(symbol="EURUSD", direction="BUY", sl_pips=20.0, tp_pips=40.0,
                    deviation_pips=0.5, commission_pips=0.7, time_stop_minutes=120)
    kamili = execute(ticks, spec, signal_time=muda,
                     requested_price=float(ticks["ask"].iloc[100]))
    kipande = B._slice(ticks, stamps_ns, muda, spec.time_stop_minutes)
    fupi = execute(kipande, spec, signal_time=muda,
                   requested_price=float(ticks["ask"].iloc[100]))

    assert fupi.outcome == kamili.outcome
    assert fupi.exit_reason == kamili.exit_reason
    assert fupi.net_pips == pytest.approx(kamili.net_pips, abs=1e-9)


def test_time_stop_inapatikana_ndani_ya_kipande(cfg_risk):
    """Kipande kikikatwa kabla ya `deadline`, trade ingeonekana UNRESOLVED."""
    from src.backtest.execution import TIME_STOP, ExecSpec, execute

    ticks = _ticks([1.10000] * 600)
    stamps = pd.DatetimeIndex(pd.to_datetime(ticks["timestamp"], utc=True)).as_unit("ns")
    muda = stamps[10]
    spec = ExecSpec(symbol="EURUSD", direction="BUY", sl_pips=50.0, tp_pips=50.0,
                    deviation_pips=0.5, commission_pips=0.7, time_stop_minutes=60)

    kipande = B._slice(ticks, stamps.view("int64"), muda, 60)
    out = execute(kipande, spec, signal_time=muda,
                  requested_price=float(ticks["ask"].iloc[10]))
    assert out.exit_reason == TIME_STOP


# ===========================================================================
# Kuripoti
# ===========================================================================


def test_matokeo_yanajielezea(cfg_risk):
    out = _endesha([1, -1], cfg_risk)
    text = out.render()
    assert out.strategy_id in text and "pips/mwezi" in text
    assert out.to_json()["metrics"]["n_trades"] == out.n_trades
