"""Faharasa za hisa na ishara ya F1 — DOCTRINE §4, §11.

Dai kubwa kuliko yote: **hakuna lookahead**. Fix ni 16:00 London; FTSE, STOXX,
S&P na TSX zote zinafunga BAADA yake. Kutumia kufunga kwa siku hiyo kungekuwa
kujua bei ambazo hazijawahi kuwepo — na kosa hilo halingeonekana kwenye
matokeo, lingeonekana kama ishara nzuri isiyo ya kawaida.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.data import indices as IX
from src.families import f1
from src.families import f1_signal as SIG


def andika(path, rows, *, headers=("Date", "Close")):
    mistari = [",".join(headers)]
    mistari += [f"{d.isoformat()},{c}" for d, c in rows]
    path.write_text("\n".join(mistari) + "\n", encoding="utf-8")
    return path


def mfululizo(jina, *, anza=date(2017, 1, 2), n=600, bei=100.0, hatua=0.1):
    siku, out, d = [], [], anza
    while len(siku) < n:
        if d.weekday() < 5:
            siku.append(d)
        d += timedelta(days=1)
    for i, x in enumerate(siku):
        out.append((x, round(bei + i * hatua, 4)))
    return IX.Series(jina, tuple(s for s, _ in out), tuple(c for _, c in out))


# ===========================================================================
# Kusoma
# ===========================================================================


def test_CSV_ya_Stooq_inasomeka(tmp_path):
    rows = [(date(2020, 1, d), 100.0 + d) for d in range(1, 29)] * 10
    rows = sorted({r[0]: r[1] for r in
                   [(date(2020, 1, 1) + timedelta(days=i), 100.0 + i)
                    for i in range(300)]}.items())
    p = andika(tmp_path / "SP500.csv", rows,
               headers=("Date", "Open", "High", "Low", "Close", "Volume"))
    # safu za ziada zisizo na thamani zinaongezwa ili DictReader ilingane
    p.write_text("Date,Open,High,Low,Close,Volume\n" + "\n".join(
        f"{d.isoformat()},1,1,1,{c},1" for d, c in rows) + "\n",
        encoding="utf-8")
    s = IX.read_csv(p)
    assert len(s.days) == 300 and s.name == "SP500"
    assert s.closes[0] == 100.0


def test_rows_CHACHE_MNO_zinalipuka(tmp_path):
    """Mfululizo mfupi hauwezi kutoa ishara ya mwezi kwa mwezi. Kulipuka ni
    bora kuliko kutoa ishara kwa miezi michache na kunyamaza kwa mingine."""
    rows = [(date(2020, 1, 1) + timedelta(days=i), 100.0 + i) for i in range(50)]
    p = andika(tmp_path / "FUPI.csv", rows)
    with pytest.raises(IX.IndexError_, match="chini ya"):
        IX.read_csv(p)


def test_bei_isiyo_chanya_INARUKWA(tmp_path):
    rows = [(date(2020, 1, 1) + timedelta(days=i), 100.0 + i) for i in range(300)]
    rows[10] = (rows[10][0], 0.0)
    p = andika(tmp_path / "X.csv", rows)
    s = IX.read_csv(p)
    assert len(s.days) == 299
    assert rows[10][0] not in s.days


def test_safu_isiyojulikana_INALIPUKA(tmp_path):
    p = tmp_path / "Y.csv"
    p.write_text("Tarehe,Bei\n2020-01-01,100\n", encoding="utf-8")
    with pytest.raises(IX.IndexError_, match="safu ya tarehe"):
        IX.read_csv(p)


# ===========================================================================
# `asof` — kila soko lina sikukuu zake
# ===========================================================================


def test_asof_inarudisha_kufunga_kwa_MWISHO_kabla():
    """Kila soko lina sikukuu zake. Kuomba tarehe isiyokuwepo kunarudisha
    kufunga kwa mwisho kabla yake — ndivyo mwekezaji halisi anavyoona soko."""
    s = mfululizo("X")
    ijumaa = next(d for d in s.days if d.weekday() == 4)
    i = s.days.index(ijumaa)
    assert s.asof(ijumaa) == s.closes[i]
    # Jumamosi na Jumapili hazipo kwenye mfululizo; zinarudisha ya Ijumaa.
    assert s.asof(ijumaa + timedelta(days=1)) == s.closes[i]
    assert s.asof(ijumaa + timedelta(days=2)) == s.closes[i]
    # Jumatatu inayofuata ni row inayofuata.
    assert s.asof(ijumaa + timedelta(days=3)) == s.closes[i + 1]


def test_asof_KABLA_ya_mfululizo_ni_None():
    s = mfululizo("X", anza=date(2020, 1, 1))
    assert s.asof(date(2019, 1, 1)) is None


def test_asof_BAADA_ya_mfululizo_inarudisha_ya_mwisho():
    s = mfululizo("X")
    assert s.asof(s.end + timedelta(days=365)) == s.closes[-1]


# ===========================================================================
# LOOKAHEAD — dai kubwa kuliko yote
# ===========================================================================


def test_kufunga_kwa_SIKU_YA_FIX_hakutumiki():
    """Kipimo kinachotofautisha: mfululizo unaoruka kwa 50% siku ya fix
    PEKEE. Ishara ikiubadilika, inakuwa inaisoma."""
    d = date(2021, 6, 30)
    kawaida = mfululizo("EU", anza=date(2020, 1, 1))

    # Nakala yenye mruko mkubwa siku ya fix.
    i = kawaida.days.index(d)
    bei = list(kawaida.closes)
    bei[i] *= 1.5
    yenye_mruko = IX.Series("EU", kawaida.days, tuple(bei))

    r1 = SIG.returns_for(d, {"EU": kawaida})
    r2 = SIG.returns_for(d, {"EU": yenye_mruko})
    assert r1 is not None and r2 is not None
    assert r1.by_index["EU"] == pytest.approx(r2.by_index["EU"])
    assert r1.end == d - timedelta(days=1)


def test_lag_SIFURI_inalipuka():
    """Hakuna njia ya kuomba kufunga kwa siku ya fix, hata kwa bahati mbaya."""
    with pytest.raises(Exception, match="lag_days"):
        SIG.returns_for(date(2021, 6, 30), {"EU": mfululizo("EU")}, lag_days=0)


def test_dirisha_linaanzia_mwisho_wa_mwezi_ULIOPITA():
    d = date(2021, 6, 30)
    r = SIG.returns_for(d, {"EU": mfululizo("EU", anza=date(2020, 1, 1))})
    assert r.start == date(2021, 5, 31)
    assert r.end == date(2021, 6, 29)


# ===========================================================================
# Ishara — mekanizimu ikiwa namba
# ===========================================================================


def _series_zenye_utendaji(utendaji: dict[str, float], d: date):
    """Mfululizo ambao kila faharasa inapanda kwa `utendaji` ndani ya mwezi."""
    out = {}
    for jina, r in utendaji.items():
        siku, x = [], date(2020, 1, 1)
        while len(siku) < 500:
            if x.weekday() < 5:
                siku.append(x)
            x += timedelta(days=1)
        mwanzo = SIG.month_start(d)
        bei = []
        for s in siku:
            bei.append(100.0 * (1.0 + r) if s > mwanzo else 100.0)
        out[jina] = IX.Series(jina, tuple(siku), tuple(bei))
    return out


def test_soko_lililofanya_VIZURI_linauzwa():
    """Mwekezaji wa Marekani anayeshikilia hisa za nchi hiyo anahitaji hedge
    kubwa zaidi → anauza sarafu yake → ananunua dola.

    Uzito wa upande wa dola unakuwa **hasi** (kununua dola) kwa soko
    lililofanya vizuri kuliko wenzake.
    """
    d = date(2021, 6, 30)
    s = _series_zenye_utendaji({"STOXX50": 0.10, "FTSE100": 0.0,
                                "NIKKEI225": 0.0, "TSX": 0.0}, d)
    ishara = SIG.signal_for(d, s)
    assert ishara is not None
    assert ishara.weights["EURUSD"] == pytest.approx(-1.0)   # euro inauzwa
    assert all(ishara.weights[x] > 0 for x in
               ("GBPUSD", "USDJPY", "USDCAD"))


def test_ishara_INASAWAZISHWA():
    d = date(2021, 6, 30)
    s = _series_zenye_utendaji({"STOXX50": 0.08, "FTSE100": 0.02,
                                "NIKKEI225": -0.03, "TSX": 0.05}, d)
    ishara = SIG.signal_for(d, s)
    assert sum(ishara.weights.values()) == pytest.approx(0.0, abs=1e-9)
    assert max(abs(w) for w in ishara.weights.values()) == pytest.approx(1.0)
    assert set(ishara.weights) == set(f1.QUALIFIED)


def test_Marekani_INATOKA_wakati_wa_kusawazisha():
    """`z = r_US − r_C`; baada ya kusawazisha, `r_US` inafutika kabisa.
    Kwa hiyo faharasa ya Marekani haiingii kwenye trade — inabaki kwa
    ukaguzi pekee."""
    d = date(2021, 6, 30)
    msingi = {"STOXX50": 0.08, "FTSE100": 0.02, "NIKKEI225": -0.03, "TSX": 0.05}
    a = SIG.signal_for(d, _series_zenye_utendaji(msingi, d))
    # Kuongeza kitu kimoja kwa ZOTE hakubadilishi ishara hata kidogo.
    zaidi = {k: v + 0.20 for k, v in msingi.items()}
    b = SIG.signal_for(d, _series_zenye_utendaji(zaidi, d))
    for s in f1.QUALIFIED:
        assert a.weights[s] == pytest.approx(b.weights[s], abs=1e-6)


def test_masoko_yakifanana_KABISA_hakuna_ishara():
    d = date(2021, 6, 30)
    s = _series_zenye_utendaji({k: 0.05 for k in
                                ("STOXX50", "FTSE100", "NIKKEI225", "TSX")}, d)
    assert SIG.signal_for(d, s) is None


def test_faharasa_MOJA_ikikosekana_hakuna_ishara():
    """Kikapu ni cha yote-au-hakuna: ishara isiyokamilika si ishara."""
    d = date(2021, 6, 30)
    s = _series_zenye_utendaji({"STOXX50": 0.1, "FTSE100": 0.0,
                                "NIKKEI225": 0.0, "TSX": 0.0}, d)
    s["TSX"] = IX.Series("TSX", s["TSX"].days[300:], s["TSX"].closes[300:]) \
        if len(s["TSX"].days) >= 500 else s["TSX"]
    del s["TSX"]
    with pytest.raises(Exception, match="hazipo"):
        SIG.signal_for(d, s)


def test_ishara_inaingia_kwenye_KIKAPU_cha_F1():
    """Kipimo cha mwisho: faharasa → ishara → kikapu chenye legs nne."""
    d = date(2021, 6, 30)
    s = _series_zenye_utendaji({"STOXX50": 0.08, "FTSE100": 0.02,
                                "NIKKEI225": -0.03, "TSX": 0.05}, d)
    ishara = SIG.signal_for(d, s)
    k, = f1.baskets([d], move_pips=lambda day, sym: 10.0, signal=ishara)
    assert len(k.legs) == 4
    assert k.net_weight == pytest.approx(0.0, abs=1e-9)
    # STOXX ilifanya vizuri kuliko wote → euro inauzwa → EURUSD inauzwa.
    kwa_symbol = {l.symbol: l for l in k.legs}
    assert kwa_symbol["EURUSD"].side == "SELL"
