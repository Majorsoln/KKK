"""Familia tatu za null — DOCTRINE §9.2, R15.

Kasoro ya data bandia haijionyeshi kama kosa. Inajionyesha kama **sakafu**, na
sakafu isiyo sahihi inapitisha au inakataa kila kitu kilichokuja baada yake bila
mtu kujua. Kwa hiyo tests hizi zinapima mambo mawili tu, lakini kwa kila familia:

* **kinachohifadhiwa** kinahifadhiwa kweli — la sivyo sakafu ni ya soko jingine
* **kinachovunjwa** kinavunjwa kweli — la sivyo edge halisi inaingia kwenye null,
  na sakafu inapanda hadi hakuna strategy inayoweza kuivuka
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.bars import check_ohlc
from src.validation import surrogates as SG

N = 3_000


def _returns(n=N, *, seed=7, vol=3e-4):
    return np.random.default_rng(seed).normal(0, vol, n)


def _ticks(r=None, *, spread_pips=1.2, n=N, seed=7):
    """Ticks za bid/ask; spread inategemea |return| — kama sokoni."""
    r = _returns(n, seed=seed) if r is None else np.asarray(r)
    mid = 1.10 * np.exp(np.cumsum(np.concatenate([[0.0], r])))
    absr = np.abs(np.concatenate([[0.0], r]))
    spread = (spread_pips + 8_000 * absr) * 1e-4
    return pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=len(mid), freq="1min", tz="UTC"),
        "bid": mid - spread / 2.0,
        "ask": mid + spread / 2.0,
    })


def _bars(n=N, *, seed=7):
    r = _returns(n, seed=seed)
    close = 1.10 * np.exp(np.cumsum(np.concatenate([[0.0], r])))
    rng = np.random.default_rng(seed + 1)
    wick = np.abs(rng.normal(0, 2e-4, len(close)))
    open_ = close * (1 + rng.normal(0, 1e-4, len(close)))
    return pd.DataFrame({
        "open": open_,
        "high": np.maximum(open_, close) * (1 + wick),
        "low": np.minimum(open_, close) * (1 - wick),
        "close": close,
        "spread_p50": 1.2 + 100 * wick,
        "n_ticks": rng.integers(20, 300, len(close)),
    }, index=pd.date_range("2020-01-01", periods=len(close), freq="1h", tz="UTC"))


def _mid(frame):
    return ((frame["bid"] + frame["ask"]) / 2.0).to_numpy()


def _acf1(x):
    x = np.asarray(x, dtype=float)
    xc = x - x.mean()
    return float(xc[:-1] @ xc[1:] / (xc @ xc))


# ===========================================================================
# Mkataba wa pamoja — familia zote tatu
# ===========================================================================


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_schema_haibadiliki(family):
    src = _ticks()
    out = SG.make(src, family, seed=1).frame
    assert list(out.columns) == list(src.columns)
    assert len(out) == len(src)


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_SAA_hazibadiliki(family):
    """Tunavunja utabirikaji, si kalenda. Sessions na wikendi ni za kweli."""
    src = _ticks()
    out = SG.make(src, family, seed=1).frame
    assert out["timestamp"].equals(src["timestamp"])


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_bei_inabaki_CHANYA(family):
    """Returns ni za log; bei hasi isingekuwa kosa linaloonekana — ingekuwa jibu."""
    out = SG.make(_ticks(), family, seed=2).frame
    assert (out["bid"] > 0).all() and (out["ask"] > 0).all()


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_spread_inasafiri_na_row_yake(family):
    """Mgawanyo wa spread unabaki, na uhusiano wake na |mwendo| pia.

    Spread ikipangwa upya peke yake, gharama ingekuwa nasibu dhidi ya
    volatility — na kila strategy ingeonekana nafuu hasa pale inapoumia zaidi.
    """
    src = _ticks()
    out = SG.make(src, family, seed=3).frame

    s0 = (src["ask"] - src["bid"]).to_numpy()
    s1 = (out["ask"] - out["bid"]).to_numpy()
    for q in (0.10, 0.50, 0.90, 0.99):
        assert np.quantile(s1, q) == pytest.approx(np.quantile(s0, q), rel=0.05), (
            f"mgawanyo wa spread umebadilika kwenye q{q}"
        )

    r1 = np.diff(np.log(_mid(out)))
    rho = np.corrcoef(np.abs(r1), s1[1:])[0, 1]
    assert rho > 0.5, f"uhusiano spread↔|mwendo| umevunjika (rho {rho:.2f})"


@pytest.mark.parametrize("family", (SG.REGIME, SG.SURROGATE))
def test_spread_ni_ZILE_ZILE_pale_rows_zinapopangwa_upya(family):
    """Familia hizi zinapanga upya; hazichukui kwa kurudia. Multiset ni ile ile.

    `block_resample` inachukua **kwa kurudia** kwa ufafanuzi wake, kwa hiyo rows
    zingine zinajirudia na multiset inabadilika — ndiyo maana ukaguzi mkali ni
    wa hizi mbili pekee.
    """
    src = _ticks()
    out = SG.make(src, family, seed=3).frame
    s0 = np.sort((src["ask"] - src["bid"]).to_numpy())
    s1 = np.sort((out["ask"] - out["bid"]).to_numpy())
    assert np.allclose(s0, s1, rtol=1e-12)


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_seed_ile_ile_inatoa_matokeo_yale_yale(family):
    a = SG.make(_ticks(), family, seed=99).frame
    b = SG.make(_ticks(), family, seed=99).frame
    pd.testing.assert_frame_equal(a, b)


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_seed_tofauti_inatoa_matokeo_tofauti(family):
    a = _mid(SG.make(_ticks(), family, seed=1).frame)
    b = _mid(SG.make(_ticks(), family, seed=2).frame)
    assert not np.allclose(a, b)


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_data_bandia_SI_ile_ile(family):
    """Familia inayorudisha ingizo kama lilivyo ingeweka edge halisi ndani ya null."""
    src = _ticks()
    out = SG.make(src, family, seed=5).frame
    assert not np.allclose(_mid(src), _mid(out))


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_bars_zinabaki_OHLC_halali(family):
    """Umbo la bar linasafiri kama nyongeza za log juu ya `close` yake yenyewe."""
    out = SG.make(_bars(), family, seed=4).frame
    ok, bad = check_ohlc(out)
    assert ok, f"bars {bad} zimevunja high/low"


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_mgawanyo_wa_returns_unakaribiana(family):
    """Null inahifadhi tabia za kitakwimu — la sivyo ni soko jingine kabisa."""
    src = _ticks()
    r0 = np.diff(np.log(_mid(src)))
    r1 = np.diff(np.log(_mid(SG.make(src, family, seed=6).frame)))
    assert r1.std() == pytest.approx(r0.std(), rel=0.15)


# ===========================================================================
# A · block_resample
# ===========================================================================


def test_block_inahifadhi_autocorrelation_NDANI_ya_block():
    """Momentum ya bars chache inanusurika — ndiyo ufafanuzi wa familia hii.

    Na ndiyo maana sakafu ni `max`: strategy inayoishi kwa momentum fupi
    itafanya kazi ndani ya null hii, kwa hiyo sakafu inayotoka hapa ni **kubwa**,
    na hiyo ndiyo bar ambayo strategy hiyo italazimika kuivuka.
    """
    rng = np.random.default_rng(11)
    r = np.zeros(N)
    for i in range(1, N):
        r[i] = 0.6 * r[i - 1] + rng.normal(0, 3e-4)

    src = _ticks(r)
    out = SG.make(src, SG.BLOCK, seed=1, block_len=100).frame
    a0, a1 = _acf1(np.diff(np.log(_mid(src)))), _acf1(np.diff(np.log(_mid(out))))
    assert a1 > 0.5 * a0, f"autocorrelation imepotea: {a0:.2f} -> {a1:.2f}"


def test_block_inavunja_uhusiano_KATI_ya_blocks():
    """Trend ya masafa marefu haipaswi kunusurika."""
    r = np.full(N, 2e-5) + _returns(N, seed=12, vol=1e-5)
    src = _ticks(r)
    out = SG.make(src, SG.BLOCK, seed=1, block_len=20).frame
    mid = _mid(out)
    # Trend ya awali ni monotone kabisa; ya bandia haipaswi kuwa hivyo... lakini
    # drift chanya inabaki (ipo ndani ya kila block). Kinachopimwa ni kwamba
    # mpangilio wa blocks umebadilika, si ishara ya drift.
    assert not np.allclose(mid, _mid(src))
    assert (np.diff(np.log(mid)) > 0).mean() == pytest.approx(
        (np.diff(np.log(_mid(src))) > 0).mean(), abs=0.05
    )


def test_block_len_unapimwa_hauhaniwi():
    """`n^(1/3)` ni sakafu; ACF inapandisha pale muundo unapoendelea zaidi."""
    huru = _returns(N, seed=13)
    assert SG.measure_block_len(huru) == max(2, int(np.ceil(N ** (1 / 3))))

    rng = np.random.default_rng(14)
    r = np.zeros(N)
    for i in range(1, N):
        r[i] = 0.95 * r[i - 1] + rng.normal(0, 3e-4)
    assert SG.measure_block_len(r) > SG.measure_block_len(huru)


def test_block_indices_zinafunika_mstari_mzima():
    rng = np.random.default_rng(0)
    idx = SG._block_indices(1000, 37, rng)
    assert len(idx) == 1000 and idx.min() >= 0 and idx.max() < 1000


def test_block_ni_ya_MVIRINGO_hakuna_upendeleo_wa_kipindi():
    """Bila kuzungusha, rows za mwisho zingechaguliwa mara chache — na upendeleo
    wa kipindi ungeonekana kama muundo."""
    rng = np.random.default_rng(1)
    hesabu = np.zeros(200)
    for _ in range(400):
        idx = SG._block_indices(200, 20, rng)
        hesabu += np.bincount(idx, minlength=200)
    mwisho, mwanzo = hesabu[-20:].mean(), hesabu[:20].mean()
    assert mwisho == pytest.approx(mwanzo, rel=0.20)


# ===========================================================================
# B · regime_shuffle
# ===========================================================================


def test_regime_mpangilio_wa_regimes_HAUBADILIKI():
    src = _ticks()
    r = np.diff(np.log(_mid(src)))
    labels = SG.default_regime(r)
    out = SG.make(src, SG.REGIME, seed=1, regime=labels).frame

    # Regime ya bandia inahesabiwa kwa data mpya; urefu wa mfululizo ni ule ule
    # kwa sababu rows zilipangwa upya NDANI ya mipaka pekee.
    assert len(labels) == len(r)
    r1 = np.diff(np.log(_mid(out)))
    kubwa = np.abs(r1)[np.array(labels) == SG.HIGH].mean()
    ndogo = np.abs(r1)[np.array(labels) == SG.LOW].mean()
    assert kubwa > ndogo, "vipindi vya msukosuko havijabaki mahali pake"


def test_regime_inavunja_mfuatano_NDANI_ya_regime():
    rng = np.random.default_rng(21)
    r = np.zeros(N)
    for i in range(1, N):
        r[i] = 0.7 * r[i - 1] + rng.normal(0, 3e-4)
    src = _ticks(r)
    out = SG.make(src, SG.REGIME, seed=1).frame
    a0, a1 = _acf1(np.diff(np.log(_mid(src)))), _acf1(np.diff(np.log(_mid(out))))
    assert a1 < 0.5 * a0, f"mfuatano wa ndani umenusurika: {a0:.2f} -> {a1:.2f}"


def test_regime_haichanganyi_vipindi_viwili():
    labels = ["LOW"] * 5 + ["HIGH"] * 5
    idx = SG._regime_indices(labels, np.random.default_rng(0))
    assert set(idx[:5]) == set(range(5))
    assert set(idx[5:]) == set(range(5, 10))


def test_regime_iliyotolewa_na_mtumiaji_lazima_ilingane():
    with pytest.raises(SG.SurrogateError, match="regime"):
        SG.make(_ticks(n=200), SG.REGIME, seed=1, regime=["LOW"] * 10)


def test_default_regime_ina_madarasa_matatu():
    labels = np.array(SG.default_regime(_returns(N)))
    assert set(labels) == {SG.LOW, SG.MID, SG.HIGH}


def _runs(labels):
    lengths, n = [], 1
    for a, b in zip(labels, labels[1:]):
        if a == b:
            n += 1
        else:
            lengths.append(n)
            n = 1
    lengths.append(n)
    return lengths


def test_regime_ni_KIPINDI_si_label_ya_bar_moja():
    """Volatility ya bar moja si regime; ni kelele ya kipimo.

    Ikitumika moja kwa moja, kila mfululizo ni wa urefu 1, shuffle haifanyi
    kitu, na familia B inarudisha ingizo lenyewe — kimya kabisa.
    """
    runs = _runs(SG.default_regime(_returns(N)))
    assert min(runs) >= SG.VOL_WINDOW, f"mfululizo mfupi kuliko dirisha: {min(runs)}"


def test_regime_zisizo_na_uendelevu_zinalipuka():
    """Kinga dhidi ya familia inayorudisha ingizo lenyewe."""
    src = _ticks()
    flicker = [SG.LOW if i % 2 else SG.HIGH for i in range(len(src) - 1)]
    with pytest.raises(SG.SurrogateError, match="uendelevu"):
        SG.make(src, SG.REGIME, seed=1, regime=flicker)


def test_merge_unaunganisha_mfululizo_mfupi():
    labels = ["LOW"] * 20 + ["HIGH"] + ["LOW"] * 20
    assert SG._merge_short_runs(labels, 5) == ["LOW"] * 41
    # wa kwanza hana uliotangulia — anaungana na ufuatao
    assert SG._merge_short_runs(["HIGH"] + ["LOW"] * 20, 5) == ["LOW"] * 21


# ===========================================================================
# C · return_surrogate (IAAFT)
# ===========================================================================


def test_iaaft_inahifadhi_MGAWANYO_haswa():
    r = _returns(1024, seed=31)
    y, _ = SG.iaaft(r, np.random.default_rng(0))
    assert np.allclose(np.sort(y), np.sort(r)), "thamani si zile zile"


def test_iaaft_inahifadhi_WIGO_kwa_karibu():
    r = _returns(1024, seed=32)
    y, _ = SG.iaaft(r, np.random.default_rng(0))
    a0, a1 = np.abs(np.fft.rfft(r)), np.abs(np.fft.rfft(y))
    assert np.corrcoef(a0, a1)[0, 1] > 0.97


def test_iaaft_inavunja_AWAMU():
    """Muundo unaotegemea *lini* unapotea; unaotegemea *mara ngapi* unabaki."""
    t = np.arange(1024)
    r = 3e-4 * np.sin(2 * np.pi * t / 64)
    y, _ = SG.iaaft(r, np.random.default_rng(0))
    assert np.corrcoef(r, y)[0, 1] < 0.9


def test_iaaft_inasimama_ranks_zikiganda():
    r = _returns(512, seed=33)
    _, used = SG.iaaft(r, np.random.default_rng(0), iters=500)
    assert used < 500, "hakuna convergence — mizunguko yote imetumika bure"


def test_surrogate_spread_inaambatanishwa_kwa_CHEO():
    """Rows hazihami; spread inafuata cheo cha |return| ili uhusiano ubaki."""
    src = _ticks()
    out = SG.make(src, SG.SURROGATE, seed=1).frame
    s1 = (out["ask"] - out["bid"]).to_numpy()[1:]
    r1 = np.abs(np.diff(np.log(_mid(out))))
    assert np.corrcoef(r1, s1)[0, 1] > 0.9


# ===========================================================================
# Mikataba
# ===========================================================================


def test_familia_isiyojulikana_inalipuka():
    with pytest.raises(SG.SurrogateError, match="familia"):
        SG.make(_ticks(n=200), "shuffle", seed=1)


def test_mstari_mfupi_unalipuka():
    with pytest.raises(SG.SurrogateError, match="rows"):
        SG.make(_ticks(n=SG.MIN_ROWS - 2), SG.BLOCK, seed=1)


def test_frame_isiyo_na_bei_inalipuka():
    frame = pd.DataFrame({"timestamp": pd.date_range("2020-01-01", periods=100, freq="1min"),
                          "x": np.arange(100.0)})
    with pytest.raises(SG.SurrogateError, match="bid"):
        SG.make(frame, SG.BLOCK, seed=1)


def test_bei_isiyo_chanya_inalipuka():
    frame = _ticks(n=200)
    frame.loc[10, "bid"] = -1.0
    frame.loc[10, "ask"] = -0.9
    with pytest.raises(SG.SurrogateError, match="chanya"):
        SG.make(frame, SG.BLOCK, seed=1)


def test_surrogate_inajielezea():
    s = SG.make(_ticks(n=500), SG.BLOCK, seed=1)
    assert s.preserves and s.breaks
    assert "block" in s.render()
    assert s.to_json()["family"] == SG.BLOCK


# ===========================================================================
# Drift ni ya SOKO, si ya generator (2026-09-01)
# ===========================================================================


def _drift(close) -> float:
    """Jumla ya log-returns — kile soko lilifanya kutoka mwanzo hadi mwisho."""
    import numpy as np

    x = np.asarray(close, dtype=float)
    return float(np.log(x[-1] / x[0]))


@pytest.mark.parametrize("family", SG.FAMILIES)
def test_drift_inahifadhiwa_KABISA(family):
    """Data bandia ni soko LILE LILE bila utabirikaji — si soko lingine.

    Kabla ya 2026-09-01, `block_resample` ilikuwa inasampuli blocks kwa
    KURUDIA, kwa hiyo block moja ingeweza kuchukuliwa mara kadhaa na jumla ya
    returns ikawa nasibu. Kipimo (bars 8,000, surrogate 40): drift ya asili
    +0.01268, lakini surrogate zilifika +0.03255 — mwelekeo mara 2.6 ya soko
    halisi.

    Athari: `null_vs_real.py` juu ya EURUSD H1 ilionyesha data bandia ni rahisi
    **mara 1.95** kuliko soko halisi, na `block_resample` ndiyo iliyokuwa
    inafunga sakafu kwa 5 kati ya 6. Sakafu ilikuwa ya soko lenye mwelekeo
    usiokuwepo.
    """
    frame = _bars(600, seed=11)
    asili = _drift(frame["close"])
    for seed in range(6):
        sur = SG.make(frame, family, seed=seed)
        assert _drift(sur.frame["close"]) == pytest.approx(asili, abs=1e-9), (
            f"{family} seed {seed} imebadilisha drift"
        )


def test_block_resample_inatumia_kila_row_MARA_MOJA():
    """Kupanga upya, si kusampuli. Ndicho kinachohifadhi drift kwa ujenzi."""
    import numpy as np

    for seed in range(5):
        idx = SG._block_indices(500, 42, np.random.default_rng(seed))
        assert len(idx) == 500
        assert sorted(idx.tolist()) == list(range(500))


def test_block_resample_inahifadhi_NDANI_na_kuvunja_KATI(  # noqa: N802
):
    """Kuhifadhi drift si kuacha kufanya kazi — jedwali la §9.2 linabaki kweli.

    Familia hii inadai kuhifadhi autocorrelation **ndani** ya block na kuvunja
    uhusiano **kati** ya blocks. Vipimo viwili, kila kimoja kwa upande wake:

    * `acf(1)` — jozi za jirani, karibu zote ndani ya block moja → inabaki
    * `VR(100)` — upeo mrefu kuliko block → inabadilika kwa kiasi kikubwa

    Mwelekeo wa mabadiliko ya `VR` unategemea data: mfululizo unaorudi nyuma
    (`VR < 1`) unapangwa upya na kupanda; unaoendelea (`VR > 1`) unashuka. Dai
    ni **kubadilika**, si kushuka — kudai upande ni kudhani kile data inachofanya.
    """
    import numpy as np

    frame = _bars(1200, seed=3)
    close = frame["close"].to_numpy(dtype=float)
    wimbi = 0.02 * np.sin(np.arange(len(close)) / 200.0 * 2 * np.pi)
    frame = frame.copy()
    for col in ("open", "high", "low", "close"):
        frame[col] = frame[col].to_numpy(dtype=float) + wimbi

    def vr(x, k):
        n = len(x) // k * k
        x = x[:n]
        return float(x.reshape(-1, k).sum(1).var(ddof=1) / (k * x.var(ddof=1)))

    r_asili = np.diff(np.log(frame["close"].to_numpy(dtype=float)))
    r_sur = np.diff(np.log(
        SG.make(frame, SG.BLOCK, seed=2).frame["close"].to_numpy(dtype=float)))

    # KATI ya blocks — imevunjwa
    assert abs(np.log(vr(r_sur, 100) / vr(r_asili, 100))) > 1.0, (
        f"VR(100) {vr(r_asili, 100):.3f} → {vr(r_sur, 100):.3f}: "
        f"muundo wa masafa marefu haujavunjwa"
    )
    # NDANI ya block — imehifadhiwa
    assert _acf1(r_sur) == pytest.approx(_acf1(r_asili), abs=0.05)
