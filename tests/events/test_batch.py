"""Proposals za wakati mmoja — DOCTRINE §11, R12.

Mshauri alitabiri kwamba jaribio linalochanganya mpangilio wa kuwasili
litafeli. Alikuwa sahihi, na sababu ni ya wazi: `evaluate_gate` inaangalia
`open_positions` **za sasa**. Ya kwanza kufika inachukua nafasi.

Jaribio la kwanza hapa chini linaonyesha kasoro **bila** mpangilio uliotangazwa.
Lililobaki linathibitisha kwamba `panga()` inaiondoa — bila kugusa RCE.
"""

from __future__ import annotations

import random

import pytest

from src.events import batch as B
from src.rce.gate import evaluate_gate


def _p(symbol, strength=1.0, family="F1", side="BUY", sl=20.0):
    return B.Proposal(symbol=symbol, side=side, strength=strength,
                      family=family, sl_pips=sl)


def _ctx():
    return {"current_balance": 10_000.0, "today_loss": 0.0, "spread_pips": 1.0}


def _bila_mpangilio(proposals, cfg, context):
    """Jinsi ambavyo ingefanyika bila `panga()` — kwa mpangilio wa kuingia."""
    from src.rce.gate import GateContext

    wazi, kubali = [], []
    for p in proposals:
        u = evaluate_gate(cfg, GateContext(symbol=p.symbol,
                                           open_positions=len(wazi),
                                           open_symbols=tuple(wazi), **context))
        if u.passed:
            wazi.append(p.symbol)
            kubali.append(p.symbol)
    return kubali


# ===========================================================================
# Kasoro yenyewe
# ===========================================================================


def test_BILA_mpangilio_matokeo_yanategemea_KUWASILI(cfg_risk):
    """Ushahidi wa kasoro, ndani ya jaribio.

    `max_correlated = 3` na `USD_group` ina EURUSD, GBPUSD, AUDUSD, NZDUSD.
    Nne zikifika, moja inakataliwa — na ipi inategemea mpangilio pekee.
    """
    kundi = [_p("EURUSD"), _p("GBPUSD"), _p("AUDUSD"), _p("NZDUSD")]
    a = _bila_mpangilio(kundi, cfg_risk, _ctx())
    b = _bila_mpangilio(list(reversed(kundi)), cfg_risk, _ctx())

    assert len(a) == len(b) == 3
    assert set(a) != set(b), "kasoro haijaonekana — jaribio halipimi kitu"


# ===========================================================================
# Suluhisho: mpangilio uliotangazwa
# ===========================================================================


def test_mpangilio_uliotangazwa_unaondoa_utegemezi(cfg_risk):
    """Dai kuu: kundi lilelile, mpangilio wowote, jibu lile lile."""
    kundi = [_p("EURUSD"), _p("GBPUSD"), _p("AUDUSD"), _p("NZDUSD"),
             _p("USDJPY"), _p("USDCHF")]
    rng = random.Random(7)

    kwanza = None
    for _ in range(30):
        changanya = kundi[:]
        rng.shuffle(changanya)
        matokeo = B.admit(changanya, gate=evaluate_gate, cfg=cfg_risk,
                          context=_ctx())
        alama = [(a.proposal.symbol, a.accepted, a.reason) for a in matokeo]
        if kwanza is None:
            kwanza = alama
        assert alama == kwanza


def test_nguvu_ya_ishara_inaamua_nafasi_zikiwa_chache(cfg_risk):
    """Uamuzi wa kiuchumi uliotangazwa: bora kwanza, si aliyefika kwanza."""
    kundi = [_p("NZDUSD", strength=0.9), _p("EURUSD", strength=0.2),
             _p("AUDUSD", strength=0.8), _p("GBPUSD", strength=0.1)]
    walipita = [p.symbol for p in
                B.waliokubaliwa(B.admit(kundi, gate=evaluate_gate,
                                        cfg=cfg_risk, context=_ctx()))]
    assert walipita[:2] == ["NZDUSD", "AUDUSD"]
    assert "GBPUSD" not in walipita          # dhaifu kuliko zote


def test_sare_inavunjwa_kwa_HERUFI_kisha_familia(cfg_risk):
    """F0 ina `strength = 1.0` kwa wote — sare lazima ivunjwe kwa uhakika."""
    kundi = [_p("USDJPY", family="B"), _p("EURUSD", family="B"),
             _p("EURUSD", family="A")]
    assert [(p.symbol, p.family) for p in B.panga(kundi)] == [
        ("EURUSD", "A"), ("EURUSD", "B"), ("USDJPY", "B")]


def test_panga_HAIBADILISHI_orodha_iliyoingizwa(cfg_risk):
    kundi = [_p("USDJPY"), _p("EURUSD")]
    B.panga(kundi)
    assert [p.symbol for p in kundi] == ["USDJPY", "EURUSD"]


def test_kundi_tupu_linarudisha_tupu(cfg_risk):
    assert B.admit([], gate=evaluate_gate, cfg=cfg_risk, context=_ctx()) == []


def test_positions_ZILIZOFUNGULIWA_tayari_zinahesabika(cfg_risk):
    """`USD_group` ikiwa na mbili tayari, moja tu mpya inapita."""
    kundi = [_p("EURUSD"), _p("GBPUSD")]
    matokeo = B.admit(kundi, gate=evaluate_gate, cfg=cfg_risk,
                      open_symbols=("AUDUSD", "NZDUSD"), context=_ctx())
    assert sum(a.accepted for a in matokeo) == 1


def test_sababu_ya_kukataa_inaandikwa(cfg_risk):
    kundi = [_p(s) for s in ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD")]
    matokeo = B.admit(kundi, gate=evaluate_gate, cfg=cfg_risk, context=_ctx())
    zilizokataliwa = [a for a in matokeo if not a.accepted]
    assert len(zilizokataliwa) == 1
    assert "max_correlated" in zilizokataliwa[0].reason


# ===========================================================================
# Ulinzi wa `Proposal`
# ===========================================================================


@pytest.mark.parametrize("mbaya", [-0.1, 1.1, 2.0])
def test_strength_nje_ya_masafa_inalipuka(mbaya):
    with pytest.raises(B.BatchError, match="strength"):
        _p("EURUSD", strength=mbaya)


@pytest.mark.parametrize("mbaya", [0.0, -5.0])
def test_sl_pips_isiyo_chanya_inalipuka(mbaya):
    """RCE inaigawanya — lots haziwezi kupatikana bila stop (§5)."""
    with pytest.raises(B.BatchError, match="sl_pips"):
        _p("EURUSD", sl=mbaya)
