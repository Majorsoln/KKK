"""Ledger ya variants — DOCTRINE §9.3 (S1), R6, R21.

`variants_tested` ndiyo namba inayoamua sakafu ya §9. Ikiwa ndogo kuliko ukweli,
sakafu inashuka na bahati inaonekana kama ugunduzi. Kwa hiyo tests hizi
zinalinda hesabu yenyewe, si urahisi wa kuiandika.
"""

from __future__ import annotations

import json

import pytest

from src.discovery import ledger as L
from src.strategies.dna import ATR_MULT, Condition, ConditionSet, Strategy


def _strategy(ref=70.0, **kw) -> Strategy:
    base = dict(
        symbol="EURUSD", direction="BUY",
        entry=ConditionSet((Condition("RSI_14", ">", ref),)),
        sl_type=ATR_MULT, sl_param=1.5, tp_type=ATR_MULT, tp_param=3.0,
        time_stop_bars=24,
    )
    base.update(kw)
    return Strategy(**base)


# ===========================================================================
# S1 — kuzalishwa si kupimwa
# ===========================================================================


def test_iliyozalishwa_pekee_HAIHESABIWI_kama_iliyopimwa():
    """`GENERATED` haijagusa data, kwa hiyo haiwezi kuwa na bahati."""
    led = L.VariantLedger()
    led.generate(_strategy())
    assert led.n_generated == 1 and led.variants_tested == 0


def test_iliyofika_backtest_INAHESABIWA():
    led = L.VariantLedger()
    rec = led.generate(_strategy())
    led.advance(rec.candidate_id, L.BACKTEST)
    assert led.variants_tested == 1


def test_iliyokataliwa_BAADA_ya_kupimwa_bado_inahesabiwa():
    """Hii ndiyo hatari kubwa: kuiacha kungeshusha sakafu.

    Candidate iliyofika backtest iligusa data. Ikikataliwa baadaye, bado
    ilikuwa na nafasi ya kuwa na bahati — na ndiyo maana `max` ya §9.1
    inaihesabu.
    """
    led = L.VariantLedger()
    rec = led.generate(_strategy())
    led.advance(rec.candidate_id, L.BACKTEST)
    led.advance(rec.candidate_id, L.VALIDATION, reject_reason="chini_ya_sakafu")
    assert led.variants_tested == 1
    assert led.records[0].reject_reason == "chini_ya_sakafu"


def test_INVALID_CANDIDATE_haihesabiwi_lakini_INAANDIKWA():
    """R21 — haikupimwa, kwa hiyo haikuwahi kupata nafasi ya bahati.

    Lakini inaandikwa: bila hivyo, ledger ingesema generator ilizalisha chache
    kuliko ilivyozalisha, na kupanga kwake kusingeweza kuchunguzwa.
    """
    led = L.VariantLedger()
    led.generate(_strategy(), reject_reason=L.INVALID_CANDIDATE)
    assert led.n_generated == 1 and led.variants_tested == 0
    assert led.n_invalid == 1
    assert led.by_reject_reason()[L.INVALID_CANDIDATE] == 1


def test_nakala_inatambulika_na_kuandikwa_kama_DUPLICATE():
    """Hash ile ile si sampuli mpya kutoka null."""
    led = L.VariantLedger()
    led.generate(_strategy())
    pili = led.generate(_strategy())
    assert pili.reject_reason == L.DUPLICATE
    assert led.n_generated == 2 and led.n_duplicate == 1
    assert led.variants_tested == 0


def test_nakala_HAIFUTWI_kimya():
    """Ikifutwa, ledger ingesema utafutaji ulikuwa mdogo kuliko ulivyokuwa."""
    led = L.VariantLedger()
    for _ in range(5):
        led.generate(_strategy())
    assert led.n_generated == 5
    assert len(led.of_hash(_strategy().variant_hash)) == 5


def test_strategies_tofauti_hazichukuliwi_kama_nakala():
    led = L.VariantLedger()
    led.generate(_strategy(ref=70.0))
    pili = led.generate(_strategy(ref=30.0))
    assert pili.reject_reason == ""
    assert led.n_duplicate == 0


# ===========================================================================
# Ledger haiandiki historia upya
# ===========================================================================


def test_kurudi_nyuma_HAKURUHUSIWI():
    led = L.VariantLedger()
    rec = led.generate(_strategy())
    led.advance(rec.candidate_id, L.VALIDATION)
    with pytest.raises(L.LedgerError, match="kurudi nyuma"):
        led.advance(rec.candidate_id, L.BACKTEST)


def test_kusonga_mbele_kunaruhusiwa_kuruka_hatua():
    led = L.VariantLedger()
    rec = led.generate(_strategy())
    led.advance(rec.candidate_id, L.SURVIVOR)
    assert led.survivors[0].candidate_id == rec.candidate_id


def test_candidate_isiyopo_inalipuka():
    with pytest.raises(L.LedgerError, match="haipo"):
        L.VariantLedger().advance("0000000-abc", L.BACKTEST)


def test_hatua_isiyojulikana_inalipuka():
    led = L.VariantLedger()
    rec = led.generate(_strategy())
    with pytest.raises(L.LedgerError, match="hatua"):
        led.advance(rec.candidate_id, "KARIBU")


# ===========================================================================
# Ushahidi
# ===========================================================================


def test_kila_candidate_ina_row_yake_yenye_ukoo():
    led = L.VariantLedger()
    mzazi = _strategy()
    mtoto = _strategy(ref=30.0, generation=1, parent_ids=(mzazi.strategy_id,))
    led.generate(mzazi)
    rec = led.generate(mtoto)
    assert rec.generation == 1
    assert rec.parent_ids == (mzazi.strategy_id,)
    assert rec.tested_at.startswith("20")


def test_ripoti_inaonyesha_pengo_kati_ya_kuzalishwa_na_kupimwa():
    led = L.VariantLedger()
    a = led.generate(_strategy(ref=70.0))
    led.advance(a.candidate_id, L.BACKTEST)
    led.generate(_strategy(ref=70.0))                                  # duplicate
    led.generate(_strategy(ref=30.0), reject_reason=L.INVALID_CANDIDATE)

    text = led.render()
    assert "zilizozalishwa 3" in text and "ZILIZOPIMWA 1" in text
    assert L.DUPLICATE in text and L.INVALID_CANDIDATE in text


def test_ledger_inaandikwa_na_kusomeka(tmp_path):
    led = L.VariantLedger()
    rec = led.generate(_strategy())
    led.advance(rec.candidate_id, L.SURVIVOR)
    led.generate(_strategy(ref=30.0), reject_reason=L.INVALID_CANDIDATE)

    path = led.write(tmp_path / "variants.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["variants_tested"] == 1 and raw["n_generated"] == 2

    rudi = L.VariantLedger.read(path)
    assert rudi.variants_tested == led.variants_tested
    assert rudi.n_invalid == 1
    assert rudi.records[0].stage_reached == L.SURVIVOR


def test_kusoma_kunahifadhi_uwezo_wa_kusonga_mbele(tmp_path):
    led = L.VariantLedger()
    rec = led.generate(_strategy())
    rudi = L.VariantLedger.read(led.write(tmp_path / "v.json"))
    rudi.advance(rec.candidate_id, L.BACKTEST)
    assert rudi.variants_tested == 1
