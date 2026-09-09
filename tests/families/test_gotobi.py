"""Gotobi — malipo ya waagizaji wa Japani — DOCTRINE §4, §9, §11.

Madai yanayopimwa ni ya **ufafanuzi**. Familia haijaendeshwa kwenye data
yoyote, na haitaendeshwa mpaka tangazo lake liwe limefungwa.

Mitego mitatu ya Gotobi, yote ikipimwa hapa:

```
kutoka kunaishia kwenye fix, hakuanzii hapo   →  edge ingefutwa kwa ufafanuzi
kalenda ya benki za Japani                    →  12% ya tarehe zingekosewa
thamani ya pip ya JPY inabadilika kwa bei     →  gharama ingekosewa kwa 37%
```
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.events import jp_calendar as JP
from src.events.clock import TOKYO_FIX, ni_gotobi
from src.families import gotobi as G
from src.families.base import FamilyError
from src.portfolio.basket import BUY
from src.portfolio.regime import MONTH_END_FIX, NORMAL, TURN_OF_YEAR, regime_of


def siku_zote(a: date, b: date) -> list[date]:
    out, d = [], a
    while d <= b:
        out.append(d)
        d += timedelta(days=1)
    return out


MIAKA_NANE = siku_zote(date(2018, 1, 1), date(2025, 12, 31))


def mwendo_thabiti(pips: float = 12.0):
    return lambda day, leg: pips


# ===========================================================================
# Tangazo
# ===========================================================================


def test_sehemu_zote_SITA_zimeandikwa():
    d = G.DECLARATION
    for sehemu in ("nanga", "mwelekeo", "kuingia", "stop", "kutoka", "ukubwa"):
        assert getattr(d, sehemu).strip(), sehemu
    assert d.trials == 1
    assert d.eligible_regimes == (NORMAL,)
    assert d.symbols == ("USDJPY",)


def test_fingerprint_ni_THABITI_na_TOFAUTI_na_ya_F0():
    from src.families import f0
    assert G.DECLARATION.fingerprint() == G.DECLARATION.fingerprint()
    assert G.DECLARATION.fingerprint() != f0.DECLARATION.fingerprint()


def test_mwelekeo_ni_KUNUNUA_dola():
    """Waagizaji wanahitaji dola; benki zinabidi zizinunue kabla ya fix."""
    s, = G.sessions_for(date(2021, 6, 15))
    assert s.side == BUY


# ===========================================================================
# Fix — mtego wa kwanza
# ===========================================================================


def test_dirisha_la_kutoka_LINAISHIA_kwenye_fix():
    """Shinikizo lipo KABLA ya 09:55. `execute` inasoma `[kutoka, kutoka+300)`,
    kwa hiyo nanga lazima iwe `fix − 300s`. Kuchukua `[09:55, 10:00)`
    kungekuwa kuuza baada ya mtiririko — kungefuta edge kwa ufafanuzi."""
    d = date(2021, 6, 15)
    s, = G.sessions_for(d)
    fix = TOKYO_FIX.at(d)
    assert s.exit_at + timedelta(seconds=G.WINDOW_SECONDS) == fix
    assert s.exit_at < fix


def test_kikao_ni_saa_1_33_kila_siku():
    """Japani haina DST, kwa hiyo urefu hauhami kabisa — tofauti na F0."""
    hai = G.eligible_days(MIAKA_NANE)
    urefu = {round(G.sessions_for(d)[0].hours, 4) for d in hai}
    assert urefu == {1.3333}, sorted(urefu)


def test_kikao_kinavuka_usiku_wa_manane_wa_UTC():
    """08:30 JST ni 23:30 UTC ya siku ILIYOTANGULIA. Msomaji lazima achukue
    partitions za siku mbili, na `siku_ya_soko` lazima irudishe tarehe ya
    Tokyo — si ya UTC ya kuingia."""
    from src.events.clock import siku_ya_soko
    d = date(2021, 6, 15)
    s, = G.sessions_for(d)
    assert s.entry_at.date() == d - timedelta(days=1)
    assert s.exit_at.date() == d
    assert siku_ya_soko(s.exit_at) == d


# ===========================================================================
# Kalenda ya benki — mtego wa pili
# ===========================================================================


def test_kalenda_ya_JAPANI_ndiyo_chaguo_msingi():
    """`holidays=None` inamaanisha "tumia kalenda ya Japani", si "hakuna
    sikukuu". Kusahau kuipitisha hakupaswi kukubalika kimya."""
    kwa_msingi = G.eligible_days(MIAKA_NANE)
    bila = G.eligible_days(MIAKA_NANE, holidays=())
    assert kwa_msingi != bila
    assert len(set(kwa_msingi) ^ set(bila)) > 40


def test_sikukuu_ya_Japani_HAIZALISHI_kikapu():
    """5 Mei 2021 ni こどもの日 — Jumatano, tarehe ÷5, benki zimefungwa.
    Bila kalenda ingeonekana gotobi kamili."""
    d = date(2021, 5, 5)
    assert d.day % 5 == 0 and d in JP.holidays(2021)
    assert G.baskets([d], move_pips=mwendo_thabiti()) == []
    # Bila kalenda ingepita kimya.
    assert G.baskets([d], move_pips=mwendo_thabiti(), holidays=()) != []


