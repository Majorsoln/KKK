"""Kalenda ya Japani — DOCTRINE §11.

Gotobi ni siku ya **malipo ya benki**, si tarehe ya kalenda. Tarehe
isiyosahihi haionekani kwenye matokeo — inaonekana kama kelele. Kwa hiyo
kalenda inapimwa dhidi ya tarehe **zinazojulikana**, si dhidi ya yenyewe.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.events import jp_calendar as JP


def test_sikukuu_za_tarehe_THABITI():
    h = JP.holidays(2023)
    for m, d in ((1, 1), (2, 11), (2, 23), (4, 29), (5, 3), (5, 4), (5, 5),
                 (8, 11), (11, 3), (11, 23)):
        assert date(2023, m, d) in h, (m, d)


def test_sikukuu_za_BENKI_za_mwisho_wa_mwaka():
    """1–3 Januari na 31 Desemba: masoko ya Japani yamefungwa hata kama si
    sikukuu za taifa. Tarehe hizo mbili ni ÷5 au karibu nazo."""
    h = JP.holidays(2023)
    assert {date(2023, 1, 2), date(2023, 1, 3), date(2023, 12, 31)} <= h


def test_Jumatatu_ya_n_th_inahesabiwa():
    """成人の日 ni Jumatatu ya PILI ya Januari."""
    assert date(2023, 1, 9) in JP.holidays(2023)      # Jumatatu ya pili
    assert date(2024, 1, 8) in JP.holidays(2024)
    assert date(2025, 1, 13) in JP.holidays(2025)


def test_ikwinoksi_inahesabiwa_na_ni_MUHIMU():
    """春分の日 mara nyingi ni tarehe 20 — ambayo ni ÷5. Bila fomula, siku
    hiyo ingehesabiwa kama gotobi wakati benki zimefungwa."""
    for mwaka, siku in ((2021, 20), (2022, 21), (2023, 21), (2024, 20),
                        (2025, 20)):
        assert date(mwaka, 3, siku) in JP.holidays(mwaka), mwaka
    # 秋分の日 — Septemba
    for mwaka, siku in ((2021, 23), (2022, 23), (2023, 23), (2024, 22)):
        assert date(mwaka, 9, siku) in JP.holidays(mwaka), mwaka


def test_siku_ya_MBADALA_ikianguka_Jumapili():
    """振替休日: 2021-08-08 (山の8) ilikuwa Jumapili → Jumatatu inafungwa.

    Mwaka 2021 ni wa Olimpiki, kwa hiyo 山の日 ilihamishwa hadi 8 Agosti;
    ilianguka Jumapili, na 9 Agosti ikawa mbadala.
    """
    h = JP.holidays(2021)
    assert date(2021, 8, 8) in h and date(2021, 8, 8).weekday() == 6
    assert date(2021, 8, 9) in h


def test_MFULULIZO_wa_Mei_unasogezwa_mpaka_siku_isiyo_sikukuu():
    """Mei 3–5 ni mfululizo. Mmoja akianguka Jumapili, mbadala si siku
    inayofuata bali ya kwanza isiyo sikukuu — Mei 6."""
    h = JP.holidays(2020)
    assert date(2020, 5, 3) in h and date(2020, 5, 3).weekday() == 6
    assert date(2020, 5, 6) in h


def test_vighairi_vya_OLIMPIKI():
    """2020 na 2021 zilihamisha sikukuu tatu kila mwaka, kwa sheria maalum.
    Ni vighairi vilivyoandikwa, si mfumo."""
    h20 = JP.holidays(2020)
    assert date(2020, 7, 23) in h20 and date(2020, 7, 24) in h20
    assert date(2020, 8, 10) in h20
    assert date(2020, 8, 11) not in h20               # 山の日 ilihamishwa
    h21 = JP.holidays(2021)
    assert date(2021, 7, 22) in h21 and date(2021, 7, 23) in h21
    assert date(2021, 10, 11) not in h21              # スポーツの日 ilihamishwa


def test_siku_ya_kuzaliwa_ya_MFALME_inahama_2019():
    """Heisei: 23 Desemba. Reiwa (tangu 2020): 23 Februari. Mwaka 2019
    haikuwepo kabisa."""
    assert date(2018, 12, 23) in JP.holidays(2018)
    assert date(2019, 12, 23) not in JP.holidays(2019)
    assert date(2020, 2, 23) in JP.holidays(2020)


def test_idadi_ya_sikukuu_iko_kwenye_safu_inayotarajiwa():
    """Japani ina sikukuu za taifa ~16 pamoja na 3 za benki. Idadi ikitoka
    kwenye safu hii, kuna sheria iliyoharibika."""
    for mwaka in range(2016, 2027):
        n = len(JP.holidays(mwaka))
        assert 17 <= n <= 24, (mwaka, n)


def test_holidays_between_inavuka_mpaka_wa_MWAKA():
    """31 Desemba na 1 Januari ziko kwenye miaka miwili tofauti."""
    h = JP.holidays_between(date(2020, 12, 25), date(2021, 1, 5))
    assert date(2020, 12, 31) in h
    assert date(2021, 1, 1) in h and date(2021, 1, 3) in h
    assert all(date(2020, 12, 25) <= d <= date(2021, 1, 5) for d in h)


def test_kalenda_INABADILISHA_tarehe_za_gotobi():
    """Kipimo cha maana: bila kalenda, **tarehe 66 kati ya 548** zingeshikwa
    vibaya kwa 2018–2025 — tungekosa siku zenye mtiririko na kutrade siku
    zisizo nazo."""
    from datetime import timedelta

    from src.events.clock import ni_gotobi

    siku, d = [], date(2018, 1, 1)
    while d <= date(2025, 12, 31):
        siku.append(d)
        d += timedelta(days=1)
    jp = JP.holidays_between(date(2018, 1, 1), date(2025, 12, 31))

    bila = {x for x in siku if ni_gotobi(x)}
    kwa = {x for x in siku if ni_gotobi(x, jp)}
    tofauti = bila ^ kwa
    assert len(tofauti) == 66, len(tofauti)
    assert 0.10 < len(tofauti) / len(kwa) < 0.14
