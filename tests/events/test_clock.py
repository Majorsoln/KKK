"""Saa za matukio — DOCTRINE §7.4, §11.

Hitilafu zinazoshughulikiwa hapa zote zina sifa moja: **zinatokea kwa mifumo,
si kwa nasibu.** Tukio la kila mwezi likishikwa saa moja nyuma kwa wiki sita
kwa mwaka si kelele — ni upendeleo unaorudia, na hauonekani kwenye `p-value`
yoyote.

Kwa hiyo majaribio haya yanapimwa dhidi ya **kalenda halisi**, si dhidi ya
hesabu ya code hii yenyewe.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from src.events import clock as C

UTC = ZoneInfo("UTC")


# ===========================================================================
# DST — hitilafu inayoathiri F0 zaidi ya familia zote
# ===========================================================================


def test_London_16_00_ni_saa_TOFAUTI_za_UTC_majira_tofauti():
    """Ndiyo sababu nzima ya moduli hii kuwepo."""
    baridi = C.LONDON_FIX.at(date(2020, 1, 15))
    kiangazi = C.LONDON_FIX.at(date(2020, 7, 15))
    assert baridi.hour == 16 and baridi.minute == 0        # GMT
    assert kiangazi.hour == 15 and kiangazi.minute == 0    # BST


def test_EU_na_US_zinabadilisha_kwa_TAREHE_TOFAUTI():
    """Wiki ambazo tofauti ya London↔New York ni saa NNE, si tano.

    2020: US ilibadilisha 8 Machi; EU ilibadilisha 29 Machi. Kati ya tarehe
    hizo, F0 ingekuwa na nanga zake mbili zikiwa zimehama kwa kiasi tofauti.
    """
    kati = date(2020, 3, 15)                    # US imesha, EU bado
    london = C.LONDON_OPEN.at(kati)
    ny = C.NY_NOON.at(kati)
    assert (ny - london) == timedelta(hours=8)  # kawaida ni saa 9

    baada = date(2020, 4, 15)                   # zote zimebadilisha
    assert (C.NY_NOON.at(baada) - C.LONDON_OPEN.at(baada)) == timedelta(hours=9)


@pytest.mark.parametrize("siku,tofauti", [
    # Kalenda halisi ya 2020: US ilibadilisha 8 Machi, EU 29 Machi;
    # EU ilibadilisha 25 Oktoba, US 1 Novemba.
    (date(2020, 3, 6), 9),      # kabla ya wote — kawaida
    (date(2020, 3, 9), 8),      # US imesha, EU bado
    (date(2020, 3, 27), 8),     # bado ndani ya dirisha
    (date(2020, 3, 30), 9),     # EU imesha — kawaida imerudi
    (date(2020, 10, 23), 9),
    (date(2020, 10, 26), 8),    # EU imerudi, US bado kwenye DST
    (date(2020, 10, 30), 8),
    (date(2020, 11, 2), 9),     # US imerudi — kawaida
])
def test_tofauti_ya_London_NY_dhidi_ya_kalenda_HALISI(siku, tofauti):
    """Ushahidi ni kalenda iliyochapishwa, si hesabu ya code hii yenyewe."""
    assert C.NY_NOON.at(siku) - C.LONDON_OPEN.at(siku) == timedelta(hours=tofauti)


def test_siku_zenye_tofauti_ziko_MACHI_OKTOBA_NOVEMBA_pekee():
    """Muundo, si idadi.

    Nilikisia "wiki 6 kwa mwaka"; kipimo kinasema 145 kwa miezi 99. Dirisha la
    Machi linatofautiana kati ya siku 10 na 15 za kazi kutegemea mwaka (US ni
    Jumapili ya PILI, EU ni ya MWISHO), na la vuli ni 5 daima. Kwa hiyo idadi
    haiwezi kutabiriwa — lakini **miezi inaweza**, na ndiyo inayothibitisha
    kwamba chanzo ni DST na si kitu kingine.
    """
    kawaida = timedelta(hours=9)
    kwa_mwezi: dict[int, int] = {}
    kwa_mwaka: dict[int, int] = {}
    d = date(2016, 1, 1)
    while d < date(2024, 4, 1):
        if d.weekday() in C.SIKU_ZA_KAZI:
            if (C.NY_NOON.at(d) - C.LONDON_OPEN.at(d)) != kawaida:
                kwa_mwezi[d.month] = kwa_mwezi.get(d.month, 0) + 1
                kwa_mwaka[d.year] = kwa_mwaka.get(d.year, 0) + 1
        d += timedelta(days=1)

    assert set(kwa_mwezi) == {3, 10, 11}, kwa_mwezi
    assert sum(kwa_mwezi.values()) > 100          # si sifuri, si chache
    # Kila mwaka una dirisha la Machi (10–15) pamoja na la vuli (5).
    assert all(13 <= n <= 22 for n in kwa_mwaka.values()), kwa_mwaka


def test_Tokyo_HAINA_DST():
    """Japani haina DST — nanga ya Gotobi ni thabiti mwaka mzima."""
    for mwezi in (1, 4, 7, 10):
        saa = C.TOKYO_FIX.at(date(2020, mwezi, 15))
        assert (saa.hour, saa.minute) == (0, 55)     # 09:55 JST = 00:55 UTC


def test_dakika_60_kabla_ya_fix_ni_dakika_60_HATA_siku_ya_mpito():
    """Kusogeza kunafanywa BAADA ya kugeuza kuwa UTC.

    Kusogeza kwenye saa ya mtaa kabla ya kugeuza kungetoa dakika 120 au 0
    kwenye siku ya mpito, bila chochote kuonyesha.
    """
    for siku in (date(2020, 3, 29), date(2020, 10, 25), date(2021, 3, 28)):
        nanga = C.LONDON_FIX.at(siku)
        kabla = C.dirisha_la_tukio(C.LONDON_FIX, siku, offset_minutes=-60)
        assert nanga - kabla == timedelta(minutes=60)


def test_saa_isiyokuwepo_haiLIPUKI():
    """01:30 haikuwepo London tarehe 29 Machi 2020. Tukio linakuwa lililo karibu."""
    saa = C.Anchor(1, 30, "Europe/London").at(date(2020, 3, 29))
    assert saa.tzinfo == UTC


def test_saa_inayojirudia_inachagua_ya_KWANZA():
    """01:30 ilijirudia 25 Oktoba 2020. Kuchagua ya pili kungebadilisha bei
    kwa saa nzima kwenye siku moja ya mwaka, bila kuonekana."""
    saa = C.Anchor(1, 30, "Europe/London").at(date(2020, 10, 25))
    assert saa.hour == 0 and saa.minute == 30        # BST bado (fold=0)


def test_tz_isiyojulikana_inalipuka():
    with pytest.raises(C.ClockError, match="IANA"):
        C.Anchor(8, 0, "Ulaya/London")


def test_saa_isiyo_halali_inalipuka():
    with pytest.raises(C.ClockError, match="saa"):
        C.Anchor(24, 0, "Europe/London")


# ===========================================================================
# Siku ya mwisho ya mwezi — inatofautiana kwa NCHI
# ===========================================================================


def test_siku_ya_mwisho_inaruka_wikendi():
    # 30 Aprili 2022 ilikuwa Jumamosi → 29 Aprili.
    assert C.siku_ya_mwisho_ya_mwezi(2022, 4) == date(2022, 4, 29)
    # 31 Julai 2021 ilikuwa Jumamosi → 30 Julai.
    assert C.siku_ya_mwisho_ya_mwezi(2021, 7) == date(2021, 7, 30)


def test_sikukuu_YA_NCHI_inabadilisha_tarehe():
    """§11 — 31 Desemba ni sikukuu Japani, si Uingereza.

    Sheria moja inayotumia kalenda MOJA ingechagua tarehe tofauti kwa legs
    tofauti za F1, na kuvunja usawa wa cross-section kimya.
    """
    uk = C.siku_ya_mwisho_ya_mwezi(2020, 12)
    jp = C.siku_ya_mwisho_ya_mwezi(2020, 12, holidays=[date(2020, 12, 31)])
    assert uk == date(2020, 12, 31)
    assert jp == date(2020, 12, 30)
    assert uk != jp


def test_sikukuu_kadhaa_mfululizo():
    zilizofungwa = [date(2020, 12, 31), date(2020, 12, 30), date(2020, 12, 29)]
    assert C.siku_ya_mwisho_ya_mwezi(2020, 12, zilizofungwa) == date(2020, 12, 28)


def test_ni_siku_ya_mwisho():
    assert C.ni_siku_ya_mwisho_ya_mwezi(date(2022, 4, 29))
    assert not C.ni_siku_ya_mwisho_ya_mwezi(date(2022, 4, 28))


def test_miezi_99_ina_siku_99_za_mwisho():
    """Dirisha la utafiti: 2016-01 hadi 2024-03. F1 ina matukio 99, si 594."""
    siku = []
    for mwaka in range(2016, 2025):
        for mwezi in range(1, 13):
            if (mwaka, mwezi) > (2024, 3):
                break
            siku.append(C.siku_ya_mwisho_ya_mwezi(mwaka, mwezi))
    assert len(siku) == 99
    assert len(set(siku)) == 99
    assert all(d.weekday() in C.SIKU_ZA_KAZI for d in siku)


# ===========================================================================
# Gotobi
# ===========================================================================


def test_gotobi_ni_tarehe_zinazogawanyika_kwa_5():
    for siku in (5, 10, 15, 20, 25, 30):
        d = date(2021, 6, siku)
        if d.weekday() in C.SIKU_ZA_KAZI:
            assert C.ni_gotobi(d), d


def test_gotobi_ya_wikendi_inaSOGEZWA_MBELE():
    """Desturi ya benki za Japani: malipo yanasogezwa mbele hadi siku ya kazi."""
    # 5 Juni 2021 ilikuwa Jumamosi → Jumatatu 7 Juni ni Gotobi.
    assert date(2021, 6, 5).weekday() == 5
    assert C.ni_gotobi(date(2021, 6, 7))
    assert not C.ni_gotobi(date(2021, 6, 8))


def test_wikendi_yenyewe_si_gotobi():
    assert not C.ni_gotobi(date(2021, 6, 5))     # Jumamosi
    assert not C.ni_gotobi(date(2021, 6, 6))     # Jumapili


def test_gotobi_hazivuki_MWEZI():
    """1 Julai haipaswi kuwa Gotobi kwa sababu 30 Juni ilikuwa wikendi."""
    assert date(2021, 5, 30).weekday() == 6      # Jumapili
    assert not C.ni_gotobi(date(2021, 6, 1))


def test_idadi_ya_gotobi_kwa_mwaka():
    """~matukio 6 kwa mwezi → ~72 kwa mwaka. §9 inatabiri ~600 kwa miezi 99."""
    n = sum(1 for i in range(365)
            if C.ni_gotobi(date(2021, 1, 1) + timedelta(days=i)))
    assert 60 <= n <= 80, n


# ===========================================================================
# Siku ya soko: 17:00 New York, si 00:00 UTC
# ===========================================================================


def test_siku_ya_soko_inaanza_17_00_New_York():
    kabla = datetime(2021, 6, 15, 20, 0, tzinfo=UTC)     # 16:00 NY
    baada = datetime(2021, 6, 15, 22, 0, tzinfo=UTC)     # 18:00 NY
    assert C.siku_ya_soko(kabla) == date(2021, 6, 15)
    assert C.siku_ya_soko(baada) == date(2021, 6, 16)


def test_siku_ya_soko_si_00_00_UTC():
    """Kutumia 00:00 UTC kungegawa siku katikati ya saa yenye ukwasi mdogo."""
    usiku = datetime(2021, 6, 16, 1, 0, tzinfo=UTC)      # 21:00 NY tarehe 15
    assert usiku.date() == date(2021, 6, 16)
    assert C.siku_ya_soko(usiku) == date(2021, 6, 16)

    jioni = datetime(2021, 6, 15, 23, 0, tzinfo=UTC)     # 19:00 NY tarehe 15
    assert C.siku_ya_soko(jioni) == date(2021, 6, 16)


def test_siku_ya_soko_inaheshimu_DST_ya_New_York():
    # Julai: 21:00 UTC = 17:00 EDT → siku inayofuata.
    assert C.siku_ya_soko(datetime(2021, 7, 15, 21, 0, tzinfo=UTC)) == date(2021, 7, 16)
    # Januari: 21:00 UTC = 16:00 EST → siku ile ile.
    assert C.siku_ya_soko(datetime(2021, 1, 15, 21, 0, tzinfo=UTC)) == date(2021, 1, 15)


# ===========================================================================
# tick-VWAP ya upande unaotekelezeka
# ===========================================================================


def _ticks(start: datetime, n: int, bid=1.2000, spread=0.00020, hatua=0.0):
    stamps = pd.date_range(start, periods=n, freq="1s", tz="UTC")
    bids = bid + np.arange(n) * hatua
    return pd.DataFrame({"timestamp": stamps, "bid": bids, "ask": bids + spread})


def test_BUY_inatumia_ASK_na_SELL_inatumia_BID():
    """Mid ingerudisha nusu ya spread kama edge isiyokuwepo."""
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    ticks = _ticks(t0, 300)
    kununua = C.vwap(ticks, t0, 300, C.BUY)
    kuuza = C.vwap(ticks, t0, 300, C.SELL)
    assert kununua.price == pytest.approx(1.20020)
    assert kuuza.price == pytest.approx(1.20000)
    assert kununua.price > kuuza.price


def test_upande_unaotekelezeka_HAULIPI_nusu_ya_spread():
    """Kununua kisha kuuza mara moja lazima kupoteze spread NZIMA."""
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    ticks = _ticks(t0, 120, spread=0.00030)
    ndani = C.vwap(ticks, t0, 60, C.BUY).price
    nje = C.vwap(ticks, t0, 60, C.SELL).price
    assert ndani - nje == pytest.approx(0.00030)


def test_dirisha_linakata_ticks_zilizo_NJE():
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    ticks = _ticks(t0, 600, hatua=0.00001)
    fupi = C.vwap(ticks, t0, 60, C.BUY)
    refu = C.vwap(ticks, t0, 600, C.BUY)
    assert fupi.n_ticks == 60 and refu.n_ticks == 600
    assert fupi.price < refu.price          # bei inapanda kwa `hatua`


def test_mpaka_wa_juu_HAUJUMUISHWI():
    """`[start, start+w)` — tick ya sekunde ya 60 ni ya dirisha linalofuata."""
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    assert C.vwap(_ticks(t0, 120), t0, 60, C.BUY).n_ticks == 60


def test_dirisha_tupu_LINALIPUKA_badala_ya_kubuni_bei():
    """Kubuni bei kungefanya tukio lionekane limetradiwa wakati halikutradiwa."""
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    ticks = _ticks(t0, 60)
    with pytest.raises(C.ClockError, match="hakuna tick"):
        C.vwap(ticks, t0 + timedelta(hours=5), 60, C.BUY)


def test_volume_inatumika_ikiwepo():
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    ticks = _ticks(t0, 3)
    ticks["ask"] = [1.0, 2.0, 3.0]
    ticks["vol"] = [1.0, 1.0, 98.0]
    sawa = C.vwap(ticks, t0, 60, C.BUY)
    kwa_uzito = C.vwap(ticks, t0, 60, C.BUY, volume_col="vol")
    assert sawa.price == pytest.approx(2.0)
    assert kwa_uzito.price == pytest.approx(2.97)


def test_bila_volume_kila_tick_ina_uzito_SAWA():
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    fill = C.vwap(_ticks(t0, 10), t0, 60, C.BUY)
    assert fill.volume == pytest.approx(10.0)     # si volume ya soko


def test_upande_usiojulikana_unalipuka():
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    with pytest.raises(C.ClockError, match="upande"):
        C.vwap(_ticks(t0, 60), t0, 60, "LONG")


def test_dirisha_lisilo_chanya_linalipuka():
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    with pytest.raises(C.ClockError, match="dirisha"):
        C.vwap(_ticks(t0, 60), t0, 0, C.BUY)


def test_safu_isiyopo_inalipuka():
    t0 = datetime(2021, 6, 15, 15, 0, tzinfo=UTC)
    ticks = _ticks(t0, 60).drop(columns=["ask"])
    with pytest.raises(C.ClockError, match="ask"):
        C.vwap(ticks, t0, 60, C.BUY)


# ===========================================================================
# Mnyororo mzima: nanga → dirisha → bei
# ===========================================================================


def test_F1_inaingia_na_kutoka_kwa_nyakati_SAHIHI_majira_yote():
    """Kuingia dakika 60 kabla ya fix, kutoka dakika 15 baada."""
    for siku in (date(2021, 1, 29), date(2021, 7, 30)):
        ndani = C.dirisha_la_tukio(C.LONDON_FIX, siku, offset_minutes=-60)
        nje = C.dirisha_la_tukio(C.LONDON_FIX, siku, offset_minutes=15)
        assert nje - ndani == timedelta(minutes=75)

        ticks = _ticks(ndani, 5400, hatua=0.000001)
        bei_ndani = C.vwap(ticks, ndani, 300, C.SELL)
        bei_nje = C.vwap(ticks, nje, 300, C.BUY)
        assert bei_nje.start > bei_ndani.end
