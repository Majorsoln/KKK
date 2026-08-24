"""Strategy DNA — DOCTRINE §10.1, §10.2, §5.

Tests hizi zinalinda mambo ambayo, yakikosewa, yanapunguza `variants_tested`
bila mtu kugundua — na kila punguzo la `variants_tested` linashusha sakafu ya
§9, yaani linafanya bahati ionekane kama ugunduzi.
"""

from __future__ import annotations

import pytest

from src.strategies import dna as D


def _cond(feature="RSI_14", op=">", ref=70.0, negate=False) -> D.Condition:
    return D.Condition(feature=feature, op=op, ref=ref, negate=negate)


def _strategy(**kw) -> D.Strategy:
    base = dict(
        symbol="EURUSD", direction="BUY",
        entry=D.ConditionSet((_cond(),)),
        sl_type=D.ATR_MULT, sl_param=1.5,
        tp_type=D.ATR_MULT, tp_param=3.0,
        time_stop_bars=24,
    )
    base.update(kw)
    return D.Strategy(**base)


# ===========================================================================
# §10.1 — strategy ni entry NA exit
# ===========================================================================


def test_exit_ni_sehemu_ya_muundo_si_ya_hiari():
    """Dataclass inaidai. Bila hivyo, exit ingeweza kutafutwa baada ya matokeo."""
    with pytest.raises(TypeError):
        D.Strategy(symbol="EURUSD", direction="BUY",
                   entry=D.ConditionSet((_cond(),)))  # bila SL/TP/time_stop


def test_entry_ILE_ILE_na_exit_tofauti_ni_strategy_MBILI():
    """§10.1: zote mbili zinahesabiwa kwenye `variants_tested`."""
    a = _strategy(tp_param=3.0)
    b = _strategy(tp_param=2.0)
    assert a.variant_hash != b.variant_hash
    assert not D.strategies_ni_moja(a, b)


def test_time_stop_ni_lazima_na_chanya():
    with pytest.raises(D.DNAError, match="time_stop"):
        _strategy(time_stop_bars=0)


def test_entry_tupu_inakataliwa():
    """'Ingia daima' si strategy — ni kutokuwa na sheria."""
    with pytest.raises(D.DNAError, match="entry"):
        _strategy(entry=D.ConditionSet())


def test_exit_tupu_inaruhusiwa_kwa_sababu_SL_TP_zipo():
    s = _strategy(exit=D.ConditionSet())
    assert s.exit.tupu and s.complexity == 1
    assert "daima" in s.exit.render()


# ===========================================================================
# `variant_hash` — utambulisho
# ===========================================================================


def test_hash_haujali_MPANGILIO_wa_masharti():
    """`A AND B` na `B AND A` ni strategy ILE ILE.

    Zisipopewa hash moja, generator ingezalisha nakala, `variants_tested`
    ingepanda bila utafutaji kupanuka, na sakafu ingekuwa juu kwa sababu ya
    kuhesabu — si kwa sababu ya kutafuta.
    """
    a = _cond("RSI_14", ">", 70.0)
    b = _cond("ADX_14", ">", 25.0)
    assert _strategy(entry=D.ConditionSet((a, b))).variant_hash == \
           _strategy(entry=D.ConditionSet((b, a))).variant_hash


def test_hash_INAJALI_logic():
    a, b = _cond("RSI_14"), _cond("ADX_14", ">", 25.0)
    assert _strategy(entry=D.ConditionSet((a, b), logic=D.AND)).variant_hash != \
           _strategy(entry=D.ConditionSet((a, b), logic=D.OR)).variant_hash


def test_hash_INAJALI_negate():
    assert _strategy(entry=D.ConditionSet((_cond(negate=False),))).variant_hash != \
           _strategy(entry=D.ConditionSet((_cond(negate=True),))).variant_hash


def test_hash_HAUJALI_ukoo():
    """Strategy ile ile iliyofikiwa kwa njia mbili ni strategy ILE ILE.

    Kuipima mara mbili ni kuhesabu utafutaji ambao haukufanyika.
    """
    a = _strategy(generation=0, parent_ids=())
    b = _strategy(generation=3, parent_ids=("x", "y"))
    assert a.variant_hash == b.variant_hash


def test_symbols_tofauti_ni_strategies_tofauti():
    assert _strategy(symbol="EURUSD").variant_hash != _strategy(symbol="GBPUSD").variant_hash


def test_unique_inaondoa_nakala_ikihifadhi_mpangilio():
    a, b = _strategy(), _strategy(tp_param=2.0)
    assert [s.variant_hash for s in D.unique([a, b, a, b, a])] == \
           [a.variant_hash, b.variant_hash]


