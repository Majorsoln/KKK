"""Lango la sakafu — DOCTRINE §9.2, §9.3, §1.1.

Lango lisilo sahihi halitoi kosa. Linapitisha au kukataa kimya, na §13 inajaa
au inabaki tupu bila sababu inayoonekana.
"""

from __future__ import annotations

import pytest

from src.discovery import survivors as SV
from src.validation.noise_floor import BETTER, WORSE, FloorEntry, NoiseFloor


def _floor(**zilizowekwa) -> NoiseFloor:
    base = {
        "net_account_return_month": (BETTER, 0.0224),
        "sharpe": (BETTER, 3.3817),
        "max_drawdown": (WORSE, 549.4842),
    }
    base.update(zilizowekwa)
    entries = {
        jina: FloorEntry(
            metric=jina, higher_is=upande,
            tail=0.95 if upande == BETTER else 0.05, floor=thamani,
            by_family={"block_resample": thamani}, n_used={"block_resample": 50},
            ci_low=thamani * 0.9, ci_high=thamani * 1.1,
        )
        for jina, (upande, thamani) in base.items()
    }
    return NoiseFloor(entries=entries,
                      families=("block_resample", "regime_shuffle", "return_surrogate"),
                      n_replicates=50, variants_tested_min=1000,
                      variants_tested_median=1000.0, without_floor=("fill_rate",))


def _metrics(**kw):
    base = {"net_account_return_month": 0.05, "sharpe": 4.0,
            "max_drawdown": 400.0, "fill_rate": 0.97}
    base.update(kw)
    return base


# ===========================================================================
# Kupita ni kuvuka MALANGO YOTE
# ===========================================================================


def test_anayevuka_yote_ananusurika():
    v = SV.screen("c1", "h1", _metrics(), _floor())
    assert v.passed and v.failed == ()


def test_kuanguka_lango_MOJA_kunatosha():
    """Malango sita si alama sita zinazoweza kuchanganywa.

    Sharpe kubwa mno haiwezi kulipia drawdown mbaya: sakafu mbili zilipimwa
    KANDO, kila moja kwa ncha yake, na kuzichanganya kungeunda kipimo cha saba
    kisichowahi kupimwa.
    """
    v = SV.screen("c1", "h1", _metrics(sharpe=99.0, max_drawdown=900.0), _floor())
    assert not v.passed and v.failed == ("max_drawdown",)


def test_zilizoanguka_ZOTE_zinaandikwa_si_ya_kwanza_pekee():
    v = SV.screen("c1", "h1",
                  _metrics(sharpe=1.0, max_drawdown=900.0,
                           net_account_return_month=0.001), _floor())
    assert set(v.failed) == {"sharpe", "max_drawdown", "net_account_return_month"}


def test_thamani_zinahifadhiwa_pamoja_na_uamuzi():
    """Swali 'kwa nini hakuna anayepita?' halipaswi kudai run nyingine."""
    v = SV.screen("c1", "h1", _metrics(sharpe=1.5), _floor())
    assert v.values["sharpe"] == pytest.approx(1.5)
    assert "sharpe" in v.render(_floor()) and "3.3817" in v.render(_floor())


def test_metric_ISIYOPO_ni_kuanguka_si_kuruka():
    """Kutokuwepo kwa kipimo si ushahidi wa kupita (§1.1)."""
    bila_sharpe = {k: v for k, v in _metrics().items() if k != "sharpe"}
    v = SV.screen("c1", "h1", bila_sharpe, _floor())
    assert "sharpe" in v.failed


def test_NaN_haipiti():
    v = SV.screen("c1", "h1", _metrics(sharpe=float("nan")), _floor())
    assert "sharpe" in v.failed


def test_kuvuka_ni_KUZIDI_si_kufikia():
    v = SV.screen("c1", "h1", _metrics(sharpe=3.3817), _floor())
    assert "sharpe" in v.failed


# ===========================================================================
# Diagnostic haihukumu (§1.1)
# ===========================================================================


def test_fill_rate_inaripotiwa_lakini_HAIHUKUMU():
    v = SV.screen("c1", "h1", _metrics(fill_rate=0.10), _floor())
    assert v.passed, "metric isiyo na sakafu imehukumu"
    assert v.diagnostics["fill_rate"] == pytest.approx(0.10)


# ===========================================================================
# Screening — muhtasari wa run nzima
# ===========================================================================


def _screening() -> SV.Screening:
    s = SV.Screening()
    s.add(SV.screen("a", "ha", _metrics(sharpe=1.0), _floor()))
    s.add(SV.screen("b", "hb", _metrics(max_drawdown=900.0), _floor()))
    s.add(SV.screen("c", "hc", _metrics(sharpe=1.0, max_drawdown=900.0), _floor()))
    return s


def test_lango_lililokata_zaidi_linaonekana():
    """Ndilo swali la kwanza pale hakuna anayepita."""
    kata = _screening().by_failed_metric()
    assert kata == {"max_drawdown": 2, "sharpe": 2}


def test_jumla_ya_kukataa_inaweza_kuzidi_idadi_ya_waliopimwa():
    """Mgombea mmoja anaweza kuanguka kwa malango kadhaa — si kosa."""
    s = _screening()
    assert sum(s.by_failed_metric().values()) > s.n_screened


def test_walionusurika_wanahesabiwa_kando():
    s = _screening()
    assert s.n_screened == 3 and len(s.survivors) == 0


