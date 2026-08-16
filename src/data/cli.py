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
import hashlib
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
        # `Authorization failed` haimaanishi code imevunjika; inamaanisha
        # terminal haijaingia kwenye akaunti yoyote NA hakuna sifa kwenye
        # environment. Ujumbe wa MT5 pekee hausemi hilo, na hausemi njia mbili
        # za kulitatua — kwa hiyo unasemwa hapa.
        if "uthoriz" in str(exc).lower() or "authoriz" in str(exc).lower():
            login_var = str(cfg.get("recorder.mt5.login_env", "ELITEFX_MT5_LOGIN"))
            print(
                "\n  Sababu: terminal haijaingia kwenye akaunti, na sifa hazipo kwenye\n"
                "  environment. Njia mbili, chagua MOJA:\n\n"
                "  1. Fungua MetaTrader 5 kwa mkono, ingia kwenye akaunti, iache wazi.\n"
                f"     (`{login_var}` haijawekwa, kwa hiyo code inategemea session ya terminal.)\n\n"
                "  2. Weka sifa kwenye `scripts\\env.local.bat` (HAIPUSHWI — G13).\n"
                "     ANDIKA THAMANI MOJA KWA MOJA, BILA mabano — cmd ya Windows\n"
                "     inasoma `<` kama redirect ya faili, si kama mahali pa kujaza:\n\n"
                f"       set {login_var}=12345678\n"
                f"       set {cfg.get('recorder.mt5.password_env', 'ELITEFX_MT5_PASSWORD')}=nenoLakoLaSiri\n"
                f"       set {cfg.get('recorder.mt5.server_env', 'ELITEFX_MT5_SERVER')}=JinaLaServer-Demo\n\n"
                "     (namba na maneno hapo juu ni MIFANO — badilisha na yako.)\n"
                "     kisha `scripts\\env.local.bat` kabla ya kuendesha amri.",
                file=sys.stderr,
            )
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

        if args.catalogue:
            ok = _print_catalogue(cfg, sorted(available), source, args) and ok
        return 0 if ok else 1
    finally:
        source.shutdown()


def _underlyings(name: str) -> tuple[str, ...]:
    """Sarafu/underlyings ndani ya jina la symbol.

    Jozi ya FX ya herufi 6 inatoa mbili; kitu kingine chochote (index,
    commodity) kinahesabiwa kama underlying MOJA yenye jina lake. Kukisia
    zaidi ya hapo kungeleta makosa kimya kwenye majina yasiyo ya kawaida.
    """
    clean = "".join(ch for ch in name.upper() if ch.isalnum())
    if len(clean) == 6 and clean.isalpha():
        return (clean[:3], clean[3:])
    return (clean,)


def _print_catalogue(cfg, available: list[str], source, args) -> bool:
    """T4 hatua 1 — orodha ya broker ikipangwa kwa UNDERLYINGS MPYA.

    Sheria ya 3 ya `docs/T4_CROSS_SECTION.md`: symbol inayoleta sarafu
    isiyokuwepo inashinda jozi mpya ya sarafu zilizopo. Sababu si ladha —
    blocs ndio kizuizi, si rows, na jozi za sarafu zilezile zinaongeza rows
    pekee. Upangaji unafanywa HAPA, na jicho, ili usiwe wa kubahatisha.

    **Hakuna kinachochaguliwa kwa `R`, `p_tp` au trendiness.** Jedwali hili
    halijui lolote kati ya hivyo, na ndiyo maana linaweza kutangazwa kabla.
    """
    suffix = str(cfg.get("recorder.mt5.symbol_suffix", "") or "")
    tuna: set[str] = set()
    for symbol in cfg.symbols:
        tuna.update(_underlyings(symbol))

    rows = []
    for name in available:
        bare = name[: -len(suffix)] if suffix and name.endswith(suffix) else name
        parts = _underlyings(bare)
        mpya = [p for p in parts if p not in tuna]
        rows.append({"symbol": name, "bare": bare, "underlyings": list(parts), "new": mpya})

    rows.sort(key=lambda r: (-len(r["new"]), r["bare"]))
    zenye_mpya = [r for r in rows if r["new"]]

    print(f"\nORODHA YA BROKER — symbols {len(rows)} zinapatikana")
    print(f"tunazo underlyings {len(tuna)}: {', '.join(sorted(tuna))}\n")
    print(f"   {'symbol':<14} {'underlyings':<14} {'MPYA'}")
    for row in zenye_mpya[: args.catalogue_limit]:
        print(f"   {row['symbol']:<14} {'/'.join(row['underlyings']):<14} "
              f"{', '.join(row['new'])}")
    if len(zenye_mpya) > args.catalogue_limit:
        print(f"   … na {len(zenye_mpya) - args.catalogue_limit} nyingine "
              f"(`--catalogue-limit` kuona zaidi)")
    print(f"\n   zinazoleta underlying MPYA : {len(zenye_mpya)}")
    print(f"   zisizoleta lolote jipya    : {len(rows) - len(zenye_mpya)}"
          "   <- hizi zinaongeza rows, si blocs")

    out_path = cfg.path_of("storage.reports_root") / "r4" / "broker_catalogue.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "server": source.source_identity(),
                "symbol_suffix": suffix,
                "n_available": len(rows),
                "underlyings_tulizonazo": sorted(tuna),
                "symbols": rows,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nushahidi: {out_path}")
    mfano = zenye_mpya[0]["symbol"] if zenye_mpya else "EURUSD"
    print(f"hatua: `probe-history --symbol {mfano} --from 2016-01-01` kwa kila mgombea.")
    return True


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
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0 if report.get("earliest_available") else 1


