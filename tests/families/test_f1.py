"""F1 — hedge ya hisa kwenye fix ya mwisho wa mwezi — DOCTRINE §4, §9, §11.

Mitego minne, yote ikipimwa hapa:

```
Σw = 0            →  bila hiyo ni bet ya dola, si ya uwiano
upande wa pair    →  kuuza dola ni BUY kwa EURUSD, SELL kwa USDJPY
thamani ya pip    →  sheria TATU tofauti kwa symbols sita
ishara ya lazima  →  bila hisa, F1 haiwezi kuendeshwa hata kidogo
```
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.events.clock import LONDON_FIX
from src.families import f1
from src.families.base import FamilyError
from src.portfolio.basket import BUY, SELL
from src.portfolio.regime import MONTH_END_FIX, TURN_OF_YEAR, regime_of


def siku_zote(a: date, b: date) -> list[date]:
    out, d = [], a
    while d <= b:
        out.append(d)
        d += timedelta(days=1)
    return out


MIAKA_NANE = siku_zote(date(2018, 1, 1), date(2025, 12, 31))
MWENDO = lambda d, s: 10.0                                     # noqa: E731


# ===========================================================================
# Tangazo
# ===========================================================================


def test_sehemu_zote_SITA_zimeandikwa():
    d = f1.DECLARATION
    for sehemu in ("nanga", "mwelekeo", "kuingia", "stop", "kutoka", "ukubwa"):
        assert getattr(d, sehemu).strip(), sehemu
    assert d.symbols == f1.SYMBOLS and len(d.symbols) == 6


def test_regimes_ni_MBILI_ili_31_Desemba_iingie():
    """31 Desemba ni siku ya mwisho ya mwezi NA iko kwenye dirisha la mwisho
    wa mwaka. Mekanizimu upo siku hiyo — benchmarks zinapimwa — kwa hiyo
    kuitoa kungepoteza tukio moja kati ya 99 kwa sheria isiyohusika."""
    assert set(f1.DECLARATION.eligible_regimes) == {MONTH_END_FIX, TURN_OF_YEAR}
    d = date(2021, 12, 31)
    assert regime_of(d) == TURN_OF_YEAR
    assert d in f1.eligible_days(MIAKA_NANE)


def test_matukio_ni_karibu_99_si_594():
    """Legs sita kwa tarehe moja ni uchunguzi MMOJA: fix ile ile, saa ile
    ile, mtiririko ule ule. Kipimo 2018–2025: **96**."""
    hai = f1.eligible_days(MIAKA_NANE)
    assert len(hai) == 96, len(hai)
    assert len({(d.year, d.month) for d in hai}) == 96          # moja kwa mwezi


def test_dirisha_linazunguka_fix():
    """Mtiririko unatekelezwa KWENYE fix, kwa hiyo dirisha lazima lilizunguke:
    kuingia kabla halijaanza, kutoka baada halijaisha."""
    d = date(2021, 6, 30)
    s, = f1.sessions_for(d)
    fix = LONDON_FIX.at(d)
    assert s.entry_at == fix - timedelta(minutes=60)
    assert s.exit_at == fix + timedelta(minutes=15)
    assert s.hours == pytest.approx(1.25)


# ===========================================================================
# Σw = 0 — mtego wa kwanza
# ===========================================================================


def test_ishara_isiyosawazishwa_INALIPUKA():
    """Bila Σw = 0, F1 ni bet ya mwelekeo wa dola yenye legs sita — kitu
    tofauti kabisa, chenye `N_eff ≈ 1` badala ya sita."""
    with pytest.raises(FamilyError, match="haujasawazishwa"):
        f1.Signal(weights={s: 1.0 for s in f1.SYMBOLS})


def test_ishara_iliyosawazishwa_INAKUBALIKA():
    w = {"EURUSD": 1.0, "GBPUSD": 0.5, "AUDUSD": -0.5,
         "USDJPY": -1.0, "USDCHF": 0.3, "USDCHF2": None}
    w.pop("USDCHF2")
    w["USDCAD"] = -0.3
    s = f1.Signal(weights=w)
    assert sum(s.weights.values()) == pytest.approx(0.0)
    assert s.gross == pytest.approx(3.6)


def test_kikapu_kilichosawazishwa_kina_net_weight_SIFURI():
    """`net_weight` ni mfiduo wa dola uliobaki. Sifuri = hakuna bet ya dola."""
    k, = f1.baskets([date(2021, 6, 30)], move_pips=MWENDO,
                    signal=f1.PLACEHOLDER)
    assert k.net_weight == pytest.approx(0.0)
    assert k.gross_weight == pytest.approx(6.0)


def test_symbol_isiyojulikana_INALIPUKA():
    with pytest.raises(FamilyError, match="hazijulikani"):
        f1.Signal(weights={"EURGBP": 1.0, "EURUSD": -1.0})


# ===========================================================================
# Upande wa pair — mtego wa pili
# ===========================================================================


@pytest.mark.parametrize("symbol,upande", [
    ("EURUSD", BUY), ("GBPUSD", BUY), ("AUDUSD", BUY),
    ("USDJPY", SELL), ("USDCHF", SELL), ("USDCAD", SELL)])
def test_kuuza_dola_kunatoa_upande_sahihi(symbol, upande):
    """Dola ikiwa NUKUU (EURUSD), kuuza dola ni KUNUNUA pair; ikiwa MSINGI
    (USDJPY), ni KUUZA. Kuchanganya kungegeuza nusu ya kikapu."""
    assert f1.side_for(symbol, +1.0) == upande
    assert f1.side_for(symbol, -1.0) != upande


def test_uzito_SIFURI_hauna_upande():
    with pytest.raises(FamilyError, match="sifuri"):
        f1.side_for("EURUSD", 0.0)


def test_legs_zinabeba_ishara_ya_DOLA_si_ya_pair():
    """`Leg.weight` ina ishara ya upande wa dola; `side` ina ya pair.
    Utekelezaji unatumia `side` na `strength`, kwa hiyo hakuna kuhesabu
    mara mbili — na `net_weight` inabaki na maana."""
    k, = f1.baskets([date(2021, 6, 30)], move_pips=MWENDO,
                    signal=f1.PLACEHOLDER)
    kwa_symbol = {l.symbol: l for l in k.legs}
    assert kwa_symbol["EURUSD"].weight > 0 and kwa_symbol["EURUSD"].side == BUY
    # USDJPY: uzito wa dola hasi (kununua dola) → kununua pair.
    assert kwa_symbol["USDJPY"].weight < 0 and kwa_symbol["USDJPY"].side == BUY


# ===========================================================================
# Thamani ya pip — mtego wa tatu
# ===========================================================================


def test_sheria_TATU_za_thamani_ya_pip():
    """Kuweka `$10` kwa zote kungekosea USDCHF kwa ~12% na USDJPY kwa ~33%."""
    assert f1.pip_value("EURUSD", 1.10) == pytest.approx(10.0)
    assert f1.pip_value("GBPUSD", 1.30) == pytest.approx(10.0)
    assert f1.pip_value("USDJPY", 150.0) == pytest.approx(6.667, rel=1e-3)
    assert f1.pip_value("USDCHF", 0.90) == pytest.approx(11.111, rel=1e-3)
    assert f1.pip_value("USDCAD", 1.35) == pytest.approx(7.407, rel=1e-3)


def test_pip_ya_JPY_ni_MARA_100_ya_nyingine():
    assert f1.PIPS["USDJPY"] == 0.01
    assert all(f1.PIPS[s] == 0.0001 for s in f1.SYMBOLS if s != "USDJPY")


def test_bei_isiyo_chanya_INALIPUKA():
    with pytest.raises(FamilyError, match="chanya"):
        f1.pip_value("USDJPY", 0.0)


# ===========================================================================
# Ishara ni ya lazima — mtego wa nne
# ===========================================================================


def test_baskets_HAIWEZI_kuitwa_bila_ishara():
    """Bila utendaji wa hisa hakuna njia ya kujua ni nani anauza nini.
    "Kwa uzito sawa" si F1; ni bet ya dola isiyo na mekanizimu."""
    with pytest.raises(TypeError):
        f1.baskets([date(2021, 6, 30)], move_pips=MWENDO)


def test_PLACEHOLDER_inajitangaza():
    """Ipo kwa lango pekee. `σ` na gharama hazitegemei ishara, kwa hiyo
    uwezekano wa kupimika unajulikana kabla ya data ya hisa."""
    assert f1.PLACEHOLDER.placeholder is True
    assert sum(f1.PLACEHOLDER.weights.values()) == pytest.approx(0.0)
    assert f1.Signal(weights={"EURUSD": 1.0, "USDJPY": -1.0}).placeholder is False


def test_siku_isiyo_na_ishara_HAIZALISHI_kikapu():
    assert f1.baskets([date(2021, 6, 30)], move_pips=MWENDO,
                      signal=lambda d: None) == []


# ===========================================================================
# Atomiki — kikapu ni cha yote-au-hakuna
# ===========================================================================


def test_leg_MOJA_ikikosa_mwendo_kikapu_KIZIMA_kinasimama():
    """Legs tano si F1 iliyopunguzwa — ni strategy nyingine yenye mwelekeo
    wa dola usiokusudiwa (kipimo cha 2026-09-07: leg dhaifu ilikataliwa
    99/99, ikijilimbikizia kikapu)."""
    bila_moja = lambda d, s: None if s == "USDCHF" else 10.0   # noqa: E731
    assert f1.baskets([date(2021, 6, 30)], move_pips=bila_moja,
                      signal=f1.PLACEHOLDER) == []


def test_vikapu_ni_ATOMIKI_na_vina_kipaumbele_cha_JUU():
    """Matukio 99 pekee: kupoteza moja ni 1% ya ushahidi, dhidi ya 0.05%
    kwa F0. Kwa hiyo F1 inapewa nafasi kwanza."""
    k, = f1.baskets([date(2021, 6, 30)], move_pips=MWENDO,
                    signal=f1.PLACEHOLDER)
    assert k.atomic is True
    assert k.priority == f1.PRIORITY == 1
    from src.families import f0, gotobi
    assert f1.PRIORITY < gotobi.PRIORITY < f0.PRIORITY


def test_kila_symbol_ina_STOP_yake():
    """Volatility inatofautiana kati ya symbols, kwa hiyo stop inatofautiana."""
    kwa_symbol = {"EURUSD": 8.0, "GBPUSD": 12.0, "AUDUSD": 9.0,
                  "USDJPY": 15.0, "USDCHF": 7.0, "USDCAD": 10.0}
    k, = f1.baskets([date(2021, 6, 30)],
                    move_pips=lambda d, s: kwa_symbol[s],
                    signal=f1.PLACEHOLDER)
    for leg in k.legs:
        assert leg.sl_pips == pytest.approx(
            f1.SL_MOVE_MULT * kwa_symbol[leg.symbol])
    assert len({l.sl_pips for l in k.legs}) == 6


def test_madirisha_ya_kusoma_ni_MAWILI_kwa_tukio():
    v = f1.baskets([date(2021, 6, 30)], move_pips=MWENDO,
                   signal=f1.PLACEHOLDER)
    assert len(f1.windows_to_read(v)) == 2
