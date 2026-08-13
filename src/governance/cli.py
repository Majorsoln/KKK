"""CLI ya usimamizi — sahihi ya PD (§0 ya IMPLEMENTATION_PLAN).

    python -m src.governance.cli sign DF-05 VERIFIED --evidence <faili> --reason "<ulichokiona>"
    python -m src.governance.cli verify          # lango G14 (CI)
    python -m src.governance.cli pending         # ni nini kinasubiri sahihi yangu?
    python -m src.governance.cli show            # sahihi zote zilizowekwa

Exit codes: 0 = sawa · 1 = kuna tatizo la kusainiwa · 2 = hitilafu ya matumizi.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .signatures import (
    DECISIONS,
    LEDGER,
    PLAN,
    SignatureError,
    append,
    load,
    pending,
    register_ids,
    verify,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_sign(args: argparse.Namespace) -> int:
    root = _repo_root()
    from src.data.config import load_config
    from src.data.manifest import code_rev

    # SABABU NDIYO SAHIHI YENYEWE. Namba, muda na hash zinathibitisha KWAMBA
    # mtu alisaini; sababu peke yake ndiyo inayosema **alichokiona**. Mstari
    # wa `...` unapita lango G14 (sababu si tupu) na hauambii kizazi kijacho
    # chochote — ni mhuri, si ukaguzi. Alama hiyo ya mfano ilikuwa kwenye
    # msaada wangu mwenyewe, na PD aliinakili; kuikataa hapa ni haki.
    if not any(ch.isalnum() for ch in args.reason):
        print(
            f'sababu `{args.reason}` haina neno hata moja — ni alama ya mfano, si ukaguzi.\n'
            "Andika ULICHOKIONA kwenye ushahidi: namba zenyewe na kwa nini zinatosha.",
            file=sys.stderr,
        )
        return 2
    if args.decision == "VERIFIED" and len(args.reason.strip()) < 20:
        print(
            f"ONYO: sababu ya VERIFIED ina herufi {len(args.reason.strip())} pekee. "
            "Mtu wa mwaka ujao ataisoma bila kumbukumbu yako.",
            file=sys.stderr,
        )

    try:
        config_hash = load_config(args.config).config_hash
    except Exception as exc:  # config isiyosomeka isizuie sahihi ya kitu kisicho cha data
        if args.require_config:
            print(f"config haijasomeka: {exc}", file=sys.stderr)
            return 2
        config_hash = ""

    signature = append(
        item=args.item,
        decision=args.decision,
        reason=args.reason,
        config_hash=config_hash,
        code_rev=code_rev(root),
        evidence=Path(args.evidence) if args.evidence else None,
        ledger=root / LEDGER,
        plan=root / PLAN,
        root=root,
    )
    print(f"sahihi #{signature.number} imewekwa:")
    print(f"  {signature.item} → {signature.decision}  ({DECISIONS[signature.decision]})")
    print(f"  mwenye sahihi : {signature.signer}")
    print(f"  config_hash   : {signature.config_hash[:12] or '—'}")
    print(f"  code_rev      : {signature.code_rev}")
    if signature.evidence:
        print(f"  ushahidi      : {signature.evidence}  sha256 {signature.evidence_sha256[:12]}")
    print()
    print("HAIJAKAMILIKA HADI UCOMMIT — commit ndiyo sahihi yenyewe:")
    print(f'  git add {LEDGER} && git commit -m "sahihi: {signature.item} {signature.decision}"')
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = _repo_root()
    report = verify(
        ledger=root / LEDGER,
        plan=root / PLAN,
        root=root,
        check_evidence=not args.no_evidence,
    )
    print(report.render())
    if args.json:
        print(json.dumps({"ok": report.ok, "problems": report.problems}, indent=2))
    return 0 if report.ok else 1


def cmd_pending(args: argparse.Namespace) -> int:
    root = _repo_root()
    items = register_ids(root / PLAN)
    waiting = pending(items, ledger=root / LEDGER)
    signed = sorted(set(items) - set(waiting))
    print(f"vimesainiwa : {len(signed)}/{len(items)}")
    print(f"vinasubiri  : {len(waiting)}")
    for item in waiting[: args.limit]:
        print(f"  · {item}")
    if len(waiting) > args.limit:
        print(f"  … na vingine {len(waiting) - args.limit}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = _repo_root()
    rows = load(root / LEDGER)
    if args.json:
        print(json.dumps([s.to_json() for s in rows], indent=2))
        return 0
    if not rows:
        print("hakuna sahihi bado.")
        return 0
    for signature in rows:
        print(
            f"#{signature.number} {signature.signed_at} · {signature.item} "
            f"→ {signature.decision} · {signature.signer}"
        )
        print(f"      {signature.reason}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.governance.cli",
        description="Sahihi ya PD — §0 ya docs/IMPLEMENTATION_PLAN.md",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_sign = subparsers.add_parser("sign", help="weka sahihi kwenye kipengele cha rejista")
    p_sign.add_argument("item", help="ID ya rejista (mf. DF-05)")
    p_sign.add_argument("decision", help=" · ".join(DECISIONS))
    p_sign.add_argument("--evidence", help="faili la ushahidi (LAZIMA kwa VERIFIED)")
    p_sign.add_argument("--reason", required=True, help="unachokiona kwenye ushahidi")
    p_sign.add_argument("--config", help="njia ya data.yaml")
    p_sign.add_argument("--require-config", action="store_true")
    p_sign.set_defaults(func=cmd_sign)

    p_verify = subparsers.add_parser("verify", help="lango G14 — sahihi zote ni halali?")
    p_verify.add_argument("--json", action="store_true")
    p_verify.add_argument(
        "--no-evidence",
        action="store_true",
        help="usikague SHA256 za ushahidi (faili za research haziko kwenye CI)",
    )
    p_verify.set_defaults(func=cmd_verify)

    p_pending = subparsers.add_parser("pending", help="vipengele vinavyosubiri sahihi ya PD")
    p_pending.add_argument("--limit", type=int, default=30)
    p_pending.set_defaults(func=cmd_pending)

    p_show = subparsers.add_parser("show", help="sahihi zote zilizowekwa")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_show)

    p_bud = subparsers.add_parser(
        "budget", help="bajeti ya majaribio (MinBTL) — imebaki ngapi"
    )
    p_bud.add_argument("--ledger")
    p_bud.set_defaults(func=cmd_budget)

    p_bud_init = subparsers.add_parser(
        "budget-init", help="tangaza bajeti — PD anasaini kwa commit"
    )
    p_bud_init.add_argument("--sr-target", type=float, required=True)
    p_bud_init.add_argument("--years", type=float, required=True)
    p_bud_init.add_argument("--ledger")
    p_bud_init.set_defaults(func=cmd_budget_init)

    p_spend = subparsers.add_parser(
        "budget-spend", help="andika matumizi ya config dhidi ya labels"
    )
    p_spend.add_argument("config_id")
    p_spend.add_argument("--weight", type=float, default=1.0)
    p_spend.add_argument("--kind", default="EVALUATION", choices=["EVALUATION", "REPLICATION"])
    p_spend.add_argument("--reason", required=True)
    p_spend.add_argument("--ledger")
    p_spend.set_defaults(func=cmd_budget_spend)
    return parser


def cmd_budget(args: argparse.Namespace) -> int:
    from . import budget as bud

    path = Path(args.ledger) if args.ledger else None
    loaded = bud.load(path)
    if loaded.total <= 0:
        print(
            "bajeti haijatangazwa. Itangaze KABLA ya evaluation ya kwanza:\n"
            "  python -m src.governance.cli budget-init --sr-target 0.7 --years 8.25",
            file=sys.stderr,
        )
        return 2
    print(f"BAJETI YA MAJARIBIO — SR* {loaded.sr_target} · miaka {loaded.years}")
    print(f"  jumla     {loaded.total:>7.1f} configs   (MinBTL)")
    print(f"  imetumika {loaded.spent:>7.1f}")
    print(f"  imebaki   {loaded.remaining:>7.1f}")
    for entry in loaded.entries:
        print(f"  #{entry.number} {entry.kind:<11} {entry.weight:>5.1f}  {entry.config_id}")
    if loaded.exhausted:
        print("\nIMEKWISHA — hakuna evaluation nyingine dhidi ya labels inayoruhusiwa.",
              file=sys.stderr)
        return 1
    return 0


def cmd_budget_init(args: argparse.Namespace) -> int:
    from . import budget as bud

    path = Path(args.ledger) if args.ledger else bud.LEDGER
    if path.is_file():
        print(f"{path} tayari ipo — bajeti haitangazwi mara mbili", file=sys.stderr)
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bud.render_header(args.sr_target, args.years), encoding="utf-8")
    total = bud.total_for(args.sr_target, args.years)
    print(f"{path} imeandikwa: SR* {args.sr_target} · miaka {args.years} → configs {total:.1f}")
    print("\nHAIJAKAMILIKA HADI UCOMMIT — commit ndiyo sahihi yenyewe:")
    print(f'  git add {path} && git commit -m "bajeti ya majaribio: SR* {args.sr_target}"')
    return 0


def cmd_budget_spend(args: argparse.Namespace) -> int:
    from . import budget as bud

    path = Path(args.ledger) if args.ledger else None
    entry = bud.spend(
        args.config_id, args.weight, args.reason, kind=args.kind, path=path
    )
    print(f"#{entry.number} {entry.kind} `{entry.config_id}` uzito {entry.weight:.1f}")
    print(f"  imebaki: {entry.remaining:.1f}")
    return 0


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
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except SignatureError as exc:
        print(f"SAHIHI IMEKATALIWA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