def cmd_check_freshness(args: argparse.Namespace) -> int:
    cfg = _load(args)
    report = check_freshness(cfg, require_storage=args.require_storage)
    if args.json:
        print(json.dumps(report.to_json(), indent=2))
    else:
        print(report.render())
    if args.out:
        Path(args.out).write_text(json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8", newline="\n")
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
    target.write_text(json.dumps(study, indent=2) + "\n", encoding="utf-8", newline="\n")
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
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
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
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

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
        # Sahihi ya DF-20 inahusu SHERIA ya setups, si faili nzima ya config.
        # Bila hii, kigezo cha `labels` kikiongezwa sahihi inaonekana imevunjika
        # ingawa sheria haijaguswa (ilitokea 2026-08-13).
        "section_hashes": {k: cfg.section_hash(k) for k in ("setups", "quality", "splits")},
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
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")

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
    totals = {
        "points": 0, "cells": 0, "setups": 0, "controls": 0, "ties": 0, "timeouts": 0,
        "m1_cells": 0, "m1_disagree": 0, "m1_ambiguous": 0,
    }
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
            totals["m1_cells"] += s["m1_cells"]
            totals["m1_disagree"] += s["m1_disagree"]
            totals["m1_ambiguous"] += s["m1_ambiguous"]
            per_symbol.setdefault(symbol, {"years": {}})["years"][str(year)] = s

    tie_frac = totals["ties"] / totals["cells"] if totals["cells"] else 0.0
    timeout_frac = totals["timeouts"] / totals["cells"] if totals["cells"] else 0.0
    m1_frac = totals["m1_disagree"] / totals["m1_cells"] if totals["m1_cells"] else 0.0
    summary = {
        "version": LABEL_BUILD_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_hash": cfg.config_hash,
        "section_hashes": {k: cfg.section_hash(k) for k in ("labels", "setups", "splits")},
        "code_rev": code_rev(),
        "holdout_start": holdout_start.isoformat(),
        "totals": {
            **totals,
            "tie_break_frac": tie_frac,
            "timeout_frac": timeout_frac,
            "m1_disagree_frac": m1_frac,
        },
        "per_symbol": per_symbol,
    }
    report_path = cfg.path_of("storage.reports_root") / "r1" / "label_build.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8", newline="\n")

    print(
        f"\njumla: points {totals['points']:,} (setup {totals['setups']:,} · control "
        f"{totals['controls']:,}) · cells {totals['cells']:,} · "
        f"timeout {timeout_frac:.1%} · tie-break {tie_frac:.2%} · "
        f"M1≠tick {m1_frac:.2%} (cells {totals['m1_cells']:,}) · "
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


def cmd_r1_summary(args: argparse.Namespace) -> int:
    """R1 — ukaguzi wa labels dhidi ya vigezo vyake (T2, RS-04/DF-21/K1-07).

    Kama `r0-summary`: haisomi ticks, inasoma kile kilichoandikwa. Ushahidi wa
    sahihi ya exit ya T2.
    """
    cfg = _load(args)
    import pandas as pd

    from .r1 import build_report, load_build_stats, load_labels
    from .splits import SplitPlan

    labels_root = cfg.research_root / "data" / "L4_labels" / "labels"
    points, barriers = load_labels(labels_root, _symbol_list(args))
    if barriers.empty:
        print(f"hakuna labels chini ya {labels_root} — `build-labels` kwanza", file=sys.stderr)
        return 2

    reports_root = cfg.path_of("storage.reports_root") / "r1"
    stats = load_build_stats(reports_root / "label_build.json")
    cost_grid = (
        [float(x) for x in args.cost_pips.split(",")] if args.cost_pips else [0.0, 0.5, 1.0]
    )
    plan = SplitPlan.from_config(cfg)
    report = build_report(
        cfg,
        points,
        barriers,
        plan.holdout_start,
        build_stats=stats,
        cost_grid=cost_grid,
        folds=plan.folds(),
    )
    p = report.payload
    if not p:
        for problem in report.problems:
            print(f"HITILAFU: {problem}", file=sys.stderr)
        return 2

    t = p["totals"]
    print("R1 — UKAGUZI WA LABELS (TRAIN+VAL pekee, G2)\n")
    print(
        f"points {t['points']:,} (setup {t['setups']:,} · control {t['controls']:,}) · "
        f"cells {t['cells']:,} · timeout {t['timeout_frac']:.2%} · "
        f"tie-break {t['tie_breaks']} ({t['tie_break_frac']:.2%})"
    )
    print(f"E[R] gross: setups {t['ev_r_gross_setups']:+.4f} R · zote {t['ev_r_gross']:+.4f} R\n")

    print("1. JIOMETRI (RS-04) — p_tp BILA timeout dhidi ya sl/(sl+tp)")
    rates = pd.DataFrame(p["base_rates"])
    print(f"   {'sl':>5} {'tp':>5} {'n':>8} {'timeout':>8} {'p_tp':>7} {'jiometri':>9} {'diff':>7} {'z':>7}")
    for _, r in rates.iterrows():
        print(
            f"   {r['sl_atr']:>5.2f} {r['tp_atr']:>5.2f} {int(r['n']):>8,} "
            f"{r['timeout_frac']:>7.1%} {r['p_tp']:>7.3f} {r['geometry']:>9.3f} "
            f"{r['diff']:>+7.3f} {r['z']:>+7.1f}"
        )
    kikomo = int(cfg.get("labels.barrier.min_labels_per_cell"))
    print(f"   cells ndogo kuliko zote (pooled): {t['min_labels_per_cell']:,} (kikomo {kikomo})")

    cov = p.get("cell_coverage") or []
    if cov:
        pooled = [r for r in cov if r["scope"] == "pooled"]
        symbol_rows = [r for r in cov if r["scope"] == "symbol"]
        print("\n1b. LABELS KWA CELL x FOLD (pooled) — KIGEZO, mizani ya mafunzo")
        for row in sorted(pooled, key=lambda r: r["fold"]):
            alama = "  <-- chini ya kikomo" if row["n_min"] < kikomo else ""
            print(
                f"   fold {row['fold']}  cell ndogo kuliko zote {row['n_min']:>7,}"
                f"  (cells {row['cells']:>9,}){alama}"
            )
        print(f"   ndogo kuliko zote: {t['min_labels_per_cell_fold']:,} (kikomo {kikomo})")

        if symbol_rows:
            print("\n1c. ...na kwa SYMBOL ndani ya fold — uchunguzi, si kigezo")
            for row in sorted(symbol_rows, key=lambda r: r["n_min"])[:5]:
                alama = "  <--" if row["n_min"] < kikomo else ""
                print(
                    f"   fold {row['fold']}  {row['symbol']:<8} {row['n_min']:>6,}{alama}"
                )
            print(
                f"   ndogo kuliko zote katika michanganyiko {len(symbol_rows)}: "
                f"{t['min_labels_per_cell_symbol_fold']:,}"
            )
    print()

    print("2. UTULIVU KWA MIAKA")
    for row in p["year_stability"]:
        print(
            f"   {row['year']}  cells {row['cells']:>8,}  p_tp {row['p_tp']:.3f}  "
            f"timeout {row['timeout_frac']:.1%}  E[R] {row['ev_r']:+.4f}"
        )
    ys = [r["p_tp"] for r in p["year_stability"]]
    if ys:
        print(f"   mwanya: {min(ys):.3f} → {max(ys):.3f}  (upana {max(ys) - min(ys):.3f})\n")

    svc = p["setup_vs_control"]
    if svc:
        print("3. SETUP DHIDI YA CONTROL (DF-20)")
        for name in ("setup", "control"):
            s = svc[name]
            print(
                f"   {name:<8} cells {s['cells']:>9,}  p_tp {s['p_tp']:.4f}  "
                f"timeout {s['timeout_frac']:.1%}  E[R] {s['ev_r']:+.4f}  "
                f"ATR p50 {s['atr_pips_median']:.1f} pips"
            )
        print(
            f"   tofauti p_tp {svc['delta_p_tp']:+.4f} (z {svc['delta_z']:+.1f}) · "
            f"E[R] {svc['delta_ev_r']:+.4f} R\n"
        )

    q = p["quantile_mid_vs_trade"]
    if q:
        print("4. QUANTILE: MID DHIDI YA BEI YA TRADE (§5.1) — kwa ISHARA ya trade")
        print(
            f"   {'symbol':<8} {'spread':>7} {'ATR':>8} {'shift p50':>10} {'p90':>8} "
            f"{'inayotarajiwa':>14} {'pooled':>9}"
        )
        for row in q:
            print(
                f"   {row['symbol']:<8} {row['spread_entry_p50']:>6.2f}p "
                f"{row['atr_pips_p50']:>7.1f}p {row['shift_p50']:>10.4f} "
                f"{row['shift_p90']:>8.4f} {row['shift_expected_p50']:>14.4f} "
                f"{row['pooled_mean_diff']:>+9.4f}"
            )
        print(
            "   `shift` = direction x (mid - trade), units za ATR. `pooled` ni wastani BILA\n"
            "   ishara — uko hapo ili ionekane kwa nini ni ~0: BUY na SELL zinafutana.\n"
        )

    f = p["fill_bootstrap"]
    if f:
        print(f"5. L-C — FILL (§5.3; cap ya stop {f['cap_stop_pips']} pips kutoka risk.yaml)")
        if "stop_sl" in f:
            s = f["stop_sl"]
            print(
                f"   SL (stop): n {s['n']:>9,}  p50 {s['p50']:.2f}  p90 {s['p90']:.2f}  "
                f"p99 {s['p99']:.2f}  max {s['max']:.1f} pips"
            )
            print(
                f"              ndani ya cap: {s['within_cap']:.2%}  "
                f"(nje ya cap: {s['over_cap']:,})"
            )
        if "limit_tp" in f:
            s = f["limit_tp"]
            print(f"   TP (limit): n {s['n']:>8,}  p50 {s['p50']:.2f}  p99 {s['p99']:.2f} pips")
        print(f"   market: prior {f['market_prior']} — §5.3 haikisii kwa historia\n")

    b = p["quality_buckets"]
    if b:
        print("6. L-D — BUCKETS kwa gharama (commission+swap PEKEE; spread imo kwenye path)")
        for cost, row in b.items():
            print(
                f"   cost {cost:>4} pips  E[R] {row['ev_r_net']:+.4f}  "
                f"A+ {row['A+']:.1%}  A {row['A']:.1%}  B {row['B']:.1%}  "
                f"reject {row['reject']:.1%}"
            )
        print("   namba halisi ya gharama ni ya RCE (T7) — hii ni unyeti\n")

    m1 = p["m1_vs_tick"]
    if m1 and m1.get("cells"):
        print("7. M1 DHIDI YA TICK")
        print(
            f"   cells {m1['cells']:,} zilizoangaliwa mara mbili · "
            f"hazikubaliani {m1['disagree']:,} ({m1['disagree_frac']:.2%}) · "
            f"M1 moja iligusa zote mbili {m1['ambiguous']:,}\n"
        )

    for note in p["notes"]:
        print(f"kumbuka: {note}")
    for problem in p["problems"]:
        print(f"HITILAFU: {problem}", file=sys.stderr)

    out_path = reports_root / "r1_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(p, indent=2, default=str), encoding="utf-8", newline="\n")
    print(f"\nushahidi: {out_path}")
    print(f"HUKUMU: {'PASS' if report.ok else 'FAIL'}")
    return 0 if report.ok else 1


def cmd_r1_ev(args: argparse.Namespace) -> int:
    """EV kwa kila cell ya grid — **inasoma tu** `r1_summary.json` iliyopo.

    Haiandiki chochote na haihesabu upya. Sababu si uvivu: `r1_summary.json`
    ndilo ushahidi wa sahihi #12–#17, na kuliandika upya kungehamisha hash yake
    na kuvunja sahihi sita mara moja (somo la #11/#18). Ripoti iliyosainiwa
    inasomwa, haiguswi.

    `ev_r` ilikuwepo ndani ya JSON tangu mwanzo; jedwali la R1 halikuionyesha.
    Ni namba ya uamuzi kuliko zote: `p_tp` dhidi ya jiometri inaeleza kama
    ulimwengu ni wa haki, `ev_r` inaeleza kama BIASHARA inalipa.
    """
    cfg = _load(args)
    path = cfg.path_of("storage.reports_root") / "r1" / "r1_summary.json"
    if not path.is_file():
        print(f"{path} haipo — `r1-summary` kwanza", file=sys.stderr)
        return 2
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("base_rates") or []
    if not rows:
        print("ripoti haina base_rates", file=sys.stderr)
        return 2

    atr_p50 = args.atr_pips
    cost = args.cost_pips
    print(f"EV KWA KILA CELL — gharama {cost} pips (commission+swap), ATR p50 {atr_p50} pips")
    print("spread IMO ndani ya path (§5.2); hii ni commission pekee juu yake.\n")
    print(f"   {'sl':>5} {'tp':>5} {'p_tp':>7} {'timeout':>8} {'EV gross':>9} "
          f"{'cost R':>8} {'EV net':>8} {'p_tp inayohitajika':>19} {'pengo':>7}")

    ranked = []
    for r in rows:
        sl, tp = float(r["sl_atr"]), float(r["tp_atr"])
        ev_gross = float(r["ev_r"])
        sl_pips = sl * atr_p50
        cost_r = cost / sl_pips if sl_pips else float("nan")
        ev_net = ev_gross - cost_r
        # p_tp inayohitajika ili EV_net = 0, ikishikilia timeout na E[R|timeout]
        # kama zilivyo. Hii ndiyo "umbali" halisi ambao model inapaswa kuufunika.
        f_to = float(r["timeout_frac"])
        resolved = 1.0 - f_to
        ev_timeout = ev_gross - resolved * (
            float(r["p_tp"]) * (tp / sl) - (1.0 - float(r["p_tp"]))
        )
        needed = (
            (cost_r - ev_timeout) / resolved + 1.0
        ) / (tp / sl + 1.0) if resolved else float("nan")
        ranked.append((ev_net, sl, tp, r, cost_r, ev_gross, needed))
        print(
            f"   {sl:>5.2f} {tp:>5.2f} {float(r['p_tp']):>7.3f} {f_to:>7.1%} "
            f"{ev_gross:>+9.4f} {cost_r:>8.4f} {ev_net:>+8.4f} "
            f"{needed:>19.3f} {needed - float(r['p_tp']):>+7.3f}"
        )

    best = max(ranked, key=lambda t: t[0])
    print(
        f"\ncell yenye pengo dogo kuliko zote: sl {best[1]:.2f} / tp {best[2]:.2f} — "
        f"EV net {best[0]:+.4f} R, model inahitaji p_tp +{best[6] - float(best[3]['p_tp']):.3f}"
    )
    print(
        "TAHADHARI: kuchagua cell kwa kuangalia jedwali hili ni UTEUZI juu ya label\n"
        "(§4.3 darasa la tatu). Grid inabaki INPUT ya model (anti-S1); jedwali hili ni\n"
        "kupima UMBALI, si kuchagua biashara."
    )
    return 0


def cmd_cost_audit(args: argparse.Namespace) -> int:
    """Gharama HALISI kwa R — ikiwemo kile stop zilizoruka zilichogharimu.

    Namba inayoamua kila kitu kingine cha T3: `cost_R` → `n_max` → `δ_MER` →
    `N_req`. R1 ilitoza −1.0 R sawasawa kila SL; hapa `touch_past_pips`
    inatumika kwa mara ya kwanza tangu ilipoanza kurekodiwa.
    """
    cfg = _load(args)
    import numpy as np

    import pandas as pd

    from .costs import (
        audit, config_budget, delta_mer, n_max_from_cost, n_required, realized_r,
    )
    from .r1 import load_labels

    labels_root = cfg.research_root / "data" / "L4_labels" / "labels"
    points, barriers = load_labels(labels_root, _symbol_list(args))
    if barriers.empty:
        print(f"hakuna labels chini ya {labels_root}", file=sys.stderr)
        return 2
    if "is_setup" in points.columns:
        keys = points.loc[points["is_setup"].fillna(False), ["symbol", "decision_time"]]
        barriers = barriers.merge(keys, on=["symbol", "decision_time"], how="inner")

    report = audit(barriers, commission_pips=args.commission_pips)
    if not report.cells:
        for note in report.notes:
            print(f"HITILAFU: {note}", file=sys.stderr)
        return 2

    frame = report.frame()
    print(f"GHARAMA HALISI KWA R — commission {args.commission_pips} pips/round-turn")
    print("spread haiingii: ishaingia kwenye path (§5.2). Setups pekee.\n")
    print(
        f"   {'sl':>5} {'tp':>5} {'SL%':>6} {'comm R':>8} {'over R':>8} {'over p99':>9} "
        f"{'cost R':>8} {'EV naive':>9} {'EV halisi':>10} {'EV net':>9}"
    )
    for _, r in frame.iterrows():
        print(
            f"   {r['sl_atr']:>5.2f} {r['tp_atr']:>5.2f} {r['p_stopped']:>5.1%} "
            f"{r['commission_r']:>8.4f} {r['overshoot_r_mean_given_stop']:>8.4f} "
            f"{r['overshoot_r_p99_given_stop']:>9.4f} {r['cost_r_total']:>8.4f} "
            f"{r['ev_r_naive']:>+9.4f} {r['ev_r_realized']:>+10.4f} {r['ev_r_net']:>+9.4f}"
        )

    # Identities za T3. Cell LAZIMA itajwe: kuichagua kwa `idxmax` ya EV ni
    # UTEUZI JUU YA LABEL (§4.3 darasa la tatu) — kosa lile lile ambalo
    # `r1-ev` inaonya dhidi yake, likirudiwa hapa (2026-08-13).
    if not args.cell:
        print(
            "\nIDENTITIES hazijahesabiwa: `--cell SL/TP` haijatajwa.\n"
            "  Kuchagua cell kwa kuangalia jedwali hili ni uteuzi juu ya label.\n"
            "  Tangaza cell, kisha isaini kama registered rule pamoja na ukiri huo:\n"
            "      python -m src.data.cli cost-audit --cell 2.0/3.0",
            file=sys.stderr,
        )
        rc_cell = 1
    else:
        rc_cell = 0
        want_sl, want_tp = (float(x) for x in args.cell.split("/"))
        match = frame[
            np.isclose(frame["sl_atr"], want_sl) & np.isclose(frame["tp_atr"], want_tp)
        ]
        if match.empty:
            print(f"cell {args.cell} haipo kwenye grid", file=sys.stderr)
            return 2
        row = match.iloc[0]
        cost_r = float(row["cost_r_total"])
        naive_cost = float(row["commission_r"])
        # `dEV/dp_tp = 1 + tp/sl` — SI 2.0 daima. Kwa cell 2.0/3.0 ni 2.5, na
        # kuitumia 2.0 kunavimbisha δ_MER kwa 25%.
        dev_dp = 1.0 + want_tp / want_sl
        n_max = n_max_from_cost(cost_r, args.sr_target, args.kappa)
        n_max_naive = n_max_from_cost(naive_cost, args.sr_target, args.kappa)
        delta = delta_mer(args.sr_target, n_max, dev_dp=dev_dp)
        need = n_required(delta)
        # Bar HALISI: umbali hadi breakeven, JUMLISHA edge inayolipa.
        ev_net = float(row["ev_r_net"])
        gap_to_breakeven = -ev_net / dev_dp
        total_lift = gap_to_breakeven + delta

        # CI kwenye `ev_r_net` — block bootstrap ya MIAKA.
        #
        # `ev_r_net` ndiyo namba inayoamua kama pool inalipa kabisa, na hadi
        # sasa ilikuwa ikiripotiwa kama nukta tupu. Nukta ya +0.0039 na nukta
        # ya +0.0039 yenye mpaka wa chini wa -0.02 ni hukumu mbili tofauti
        # kabisa, na tofauti hiyo ndiyo inayoamua kama kuna kitu cha kujenga.
        cell_rows = barriers[
            np.isclose(barriers["sl_atr"], want_sl) & np.isclose(barriers["tp_atr"], want_tp)
        ]
        r_rows = realized_r(cell_rows, commission_pips=args.commission_pips)
        yrs = pd.to_datetime(cell_rows["decision_time"]).dt.year.to_numpy()
        levels = np.unique(yrs)
        sums = np.array([np.nansum(r_rows[yrs == lv]) for lv in levels])
        counts = np.array([int((yrs == lv).sum()) for lv in levels], dtype=float)
        boot = np.random.RandomState(20260814)
        pick = boot.randint(0, len(levels), size=(5000, len(levels)))
        draws = sums[pick].sum(axis=1) / np.maximum(counts[pick].sum(axis=1), 1.0)
        ev_low, ev_high = (float(np.percentile(draws, 5)), float(np.percentile(draws, 95)))

        print(f"\nIDENTITIES (cell {want_sl:.2f}/{want_tp:.2f} · SR* {args.sr_target} · κ {args.kappa})")
        print(f"   dEV/dp_tp = 1 + tp/sl = {dev_dp:.2f}")
        print(f"   commission pekee    : cost_R {naive_cost:.4f}  →  n_max {n_max_naive:>7,.0f}/mwaka")
        print(f"   PAMOJA na overshoot : cost_R {cost_r:.4f}  →  n_max {n_max:>7,.0f}/mwaka")
        if naive_cost > 0:
            print(f"   overshoot inaongeza gharama kwa {cost_r / naive_cost - 1:.0%}"
                  f" na inashusha n_max kwa {1 - n_max / n_max_naive:.0%}")
        print(f"\n   EV net  {ev_net:>+8.4f} R   ·   90% CI [{ev_low:+.4f}, {ev_high:+.4f}]")
        print("   " + ("pool INALIPA (mpaka wa chini juu ya sifuri)" if ev_low > 0
                       else "pool HAIJATHIBITIKA kulipa — mpaka wa chini uko chini ya sifuri"))
        print(f"\n   hadi breakeven        {gap_to_breakeven:>8.4f} p_tp")
        print(f"   δ_MER (SR* {args.sr_target})        {delta:>8.4f} p_tp")
        print(f"   ---------------------------------------")
        print(f"   LIFT INAYOHITAJIKA    {total_lift:>8.4f} p_tp     (SETUP-v1 ililetea +0.0251)")
        print(f"\n   N_req {need:>8,.0f}  ·  config budget "
              f"{config_budget(args.sr_target, args.years):.1f}")
        print(f"\n   endelea: python -m src.data.cli effective-n --delta {delta:.4f}")

    # Faili la ushahidi linaitwa kwa IDADI YA SYMBOLS lililopimwa.
    #
    # Toleo la kwanza liliandika `cost_audit.json` daima. Kuendesha
    # `--symbols <subset>` kuliandika juu ya ushahidi wa pool nzima —
    # ushahidi ule ule uliotajwa na sahihi #19 ya DF-20. Populations mbili
    # tofauti, jina moja: hiyo ni provenance iliyovunjika, na inaonekana kama
    # sahihi iliyoharibika badala ya kipimo kipya (2026-08-14).
    chosen = _symbol_list(args)
    stem = "cost_audit"
    if chosen:
        digest = hashlib.sha256(",".join(sorted(chosen)).encode("utf-8")).hexdigest()[:8]
        stem = f"cost_audit_{len(chosen)}sym_{digest}"
        print(f"\n   POPULATION NDOGO: symbols {len(chosen)} — ushahidi unaandikwa `{stem}.json`,")
        print("   si juu ya `cost_audit.json` ya pool nzima.")
    out_path = cfg.path_of("storage.reports_root") / "r1" / f"{stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "commission_pips": args.commission_pips,
                # Population LAZIMA iandikwe ndani ya faili, si kwenye jina pekee:
                # jina linaweza kunakiliwa, yaliyomo hayawezi.
                "symbols": sorted(chosen) if chosen else "zote",
                "n_symbols": len(chosen) if chosen else None,
                "sr_target": args.sr_target,
                "kappa": args.kappa,
                "years": args.years,
                "cells": frame.to_dict(orient="records"),
                "identities": None if rc_cell else {
                    "cell": [want_sl, want_tp],
                    "dev_dp": dev_dp,
                    "cost_r_commission_only": naive_cost,
                    "cost_r_total": cost_r,
                    "n_max": n_max,
                    "n_max_commission_only": n_max_naive,
                    "ev_r_net": ev_net,
                    "ev_r_net_ci90": [ev_low, ev_high],
                    "ev_r_net_positive": bool(ev_low > 0),
                    "gap_to_breakeven": gap_to_breakeven,
                    "delta_mer": delta,
                    "total_lift_required": total_lift,
                    "n_required": need,
                    "config_budget": config_budget(args.sr_target, args.years),
                    "two_sided": True,
                },
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nushahidi: {out_path}")
    return rc_cell


def cmd_effective_n(args: argparse.Namespace) -> int:
    """Observations HURU ngapi tunazo — envelope ya makadirio manne."""
    cfg = _load(args)
    from .costs import n_required
    from .effective_n import estimate
    from .r1 import load_labels

    labels_root = cfg.research_root / "data" / "L4_labels" / "labels"
    points, _ = load_labels(labels_root, _symbol_list(args))
    if points.empty:
        print(f"hakuna points chini ya {labels_root}", file=sys.stderr)
        return 2
    if "is_setup" in points.columns and not args.include_control:
        points = points[points["is_setup"].fillna(False)]

    result = estimate(points, horizon_bars=int(cfg.get("labels.horizon_bars")))
    print("EFFECTIVE N — ndogo kuliko zote, si wastani\n")
    print(f"   n_raw    {result.n_raw:>10,}   points (setups pekee)" )
    print(f"   n_uniq   {result.n_uniq:>10,.0f}   concurrency ya labels zinazopishana")
    print(f"   n_time   {result.n_time:>10,.0f}   τ = {result.tau:.2f}")
    print(f"   n_cross  {result.n_cross:>10,.0f}   factors huru {result.participation_ratio:.2f}"
          f" kati ya symbols {result.symbols}")
    print(f"   n_block  {result.n_block:>10,.0f}   blocks × breadth")
    print(f"\n   N_eff    {result.n_eff:>10,.0f}")

    if args.delta:
        need = n_required(args.delta)
        verdict = "INATOSHA" if result.n_eff >= need else "HAITOSHI"
        print(f"\n   δ = {args.delta}  →  N_req {need:,.0f}  →  **{verdict}**"
              f"  ({result.n_eff / need:.2f}×)")
    for note in result.notes:
        print(f"\nkumbuka: {note}")

    out_path = cfg.path_of("storage.reports_root") / "r1" / "effective_n.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.to_json(), indent=2), encoding="utf-8", newline="\n")
    print(f"\nushahidi: {out_path}")
    return 0


def cmd_setup_effect(args: argparse.Namespace) -> int:
    """Je makali ya SETUP-v1 ni utabiri, au uteuzi wa volatility? (T3 hatua 2)

    Inagharimu bajeti: inatathmini dhidi ya labels na matokeo yake yataamua
    kama tunaendelea. Hilo ni uteuzi, hata kama ni uchambuzi.
    """
    cfg = _load(args)
    import numpy as np

    from src.governance import budget as bud

    from .costs import realized_r
    from .matching import DEFAULT_STRATA, build_strata, matched_effect
    from .r1 import load_labels

    bud.guard()
    want_sl, want_tp = (float(x) for x in args.cell.split("/"))

    labels_root = cfg.research_root / "data" / "L4_labels" / "labels"
    points, barriers = load_labels(labels_root, _symbol_list(args))
    if barriers.empty:
        print(f"hakuna labels chini ya {labels_root}", file=sys.stderr)
        return 2

    cells = barriers[
        np.isclose(barriers["sl_atr"], want_sl) & np.isclose(barriers["tp_atr"], want_tp)
    ].copy()
    if cells.empty:
        print(f"cell {args.cell} haipo kwenye grid", file=sys.stderr)
        return 2
    cells["r_net"] = realized_r(cells, commission_pips=args.commission_pips)

    frame = points.merge(
        cells[["symbol", "decision_time", "r_net"]], on=["symbol", "decision_time"], how="inner"
    )
    frame = build_strata(frame)
    result = matched_effect(
        frame, outcome="r_net", strata=DEFAULT_STRATA, cell=(want_sl, want_tp),
        n_boot=args.bootstrap,
    )

    print(f"SETUP DHIDI YA CONTROL, NDANI YA STRATA — cell {want_sl}/{want_tp}")
    print(f"strata: {' · '.join(DEFAULT_STRATA)}\n")
    print(f"   setups {result.n_setup:,}  ·  controls {result.n_control:,}")
    print(f"   strata {result.strata_total:,} · zenye zote mbili {result.strata_both:,}"
          f" · common support {result.support_frac:.1%}\n")
    print(f"   tofauti GHAFI       {result.raw_diff:+.4f} R")
    print(f"   tofauti NDANI YA STRATA {result.matched_diff:+.4f} R", end="")
    if np.isfinite(result.ci_low):
        print(f"   [90% CI {result.ci_low:+.4f}, {result.ci_high:+.4f}]")
    else:
        print()
    if np.isfinite(result.raw_diff) and result.raw_diff != 0:
        print(f"   imepungua kwa {1 - result.matched_diff / result.raw_diff:.0%}")

    verdict = "—"
    if np.isfinite(result.matched_diff):
        if np.isfinite(result.ci_low) and result.ci_low > 0:
            verdict = "HALISI — CI haiguzi sifuri"
        elif result.matched_diff <= 0.2 * result.raw_diff:
            verdict = "ARTEFACT — karibu yote ilikuwa uteuzi wa mazingira"
        else:
            verdict = "DHAIFU — imebaki lakini CI inaguza sifuri"
    print(f"\n   HUKUMU: {verdict}")
    for note in result.notes:
        print(f"\nkumbuka: {note}")

    out_path = cfg.path_of("storage.reports_root") / "r2" / "setup_effect.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.to_json(), indent=2, default=str), encoding="utf-8", newline="\n")
    print(f"\nushahidi: {out_path}")
    print(
        "\nbajeti: matumizi hayajaandikwa. Yaandike ukikubali matokeo:\n"
        f'  python -m src.governance.cli budget-spend setup-effect-{args.cell.replace("/", "-")}'
        ' --reason "..."'
    )
    return 0


def cmd_build_features(args: argparse.Namespace) -> int:
    """L3 — features 25 kwa kila symbol, kutoka bars za H1 za L2 (§6.1).

    TRAIN+VAL PEKEE (G2): bars kuanzia `holdout_start` **hazisomwi kabisa**.
    Sio kwamba features za holdout zingevuja zenyewe — rolling ni ya nyuma
    pekee — bali kwamba faili isiyokuwepo haiwezi kutumiwa kimakosa baadaye.

    `setup_v1_flag` inatoka kwenye points za L4, si kuhesabiwa upya (sheria 6).
    """
    cfg = _load(args)
    import pandas as pd

    from .bars import read_bars
    from .features import FEATURE_SET_VERSION, build, coverage
    from .r1 import load_labels
    from .splits import SplitPlan

    symbols = _symbol_list(args) or cfg.symbols
    holdout_start = SplitPlan.from_config(cfg).holdout_start
    labels_root = cfg.research_root / "data" / "L4_labels" / "labels"
    points, _ = load_labels(labels_root, symbols)
    out_root = cfg.research_root / "data" / "L3_features"

    summary: dict[str, Any] = {}
    for symbol in symbols:
        try:
            bars = read_bars(cfg.l2_root, symbol, "H1")
        except FileNotFoundError:
            print(f"{symbol}: bars za H1 hazipo — `build-l2` kwanza", file=sys.stderr)
            return 2
        bars = bars[bars.index < pd.Timestamp(holdout_start, tz="UTC")]  # G2

        setups = None
        if not points.empty and "is_setup" in points.columns:
            mine = points[points["symbol"] == symbol]
            if not mine.empty:
                setups = mine[["decision_time", "is_setup"]]

        frame = build(bars, symbol, setups=setups)
        target = out_root / f"symbol={symbol}" / "features.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".parquet.tmp")
        frame.reset_index().to_parquet(tmp, index=False, compression="zstd")
        tmp.replace(target)

        cov = coverage(frame)
        summary[symbol] = {
            "bars": int(len(frame)),
            "setup_flags": int(frame["setup_v1_flag"].sum()),
            "coverage_min": float(cov.iloc[0]),
            "coverage_min_feature": str(cov.index[0]),
        }
        print(
            f"{symbol} · bars {len(frame):>7,} · setups {int(frame['setup_v1_flag'].sum()):>5,}"
            f" · coverage ndogo {cov.iloc[0]:.1%} ({cov.index[0]})"
        )

    report_path = cfg.path_of("storage.reports_root") / "r3" / "features.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "feature_set_version": FEATURE_SET_VERSION,
                "config_hash": cfg.config_hash,
                "holdout_start": holdout_start.isoformat(),
                "per_symbol": summary,
            },
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nL3: {out_root}\nushahidi: {report_path}")
    return 0


