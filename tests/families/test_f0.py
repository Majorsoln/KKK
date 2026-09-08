"""F0 — mtiririko wa saa za nchi — DOCTRINE §4, §9, §11.

Madai yanayopimwa hapa ni ya **ufafanuzi**, si ya utendaji. F0 haijaendeshwa
kwenye data yoyote bado, na haitaendeshwa mpaka tangazo lake liwe limefungwa.
Kila kitu kinachoweza kuharibu tafsiri ya matokeo kimya — nanga inayohama kwa
DST, stop yenye lookahead, siku ya mwisho wa mwezi ikiingia kimya — kinapimwa
hapa, kabla ya row moja ya ticks kusomwa.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.events.clock import NY_NOON
from src.families import f0
from src.families.base import FamilyError
from src.portfolio.basket import BUY, SELL
from src.portfolio.regime import MONTH_END_FIX, NORMAL, TURN_OF_YEAR, regime_of


def siku_zote(a: date, b: date) -> list[date]:
    out, d = [], a
    while d <= b:
        out.append(d)
        d += timedelta(days=1)
    return out


MIAKA_NANE = siku_zote(date(2018, 1, 1), date(2025, 12, 31))


def mwendo_thabiti(pips: float = 20.0):
    """Mwendo usiobadilika — kwa majaribio yanayopima kalenda, si ukubwa."""
    return lambda day, leg: pips


# ===========================================================================
# Tangazo
# ===========================================================================


def test_sehemu_zote_SITA_zimeandikwa():
    """§4 — familia isiyokamilika haiendeshwi."""
    d = f0.DECLARATION
    for sehemu in ("nanga", "mwelekeo", "kuingia", "stop", "kutoka", "ukubwa"):
        assert getattr(d, sehemu).strip(), sehemu
    assert d.trials == 1
    assert d.eligible_regimes == (NORMAL,)


def test_fingerprint_ni_THABITI():
    """Ikibadilika kati ya run mbili, ni familia mbili — na α mbili."""
    assert f0.DECLARATION.fingerprint() == f0.DECLARATION.fingerprint()
    assert len(f0.DECLARATION.fingerprint()) == 32


def test_kubadilisha_kigezo_KUNABADILISHA_fingerprint():
    from dataclasses import replace
    nyingine = replace(f0.DECLARATION,
                       params={**f0.DECLARATION.params, "sl_move_mult": 3.0})
    assert nyingine.fingerprint() != f0.DECLARATION.fingerprint()


def test_familia_isiyo_na_mekanizimu_HAIKUBALIKI():
    from dataclasses import replace
    with pytest.raises(FamilyError, match="mekanizimu"):
        replace(f0.DECLARATION, mechanism="  ")


# ===========================================================================
# Mielekeo — F0 si bet ya mwelekeo wa dola
# ===========================================================================


def test_legs_mbili_zina_mielekeo_TOFAUTI():
    """Kiini cha muundo: kama faida inatoka kwenye mwelekeo wa dola kwa
    kipindi chetu, legs mbili zinafutana na jibu ni sifuri. Kinachoweza
    kunusurika ni muundo wa saa za siku pekee."""
    a, b = f0.sessions_for(date(2021, 6, 15))
    assert a.side == SELL and a.leg == f0.LEG_A
    assert b.side == BUY and b.leg == f0.LEG_B


def test_kikapu_kimoja_kwa_kila_leg():
    """Legs zina nanga tofauti; kikapu ni nia moja kwenye dirisha MOJA."""
    v = f0.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti())
    assert len(v) == 2
    assert [len(k.legs) for k in v] == [1, 1]
    assert {k.basket_id for k in v} == {"F0:2021-06-15:A", "F0:2021-06-15:B"}


# ===========================================================================
# DST — kasoro kubwa kuliko zote za F0 (§11)
# ===========================================================================


def test_leg_A_ni_masaa_TISA_kila_siku_bila_ubaguzi():
    """Nanga zote mbili za leg A ziko kwenye saa ya London, kwa hiyo urefu
    hauhami kabisa. Ndiyo sababu nzima ya kushika mpaka wa Ulaya kwenye saa
    ya Ulaya. Kipimo: siku 1,924/1,924 (2026-09-08)."""
    hai = f0.eligible_days(MIAKA_NANE)
    urefu = {round(f0.sessions_for(d)[0].hours, 4) for d in hai}
    assert urefu == {9.0}, sorted(urefu)


def test_kushika_kwenye_saa_ya_NY_kungehamisha_mpaka_siku_131():
    """Jedwali la §9 linaandika nanga ya kati kama "12:00 NY". Ni kitu kile
    kile kwa wiki 49/52 — lakini si kwenye wiki za mpito wa DST.

    Kipimo (2018–2025): siku **131** kati ya 1,924 (6.8%) ambapo 17:00 London
    si 12:00 New York. Kwenye siku hizo, kushika kwa saa ya NY kungefupisha
    leg A hadi masaa 8 kwa sababu ya nchi **isiyohusika na mekanizimu**.
    """
    hai = f0.eligible_days(MIAKA_NANE)
    tofauti = [d for d in hai if f0.A_EXIT.at(d) != NY_NOON.at(d)]
    assert len(tofauti) == 131, len(tofauti)
    assert 0.05 < len(tofauti) / len(hai) < 0.08

    d = tofauti[0]
    saa_london = (f0.A_EXIT.at(d) - f0.A_ENTRY.at(d)).total_seconds() / 3600
    saa_ny = (NY_NOON.at(d) - f0.A_ENTRY.at(d)).total_seconds() / 3600
    assert saa_london == 9.0 and saa_ny == 8.0


def test_leg_B_INAFUPIKA_kwenye_wiki_za_mpito():
    """Na hiyo ni sahihi: madawati ya Ulaya yameondoka saa moja baadaye kwa
    saa ya New York, kwa hiyo kikao cha Marekani pekee ni kifupi kweli."""
    hai = f0.eligible_days(MIAKA_NANE)
    urefu = sorted({round(f0.sessions_for(d)[1].hours, 2) for d in hai})
    assert urefu == [3.42, 4.42], urefu


def test_leg_B_INAINGIA_baada_ya_dirisha_la_kutoka_la_A():
    """Bila hilo, bei ya kutoka ya A na ya kuingia ya B zingetoka ticks
    zilezile, na akaunti ingekuwa na nafasi mbili za symbol moja."""
    for d in (date(2021, 3, 17), date(2021, 6, 15), date(2021, 11, 2)):
        a, b = f0.sessions_for(d)
        assert b.entry_at == a.exit_at + f0.B_ENTRY_DELAY
        assert (b.entry_at - a.exit_at).total_seconds() == f0.WINDOW_SECONDS


def test_leg_B_HAIWEZI_kuwa_na_urefu_hasi_kwa_miaka_kumi():
    """Sheria ya DST imebadilika mara mbili tangu 2007. Ikibadilika tena hivi
    kwamba 17:00 London inapita 16:30 NY, `sessions_for` inalipuka badala ya
    kutoa leg ya urefu hasi kimya."""
    for d in f0.eligible_days(siku_zote(date(2016, 1, 1), date(2025, 12, 31))):
        a, b = f0.sessions_for(d)
        assert b.exit_at > b.entry_at > a.exit_at > a.entry_at


# ===========================================================================
# Regime — kutokuendesha ni sehemu ya ufafanuzi, si kuzunguka lango
# ===========================================================================


def test_siku_ya_mwisho_wa_mwezi_HAIZALISHI_kikapu():
    d = date(2021, 6, 30)
    assert regime_of(d) == MONTH_END_FIX
    assert f0.baskets([d], move_pips=mwendo_thabiti()) == []


def test_mwisho_wa_mwaka_HAUZALISHI_kikapu():
    d = date(2021, 12, 23)
    assert regime_of(d) == TURN_OF_YEAR
    assert f0.baskets([d], move_pips=mwendo_thabiti()) == []


def test_wikendi_na_sikukuu_HAZIZALISHI_kikapu():
    jumamosi = date(2021, 6, 19)
    sikukuu = date(2021, 6, 15)
    assert f0.baskets([jumamosi], move_pips=mwendo_thabiti()) == []
    assert f0.baskets([sikukuu], move_pips=mwendo_thabiti(),
                      holidays=[sikukuu]) == []


def test_idadi_ya_matukio_kwa_miaka_NANE():
    """Jedwali la §9 linakadiria ~2,100. Kipimo halisi kwa 2018–2025, baada ya
    kuondoa wikendi, mwisho wa mwezi na mwisho wa mwaka: **siku 1,924**, yaani
    **legs 3,848**.

    Kwa bootstrap, `n` ni **siku** (curve ni ya siku), si legs. Kwa hiyo
    kalibrisheni ya §7.1b inasomwa kwa n = 1,924, si 3,848:
    `√(1924/2100) = 0.957` — nguvu ndogo kidogo kuliko ilivyokadiriwa.
    """
    hai = f0.eligible_days(MIAKA_NANE)
    assert len(hai) == 1924, len(hai)
    v = f0.baskets(MIAKA_NANE, move_pips=mwendo_thabiti())
    assert len(v) == 3848, len(v)


# ===========================================================================
# Mwendo — stop ni bima, na haijui yajayo
# ===========================================================================


def test_mwendo_unatumia_vikao_VILIVYOPITA_pekee():
    """Lookahead hapa isingeonekana kama kosa: siku zenye mwendo mkubwa
    zingepewa lots ndogo *kwa sababu* mwendo ulikuwa mkubwa, na curve
    ingeonekana laini kuliko ilivyo."""
    siku = [date(2021, 1, d) for d in range(4, 26)]        # siku 22 mfululizo
    ranges = {(d, f0.LEG_A): 10.0 for d in siku}
    ranges[(siku[-1], f0.LEG_A)] = 1_000.0                 # mruko wa siku ya mwisho

    stop = f0.stop_from_moves(ranges, lookback=20, min_sessions=10)
    # Siku ya mruko yenyewe haioni mruko wake.
    assert stop[(siku[-1], f0.LEG_A)] == pytest.approx(10.0)


def test_vikao_vichache_mno_HAVIPATI_stop():
    siku = [date(2021, 1, d) for d in range(4, 16)]        # siku 12
    ranges = {(d, f0.LEG_A): 10.0 for d in siku}
    stop = f0.stop_from_moves(ranges, lookback=20, min_sessions=10)
    assert siku[0] not in {k[0] for k in stop}
    assert len(stop) == 2                                   # 12 − 10


def test_siku_isiyo_na_mwendo_HAIZALISHI_kikapu_kimya():
    """Bila stop hakuna lots (§5). Kuruka siku ni sahihi; kubuni stop si."""
    d = date(2021, 6, 15)
    assert f0.baskets([d], move_pips=lambda day, leg: None) == []
    assert len(f0.baskets([d], move_pips={(d, f0.LEG_A): 20.0})) == 1


def test_stop_ni_MIZIDISHO_ya_mwendo():
    v = f0.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti(17.0))
    for k in v:
        assert k.legs[0].sl_pips == pytest.approx(f0.SL_MOVE_MULT * 17.0)
        assert k.legs[0].meta["move_pips"] == 17.0


def test_mwendo_mkubwa_unatoa_stop_kubwa_na_hivyo_lots_NDOGO():
    """§5.1 — `lots ∝ 1/mwendo`. Kulenga volatility hakuhitaji mfumo wa pili."""
    ndogo = f0.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti(10.0))
    kubwa = f0.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti(40.0))
    assert kubwa[0].legs[0].sl_pips == 4 * ndogo[0].legs[0].sl_pips


def test_mwendo_usio_chanya_UNALIPUKA():
    with pytest.raises(FamilyError, match="chanya"):
        f0.stop_from_moves({(date(2021, 1, 4), f0.LEG_A): 0.0},
                           lookback=20, min_sessions=1)


# ===========================================================================
# Vikapu — sifa zinazotegemewa na arbiter na runner
# ===========================================================================


def test_vikapu_ni_ATOMIKI_na_vinatangaza_NORMAL_pekee():
    for k in f0.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti()):
        assert k.atomic is True
        assert k.eligible_regimes == (NORMAL,)
        assert k.priority == f0.PRIORITY
        assert k.family == f0.FAMILY


def test_uzito_ni_MOJA_kwa_sababu_hakuna_ishara():
    for k in f0.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti()):
        assert k.legs[0].weight == 1.0
        assert abs(k.net_weight) == 1.0


def test_hakuna_kikapu_kinachoshikilia_USIKU():
    """Legs zote zinafungwa siku ile ile, kwa hiyo swap ni sifuri — pamoja na
    Jumatano ya mara tatu (§11)."""
    from src.events.clock import usiku_wa_swap
    for d in f0.eligible_days(siku_zote(date(2021, 1, 1), date(2021, 12, 31))):
        for k in f0.baskets([d], move_pips=mwendo_thabiti()):
            assert usiku_wa_swap(k.entry_at, k.planned_exit_at).billed_nights == 0


def test_madirisha_ya_kusoma_ni_MANNE_kwa_siku():
    """Dakika 20 kati ya 1,440 — ndiyo tofauti kati ya dakika na masaa
    tunaposoma miaka minane ya ticks."""
    v = f0.baskets([date(2021, 6, 15)], move_pips=mwendo_thabiti())
    madirisha = f0.windows_to_read(v)
    assert len(madirisha) == 4
    assert {w for _, w in madirisha} == {f0.WINDOW_SECONDS}
    jumla = sum(w for _, w in madirisha) / 60
    assert jumla == 20.0
