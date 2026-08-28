"""Calibration B — DOCTRINE §9, R4, R5, R6, R15.

Sakafu isiyo sahihi haitoi kosa. Inapitisha au inakataa kila kitu kilichokuja
baada yake, kimya, kwa miezi. Kwa hiyo tests hizi zinalinda njia nne ambazo
sakafu inaweza kuwa si sakafu:

* sakafu MOJA ikitumika kwa vipimo vyote — vipimo tofauti, mgawanyo tofauti
* metric isiyo na sakafu ikitumika kama lango — hukumu bila kipimo
* sakafu ya candidate MMOJA — tatizo la §9.1 ni tabia ya `max` ya `K`
* `max` ikichukuliwa upande usio sahihi kwa metric ambayo `ndogo ni bora`
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from src.validation import noise_floor as NF
from src.validation import surrogates as SG

N = 800
REPS = NF.MIN_REPLICATES


def _ticks(n=N, seed=7):
    r = np.random.default_rng(seed).normal(0, 3e-4, n - 1)
    mid = 1.10 * np.exp(np.cumsum(np.concatenate([[0.0], r])))
    return pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=n, freq="1min", tz="UTC"),
        "bid": mid - 0.6e-4,
        "ask": mid + 0.6e-4,
    })


def _pipeline(values: dict[str, float] | None = None, *, variants: int = 500,
              noise: float = 0.0, seed: int = 0):
    """Pipeline bandia inayorudisha metrics za candidate 'bora'."""
    base = {"net_pips_month": 10.0, "sharpe": 0.8, "max_drawdown": 200.0,
            "fill_rate": 0.9, "profit_factor": 1.2,
            "profitable_month_fraction": 0.6, "net_account_return_month": 0.01}
    base.update(values or {})
    rng = np.random.default_rng(seed)

    def run(frame):
        out = {k: v + (rng.normal(0, noise) if noise else 0.0) for k, v in base.items()}
        out[NF.VARIANTS_KEY] = variants
        return out

    return run


def _floor(**kw) -> NF.NoiseFloor:
    kw.setdefault("n_replicates", REPS)
    kw.setdefault("seed", 1)
    kw.setdefault("progress", None)
    run = kw.pop("run", None) or _pipeline()
    return NF.calibrate(_ticks(), run, **kw)


# ===========================================================================
# Sakafu ni JEDWALI, si namba
# ===========================================================================


def test_kila_metric_ina_sakafu_yake():
    table = _floor(run=_pipeline(noise=0.5, seed=3))
    assert set(table.entries) == {m.name for m in NF.DEFAULT_METRICS}
    assert table.entries["sharpe"].floor != table.entries["net_pips_month"].floor


def test_metric_isiyo_na_sakafu_HAIWEZI_kuwa_lango():
    """§1.1 — kurudisha True ingekuwa kupitisha bila kipimo; False, kukataa bila kipimo."""
    table = _floor()
    with pytest.raises(NF.NoFloorError, match="expectancy"):
        table.gate("expectancy", 99.0)
    with pytest.raises(NF.NoFloorError):
        table.floor("expectancy")


def test_metric_isiyoripotiwa_inaishia_BILA_sakafu():
    run = _pipeline()

    def bila_sharpe(frame):
        out = run(frame)
        out.pop("sharpe")
        return out

    table = _floor(run=bila_sharpe)
    assert "sharpe" not in table
    assert "sharpe" in table.without_floor
    with pytest.raises(NF.NoFloorError):
        table.gate("sharpe", 5.0)


def test_metric_ya_ziada_inarekodiwa_haitupwi_kimya():
    run = _pipeline()

    def na_ziada(frame):
        out = run(frame)
        out["expectancy_R"] = 0.05
        return out

    table = _floor(run=na_ziada)
    assert "expectancy_R" in table.without_floor


# ===========================================================================
# Upande wa sakafu
# ===========================================================================


def test_kuvuka_ni_KUZIDI_si_kufikia():
    table = _floor()
    floor = table.floor("net_pips_month")
    assert not table.gate("net_pips_month", floor)
    assert table.gate("net_pips_month", floor + 1e-9)


def test_metric_ambayo_NDOGO_ni_bora_inatumia_p5():
    table = _floor(run=_pipeline(noise=20.0, seed=4))
    dd = table.entries["max_drawdown"]
    assert dd.tail == NF.P_LOW
    assert table.gate("max_drawdown", dd.floor - 1.0)
    assert not table.gate("max_drawdown", dd.floor + 1.0)


def test_max_inachukuliwa_upande_SAHIHI_kwa_kila_metric():
    """R15: inayotumika ni **ngumu zaidi**, si `max` ya kiufundi.

    Kwa `max_drawdown` (ndogo ni bora) ngumu zaidi ni p5 **ndogo** kuliko zote.
    Kuchukua `max` hapo kungechukua sakafu RAHISI kuliko zote — kinyume kabisa
    cha sheria, na hakuna kinachoonyesha kosa hilo isipokuwa candidates dhaifu
    zikianza kupita.
    """
    table = _floor(run=_pipeline(noise=15.0, seed=5))

    juu = table.entries["net_pips_month"]
    assert juu.floor == pytest.approx(max(juu.by_family.values()))

    chini = table.entries["max_drawdown"]
    assert chini.floor == pytest.approx(min(chini.by_family.values()))
    assert chini.binding_family == min(chini.by_family, key=chini.by_family.get)


def test_thamani_ya_nan_haipiti():
    table = _floor()
    assert not table.gate("sharpe", float("nan"))


# ===========================================================================
# `variants_tested` — R6 / S1
# ===========================================================================


def test_pipeline_isiyotangaza_variants_inalipuka():
    def kimya(frame):
        return {"net_pips_month": 10.0}

    with pytest.raises(NF.CalibrationError, match="variants_tested"):
        _floor(run=kimya)


def test_variants_MMOJA_haikubaliki():
    """Sakafu ya candidate mmoja ni sakafu ya swali ambalo hakuna aliyeuliza."""
    with pytest.raises(NF.CalibrationError, match="max"):
        _floor(run=_pipeline(variants=1))


def test_variants_zinaingia_kwenye_ripoti():
    table = _floor(run=_pipeline(variants=1234))
    assert table.variants_tested_min == 1234
    assert "1,234" in table.render()


def test_pipeline_isiyorudisha_mapping_inalipuka():
    with pytest.raises(NF.CalibrationError, match="mapping"):
        _floor(run=lambda frame: [1, 2, 3])


# ===========================================================================
# Replicates na familia
# ===========================================================================


def test_replicates_chache_zinakataliwa():
    """`p95` ya pointi 20 ni thamani ya pili kwa ukubwa — jina lake ni percentile."""
    with pytest.raises(NF.CalibrationError, match="replicates"):
        _floor(n_replicates=NF.MIN_REPLICATES - 1)


def test_familia_moja_haitoshi():
    """R15 — sakafu ya familia moja ni nusu soko, nusu generator, na hazitofautishwi."""
    with pytest.raises(NF.CalibrationError, match="R15"):
        _floor(families=(SG.BLOCK,))


def test_familia_isiyojulikana_inakataliwa():
    with pytest.raises(NF.CalibrationError, match="hazijulikani"):
        _floor(families=(SG.BLOCK, SG.REGIME, "bootstrap"))


def test_familia_zote_tatu_zinaendeshwa():
    zilizoonekana = []

    def run(frame):
        zilizoonekana.append(len(frame))
        return {NF.VARIANTS_KEY: 100, "sharpe": 0.5}

    table = _floor(run=run)
    assert len(zilizoonekana) == 3 * REPS
    assert set(table.families) == set(SG.FAMILIES)
    assert set(table.entries["sharpe"].by_family) == set(SG.FAMILIES)


# ===========================================================================
# Kuzalisha upya na ushahidi
# ===========================================================================


def test_seed_ile_ile_inatoa_sakafu_ILE_ILE():
    a = _floor(run=_pipeline(noise=2.0, seed=0), seed=42)
    b = _floor(run=_pipeline(noise=2.0, seed=0), seed=42)
    assert a.entries["net_pips_month"].floor == b.entries["net_pips_month"].floor


def test_seed_inatofautisha_replicates_ndani_ya_familia():
    seeds = {NF._seed_of(1, SG.BLOCK, r) for r in range(20)}
    assert len(seeds) == 20
    assert NF._seed_of(1, SG.BLOCK, 0) != NF._seed_of(1, SG.REGIME, 0)


def test_ushahidi_una_TAREHE_na_unasomeka(tmp_path):
    """R5 — Calibration B inahifadhiwa kama ushahidi wenye tarehe."""
    table = _floor(run=_pipeline(noise=1.0, seed=6), source="EURUSD H1 2016-2024")
    path = table.write(tmp_path / "noise_floor.json")

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["created_at"].startswith("20") and raw["source"] == "EURUSD H1 2016-2024"

    rudi = NF.NoiseFloor.read(path)
    assert rudi.entries["sharpe"].floor == table.entries["sharpe"].floor
    assert rudi.gate("sharpe", 99.0) and not rudi.gate("sharpe", -99.0)


def test_ripoti_inaonyesha_familia_iliyofunga_sakafu():
    table = _floor(run=_pipeline(noise=3.0, seed=7))
    text = table.render()
    for fam in SG.FAMILIES:
        assert fam[:5] in text
    assert "variants_tested" in text


def test_ci_inaandikwa_pamoja_na_sakafu():
    """Sakafu ina kutokuwa na uhakika; kunaandikwa badala ya kunyamaziwa."""
    e = _floor(run=_pipeline(noise=5.0, seed=8)).entries["net_pips_month"]
    assert e.ci_low <= e.ci_high
    assert e.uncertainty >= 0


def test_ci_ni_ya_familia_ILIYOFUNGA_sakafu():
    """CI ya pooled ingeeleza namba isiyotumika — na sakafu ingetua nje yake."""
    for e in _floor(run=_pipeline(noise=8.0, seed=9)).entries.values():
        assert e.ci_low <= e.floor <= e.ci_high, f"{e.metric} ipo nje ya CI yake"


def test_progress_inachapisha_kila_replicate():
    """R23 — hakuna kinachoendeshwa kimya."""
    lines: list[str] = []
    _floor(progress=lines.append)
    hatua = [line for line in lines if line.strip().startswith(SG.BLOCK)]
    assert len(hatua) == REPS
    assert f"{REPS}/{REPS}" in hatua[-1]


# ===========================================================================
# R5 — generator haifunguki bila ushahidi
# ===========================================================================


def test_generator_haifunguki_bila_calibration_A(tmp_path):
    b = _floor().write(tmp_path / "noise_floor.json")
    with pytest.raises(NF.CalibrationError, match="Calibration A"):
        NF.guard_generator(noise_floor_path=b, cost_calibration_path=tmp_path / "hakuna.json")


def test_generator_haifunguki_bila_calibration_B(tmp_path):
    a = tmp_path / "cost.json"
    a.write_text("{}", encoding="utf-8")
    with pytest.raises(NF.CalibrationError, match="Calibration B"):
        NF.guard_generator(
            noise_floor_path=tmp_path / "hakuna.json", cost_calibration_path=a
        )


def test_generator_inafunguka_ushahidi_ukiwepo(tmp_path):
    a = tmp_path / "cost.json"
    a.write_text("{}", encoding="utf-8")
    b = _floor().write(tmp_path / "noise_floor.json")
    table = NF.guard_generator(noise_floor_path=b, cost_calibration_path=a)
    assert table.entries


def test_jedwali_tupu_halifungui_generator(tmp_path):
    a = tmp_path / "cost.json"
    a.write_text("{}", encoding="utf-8")
    b = tmp_path / "noise_floor.json"
    tupu = _floor()
    payload = tupu.to_json()
    payload["entries"] = {}
    b.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(NF.CalibrationError, match="sakafu hata moja"):
        NF.guard_generator(noise_floor_path=b, cost_calibration_path=a)


# ===========================================================================
# Mikataba midogo
# ===========================================================================


def test_higher_is_lazima_iwe_mojawapo():
    with pytest.raises(NF.CalibrationError, match="higher_is"):
        NF.MetricSpec("x", "kubwa")


# ===========================================================================
# `inf` si "kubwa" — ni "haihesabiki" (Calibration B ya kwanza, 2026-08-26)
# ===========================================================================


def _na_inf(mara, kila: int):
    """Pipeline inayotoa `inf` kila run ya `kila` — kama mgombea asiye na hasara."""
    def pipeline(_sur):
        mara["n"] += 1
        pf = float("inf") if kila and mara["n"] % kila == 0 else 2.0 + mara["n"] % 3
        return {"profit_factor": pf, "sharpe": 1.0, NF.VARIANTS_KEY: 20}
    return pipeline


def test_inf_HAICHAFUI_sakafu_za_metrics_nyingine():
    """Kabla ya marekebisho, `inf` moja iligeuza sakafu YOTE ya metric kuwa NaN.

    `np.quantile` inafanya interpolation, na `inf − inf` ni `NaN`. Lango la
    `> NaN` halipitiki kamwe wala halionyeshi kwa nini — run ya kwanza ya
    Calibration B ilipoteza lango zima la `profit_factor` hivyo.
    """
    jedwali = _floor(run=_na_inf({"n": 0}, 4))
    assert math.isfinite(jedwali.entries["sharpe"].floor)
    assert "profit_factor" not in jedwali.entries


def test_metric_yenye_inf_inaishia_BILA_sakafu_si_na_sakafu_ya_uongo():
    """§1.1 — bora metric ikose lango kuliko iwe na lango lisilo na maana."""
    jedwali = _floor(run=_na_inf({"n": 0}, 4))
    assert "profit_factor" in jedwali.without_floor
    with pytest.raises(NF.NoFloorError):
        jedwali.gate("profit_factor", 99.0)


def test_bila_inf_sakafu_inapatikana_kama_kawaida():
    jedwali = _floor(run=_na_inf({"n": 0}, 0))
    assert math.isfinite(jedwali.entries["profit_factor"].floor)


def test_ni_namba_inakataa_NaN_na_inf():
    assert NF._ni_namba(1.5) and NF._ni_namba(0)
    assert not NF._ni_namba(float("inf"))
    assert not NF._ni_namba(float("-inf"))
    assert not NF._ni_namba(float("nan"))
    assert not NF._ni_namba(None) and not NF._ni_namba("x")