def _t3_dataset(cfg, args) -> dict | None:
    """Data ya T3 — points za setup × cell iliyosainiwa × features za L3.

    Imetolewa nje ya `meta-label` ili `placebo` itumie **njia ile ile kabisa**.
    Placebo inayopakia data kwa njia yake mwenyewe haipimi pipeline; inapima
    pipeline nyingine inayofanana nayo, na hilo ndilo hasa kosa ambalo hatua
    ya 4 ipo kulikamata.

    Inarudisha `None` ikiwa kitu hakipo (ujumbe umeshaandikwa kwenye stderr).
    """
    import numpy as np
    import pandas as pd

    from .costs import realized_r
    from .experiment import add_uniqueness
    from .labels import TP_FIRST
    from .r1 import load_labels
    from .splits import SplitPlan

    reports = cfg.path_of("storage.reports_root")
    cost_path = reports / "r1" / "cost_audit.json"
    if not cost_path.exists():
        print(f"`{cost_path}` haipo — endesha `cost-audit --cell SL/TP` kwanza", file=sys.stderr)
        return None
    identities = json.loads(cost_path.read_text(encoding="utf-8")).get("identities")
    if not identities:
        print("`cost_audit.json` haina identities — endesha `cost-audit --cell SL/TP`",
              file=sys.stderr)
        return None

    want_sl, want_tp = (float(x) for x in args.cell.split("/"))
    if not np.allclose(identities["cell"], [want_sl, want_tp]):
        print(
            f"cell {args.cell} haifanani na iliyo kwenye cost_audit.json "
            f"({identities['cell']}). Kubadilisha cell sasa ni UTEUZI JUU YA LABEL.",
            file=sys.stderr,
        )
        return None

    labels_root = cfg.research_root / "data" / "L4_labels" / "labels"
    points, barriers = load_labels(labels_root, _symbol_list(args))
    if barriers.empty or points.empty:
        print(f"hakuna labels chini ya {labels_root}", file=sys.stderr)
        return None
    points = points[points["is_setup"].fillna(False)]
    cells = barriers[
        np.isclose(barriers["sl_atr"], want_sl) & np.isclose(barriers["tp_atr"], want_tp)
    ].copy()
    cells["y"] = (cells["outcome"] == TP_FIRST).astype(float)
    cells["r_net"] = realized_r(cells, commission_pips=args.commission_pips)

    frame = points.merge(
        cells[["symbol", "decision_time", "y", "r_net"]],
        on=["symbol", "decision_time"], how="inner",
    )
    # Breakeven kwa idadi ILE ILE iliyotumika kwenye cost-audit (setups zote za
    # cell hii), si kwa subset iliyobaki baada ya features — la sivyo lango
    # lingehama pamoja na data linayoipima.
    p_tp_base = float(frame["y"].mean())

    features_root = cfg.research_root / "data" / "L3_features"
    pieces = []
    for symbol, chunk in frame.groupby("symbol", sort=False):
        path = features_root / f"symbol={symbol}" / "features.parquet"
        if not path.exists():
            print(f"{symbol}: features hazipo — `build-features` kwanza", file=sys.stderr)
            return None
        feats = pd.read_parquet(path).drop(columns=["timestamp"], errors="ignore")
        pieces.append(chunk.merge(feats, on="decision_time", how="inner", suffixes=("", "_feat")))
    joined = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    if joined.empty:
        print("join ya features na points imetoa sifuri", file=sys.stderr)
        return None

    # G2 mara ya pili — features zinaweza kuwa zilijengwa kwa config nyingine.
    plan = SplitPlan.from_config(cfg)
    intruders = int((joined["decision_time"].dt.date >= plan.holdout_start).sum())
    if intruders:
        print(f"G2: FAIL — rows {intruders:,} ziko ndani ya holdout", file=sys.stderr)
        return None

    horizon = int(cfg.get("labels.horizon_bars"))
    return {
        "joined": add_uniqueness(joined, horizon),
        "folds": list(plan.folds()),
        "horizon": horizon,
        "identities": identities,
        "cell": (want_sl, want_tp),
        "p_tp_base": p_tp_base,
        "breakeven": p_tp_base + float(identities["gap_to_breakeven"]),
        "delta_mer": float(identities["delta_mer"]),
        "n_points": int(len(frame)),
        "reports": reports,
    }


