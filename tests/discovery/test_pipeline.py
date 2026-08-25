"""Pipeline ya kutafuta — DOCTRINE §8.4, §9.2, R6, R17, S1.

Kipimo muhimu zaidi hapa si kwamba inatoa strategy nzuri. Ni kwamba **inatoa
matokeo YALE YALE** ikipewa data ile ile na seed ile ile: `calibrate()` inajenga
mgawanyo kutoka runs 150, na generator isiyo thabiti ingechanganya kelele ya
soko na kelele ya utafutaji kwenye `max` mmoja usiotenganishika.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import BrokerFacts
from src.data.bars import build
from src.data.window import Stage, Window
from src.discovery import pipeline as P
from src.discovery.generator import GeneratorSpec
from src.rce.cost import SymbolSpec
from src.validation.noise_floor import VARIANTS_KEY

STAGE = Stage(
    window=Window(pd.Timestamp("2019-01-01", tz="UTC"), pd.Timestamp("2024-12-31", tz="UTC")),
    name="pipeline", purpose="§9.2",
)

BROKER = BrokerFacts(
    spec=SymbolSpec(symbol="EURUSD", point=0.00001, contract_size=100_000,
                    volume_min=0.01, volume_step=0.01, volume_max=50.0),
    pip_value_acct=10.0, commission_round_turn=7.0,
)


def _bars(n_bars=400, *, seed=3, drift=0.0):
    rng = np.random.default_rng(seed)
    n = n_bars * 60
    stamps = pd.date_range("2020-02-01", periods=n, freq="1min", tz="UTC")
    mid = 1.10 + np.cumsum(rng.normal(drift, 2e-5, n))
    half = 0.6e-4
    ticks = pd.DataFrame({"timestamp": stamps, "bid": mid - half, "ask": mid + half})
    ticks.attrs["symbol"] = "EURUSD"
    out = build(ticks, "H1", STAGE).bars
    out.attrs["symbol"] = "EURUSD"
    return out


def _spec(n=12, **kw) -> P.PipelineSpec:
    base = dict(symbol="EURUSD", timeframe="H1", broker=BROKER,
                generator=GeneratorSpec(symbols=("EURUSD",)), n_candidates=n)
    base.update(kw)
    return P.PipelineSpec(**base)


@pytest.fixture(scope="module")
def bars():
    return _bars()


def _sawa(a: dict, b: dict) -> bool:
    """Ulinganisho unaokubali `NaN == NaN`.

    Run isiyo na mshindi inatoa `NaN` kila mahali, na `NaN != NaN` ingefanya
    test ya kuzalishika upya ifeli hasa pale inapopaswa kupita.
    """
    import math

    if set(a) != set(b):
        return False
    for k in a:
        x, y = a[k], b[k]
        pande_mbili_nan = (isinstance(x, float) and isinstance(y, float)
                           and math.isnan(x) and math.isnan(y))
        if not pande_mbili_nan and x != y:
            return False
    return True


# ===========================================================================
# Kuzalishika upya — sharti la §9.2
# ===========================================================================


def test_seed_ile_ile_inatoa_matokeo_YALE_YALE(bars, cfg_risk):
    """`calibrate()` inabadilisha DATA, si generator.

    Generator ikibadilika kila replicate, `max` ungekuwa wa vitu viwili
    visivyotenganishika: kelele ya soko na kelele ya utafutaji.
    """
    a = P.search(bars, _spec(), cfg_risk=cfg_risk, seed=5, starting_balance=10_000.0)
    b = P.search(bars, _spec(), cfg_risk=cfg_risk, seed=5, starting_balance=10_000.0)
    assert _sawa(a.metrics(), b.metrics())
    assert a.best_id == b.best_id


def test_seed_tofauti_inatafuta_wagombea_tofauti(bars, cfg_risk):
    a = P.search(bars, _spec(), cfg_risk=cfg_risk, seed=5, starting_balance=10_000.0)
    b = P.search(bars, _spec(), cfg_risk=cfg_risk, seed=6, starting_balance=10_000.0)
    hash_a = {r.variant_hash for r in a.ledger.records}
    hash_b = {r.variant_hash for r in b.ledger.records}
    assert hash_a != hash_b


# ===========================================================================
# S1 / R6 — kilichokataliwa bado kimehesabiwa
# ===========================================================================


def test_variants_tested_inajumuisha_waliokataliwa_na_lango_la_uchumi(bars, cfg_risk):
    """Mgombea aliyekataliwa na §8.4 amegusa data.

    Kutomhesabu kungeshusha sakafu kwa utafutaji ambao ulifanyika kweli —
    upande usio salama kabisa.
    """
    out = P.search(bars, _spec(20), cfg_risk=cfg_risk, seed=9,
                   starting_balance=10_000.0)
    walikataliwa = sum(n for jina, n in out.by_reason.items() if jina != "SAWA")
    assert walikataliwa > 0
    assert out.variants_tested > out.n_passed_economics


def test_variants_tested_ni_ya_LEDGER_si_len_ya_walionusurika(bars, cfg_risk):
    out = P.search(bars, _spec(20), cfg_risk=cfg_risk, seed=9,
                   starting_balance=10_000.0)
    assert out.variants_tested == out.ledger.variants_tested
    assert out.metrics()[VARIANTS_KEY] == out.variants_tested


def test_kila_mgombea_ana_row_kwenye_ledger(bars, cfg_risk):
    out = P.search(bars, _spec(15), cfg_risk=cfg_risk, seed=4,
                   starting_balance=10_000.0)
    assert out.ledger.n_generated == 15


# ===========================================================================
# R17 — bora anachaguliwa kwa metric YENYE MAMLAKA
# ===========================================================================


@pytest.fixture(scope="module")
def bars_zenye_mwelekeo():
    """Bei yenye drift — hapa strategies za BUY zina edge ya KWELI.

    Bila hii, test ingetegemea bahati ya seed: juu ya random walk yenye spread,
    mara nyingi hakuna anayepita §8.4, na test ingerukwa — yaani isingepima
    chochote.
    """
    return _bars(600, seed=21, drift=1.2e-6)


def test_bora_ni_wa_juu_kabisa_kwa_select_by(bars_zenye_mwelekeo, cfg_risk):
    out = P.search(bars_zenye_mwelekeo, _spec(60), cfg_risk=cfg_risk, seed=13,
                   starting_balance=10_000.0)
    assert out.best is not None, out.render()
    assert out.best.metrics()[P.SELECT_BY] == out.metrics()[P.SELECT_BY]
    assert out.best_economics.passes


def test_bora_ni_KILELE_cha_waliopita_si_wa_mwisho(bars_zenye_mwelekeo, cfg_risk):
    """Ndicho kiini cha §9.1: sakafu ni ya `max`, si ya mgombea wa nasibu.

    Kosa la kushikilia wa mwisho aliyepita — au `>=` badala ya `>` — lingefanya
    sakafu ipime jaribio moja lolote, na §9.1 nzima ingepotea.
    """
    walipita: list[float] = []

    def kamata(_cid, result, _eco) -> None:
        walipita.append(result.metrics()[P.SELECT_BY])

    out = P.search(bars_zenye_mwelekeo, _spec(60), cfg_risk=cfg_risk, seed=13,
                   starting_balance=10_000.0, on_pass=kamata)

    assert len(walipita) == out.n_passed_economics >= 2
    assert out.metrics()[P.SELECT_BY] == pytest.approx(max(walipita))


def test_on_pass_haiitwi_kwa_waliokataliwa(bars, cfg_risk):
    walioitwa: list[str] = []
    out = P.search(bars, _spec(20), cfg_risk=cfg_risk, seed=9,
                   starting_balance=10_000.0,
                   on_pass=lambda cid, *_: walioitwa.append(cid))
    assert len(walioitwa) == out.n_passed_economics
    assert len(walioitwa) < out.variants_tested


def test_select_by_inaandikwa_kwenye_ushahidi(bars, cfg_risk):
    """Sakafu ni halali kwa sheria ya kuchagua ILE ILE tu (§9.2).

    Ikibadilika bila kuonekana, sakafu ya zamani ingehukumu utafutaji mpya.
    """
    out = P.search(bars, _spec(5), cfg_risk=cfg_risk, seed=1,
                   starting_balance=10_000.0)
    assert out.to_json()["spec"]["select_by"] == P.SELECT_BY


def test_bila_mshindi_metrics_ni_NaN_lakini_variants_tested_ni_HALISI(cfg_risk):
    """Run isiyo na mshindi haisemi 'sifuri', inasema 'hakuna'.

    Sifuri ingeingia kwenye mgawanyo na kushusha sakafu; `NaN` inarukwa.
    """
    import math

    out = P.SearchResult(spec=_spec(), ledger=P.VariantLedger())
    for _ in range(3):
        out.ledger.records.append(_rekodi())
    m = out.metrics()
    assert math.isnan(m["sharpe"]) and math.isnan(m["net_pips_month"])
    assert m[VARIANTS_KEY] == out.ledger.variants_tested


def _rekodi():
    from src.discovery.ledger import BACKTEST, VariantRecord

    return VariantRecord(
        candidate_id="x", variant_hash="h", generation=0, parent_ids=(),
        tested_at="", stage_reached=BACKTEST, symbol="EURUSD", complexity=1,
    )


# ===========================================================================
# `for_calibration` — mkataba wa `calibrate()`
# ===========================================================================


def test_for_calibration_inatimiza_mkataba_wa_calibrate(bars, cfg_risk):
    """Mapping yenye `variants_tested` ≥ 2 — ndicho `_check_result` inachodai."""
    from src.validation.noise_floor import _check_result

    fn = P.for_calibration(_spec(6), cfg_risk=cfg_risk, seed=2,
                           starting_balance=10_000.0)
    out = fn(bars)
    _check_result(out, "block_resample", 0)
    assert out[VARIANTS_KEY] >= 2


def test_for_calibration_inafunga_search_ILE_ILE(bars, cfg_risk):
    """Mnyororo wa pili ungefanya sakafu ipime utafutaji mwingine (§9.2)."""
    fn = P.for_calibration(_spec(6), cfg_risk=cfg_risk, seed=2,
                           starting_balance=10_000.0)
    moja_kwa_moja = P.search(bars, _spec(6), cfg_risk=cfg_risk, seed=2,
                             starting_balance=10_000.0).metrics()
    assert _sawa(fn(bars), moja_kwa_moja)


def test_metrics_hazina_n_trades_wala_path_dependence(bars, cfg_risk):
    """`calibrate()` inaweka kila key isiyojulikana kwenye `without_floor`.

    `n_trades` si metric ya utendaji; ingeonekana kama metric isiyo na sakafu
    na kuchafua ripoti kwa kitu ambacho hakikuwahi kuwa lango.
    """
    out = P.search(bars, _spec(6), cfg_risk=cfg_risk, seed=2,
                   starting_balance=10_000.0).metrics()
    assert "n_trades" not in out and "path_dependence" not in out


# ===========================================================================
# §9.2 — surrogate inapita kwenye pipeline ILE ILE
# ===========================================================================


def test_surrogate_inapita_bila_kubadilisha_chochote(bars, cfg_risk):
    from src.validation import surrogates as S

    sur = S.make(bars, S.BLOCK, seed=7)
    fn = P.for_calibration(_spec(6), cfg_risk=cfg_risk, seed=2,
                           starting_balance=10_000.0)
    out = fn(sur.frame)
    assert out[VARIANTS_KEY] == 6


# ===========================================================================
# Mikataba
# ===========================================================================


def test_mgombea_MMOJA_hana_max():
    with pytest.raises(P.PipelineError, match="max"):
        _spec(1)


def test_symbol_isiyo_kwenye_generator_inalipuka():
    with pytest.raises(P.PipelineError, match="GBPUSD"):
        _spec(symbol="GBPUSD")


def test_inajielezea(bars, cfg_risk):
    out = P.search(bars, _spec(6), cfg_risk=cfg_risk, seed=2,
                   starting_balance=10_000.0)
    text = out.render()
    assert "UTAFUTAJI" in text and P.SELECT_BY in text
    assert out.to_json()["spec"]["substrate"] == "bar_path"
