"""DF-04/DF-03/DF-01 — recorder wa tick feed ya broker.

Spec: `docs/DATA_FEATURE_STANDARD.md` §2 + §2.2 (provenance, "kurekodi kuanzia SASA")
Rejista: DF-04 (recorder inarekodi kila siku ya trading), DF-03 (tag ya provenance),
DF-01 (partition inaandikwa mara moja + SHA256)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.data.manifest import L0Manifest, PROVENANCE_BROKER
from src.data.mt5_source import ReplayTickSource
from src.data.recorder import RecorderSettings, TickRecorder
from src.data.schema import CANONICAL_COLUMNS, read_partition

MONDAY = datetime(2026, 8, 3, tzinfo=timezone.utc)  # Jumatatu
TUESDAY = MONDAY + timedelta(days=1)
WEDNESDAY = MONDAY + timedelta(days=2)


def ticks_for_days(days, per_day: int = 5, symbol_base: float = 1.09) -> pd.DataFrame:
    rows = []
    for day in days:
        for i in range(per_day):
            stamp = day.replace(hour=9) + timedelta(minutes=i)
            bid = symbol_base + i * 1e-5
            rows.append(
                {
                    "timestamp": stamp,
                    "bid": bid,
                    "ask": bid + 1e-4,
                    "bid_vol": 1.0 + i,
                    "ask_vol": 2.0 + i,
                    "flags": 6,
                    "volume_real": 1.0 + i,
                }
            )
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True).astype("datetime64[us, UTC]")
    return frame


@pytest.fixture
def recorder_factory(cfg, l0_root):
    def _make(frames, now: datetime, symbols=("EURUSD",)):
        settings = RecorderSettings.from_config(cfg)
        settings.symbols = list(symbols)
        source = ReplayTickSource(frames)
        return TickRecorder(source, cfg, settings=settings, clock=lambda: now)

    return _make


def test_recorder_inaandika_partition_kwa_kila_siku_ya_trading(recorder_factory, l0_root):
    """DF-04: kila siku iliyofungwa inapata partition yake — moja, si zaidi."""
    frames = {"EURUSD": ticks_for_days([MONDAY, TUESDAY, WEDNESDAY])}
    recorder = recorder_factory(frames, now=WEDNESDAY.replace(hour=12))
    result = recorder.poll_once()

    assert [w.day for w in result.written] == ["2026-08-03", "2026-08-04"]
    assert all(w.rows == 5 for w in result.written)
    for day in ("2026-08-03", "2026-08-04"):
        path = l0_root / "provenance=broker" / "symbol=EURUSD" / f"date={day}" / "ticks.parquet"
        assert path.is_file()
    # Siku ya leo bado haijafungwa — haiandikwi (spec: partition inaandikwa MARA MOJA).
    assert not (l0_root / "provenance=broker" / "symbol=EURUSD" / "date=2026-08-05").exists()
    assert result.buffered_days["EURUSD"].startswith("2026-08-05")


def test_partition_ina_tag_ya_provenance_broker(recorder_factory, l0_root):
    """DF-03: kila partition mpya ina `provenance: broker` (metadata + njia)."""
    recorder = recorder_factory({"EURUSD": ticks_for_days([MONDAY])}, now=TUESDAY.replace(hour=12))
    result = recorder.poll_once()
    path = Path(result.written[0].path)

    assert "provenance=broker" in path.parts
    metadata = pq.read_table(path).schema.metadata
    assert metadata[b"provenance"] == b"broker"
    assert metadata[b"symbol"] == b"EURUSD"
    assert metadata[b"date"] == b"2026-08-03"
    assert metadata[b"timestamp_tz"] == b"UTC"
    assert metadata[b"schema"] == b",".join(c.encode() for c in CANONICAL_COLUMNS)
    assert metadata[b"config_hash"] == recorder.cfg.config_hash.encode()
    assert metadata[b"source"] == b"replay"


def test_partition_mpya_inaingia_manifest_na_sha256(recorder_factory, cfg):
    """DF-01: hash inarekodiwa wakati ule ule partition inapoandikwa."""
    recorder = recorder_factory({"EURUSD": ticks_for_days([MONDAY])}, now=TUESDAY.replace(hour=12))
    written = recorder.poll_once().written[0]

    manifest = L0Manifest.load(cfg.l0_manifest_path)
    entry = manifest.entries[manifest.key_for(Path(written.path))]
    assert entry.provenance == PROVENANCE_BROKER
    assert entry.sha256 == written.sha256
    assert entry.symbol == "EURUSD"
    assert entry.rows == 5
    assert manifest.verify().ok


def test_partition_iliyoandikwa_inasomeka_kwa_schema_ya_kawaida(recorder_factory, cfg):
    """Mtiririko mzima: broker -> L0 -> normalization (DF-02) bila mshono."""
    recorder = recorder_factory({"EURUSD": ticks_for_days([MONDAY])}, now=TUESDAY.replace(hour=12))
    path = recorder.poll_once().written[0].path
    frame = read_partition(path, cfg)
    assert tuple(frame.columns) == CANONICAL_COLUMNS
    assert str(frame["timestamp"].dtype) == "datetime64[us, UTC]"
    assert (frame["ask"] > frame["bid"]).all()


def test_poll_ya_pili_hairudii_kuandika(recorder_factory, l0_root):
    """Immutability + kutorudia: poll ya pili haigusi partitions zilizopo."""
    frames = {"EURUSD": ticks_for_days([MONDAY, TUESDAY, WEDNESDAY])}
    recorder = recorder_factory(frames, now=WEDNESDAY.replace(hour=12))
    first = recorder.poll_once()
    hashes = {w.path: Path(w.path).read_bytes() for w in first.written}

    second = recorder.poll_once()
    assert second.written == []
    for path, payload in hashes.items():
        assert Path(path).read_bytes() == payload


def test_watermark_inayoendelea_baada_ya_kuanza_upya(recorder_factory, cfg, l0_root):
    """Recorder ikianza upya inaendelea pale ilipoishia (hali iko kwenye disk)."""
    frames = {"EURUSD": ticks_for_days([MONDAY, TUESDAY, WEDNESDAY])}
    recorder_factory(frames, now=TUESDAY.replace(hour=12)).poll_once()

    fresh = recorder_factory(frames, now=WEDNESDAY.replace(hour=12))
    assert fresh.state.symbols["EURUSD"].last_written_day == "2026-08-03"
    result = fresh.poll_once()
    assert [w.day for w in result.written] == ["2026-08-04"]


def test_kuandika_juu_ya_partition_iliyopo_kunakataliwa(recorder_factory):
    """DF-01: faili la L0 likishakuwepo, recorder hailiandiki tena kamwe."""
    recorder = recorder_factory({"EURUSD": ticks_for_days([MONDAY])}, now=TUESDAY.replace(hour=12))
    recorder.poll_once()
    with pytest.raises(FileExistsError):
        recorder._write_partition("EURUSD", MONDAY.date(), ticks_for_days([MONDAY]))


def test_siku_ya_trading_bila_ticks_inarekodiwa_kama_onyo(recorder_factory, l0_root):
    """DF-04: ukimya wa siku ya trading ni taarifa — hakuna partition tupu ya kubuni."""
    frames = {"EURUSD": ticks_for_days([MONDAY, WEDNESDAY])}
    recorder = recorder_factory(frames, now=WEDNESDAY.replace(hour=12))
    result = recorder.poll_once()

    assert ("EURUSD", "2026-08-04") in result.empty_days
    assert [w.day for w in result.written] == ["2026-08-03"]
    assert not (l0_root / "provenance=broker" / "symbol=EURUSD" / "date=2026-08-04").exists()
    assert recorder.state.symbols["EURUSD"].empty_days == ["2026-08-04"]


def test_jumamosi_kimya_si_onyo(recorder_factory):
    """Soko limefungwa Jumamosi — ukimya wake hauzalishi ONYO (kalenda ya §3)."""
    saturday = datetime(2026, 8, 8, tzinfo=timezone.utc)
    monday_next = datetime(2026, 8, 10, tzinfo=timezone.utc)
    frames = {"EURUSD": ticks_for_days([datetime(2026, 8, 7, tzinfo=timezone.utc)])}  # Ijumaa
    recorder = recorder_factory(frames, now=monday_next.replace(hour=12))
    result = recorder.poll_once()
    empty = {day for _, day in result.empty_days}
    assert saturday.date().isoformat() not in empty


def test_symbols_nyingi_zinarekodiwa_kwa_pamoja(recorder_factory, l0_root):
    frames = {
        "EURUSD": ticks_for_days([MONDAY], symbol_base=1.09),
        "XAUUSD": ticks_for_days([MONDAY], symbol_base=2400.0),
    }
    recorder = recorder_factory(frames, now=TUESDAY.replace(hour=12), symbols=("EURUSD", "XAUUSD"))
    result = recorder.poll_once()
    assert {w.symbol for w in result.written} == {"EURUSD", "XAUUSD"}


def test_hitilafu_ya_symbol_moja_haisimamishi_recorder(recorder_factory, cfg, l0_root):
    """"Huanza, hauishii": chanzo kikikataa symbol moja, nyingine zinaendelea."""

    class HalfBrokenSource(ReplayTickSource):
        name = "half-broken"

        def fetch_ticks(self, symbol, start, end):
            if symbol == "GBPUSD":
                raise RuntimeError("broker amekata muunganisho")
            return super().fetch_ticks(symbol, start, end)

    settings = RecorderSettings.from_config(cfg)
    settings.symbols = ["EURUSD", "GBPUSD"]
    recorder = TickRecorder(
        HalfBrokenSource({"EURUSD": ticks_for_days([MONDAY])}),
        cfg,
        settings=settings,
        clock=lambda: TUESDAY.replace(hour=12),
    )
    result = recorder.poll_once()
    assert [w.symbol for w in result.written] == ["EURUSD"]
    assert result.errors and result.errors[0]["symbol"] == "GBPUSD"


def test_run_forever_inaendelea_hadi_isimamishwe(recorder_factory):
    """Mzunguko usioisha ni wa lazima (§2.2); hapa unasimamishwa kwa `stop`."""
    recorder = recorder_factory({"EURUSD": ticks_for_days([MONDAY])}, now=TUESDAY.replace(hour=12))
    slept: list[float] = []
    polls = recorder.run_forever(max_polls=3, sleeper=slept.append)
    assert polls == 3
    assert slept == [recorder.settings.poll_seconds] * 2


# ---------------------------------------------------------------------------
# Muunganisho wa MT5: timeout + ushauri wa terminal path (imegunduliwa T0, PD 2026-08-04)
# ---------------------------------------------------------------------------


class _FakeMT5:
    """MT5 bandia: inarekodi kwargs za initialize na kurudisha matokeo yaliyopangwa."""

    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.kwargs: dict = {}

    def initialize(self, **kwargs):
        self.kwargs = kwargs
        return self.ok

    def last_error(self):
        return (-10003, "IPC initialize failed, MetaTrader 5 x64 not found")

    def terminal_info(self):
        return "fake-terminal"

    def shutdown(self):
        return None


def test_mt5_inapitisha_timeout_na_path_kwenye_initialize():
    from src.data.mt5_source import MT5Credentials, MT5TickSource

    source = MT5TickSource(
        credentials=MT5Credentials(terminal_path=r"C:\MT5\terminal64.exe"),
        timeout_ms=15000,
    )
    fake = _FakeMT5(ok=True)
    source._mt5 = fake
    source.connect()
    assert fake.kwargs["path"] == r"C:\MT5\terminal64.exe"
    assert fake.kwargs["timeout"] == 15000


def test_mt5_bila_terminal_path_inatoa_ushauri_wa_10003():
    """Kosa -10003 lililoonekana T0: bila path MT5 haijitafuti — ujumbe uelekeze."""
    import pytest as _pytest

    from src.data.mt5_source import MT5Credentials, MT5TickSource, SourceError

    source = MT5TickSource(credentials=MT5Credentials(), timeout_ms=15000)
    source._mt5 = _FakeMT5(ok=False)
    with _pytest.raises(SourceError, match="ELITEFX_MT5_TERMINAL"):
        source.connect()


# ---------------------------------------------------------------------------
# Provenance ya broker: data ya brokers wawili haichanganywi (spec §2.2)
# ---------------------------------------------------------------------------


def _recorder_with_broker(cfg, l0_root, broker_id, source):
    from src.data.recorder import RecorderSettings, TickRecorder

    settings = RecorderSettings.from_config(cfg)
    settings.broker_id = broker_id
    settings.symbols = ["EURUSD"]
    return TickRecorder(source, cfg, settings=settings)


def test_broker_id_ni_lazima(cfg, l0_root):
    import pytest as _pytest

    from src.data.mt5_source import ReplayTickSource

    rec = _recorder_with_broker(cfg, l0_root, "", ReplayTickSource({}))
    with _pytest.raises(ValueError, match="broker_id"):
        rec.poll_once()


def test_broker_akibadilika_recorder_inasimama(cfg, l0_root):
    """Kubadilisha broker bila kubadilisha L0 = kuchanganya gharama za watu wawili."""
    import pytest as _pytest

    from src.data.mt5_source import ReplayTickSource

    first = _recorder_with_broker(cfg, l0_root, "broker-a", ReplayTickSource({}))
    first.poll_once()
    assert first.state.broker_id == "broker-a"

    second = _recorder_with_broker(cfg, l0_root, "broker-b", ReplayTickSource({}))
    with _pytest.raises(ValueError, match="UKIUKAJI WA PROVENANCE"):
        second.poll_once()

    same = _recorder_with_broker(cfg, l0_root, "broker-a", ReplayTickSource({}))
    same.poll_once()  # broker yule yule — inaendelea


def test_server_ikibadilika_bila_lebo_kubadilika_recorder_inasimama(cfg, l0_root):
    """Lebo inaweza kuandikwa vibaya; server ya MT5 haiwezi — inalinganishwa kando."""
    import pytest as _pytest

    from src.data.mt5_source import ReplayTickSource

    class _WithServer(ReplayTickSource):
        def __init__(self, server: str) -> None:
            super().__init__({})
            self._server = server

        def source_identity(self) -> str:
            return self._server

    first = _recorder_with_broker(cfg, l0_root, "broker-x", _WithServer("Dukascopy-demo-mt5-1"))
    first.poll_once()
    assert first.state.broker_server == "Dukascopy-demo-mt5-1"

    # Lebo ile ile, lakini akaunti imehamia server nyingine — hii ndiyo hatari halisi.
    second = _recorder_with_broker(cfg, l0_root, "broker-x", _WithServer("Exness-Real-7"))
    with _pytest.raises(ValueError, match="UKIUKAJI WA PROVENANCE"):
        second.poll_once()