def cmd_meta_label(args: argparse.Namespace) -> int:
    """T3 hatua 3 — je model inaweza kuchuja SETUP-v1 vizuri kuliko SETUP-v1?

    Hii ndiyo amri inayogharimu bajeti. Kila kitu kimekwisha tangazwa kabla
    yake: cell (sahihi), features (`FEATURE_NAMES`), folds (DF-14),
    hyperparameters (`experiment.py`), na malango matatu (`metalabel.py`).
    Kilichobaki ni kuendesha na kusoma jibu.

    **Breakeven inatoka `cost_audit.json`, si hapa.** `gap_to_breakeven` ni
    umbali wa `p_tp` hadi EV = 0 ukitumia `dEV/dp_tp = 1 + tp/sl`. Hiyo ni
    linearization kuzunguka base rate: inadhania mzunguko wa uzito ni
    **TP ↔ SL** huku timeout ikibaki ile ile. Kwa subset iliyochaguliwa na
    model, timeout rate inaweza kutofautiana — kwa hiyo `R` HALISI ya kila
    decile inaripotiwa kando kama ushahidi, si kama lango (lango
    lililotangazwa halibadilishwi baada ya kuona data).
    """
    cfg = _load(args)
    import numpy as np

    from src.governance import budget as bud

    from .effective_n import estimate
    from .experiment import EXPERIMENT_VERSION, available_models, oof_predict
    from .features import FEATURE_NAMES, FEATURE_SET_VERSION
    from .manifest import code_rev
    from .metalabel import METALABEL_VERSION, evaluate

    bud.guard()
    models = available_models()
    if args.model not in models:
        print(
            f"model `{args.model}` haipatikani. Zilizopo: {', '.join(sorted(models))}."
            + ("\n  `xgboost` haijafungwa kwenye mazingira haya." if "xgboost" not in models else ""),
            file=sys.stderr,
        )
        return 2

    data = _t3_dataset(cfg, args)
    if data is None:
        return 2
    joined, folds, horizon = data["joined"], data["folds"], data["horizon"]
    identities, (want_sl, want_tp) = data["identities"], data["cell"]
    p_tp_base, breakeven, delta = data["p_tp_base"], data["breakeven"], data["delta_mer"]
    reports = data["reports"]

    result_oof = oof_predict(
        joined, FEATURE_NAMES, "y", folds,
        models[args.model], weight_col=None if args.unweighted else "uniqueness",
    )
    scored = joined[result_oof.mask].copy()
    scored["score"] = result_oof.score[result_oof.mask]
    if len(scored) < 500:
        print(f"rows zilizopata score ni {len(scored):,} pekee — jaribio haliwezi kuendelea",
              file=sys.stderr)
        return 2

    # N_eff INAHESABIWA UPYA kwa rows zilizopata score. Ile ya `effective_n.json`
    # ni ya setups 25,314; baada ya NaN za features na coverage ya folds sampuli
    # ni ndogo, na kutumia namba kubwa kungefanya kifungu cha nguvu kisifanye kazi.
    neff = estimate(scored, horizon_bars=horizon)
    n_required = float(identities["n_required"])

    result = evaluate(
        scored["score"].to_numpy(),
        scored["y"].to_numpy(),
        scored["decision_time"].dt.year.to_numpy(),
        breakeven=breakeven,
        delta_mer=delta,
        n_eff=neff.n_eff,
        n_required=n_required,
        n_boot=args.bootstrap,
    )

    # --------------------------------------------------------------- ripoti
    print(f"META-LABELLING — cell {want_sl}/{want_tp} · model `{args.model}`"
          f" · features {len(FEATURE_NAMES)}\n")
    print(f"   points za setup   {data['n_points']:>8,}")
    print(f"   baada ya features {len(joined):>8,}   (NaN zilizotolewa: {result_oof.dropped_nan:,})")
    print(f"   zenye score OOF   {len(scored):>8,}   folds {len(result_oof.folds)}/{len(folds)}")
    print(f"   N_eff             {neff.n_eff:>8,.0f}   dhidi ya N_req {n_required:,.0f}")
    print(f"\n   p_tp ya msingi {p_tp_base:.4f}  ·  breakeven {breakeven:.4f}"
          f"  ·  lengo {breakeven + delta:.4f}")

    if result.deciles:
        # Mgawanyo ULE ULE wa `decile_table` — argsort + array_split, si quantiles.
        # Quantiles zingetoa `n` tofauti kwenye scores zenye ties, na jedwali
        # lingeonyesha safu mbili zisizolingana zikiitwa "decile ile ile".
        groups = np.array_split(np.argsort(scored["score"].to_numpy()), 10)
        r_all = scored["r_net"].to_numpy(dtype=float)
        print(f"\n   {'dec':>4} {'n':>7} {'empirical':>10} {'fitted':>8} {'R halisi':>10}")
        for row in result.deciles:
            g = groups[int(row["decile"]) - 1]
            r_mean = float(np.nanmean(r_all[g])) if len(g) else float("nan")
            print(f"   {row['decile']:>4} {row['n']:>7,} {row['empirical']:>10.4f} "
                  f"{row.get('fitted', float('nan')):>8.4f} {r_mean:>+10.4f}")
            row["r_net_mean"] = r_mean

    print()
    for gate in result.gates:
        mark = "PASS" if gate.passed else "FAIL"
        print(f"   {gate.name:<15} {gate.value:>8.4f}  dhidi ya {gate.threshold:>8.4f}  {mark}")
        if gate.detail:
            print(f"       {gate.detail}")
    if result.inconclusive:
        print("\n   HUKUMU: INCONCLUSIVE — sampuli haitoshi, matokeo hayasomwi")
    else:
        print(f"\n   HUKUMU: {'IMEPITA' if result.passed else 'IMEFELI'}")
    for note in result.notes + result_oof.notes:
        print(f"\nkumbuka: {note}")

    payload = result.to_json()
    payload.update(
        {
            "experiment_version": EXPERIMENT_VERSION,
            "metalabel_version": METALABEL_VERSION,
            "feature_set_version": FEATURE_SET_VERSION,
            "config_hash": cfg.config_hash,
            "section_hashes": {k: cfg.section_hash(k) for k in ("setups", "labels", "splits")},
            "code_rev": code_rev(),
            "cell": [want_sl, want_tp],
            "model": args.model,
            "weighted": not args.unweighted,
            "commission_pips": args.commission_pips,
            "features": list(FEATURE_NAMES),
            "n_points": data["n_points"],
            "n_joined": int(len(joined)),
            "n_scored": int(len(scored)),
            "dropped_nan": int(result_oof.dropped_nan),
            "p_tp_base": p_tp_base,
            "effective_n_scored": neff.to_json(),
            "folds": [f.__dict__ for f in result_oof.folds],
            "oof_notes": result_oof.notes,
        }
    )
    out_path = reports / "r3" / f"meta_label_{args.model}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8", newline="\n")
    print(f"\nushahidi: {out_path}")
    print(
        "\nbajeti: matumizi hayajaandikwa. Yaandike ukikubali matokeo:\n"
        f"  python -m src.governance.cli budget-spend meta-label-{args.model}"
        ' --reason "..."'
    )
    return 0


