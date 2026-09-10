"""Mnyororo wa udhibiti chanya — DOCTRINE §7.1, LANGO 1.

Majaribio haya ni ya haraka (siku chache) kwa sababu curve kamili ya nguvu ni
ya `scripts/positive_control.py`. Yanachothibitisha ni kwamba mnyororo
unaunganika: edge iliyopandwa kwenye BEI inafika hadi kwenye `p-value`.
"""

from __future__ import annotations

import pytest

from src.analysis import control as C
from src.analysis import probe as P


def test_mfululizo_una_sigma_ya_SOKO_HALISI(cfg_risk):
    """Kasoro ya pili ya µs/ns ilifanya σ iwe ndogo mara kumi.

    `σ_H1 = 13 pips` → hold ya masaa 9 inapaswa kutoa `13 × √9 ≈ 39 pips`.
    Kwa `sl + cost ≈ 27`, hiyo ni `σ_R ≈ 1.4`.
    """
    curve, _ = P.run_once(P.ProbeSpec(n_days=120), cfg=cfg_risk, pips=0.0,
                          seed=1, B=200)
    sd = float(curve.values().std(ddof=1))
    assert 0.9 < sd < 2.0, sd


def test_bila_edge_hakuna_kuona(cfg_risk):
    curve, r = P.run_once(P.ProbeSpec(n_days=120), cfg=cfg_risk, pips=0.0,
                          seed=3, B=300)
    assert r.p_value > 0.05
    assert curve.n == curve.n_active == 120


def test_edge_KUBWA_inaonekana(cfg_risk):
    """Kama hii inashindwa, mnyororo umevunjika mahali fulani."""
    _, r = P.run_once(P.ProbeSpec(n_days=120), cfg=cfg_risk, pips=15.0,
                      seed=3, B=300)
    assert r.p_value < 0.05
    assert r.mean > 0


def test_edge_kubwa_zaidi_inatoa_delta_KUBWA_zaidi(cfg_risk):
    d = []
    for pips in (0.0, 5.0, 15.0):
        curve, _ = P.run_once(P.ProbeSpec(n_days=100), cfg=cfg_risk, pips=pips,
                              seed=5, B=200)
        d.append(C.delta(curve))
    assert d == sorted(d)


def test_gharama_inaonekana_kwenye_wastani(cfg_risk):
    """Bila edge, wastani unapaswa kuwa karibu na −(spread + commission)/(sl+cost).

    Ni ukaguzi wa upatanisho: kama gharama ingehesabiwa mara mbili, wastani
    ungekuwa mbaya mara mbili.
    """
    spec = P.ProbeSpec(n_days=400)
    curve, _ = P.run_once(spec, cfg=cfg_risk, pips=0.0, seed=11, B=200)
    # Gharama ≈ spread 1.6 + commission 0.7 = 2.3 pips juu ya (25 + ~4) ≈ 0.08R
    inayotarajiwa = -(spec.spread_pips + 0.7) / (spec.sl_pips + 4.0)
    kosa = float(curve.values().std(ddof=1)) / (len(curve.values()) ** 0.5)
    assert abs(curve.values().mean() - inayotarajiwa) < 3 * kosa


def test_madirisha_yanafuata_DST(cfg_risk):
    """Nanga ni `(saa ya mtaa, tz)`, kwa hiyo urefu wa hold unabadilika.

    Januari na Julai ZOTE zina saa 9: London na New York zinahama kwa mwelekeo
    mmoja. Tofauti ipo tu kwenye wiki ambazo moja imehama na nyingine bado —
    US ni Jumapili ya PILI ya Machi (14 Machi 2021), EU ni ya MWISHO (28).
    """
    from datetime import date

    kawaida = P.windows_for([date(2021, 1, 15), date(2021, 7, 15)])
    assert all((w.end - w.start).total_seconds() / 3600 == 9.0 for w in kawaida)

    kati = P.windows_for([date(2021, 3, 17)])[0]         # US imesha, EU bado
    assert (kati.end - kati.start).total_seconds() / 3600 == 8.0


def test_ticks_zinazalishwa_kwa_madirisha_PEKEE(cfg_risk):
    """Mfululizo mzima wa miaka minane ungekuwa rows milioni 250."""
    spec = P.ProbeSpec(n_days=20)
    w = P.windows_for(spec.days())
    ticks = P.synthetic_ticks(w, spec, seed=1)
    assert len(ticks) == 20 * 2 * P.WINDOW_SECONDS


def test_run_ile_ile_inatoa_jibu_LILE_LILE(cfg_risk):
    a = P.run_once(P.ProbeSpec(n_days=60), cfg=cfg_risk, pips=4.0, seed=9, B=200)
    b = P.run_once(P.ProbeSpec(n_days=60), cfg=cfg_risk, pips=4.0, seed=9, B=200)
    assert a[1].p_value == b[1].p_value
    assert a[0].total_r == pytest.approx(b[0].total_r)
