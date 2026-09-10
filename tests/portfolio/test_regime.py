"""Mifumo ya kalenda — DOCTRINE §6, §11.

Regime si urahisi wa code. Ni **ufafanuzi wa familia**: F0 ni mtiririko wa saa
za kawaida, na siku ya fix ya mwisho wa mwezi si siku ya kawaida.

Kutangaza hilo kabla ni sehemu ya F0. Kugundua baadaye kwamba "F0 inaonekana
bora ukiondoa mwisho wa mwezi" ingekuwa uamuzi wa utafiti unaohesabika kwenye
bajeti ya majaribio.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.events import clock as C
from src.portfolio import regime as R


def test_siku_ya_kawaida():
    assert R.regime_of(date(2021, 6, 15)) == R.NORMAL


def test_siku_ya_mwisho_wa_mwezi():
    assert R.regime_of(date(2021, 6, 30)) == R.MONTH_END_FIX


def test_wikendi_na_sikukuu_ni_HOLIDAY():
    assert R.regime_of(date(2021, 6, 12)) == R.HOLIDAY          # Jumamosi
    assert R.regime_of(date(2021, 6, 15),
                       holidays=[date(2021, 6, 15)]) == R.HOLIDAY


def test_mwisho_wa_mwaka():
    for d in (date(2021, 12, 22), date(2021, 12, 31), date(2022, 1, 3)):
        assert R.regime_of(d) == R.TURN_OF_YEAR, d
    assert R.regime_of(date(2022, 1, 4)) == R.NORMAL


def test_siku_ya_benki_kuu():
    fomc = date(2021, 6, 16)
    assert R.regime_of(fomc) == R.NORMAL
    assert R.regime_of(fomc, cb_days=[fomc]) == R.CB_EVENT


def test_mwisho_wa_mwezi_iko_JUU_ya_benki_kuu():
    """Mtiririko wa hedge ni wa LAZIMA; tukio la benki kuu ni la habari."""
    d = date(2021, 6, 30)
    assert R.regime_of(d, cb_days=[d]) == R.MONTH_END_FIX


def test_31_Desemba_ni_TURN_OF_YEAR_si_MONTH_END():
    """Mpangilio wa kipaumbele umeandikwa mara moja na ni wa kudumu."""
    assert R.regime_of(date(2021, 12, 31)) == R.TURN_OF_YEAR


def test_kila_siku_ina_regime_MOJA_pekee():
    d = date(2016, 1, 1)
    while d < date(2024, 4, 1):
        assert R.regime_of(d) in R.REGIMES, d
        d += timedelta(days=1)


def test_idadi_ya_siku_za_MONTH_END_FIX():
    """F1 ina matukio 99 — lakini Desemba inachukuliwa na TURN_OF_YEAR."""
    n = sum(1 for i in range(3013)
            if (d := date(2016, 1, 1) + timedelta(days=i)) < date(2024, 4, 1)
            and R.regime_of(d) == R.MONTH_END_FIX)
    # Miezi 99 pungufu Desemba nane (2016–2023), ambazo ni TURN_OF_YEAR.
    assert n == 99 - 8, n


def test_gotobi_halali_inaruka_regime_zisizo_NORMAL():
    """Gotobi haigongani na F1 kwa muda, lakini sheria ni moja kwa familia zote."""
    mwisho = date(2016, 6, 30)
    assert C.ni_gotobi(mwisho)
    assert R.regime_of(mwisho) == R.MONTH_END_FIX
    assert not R.ni_gotobi_halali(mwisho)

    kawaida = date(2021, 6, 15)
    assert C.ni_gotobi(kawaida) and R.ni_gotobi_halali(kawaida)


def test_gharama_ya_kutengana_imepimwa():
    """Namba zinazoingia kwenye doctrine, si makadirio."""
    siku = [d for i in range(3013)
            if (d := date(2016, 1, 1) + timedelta(days=i)) < date(2024, 4, 1)]
    kazi = [d for d in siku if C.ni_siku_ya_kazi(d)]
    f0_kawaida = [d for d in kazi if R.regime_of(d) == R.NORMAL]
    gotobi_zote = [d for d in kazi if C.ni_gotobi(d)]
    gotobi_halali = [d for d in kazi if R.ni_gotobi_halali(d)]

    # F0 inapoteza siku zisizo NORMAL (mwisho wa mwezi + mwisho wa mwaka).
    kupotea = (len(kazi) - len(f0_kawaida)) / len(kazi)
    assert 0.05 < kupotea < 0.11, kupotea
    # Gotobi inapoteza kidogo zaidi kwa sababu ya tarehe 30/31.
    g = 1 - len(gotobi_halali) / len(gotobi_zote)
    assert 0.05 < g < 0.16, g