def cmd_placebo(args: argparse.Namespace) -> int:
    """T3 hatua 4 — pipeline inatoa nini pale HAKUNA signal kabisa?

    Kigezo cha 0.7 kwenye Spearman kilichaguliwa kwa hoja, si kwa kupimwa.
    Hatua hii inabadilisha hoja kuwa **mgawanyo**: endesha pipeline ILE ILE
    mara nyingi kwenye labels zilizoharibiwa, kisha angalia matokeo halisi
    yanakaa wapi ndani ya mgawanyo huo. Pipeline ikitoa matokeo chanya pale
    hakuna signal, **kila kitu kilicho juu yake ni batili**.

    **Haigharimu bajeti**, na sababu ni ya kanuni, si ya urahisi: labels
    zilizoharibiwa haziwezi kutumika kuchagua strategy. Hakuna uteuzi, hakuna
    multiple-testing surface. Ndiyo maana `budget.guard()` haipo hapa.

    **Njia ya kuharibu ni mzunguko (`rotation`), si kuchanganya (`shuffle`).**
    Kuchanganya rows kunavunja autocorrelation ya labels pia, na null
    inayotokana nayo ni **nyembamba kupita kiasi** — kila kitu kinaonekana
    muhimu ukilinganisha nayo. Mzunguko wa duara ndani ya kila symbol
    unahifadhi muundo wote wa mfululizo na unavunja **upatanifu na features
    pekee**, ambao ndio hasa unaodaiwa.
    """
    cfg = _load(args)
    import numpy as np

    from .experiment import available_models, oof_predict
    from .features import FEATURE_NAMES
    from .metalabel import decile_table, logistic_calibrate, apply_calibration, spearman

    models = available_models()
    if args.model not in models:
        print(f"model `{args.model}` haipatikani. Zilizopo: {', '.join(sorted(models))}",
              file=sys.stderr)
        return 2
    data = _t3_dataset(cfg, args)
    if data is None:
        return 2
    joined, folds = data["joined"], data["folds"]
    weight_col = None if args.unweighted else "uniqueness"

    def _run(frame, target: str) -> dict | None:
        """Pipeline nzima → takwimu tatu. NI NJIA ILE ILE ya `meta-label`."""
        out = oof_predict(frame, FEATURE_NAMES, target, folds, models[args.model], weight_col)
        if out.mask.sum() < 500:
            return None
        score = out.score[out.mask]
        y = frame[target].to_numpy(dtype=float)[out.mask]
        r_net = frame["r_net"].to_numpy(dtype=float)[out.mask]
        a, b = logistic_calibrate(score, y)
        top = score >= float(np.quantile(score, 0.9))
        stats = {
            "top_fitted": float(apply_calibration(score[top], a, b).mean()),
        }

        if args.within_symbol:
            # Ondoa base rate ya KILA symbol kabla ya kupima chochote.
            #
            # Bila hii, model inayojua tu "hii ni XAUUSD, ile ni EURCHF"
            # inapata deciles zinazopanda vizuri kabisa — kwa sababu symbols
            # zina `p_tp` tofauti. Hicho si kupanga kwa WAKATI; ni upendeleo
            # tuli ambao base rate tayari inaubeba. Hapa kinaondolewa.
            sym = frame["symbol"].to_numpy()[out.mask]
            for column in (y, r_net):
                for one in np.unique(sym):
                    pick = sym == one
                    column[pick] -= column[pick].mean()

        table = decile_table(score, y, calibration=(a, b))
        stats["rho"] = float(spearman(table["decile"], table["empirical"]))
        stats["top_r_net"] = float(np.nanmean(r_net[top]))
        return stats

    # Jedwali la kila symbol — msingi wa uchunguzi wote wa uchafuzi.
    #
    # `rotation` na `block` zinazungusha NDANI ya symbol, kwa hiyo zinahifadhi
    # `p_tp` ya kila symbol **kamili**. `shuffle` pekee ndiyo inayoivunja. Kwa
    # hiyo tofauti kubwa kati ya symbols inatosha kuchafua null mbili kati ya
    # tatu, bila uvujaji wowote wa muda kuhusika.
    per_symbol = joined.groupby("symbol").agg(
        n=("y", "size"), p_tp=("y", "mean"), r_net=("r_net", "mean")
    ).sort_values("p_tp")
    span_p = float(per_symbol["p_tp"].max() - per_symbol["p_tp"].min())
    span_r = float(per_symbol["r_net"].max() - per_symbol["r_net"].min())

    # CI kwa block bootstrap ya MIAKA — si rows. Bila hii, jedwali la symbols
    # 12 ni mwaliko wa kuchagua bora zaidi kwa jicho, na kwa symbols 12 tofauti
    # ya kubahatisha peke yake inaweza kufika ~3.4 SE. Kikomo cha chini ndicho
    # kinachotofautisha "symbol hii inalipa" na "symbol hii ilibahatika".
    boot = np.random.RandomState(args.seed)
    years_all = joined["decision_time"].dt.year.to_numpy()
    k = int(len(per_symbol))
    # Šidák: kuangalia symbols `k` kisha kuchagua bora zaidi si jaribio moja.
    # Kwa 5% ya FAMILIA nzima, kila symbol inahitaji mpaka wa `1 - 0.95^(1/k)`.
    # Kwa k = 12 hiyo ni asilimia 0.427, si 5 — tofauti ya mara kumi.
    q_fwer = 100.0 * (1.0 - 0.95 ** (1.0 / max(k, 1)))
    n_boot = 5000

    lows: dict[str, tuple[float, float]] = {}
    for name in per_symbol.index:
        pick = (joined["symbol"] == name).to_numpy()
        vals, yrs = joined["r_net"].to_numpy(dtype=float)[pick], years_all[pick]
        levels = np.unique(yrs)
        # Jumla na idadi kwa kila mwaka — bootstrap inakuwa hesabu ya vector,
        # si kuunganisha index mara 5,000 × 12.
        sums = np.array([np.nansum(vals[yrs == lv]) for lv in levels])
        counts = np.array([int((yrs == lv).sum()) for lv in levels], dtype=float)
        draw_idx = boot.randint(0, len(levels), size=(n_boot, len(levels)))
        draws = sums[draw_idx].sum(axis=1) / np.maximum(counts[draw_idx].sum(axis=1), 1.0)
        lows[name] = (float(np.percentile(draws, 5)), float(np.percentile(draws, q_fwer)))
    per_symbol["r_net_p5"] = [lows[n][0] for n in per_symbol.index]
    per_symbol["r_net_fwer"] = [lows[n][1] for n in per_symbol.index]

    print(f"   {'symbol':<8} {'n':>7} {'p_tp':>8} {'R halisi':>10} {'p5':>9} {'FWER':>9}")
    for name, row in per_symbol.iterrows():
        # Bendera inategemea mpaka ULIOREKEBISHWA pekee. Toleo la kwanza
        # liliweka bendera kwenye p5 ghafi, na kwa symbols 12 hiyo ni mwaliko
        # wa kosa lile lile ambalo jedwali hili lilipaswa kulizuia: bora kati
        # ya 12 karibu daima ina p5 chanya kwa bahati (2026-08-14).
        alama = "  <-- inashikilia" if row["r_net_fwer"] > 0 else ""
        print(f"   {name:<8} {int(row['n']):>7,} {row['p_tp']:>8.4f} "
              f"{row['r_net']:>+10.4f} {row['r_net_p5']:>+9.4f} "
              f"{row['r_net_fwer']:>+9.4f}{alama}")
    print(f"   utofauti kati ya symbols: p_tp {span_p:.4f} · R {span_r:.4f}")
    print(f"   bar ya T3 kwa lift ya jumla: +0.0751 R")
    print(f"   FWER = mpaka wa Šidák kwa symbols {k} (asilimia {q_fwer:.3f}, si 5)")

    # Je mpangilio wa symbols unaelezwa na TRENDINESS, si na bahati?
    #
    # Hii ndiyo tofauti kati ya nadharia na uchimbaji: `eff_ratio` na `adx`
    # zinahesabiwa kutoka BEI PEKEE, hazijui label yoyote. Zikipanga symbols
    # kwa mpangilio ule ule ambao `R` inazipanga, kuna utaratibu wa kiuchumi
    # nyuma ya jedwali. Zisipopanga, jedwali ni orodha ya matokeo tu.
    mechanism = {}
    for column in ("eff_ratio_24h", "adx14"):
        if column in joined.columns:
            by_symbol = joined.groupby("symbol")[column].mean().reindex(per_symbol.index)
            mechanism[column] = float(spearman(by_symbol.to_numpy(), per_symbol["r_net"].to_numpy()))
    if mechanism:
        # Symbols 12 SI observations 12. Sarafu 6 zinazounda jozi 12 zinatoa
        # blocs chache zaidi: EUR-crosses zinasogea pamoja, JPY-crosses pamoja,
        # dollar za commodity pamoja. `ρ` ya jozi 12 ikihukumiwa kama n = 12
        # inarudia kosa lile lile la `effective-n` (mapitio ya nje: *"you cannot
        # infer effective N from raw instrument count"*), likiwa kwenye mhimili
        # wa cross-section badala ya wa muda.
        from .effective_n import participation_ratio

        panel = joined.pivot_table(
            index=joined["decision_time"].dt.floor("1D"),
            columns="symbol", values="r_net", aggfunc="mean",
        ).sort_index()
        blocs = participation_ratio(panel)
        # Fisher: `ρ` inayohitajika kwa 5% ya upande mmoja kwa n huru.
        rho_crit = 1.645 / np.sqrt(max(blocs - 1.0, 1.0))
        detail = " · ".join(f"{name} ρ {value:+.3f}" for name, value in mechanism.items())
        print(f"   mpangilio dhidi ya trendiness (bila label): {detail}")
        print(f"   blocs huru {blocs:.2f} (si {k}) → ρ inayohitajika {rho_crit:.3f} "
              f"kwa 5% ya upande mmoja")
        best = max(mechanism.values())
        print("   " + ("utaratibu UMETHIBITIKA" if best >= rho_crit
                       else f"HAIJATHIBITIKA — kubwa ni {best:+.3f}, pungufu ya {rho_crit:.3f}"))
        mechanism["_blocs"] = blocs
        mechanism["_rho_required"] = float(rho_crit)
    print()

    halisi = _run(joined, "y")
    if halisi is None:
        print("rows zilizopata score hazitoshi", file=sys.stderr)
        return 2
    njia = f"{args.mode} ({args.block})" if args.mode == "block" else args.mode
    upeo = " · NDANI YA SYMBOL" if args.within_symbol else ""
    print(f"PLACEBO — model `{args.model}` · njia `{njia}` · marudio {args.reps}{upeo}")
    print("labels zimeharibiwa; features, folds na uzito ni vile vile.\n")
    print(f"   HALISI:  rho {halisi['rho']:+.4f} · top fitted {halisi['top_fitted']:.4f} "
          f"· top R {halisi['top_r_net']:+.4f}\n")

    rng = np.random.RandomState(args.seed)
    symbols = joined["symbol"].to_numpy()
    order_key = joined["decision_time"].to_numpy()
    # Msingi wa kulinganisha na null. Kwa `--within-symbol`, `r_net` inaondolewa
    # wastani wa kila symbol ndani ya `_run`, kwa hiyo msingi wake ni **sifuri**,
    # si wastani ghafi wa sampuli. Kulinganisha decile ya juu iliyoondolewa
    # wastani na msingi ghafi wa -0.0163 ni kulinganisha vitu viwili tofauti, na
    # kunatoa onyo la uchafuzi lisilo la kweli (2026-08-14).
    base_r = 0.0 if args.within_symbol else float(np.nanmean(joined["r_net"].to_numpy(dtype=float)))
    null: list[dict] = []
    for rep in range(args.reps):
        fake = joined.copy()
        values = fake["y"].to_numpy(dtype=float).copy()
        if args.mode == "rotation":
            # Mzunguko wa duara NDANI ya kila symbol, KWA MPANGILIO WA MUDA.
            # Bila `argsort` hapa, `np.roll` inazungusha mpangilio wa rows
            # kwenye parquet — permutation halali, lakini SI mzunguko wa muda,
            # na dai la "muundo wa mfululizo unabaki" lingekuwa la uongo.
            for symbol in np.unique(symbols):
                idx = np.flatnonzero(symbols == symbol)
                idx = idx[np.argsort(order_key[idx], kind="stable")]
                shift = int(rng.randint(1, max(len(idx) - 1, 2)))
                values[idx] = np.roll(values[idx], shift)
        elif args.mode == "block":
            # Vipande vya mfululizo vinabadilishwa NAFASI, si rows.
            #
            # Hii ndiyo null sahihi kati ya zile mbili nyingine, na sababu
            # imepimwa si kudhaniwa:
            #   * `rotation` inahifadhi kumbukumbu ndefu (regimes za miezi),
            #     kwa hiyo signal inabaki NDANI ya null. Ilipimwa: decile ya
            #     juu ya null ilitoa +0.0275 R dhidi ya msingi -0.0163.
            #   * `shuffle` inavunja hata autocorrelation ya karibu (τ 2.49),
            #     kwa hiyo null ni nyembamba kuliko ukweli.
            # Kipande cha ~mwezi mmoja na nusu kinahifadhi τ ndani yake na
            # kinavunja upatanifu wa regimes kati ya features na labels.
            for symbol in np.unique(symbols):
                idx = np.flatnonzero(symbols == symbol)
                idx = idx[np.argsort(order_key[idx], kind="stable")]
                chunks = [idx[i:i + args.block] for i in range(0, len(idx), args.block)]
                if len(chunks) < 3:
                    continue
                taken = values[np.concatenate([chunks[j] for j in rng.permutation(len(chunks))])]
                values[idx] = taken
        elif args.mode == "shuffle":
            rng.shuffle(values)
        else:  # bernoulli
            values = (rng.uniform(size=len(values)) < values.mean()).astype(float)
        fake["y_fake"] = values

        got = _run(fake, "y_fake")
        if got is None:
            continue
        null.append(got)
        print(f"   {rep + 1:>3}/{args.reps}  rho {got['rho']:+.4f} · "
              f"top fitted {got['top_fitted']:.4f} · top R {got['top_r_net']:+.4f}")

    if len(null) < 5:
        print(f"marudio yaliyofanikiwa ni {len(null)} pekee — hayatoshi", file=sys.stderr)
        return 2

    print(f"\n   {'takwimu':<14} {'halisi':>9} {'null p50':>9} {'null p95':>9} "
          f"{'null max':>9} {'p-value':>9}")
    verdict_ok = True
    for key, label in (("rho", "discrimination"), ("top_fitted", "top fitted"),
                       ("top_r_net", "top R halisi")):
        draws = np.array([n[key] for n in null], dtype=float)
        # p ya upande mmoja, ikihesabu halisi yenyewe: (#{null ≥ halisi} + 1)/(N + 1).
        # Kuacha "+1" kunatoa p = 0 isiyowezekana kwa marudio machache.
        pval = float((np.sum(draws >= halisi[key]) + 1) / (len(draws) + 1))
        print(f"   {label:<14} {halisi[key]:>+9.4f} {np.median(draws):>+9.4f} "
              f"{np.percentile(draws, 95):>+9.4f} {draws.max():>+9.4f} {pval:>9.3f}")
        if key == "rho" and pval > 0.05:
            verdict_ok = False

    # Lango la placebo: si "matokeo halisi ni mazuri", bali "pipeline haitoi
    # matokeo kama haya bila signal". Ndiyo maana rho ndiyo inayohukumu —
    # ndiyo takwimu pekee kati ya tatu inayopima UWEZO WA KUPANGA peke yake.
    print(f"\n   HUKUMU: {'PIPELINE NI SAFI' if verdict_ok else 'PIPELINE INATILIWA SHAKA'}")
    if not verdict_ok:
        print("   discrimination ya kelele inafikia ile halisi — matokeo ya hatua 3 ni batili")

    # ------------------------------------------------------------------
    # UKAGUZI WA NULL YENYEWE — je null ni null kweli?
    #
    # Model iliyofundishwa kwa labels ZILIZOHARIBIWA haipaswi kuwa na uwezo
    # wowote wa kuchagua trades bora. Kwa hiyo `R` HALISI ya decile yake ya
    # juu inapaswa kukaa kwenye msingi wa sampuli nzima. Ikikaa juu yake kwa
    # utaratibu, null imehifadhi taarifa iliyodaiwa kuiharibu — na p-value
    # zote hapo juu ni KUBWA KULIKO ZINAVYOSTAHILI (conservative), si ndogo.
    #
    # Kipimo hiki kinaangalia CHOMBO cha kupimia, si strategy. Kimeongezwa
    # 2026-08-14 baada ya kuona `rotation` ikitoa null median +0.0275 dhidi ya
    # msingi -0.0163. Hakigusi lango lolote la hatua 3 wala halibadilishi
    # hukumu yoyote — ndiyo maana kuongezwa kwake baada ya kuona matokeo ni
    # halali, tofauti na kuhamisha lango.
    null_top_r = float(np.median([n["top_r_net"] for n in null]))
    print(f"\n   UKAGUZI WA NULL: msingi wa sampuli {base_r:+.4f} R · "
          f"null median ya decile ya juu {null_top_r:+.4f} R")
    if null_top_r > base_r + 0.01:
        print(
            "   NULL IMECHAFULIWA. Model iliyofundishwa kwa labels zilizoharibiwa\n"
            "   bado inachagua trades bora kuliko msingi — kwa hiyo `--mode "
            f"{args.mode}`\n   haikuvunja uhusiano, imeuhifadhi. p-value hapo juu ni "
            "CONSERVATIVE.\n"
            "   Linganisha na `--mode shuffle`, ambayo inavunja kila kitu\n"
            "   (ikiwemo autocorrelation, kwa hiyo null yake ni NYEMBAMBA MNO).\n"
            "   Ukweli uko kati ya hizo mbili."
        )
    else:
        print("   null iko kwenye msingi — haijahifadhi taarifa.")

    tag = f"{args.mode}{args.block}" if args.mode == "block" else args.mode
    if args.within_symbol:
        tag += "_ndani"
    out_path = data["reports"] / "r3" / f"placebo_{args.model}_{tag}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "model": args.model,
                "mode": args.mode,
                "block": args.block if args.mode == "block" else None,
                "reps": args.reps,
                "reps_ok": len(null),
                "seed": args.seed,
                "weighted": not args.unweighted,
                "within_symbol": bool(args.within_symbol),
                "per_symbol": per_symbol.reset_index().to_dict(orient="records"),
                "span_p_tp": span_p,
                "span_r_net": span_r,
                "fwer_percentile": q_fwer,
                "mechanism_spearman": mechanism,
                "cell": list(data["cell"]),
                "observed": halisi,
                "base_r_net": base_r,
                "null_top_r_median": null_top_r,
                "null_contaminated": bool(null_top_r > base_r + 0.01),
                "null": null,
                "p_values": {
                    key: float((sum(n[key] >= halisi[key] for n in null) + 1) / (len(null) + 1))
                    for key in ("rho", "top_fitted", "top_r_net")
                },
                "clean": verdict_ok,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nushahidi: {out_path}")
    return 0 if verdict_ok else 1


