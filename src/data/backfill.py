"""DF-03/DF-04 — kuziba mapengo ya siku zilizorukwa (reconciliation).

Recorder ya kawaida (`recorder.py`) inasonga mbele kwa **watermark**: inarekodi
kuanzia pale ilipoishia. Hiyo inatosha pale kila kitu kikienda sawa, lakini
production si hivyo:

* MT5 ikishindwa dakika ile siku inapofungwa, siku ile inawekwa `empty` na
  watermark **inaipita** — hairudiwi kamwe;
* `_state/recorder_state.json` ikipotea, watermark inarudi `initial_backfill_days`
  pekee — kilicho nyuma ya hapo hakirudi;
* kompyuta ikizimwa wikendi nzima, hakuna kinachohakikisha siku zilizokosekana
  zimezibwa.

Kwa hiyo module hii **haitegemei state hata kidogo**. Ukweli ni:

    zinazotarajiwa = kalenda ya trading (siku KAMILI kati ya A na B)
    zilizopo       = partitions zilizoko kwenye DISK
    zinazokosekana = tofauti yake

Kisha zinazokosekana zinavutwa kutoka history ya broker. Sheria za §2 zinabaki:
partition iliyopo **haiguswi kamwe** (append-only), na siku isiyokuwa na ticks
kwa broker **haiandikwi kama partition tupu** — inaripotiwa.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .calendar import TradingCalendar
from .manifest import L0Manifest

LOG = logging.getLogger("elitefx.backfill")

# Sababu za siku kutokuwa na partition — zinatofautishwa kwa makusudi.
REASON_WRITTEN = "written"  # imezibwa sasa
REASON_NO_TICKS = "no_ticks"  # broker hana ticks za siku hii (likizo isiyo kwenye kalenda?)
REASON_FETCH_FAILED = "fetch_failed"  # chanzo kimeshindwa — INAJARIBIWA TENA
REASON_EXISTS = "exists"  # ilishakuwepo (haiguswi)


@dataclass
class MissingDay:
    symbol: str
    day: date

    @property
    def label(self) -> str:
        return f"{self.symbol} {self.day.isoformat()}"


@dataclass
class BackfillOutcome:
    """Matokeo ya kuziba mapengo — kila siku na hatma yake."""

    written: list[dict[str, object]] = field(default_factory=list)
    no_ticks: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    scanned_days: int = 0
    symbols: int = 0
    stopped_early: str = ""

    @property
    def ok(self) -> bool:
        """Kupita = hakuna siku iliyoshindwa kuvutwa. `no_ticks` si kufeli."""
        return not self.failed

    def summary(self) -> str:
        base = (
            f"missing={self.scanned_days} written={len(self.written)} "
            f"no_ticks={len(self.no_ticks)} failed={len(self.failed)}"
        )
        return f"{base} · IMESIMAMA: {self.stopped_early}" if self.stopped_early else base


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, dtime.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def existing_days(l0_root: Path, symbol: str, provenance: str = "broker") -> set[date]:
    """Siku zilizo na partition kwenye DISK (ukweli, si state)."""
    base = Path(l0_root) / f"provenance={provenance}" / f"symbol={symbol}"
    if not base.is_dir():
        return set()
    days: set[date] = set()
    for child in base.iterdir():
        if child.is_dir() and child.name.startswith("date="):
            try:
                days.add(date.fromisoformat(child.name.split("=", 1)[1]))
            except ValueError:
                continue
    return days


def find_missing_days(
    l0_root: Path,
    symbols: list[str],
    start: date,
    end: date,
    calendar: TradingCalendar,
    provenance: str = "broker",
) -> list[MissingDay]:
    """Siku KAMILI za trading kati ya `start` na `end` zisizo na partition.

    Hii ndiyo hoja kuu ya module: inalinganisha kalenda na disk. State
    haitumiki, kwa hiyo inafanya kazi hata baada ya state kupotea kabisa.
    """
    expected = calendar.full_trading_days(start, end)
    missing: list[MissingDay] = []
    for symbol in symbols:
        have = existing_days(l0_root, symbol, provenance)
        missing.extend(MissingDay(symbol, day) for day in expected if day not in have)
    return sorted(missing, key=lambda m: (m.day, m.symbol))


def backfill_missing(
    recorder,
    start: date,
    end: date,
    symbols: list[str] | None = None,
    dry_run: bool = False,
    max_days: int | None = None,
    manifest: L0Manifest | None = None,
    on_progress=None,
    max_consecutive_failures: int = 5,
) -> BackfillOutcome:
    """Vuta na uandike siku zinazokosekana. Partition iliyopo HAIGUSWI (§2).

    **Circuit breaker:** kufeli `max_consecutive_failures` mfululizo kunasimamisha
    kazi. Sababu: broker asipokuwa na history ya kina hicho, kila siku itafeli —
    na kila kufeli kunachukua muda wa timeout ya MT5 (~sekunde 100). Kuendelea
    kungechukua siku nzima bila kuandika chochote. Kufeli mfululizo ni **jibu**
    (mpaka wa history umefikiwa), si hali ya kurudia. Tumia `probe_history()`
    kujua mpaka huo kwa maombi machache.
    """
    settings = recorder.settings
    symbols = symbols or list(settings.symbols)
    outcome = BackfillOutcome(symbols=len(symbols))

    missing = find_missing_days(
        settings.l0_root, symbols, start, end, recorder.calendar, settings.provenance
    )
    outcome.scanned_days = len(missing)
    if max_days is not None:
        missing = missing[:max_days]
    if not missing or dry_run:
        for item in missing:
            LOG.info("inakosekana: %s", item.label)
        return outcome

    own_manifest = manifest is None
    manifest = manifest or L0Manifest.load_or_new(
        settings.manifest_path, settings.l0_root, recorder.cfg.config_hash
    )

    consecutive_failures = 0
    for index, item in enumerate(missing, start=1):
        if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
            outcome.stopped_early = (
                f"kufeli {consecutive_failures} mfululizo — kazi imesimamishwa. "
                "Huenda broker hana history ya kina hiki (tumia `probe-history`)."
            )
            LOG.warning(outcome.stopped_early)
            break
        if on_progress:
            on_progress(index, len(missing), item.label)
        path = recorder.partition_path(item.symbol, item.day)
        if path.exists():  # imeandikwa na poll ya kawaida wakati huu huu
            continue
        day_start, day_end = _day_bounds(item.day)
        try:
            frame = recorder.source.fetch_ticks(item.symbol, day_start, day_end)
            frame = recorder._prepare_frame(
                frame if frame is not None else pd.DataFrame(columns=["timestamp"])
            )
        except Exception as exc:
            LOG.warning("%s: kuvuta kumeshindikana: %s", item.label, exc)
            outcome.failed.append(
                {"symbol": item.symbol, "day": item.day.isoformat(), "error": str(exc)}
            )
            consecutive_failures += 1
            continue
        consecutive_failures = 0

        if not frame.empty:
            frame = frame[frame["timestamp"].dt.date == item.day]
        if frame.empty:
            # Broker hana ticks za siku hii. HAIANDIKWI kama partition tupu —
            # data ya kubuni ni marufuku (§3). Inaripotiwa ili R0 iione.
            LOG.info("%s: broker hana ticks (haiandikwi)", item.label)
            outcome.no_ticks.append(item.label)
            continue

        written = recorder._write_day(item.symbol, item.day, frame, manifest)
        outcome.written.append(
            {"symbol": written.symbol, "day": written.day, "rows": written.rows}
        )

    if own_manifest and (outcome.written or outcome.failed):
        manifest.save()
    return outcome


# ---------------------------------------------------------------------------
# Kina cha history ya broker
# ---------------------------------------------------------------------------


def probe_history(
    recorder,
    symbol: str,
    earliest: date,
    latest: date,
    on_step=None,
) -> dict[str, object]:
    """Tafuta siku ya kwanza kabisa ambayo broker ana ticks (binary search).

    Bila hii, kugundua mpaka wa history kunahitaji kujaribu kila siku — na kila
    kufeli ni ~sekunde 100 za timeout. Binary search inajibu swali lile lile kwa
    maombi ~log2(siku), yaani chini ya 10 badala ya mamia.

    Inarudisha `{"symbol", "earliest_available", "probes", "checked"}`.
    """
    def _has_ticks(day: date) -> bool:
        start, end = _day_bounds(day)
        try:
            frame = recorder.source.fetch_ticks(symbol, start, end)
        except Exception as exc:
            LOG.info("probe %s %s: haipatikani (%s)", symbol, day, exc)
            return False
        return frame is not None and not frame.empty

    probes: list[dict[str, object]] = []

    def _probe(day: date) -> bool:
        ok = _has_ticks(day)
        probes.append({"day": day.isoformat(), "has_ticks": ok})
        if on_step:
            on_step(day, ok)
        return ok

    if not _probe(latest):
        return {
            "symbol": symbol,
            "earliest_available": None,
            "probes": probes,
            "checked": f"{earliest} -> {latest}",
            "note": "hata siku ya mwisho haina ticks — angalia muunganisho au symbol",
        }
    if _probe(earliest):
        return {
            "symbol": symbol,
            "earliest_available": earliest.isoformat(),
            "probes": probes,
            "checked": f"{earliest} -> {latest}",
            "note": "history inafika angalau mwanzo wa dirisha ulilotoa",
        }

    lo, hi = earliest, latest  # lo: haina · hi: ina
    while (hi - lo).days > 1:
        mid = lo + timedelta(days=(hi - lo).days // 2)
        if _probe(mid):
            hi = mid
        else:
            lo = mid
    return {
        "symbol": symbol,
        "earliest_available": hi.isoformat(),
        "probes": probes,
        "checked": f"{earliest} -> {latest}",
    }
