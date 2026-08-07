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
    python -m src.data.cli compare-variants   # RS-03 — Toleo A ↔ Toleo B baada ya normalization
    python -m src.data.cli build-l2           # DF-06 — bars za TF 7 kutoka ticks
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
    diff_path.write_text(json.dumps(build.comparison, indent=2) + "\n", encoding="utf-8")

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


def cmd_quality_stats(args: argparse.Namespace) -> int:
    """DF-05 — mgawanyo wa thamani za L1 → vizingiti vinavyotokana na DATA."""
    cfg = _load(args)
    from .quality import render_threshold_study, threshold_study

    out_dir = _quality_dir(args, cfg)
    path = Path(args.report).expanduser() if args.report else out_dir / "quality_report.json"
    if not path.is_file():
        print(f"quality_report.json haipo: {path} — endesha `check-l1` kwanza.", file=sys.stderr)
        return 2

    study = threshold_study(json.loads(path.read_text(encoding="utf-8")))
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


def cmd_build_l2(args: argparse.Namespace) -> int:
    """DF-06 — bars za TF 7 kutoka ticks (spec §4)."""
    cfg = _load(args)
    from .audit import build_l2

    l0_root = Path(args.l0_root).expanduser() if args.l0_root else cfg.l0_root
    l2_root = Path(args.l2_root).expanduser() if args.l2_root else cfg.l2_root
    on_progress, started = _progress_printer(args.progress_every)

    builds = build_l2(
        cfg,
        l0_root=l0_root,
        l2_root=l2_root,
        symbols=_symbol_list(args),
        timeframes=[t.strip() for t in args.timeframes.split(",")] if args.timeframes else None,
        max_rows_per_chunk=args.max_rows_per_chunk,
        on_progress=on_progress,
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

    p_stats = subparsers.add_parser(
        "quality-stats",
        help="DF-05 — mgawanyo wa L1 → vizingiti kutoka DATA (haisomi parquet)",
        parents=[common],
    )
    p_stats.add_argument("--report", help="quality_report.json (default: out-dir)")
    p_stats.add_argument("--out-dir")
    p_stats.set_defaults(func=cmd_quality_stats)

    p_var = subparsers.add_parser(
        "compare-variants",
        help="RS-03 — Toleo A ↔ Toleo B baada ya normalization (§2.1)",
        parents=[common],
    )
    p_var.add_argument("--l0-root")
    p_var.add_argument("--out-dir")
    p_var.set_defaults(func=cmd_compare_variants)

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
        default=20_000_000,
        help="ticks kwa kipande kimoja (kumbukumbu); mipaka ni ya SIKU za UTC",
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
    p_sent.set_defaults(func=cmd_sentinel)

    p_split = subparsers.add_parser(
        "splits", help="DF-14 / G2 — mpango wa splits + holdout guard (§7)", parents=[common]
    )
    p_split.add_argument("--out", help="andika mpango kama JSON")
    p_split.set_defaults(func=cmd_splits)

    p_cfg = subparsers.add_parser("config-hash", help="fingerprint ya config/data.yaml", parents=[common])
    p_cfg.set_defaults(func=cmd_config_hash)

    return parser


def main(argv: list[str] | None = None) -> int:
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
