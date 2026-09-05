"""Generator — DOCTRINE §10.3, §10.4, R5, R21.

Kasoro ya generator haijionyeshi kama kosa. Inajionyesha kama strategy nzuri
ambayo hakuna aliyeihesabu — kwa sababu `variants_tested` iliyopotoka
inashusha sakafu ya §9, na sakafu iliyoshuka inapitisha bahati.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.discovery import generator as G
from src.discovery.ledger import INVALID_CANDIDATE, VariantLedger
from src.strategies.dna import ATR_MULT, Condition, ConditionSet, Strategy
from src.validation.noise_floor import CalibrationError


def _spec(**kw) -> G.GeneratorSpec:
    base = dict(symbols=("EURUSD", "GBPUSD"), max_conditions=4)
    base.update(kw)
    return G.GeneratorSpec(**base)


def _rng(seed=0):
    return np.random.default_rng(seed)


def _strategy(n_entry=1, n_exit=0, **kw) -> Strategy:
    base = dict(
        symbol="EURUSD", direction="BUY",
        entry=ConditionSet(tuple(Condition("RSI_14", ">", 50.0 + i)
                                 for i in range(n_entry))),
        exit=ConditionSet(tuple(Condition("ADX_14", ">", 20.0 + i)
                                for i in range(n_exit))),
        sl_type=ATR_MULT, sl_param=1.5, tp_type=ATR_MULT, tp_param=3.0,
        time_stop_bars=24,
    )
    base.update(kw)
    return Strategy(**base)


# ===========================================================================
# R5 — mlango
# ===========================================================================


def test_generator_HAIFUNGUKI_bila_calibration(tmp_path):
    """Generator inayoendeshwa kabla ya sakafu inatoa 'ugunduzi' usiopimika."""
    with pytest.raises(CalibrationError, match="Calibration A"):
        G.open_generator(noise_floor_path=tmp_path / "b.json",
                         cost_calibration_path=tmp_path / "a.json")


def test_generator_inafunguka_ushahidi_ukiwepo(tmp_path):
    import json

    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({
        "families": ["block_resample", "regime_shuffle", "return_surrogate"],
        "n_replicates": 50, "variants_tested_min": 100, "variants_tested_median": 100.0,
        "entries": {"sharpe": {
            "metric": "sharpe", "higher_is": "better", "tail": 0.95, "floor": 1.2,
            "by_family": {"block_resample": 1.2}, "n_used": {"block_resample": 50},
            "ci_low": 1.0, "ci_high": 1.4,
        }},
    }), encoding="utf-8")

    sakafu = G.open_generator(noise_floor_path=tmp_path / "b.json",
                              cost_calibration_path=tmp_path / "a.json")
    assert sakafu.floor("sharpe") == pytest.approx(1.2)


# ===========================================================================
# §10.3 — mipaka ya utafutaji
# ===========================================================================


def test_max_conditions_juu_ya_KIKOMO_inakataliwa():
    """Strategy yenye masharti mengi inaweza kuonekana nzuri kwa kukariri."""
    with pytest.raises(G.GeneratorError, match="max_conditions"):
        _spec(max_conditions=G.MAX_CONDITIONS_KIKOMO + 1)


def test_kila_strategy_iliyozalishwa_ina_entry_NA_exit():
    for s in G.generate(_spec(), 200, seed=1):
        assert len(s.entry) >= 1
        assert s.time_stop_bars > 0 and s.sl_param > 0 and s.tp_param > 0


def test_hakuna_iliyozalishwa_inayovunja_max_conditions():
    spec = _spec(max_conditions=3)
    for s in G.generate(spec, 300, seed=2):
        assert s.complexity <= spec.max_conditions


def test_seed_ile_ile_inatoa_strategies_ZILE_ZILE():
    a = [s.variant_hash for s in G.generate(_spec(), 50, seed=7)]
    b = [s.variant_hash for s in G.generate(_spec(), 50, seed=7)]
    assert a == b


def test_seed_tofauti_inatoa_utafutaji_tofauti():
    a = {s.variant_hash for s in G.generate(_spec(), 50, seed=1)}
    b = {s.variant_hash for s in G.generate(_spec(), 50, seed=2)}
    assert len(a & b) < len(a) // 2


def test_maktaba_haina_percentile_isiyo_na_dirisha():
    """§5 — `dna` ingeikataa, lakini kuiweka hapa kunaifanya ionekane mapema."""
    for spec in G.MAKTABA:
        if "percentile" in spec.name.lower():
            assert spec.name.endswith("d"), spec.name


def test_maktaba_ina_familia_zote_za_10_3():
    majina = " ".join(s.name for s in G.MAKTABA)
    for familia in ("EMA", "RSI", "ADX", "ATR_percentile", "return_", "dist_from"):
        assert familia in majina, familia


# ===========================================================================
# R21 — invariant baada ya KILA mutation
# ===========================================================================


def test_recombine_INAWEZA_kuvunja_kikomo_na_haifichi():
    """Mzazi 4 + mzazi 4 = mtoto 8. Function haizuii; `spawn` ndiyo inayokagua.

    Kuficha ukiukaji ndani ya `recombine` kungefanya R21 isiweze kupimwa.
    """
    a = _strategy(n_entry=4, n_exit=0)
    b = _strategy(n_entry=1, n_exit=4)
    mtoto = G.recombine(a, b, _rng())
    assert mtoto.complexity == 8
    assert not G.valid(mtoto, _spec(max_conditions=4))


def test_mtoto_asiye_halali_ni_INVALID_na_haendi_kwenye_data():
    spawner = G.Spawner(spec=_spec(max_conditions=4), ledger=VariantLedger())
    mbaya = G.recombine(_strategy(n_entry=4), _strategy(n_entry=1, n_exit=4), _rng())

    assert spawner.spawn(mbaya) is None
    assert spawner.ledger.n_generated == 1
    assert spawner.ledger.variants_tested == 0
    assert spawner.ledger.n_invalid == 1


def test_mtoto_halali_anapita():
    spawner = G.Spawner(spec=_spec(max_conditions=4))
    assert spawner.spawn(_strategy(n_entry=2)) is not None
    assert spawner.ledger.n_invalid == 0


def test_kizazi_kizima_kinaheshimu_R21():
    spec = _spec(max_conditions=4)
    spawner = G.Spawner(spec=spec)
    walionusurika = [s for s in G.generate(spec, 12, seed=3)]
    watoto = spawner.next_generation(walionusurika, n=200, rng=_rng(5))

    assert all(c.complexity <= spec.max_conditions for c in watoto)
    # Wote — halali na si halali — wameandikwa.
    assert spawner.ledger.n_generated == 200
    assert spawner.ledger.variants_tested == 0
    assert len(watoto) + spawner.ledger.n_invalid + spawner.ledger.n_duplicate == 200


def test_mutation_inabadilisha_KIPANDE_kimoja():
    mzazi = _strategy(n_entry=3, n_exit=1)
    rng = _rng(11)
    watoto = [G.mutate(mzazi, _spec(), rng) for _ in range(50)]

    for mtoto in watoto:
        assert mtoto.generation == mzazi.generation + 1
        assert mtoto.parent_ids == (mzazi.strategy_id,)
        assert mtoto.symbol == mzazi.symbol
    assert sum(c.variant_hash != mzazi.variant_hash for c in watoto) > 40


def test_mutation_inayotua_kwenye_MZAZI_inaandikwa_kama_DUPLICATE():
    """Nasibu inaweza kuchagua thamani ile ile — `sl_param` 1.5 tena, mf.

    Kulazimisha mabadiliko kungebadilisha mgawanyo wa utafutaji: kuondoa
    'hakuna mabadiliko' kunafanya mutation isiwe nasibu tena. Njia sahihi ni
    kuiruhusu na kuiandika — na hapo `variants_tested` haiipandi, kwa sababu
    hakuna kilichopimwa kipya.
    """
    spawner = G.Spawner(spec=_spec())
    mzazi = _strategy(n_entry=2)
    spawner.spawn(mzazi)

    pacha = _strategy(n_entry=2, generation=1, parent_ids=(mzazi.strategy_id,))
    assert pacha.variant_hash == mzazi.variant_hash
    assert spawner.spawn(pacha) is None
    assert spawner.ledger.n_duplicate == 1
    assert spawner.ledger.variants_tested == 0


def test_recombine_ya_symbols_tofauti_inalipuka():
    with pytest.raises(G.GeneratorError, match="symbols tofauti"):
        G.recombine(_strategy(symbol="EURUSD"), _strategy(symbol="GBPUSD"), _rng())


def test_kizazi_bila_walionusurika_ni_tupu():
    assert G.Spawner(spec=_spec()).next_generation([], n=10, rng=_rng()) == []


# ===========================================================================
# Ukoo unabaki kwenye ushahidi
# ===========================================================================


def test_ukoo_wa_mtoto_unaandikwa_kwenye_ledger():
    spawner = G.Spawner(spec=_spec())
    mzazi = _strategy(n_entry=2)
    mtoto = G.mutate(mzazi, spawner.spec, _rng(2))
    spawner.spawn(mtoto)

    rec = spawner.ledger.records[0]
    assert rec.generation == 1 and rec.parent_ids == (mzazi.strategy_id,)
