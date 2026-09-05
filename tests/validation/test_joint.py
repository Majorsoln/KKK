"""Lango la pamoja — DOCTRINE §9.9.

Kasoro iliyosababisha moduli hii ni ya aina hatari zaidi: **kila sehemu ilikuwa
sahihi, mkusanyiko haukuwa.** Kila sakafu ilikuwa `p95` halali ya metric yake;
kudai zote kwa wakati mmoja kulizalisha lango lenye kosa la aina-I chini ya
0.7%, na hakuna namba yoyote kwenye faili iliyoonyesha hilo.

Kwa hiyo dai kuu la majaribio haya si "code inaendesha" bali **kiwango cha null
kinachopita ni kile kilichotangazwa**.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.validation import joint as JT

BORA = JT.BETTER
MBAYA = "worse"


def _rows(rng, n=50, metrics=("a", "b", "c"), rho=0.0, shift=0.0):
    """Replicates `n`, kila moja na metrics zenye uhusiano `rho`."""
    out = []
    for _ in range(n):
        pamoja = rng.normal()
        out.append({
            m: shift + rho * pamoja + math.sqrt(1 - rho ** 2) * rng.normal()
            for m in metrics
        })
    return out


def _familia(rng, **kw):
    return {f"fam{i}": _rows(rng, **kw) for i in range(3)}


# ===========================================================================
# `u_stat`
# ===========================================================================


def test_u_ni_fungu_la_null_zinazozidiwa():
    ref = [1.0, 2.0, 3.0, 4.0]
    # 2.5 inazidi 1.0 na 2.0 → k=2, n=4 → 3/5
    assert JT.u_stat(2.5, ref, BORA) == pytest.approx(3 / 5)


def test_u_ya_juu_kabisa_ni_MOJA():
    """Halisi na null lazima zifikie kikomo kilekile — vinginevyo lango ni
    rahisi kwa halisi kwa sababu ya hesabu, si ya soko."""
    ref = [1.0, 2.0, 3.0]
    assert JT.u_stat(99.0, ref, BORA) == pytest.approx(1.0)


def test_u_inageuka_kwa_metric_ambayo_NDOGO_ni_bora():
    ref = [10.0, 20.0, 30.0, 40.0]
    assert JT.u_stat(15.0, ref, MBAYA) == pytest.approx(4 / 5)   # inazidi 20,30,40
    assert JT.u_stat(35.0, ref, MBAYA) == pytest.approx(2 / 5)   # inazidi 40 pekee


def test_sawa_HAIHESABIWI_kama_kuzidi():
    """Sheria ile ile ya `FloorEntry.passes`: kuvuka ni kuzidi, si kufikia."""
    assert JT.u_stat(2.0, [1.0, 2.0, 3.0], BORA) == pytest.approx(2 / 4)


@pytest.mark.parametrize("mbaya", [float("nan"), float("inf"), None, "x"])
def test_thamani_isiyohesabika_ni_SIFURI_si_kurukwa(mbaya):
    """§1.1 — kutokuwepo kwa kipimo si ushahidi wa kupita."""
    assert JT.u_stat(mbaya, [1.0, 2.0, 3.0], BORA) == 0.0


def test_marejeo_matupu_yanalipuka():
    with pytest.raises(JT.JointError):
        JT.u_stat(1.0, [], BORA)


# ===========================================================================
# `T = min(u)` — si wastani
# ===========================================================================


def test_T_ni_mwelekeo_DHAIFU_zaidi():
    rng = np.random.default_rng(1)
    gate = JT.calibrate_joint(_familia(rng), {"a": BORA, "b": BORA, "c": BORA})
    u = gate.u({"a": 99.0, "b": 99.0, "c": -99.0})
    assert gate.t({"a": 99.0, "b": 99.0, "c": -99.0}) == pytest.approx(min(u.values()))


def test_ubora_mkubwa_HAULIPII_udhaifu():
    """Ndicho §9.2 inachokataa, na `min` inakikataa vilevile."""
    rng = np.random.default_rng(2)
    gate = JT.calibrate_joint(_familia(rng), {"a": BORA, "b": BORA, "c": BORA})
    bora_kwa_wote = {"a": 5.0, "b": 5.0, "c": 5.0}
    mmoja_dhaifu = {"a": 500.0, "b": 500.0, "c": -5.0}
    assert gate.passes(bora_kwa_wote)
    assert not gate.passes(mmoja_dhaifu)


def test_metric_ISIYOKUWEPO_inaanguka():
    rng = np.random.default_rng(3)
    gate = JT.calibrate_joint(_familia(rng), {"a": BORA, "b": BORA, "c": BORA})
    assert not gate.passes({"a": 99.0, "b": 99.0})
    assert "c" in gate.failed({"a": 99.0, "b": 99.0})


def test_failed_inaorodhesha_dhaifu_KWANZA():
    rng = np.random.default_rng(4)
    gate = JT.calibrate_joint(_familia(rng), {"a": BORA, "b": BORA, "c": BORA})
    kutofaulu = gate.failed({"a": -99.0, "b": 0.0, "c": -50.0})
    assert kutofaulu[0] == "a"


def test_failed_tupu_ni_sawa_na_passes():
    rng = np.random.default_rng(5)
    gate = JT.calibrate_joint(_familia(rng), {"a": BORA, "b": BORA})
    for x in (-5.0, 0.0, 0.5, 5.0):
        v = {"a": x, "b": x}
        assert gate.passes(v) == (not gate.failed(v))
        assert gate.passes(v) == (gate.t(v) > gate.floor)


# ===========================================================================
# Ukalibrishaji — ndilo dai zima
# ===========================================================================


@pytest.mark.parametrize("seed", range(20, 32))
@pytest.mark.parametrize("shift", [0.0, 1.0, 3.0])
def test_kiwango_kinabaki_ndani_ya_masafa_yaliyotangazwa(seed, shift):
    """Dai la moduli: `[5%/3, 5%]`, si namba moja.

    `shift` ni tofauti ya ugumu kati ya familia — ndicho kigezo pekee
    kinachoamua kiasi ambacho `max` ya §9.2 inaongeza. `0.0` ni familia
    zinazofanana, `3.0` ni moja ngumu kupita zote.

    Hata kwa `shift=0.0` kiwango hakifikii 5%: `max` ya makadirio MATATU ya
    `p95`, kila moja kutoka pointi 50, iko juu ya `p95` halisi kwa sababu ya
    kelele ya sampuli pekee. Kwa hiyo masafa yanaegemea upande wa chini — na
    hiyo ni upande salama.
    """
    rng = np.random.default_rng(seed)
    fam = {
        "a": _rows(rng, n=50, metrics=tuple("abcd")),
        "b": _rows(rng, n=50, metrics=tuple("abcd"), shift=shift / 2),
        "c": _rows(rng, n=50, metrics=tuple("abcd"), shift=shift),
    }
    gate = JT.calibrate_joint(fam, {m: BORA for m in "abcd"})
    assert 0.005 <= gate.null_pass_rate <= 0.060, gate.null_pass_rate


def test_kiwango_HAKIPUNGUI_metrics_zikiongezeka():
    """Ndiyo kasoro yenyewe: mkusanyiko wa sakafu ulipungua kwa kila metric
    iliyoongezwa, mpaka sifuri. `T` haifanyi hivyo."""
    viwango = []
    for k in (2, 4, 6):
        metrics = tuple("abcdef"[:k])
        gate = JT.calibrate_joint(
            _familia(np.random.default_rng(100 + k), n=50, metrics=metrics),
            {m: BORA for m in metrics},
        )
        viwango.append(gate.null_pass_rate)
    assert min(viwango) > 0.010, viwango
    assert max(viwango) <= 0.060, viwango


def test_MKUSANYIKO_wa_sakafu_ndio_uliokuwa_na_kasoro():
    """Ushahidi wa kasoro yenyewe, ndani ya jaribio: p95 kwa kila metric peke
    yake, zote kwa pamoja, zinapitisha ~0 wakati metrics ni huru."""
    rng = np.random.default_rng(13)
    fam = _familia(rng, n=50, metrics=tuple("abcde"))
    zote = [r for rows in fam.values() for r in rows]

    sakafu = {
        m: max(float(np.quantile([r[m] for r in rows], 0.95))
               for rows in fam.values())
        for m in "abcde"
    }
    walipita = sum(1 for r in zote if all(r[m] > sakafu[m] for m in "abcde"))
    assert walipita == 0

    gate = JT.calibrate_joint(fam, {m: BORA for m in "abcde"})
    assert gate.null_pass_rate > 0.005


def test_uhusiano_mkubwa_HAUBADILISHI_kiwango():
    """Kwa mkusanyiko wa sakafu, kiwango kilitegemea uhusiano kati ya metrics —
    kigezo ambacho hakuna anayekijua wala kukitangaza. `T` haikitegemei."""
    huru = JT.calibrate_joint(
        _familia(np.random.default_rng(21), n=50, metrics=tuple("abcd"), rho=0.0),
        {m: BORA for m in "abcd"})
    fungamano = JT.calibrate_joint(
        _familia(np.random.default_rng(22), n=50, metrics=tuple("abcd"), rho=0.98),
        {m: BORA for m in "abcd"})
    assert abs(huru.null_pass_rate - fungamano.null_pass_rate) < 0.03


def test_familia_NGUMU_zaidi_ndiyo_inayofunga():
    """R15 — sakafu inatoka kwa familia ngumu zaidi, si wastani wao."""
    rng = np.random.default_rng(31)
    fam = {
        "rahisi": _rows(rng, n=50, metrics=("a", "b"), shift=-3.0),
        "kati": _rows(rng, n=50, metrics=("a", "b"), shift=0.0),
        "ngumu": _rows(rng, n=50, metrics=("a", "b"), shift=3.0),
    }
    gate = JT.calibrate_joint(fam, {"a": BORA, "b": BORA})
    assert gate.floor == pytest.approx(max(gate.by_family.values()))
    assert max(gate.by_family, key=lambda k: gate.by_family[k]) == "ngumu"


def test_mwelekeo_wa_metric_unaheshimiwa_kwenye_ukalibrishaji():
    """`max_drawdown` ndogo ni bora. Ikichukuliwa vibaya, replicates bora
    zingeonekana mbaya na sakafu ingegeuka kimya."""
    rng = np.random.default_rng(41)
    fam = {f"fam{i}": [{"dd": float(x)} for x in rng.uniform(0, 100, 50)]
           for i in range(3)}
    gate = JT.calibrate_joint(fam, {"dd": MBAYA})
    assert gate.u({"dd": 0.0})["dd"] > gate.u({"dd": 99.0})["dd"]
    assert gate.passes({"dd": -1.0})
    assert not gate.passes({"dd": 200.0})


def test_replicate_zenye_metric_isiyohesabika_zinahesabiwa():
    rng = np.random.default_rng(51)
    fam = _familia(rng, n=50, metrics=("a", "b"))
    fam["fam0"][0]["a"] = float("inf")
    fam["fam0"][1]["a"] = float("nan")
    gate = JT.calibrate_joint(fam, {"a": BORA, "b": BORA})
    assert gate.n_incomplete == 2
    # Hazikuingia kwenye marejeo, lakini zilihesabiwa kwenye `n_null`.
    assert len(gate.reference["a"]) == 148
    assert gate.n_null == 150


def test_bila_metric_hakuna_lango():
    with pytest.raises(JT.JointError):
        JT.calibrate_joint({"fam0": [{"a": 1.0}]}, {})


def test_bila_replicate_hakuna_lango():
    with pytest.raises(JT.JointError):
        JT.calibrate_joint({"fam0": []}, {"a": BORA})


def test_metric_isiyo_na_thamani_halali_hata_moja_inalipuka():
    fam = {f"fam{i}": [{"a": float("nan")} for _ in range(50)] for i in range(3)}
    with pytest.raises(JT.JointError, match="`a`"):
        JT.calibrate_joint(fam, {"a": BORA})


# ===========================================================================
# JSON
# ===========================================================================


def test_json_inarudisha_UAMUZI_ule_ule():
    rng = np.random.default_rng(61)
    gate = JT.calibrate_joint(_familia(rng, metrics=("a", "dd")),
                              {"a": BORA, "dd": MBAYA})
    rudi = JT.JointGate.from_json(gate.to_json())

    assert rudi.floor == pytest.approx(gate.floor)
    assert rudi.null_pass_rate == pytest.approx(gate.null_pass_rate)
    for x in (-2.0, 0.0, 1.0, 2.0, 5.0):
        v = {"a": x, "dd": -x}
        assert rudi.passes(v) == gate.passes(v)
        assert rudi.t(v) == pytest.approx(gate.t(v))


def test_json_inashika_MWELEKEO():
    """Mwelekeo uliopotea wakati wa kusoma faili ungegeuza lango kimya."""
    rng = np.random.default_rng(62)
    gate = JT.calibrate_joint(_familia(rng, metrics=("dd",)), {"dd": MBAYA})
    assert JT.JointGate.from_json(gate.to_json()).higher_is == {"dd": MBAYA}


def test_kiwango_cha_nje_ya_masafa_kinatangazwa():
    """Ripoti isiyosema kuwa hesabu imeharibika ni ripoti inayoonekana halali."""
    rng = np.random.default_rng(71)
    gate = JT.calibrate_joint(_familia(rng, metrics=("a", "b")),
                              {"a": BORA, "b": BORA})
    assert gate.ndani_ya_masafa
    assert "KOSA" not in gate.render()

    import dataclasses

    mbovu = dataclasses.replace(gate, null_pass_rate=0.42)
    assert not mbovu.ndani_ya_masafa
    assert "KOSA" in mbovu.render()

    sifuri = dataclasses.replace(gate, null_pass_rate=0.0)
    assert not sifuri.ndani_ya_masafa