def cmd_cross_power(args: argparse.Namespace) -> int:
    """T4 — blocs ngapi zinahitajika kupima sheria ya cross-section?

    Hatua 4 iliishia hapa: `ρ` ya trendiness ilikuwa +0.545, ikihitaji 0.643,
    na tofauti hiyo si ya `ρ` bali ya **blocs**. Symbols 12 zilitoa 7.54 huru
    pekee, kwa hiyo hakuna `ρ` iliyoweza kuhitimisha.

    Utambulisho ni wa Fisher: `ρ_crit = z_α ÷ √(blocs − 1)`, ukigeuzwa
    `blocs = 1 + (z_α ÷ ρ)²`.

    **Symbols si blocs.** Jozi zinazoshiriki sarafu zinasogea pamoja; kuongeza
    EURNOK kwenye pool yenye EUR nyingi kunaongeza row, si taarifa. Ndiyo maana
    amri hii inaripoti mipaka miwili badala ya namba moja: ya chini inadhania
    urudufu ule ule wa sasa, ya juu inadhania kila symbol mpya inaleta bloc
    yake. Ukweli uko kati, na uko karibu na upi **inategemea sarafu, si idadi**.
    """
    import numpy as np
    from statistics import NormalDist

    alpha = args.alpha / args.tests if args.tests > 1 else args.alpha
    z = NormalDist().inv_cdf(1.0 - alpha)
    need = 1.0 + (z / args.rho) ** 2

    print(f"NGUVU YA CROSS-SECTION — ρ {args.rho:.3f} · α {args.alpha} "
          f"· vipimo {args.tests}\n")
    if args.tests > 1:
        print(f"   Šidák: α kwa kila kipimo = {alpha:.4f}  (z = {z:.3f})")
    print(f"   blocs zinazohitajika : {need:>6.1f}")
    print(f"   blocs zilizopo       : {args.blocs:>6.2f}   (symbols {args.symbols})")
    detectable = z / np.sqrt(max(args.blocs - 1.0, 1e-9))
    print(f"   ρ inayoweza kupimika kwa blocs zilizopo: {detectable:.3f}")

    if args.blocs >= need:
        print("\n   INATOSHA — hakuna haja ya symbols zaidi kwa swali hili.")
        rc = 0
    else:
        ratio = args.blocs / max(args.symbols, 1)
        # Mpaka wa chini: symbols mpya zina urudufu ULE ULE wa zilizopo.
        # Mpaka wa juu: kila symbol mpya inaleta bloc kamili.
        pessimistic = int(np.ceil(need / max(ratio, 1e-9)))
        optimistic = int(np.ceil(args.symbols + (need - args.blocs)))
        print(f"\n   HAITOSHI — pungufu ya blocs {need - args.blocs:.1f}")
        print(f"   symbols zinazohitajika: kati ya {optimistic} na {pessimistic}")
        print(f"      {optimistic:>3} ikiwa kila symbol mpya inaleta bloc yake "
              "(sarafu MPYA, si jozi mpya za zile zile)")
        print(f"      {pessimistic:>3} ikiwa urudufu unabaki {ratio:.2f} bloc kwa symbol "
              "(jozi zaidi za sarafu zile zile)")
        print("\n   Tofauti kati ya namba hizo mbili ndiyo thamani ya kuchagua "
              "sarafu\n   mpya badala ya jozi mpya. Si suala la idadi.")
        rc = 1

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {
                    "rho": args.rho,
                    "alpha": args.alpha,
                    "tests": args.tests,
                    "alpha_per_test": alpha,
                    "blocs_required": need,
                    "blocs_available": args.blocs,
                    "symbols_available": args.symbols,
                    "rho_detectable_now": float(detectable),
                    "sufficient": bool(args.blocs >= need),
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"\nushahidi: {args.out}")
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
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"mpango: {args.out}")
    return 0