def test_ripoti_inaonyesha_dai_la_kila_lango():
    text = _screening().render(_floor())
    assert "max_drawdown" in text and "549.4842" in text


def test_json_ina_kila_uamuzi_si_walionusurika_pekee():
    out = _screening().to_json()
    assert out["n_screened"] == 3 and len(out["verdicts"]) == 3
    assert out["n_survivors"] == 0


# ===========================================================================
# §9.9 — lango la pamoja linapokuwepo, ndilo linaloamua
# ===========================================================================


def _floor_ya_pamoja(rho: float = 0.0) -> NoiseFloor:
    """Jedwali kamili: sakafu za kila metric NA lango la pamoja, kutoka safu."""
    import math

    import numpy as np

    from src.validation import noise_floor as NF

    rng = np.random.default_rng(9)
    specs = (NF.MetricSpec("net_account_return_month", BETTER),
             NF.MetricSpec("sharpe", BETTER),
             NF.MetricSpec("max_drawdown", WORSE, lo=0.0))
    fams = ("block_resample", "regime_shuffle", "return_surrogate")

    rows = {}
    for f in fams:
        zake = []
        for _ in range(50):
            pamoja = rng.normal()
            def kelele():
                return rho * pamoja + math.sqrt(1 - rho ** 2) * rng.normal()
            zake.append({
                "net_account_return_month": 0.01 + 0.01 * kelele(),
                "sharpe": 1.0 + 0.5 * kelele(),
                "max_drawdown": 400.0 - 50.0 * kelele(),
                "fill_rate": 0.95,
                NF.VARIANTS_KEY: 1000,
            })
        rows[f] = zake

    return NF.floor_from_rows(
        rows, metrics=specs, families=fams, n_replicates=50,
        variants=[1000] * 150, seed=3, source="jaribio",
    )


def test_lango_la_pamoja_ndilo_linaloamua():
    floor = _floor_ya_pamoja()
    assert floor.joint is not None
    v = SV.screen("c1", "h1", _metrics(net_account_return_month=9.0,
                                       sharpe=9.0, max_drawdown=1.0), floor)
    assert v.passed and v.joint
    assert v.t == pytest.approx(1.0)
    assert v.t > v.joint_floor


def test_mwelekeo_MMOJA_dhaifu_unatosha_kukataa():
    """`min`, si wastani — ubora wa wengine haulipii."""
    floor = _floor_ya_pamoja()
    v = SV.screen("c1", "h1", _metrics(net_account_return_month=9.0,
                                       sharpe=9.0, max_drawdown=99_999.0), floor)
    assert not v.passed
    assert v.failed == ("max_drawdown",)


def test_kiwango_cha_null_kinacholingana_na_kilichotangazwa():
    """Dai zima la §9.9, likipimwa kupitia `screen()` yenyewe."""
    floor = _floor_ya_pamoja()
    ref = floor.joint.reference
    n = len(ref["sharpe"])
    walipita = sum(
        1 for i in range(n)
        if SV.screen(f"n{i}", "", {m: ref[m][i] for m in ref}, floor).passed
    )
    assert walipita / n == pytest.approx(floor.joint.null_pass_rate, abs=1.0 / n)
    assert walipita > 0


def test_mkusanyiko_wa_zamani_ungekataa_ZAIDI():
    """Ushahidi wa mwelekeo wa mabadiliko: §9.9 ni LEGEVU kuliko §9.2, na kwa
    kiasi kinachopimwa — si kubwa kiasi cha kufuta kipimo."""
    floor = _floor_ya_pamoja()
    ref = floor.joint.reference
    n = len(ref["sharpe"])
    safu = [{m: ref[m][i] for m in ref} for i in range(n)]

    pamoja = sum(1 for r in safu if SV.screen("x", "", r, floor).passed)
    zamani = sum(1 for r in safu
                 if all(floor.gate(m, r[m]) for m in floor.entries))
    assert zamani <= pamoja
    assert pamoja / n < 0.05


def test_jedwali_LISILO_na_lango_la_pamoja_linatumia_kanuni_ya_zamani():
    """Si kudhani — `Verdict.joint` inasema kanuni ipi ilitumika."""
    v = SV.screen("c1", "h1", _metrics(), _floor())
    assert v.passed and not v.joint
    assert v.u == {} and v.below_own_floor == ()


def test_aliyepita_pamoja_lakini_chini_ya_sakafu_yake_ANAANDIKWA():
    """Tofauti kati ya kanuni mbili haipaswi kupotea kimya."""
    floor = _floor_ya_pamoja()
    juu = max(floor.entries["sharpe"].floor, 0.0)
    m = _metrics(net_account_return_month=9.0, sharpe=juu, max_drawdown=1.0)
    v = SV.screen("c1", "h1", m, floor)
    if v.passed:
        # `sharpe` iko sawasawa na sakafu yake, kwa hiyo `passes()` inaikataa.
        assert "sharpe" in v.below_own_floor
        assert "chini ya sakafu yake" in v.render()


def test_ripoti_inasema_kanuni_iliyotumika():
    floor = _floor_ya_pamoja()
    s = SV.Screening()
    s.add(SV.screen("a", "ha", _metrics(sharpe=-9.0), floor))
    assert "§9.9" in s.render(floor)

    z = SV.Screening()
    z.add(SV.screen("a", "ha", _metrics(sharpe=1.0), _floor()))
    assert "§9.2" in z.render(_floor())
