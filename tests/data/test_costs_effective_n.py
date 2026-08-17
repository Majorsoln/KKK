"""Gharama halisi + effective N — vipimo vinavyoamua kama T3 inawezekana.

Kila test hapa inalinda namba ambayo, ikiwa mbaya, inafanya kila hesabu iliyo
juu yake iwe mbaya. Mbili kati yake zinalinda makosa halisi yaliyotokea kwenye
mapitio ya nje ya 2026-08-13.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.costs import (
    audit,
    config_budget,
    delta_mer,
    n_max_from_cost,
    n_required,
    realized_r,
)
from src.data.effective_n import (
    average_uniqueness,
    estimate,
    integrated_autocorr_time,
    participation_ratio,
)
from src.data.labels import SL_FIRST, TIMEOUT, TP_FIRST


def _cells(rows: list[tuple], sl_pips: float = 32.0) -> pd.DataFrame:
    """(sl, tp, outcome, touch_past_pips) → frame ya barriers."""
    return pd.DataFrame(
        [
            {
                "symbol": "EURUSD",
                "decision_time": pd.Timestamp("2020-01-01", tz="UTC"),
                "sl_atr": sl,
                "tp_atr": tp,
                "outcome": outcome,
                "timeout_return_r": 0.0 if outcome == TIMEOUT else None,
                "sl_pips": sl_pips,
                "touch_past_pips": past,
            }
            for sl, tp, outcome, past in rows
        ]
    )


# ===========================================================================
# Gharama halisi
# ===========================================================================


def test_stop_iliyoruka_inagharimu_zaidi_ya_r_moja():
    """R1 ilitoza −1.0 R sawasawa. Bei haisimami kwenye barrier — inairuka."""
    frame = _cells([(2.0, 2.0, SL_FIRST, 16.0)], sl_pips=32.0)
    r = realized_r(frame, commission_pips=0.0)
    assert r[0] == pytest.approx(-1.5), "16 pips juu ya stop ya 32 = nusu R ya ziada"


def test_tp_iliyorukwa_hailipi_ziada():
    """Limit inajaza kwa bei YAKE — bei kuruka juu yake si faida."""
    frame = _cells([(2.0, 2.0, TP_FIRST, 40.0)], sl_pips=32.0)
    assert realized_r(frame, commission_pips=0.0)[0] == pytest.approx(1.0)


def test_commission_inagawanywa_kwa_sl_pips():
    """`cost_R = commission_pips ÷ sl_pips` — stop pana ni nafuu kwa R."""
    nyembamba = _cells([(0.5, 0.5, TP_FIRST, 0.0)], sl_pips=8.0)
    pana = _cells([(2.0, 2.0, TP_FIRST, 0.0)], sl_pips=32.0)
    assert realized_r(nyembamba, 0.7)[0] == pytest.approx(1.0 - 0.7 / 8.0)
    assert realized_r(pana, 0.7)[0] == pytest.approx(1.0 - 0.7 / 32.0)


def test_gap_ile_ile_inagharimu_kidogo_kwenye_stop_pana():
    """Hoja iliyoanguka kwenye mapitio: wide stop SI fragile zaidi kwa gaps.

    Mtaalamu wa 2 alidai tail risk inaishi kwenye wide-stop corner. Kwa R units
    ni kinyume kabisa, na alikubali. Test hii inashikilia ukweli huo.
    """
    gap = 2503.7
    pana = realized_r(_cells([(2.0, 2.0, SL_FIRST, gap)], sl_pips=713.0), 0.0)[0]
    nyembamba = realized_r(_cells([(0.5, 0.5, SL_FIRST, gap)], sl_pips=178.0), 0.0)[0]
    assert pana > nyembamba, "stop pana inagharimu KIDOGO kwa gap ile ile"
    assert pana == pytest.approx(-4.51, abs=0.02)
    assert nyembamba == pytest.approx(-15.06, abs=0.05)


def test_audit_inatenganisha_gharama_naive_na_halisi():
    rows = [(2.0, 2.0, SL_FIRST, 32.0)] * 50 + [(2.0, 2.0, TP_FIRST, 0.0)] * 50
    report = audit(_cells(rows), commission_pips=0.7)
    cell = report.cells[0]
    assert cell.p_stopped == pytest.approx(0.5)
    assert cell.overshoot_r_mean_given_stop == pytest.approx(1.0)   # 32/32
    # naive: (50·1 − 50·1)/100 = 0 ; halisi: (50·1 − 50·2)/100 = −0.5
    assert cell.ev_r_naive == pytest.approx(0.0)
    assert cell.ev_r_realized == pytest.approx(-0.5)
    # gharama = commission + P(stop)·E[overshoot|stop]
    assert cell.cost_r_total == pytest.approx(0.7 / 32.0 + 0.5 * 1.0)


def test_audit_inakataa_labels_za_toleo_la_kwanza():
    """Bila `touch_past_pips`, gharama HAIWEZI kupimwa — isiripotiwe kama sifuri."""
    frame = _cells([(1.0, 1.0, SL_FIRST, 0.0)]).drop(columns=["touch_past_pips"])
    report = audit(frame)
    assert not report.cells
    assert any("toleo la 1" in n for n in report.notes)


# ===========================================================================
# Identities za T3
# ===========================================================================


def test_n_max_inashuka_kwa_mraba_wa_gharama():
    """`√n ≤ κ·SR*/cost_R` — gharama mara mbili = n_max robo."""
    a = n_max_from_cost(cost_r=0.022, sr_target=0.7, kappa=0.50)
    b = n_max_from_cost(cost_r=0.044, sr_target=0.7, kappa=0.50)
    assert a == pytest.approx(253.0, rel=0.01)
    assert b == pytest.approx(a / 4.0, rel=0.01)


def test_delta_mer_inashuka_kwa_mzizi_wa_n():
    """Frequency inanunuliwa kwa sample size: n kubwa → δ ndogo → data zaidi."""
    assert delta_mer(0.7, 253) == pytest.approx(0.022, abs=0.001)
    assert delta_mer(0.7, 1012) == pytest.approx(delta_mer(0.7, 253) / 2.0, rel=0.01)


def test_delta_mer_inategemea_uwiano_wa_tp_kwa_sl():
    """`dEV/dp_tp = 1 + tp/sl` — si 2.0 daima.

    Kwa cell 2.0/3.0 ni 2.5. Kutumia 2.0 kunavimbisha δ_MER (0.0294 badala ya
    0.0235) — na kwa sababu `N_req ∝ 1/δ²`, kunafanya data inayohitajika
    **ionekane ndogo** kuliko ilivyo: 2,269 badala ya 3,549.

    Ndio mwelekeo hatari: kosa lilifanya jaribio lionekane rahisi zaidi.
    Kosa lililotokea kwenye run ya kwanza ya `cost-audit` (2026-08-13).
    """
    n = 142.0
    sawa = delta_mer(0.7, n, dev_dp=1.0 + 3.0 / 2.0)      # cell 2.0/3.0
    kosa = delta_mer(0.7, n, dev_dp=2.0)                  # dhana ya tp/sl = 1
    assert sawa == pytest.approx(0.0235, abs=0.0005)
    assert kosa == pytest.approx(0.0294, abs=0.0005)
    assert n_required(sawa) == pytest.approx(3_549, rel=0.02)
    assert n_required(kosa) == pytest.approx(2_269, rel=0.02)
    assert n_required(kosa) < n_required(sawa), "kosa lilipunguza data inayoonekana kuhitajika"


def test_n_required_ni_one_sample_si_two():
    """Swali ni "je inazidi breakeven ILIYOFAHAMIKA" — one-sample.

    Formula ya two-sample ingedai mara mbili ya data, na hukumu ya mradi
    ingehama kutoka "inawezekana" kwenda "acha" (mapitio ya nje, 2026-08-13).
    """
    assert n_required(0.007) == pytest.approx(40_000, rel=0.02)
    assert n_required(0.022) == pytest.approx(4_050, rel=0.03)
    # Two-sample ingedai mara mbili — ndilo kosa lililotokea.
    assert n_required(0.007) * 2 == pytest.approx(80_000, rel=0.02)
    # One-sided ni rahisi zaidi; tumechagua ya tahadhari kwa MAKUSUDI.
    assert n_required(0.007, two_sided=False) == pytest.approx(31_500, rel=0.02)


def test_config_budget_inategemea_sr_unayoiahidi():
    """Bajeti si mali ya dataset pekee — ni function ya ahadi yako."""
    assert config_budget(1.0, 8.25) == pytest.approx(62, rel=0.02)
    assert config_budget(0.7, 8.25) == pytest.approx(7.5, rel=0.03)
    assert config_budget(0.5, 8.25) == pytest.approx(2.8, rel=0.03)


def test_mnyororo_kamili_wa_identities():
    """cost_R → n_max → δ_MER → N_req, kama utakavyosainiwa."""
    n_max = n_max_from_cost(0.022, sr_target=0.7, kappa=0.50)
    delta = delta_mer(0.7, n_max)
    need = n_required(delta)
    assert n_max == pytest.approx(253, rel=0.01)
    assert delta == pytest.approx(0.0220, abs=0.0005)
    assert need == pytest.approx(4_050, rel=0.03)


# ===========================================================================
# Effective N
# ===========================================================================


def _points(n: int, freq: str = "1D", symbols: tuple[str, ...] = ("EURUSD",)) -> pd.DataFrame:
    rows = []
    for symbol in symbols:
        stamps = pd.date_range("2020-01-01", periods=n, freq=freq, tz="UTC")
        rng = np.random.RandomState(abs(hash(symbol)) % 2**31)
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "decision_time": stamps,
                    "terminal_atr": rng.normal(0, 1, n),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def test_uniqueness_ni_moja_pale_labels_hazipishani():
    """Labels zisizogusana ni observations kamili — uzito 1.0 kila moja."""
    points = _points(50, freq="48h")      # nafasi 48 bars, horizon 24
    total, weights = average_uniqueness(points, horizon_bars=24)
    assert total == pytest.approx(50.0)
    assert weights.round(6).eq(1.0).all()


def test_uniqueness_haiadhibu_symbols_kwa_kuwepo_tu():
    """Symbols HURU zisipunguzane uniqueness kwa kuwa tu ziko hai kwa wakati mmoja.

    Toleo la kwanza lilihesabu concurrency kwenye timeline moja ya symbols zote.
    Kila label ilionekana ya kipekee kwa 8.6% — na 8.6% ≈ 1/12, idadi ya symbols
    zetu, si mali ya data. Hilo lilishusha N_eff mara nne na lilikaribia kufunga
    mradi unaowezekana (2026-08-13).

    Kupishana kwa MUDA ni kazi ya `n_uniq`; redundancy ya cross-sectional ni
    kazi ya `participation_ratio`. Kuvichanganya ni kuhesabu mara mbili.
    """
    moja = _points(60, freq="48h", symbols=("EURUSD",))
    kumi_mbili = _points(
        60, freq="48h",
        symbols=tuple(f"S{i}" for i in range(12)),
    )
    total_moja, _ = average_uniqueness(moja, horizon_bars=24)
    total_12, _ = average_uniqueness(kumi_mbili, horizon_bars=24)

    assert total_moja == pytest.approx(60.0)
    # Symbols 12, kila moja na labels 60 zisizopishana → 720, si 60.
    assert total_12 == pytest.approx(720.0), "symbols hazipaswi kupunguzana"


def test_uniqueness_inaporomoka_labels_zikipishana():
    """Bars 23/24 zikishirikiwa, observations 100 si 100."""
    points = _points(100, freq="1h")      # nafasi bar 1, horizon 24
    total, _ = average_uniqueness(points, horizon_bars=24)
    assert total < 20.0, "labels zinazopishana kabisa haziwezi kuwa 100 huru"
    assert total > 4.0


def test_tau_inakua_kwa_mfululizo_wenye_kumbukumbu():
    """Random walk ina autocorrelation; kelele safi haina."""
    rng = np.random.RandomState(0)
    kelele = pd.Series(rng.normal(0, 1, 2000))
    kumbukumbu = pd.Series(np.cumsum(rng.normal(0, 1, 2000)))
    assert integrated_autocorr_time(kelele) < 3.0
    assert integrated_autocorr_time(kumbukumbu) > 20.0


def test_participation_ratio_inahesabu_factors_si_columns():
    """Columns 12 zenye factor MOJA si breadth ya 12."""
    rng = np.random.RandomState(1)
    factor = rng.normal(0, 1, 500)
    moja = pd.DataFrame({f"s{i}": factor + rng.normal(0, 0.01, 500) for i in range(12)})
    huru = pd.DataFrame({f"s{i}": rng.normal(0, 1, 500) for i in range(12)})
    assert participation_ratio(moja) < 1.5, "factor moja lazima ionekane kama ~1"
    assert participation_ratio(huru) > 10.0, "columns huru lazima zionekane kama ~12"


def test_n_block_inazidishwa_kwa_breadth_si_kuachwa_kwa_symbol_moja():
    """Kosa halisi la mapitio: blocks ni ZA KILA SYMBOL.

    Kuzitumia kama jumla kunashusha N kwa mara tano na kunageuza hukumu ya
    mradi. Symbols zaidi zenye tabia huru lazima ziinue n_block.
    """
    moja = estimate(_points(400, symbols=("EURUSD",)), horizon_bars=24)
    nne = estimate(
        _points(400, symbols=("EURUSD", "GBPUSD", "USDJPY", "XAUUSD")), horizon_bars=24
    )
    assert nne.n_block > moja.n_block * 2.0
    assert nne.participation_ratio > 2.0


def test_n_eff_ni_ndogo_kuliko_zote_si_wastani():
    result = estimate(_points(300, freq="1h"), horizon_bars=24)
    assert result.n_eff == min(
        x for x in (result.n_uniq, result.n_time, result.n_cross, result.n_block) if x > 0
    )
    assert result.n_eff <= result.n_raw


def test_cost_audit_ya_subset_haiandiki_juu_ya_ushahidi_wa_pool_nzima(tmp_path, monkeypatch):
    """Populations mbili, jina moja = provenance iliyovunjika.

    `cost_audit.json` ndilo ushahidi uliotajwa na sahihi #19. Kuendesha
    `--symbols <subset>` kuliandika juu yake, na matokeo yalionekana kama
    sahihi iliyoharibika badala ya kipimo kipya cha population nyingine.
    """
    import hashlib

    zote = ["EURUSD", "GBPUSD", "USDJPY"]
    digest = hashlib.sha256(",".join(sorted(zote)).encode("utf-8")).hexdigest()[:8]
    assert f"cost_audit_{len(zote)}sym_{digest}" != "cost_audit"
    # Jina lile lile kwa seti ile ile, tofauti kwa seti tofauti.
    nyingine = ["EURUSD", "GBPUSD"]
    other = hashlib.sha256(",".join(sorted(nyingine)).encode("utf-8")).hexdigest()[:8]
    assert other != digest
    # Mpangilio wa symbols hauhesabiki — seti ndiyo inayohesabika.
    tena = hashlib.sha256(",".join(sorted(reversed(zote))).encode("utf-8")).hexdigest()[:8]
    assert tena == digest


# ===========================================================================
# T4 — nguvu ya cross-section
# ===========================================================================


def test_blocs_zinazohitajika_ni_kinyume_cha_rho_crit():
    """`ρ_crit = z/√(blocs−1)` na `blocs = 1 + (z/ρ)²` lazima zilingane.

    Kama hazilingani, kizingiti kinachoripotiwa na idadi inayopendekezwa ni
    vitu viwili tofauti, na mpango wa T4 unajengwa juu ya mchanga.
    """
    import math
    from statistics import NormalDist

    z = NormalDist().inv_cdf(0.95)
    for rho in (0.40, 0.50, 0.545, 0.70):
        blocs = 1.0 + (z / rho) ** 2
        assert z / math.sqrt(blocs - 1.0) == pytest.approx(rho, rel=1e-9)


def test_kipimo_kimoja_kinapunguza_blocs_zinazohitajika():
    """Kutangaza kipimo KIMOJA badala ya viwili ni uamuzi wa gharama, si mtindo."""
    from statistics import NormalDist

    dist = NormalDist()
    kimoja = 1.0 + (dist.inv_cdf(0.95) / 0.545) ** 2
    viwili = 1.0 + (dist.inv_cdf(1 - 0.05 / 2) / 0.545) ** 2
    assert kimoja < viwili
    # Kwa ρ 0.545: 10.1 dhidi ya 13.9 — blocs 3.8 zaidi, yaani symbols 4-6.
    assert viwili - kimoja == pytest.approx(3.82, abs=0.05)


def test_athari_ndogo_inadai_blocs_nyingi_zaidi():
    from statistics import NormalDist

    z = NormalDist().inv_cdf(0.95)
    assert (1.0 + (z / 0.434) ** 2) > (1.0 + (z / 0.545) ** 2) > (1.0 + (z / 0.70) ** 2)


def test_participation_ratio_inapendelea_safu_HURU_kuliko_rudufu():
    """Msingi wa `select-symbols`: bloc mpya si safu mpya.

    Greedy inachagua kwa PR. Ikiwa PR haitofautishi safu huru na nakala,
    uchaguzi mzima ni wa bahati — na `USDAED` (AED imefungwa kwa USD)
    ingechaguliwa sawa na `USDMXN`.
    """
    import numpy as np
    import pandas as pd

    from src.data.effective_n import participation_ratio

    rng = np.random.RandomState(0)
    base = pd.DataFrame(rng.normal(size=(400, 3)), columns=["a", "b", "c"])

    huru = base.copy()
    huru["d"] = rng.normal(size=400)                      # bloc mpya kabisa
    rudufu = base.copy()
    rudufu["d"] = base["a"] + rng.normal(0, 0.01, 400)    # nakala ya `a`

    assert participation_ratio(huru) > participation_ratio(rudufu)
    # Nakala HAIONGEZI — inashusha PR chini ya msingi wenyewe. Kwa hiyo greedy
    # ya `select-symbols` (`best_pr > pr`) inaikataa yenyewe, bila sheria ya
    # ziada: symbol isiyoleta bloc haichaguliwi kabisa.
    assert participation_ratio(rudufu) < participation_ratio(base)
    assert participation_ratio(huru) > participation_ratio(base)


def test_jozi_iliyofungwa_inaonekana_huru_kwa_pr_lakini_haitembei():
    """Kwa nini `select-symbols` inahitaji sakafu ya volatility.

    `EURDKK` (DKK imefungwa kwa EUR) ilichaguliwa KWANZA na toleo la kwanza.
    Returns zake ni karibu kelele ya kupima tu — hazihusiani na kitu chochote,
    kwa hiyo PR inapanda. Lakini SETUP-v1 ina lango la ATR band: jozi
    isiyotembea haitoi setups, na `R` yake haipo. Bloc isiyo na trades si bloc.
    """
    import numpy as np
    import pandas as pd

    from src.data.effective_n import participation_ratio

    rng = np.random.RandomState(1)
    soko = rng.normal(0, 0.006, 800)
    frame = pd.DataFrame({
        "a": soko + rng.normal(0, 0.002, 800),
        "b": soko + rng.normal(0, 0.002, 800),
        "c": soko + rng.normal(0, 0.002, 800),
    })
    peg = frame.copy()
    peg["d"] = rng.normal(0, 0.00008, 800)      # imefungwa: haitembei

    # PR inapanda — ndiyo tatizo lenyewe.
    assert participation_ratio(peg) > participation_ratio(frame)
    # Sakafu ndiyo inayoikataa: volatility yake ni chini ya nusu ya ndogo zetu.
    vol = peg.std() * np.sqrt(252.0)
    sakafu = float(vol[["a", "b", "c"]].min()) * 0.5
    assert vol["d"] < sakafu


def test_spread_pana_inaua_setup_bila_kujali_kitu_kingine():
    """Kwa nini `select-symbols` inaripoti gharama kabla ya kurekodi ticks.

    Utambulisho `√n ≤ κ·SR*/cost_R`: gharama ikiongezeka mara mbili, `n_max`
    inashuka mara nne. Symbol yenye spread pana kuliko zetu inaingiza gharama
    hiyo kwenye pool NZIMA, si kwake peke yake.
    """
    from src.data.costs import n_max_from_cost

    n_zetu = n_max_from_cost(0.0271, sr_target=0.7, kappa=0.5)
    n_pana = n_max_from_cost(0.0271 * 2, sr_target=0.7, kappa=0.5)
    assert n_pana == pytest.approx(n_zetu / 4.0, rel=1e-9)
    assert n_zetu > 150 and n_pana < 50


def test_mpaka_wa_grid_nzima_ni_mkali_kuliko_wa_cell_moja():
    """Cells 49 zikiangaliwa kisha bora ikachaguliwa — CI yake ni ya uongo.

    Ni kosa lile lile la jedwali la symbols 12: bora kati ya wengi karibu
    daima ina mpaka wa chini chanya kwa bahati. Šidák kwa 49 inadai asilimia
    0.105, si 5 — tofauti ya mara 48.
    """
    import numpy as np

    q5 = 5.0
    q_fwer = 100.0 * (1.0 - 0.95 ** (1.0 / 49))
    assert q_fwer < q5 / 40, f"marekebisho ni hafifu: {q_fwer:.4f}"

    rng = np.random.RandomState(0)
    draws = rng.normal(0.02, 0.012, 20000)
    low5 = float(np.percentile(draws, q5))
    low_f = float(np.percentile(draws, q_fwer))
    assert low_f < low5, "mpaka wa FWER lazima uwe chini"
    # Kwa athari ya +0.02 na SE 0.012, tofauti ni ya kuamua: p5 chanya,
    # FWER hasi — hukumu mbili tofauti kabisa kutoka data ile ile.
    assert low5 > 0 and low_f < 0