def cmd_config_hash(args: argparse.Namespace) -> int:
    cfg = _load(args)
    payload: dict[str, Any] = {"config": str(cfg.path), "config_hash": cfg.config_hash}
    if args.sections:
        payload["sections"] = cfg.section_hashes()
    if args.since:
        # Sahihi inaelekeza `code_rev`. Swali si "config imebadilika?" bali
        # "je SEHEMU inayohusika na sahihi hii imebadilika?" — hilo ndilo
        # linaloweza kujibiwa, na ni tofauti kabisa (2026-08-13, sahihi #11).
        payload["since"] = args.since
        payload["changed"] = _sections_changed(cfg, args.since)
    print(json.dumps(payload, indent=2))
    return 0


def _sections_changed(cfg, revision: str) -> dict[str, str]:
    """Sehemu zilizobadilika kati ya commit `revision` na config ya sasa."""
    import subprocess

    import yaml

    try:
        blob = subprocess.run(
            ["git", "show", f"{revision}:config/data.yaml"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return {"—": f"commit `{revision}` haipatikani ({exc})"}

    old = yaml.safe_load(blob) or {}
    out: dict[str, str] = {}
    for name in sorted(set(old) | set(cfg.raw)):
        before = json.dumps(old.get(name), sort_keys=True, default=str)
        after = json.dumps(cfg.raw.get(name), sort_keys=True, default=str)
        out[name] = "IMEBADILIKA" if before != after else "sawa"
    return out


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
    p_mt5.add_argument(
        "--catalogue",
        action="store_true",
        help="T4 — orodha ya symbols zote za broker, zikipangwa kwa UNDERLYING MPYA",
    )
    p_mt5.add_argument("--catalogue-limit", type=int, default=40)
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

    p_r1 = subparsers.add_parser(
        "r1-summary",
        help="R1 — labels dhidi ya vigezo vyao (RS-04, DF-21, K1-07) — ushahidi wa T2",
        parents=[common],
    )
    p_r1.add_argument("--symbols", help="orodha ya symbols, comma separated")
    p_r1.add_argument(
        "--cost-pips",
        help="mkunjo wa unyeti wa L-D, mf. 0,0.5,1 (commission+swap; spread imo kwenye path)",
    )
    p_r1.set_defaults(func=cmd_r1_summary)

    p_ev = subparsers.add_parser(
        "r1-ev",
        help="EV kwa kila cell kutoka r1_summary.json (INASOMA tu — haiguswi ushahidi)",
        parents=[common],
    )
    p_ev.add_argument("--cost-pips", type=float, default=0.7, help="commission+swap (default 0.7)")
    p_ev.add_argument("--atr-pips", type=float, default=16.1, help="ATR p50 ya setups")
    p_ev.set_defaults(func=cmd_r1_ev)

    p_cost = subparsers.add_parser(
        "cost-audit",
        help="gharama HALISI kwa R (stop zilizoruka) + identities za T3",
        parents=[common],
    )
    p_cost.add_argument("--symbols")
    p_cost.add_argument("--commission-pips", type=float, default=0.7)
    p_cost.add_argument("--sr-target", type=float, default=0.7, help="SR* iliyosainiwa")
    p_cost.add_argument("--kappa", type=float, default=0.50, help="cost drag / net target")
    p_cost.add_argument("--years", type=float, default=8.25, help="TRAIN+VAL kwa MinBTL")
    p_cost.add_argument(
        "--cell",
        help="cell ya identities, mf. 2.0/3.0. LAZIMA itangazwe — kuichagua kwa "
        "kuangalia jedwali ni uteuzi juu ya label (§4.3)",
    )
    p_cost.set_defaults(func=cmd_cost_audit)

    p_neff = subparsers.add_parser(
        "effective-n",
        help="observations HURU — envelope ya makadirio manne",
        parents=[common],
    )
    p_neff.add_argument("--symbols")
    p_neff.add_argument("--delta", type=float, help="δ_MER — inaonyesha kama N inatosha")
    p_neff.add_argument("--include-control", action="store_true")
    p_neff.set_defaults(func=cmd_effective_n)

    p_eff = subparsers.add_parser(
        "setup-effect",
        help="T3 hatua 2 — je makali ya SETUP-v1 ni utabiri au uteuzi wa volatility?",
        parents=[common],
    )
    p_eff.add_argument("--symbols")
    p_eff.add_argument("--cell", default="2.0/3.0", help="cell iliyosainiwa")
    p_eff.add_argument("--commission-pips", type=float, default=0.7)
    p_eff.add_argument("--bootstrap", type=int, default=500)
    p_eff.set_defaults(func=cmd_setup_effect)

    p_feat = subparsers.add_parser(
        "build-features",
        help="L3 — features 25 kwa kila symbol kutoka bars za H1 (§6.1)",
        parents=[common],
    )
    p_feat.add_argument("--symbols")
    p_feat.set_defaults(func=cmd_build_features)

    p_meta = subparsers.add_parser(
        "meta-label",
        help="T3 hatua 3 — purged CV + malango matatu (INAGHARIMU BAJETI)",
        parents=[common],
    )
    p_meta.add_argument("--symbols")
    p_meta.add_argument("--cell", default="2.0/3.0", help="cell iliyosainiwa")
    p_meta.add_argument("--model", default="logistic", help="`logistic` (msingi) au `xgboost`")
    p_meta.add_argument("--commission-pips", type=float, default=0.7)
    p_meta.add_argument("--bootstrap", type=int, default=500)
    p_meta.add_argument(
        "--unweighted",
        action="store_true",
        help="ondoa uzito wa uniqueness — kwa kulinganisha PEKEE, si kwa hukumu",
    )
    p_meta.set_defaults(func=cmd_meta_label)

    p_plac = subparsers.add_parser(
        "placebo",
        help="T3 hatua 4 — pipeline inatoa nini bila signal? (HAIGHARIMU BAJETI)",
        parents=[common],
    )
    p_plac.add_argument("--symbols")
    p_plac.add_argument("--cell", default="2.0/3.0")
    p_plac.add_argument("--model", default="logistic")
    p_plac.add_argument("--commission-pips", type=float, default=0.7)
    p_plac.add_argument("--reps", type=int, default=20)
    p_plac.add_argument(
        "--mode",
        default="block",
        choices=("block", "rotation", "shuffle", "bernoulli"),
        help="block (chaguo-msingi) ndiyo sahihi; rotation inahifadhi kumbukumbu "
             "ndefu (null imechafuliwa), shuffle inavunja hata τ (null nyembamba mno)",
    )
    p_plac.add_argument(
        "--block",
        type=int,
        default=32,
        help="urefu wa kipande kwa `--mode block` (points ~32 = miezi 1.5)",
    )
    p_plac.add_argument("--seed", type=int, default=20260814)
    p_plac.add_argument("--unweighted", action="store_true")
    p_plac.add_argument(
        "--within-symbol",
        action="store_true",
        help="ondoa base rate ya kila symbol kabla ya kupima — inatenganisha "
             "ujuzi wa WAKATI na utambuzi wa SYMBOL",
    )
    p_plac.set_defaults(func=cmd_placebo)

    p_cross = subparsers.add_parser(
        "cross-power",
        help="T4 — blocs ngapi zinahitajika kupima sheria ya cross-section",
        parents=[common],
    )
    p_cross.add_argument("--rho", type=float, default=0.545, help="athari ya kupimwa")
    p_cross.add_argument("--blocs", type=float, default=7.54, help="participation ratio ya sasa")
    p_cross.add_argument("--symbols", type=int, default=12)
    p_cross.add_argument("--alpha", type=float, default=0.05)
    p_cross.add_argument("--tests", type=int, default=1, help="vipimo vilivyotangazwa")
    p_cross.add_argument("--out")
    p_cross.set_defaults(func=cmd_cross_power)

    p_split = subparsers.add_parser(
        "splits", help="DF-14 / G2 — mpango wa splits + holdout guard (§7)", parents=[common]
    )
    p_split.add_argument("--out", help="andika mpango kama JSON")
    p_split.set_defaults(func=cmd_splits)

    p_cfg = subparsers.add_parser("config-hash", help="fingerprint ya config/data.yaml", parents=[common])
    p_cfg.add_argument(
        "--sections", action="store_true", help="fingerprint ya KILA sehemu, si faili nzima"
    )
    p_cfg.add_argument(
        "--since",
        metavar="COMMIT",
        help="sehemu zipi zimebadilika tangu commit hii (mf. `code_rev` ya sahihi)",
    )
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
