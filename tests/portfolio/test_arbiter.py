"""Uamuzi wa portfolio — DOCTRINE §6, R12.

Kipimo cha 2026-09-07 kilionyesha kwamba kupanga **legs** kwa nguvu ya ishara
kunaondoa utegemezi wa mpangilio wa kuwasili lakini kunazalisha kitu kibaya
zaidi: leg dhaifu kuliko zote inakataliwa 99/99, na kikapu kinachopimwa
kinajilimbikizia ishara kali kuliko kilichotangazwa.

Majaribio haya yanathibitisha kwamba kitengo cha uamuzi ni **kikapu**, na
kwamba matokeo hayategemei mpangilio wa kuwasili wala hayavunji kikapu.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.portfolio import arbiter as A
from src.portfolio import basket as BK
from src.portfolio import regime as R
from src.rce.gate import evaluate_gate

UTC = ZoneInfo("UTC")
T0 = datetime(2021, 6, 15, 14, 0, tzinfo=UTC)

F1_LEGS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF")


def _leg(sym, w=1.0, sl=20.0):
    return BK.Leg(symbol=sym, side="BUY" if w > 0 else "SELL",
                  sl_pips=sl, weight=w)


def _basket(family, symbols, *, priority=1, atomic=True, weights=None,
            regimes=(R.NORMAL,), bid=None, dakika=75):
    w = weights or [1.0] * len(symbols)
    return BK.Basket(
        family=family, basket_id=bid or f"{family}:2021-06-15",
        legs=tuple(_leg(s, x) for s, x in zip(symbols, w)),
        entry_at=T0, planned_exit_at=T0 + timedelta(minutes=dakika),
        priority=priority, atomic=atomic, eligible_regimes=regimes)


def _ctx():
    return {"current_balance": 10_000.0, "today_loss": 0.0, "spread_pips": 1.0}


def _run(baskets, cfg, **kw):
    return A.arbitrate(baskets, gate=evaluate_gate, cfg=cfg, context=_ctx(), **kw)


# ===========================================================================
# Yote-au-hakuna
# ===========================================================================


def test_kikapu_KIZIMA_kinasimama_leg_moja_ikikataliwa(cfg_risk):
    """Dai kuu. `USD_group` ina kikomo 3; kikapu chenye wanne kinasimama."""
    k = _basket("X", ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"))
    out = _run([k], cfg_risk)
    assert out.admitted == []
    v = out.verdicts[0]
    assert v.reason.startswith(A.REJECT_ATOMIC)
    assert "max_correlated" in v.reason
    assert v.failing_symbol == "NZDUSD"


def test_F1_yenye_legs_sita_inapita_nzima(cfg_risk):
    """USD_group: EURUSD, GBPUSD, AUDUSD = 3 hasa. USD_strength: 3 hasa."""
    out = _run([_basket("F1", F1_LEGS)], cfg_risk)
    assert len(out.admitted) == 1
    assert sorted(out.symbols) == sorted(F1_LEGS)


def test_hakuna_leg_inayokatwa_kwa_NGUVU(cfg_risk):
    """Kasoro iliyosababisha safu hii: leg dhaifu ikikatwa 99/99.

    Nguvu tofauti sana, lakini kikapu kinapita **kizima** au hakipiti kabisa —
    hakuna leg inayoachwa nyuma.
    """
    dhaifu = [0.9, 0.05, 0.8, 0.02, 0.7, 0.01]
    out = _run([_basket("F1", F1_LEGS, weights=dhaifu)], cfg_risk)
    assert len(out.admitted) == 1
    assert len(out.admitted[0].legs) == 6           # zote, si tano


def test_kikapu_kisicho_atomiki_kinaruhusu_sehemu(cfg_risk):
    """Lazima kitangazwe waziwazi — chaguo-msingi ni atomiki."""
    k = _basket("X", ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"), atomic=False)
    out = _run([k], cfg_risk)
    assert len(out.admitted) == 1
    assert out.verdicts[0].reason.startswith("partial")


# ===========================================================================
# Mpangilio wa kuwasili hauna athari
# ===========================================================================


def test_matokeo_HAYATEGEMEI_mpangilio_wa_kuwasili(cfg_risk):
    vikapu = [
        _basket("F1", F1_LEGS, priority=1),
        _basket("F0", ("EURUSD",), priority=2, bid="F0:A"),
        _basket("G", ("USDJPY",), priority=3, bid="G:1"),
    ]
    rng = random.Random(3)
    kwanza = None
    for _ in range(30):
        changanya = vikapu[:]
        rng.shuffle(changanya)
        out = _run(changanya, cfg_risk)
        alama = [(v.basket.basket_id, v.admitted, v.reason) for v in out.verdicts]
        if kwanza is None:
            kwanza = alama
        assert alama == kwanza


def test_kipaumbele_kinaamua_nani_anapata_nafasi(cfg_risk):
    """F1 (matukio 99) iko juu ya F0 (matukio 4,302) — nafasi yake
    haiwezi kubadilishwa, ya F0 inaweza."""
    kubwa = _basket("F1", ("EURUSD", "GBPUSD", "AUDUSD"), priority=1)
    ndogo = _basket("F0", ("NZDUSD",), priority=2, bid="F0:A")
    out = _run([ndogo, kubwa], cfg_risk)
    assert [v.basket.family for v in out.verdicts] == ["F1", "F0"]
    assert out.verdicts[0].admitted
    assert not out.verdicts[1].admitted      # USD_group imejaa


# ===========================================================================
# Regime
# ===========================================================================


def test_familia_isiyostahili_leo_HAIENDESHWI(cfg_risk):
    f0 = _basket("F0", ("EURUSD",), regimes=(R.NORMAL,))
    out = _run([f0], cfg_risk, regime=R.MONTH_END_FIX)
    assert out.admitted == []
    assert out.verdicts[0].reason == A.REJECT_REGIME


def test_F1_inaendeshwa_siku_ya_mwisho_wa_mwezi(cfg_risk):
    f1 = _basket("F1", F1_LEGS, regimes=(R.MONTH_END_FIX,))
    out = _run([f1], cfg_risk, regime=R.MONTH_END_FIX)
    assert len(out.admitted) == 1


def test_siku_ya_F1_F0_inasimama_na_F1_inapata_legs_ZOTE(cfg_risk):
    """Mfano halisi wa 2016-06-30 — sababu nzima ya kutengana."""
    f1 = _basket("F1", F1_LEGS, priority=1, regimes=(R.MONTH_END_FIX,))
    f0 = _basket("F0", ("EURUSD",), priority=2, regimes=(R.NORMAL,), bid="F0:A")
    out = _run([f1, f0], cfg_risk, regime=R.MONTH_END_FIX)

    assert len(out.admitted) == 1
    assert len(out.admitted[0].legs) == 6
    assert out.verdicts[1].reason == A.REJECT_REGIME
    assert out.symbols.count("EURUSD") == 1        # si mara mbili


# ===========================================================================
# Marudio ya symbol
# ===========================================================================


def test_symbol_iliyoshikwa_tayari_inasimamisha_kikapu(cfg_risk):
    """Netting haijajengwa; kufungua symbol ileile mara mbili ni kuhesabu
    hatari moja mara mbili."""
    out = _run([_basket("F0", ("EURUSD",))], cfg_risk, open_symbols=("EURUSD",))
    assert out.admitted == []
    assert out.verdicts[0].reason == A.REJECT_DUPLICATE


def test_symbol_iliyorudiwa_NDANI_ya_kikapu_inalipuka():
    with pytest.raises(BK.BasketError, match="imerudiwa"):
        _basket("X", ("EURUSD", "EURUSD"))


# ===========================================================================
# Hash ya portfolio
# ===========================================================================


def test_hash_inabadilika_KIPAUMBELE_kikibadilika():
    """Kubadilisha kipaumbele ni kubadilisha strategy inayopimwa."""
    a = BK.portfolio_hash([_basket("F1", F1_LEGS, priority=1)], regime=R.NORMAL)
    b = BK.portfolio_hash([_basket("F1", F1_LEGS, priority=2)], regime=R.NORMAL)
    assert a != b


def test_hash_inabadilika_ATOMIKI_ikibadilika():
    a = BK.portfolio_hash([_basket("F1", F1_LEGS, atomic=True)], regime=R.NORMAL)
    b = BK.portfolio_hash([_basket("F1", F1_LEGS, atomic=False)], regime=R.NORMAL)
    assert a != b


def test_hash_HAITEGEMEI_mpangilio_wa_kuingiza():
    x = _basket("F1", F1_LEGS, priority=1)
    y = _basket("F0", ("EURUSD",), priority=2, bid="F0:A")
    assert (BK.portfolio_hash([x, y], regime=R.NORMAL)
            == BK.portfolio_hash([y, x], regime=R.NORMAL))


def test_hash_inabadilika_REGIME_ikibadilika():
    k = [_basket("F1", F1_LEGS)]
    assert (BK.portfolio_hash(k, regime=R.NORMAL)
            != BK.portfolio_hash(k, regime=R.MONTH_END_FIX))


# ===========================================================================
# Kutoka kwa saa, na positions zilizobaki
# ===========================================================================


def test_planned_exit_ya_LAZIMA_na_ya_mbeleni():
    with pytest.raises(BK.BasketError, match="planned_exit_at"):
        BK.Basket(family="X", basket_id="x", legs=(_leg("EURUSD"),),
                  entry_at=T0, planned_exit_at=T0, priority=1)


def test_position_iliyopita_saa_yake_ni_STALE():
    class P:
        def __init__(self, t): self.planned_exit_at = t

    hai = P(T0 + timedelta(hours=1))
    imebaki = P(T0 - timedelta(hours=1))
    assert BK.stale([hai, imebaki], T0) == [imebaki]
    assert BK.stale([hai], T0) == []


def test_backtest_haipaswi_kuwa_na_STALE_hata_moja():
    """§4.1 — kutoka ni kwa saa. Kwenye backtest hii ni tupu DAIMA."""
    class P:
        def __init__(self, t): self.planned_exit_at = t

    zilizofungwa = [P(T0 + timedelta(minutes=m)) for m in (30, 60, 75)]
    assert BK.stale(zilizofungwa, T0 + timedelta(minutes=29)) == []


# ===========================================================================
# Ulinzi wa `Leg` na `Basket`
# ===========================================================================


@pytest.mark.parametrize("mbaya", [0.0, -5.0])
def test_sl_pips_isiyo_chanya_inalipuka(mbaya):
    with pytest.raises(BK.BasketError, match="sl_pips"):
        _leg("EURUSD", sl=mbaya)


@pytest.mark.parametrize("mbaya", [0.0, 1.5, -2.0])
def test_weight_nje_ya_masafa_inalipuka(mbaya):
    with pytest.raises(BK.BasketError, match="weight"):
        _leg("EURUSD", w=mbaya)


def test_kikapu_kisicho_na_leg_kinalipuka():
    with pytest.raises(BK.BasketError, match="leg hata moja"):
        BK.Basket(family="X", basket_id="x", legs=(), entry_at=T0,
                  planned_exit_at=T0 + timedelta(minutes=1), priority=1)


def test_regime_isiyotangazwa_inalipuka():
    with pytest.raises(BK.BasketError, match="hazijulikani"):
        _basket("X", ("EURUSD",), regimes=("MSIMU_WA_MVUA",))


def test_net_weight_ya_kikapu_kilichosawazishwa_ni_karibu_sifuri():
    """Inaripotiwa, si kudhaniwa — §18 ya ushauri."""
    k = _basket("F1", F1_LEGS, weights=[0.5, -0.3, 0.2, -0.4, 0.1, -0.1])
    assert abs(k.net_weight) < 1e-9
    assert k.gross_weight == pytest.approx(1.6)