def test_gotobi_iliyosogezwa_MBELE_inahesabiwa():
    """Tarehe ÷5 ikianguka siku isiyo ya kazi, malipo yanasogezwa mbele hadi
    siku ya kazi inayofuata — ndiyo desturi ya benki."""
    hai = set(G.eligible_days(MIAKA_NANE))
    jp = JP.holidays_between(date(2018, 1, 1), date(2025, 12, 31))
    zilizosogezwa = [d for d in hai if d.day % 5 != 0]
    assert len(zilizosogezwa) > 100
    for d in zilizosogezwa[:20]:
        assert ni_gotobi(d, jp)


def test_mwisho_wa_mwezi_na_mwaka_HAVIZALISHI_kikapu():
    kwa_mwezi = date(2021, 6, 30)
    kwa_mwaka = date(2021, 12, 30)
    assert regime_of(kwa_mwezi) == MONTH_END_FIX
    assert regime_of(kwa_mwaka) == TURN_OF_YEAR
    for d in (kwa_mwezi, kwa_mwaka):
        assert G.baskets([d], move_pips=mwendo_thabiti()) == []


def test_idadi_ya_matukio_kwa_miaka_NANE():
    """Jedwali la §9 linakadiria ~600. Kipimo halisi: **500**, baada ya
    kuondoa sikukuu za Japani, mwisho wa mwezi na mwisho wa mwaka.

    Ni leg MOJA kwa siku, kwa hiyo `n` ya bootstrap ni 500 — si nusu ya
    1,924 za F0, ni robo. Nguvu ni `√(500/1913) = 0.51` ya F0.
    """
    hai = G.eligible_days(MIAKA_NANE)
    assert len(hai) == 500, len(hai)
    assert len(G.baskets(MIAKA_NANE, move_pips=mwendo_thabiti())) == 500


def test_matukio_yanagawanyika_SAWA_kwa_miaka():
    """~62 kwa mwaka. Mwaka mmoja ukiwa na 40 au 80, kuna kasoro ya kalenda."""
    import collections
    kwa_mwaka = collections.Counter(d.year for d in G.eligible_days(MIAKA_NANE))
    assert set(kwa_mwaka) == set(range(2018, 2026))
    assert all(58 <= n <= 68 for n in kwa_mwaka.values()), dict(kwa_mwaka)


# ===========================================================================
# Thamani ya pip ya JPY — mtego wa tatu
# ===========================================================================


def test_thamani_ya_pip_INABADILIKA_kwa_bei():
    """Kwa EURUSD ni $10 daima. Kwa USDJPY ni `1000 ÷ bei`."""
    assert G.pip_value(100.0) == pytest.approx(10.0)
    assert G.pip_value(150.0) == pytest.approx(6.6667, rel=1e-4)
    assert G.pip_value(110.0) / G.pip_value(160.0) == pytest.approx(160 / 110)


def test_safu_ya_sampuli_inatoa_tofauti_ya_ASILIMIA_37():
    """USDJPY ilitoka ~102 (2020) hadi ~162 (2024). Kuweka thamani thabiti
    kungebadilisha `commission_pips` kwa kiasi kile kile."""
    juu, chini = G.pip_value(102.0), G.pip_value(162.0)
    assert (juu - chini) / juu == pytest.approx(0.37, abs=0.02)


def test_bei_isiyo_chanya_INALIPUKA():
    with pytest.raises(FamilyError, match="chanya"):
        G.pip_value(0.0)


def test_commission_kwa_pips_inategemea_BEI():
    """$7 round-turn kwa lot. Kwa bei 110 ni pips 0.77; kwa 160 ni 1.12."""
    assert 7.0 / G.pip_value(110.0) == pytest.approx(0.77, abs=0.01)
    assert 7.0 / G.pip_value(160.0) == pytest.approx(1.12, abs=0.01)


# ===========================================================================
# Vikapu
# ===========================================================================


def test_kikapu_kimoja_chenye_leg_MOJA():
    d = date(2021, 6, 15)
    v = G.baskets([d], move_pips=mwendo_thabiti())
    assert len(v) == 1 and len(v[0].legs) == 1
    assert v[0].basket_id == "Gotobi:2021-06-15:T"
    assert v[0].priority == G.PRIORITY < 3       # mbele ya F0


def test_stop_ni_MIZIDISHO_ya_mwendo():
    v = G.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti(9.0))
    assert v[0].legs[0].sl_pips == pytest.approx(G.SL_MOVE_MULT * 9.0)


def test_siku_isiyo_na_mwendo_HAIZALISHI_kikapu_kimya():
    assert G.baskets([date(2021, 6, 15)],
                     move_pips=lambda d, leg: None) == []


def test_hakuna_kikapu_kinachoshikilia_USIKU():
    """Kikao kinavuka usiku wa manane wa UTC lakini si rollover ya 17:00 NY,
    kwa hiyo swap ni sifuri."""
    from src.events.clock import usiku_wa_swap
    for d in G.eligible_days(siku_zote(date(2021, 1, 1), date(2021, 12, 31))):
        for k in G.baskets([d], move_pips=mwendo_thabiti()):
            assert usiku_wa_swap(k.entry_at, k.planned_exit_at).billed_nights == 0


def test_madirisha_ya_kusoma_ni_MAWILI_kwa_tukio():
    v = G.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti())
    madirisha = G.windows_to_read(v)
    assert len(madirisha) == 2
    assert {w for _, w in madirisha} == {G.WINDOW_SECONDS}
