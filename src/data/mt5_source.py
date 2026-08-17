"""Vyanzo vya ticks kwa recorder: MT5 (live/demo) na replay (tests/backfill).

`MetaTrader5` haipo kwenye mazingira ya CI (ni Windows-only), kwa hiyo import
yake ni ya **ndani ya function** — module hii inapakiwa popote, na kosa la
kukosekana kwa MT5 linatokea pale tu mtu anapojaribu kuunganisha kweli.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .schema import CANONICAL_COLUMNS

LOG = logging.getLogger("elitefx.recorder.source")

# Bendera za MT5 (MqlTick.flags) — zinatumika kugawa volume kwa upande sahihi.
TICK_FLAG_BID = 2
TICK_FLAG_ASK = 4


class SourceError(RuntimeError):
    """Chanzo cha ticks hakikuweza kuunganishwa au kutoa data."""


def _empty_frame(extra: Iterable[str] = ()) -> pd.DataFrame:
    frame = pd.DataFrame({column: pd.Series(dtype="float64") for column in CANONICAL_COLUMNS})
    frame["timestamp"] = pd.Series(dtype="datetime64[us, UTC]")
    for column in extra:
        frame[column] = pd.Series(dtype="float64")
    return frame[list(CANONICAL_COLUMNS) + list(extra)]


@dataclass
class MT5Credentials:
    """Sifa za kuingia — zinatoka environment, KAMWE si kwenye config au code."""

    login: int | None = None
    password: str | None = None
    server: str | None = None
    terminal_path: str | None = None

    @classmethod
    def from_env(cls, cfg=None) -> "MT5Credentials":
        def _env(key: str, default: str) -> str | None:
            name = str(cfg.get(f"recorder.mt5.{key}", default)) if cfg is not None else default
            return os.environ.get(name)

        login = _env("login_env", "ELITEFX_MT5_LOGIN")
        return cls(
            login=int(login) if login else None,
            password=_env("password_env", "ELITEFX_MT5_PASSWORD"),
            server=_env("server_env", "ELITEFX_MT5_SERVER"),
            terminal_path=_env("terminal_path_env", "ELITEFX_MT5_TERMINAL"),
        )


class MT5TickSource:
    """Ticks za bid/ask kutoka terminal ya MT5 (`copy_ticks_range`, COPY_TICKS_ALL).

    Uwazi kuhusu volumes (spec §2 inataka `bid_vol`/`ask_vol`): MT5 haitoi
    volume kwa kila upande. Tick moja inabeba `volume_real` na bendera
    zinazoonyesha upande uliobadilika. Kwa hiyo volume ya tick inawekwa kwenye
    upande ulioupdate (BID -> `bid_vol`, ASK -> `ask_vol`); tick isiyo na
    bendera hizo inapata 0. Hii ni **mgawanyo uliotangazwa**, si makadirio —
    columns za ziada `flags`/`volume_real` zinahifadhiwa kwenye partition ili
    ukweli wa chanzo usipotee.
    """

    name = "mt5"
    extra_columns = ("flags", "volume_real")

    def __init__(
        self,
        credentials: MT5Credentials | None = None,
        symbol_suffix: str = "",
        timeout_ms: int | None = None,
        fetch_retries: int = 2,
        retry_delay_s: float = 3.0,
    ) -> None:
        self.credentials = credentials or MT5Credentials()
        self.symbol_suffix = symbol_suffix
        self.timeout_ms = timeout_ms
        self.fetch_retries = max(0, int(fetch_retries))
        self.retry_delay_s = float(retry_delay_s)
        self._mt5: Any | None = None

    # ---------- muunganisho ----------

    def _module(self) -> Any:
        if self._mt5 is not None:
            return self._mt5
        try:
            import MetaTrader5 as mt5  # type: ignore import-not-found
        except ImportError as exc:  # pragma: no cover - MT5 haipo Linux/CI
            raise SourceError(
                "package `MetaTrader5` haipo. Recorder inahitaji terminal ya MT5 "
                "(Windows au Wine) — PD anaandaa mazingira na akaunti (T0)."
            ) from exc
        self._mt5 = mt5
        return mt5

    def connect(self) -> None:
        """Anzisha terminal + login. Ikishindikana → SourceError yenye sababu ya MT5."""
        mt5 = self._module()
        kwargs: dict[str, Any] = {}
        creds = self.credentials
        if creds.terminal_path:
            kwargs["path"] = creds.terminal_path
        if creds.login:
            kwargs.update(login=creds.login, password=creds.password, server=creds.server)
        if self.timeout_ms:
            # Bila timeout, MT5 inasubiri sekunde 60 kimya terminal isipopatikana.
            # Kigezo kinatoka config (`recorder.mt5.timeout_ms`) — si code (G10).
            kwargs["timeout"] = int(self.timeout_ms)
        if not mt5.initialize(**kwargs):
            hint = ""
            if not creds.terminal_path:
                hint = (
                    " — `ELITEFX_MT5_TERMINAL` haijawekwa; MT5 haiwezi kujitafuta yenyewe "
                    "kwenye mazingira mengi (kosa -10003). Weka njia kamili ya terminal64.exe."
                )
            raise SourceError(f"mt5.initialize imeshindikana: {mt5.last_error()}{hint}")
        LOG.info("MT5 imeunganishwa: %s", mt5.terminal_info())

    def source_identity(self) -> str:
        """Server halisi ya akaunti (mf. `Dukascopy-demo-mt5-1`).

        Hii ni **ukweli kutoka MT5**, tofauti na `recorder.broker_id` ambayo ni
        lebo ya PD. `terminal_info().company` HAITUMIKI: inaripoti msambazaji wa
        terminal (mara nyingi "MetaQuotes Ltd."), si broker wa akaunti.
        """
        mt5 = self._module()
        account = mt5.account_info()
        return str(getattr(account, "server", "") or "") if account else ""

    def shutdown(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()

    def __enter__(self) -> "MT5TickSource":
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.shutdown()

    # ---------- kuvuta ticks ----------

    def broker_symbol(self, symbol: str) -> str:
        return f"{symbol}{self.symbol_suffix}"

    def fetch_ticks(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Ticks za [start, end). Jaribio la kwanza linaweza kuanzisha upakuaji.

        MT5 haihifadhi history yote kwenye terminal. Ombi la kwanza la kipindi
        kisichokuwepo **linaanzisha upakuaji** kutoka broker na linarudi
        `(-1, 'Terminal: Call failed')`. Ombi la pili baada ya sekunde chache
        mara nyingi linafanikiwa. Kwa hiyo tunajaribu tena — lakini kwa idadi
        iliyowekwa (`recorder.mt5.fetch_retries`), si milele: broker asipokuwa
        na kina hicho, kufeli ni JIBU (mpaka wa history), si hitilafu ya kurudia.
        """
        import time as _time

        mt5 = self._module()
        broker_symbol = self.broker_symbol(symbol)
        if not mt5.symbol_select(broker_symbol, True):
            raise SourceError(f"{broker_symbol}: symbol_select imeshindikana: {mt5.last_error()}")

        last_error: Any = None
        for attempt in range(self.fetch_retries + 1):
            ticks = mt5.copy_ticks_range(
                broker_symbol,
                start.astimezone(timezone.utc),
                end.astimezone(timezone.utc),
                mt5.COPY_TICKS_ALL,
            )
            if ticks is not None:
                if len(ticks) == 0:
                    return _empty_frame(self.extra_columns)
                return self._to_canonical(pd.DataFrame(ticks))
            last_error = mt5.last_error()
            if attempt < self.fetch_retries:
                LOG.debug(
                    "%s %s: jaribio %d limeshindikana (%s) — upakuaji unaweza kuwa unaendelea",
                    broker_symbol,
                    start.date(),
                    attempt + 1,
                    last_error,
                )
                _time.sleep(self.retry_delay_s)
        raise SourceError(f"{broker_symbol}: copy_ticks_range: {last_error}")

    def warm_up(self, symbols: list[str]) -> int:
        """Weka symbols zote kwenye Market Watch KWA PAMOJA.

        `symbol_select` ni ya papo hapo, lakini ndiyo inayoanzisha usawazishaji
        wa history. Kuziita zote kwanza kunafanya broker apakue kwa **sambamba**
        wakati tunasubiri, badala ya symbol moja kwa wakati — tofauti kati ya
        dakika chache na saa mbili kwa symbols 48.
        """
        mt5 = self._module()
        return sum(1 for s in symbols if mt5.symbol_select(self.broker_symbol(s), True))

    def fetch_daily_close(
        self, symbol: str, start: datetime, end: datetime, retries: int = 0
    ) -> pd.Series:
        """Bei za kufunga za D1 — kwa ajili ya kupima UHURU kati ya symbols pekee.

        **Si data ya mafunzo.** Hii ni nyepesi mara elfu kuliko ticks, na
        inatumika kwa kazi moja: kuhesabu correlation ili kujua symbol mpya
        inaleta bloc au inarudia iliyopo. Kuvuta ticks kwa wagombea 36 ili
        kupima correlation kungechukua siku; D1 inachukua sekunde.

        Inarudisha Series tupu ikiwa broker hana kina hicho — hilo ni **jibu**
        (mpaka wa history), si hitilafu.

        **Inajaribu tena, kama `fetch_ticks`.** Toleo la kwanza halikufanya
        hivyo, na matokeo yalikuwa ya kupotosha kabisa: EURUSD ilitoa bars
        2,146 na symbols 45 zilizofuata zikatoa **sifuri**, zikionekana kama
        broker hana data — wakati tunazo bars 50,263 za USDCHF kwenye L2 yetu
        wenyewe. Sababu ni ile ile iliyoandikwa kwenye `fetch_ticks`: ombi la
        kwanza linaanzisha upakuaji na linarudi tupu (2026-08-16).
        """
        import time as _time

        mt5 = self._module()
        broker_symbol = self.broker_symbol(symbol)
        if not mt5.symbol_select(broker_symbol, True):
            return pd.Series(dtype=float, name=symbol)

        rates = None
        for attempt in range(max(retries, self.fetch_retries) + 1):
            rates = mt5.copy_rates_range(
                broker_symbol,
                mt5.TIMEFRAME_D1,
                start.astimezone(timezone.utc),
                end.astimezone(timezone.utc),
            )
            if rates is not None and len(rates) > 0:
                break
            if attempt < max(retries, self.fetch_retries):
                _time.sleep(self.retry_delay_s)
        if rates is None or len(rates) == 0:
            return pd.Series(dtype=float, name=symbol)
        frame = pd.DataFrame(rates)
        stamps = pd.to_datetime(frame["time"], unit="s", utc=True)
        return pd.Series(
            pd.to_numeric(frame["close"], errors="coerce").to_numpy(),
            index=stamps,
            name=symbol,
        ).sort_index()

    def _to_canonical(self, raw: pd.DataFrame) -> pd.DataFrame:
        volume = (
            raw["volume_real"]
            if "volume_real" in raw.columns
            else raw.get("volume", pd.Series(0.0, index=raw.index))
        )
        volume = pd.to_numeric(volume, errors="coerce").fillna(0.0).astype("float64")
        flags = pd.to_numeric(raw.get("flags", 0), errors="coerce").fillna(0).astype("int64")

        frame = pd.DataFrame(index=raw.index)
        frame["timestamp"] = pd.to_datetime(raw["time_msc"], unit="ms", utc=True).astype(
            "datetime64[us, UTC]"
        )
        frame["bid"] = pd.to_numeric(raw["bid"], errors="coerce").astype("float64")
        frame["ask"] = pd.to_numeric(raw["ask"], errors="coerce").astype("float64")
        frame["bid_vol"] = volume.where((flags & TICK_FLAG_BID) != 0, 0.0)
        frame["ask_vol"] = volume.where((flags & TICK_FLAG_ASK) != 0, 0.0)
        frame["flags"] = flags
        frame["volume_real"] = volume
        return frame.reset_index(drop=True)


class ReplayTickSource:
    """Chanzo cha ticks kutoka DataFrame/parquet — kwa tests na backfill.

    Kinatumika pia pale PD anapokabidhi dump ya ticks za broker zilizovutwa nje
    ya recorder: mtiririko wa kuandika, hashing na provenance unabaki ule ule.
    """

    name = "replay"

    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = {
            symbol: frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
            for symbol, frame in frames.items()
        }

    @classmethod
    def from_parquet_dir(cls, directory: str | Path) -> "ReplayTickSource":
        frames: dict[str, pd.DataFrame] = {}
        for path in sorted(Path(directory).glob("*.parquet")):
            frames[path.stem.upper()] = pd.read_parquet(path)
        return cls(frames)

    def fetch_ticks(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        frame = self.frames.get(symbol)
        if frame is None or frame.empty:
            return _empty_frame()
        stamps = pd.to_datetime(frame["timestamp"], utc=True)
        window = frame.loc[(stamps >= start) & (stamps < end)]
        return window.reset_index(drop=True)
