"""CLI ya tabaka la data (T0 + T1).

T0 — L0 na recorder:

    python -m src.data.cli init-research      # §9 — muundo wa research storage
    python -m src.data.cli hash-l0            # DF-01 — SHA256 ya partitions ZOTE + manifest
    python -m src.data.cli verify-l0          # DF-01 — lango la CI (hash check kila build)
    python -m src.data.cli record             # DF-04 — recorder wa feed ya broker
    python -m src.data.cli backfill           # DF-03 — ziba siku zilizorukwa
    python -m src.data.cli probe-history      # DF-03 — kina cha history ya broker
    python -m src.data.cli check-mt5          # ukaguzi wa mazingira ya MT5
    python -m src.data.cli check-freshness    # DF-04 — ONYO: siku ya trading bila data
    python -m src.data.cli inspect <faili>    # DF-02 — schema moja kutoka Toleo A/B
    python -m src.data.cli config-hash        # fingerprint ya config/data.yaml (§8)

T1 — ukaguzi wa R0 (mfuatano huu, si mwingine):

    python -m src.data.cli build-calendar     # RS-03 — kalenda ya sessions KUTOKA DATA
    python -m src.data.cli check-l1           # DF-05 — checks za ubora + quality_report.json
    python -m src.data.cli quality-stats      # DF-05 — vizingiti kutoka DATA (haisomi parquet)
    python -m src.data.cli r0-summary         # R0  — vigezo vyote kwenye jedwali moja
    python -m src.data.cli symbol-profile     # R0  — wasifu kwa mwaka: chanzo kilibadilika?
    python -m src.data.cli compare-variants   # RS-03 — Toleo A ↔ Toleo B baada ya normalization
    python -m src.data.cli compare-provenance # R0   — aggregator ↔ broker, siku zinazopishana
    python -m src.data.cli build-l2           # DF-06 — bars za TF 7 kutoka ticks
    python -m src.data.cli detect-setups      # DF-20 — SETUP-v1 decision points (§4.3)
    python -m src.data.cli build-labels       # DF-09/10/11 — L4 labels kwa path ya ticks
    python -m src.data.cli sentinel           # DF-08 / G1 — sentinel ya uvujaji
    python -m src.data.cli splits             # DF-14 / G2 — mpango wa splits + holdout guard

`check-l1` inahitaji kalenda; `sentinel` inahitaji bars. Ndiyo maana mfuatano ni huo.

Exit codes: 0 = sawa/skipped · 1 = ONYO au ukiukaji · 2 = hitilafu ya matumizi.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from .config import ConfigError, DataConfig, load_config
from .freshness import check_freshness
from .manifest import L0Manifest, ManifestError, hash_l0_tree
from .research_layout import init_research_tree, verify_research_tree

LOG = logging.getLogger("elitefx.data")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s · %(message)s",
    )


def _load(args: argparse.Namespace) -> DataConfig:
    return load_config(args.config)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_init_research(args: argparse.Namespace) -> int:
    cfg = _load(args)
    root = Path(args.root).expanduser() if args.root else cfg.research_root
    result = init_research_tree(root, write_readme=not args.no_readme)
    print(result.render())
    missing = verify_research_tree(root)
    if missing:
        print("folda hazikukamilika: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


def cmd_hash_l0(args: argparse.Namespace) -> int:
    cfg = _load(args)
    root = Path(args.l0_root).expanduser() if args.l0_root else cfg.l0_root
    manifest_path = Path(args.manifest).expanduser() if args.manifest else cfg.l0_manifest_path
    started = time.monotonic()
    every = max(1, int(args.progress_every))

    def _progress(done: int, total: int, key: str) -> None:
        if done % every and done != total:
            return
        elapsed = time.monotonic() - started
        rate = done / elapsed if elapsed > 0 else 0.0
        eta = (total - done) / rate if rate > 0 else 0.0
        print(
            f"  [{done}/{total}] {done * 100 // max(total, 1)}% · "
            f"{rate:.1f} partitions/s · imebaki ~{eta / 60:.1f} min · {key}",
            flush=True,
        )

    manifest, result = hash_l0_tree(
        cfg,
        l0_root=root,
        manifest_path=manifest_path,
        read_metadata=not args.no_metadata,
        allow_mutation=args.allow_mutation,
        mutation_reason=args.reason,
        resume=not args.no_resume,
        prune_missing=args.prune_missing,
        on_progress=_progress,
    )
    print(
        f"L0 hashing: scanned={result.scanned} added={result.added} "
        f"confirmed={result.confirmed} skipped={result.skipped} "
        f"pruned={len(result.pruned)} mutated={len(result.mutated)} · "
        f"{time.monotonic() - started:.0f}s"
    )
    print(f"provenance: {json.dumps(manifest.provenance_counts())}")
    print(f"manifest: {result.manifest_path}")
    for failure in result.failed:
        print(f"  ! {failure['partition']}: {failure['error']}", file=sys.stderr)
    return 0 if result.ok else 1


def cmd_verify_l0(args: argparse.Namespace) -> int:
    cfg = _load(args)
    try:
        manifest_path = Path(args.manifest).expanduser() if args.manifest else cfg.l0_manifest_path
    except ConfigError as exc:
        if args.require_storage:
            raise
        print(f"verify-l0: SKIPPED — {exc}")
        return 0
    if not manifest_path.is_file():
        if args.require_storage:
            print(f"verify-l0: manifest haipo: {manifest_path}", file=sys.stderr)
            return 1
        print(f"verify-l0: SKIPPED — manifest haipo ({manifest_path})")
        return 0
    manifest = L0Manifest.load(manifest_path)
    started = time.monotonic()
    every = max(1, int(args.progress_every))

    def _progress(done: int, total: int, key: str) -> None:
        if done % every and done != total:
            return
        elapsed = time.monotonic() - started
        rate = done / elapsed if elapsed > 0 else 0.0
        eta = (total - done) / rate if rate > 0 else 0.0
        print(
            f"  [{done}/{total}] {done * 100 // max(total, 1)}% · "
            f"{rate:.1f} partitions/s · imebaki ~{eta / 60:.1f} min",
            flush=True,
        )

    result = manifest.verify(on_progress=_progress)
    print(
        f"verify-l0: {'PASS' if result.ok else 'FAIL'} · {result.summary()} · "
        f"{time.monotonic() - started:.0f}s"
    )
    for key in result.changed:
        print(f"  ! IMEBADILIKA (DF-01): {key}", file=sys.stderr)
    for key in result.missing:
        print(f"  ! IMEPOTEA: {key}", file=sys.stderr)
    if result.untracked and args.strict:
        for key in result.untracked:
            print(f"  ! HAIJAHASHIWA: {key}", file=sys.stderr)
        return 1 if not result.ok or result.untracked else 0
    return 0 if result.ok else 1


def cmd_record(args: argparse.Namespace) -> int:
    cfg = _load(args)
    from .mt5_source import MT5Credentials, MT5TickSource, ReplayTickSource
    from .recorder import RecorderSettings, TickRecorder

    settings = RecorderSettings.from_config(cfg)
    if args.symbols:
        settings.symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    if args.replay_dir:
        source = ReplayTickSource.from_parquet_dir(args.replay_dir)
    else:
        source = MT5TickSource(
            credentials=MT5Credentials.from_env(cfg),
            symbol_suffix=str(cfg.get("recorder.mt5.symbol_suffix", "")),
            timeout_ms=int(cfg.get("recorder.mt5.timeout_ms", 15000)),
            fetch_retries=int(cfg.get("recorder.mt5.fetch_retries", 2)),
            retry_delay_s=float(cfg.get("recorder.mt5.retry_delay_s", 3)),
        )
        source.connect()

    recorder = TickRecorder(source, cfg, settings=settings)
    try:
        if args.once:
            outcome = recorder.poll_once()
            print(f"poll: {outcome.summary()}")
            for written in outcome.written:
                print(f"  + {written.symbol} {written.day}: ticks={written.rows} {written.sha256}")
            for symbol, day in outcome.empty_days:
                print(f"  ! {symbol} {day}: siku ya trading bila ticks (DF-04)")
            return 0 if not outcome.errors else 1
        recorder.run_forever(max_polls=args.max_polls)
        return 0
    finally:
        shutdown = getattr(source, "shutdown", None)
        if callable(shutdown):
            shutdown()


def cmd_backfill(args: argparse.Namespace) -> int:
    """DF-03 — ziba siku zilizorukwa (ukweli ni disk, si state)."""
    cfg = _load(args)
    from datetime import date, timedelta

    from .backfill import backfill_missing
    from .mt5_source import MT5Credentials, MT5TickSource, ReplayTickSource
    from .recorder import RecorderSettings, TickRecorder

    settings = RecorderSettings.from_config(cfg)
    if args.symbols:
        settings.symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    end = date.fromisoformat(args.to) if args.to else date.today() - timedelta(days=1)
    start = (
        date.fromisoformat(getattr(args, "from"))
        if getattr(args, "from")
        else end - timedelta(days=settings.reconcile_lookback_days)
    )

    if args.replay_dir:
        source = ReplayTickSource.from_parquet_dir(args.replay_dir)
    else:
        source = MT5TickSource(
            credentials=MT5Credentials.from_env(cfg),
            symbol_suffix=str(cfg.get("recorder.mt5.symbol_suffix", "")),
            timeout_ms=int(cfg.get("recorder.mt5.timeout_ms", 15000)),
            fetch_retries=int(cfg.get("recorder.mt5.fetch_retries", 2)),
            retry_delay_s=float(cfg.get("recorder.mt5.retry_delay_s", 3)),
        )
        if not args.dry_run:
            source.connect()

    recorder = TickRecorder(source, cfg, settings=settings)
    started = time.monotonic()

    def _progress(done: int, total: int, label: str) -> None:
        print(f"  [{done}/{total}] {label}", flush=True)

    try:
        outcome = backfill_missing(
            recorder,
            start=start,
            end=end,
            symbols=settings.symbols,
            dry_run=args.dry_run,
            max_days=args.max_days,
            on_progress=None if args.dry_run else _progress,
            max_consecutive_failures=args.max_consecutive_failures,
        )
    finally:
        shutdown = getattr(source, "shutdown", None)
        if callable(shutdown) and not args.dry_run:
            shutdown()

    print(
        f"backfill {start} -> {end}: {outcome.summary()} · "
        f"{time.monotonic() - started:.0f}s"
    )
    for item in outcome.no_ticks:
        print(f"  ~ hakuna ticks kwa broker: {item}")
    for item in outcome.failed:
        print(f"  ! {item['symbol']} {item['day']}: {item['error']}", file=sys.stderr)
    return 0 if outcome.ok else 1


def cmd_check_mt5(args: argparse.Namespace) -> int:
    """Ukaguzi wa mazingira ya MT5: muunganisho, server, symbols (SETUP §1)."""
    cfg = _load(args)
    from .mt5_source import MT5Credentials, MT5TickSource, SourceError

    creds = MT5Credentials.from_env(cfg)
    source = MT5TickSource(
        credentials=creds,
        symbol_suffix=str(cfg.get("recorder.mt5.symbol_suffix", "")),
        timeout_ms=int(cfg.get("recorder.mt5.timeout_ms", 15000)),
    )
    print(f"terminal : {creds.terminal_path or '(HAIJAWEKWA — ELITEFX_MT5_TERMINAL)'}")
    print(f"login    : {'kutoka env' if creds.login else 'session ya terminal (hiari haijawekwa)'}")
    try:
        source.connect()
    except SourceError as exc:
        print(f"muunganisho: IMESHINDIKANA — {exc}", file=sys.stderr)
        return 1

    try:
        mt5 = source._module()
        account = mt5.account_info()
        server = source.source_identity()
        broker_id = str(cfg.get("recorder.broker_id", "") or "")
        available = {s.name for s in (mt5.symbols_get() or [])}
        wanted = [source.broker_symbol(s) for s in cfg.symbols]
        missing = [s for s in wanted if s not in available]

        print(f"muunganisho: SAWA · akaunti {getattr(account, 'login', '?')}")
        print(f"server   : {server}    <- kitambulisho cha broker (SI terminal_info().company)")
        print(f"broker_id: {broker_id or '(HAIJAWEKWA — config/data.yaml recorder.broker_id)'}")
        print(f"symbols  : {len(wanted) - len(missing)}/{len(wanted)} zinapatikana")
        if missing:
            print(f"  HAZIPO : {missing}", file=sys.stderr)
            print("  Broker akiwa na kiambishi, weka `recorder.mt5.symbol_suffix` kwenye config.")
        ok = not missing and bool(broker_id)
        if not broker_id:
            print("  `recorder.broker_id` ni LAZIMA kabla ya kurekodi (spec §2.2).", file=sys.stderr)
        return 0 if ok else 1
    finally:
        source.shutdown()


def cmd_probe_history(args: argparse.Namespace) -> int:
    """Tafuta kina cha tick history ya broker (binary search, maombi machache)."""
    cfg = _load(args)
    from datetime import date, timedelta

    from .backfill import probe_history
    from .mt5_source import MT5Credentials, MT5TickSource
    from .recorder import RecorderSettings, TickRecorder

    settings = RecorderSettings.from_config(cfg)
    symbol = (args.symbol or settings.symbols[0]).upper()
    latest = date.fromisoformat(args.to) if args.to else date.today() - timedelta(days=1)
    earliest = (
        date.fromisoformat(getattr(args, "from"))
        if getattr(args, "from")
        else latest - timedelta(days=365 * 2)
    )

    source = MT5TickSource(
        credentials=MT5Credentials.from_env(cfg),
        symbol_suffix=str(cfg.get("recorder.mt5.symbol_suffix", "")),
        timeout_ms=int(cfg.get("recorder.mt5.timeout_ms", 15000)),
        fetch_retries=int(cfg.get("recorder.mt5.fetch_retries", 2)),
        retry_delay_s=float(cfg.get("recorder.mt5.retry_delay_s", 3)),
    )
    source.connect()
    recorder = TickRecorder(source, cfg, settings=settings)

    def _step(day, ok: bool) -> None:
        print(f"  {day}: {'ina ticks' if ok else 'HAINA'}", flush=True)

    try:
        report = probe_history(recorder, symbol, earliest, latest, on_step=_step)
    finally:
        source.shutdown()

    print(json.dumps(report, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report.get("earliest_available") else 1


def cmd_check_freshness(args: argparse.Namespace) -> int:
    cfg = _load(args)
    report = check_freshness(cfg, require_storage=args.require_storage)
    if args.json:
        print(json.dumps(report.to_json(), indent=2))
    else:
        print(report.render())
    if args.out:
        Path(args.out).write_text(json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8")
    return report.exit_code


def cmd_inspect(args: argparse.Namespace) -> int:
    cfg = _load(args)
    from .schema import describe_partition

    for path in args.paths:
        print(json.dumps(describe_partition(path, cfg), indent=2))
    return 0


# ---------------------------- T1 (R0) -------------------------------------


def _progress_printer(every: int) -> tuple:
    """Maendeleo yenye ETA — kazi za T1 ni za masaa, si za sekunde."""
    started = time.monotonic()
    every = max(1, int(every))

    def _print(done: int, total: int, key: str) -> None:
        if done % every and done != total:
            return
        elapsed = time.monotonic() - started
        rate = done / elapsed if elapsed > 0 else 0.0
        eta = (total - done) / rate if rate > 0 else 0.0
        print(
            f"  [{done}/{total}] {done * 100 // max(total, 1)}% · {rate:.1f}/s · "
            f"imebaki ~{eta / 60:.1f} min · {key}",
            flush=True,
        )

    return _print, started


def _quality_dir(args: argparse.Namespace, cfg: DataConfig) -> Path:
    return Path(args.out_dir).expanduser() if args.out_dir else cfg.quality_reports_dir


def _symbol_list(args: argparse.Namespace) -> list[str] | None:
    raw = getattr(args, "symbols", None)
    return [s.strip().upper() for s in raw.split(",") if s.strip()] if raw else None


def cmd_build_calendar(args: argparse.Namespace) -> int:
    """RS-03 — kalenda ya sessions KUTOKA KWENYE DATA (spec §3)."""
    cfg = _load(args)
    from .audit import build_session_calendar

    root = Path(args.l0_root).expanduser() if args.l0_root else cfg.l0_root
    out_dir = _quality_dir(args, cfg)
    on_progress, started = _progress_printer(args.progress_every)

    build = build_session_calendar(
        cfg,
        root=root,
        symbols=_symbol_list(args),
        cache_path=None if args.no_cache else out_dir / "_calendar_scan.jsonl",
        on_progress=on_progress,
        limit=args.limit,
    )
    calendar_path = build.calendar.save(out_dir / "session_calendar.json")
    diff_path = out_dir / "calendar_vs_assumed.json"
    diff_path.write_text(
        json.dumps({**build.comparison, "by_variant": build.by_variant}, indent=2) + "\n",
        encoding="utf-8",
    )

    print(build.render())
    print(f"kalenda : {calendar_path}")
    print(f"tofauti : {diff_path} · {time.monotonic() - started:.0f}s")
    return 0 if not build.failed else 1


def cmd_check_l1(args: argparse.Namespace) -> int:
    """DF-05 — checks za L1 + `quality_report.json` (spec §3)."""
    cfg = _load(args)
    from .audit import run_quality_audit
    from .session_calendar import SessionCalendar

    root = Path(args.l0_root).expanduser() if args.l0_root else cfg.l0_root
    out_dir = _quality_dir(args, cfg)
    calendar_path = (
        Path(args.calendar).expanduser() if args.calendar else out_dir / "session_calendar.json"
    )
    if calendar_path.is_file():
        calendar = SessionCalendar.load(calendar_path)
        print(f"kalenda : {calendar_path} (siku {len(calendar.days)})")
    else:
        calendar = None
        print(
            f"kalenda : HAIPO ({calendar_path}) — coverage na session HAZITAHUKUMIWA. "
            "Kimbiza `build-calendar` kwanza.",
            file=sys.stderr,
        )

    on_progress, started = _progress_printer(args.progress_every)
    report = run_quality_audit(
        cfg,
        root=root,
        calendar=calendar,
        symbols=_symbol_list(args),
        on_progress=on_progress,
        limit=args.limit,
        cache_path=None if args.no_cache else out_dir / "_l1_scan.jsonl",
    )
    path = report.save(out_dir / "quality_report.json")
    print(report.render())
    print(f"ripoti  : {path} · {time.monotonic() - started:.0f}s")
    return 0 if not report.failed else 1


def cmd_audit_status(args: argparse.Namespace) -> int:
    """Hatua za R0 zilizokamilika — baada ya kukatika, hili ndilo swali la kwanza."""
    cfg = _load(args)
    from .audit import select_partitions

    out_dir = _quality_dir(args, cfg)
    l0_root = cfg.l0_root
    l2_root = cfg.l2_root
    total = len(select_partitions(cfg, l0_root))
    print(f"L0: partitions {total}\n")

    def _cached(name: str) -> int:
        path = out_dir / name
        if not path.is_file():
            return 0
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())

    rows: list[tuple[str, str, str]] = []
    cal_cache = _cached("_calendar_scan.jsonl")
    cal_done = (out_dir / "session_calendar.json").is_file()
    rows.append(
        (
            "1 kalenda",
            "IMEKAMILIKA" if cal_done else f"{cal_cache}/{total} kwenye cache",
            "session_calendar.json" if cal_done else "endesha build-calendar",
        )
    )
    l1_cache = _cached("_l1_scan.jsonl")
    l1_done = (out_dir / "quality_report.json").is_file()
    rows.append(
        (
            "2 L1 checks",
            "IMEKAMILIKA" if l1_done else f"{l1_cache}/{total} kwenye cache",
            "quality_report.json" if l1_done else "endesha check-l1",
        )
    )
    for label, name in (
        ("3a Toleo A↔B", "variant_comparison.json"),
        ("3b aggregator↔broker", "provenance_comparison.json"),
        ("5 splits", "splits.json"),
    ):
        exists = (out_dir / name).is_file()
        rows.append((label, "IMEKAMILIKA" if exists else "—", name if exists else ""))

    timeframes = list(cfg.get("bars.timeframes"))
    symbols = cfg.symbols
    ready = [
        s
        for s in symbols
        if all((l2_root / f"symbol={s}" / f"tf={tf}" / "bars.parquet").is_file() for tf in timeframes)
    ]
    state = l2_root / "_l2_state.json"
    tracked = 0
    if state.is_file():
        try:
            tracked = len(json.loads(state.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            tracked = 0
    rows.append(
        (
            "4 L2 bars",
            f"{len(ready)}/{len(symbols)} symbols zina TF {len(timeframes)}",
            f"_l2_state.json: {tracked} zimefuatiliwa" if state.is_file() else "hakuna hali",
        )
    )

    width = max(len(r[0]) for r in rows)
    for label, status, note in rows:
        print(f"  {label:<{width}}  {status:<28}  {note}")

    if ready and not state.is_file():
        print(
            f"\nONYO: symbols {len(ready)} zina bars lakini hakuna `_l2_state.json` — "
            "zilijengwa na toleo la zamani lisilo na resume. `build-l2` itazijenga upya.\n"
            "Kuziepuka: endesha `build-l2 --symbols <zilizobaki>` kwa zile pekee zisizokuwepo."
        )
        print(f"  zilizopo : {','.join(ready)}")
        missing = [s for s in symbols if s not in ready]
        if missing:
            print(f"  zinazokosekana: {','.join(missing)}")
    return 0


def cmd_symbol_profile(args: argparse.Namespace) -> int:
    """Wasifu wa kila symbol kwa MWAKA — kugundua chanzo kilipobadilika.

    Kipimo cha 2026-08-08 kilionyesha mfumo usioelezeka: EURCHF na GBPJPY
    zilifeli `gaps`/`stale_feed` siku ~117 mwaka **2023** pekee, wakati miaka
    mingine zilikuwa na chache. Kufeli kunakojikita mwaka mmoja si bahati mbaya
    ya siku moja moja — ni dalili ya **chanzo kilichobadilika**.

    Amri hii inasoma `session_calendar.json` (haisomi parquet) na kuonyesha,
    kwa kila symbol/mwaka, median ya dakika zenye quote na mipaka ya session.
    Chanzo kikibadilika, namba hizi zinabadilika hatua moja — na inaonekana.
    """
    cfg = _load(args)
    from .session_calendar import SessionCalendar

    out_dir = _quality_dir(args, cfg)
    path = Path(args.calendar).expanduser() if args.calendar else out_dir / "session_calendar.json"
    if not path.is_file():
        print(f"kalenda haipo: {path} — endesha `build-calendar`.", file=sys.stderr)
        return 2

    calendar = SessionCalendar.load(path)
    wanted = _symbol_list(args)
    import statistics

    for symbol in sorted(calendar.symbol_expect):
        if wanted and symbol not in wanted:
            continue
        by_year: dict[str, list[list[float]]] = {}
        for day, values in calendar.symbol_expect[symbol].items():
            by_year.setdefault(day[:4], []).append(values)
        print(f"\n{symbol}")
        previous: float | None = None
        for year, rows in sorted(by_year.items()):
            minutes = statistics.median(v[0] for v in rows)
            opens = statistics.median(v[1] for v in rows)
            closes = statistics.median(v[2] for v in rows)
            shift = ""
            if previous and previous > 0:
                change = minutes / previous - 1
                if abs(change) >= args.jump:
                    shift = f"   <== HATUA {change:+.0%}"
            print(
                f"  {year}  siku {len(rows):>4}  dakika {minutes:>7.0f}  "
                f"session {int(opens) // 60:02d}:{int(opens) % 60:02d}"
                f"–{int(closes) // 60:02d}:{int(closes) % 60:02d}{shift}"
            )
            previous = minutes
    print(
        f"\n`HATUA` = mabadiliko ya median ya dakika kwa zaidi ya {args.jump:.0%} kutoka mwaka "
        "uliotangulia. Chanzo kikibadilika, kinaonekana hapa."
    )
    return 0


def cmd_r0_summary(args: argparse.Namespace) -> int:
    """R0 dhidi ya vigezo vyake (RESEARCH_PLAN_R0 §R0) — ushahidi wa sahihi ya T1.

    Inasoma ripoti zilizoshaandikwa; **haihesabu chochote upya** na haisomi
    parquet. Kila mstari ni kigezo kimoja cha jedwali la §R0, namba yake halisi,
    na hukumu ya kiufundi. Hukumu ya mwisho ni ya PD — hii inampa jedwali moja
    badala ya faili sita.
    """
    cfg = _load(args)
    out_dir = _quality_dir(args, cfg)

    def _read(name: str) -> dict | None:
        path = out_dir / name
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    quality = _read("quality_report.json")
    calendar = _read("calendar_vs_assumed.json")
    variants = _read("variant_comparison.json")
    provenance = _read("provenance_comparison.json")
    if quality is None:
        print("quality_report.json haipo — endesha `scripts\\audit.bat`.", file=sys.stderr)
        return 2

    from .quality import schema_warning

    stale = schema_warning(quality)
    if stale:
        # Ripoti ya code ya zamani inaonekana sawa kabisa na ya mpya: namba ni
        # halali, jedwali ni kamili, na hakuna kinachotofautiana kwa macho.
        # Ndiyo maana onyo lazima liwe hapa juu, kabla ya namba yoyote.
        print(stale, file=sys.stderr)
        print("", file=sys.stderr)

    rows: list[tuple[str, str, str]] = []
    attention = 0

    def _add(kigezo: str, namba: str, ok: bool | None) -> None:
        nonlocal attention
        mark = "—" if ok is None else ("PASS" if ok else "ANGALIA")
        if ok is False:
            attention += 1
        rows.append((kigezo, namba, mark))

    totals = quality.get("totals", {})
    # Kitengo ni SIKU (§3). Kugawanya siku kwa idadi ya PARTITIONS kungetoa
    # asilimia zilizovimba — partition ya mwezi ina siku ~22.
    days = int(totals.get("days", 0))
    days_passed = int(totals.get("days_passed", 0))
    if days:
        _add("siku zilizopita §3", f"{days_passed}/{days} ({days_passed / days:.1%})", None)
    _add(
        "  (partitions)",
        f"{totals.get('passed', 0)}/{totals.get('partitions', 0)}",
        None,
    )

    for reason, count in (quality.get("fail_reasons") or {}).items():
        share = count / days if days else 0.0
        _add(f"  kufeli: {reason}", f"siku {count} ({share:.2%})", share <= 0.01)

    years = quality.get("coverage_by_symbol") or {}
    short = [s for s, v in years.items() if v.get("meets_min_years") is False]
    if years:
        span = min(v.get("years", 0) for v in years.values())
        _add(
            f"miaka ≥ min_years ({cfg.get('source.min_years')})",
            f"ndogo kuliko zote: {span:.1f} · zilizopungua: {len(short)}",
            not short,
        )

    if calendar:
        _add(
            "siku zilizotarajiwa bila data",
            str(len(calendar.get("silent_but_expected", []))),
            not calendar.get("silent_but_expected"),
        )
        _add(
            "Jumamosi zenye ticks (zinahitaji maelezo)",
            str(len(calendar.get("unexpected_active", []))),
            not calendar.get("unexpected_active"),
        )
        _add(
            "sikukuu zenye ticks (25 Des / 1 Jan — soko jembamba)",
            str(len(calendar.get("holiday_thin", []))),
            None,
        )
        _add(
            "Jumapili zenye ticks (ufunguzi wa wiki)",
            str(len(calendar.get("weekend_open", []))),
            None,
        )
        for name, entry in sorted((calendar.get("by_variant") or {}).items()):
            _add(
                f"  Toleo {name}: symbols {len(entry.get('symbols', []))}",
                f"{entry.get('first_day')} → {entry.get('last_day')} · "
                f"session {entry.get('session_open')}–{entry.get('session_close')}",
                None,
            )

    if variants:
        identical = variants.get("canonical_schema_identical")
        _add("Toleo A ↔ B: schema moja baada ya normalization", str(identical), bool(identical))

    if provenance:
        ratio = (provenance.get("spread_p50_ratio") or {}).get("median")
        days = len(provenance.get("overlap_days", []))
        if ratio:
            _add(
                "spread broker ÷ aggregator (siku zinazopishana)",
                f"{ratio} kwa siku {days}",
                ratio <= float(cfg.get("research.ev.cost_stress_mult", 1.5)),
            )
        else:
            _add("spread broker ÷ aggregator", "haikupimika", False)

    # `_add` LAZIMA iitwe kabla ya kuchapisha — mstari ulioongezwa baadaye
    # unaingia kwenye `rows` bila kuonekana kamwe. Ndivyo mstari huu
    # ulivyokosekana kwenye kipimo cha kwanza (2026-08-10).
    if totals.get("split_day_pieces_merged"):
        _add(
            "  vipande vya siku vilivyounganishwa",
            f"{totals['split_day_pieces_merged']} "
            f"(nakala: {totals.get('overlapping_day_pieces', 0)})",
            None,
        )

    width = max(len(r[0]) for r in rows)
    print("R0 — DATA AUDIT dhidi ya vigezo vya RESEARCH_PLAN_R0 §R0\n")
    for kigezo, namba, mark in rows:
        print(f"  {kigezo:<{width}}  {namba:<34}  {mark}")
    print(f"\nvinavyohitaji uamuzi wako: {attention}")
    print(f"config_hash: {quality.get('config_hash', '')[:16]}")
    # Vizingiti NA code. Ripoti isiyosema code ilikuwa ipi haiwezi kuzalishwa
    # upya wala kukanushwa — na ndiyo ilivyoruhusu run ya code ya zamani
    # kuonekana halali kabisa (2026-08-09).
    print(f"code_rev   : {quality.get('code_rev', 'haijulikani')[:16]}")
    print(f"iliandikwa : {quality.get('built_at', 'haijulikani')}")
    print(
        "\nSahihi ya T1 (baada ya kupitia):\n"
        f"  scripts\\sign.bat DF-05 VERIFIED --evidence {out_dir / 'quality_report.json'} "
        '--reason "<namba ulizoziona, na kwa nini zinatosha>"'
    )
    return 0 if attention == 0 else 1


def cmd_quality_stats(args: argparse.Namespace) -> int:
    """DF-05 — mgawanyo wa thamani za L1 → vizingiti vinavyotokana na DATA."""
    cfg = _load(args)
    from .quality import render_threshold_study, threshold_study

    from .quality import DETAIL_NAME

    out_dir = _quality_dir(args, cfg)
    # Kina (kila siku) kiko kwenye faili lake; muhtasari ni mdogo na hauna checks.
    path = Path(args.report).expanduser() if args.report else out_dir / DETAIL_NAME
    if not path.is_file():
        print(
            f"{path.name} haipo: {path}\n"
            "  Kina cha kila siku kinaandikwa na `check-l1` pamoja na muhtasari. "
            "Endesha `check-l1` kwanza.",
            file=sys.stderr,
        )
        return 2

    report = json.loads(path.read_text(encoding="utf-8"))

    if args.reason:
        # Orodha ya partitions zilizofeli kwa sababu moja — pamoja na `detail`,
        # ambayo ndiyo inayosema ni NINI hasa (mf. "zilizorudi nyuma=0
        # duplicates=4"). Bila hii, `bad_timestamps: 16` ni namba isiyo na jibu.
        shown = 0
        for part in report.get("partitions", []):
            # Checks ziko ndani ya kila SIKU; zile za partition nzima (mf. faili
            # tupu) ziko `part["checks"]`. Zote mbili zinaangaliwa.
            units = [(d.get("day", "?"), d.get("checks", [])) for d in part.get("days", [])]
            units.append(("(faili)", part.get("checks", [])))
            for day, checks in units:
                for check in checks:
                    if check.get("reason") != args.reason:
                        continue
                    shown += 1
                    if shown <= args.limit:
                        print(
                            f"{part.get('symbol')} · {day} · "
                            f"{check['name']}={check.get('value')} · {check.get('detail', '')}"
                        )
        print(f"jumla: siku {shown} zenye `{args.reason}`")
        return 0 if shown == 0 else 1

    if args.what_if:
        from .quality import what_if

        proposals: dict[str, float] = {}
        for item in args.what_if.split(","):
            if "=" not in item:
                print(f"muundo: --what-if coverage=0.98,gaps=7200 (si `{item}`)", file=sys.stderr)
                return 2
            name, _, value = item.partition("=")
            proposals[name.strip()] = float(value)
        try:
            result = what_if(report, proposals)
        except ValueError as exc:
            print(f"HITILAFU: {exc}", file=sys.stderr)
            return 2
        print(f"siku zote: {result['days']}")
        print(f"  zinafeli SASA   : {result['failing_now']} ({result['failing_now']/max(result['days'],1):.2%})")
        print(f"  zingefeli BAADA : {result['failing_after']} ({result['failing_after']/max(result['days'],1):.2%})")
        print(f"  zingerudi       : {result['recovered']}")
        for name, count in result["per_check"].items():
            print(f"    {name} @ {proposals[name]}: siku {count} zingefeli kwa ukaguzi huu")
        return 0

    study = threshold_study(report)
    print(render_threshold_study(study))
    target = out_dir / "threshold_study.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(study, indent=2) + "\n", encoding="utf-8")
    print(f"ripoti: {target}")
    return 0


def cmd_compare_variants(args: argparse.Namespace) -> int:
    """RS-03 — Toleo A ↔ Toleo B baada ya normalization (spec §2.1)."""
    cfg = _load(args)
    from .audit import compare_variants
    from .session_calendar import SessionCalendar

    root = Path(args.l0_root).expanduser() if args.l0_root else cfg.l0_root
    out_dir = _quality_dir(args, cfg)
    calendar_path = out_dir / "session_calendar.json"
    calendar = SessionCalendar.load(calendar_path) if calendar_path.is_file() else None

    summary = compare_variants(cfg, root, calendar=calendar)
    path = out_dir / "variant_comparison.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary.get("variants", {}), indent=2))
    identical = summary.get("canonical_schema_identical")
    print(f"schema ya kawaida inalingana A↔B: {'NDIYO' if identical else 'HAPANA'}")
    print(f"ripoti: {path}")
    return 0 if identical else 1


def cmd_compare_provenance(args: argparse.Namespace) -> int:
    """R0 — aggregator ↔ broker kwa siku zinazopishana (spec §2.2 sharti 2)."""
    cfg = _load(args)
    from .audit import compare_provenance

    root = Path(args.l0_root).expanduser() if args.l0_root else cfg.l0_root
    out_dir = _quality_dir(args, cfg)
    on_progress, started = _progress_printer(args.progress_every)

    summary = compare_provenance(
        cfg, root, symbols=_symbol_list(args), on_progress=on_progress
    )
    path = out_dir / "provenance_comparison.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if not summary["comparisons"]:
        print(
            "hakuna siku zinazopishana kati ya aggregator na broker — "
            "ulinganisho wa §2.2 hauwezekani bado.",
            file=sys.stderr,
        )
        print(f"ripoti: {path}")
        return 1

    ratio = summary["spread_p50_ratio"]
    print(
        f"siku zinazopishana: {len(summary['overlap_days'])} · "
        f"symbols {len(summary['symbols'])} · linganisho {summary['comparisons']}"
    )
    print(
        f"spread_p50 broker/aggregator: median={ratio['median']} "
        f"(min={ratio['min']} max={ratio['max']})"
    )
    print("  >1 = broker ni ghali zaidi kuliko data tuliyofundishia (EV ingekuwa ya matumaini)")
    for row in summary["rows"][:12]:
        print(
            f"  {row['symbol']} {row['day']}: agg={row['aggregator']['spread_p50']} "
            f"broker={row['broker']['spread_p50']} pips · "
            f"uwiano={row['spread_p50_ratio']} · ticks x{row['tick_ratio']}"
        )
    print(f"ripoti: {path} · {time.monotonic() - started:.0f}s")
    return 0


def cmd_build_l2(args: argparse.Namespace) -> int:
    """DF-06 — bars za TF 7 kutoka ticks (spec §4)."""
    cfg = _load(args)
    from .audit import adopt_existing_l2, build_l2

    l0_root = Path(args.l0_root).expanduser() if args.l0_root else cfg.l0_root
    l2_root = Path(args.l2_root).expanduser() if args.l2_root else cfg.l2_root
    timeframes = [t.strip() for t in args.timeframes.split(",")] if args.timeframes else None

    if args.adopt_existing:
        adopted = adopt_existing_l2(
            cfg, l0_root, l2_root, symbols=_symbol_list(args), timeframes=timeframes
        )
        print(
            f"zimeandikishwa bila kujengwa upya: {len(adopted)} "
            f"({', '.join(adopted) if adopted else 'hakuna'})"
        )
        if not args.build_after_adopt:
            return 0

    on_progress, started = _progress_printer(args.progress_every)

    builds = build_l2(
        cfg,
        l0_root=l0_root,
        l2_root=l2_root,
        symbols=_symbol_list(args),
        timeframes=timeframes,
        max_rows_per_chunk=args.max_rows_per_chunk,
        on_progress=on_progress,
        resume=not args.no_resume,
    )
    for build in builds:
        print(build.render())
    print(f"L2: {l2_root} · {time.monotonic() - started:.0f}s")
    return 0 if all(b.ok for b in builds) else 1


def cmd_sentinel(args: argparse.Namespace) -> int:
    """DF-08 / lango G1 — sentinel ya uvujaji (spec §4.2)."""
    cfg = _load(args)
    import pandas as pd

    from .asof import decision_points
    from .sentinel import run_sentinel

    timeframes = [t.strip() for t in args.timeframes.split(",")] if args.timeframes else ["H1", "H4", "D1"]

    if args.synthetic:
        from .bars import build_all_timeframes

        count = 3600 * 24 * 3
        stamps = pd.date_range("2026-08-01", periods=count, freq="1s", tz="UTC")
        bid = 1.10 + (pd.Series(range(count)) % 500) * 0.00001
        ticks = pd.DataFrame(
            {
                "timestamp": stamps.astype("datetime64[us, UTC]"),
                "bid": bid.values,
                "ask": (bid + 0.0001).values,
                "bid_vol": 1.0,
                "ask_vol": 1.0,
            }
        )
        bars_by_tf = build_all_timeframes(ticks, "EURUSD", timeframes)
        label = "synthetic"
    else:
        from .bars import read_bars

        l2_root = Path(args.l2_root).expanduser() if args.l2_root else cfg.l2_root
        symbol = (args.symbol or cfg.symbols[0]).upper()
        try:
            bars_by_tf = {tf: read_bars(l2_root, symbol, tf) for tf in timeframes}
        except FileNotFoundError as exc:
            print(f"sentinel: bars za L2 hazipo ({exc}). Kimbiza `build-l2`.", file=sys.stderr)
            return 2
        label = symbol

    points = list(decision_points(bars_by_tf["H1"]))[-int(args.points) :]
    result = run_sentinel(bars_by_tf, points, lambda bars, t: _reference_features(bars, t))
    print(f"{label} · {result.summary()}")
    for item in result.leaked[:10]:
        print(f"  ! {item['feature']} @ {item['decision_time']}", file=sys.stderr)

    # SENTINEL LAZIMA IACHE ALAMA. Ni lango la G1 — kinga kuu dhidi ya uvujaji —
    # lakini ilikuwa inachapisha mstari mmoja na kutoweka. Sahihi ya `VERIFIED`
    # inahitaji faili la kushikilia SHA256 yake; bila artifact, sahihi
    # ingelazimika kuelekeza faili lisilohusika (2026-08-10, sahihi #9).
    if args.out:
        from datetime import datetime, timezone

        from .manifest import code_rev

        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "code_rev": code_rev(),
                    "config_hash": getattr(cfg, "config_hash", ""),
                    "source": label,
                    "timeframes": timeframes,
                    "points": result.checked_points,
                    "features": result.features,
                    "leaked": len(result.leaked),
                    "passed": result.passed,
                    "detail": result.leaked[:50],
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        print(f"ushahidi: {out}")
    return 0 if result.passed else 1


def _reference_features(bars_by_tf, t):
    """Features za kumbukumbu: zinasoma bar ya as-of PEKEE (spec §4.1).

    Hizi si features za utafiti (hizo ni T2). Ni kipimo cha sentinel yenyewe:
    zikibadilika data ya baadaye ikichanganywa, tatizo liko kwenye as-of, si
    kwenye feature.
    """
    from .asof import asof_snapshot

    out = {}
    for tf, bar in asof_snapshot(bars_by_tf, t).items():
        out[f"{tf}_close"] = float(bar["close"]) if bar is not None else None
        out[f"{tf}_spread_p50"] = float(bar["spread_p50"]) if bar is not None else None
    return out


def cmd_detect_setups(args: argparse.Namespace) -> int:
    """DF-20 — SETUP-v1 juu ya bars za H1 za L2 (spec §4.3).

    Hii ndiyo hatua ya PRE-REGISTRATION: rate inaonekana HAPA, kabla ya label
    yoyote. Kutuna vigezo kufikia ~5% kunaruhusiwa sasa (§4.3 sheria 2);
    baada ya labels, kutuna kwa lolote ni selection leakage.
    """
    cfg = _load(args)
    from datetime import datetime, timezone

    from .bars import read_bars
    from .manifest import code_rev
    import pandas as pd

    from .setups import (
        SETUP_SCHEMA_VERSION,
        detect_setups,
        load_excluded_days,
        sweep_trigger,
    )
    from .splits import SplitPlan

    symbols = _symbol_list(args) or cfg.symbols
    holdout_start = SplitPlan.from_config(cfg).holdout_start
    out_root = cfg.research_root / "data" / "L4_labels" / "setups"

    # §3 `fail_action: exclude` — hukumu ya R0 inapakwa HAPA. Bila hii, siku
    # 912 ulizoziondoa (2023 ya Toleo B) na siku zote zilizofeli checks
    # zingeingia kwenye decision points kimya, na uamuzi wako ungekuwa bure.
    report_path = cfg.quality_reports_dir / "quality_report.json"
    excluded = load_excluded_days(report_path)
    if not excluded:
        print(
            f"ONYO: `{report_path}` haipo au haina siku zilizofeli — decision "
            "points zitajumuisha siku ZOTE, ikiwemo zilizofeli §3. Endesha "
            "`scripts\\audit.bat` kwanza.",
            file=sys.stderr,
        )

    if args.sweep:
        # Kutuna kwa RATE, kutoka kwenye mgawanyo — si mezani (§4.3 sheria 2).
        # HAKUNA parquet inayoandikwa hapa: hii ni hatua ya kuchagua kizingiti,
        # si ya kuzalisha decision points.
        mults = [float(x) for x in args.sweep.split(",")]
        totals: dict[float, int] = {m: 0 for m in mults}
        eligible_all = 0
        for symbol in symbols:
            try:
                bars = read_bars(cfg.l2_root, symbol, "H1")
            except FileNotFoundError:
                print(f"{symbol}: bars za H1 hazipo — `build-l2` kwanza", file=sys.stderr)
                return 2
            bars = bars[bars.index < pd.Timestamp(holdout_start, tz="UTC")]  # G2
            blocked = excluded.get(symbol.upper(), set())
            rows = sweep_trigger(cfg, bars, symbol, mults, excluded_days=blocked)
            eligible_all += int(
                detect_setups(cfg, bars, symbol, excluded_days=blocked).frame["eligible"].sum()
            )
            for row in rows:
                totals[row["min_atr_mult"]] += row["setups"]
            print(
                f"{symbol}: "
                + " · ".join(f"{r['min_atr_mult']}→{r['rate']:.1%}" for r in rows)
            )
        target = float(cfg.get("setups.target_rate"))
        print(f"\npooled (TRAIN+VAL, eligible {eligible_all:,}) · lengo ~{target:.0%}")
        for mult in mults:
            rate = totals[mult] / eligible_all if eligible_all else 0.0
            mark = "  <== karibu na lengo" if abs(rate - target) <= 0.02 else ""
            print(f"  min_atr_mult {mult:<5} → setups {totals[mult]:>9,}  rate {rate:>7.2%}{mark}")
        print(
            "\nChagua kizingiti, kiweke `setups.trigger.min_atr_mult` kwenye config, "
            "kisha endesha `detect-setups` bila `--sweep`."
        )
        return 0

    per_symbol: dict[str, dict] = {}
    pooled = {"setups": 0, "eligible": 0, "holdout": 0, "controls": 0}
    gates = {"fail_spread": 0, "fail_atr_band": 0, "fail_trigger": 0}
    for symbol in symbols:
        try:
            bars = read_bars(cfg.l2_root, symbol, "H1")
        except FileNotFoundError:
            print(f"{symbol}: bars za H1 hazipo — `build-l2` kwanza", file=sys.stderr)
            return 2
        result = detect_setups(cfg, bars, symbol, excluded_days=excluded.get(symbol.upper(), set()))
        frame = result.frame

        # G2: decision points za HOLDOUT zinawekwa alama SASA — mjenzi wa
        # labels anazikataa. Kuchuja hapa kungeficha ukubwa wa holdout.
        frame["in_holdout"] = frame["decision_time"].dt.date >= holdout_start
        n_holdout = int((frame["is_setup"] & frame["in_holdout"]).sum())

        path = out_root / f"symbol={symbol}" / "setups.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path)

        # RATE INAHESABIWA KWA TRAIN+VAL PEKEE — hesabu na mwenzake.
        # Kipimo cha kwanza kilitoa numerator bila holdout lakini denominator
        # NAYO — holdout ni ~miaka 2 kati ya 10.6, kwa hiyo rate ilikuwa
        # imeshushwa kwa ~20% kimya (2026-08-11).
        train = frame[~frame["in_holdout"]]
        tv = {
            "bars_day_excluded": int(train["day_excluded"].sum()),
            "eligible": int(train["eligible"].sum()),
            "setups": int(train["is_setup"].sum()),
            "controls": int(train["is_control"].sum()),
            "fail_spread": int((train["eligible"] & ~train["spread_ok"]).sum()),
            "fail_atr_band": int((train["eligible"] & ~train["atr_ok"]).sum()),
            "fail_trigger": int((train["eligible"] & ~train["trigger_ok"]).sum()),
        }
        tv["rate"] = tv["setups"] / tv["eligible"] if tv["eligible"] else 0.0

        per_symbol[symbol] = {**result.stats, "setups_holdout": n_holdout, "train_val": tv}
        pooled["setups"] += tv["setups"]
        pooled["eligible"] += tv["eligible"]
        pooled["controls"] += tv["controls"]
        pooled["holdout"] += n_holdout
        for key in gates:
            gates[key] += tv[key]
        print(
            f"{symbol} · {result.rule_id} · TRAIN+VAL: eligible {tv['eligible']} · "
            f"setups {tv['setups']} ({tv['rate']:.2%}) · control {tv['controls']} · "
            f"holdout {n_holdout} · siku zilizofeli §3 {tv['bars_day_excluded']} bars"
        )

    target = float(cfg.get("setups.target_rate"))
    pooled_setups = pooled["setups"]
    pooled_eligible = pooled["eligible"]
    pooled_holdout = pooled["holdout"]
    pooled_rate = pooled_setups / pooled_eligible if pooled_eligible else 0.0
    summary = {
        "rule_id": str(cfg.get("setups.rule_id")),
        "schema": SETUP_SCHEMA_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_hash": cfg.config_hash,
        "code_rev": code_rev(),
        "holdout_start": holdout_start.isoformat(),
        "quality_report": str(report_path),
        "excluded_symbols_with_days": {k: len(v) for k, v in sorted(excluded.items())},
        "target_rate": target,
        "pooled_rate_train_val": pooled_rate,
        "pooled_setups_train_val": pooled_setups,
        "pooled_setups_holdout": pooled_holdout,
        "pooled_controls_train_val": pooled["controls"],
        # Kila gate PEKE YAKE kati ya bars zenye viashiria (TRAIN+VAL). Hizi
        # ndizo namba za kutuna: gate inayokataa chache ndiyo iliyolegea.
        "gate_rejects_train_val": gates,
        "per_symbol": per_symbol,
    }
    report_path = cfg.path_of("storage.reports_root") / "r1" / "setup_rates.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(
        f"\npooled (TRAIN+VAL): setups {pooled_setups} / eligible {pooled_eligible} "
        f"= {pooled_rate:.2%} · lengo ~{target:.0%} · holdout (zimetengwa) {pooled_holdout}"
    )
    print("gate inayokataa NGAPI (peke yake, kati ya eligible za TRAIN+VAL):")
    for name, count in gates.items():
        share = count / pooled_eligible if pooled_eligible else 0.0
        print(f"  {name:<16} {count:>9,}  ({share:.1%} zinakataliwa)")
    print(f"ushahidi: {report_path}")
    # Rate iliyo mbali mara mbili na lengo ni dalili ya vigezo vibaya — ONYO,
    # si kizuizi: PD ndiye anayeamua kutuna (kabla ya labels) au kukubali.
    if pooled_rate > 2 * target or pooled_rate < target / 2:
        print(
            f"ONYO: rate {pooled_rate:.2%} iko mbali na lengo {target:.0%} — "
            "tuna vigezo vya config (§4.3 inaruhusu KABLA ya labels), au kubali kwa maandishi.",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_build_labels(args: argparse.Namespace) -> int:
    """DF-09/10/11 — L4: labels kwa path ya ticks (spec §5).

    TRAIN+VAL PEKEE (G2). Inaendelea ilipoishia: hali ni ya `(symbol, mwaka)`,
    kwa hiyo kukatika kunapoteza mwaka mmoja, si kazi ya masaa.
    """
    cfg = _load(args)
    from datetime import datetime, timezone

    import pandas as pd

    from .label_build import (
        LABEL_BUILD_VERSION,
        build_labels_for_symbol,
        holdout_guard,
        load_state,
        save_state,
        split_by_year,
    )
    from .manifest import code_rev
    from .splits import SplitPlan

    # DF-20 (§4.3 sheria 5): "R1 haianzi kabla sheria hii haijasainiwa na PD".
    # Hii ndiyo kinga ya darasa la tatu la uvujaji; haiwezi kuwa ya hiari.
    if not args.skip_signature_check:
        from src.governance.signatures import LEDGER, load as load_signatures

        root = Path(__file__).resolve().parents[2]
        signed = {
            s.item
            for s in load_signatures(root / LEDGER)
            if s.decision in ("APPROVED", "VERIFIED")
        }
        if "DF-20" not in signed:
            print(
                "DF-20 haijasainiwa. Sheria ya setup ni PRE-REGISTRATION (§4.3 sheria 5): "
                "label ikihesabiwa kabla ya sahihi, kila namba ya R1+ ni ya baada ya "
                "ukweli.\n  scripts\\sign.bat DF-20 APPROVED --evidence "
                "research\\reports\\r1\\setup_rates.json --reason \"...\"",
                file=sys.stderr,
            )
            return 2

    symbols = _symbol_list(args) or cfg.symbols
    holdout_start = SplitPlan.from_config(cfg).holdout_start
    setups_root = cfg.research_root / "data" / "L4_labels" / "setups"
    out_root = cfg.research_root / "data" / "L4_labels" / "labels"
    state_path = out_root / "_label_state.json"

    state = load_state(state_path)
    if state.get("config_hash") not in (None, cfg.config_hash) and not args.no_resume:
        print(
            f"ONYO: hali iliyohifadhiwa ni ya config nyingine "
            f"({str(state.get('config_hash'))[:16]} vs {cfg.config_hash[:16]}) — "
            "inaanza upya.",
            file=sys.stderr,
        )
        state = {}
    done: set[str] = set() if args.no_resume else set(state.get("done", []))

    on_progress, started = _progress_printer(args.progress_every)
    totals = {"points": 0, "cells": 0, "setups": 0, "controls": 0, "ties": 0, "timeouts": 0}
    per_symbol: dict[str, Any] = {}

    for symbol in symbols:
        setups_path = setups_root / f"symbol={symbol}" / "setups.parquet"
        if not setups_path.is_file():
            print(f"{symbol}: setups hazipo — `detect-setups` kwanza", file=sys.stderr)
            return 2
        frame = pd.read_parquet(setups_path)
        frame = holdout_guard(frame, holdout_start)   # G2, mara ya pili

        for year, chunk in split_by_year(frame).items():
            key = f"{symbol}/{year}"
            target = out_root / f"symbol={symbol}"
            if key in done and (target / f"points-{year}.parquet").is_file():
                continue
            result = build_labels_for_symbol(
                cfg, cfg.l0_root, symbol, chunk, on_progress=on_progress
            )
            target.mkdir(parents=True, exist_ok=True)
            if not result.points.empty:
                result.points.to_parquet(target / f"points-{year}.parquet", index=False)
                result.barriers.to_parquet(target / f"barriers-{year}.parquet", index=False)
            done.add(key)
            save_state(state_path, done, cfg.config_hash)
            print(f"  {year}: {result.render()}")

            s = result.stats
            totals["points"] += s["points"]
            totals["cells"] += s["cells"]
            totals["setups"] += s["setups"]
            totals["controls"] += s["controls"]
            totals["ties"] += s["tie_breaks"]
            totals["timeouts"] += s["timeouts"]
            per_symbol.setdefault(symbol, {"years": {}})["years"][str(year)] = s

    tie_frac = totals["ties"] / totals["cells"] if totals["cells"] else 0.0
    timeout_frac = totals["timeouts"] / totals["cells"] if totals["cells"] else 0.0
    summary = {
        "version": LABEL_BUILD_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_hash": cfg.config_hash,
        "code_rev": code_rev(),
        "holdout_start": holdout_start.isoformat(),
        "totals": {**totals, "tie_break_frac": tie_frac, "timeout_frac": timeout_frac},
        "per_symbol": per_symbol,
    }
    report_path = cfg.path_of("storage.reports_root") / "r1" / "label_build.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print(
        f"\njumla: points {totals['points']:,} (setup {totals['setups']:,} · control "
        f"{totals['controls']:,}) · cells {totals['cells']:,} · "
        f"timeout {timeout_frac:.1%} · tie-break {tie_frac:.2%} · "
        f"{time.monotonic() - started:.0f}s"
    )
    print(f"ushahidi: {report_path}")

    rc = 0
    max_timeout = float(cfg.get("labels.barrier.max_timeout_frac"))
    if timeout_frac > max_timeout:
        print(
            f"ONYO: timeout {timeout_frac:.1%} > kikomo {max_timeout:.0%} — setup nyingi "
            "hazifiki popote ndani ya horizon (§5.5).",
            file=sys.stderr,
        )
        rc = 1
    if tie_frac > 0.01:
        # §5.2: "R1 inaripoti mara ngapi tie-break ilitumika; ikizidi 1% ya
        # labels, inapanda kwa PD — sheria isiyopimwa mzunguko wake ni dhana."
        print(
            f"ONYO: tie-break {tie_frac:.2%} > 1% — sheria ya SL-kwanza inagusa "
            "labels nyingi kuliko ilivyotarajiwa; inapanda kwa PD (§5.2).",
            file=sys.stderr,
        )
        rc = 1
    return rc


def cmd_splits(args: argparse.Namespace) -> int:
    """DF-14 / lango G2 — mpango wa splits kutoka config PEKEE (spec §7)."""
    cfg = _load(args)
    from .splits import HoldoutViolation, SplitPlan

    plan = SplitPlan.from_config(cfg)
    print(plan.render())

    # G2: hakuna fold ya TRAIN/VALIDATION inayogusa holdout wala RESERVE.
    try:
        for fold in plan.folds():
            plan.assert_trainval_only([fold.val_start, fold.val_end], purpose=f"fold F{fold.index}")
            for start, end in fold.train_ranges:
                plan.assert_trainval_only([start, end], purpose=f"train ya F{fold.index}")
    except HoldoutViolation as exc:
        print(f"G2: FAIL — {exc}", file=sys.stderr)
        return 1
    print("G2: PASS — folds zote ziko ndani ya TRAIN+VALIDATION")

    if args.out:
        payload = {
            "config_hash": cfg.config_hash,
            "data_start": plan.data_start.isoformat(),
            "trainval_end": plan.trainval_end.isoformat(),
            "holdout_start": plan.holdout_start.isoformat(),
            "embargo_bars": plan.embargo_bars,
            "folds": [
                {
                    "index": f.index,
                    "val_start": f.val_start.isoformat(),
                    "val_end": f.val_end.isoformat(),
                    "train_ranges": [[a.isoformat(), b.isoformat()] for a, b in f.train_ranges],
                }
                for f in plan.folds()
            ],
        }
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"mpango: {args.out}")
    return 0


def cmd_config_hash(args: argparse.Namespace) -> int:
    cfg = _load(args)
    print(json.dumps({"config": str(cfg.path), "config_hash": cfg.config_hash}, indent=2))
    return 0


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.data.cli",
        description="Tabaka la data L0 — recorder, hashes, normalization (spec: docs/DATA_FEATURE_STANDARD.md)",
    )
    parser.add_argument("--config", help="njia ya data.yaml (default: config/data.yaml ya repo)")
    parser.add_argument("-v", "--verbose", action="store_true")
    # `-v` ikubalike pia BAADA ya subcommand (`... record -v`) — SUPPRESS inazuia
    # default ya subparser kufuta ile ya juu.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init-research", help="§9 — simamisha muundo wa research repo", parents=[common])
    p_init.add_argument("--root", help="mzizi wa research (default: storage.research_root)")
    p_init.add_argument("--no-readme", action="store_true")
    p_init.set_defaults(func=cmd_init_research)

    p_hash = subparsers.add_parser("hash-l0", help="DF-01 — SHA256 ya partitions zote + manifest", parents=[common])
    p_hash.add_argument("--l0-root")
    p_hash.add_argument("--manifest")
    p_hash.add_argument("--no-metadata", action="store_true", help="usisome rows/tarehe za ndani")
    p_hash.add_argument(
        "--allow-mutation",
        action="store_true",
        help="ruhusu hash iliyobadilika kuandikwa (inahitaji --reason; inaingia mutation_log)",
    )
    p_hash.add_argument("--reason", help="sababu ya kuandika juu ya hash iliyopo")
    p_hash.add_argument(
        "--no-resume",
        action="store_true",
        help="rudia partitions zote hata zilizo kwenye manifest (default: ruka zisizobadilika)",
    )
    p_hash.add_argument(
        "--prune-missing",
        action="store_true",
        help="ondoa entries za partitions zilizofutwa (inahitaji --reason; inaingia mutation_log)",
    )
    p_hash.add_argument("--progress-every", type=int, default=100, help="chapisha maendeleo kila N")
    p_hash.set_defaults(func=cmd_hash_l0)

    p_verify = subparsers.add_parser("verify-l0", help="DF-01 — lango la CI: hash check", parents=[common])
    p_verify.add_argument("--manifest")
    p_verify.add_argument("--strict", action="store_true", help="partition isiyo kwenye manifest = FAIL")
    p_verify.add_argument("--require-storage", action="store_true")
    p_verify.add_argument("--progress-every", type=int, default=250, help="chapisha maendeleo kila N")
    p_verify.set_defaults(func=cmd_verify_l0)

    p_record = subparsers.add_parser("record", help="DF-04 — recorder wa feed ya broker (MT5)", parents=[common])
    p_record.add_argument("--once", action="store_true", help="poll moja badala ya mzunguko usioisha")
    p_record.add_argument("--max-polls", type=int)
    p_record.add_argument("--symbols", help="orodha ya symbols (comma) badala ya config")
    p_record.add_argument("--replay-dir", help="chanzo cha replay (parquet kwa kila symbol)")
    p_record.set_defaults(func=cmd_record)

    p_back = subparsers.add_parser(
        "backfill",
        help="DF-03 — ziba siku zilizorukwa (kalenda dhidi ya disk)",
        parents=[common],
    )
    p_back.add_argument("--from", dest="from", help="tarehe ya kuanzia (YYYY-MM-DD)")
    p_back.add_argument("--to", help="tarehe ya kuishia (YYYY-MM-DD; default: jana)")
    p_back.add_argument("--symbols", help="orodha ya symbols (comma) badala ya config")
    p_back.add_argument("--dry-run", action="store_true", help="onyesha zinazokosekana bila kuvuta")
    p_back.add_argument("--max-days", type=int, help="kikomo cha siku kwa run moja")
    p_back.add_argument("--replay-dir", help="chanzo cha replay badala ya MT5")
    p_back.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=5,
        help="kufeli mfululizo kunakosimamisha kazi (0 = usisimame)",
    )
    p_back.set_defaults(func=cmd_backfill)

    p_mt5 = subparsers.add_parser(
        "check-mt5",
        help="ukaguzi wa mazingira ya MT5: muunganisho, server, symbols",
        parents=[common],
    )
    p_mt5.set_defaults(func=cmd_check_mt5)

    p_probe = subparsers.add_parser(
        "probe-history",
        help="kina cha tick history ya broker (binary search)",
        parents=[common],
    )
    p_probe.add_argument("--symbol", help="symbol moja (default: ya kwanza ya config)")
    p_probe.add_argument("--from", dest="from", help="mwanzo wa dirisha (default: miaka 2 nyuma)")
    p_probe.add_argument("--to", help="mwisho wa dirisha (default: jana)")
    p_probe.add_argument("--out", help="andika ripoti ya JSON")
    p_probe.set_defaults(func=cmd_probe_history)

    p_fresh = subparsers.add_parser("check-freshness", help="DF-04 — ONYO la siku isiyorekodiwa", parents=[common])
    p_fresh.add_argument("--json", action="store_true")
    p_fresh.add_argument("--out", help="andika ripoti ya JSON kwenye faili")
    p_fresh.add_argument("--require-storage", action="store_true")
    p_fresh.set_defaults(func=cmd_check_freshness)

    p_inspect = subparsers.add_parser("inspect", help="DF-02 — schema moja kutoka Toleo A/B", parents=[common])
    p_inspect.add_argument("paths", nargs="+")
    p_inspect.set_defaults(func=cmd_inspect)

    # ---------------------------- T1 (R0) ---------------------------------

    p_cal = subparsers.add_parser(
        "build-calendar",
        help="RS-03 — kalenda ya sessions kutoka DATA (§3)",
        parents=[common],
    )
    p_cal.add_argument("--l0-root")
    p_cal.add_argument("--out-dir", help="default: storage.reports_root/quality")
    p_cal.add_argument("--symbols", help="orodha ya symbols (comma)")
    p_cal.add_argument("--limit", type=int, help="partitions chache kwa jaribio")
    p_cal.add_argument("--no-cache", action="store_true", help="usitumie/usiandike cache ya scan")
    p_cal.add_argument("--progress-every", type=int, default=100)
    p_cal.set_defaults(func=cmd_build_calendar)

    p_l1 = subparsers.add_parser(
        "check-l1",
        help="DF-05 — checks za ubora + quality_report.json (§3)",
        parents=[common],
    )
    p_l1.add_argument("--l0-root")
    p_l1.add_argument("--out-dir")
    p_l1.add_argument("--calendar", help="session_calendar.json (default: out-dir)")
    p_l1.add_argument("--symbols")
    p_l1.add_argument("--limit", type=int)
    p_l1.add_argument("--no-cache", action="store_true")
    p_l1.add_argument("--progress-every", type=int, default=100)
    p_l1.set_defaults(func=cmd_check_l1)

    p_status = subparsers.add_parser(
        "audit-status",
        help="hatua za R0 zilizokamilika (baada ya kukatika)",
        parents=[common],
    )
    p_status.add_argument("--out-dir")
    p_status.set_defaults(func=cmd_audit_status)

    p_prof = subparsers.add_parser(
        "symbol-profile",
        help="wasifu wa symbol kwa mwaka — kugundua chanzo kilipobadilika",
        parents=[common],
    )
    p_prof.add_argument("--calendar")
    p_prof.add_argument("--out-dir")
    p_prof.add_argument("--symbols")
    p_prof.add_argument("--jump", type=float, default=0.05, help="hatua inayotangazwa (0.05 = 5%%)")
    p_prof.set_defaults(func=cmd_symbol_profile)

    p_r0 = subparsers.add_parser(
        "r0-summary",
        help="R0 dhidi ya vigezo vyake — ushahidi wa sahihi ya T1",
        parents=[common],
    )
    p_r0.add_argument("--out-dir")
    p_r0.set_defaults(func=cmd_r0_summary)

    p_stats = subparsers.add_parser(
        "quality-stats",
        help="DF-05 — mgawanyo wa L1 → vizingiti kutoka DATA (haisomi parquet)",
        parents=[common],
    )
    p_stats.add_argument("--report", help="quality_report.json (default: out-dir)")
    p_stats.add_argument("--out-dir")
    p_stats.add_argument(
        "--reason",
        help="badala ya mgawanyo, orodhesha partitions zilizofeli kwa sababu hii "
        "(mf. bad_timestamps, quote_violation, intrasession_gap)",
    )
    p_stats.add_argument("--limit", type=int, default=40, help="mistari ya kuonyesha na --reason")
    p_stats.add_argument(
        "--what-if",
        help="jaribu vizingiti: `coverage=0.98,gaps=7200` — inaonyesha siku ngapi zingefeli",
    )
    p_stats.set_defaults(func=cmd_quality_stats)

    p_var = subparsers.add_parser(
        "compare-variants",
        help="RS-03 — Toleo A ↔ Toleo B baada ya normalization (§2.1)",
        parents=[common],
    )
    p_var.add_argument("--l0-root")
    p_var.add_argument("--out-dir")
    p_var.set_defaults(func=cmd_compare_variants)

    p_prov = subparsers.add_parser(
        "compare-provenance",
        help="R0 — aggregator ↔ broker kwa siku zinazopishana (§2.2)",
        parents=[common],
    )
    p_prov.add_argument("--l0-root")
    p_prov.add_argument("--out-dir")
    p_prov.add_argument("--symbols")
    p_prov.add_argument("--progress-every", type=int, default=5)
    p_prov.set_defaults(func=cmd_compare_provenance)

    p_l2 = subparsers.add_parser(
        "build-l2", help="DF-06 — bars za TF 7 kutoka ticks (§4)", parents=[common]
    )
    p_l2.add_argument("--l0-root")
    p_l2.add_argument("--l2-root")
    p_l2.add_argument("--symbols")
    p_l2.add_argument("--timeframes", help="default: bars.timeframes ya config")
    p_l2.add_argument(
        "--max-rows-per-chunk",
        type=int,
        default=5_000_000,
        help="ticks kwa kipande kimoja (kumbukumbu); mipaka ni ya SIKU za UTC",
    )
    p_l2.add_argument(
        "--adopt-existing",
        action="store_true",
        help="andikisha bars zilizopo (TF zote) kwenye hali bila kuzijenga upya",
    )
    p_l2.add_argument(
        "--build-after-adopt",
        action="store_true",
        help="baada ya kuandikisha, endelea kujenga zilizobaki",
    )
    p_l2.add_argument(
        "--no-resume",
        action="store_true",
        help="jenga upya symbols zote hata zilizokwisha (default: ruka zisizobadilika)",
    )
    p_l2.add_argument("--progress-every", type=int, default=1)
    p_l2.set_defaults(func=cmd_build_l2)

    p_sent = subparsers.add_parser(
        "sentinel", help="DF-08 / G1 — sentinel ya uvujaji (§4.2)", parents=[common]
    )
    p_sent.add_argument("--l2-root")
    p_sent.add_argument("--symbol")
    p_sent.add_argument("--timeframes", help="default: H1,H4,D1")
    p_sent.add_argument("--points", type=int, default=50, help="decision points za mwisho")
    p_sent.add_argument(
        "--synthetic",
        action="store_true",
        help="data ya kutengeneza badala ya L2 — lango la CI linalofanya kazi bila storage",
    )
    p_sent.add_argument(
        "--out",
        help="andika ushahidi (sentinel.json) — sahihi ya VERIFIED inahitaji faili la kushikilia",
    )
    p_sent.set_defaults(func=cmd_sentinel)

    p_setups = subparsers.add_parser(
        "detect-setups",
        help="DF-20 — SETUP-v1: decision points + control (§4.3) — KABLA ya labels",
        parents=[common],
    )
    p_setups.add_argument("--symbols", help="orodha ya symbols, comma separated")
    p_setups.add_argument(
        "--sweep",
        help="rate kwa kila min_atr_mult (mf. 1.0,1.5,2.0,2.5) — kuchagua kizingiti; "
        "haiandiki decision points",
    )
    p_setups.set_defaults(func=cmd_detect_setups)

    p_labels = subparsers.add_parser(
        "build-labels",
        help="DF-09/10/11 — L4: labels kwa path ya ticks (§5). TRAIN+VAL pekee",
        parents=[common],
    )
    p_labels.add_argument("--symbols", help="orodha ya symbols, comma separated")
    p_labels.add_argument("--no-resume", action="store_true", help="anza upya, puuza hali")
    p_labels.add_argument("--progress-every", type=int, default=1000)
    p_labels.add_argument(
        "--skip-signature-check",
        action="store_true",
        help="kwa tests pekee — DF-20 ni pre-registration ya lazima (§4.3 sheria 5)",
    )
    p_labels.set_defaults(func=cmd_build_labels)

    p_split = subparsers.add_parser(
        "splits", help="DF-14 / G2 — mpango wa splits + holdout guard (§7)", parents=[common]
    )
    p_split.add_argument("--out", help="andika mpango kama JSON")
    p_split.set_defaults(func=cmd_splits)

    p_cfg = subparsers.add_parser("config-hash", help="fingerprint ya config/data.yaml", parents=[common])
    p_cfg.set_defaults(func=cmd_config_hash)

    return parser


def _force_utf8() -> None:
    """Lazimisha UTF-8 kwenye stdout/stderr.

    Windows: Python inachagua encoding kwa **aina ya lengo**. Console inaweza
    kuwa UTF-8, lakini output ikielekezwa kwenye PIPE au FAILI (mfano
    `audit.bat` inayoandika log kwa `Tee-Object`), inarudi kwenye cp1252 ya
    locale — na `→`, `≥`, `↔` hazipo humo. Matokeo: `UnicodeEncodeError`
    inayoua amri **baada ya kazi yote kumalizika**, ikipoteza ripoti ya mwisho.

    `errors="replace"` ni kinga ya mwisho: console ya zamani isiyoweza kuonyesha
    herufi fulani ionyeshe `?` badala ya kuanguka. Ripoti ya JSON haiathiriki —
    inaandikwa UTF-8 moja kwa moja, si kupitia stdout.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):  # stream isiyokubali — si sababu ya kusimama
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))
    try:
        return int(args.func(args))
    except (ConfigError, ManifestError) as exc:
        print(f"HITILAFU: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
