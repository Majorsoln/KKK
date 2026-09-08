"""Kusoma ticks kwa madirisha — DOCTRINE §7.4.

Dai kuu ni kwamba **kile kinachorudishwa ni kile kilichoombwa, na si zaidi**.
Msomaji anayerudisha rows za ziada hafanyi kosa linaloonekana: VWAP yake
inakuwa ya dirisha pana kuliko lililotangazwa, na bei inakuwa laini kuliko
soko. Kwa hiyo mipaka inapimwa hapa kwa tick moja moja.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data import ticks as T


def _ticks(start: datetime, n: int, *, freq="1s", bid=1.2000, spread=0.00016):
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"timestamp": idx, "bid": bid, "ask": bid + spread})


def andika(root: Path, symbol: str, day, frame, *, provenance="aggregator",
           toleo="A"):
    """Andika partition kwa muundo wa PD: `provenance=…/symbol=…/year=/month=/day=`."""
    folda = (root / f"provenance={provenance}" / f"symbol={symbol}"
             / f"year={day.year}" / f"month={day.month:02d}" / f"day={day.day:02d}")
    folda.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if toleo == "B":
        out = out.rename(columns={"timestamp": "ts"})
        out["bid_volume"] = 1.0
        out["ask_volume"] = 1.0
    out.to_parquet(folda / "ticks.parquet", index=False)
    return folda / "ticks.parquet"


@pytest.fixture
def L0(tmp_path):
    root = tmp_path / "L0_raw"
    siku = [datetime(2021, 6, d, tzinfo=timezone.utc).date() for d in (14, 15, 16)]
    for d in siku:
        # 07:00 → 21:00 UTC: inashughulikia nanga zote nne za F0 kwa siku
        # ya kiangazi (08:00 BST = 07:00 UTC; 16:30 EDT = 20:30 UTC).
        andika(root, "EURUSD", d,
               _ticks(datetime(d.year, d.month, d.day, 7, 0, tzinfo=timezone.utc),
                      3600 * 14))
    return root


# ===========================================================================
# Kutambua kilichopo
# ===========================================================================


def test_symbol_inatambulika_kutoka_NJIA(L0):
    inv = T.discover(L0)
    assert inv.symbols == ["EURUSD"]
    assert len(inv.partitions) == 3


def test_neno_SYMBOL_halihesabiwi_kama_pair(tmp_path):
    """`symbol=EURUSD` ina herufi sita kubwa mbili: `SYMBOL` na `EURUSD`.
    Bila ukaguzi wa sarafu, kila partition ingewekwa chini ya "SYMBOL"."""
    d = datetime(2021, 6, 14, tzinfo=timezone.utc).date()
    andika(tmp_path, "EURUSD", d,
           _ticks(datetime(2021, 6, 14, 8, 0, tzinfo=timezone.utc), 60))
    assert T.discover(tmp_path).symbols == ["EURUSD"]


def test_kipindi_kinasomeka_kutoka_tags(L0):
    inv = T.discover(L0)
    assert sorted(p.period for p in inv.partitions) == [
        "2021-06-14", "2021-06-15", "2021-06-16"]


def test_tarehe_isiyosomeka_INALIPUKA_si_kupuuzwa(tmp_path):
    """`day=29 (1)` ni nakala ya Windows. Ikipakiwa kimya, ticks za siku hiyo
    zinahesabiwa maradufu na spread yake inapata uzito maradufu."""
    folda = tmp_path / "symbol=EURUSD" / "year=2021" / "month=06" / "day=29 (1)"
    folda.mkdir(parents=True)
    _ticks(datetime(2021, 6, 29, 8, 0, tzinfo=timezone.utc), 60).to_parquet(
        folda / "ticks.parquet", index=False)
    inv = T.discover(tmp_path)
    with pytest.raises(T.TickError, match="isiyosomeka"):
        inv.of("EURUSD")


def test_vyanzo_viwili_HAVICHANGANYWI(tmp_path):
    d = datetime(2021, 6, 14, tzinfo=timezone.utc).date()
    f = _ticks(datetime(2021, 6, 14, 8, 0, tzinfo=timezone.utc), 60)
    andika(tmp_path, "EURUSD", d, f, provenance="aggregator")
    andika(tmp_path, "EURUSD", d, f, provenance="broker")
    with pytest.raises(T.TickError, match="provenance"):
        T.discover(tmp_path).of("EURUSD")
    # Kuchagua kimoja kunatatua.
    assert len(T.discover(tmp_path, provenance="broker").of("EURUSD")) == 1


# ===========================================================================
# Schema mbili, frame moja
# ===========================================================================


def test_toleo_B_linanormalizwa_kuwa_schema_MOJA(tmp_path):
    d = datetime(2021, 6, 14, tzinfo=timezone.utc).date()
    andika(tmp_path, "GBPJPY", d,
           _ticks(datetime(2021, 6, 14, 8, 0, tzinfo=timezone.utc), 600),
           toleo="B")
    inv = T.discover(tmp_path)
    out = T.read_windows(inv, "GBPJPY",
                         [(datetime(2021, 6, 14, 8, 0, tzinfo=timezone.utc), 60)])
    assert list(out.columns)[:3] == ["timestamp", "bid", "ask"]
    assert len(out) == 60


def test_frame_isiyo_na_ASK_inalipuka():
    frame = pd.DataFrame({"timestamp": pd.date_range(
        "2021-06-14", periods=3, freq="1s", tz="UTC"), "bid": 1.2})
    with pytest.raises(T.TickError, match="ask"):
        T.normalize(frame, source="x")


# ===========================================================================
# Madirisha — dai kuu
# ===========================================================================


def test_dirisha_linarudisha_HASA_sekunde_zilizoombwa(L0):
    inv = T.discover(L0)
    anza = datetime(2021, 6, 15, 8, 0, tzinfo=timezone.utc)
    out = T.read_windows(inv, "EURUSD", [(anza, 300)])
    assert len(out) == 300
    assert out["timestamp"].min() == anza
    assert out["timestamp"].max() == anza + timedelta(seconds=299)


def test_mpaka_wa_juu_HAUJUMUISHWI(L0):
    """`[mwanzo, mwisho)` — tick ya sekunde ya 300 ni ya dirisha lingine."""
    inv = T.discover(L0)
    anza = datetime(2021, 6, 15, 8, 0, tzinfo=timezone.utc)
    out = T.read_windows(inv, "EURUSD", [(anza, 300)])
    assert (anza + timedelta(seconds=300)) not in set(out["timestamp"])


def test_madirisha_manne_yanarudisha_rows_MANNE_x_300(L0):
    """Umbo la siku ya F0: ncha nne, dakika 20 kati ya 1,440."""
    inv = T.discover(L0)
    saa = [8, 12, 16, 20]
    maombi = [(datetime(2021, 6, 15, h, 0, tzinfo=timezone.utc), 300) for h in saa]
    out = T.read_windows(inv, "EURUSD", maombi)
    assert len(out) == 4 * 300
    assert sorted({t.hour for t in out["timestamp"]}) == saa


def test_siku_ZISIZOOMBWA_hazisomwi(L0):
    """Ndio uokoaji wote: partition isiyoguswa na dirisha lolote haifunguliwi."""
    inv = T.discover(L0)
    anza = datetime(2021, 6, 15, 8, 0, tzinfo=timezone.utc)
    out = T.read_windows(inv, "EURUSD", [(anza, 300)])
    assert {t.date() for t in out["timestamp"]} == {anza.date()}


def test_partition_isiyo_na_tarehe_INASOMWA_kwa_tahadhari(tmp_path):
    """Kuruka faili kwa sababu haijatajwa tarehe kungefanya siku zikose ticks
    kimya. Jibu la tahadhari ni kuisoma."""
    folda = tmp_path / "EURUSD"
    folda.mkdir(parents=True)
    _ticks(datetime(2021, 6, 15, 8, 0, tzinfo=timezone.utc), 600).to_parquet(
        folda / "ticks.parquet", index=False)
    inv = T.discover(tmp_path)
    assert inv.partitions[0].period == ""
    out = T.read_windows(
        inv, "EURUSD", [(datetime(2021, 6, 15, 8, 0, tzinfo=timezone.utc), 120)])
    assert len(out) == 120


def test_dirisha_lisilo_na_tick_LINARUDISHA_TUPU(L0):
    """Halikosewi hapa — `clock.vwap` ndiyo inayolipuka, ikiwa na tarehe."""
    inv = T.discover(L0)
    usiku = datetime(2021, 6, 15, 2, 0, tzinfo=timezone.utc)
    assert T.read_windows(inv, "EURUSD", [(usiku, 300)]).empty


def test_maombi_matupu_yanarudisha_frame_yenye_SAFU_sahihi(L0):
    out = T.read_windows(T.discover(L0), "EURUSD", [])
    assert list(out.columns) == ["timestamp", "bid", "ask"] and out.empty


def test_bei_zinabaki_ZILEZILE_baada_ya_kusoma(L0):
    inv = T.discover(L0)
    out = T.read_windows(
        inv, "EURUSD", [(datetime(2021, 6, 15, 8, 0, tzinfo=timezone.utc), 10)])
    assert np.allclose(out["bid"], 1.2000)
    assert np.allclose(out["ask"] - out["bid"], 0.00016)


# ===========================================================================
# Mnyororo: msomaji → nanga za F0 → VWAP
# ===========================================================================


def test_madirisha_ya_F0_yanapatikana_kutoka_kwenye_diski(L0):
    """Kipimo cha mwisho: `windows_to_read` ya F0 → msomaji → `quotes`."""
    from src.events.clock import quotes
    from src.families import f0

    inv = T.discover(L0)
    siku = [datetime(2021, 6, 15, tzinfo=timezone.utc).date()]
    vikapu = f0.baskets(siku, move_pips=lambda d, leg: 20.0)
    assert len(vikapu) == 2

    maombi = f0.windows_to_read(vikapu)
    frame = T.read_windows(inv, "EURUSD", maombi)
    # Ncha nne: kuingia/kutoka kwa leg A, kuingia/kutoka kwa leg B.
    assert len(maombi) == 4 and len(frame) == 4 * 300
    assert [t.strftime("%H:%M") for t, _ in maombi] == [
        "07:00", "16:00", "16:05", "20:30"]

    k = vikapu[0]
    q = quotes(frame, k.entry_at, f0.WINDOW_SECONDS)
    assert q.n_ticks == 300
    assert q.spread_pips(0.0001) == pytest.approx(1.6)