# ===========================================================================
# §5 — percentile bila dirisha HAIRUHUSIWI
# ===========================================================================


def test_percentile_bila_dirisha_inalipuka():
    """Percentile juu ya sample nzima ingempa bar ya 2017 taarifa ya 2020."""
    with pytest.raises(D.DNAError, match="percentile"):
        _cond(feature="ATR_percentile", ref=0.5)


def test_percentile_yenye_dirisha_inapita():
    assert _cond(feature="ATR_percentile_252d", ref=0.5).feature.endswith("252d")


def test_dirisha_linakaguliwa_hata_kwenye_ref():
    with pytest.raises(D.DNAError, match="percentile"):
        _cond(feature="RSI_14", ref="tick_count_percentile")


# ===========================================================================
# Vipimo
# ===========================================================================


def test_complexity_ni_jumla_ya_entry_na_exit():
    """§21: `len(entry_conditions) + len(exit_conditions)`."""
    s = _strategy(entry=D.ConditionSet((_cond(), _cond("ADX_14", ">", 25.0))),
                  exit=D.ConditionSet((_cond("RSI_14", "<", 30.0),)))
    assert s.complexity == 3


def test_features_used_hazijirudii():
    s = _strategy(entry=D.ConditionSet((_cond("RSI_14"), _cond("RSI_14", "<", 30.0))),
                  exit=D.ConditionSet((_cond("ADX_14", ">", 25.0),)))
    assert s.features_used == ("RSI_14", "ADX_14")


def test_feature_ya_ref_inaingia_kwenye_features_used():
    s = _strategy(entry=D.ConditionSet((_cond("EMA_20", D.CROSS_ABOVE, "EMA_50"),)))
    assert s.features_used == ("EMA_20", "EMA_50")


# ===========================================================================
# Mikataba midogo
# ===========================================================================


def test_op_isiyojulikana_inalipuka():
    with pytest.raises(D.DNAError, match="op"):
        _cond(op="karibu_na")


def test_direction_isiyojulikana_inalipuka():
    with pytest.raises(D.DNAError, match="direction"):
        _strategy(direction="LONG")


def test_sl_param_isiyo_chanya_inalipuka():
    with pytest.raises(D.DNAError, match="sl_param"):
        _strategy(sl_param=0.0)


def test_strategy_inajielezea():
    s = _strategy(exit=D.ConditionSet((_cond("RSI_14", "<", 30.0),)))
    text = s.render()
    assert "ENTRY" in text and "EXIT" in text and s.variant_hash in text
    assert s.to_json()["complexity"] == 2


# ===========================================================================
# Nakala ndani ya ConditionSet
# ===========================================================================


def test_sharti_lililojirudia_linaanguka():
    """`A AND A` ni `A` — si strategy yenye masharti mawili."""
    a = _cond("RSI_14", ">", 70.0)
    seti = D.ConditionSet((a, a, a))
    assert len(seti) == 1
    assert seti.render() == a.render()


def test_nakala_ISIYOANGUKA_ingeleta_hash_MBILI_kwa_strategy_MOJA():
    """Ingekuwa `variants_tested` inapanda bila utafutaji kupanuka."""
    a = _cond("RSI_14", ">", 70.0)
    assert _strategy(entry=D.ConditionSet((a,))).variant_hash == \
           _strategy(entry=D.ConditionSet((a, a))).variant_hash


def test_complexity_haihesabu_masharti_yasiyobana_chochote():
    """§13 ingeadhibu strategy kwa kitu isichokifanya."""
    a = _cond("RSI_14", ">", 70.0)
    assert _strategy(entry=D.ConditionSet((a, a, a))).complexity == 1


def test_masharti_yanayotofautiana_kwa_negate_HAYAANGUKI():
    a = _cond("RSI_14", ">", 70.0, negate=False)
    b = _cond("RSI_14", ">", 70.0, negate=True)
    assert len(D.ConditionSet((a, b))) == 2


def test_madokezo_HAYAGUNDULIKI_na_hiyo_ni_ya_makusudi():
    """`return_1 < 0` inadokeza `return_1 < 0.01` chini ya AND.

    Kugundua madokezo ni gumu; kuyaacha kunaadhibu strategy kupita kiasi kupitia
    `complexity` — upande salama, si upande unaoficha kitu.
    """
    seti = D.ConditionSet((_cond("return_1", "<", 0.0), _cond("return_1", "<", 0.01)))
    assert len(seti) == 2
