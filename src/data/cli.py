"""CLI ya tabaka la data (T0).

    python -m src.data.cli init-research      # §9 — muundo wa research storage
    python -m src.data.cli hash-l0            # DF-01 — SHA256 ya partitions ZOTE + manifest
    python -m src.data.cli verify-l0          # DF-01 — lango la CI (hash check kila build)
    python -m src.data.cli record             # DF-04 — recorder wa feed ya broker
    python -m src.data.cli check-freshness    # DF-04 — ONYO: siku ya trading bila data
    python -m src.data.cli inspect <faili>    # DF-02 — schema moja kutoka Toleo A/B
    python -m src.data.cli config-hash        # fingerprint ya config/data.yaml (§8)

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
        on_progress=_progress,
    )
    print(
        f"L0 hashing: scanned={result.scanned} added={result.added} "
        f"confirmed={result.confirmed} skipped={result.skipped} "
        f"mutated={len(result.mutated)} · {time.monotonic() - started:.0f}s"
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

    p_fresh = subparsers.add_parser("check-freshness", help="DF-04 — ONYO la siku isiyorekodiwa", parents=[common])
    p_fresh.add_argument("--json", action="store_true")
    p_fresh.add_argument("--out", help="andika ripoti ya JSON kwenye faili")
    p_fresh.add_argument("--require-storage", action="store_true")
    p_fresh.set_defaults(func=cmd_check_freshness)

    p_inspect = subparsers.add_parser("inspect", help="DF-02 — schema moja kutoka Toleo A/B", parents=[common])
    p_inspect.add_argument("paths", nargs="+")
    p_inspect.set_defaults(func=cmd_inspect)

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
