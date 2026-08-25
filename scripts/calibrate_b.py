"""Calibration B — sakafu ya kelele (DOCTRINE §9.2, R5, R15).

```
bars halisi ──▶ familia TATU za data bandia ──▶ pipeline ILE ILE ──▶ p95 ──▶ sakafu
```

Kinachopimwa si "je strategy hii ni nzuri?" bali *"injini hii, ikipewa data
isiyo na edge KABISA, inagundua nini?"* Jibu ni sakafu, na kila lango la §13
linalipima dhidi yake.

---

**Kwa nini inachukua muda.** Runs ni `familia 3 × replicates` — kwa chaguo-msingi
150 — na kila run inaendesha wagombea `--candidates` juu ya historia nzima.
Hakuna njia ya mkato: `--replicates` chini ya 50 inakataliwa na
`noise_floor.MIN_REPLICATES` kwa sababu p95 ya pointi 20 ni thamani ya pili kwa
ukubwa — jina lake ni percentile, tabia yake ni `max`.

`--dry-run` inapima run MOJA na kutabiri muda wa jumla kabla ya kuanza.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.backtest.engine import BrokerFacts  # noqa: E402
from src.data.bars import build  # noqa: E402
from src.data.load import discover, iter_months, load_exclusions  # noqa: E402
from src.data.window import declare, research_window  # noqa: E402
from src.discovery import pipeline as P  # noqa: E402
from src.discovery.generator import GeneratorSpec  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import SymbolSpec, pip_size  # noqa: E402
from src.validation import noise_floor as NF  # noqa: E402
from src.validation import surrogates as S  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from calibrate_a import _root, pip_value_usd  # noqa: E402


def bars_za_dirisha(inv, symbol: str, timeframe: str, stage, *, day_tz: str,
                    months: int, pip: float, verbose: bool = True):
    """Bars za historia nzima, mwezi kwa mwezi kisha zikiunganishwa.

    Ticks zinasomwa kwa mwezi (GB kadhaa kwa symbol) lakini bars zinazobaki ni
    ndogo: H1 ya miaka 8 ni rows ~50,000.
    """
    import pandas as pd

    vipande = []
    n_ticks = 0
    for i, (label, chunk, report) in enumerate(
        iter_months(inv, symbol, stage, max_spread_pips=None, pip=pip, strict=False)
    ):
        if months and i >= months:
            break
        bars = build(chunk, timeframe, stage, day_tz=day_tz).bars
        n_ticks += len(chunk)
        if len(bars):
            vipande.append(bars)
        if verbose:
            print(f"   {symbol} {label}  ticks {len(chunk):>9,}  bars {len(bars):>6,}"
                  f"  onyo {len(report.warnings)}", flush=True)

    if not vipande:
        raise SystemExit(f"hakuna bars za {symbol} {timeframe}")
    out = pd.concat(vipande).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    out.attrs["symbol"] = symbol
    return out, n_ticks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--tf", default="H1", help="R11 inafunga entry kwenye H1")
    ap.add_argument("--candidates", type=int, default=200,
                    help="wagombea kwa kila replicate — K ya §9.1")
    ap.add_argument("--replicates", type=int, default=NF.MIN_REPLICATES)
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--months", type=int, default=0, help="0 = zote")
    ap.add_argument("--max-conditions", type=int, default=4)
    ap.add_argument("--hour-tz", default="UTC",
                    help="§8.6 — feeds mbili hazitumii mkataba mmoja")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pip-value", nargs="*", default=[], metavar="SYM=VAL")
    ap.add_argument("--dry-run", action="store_true",
                    help="pima run MOJA, tabiri muda, kisha simama")
    args = ap.parse_args()

    root = _root(args.root)
    cfg_data = load_config(REPO / "config" / "data.yaml")
    cfg_risk = load_config(REPO / "config" / "risk.yaml")
    cfg_broker = load_config(REPO / "config" / "broker_costs.yaml")

    day_tz = str(cfg_data.get("broker_server_tz", "UTC"))
    window = research_window(cfg_data)
    stage = declare(window, name="calibration_b", purpose="DOCTRINE §9.2")

    print(f"L0: {root}")
    print(f"dirisha: {window.start.date()} → {window.end.date()} · day_tz {day_tz}")
    print(f"symbol {args.symbol} · TF {args.tf} · hour_tz {args.hour_tz}")
    print(f"wagombea {args.candidates:,} · replicates {args.replicates} × "
          f"familia {len(S.FAMILIES)} = runs {args.replicates * len(S.FAMILIES):,}\n")

    inv = discover(root, provenance=args.provenance,
                   exclusions=load_exclusions(cfg_data))
    if not inv.of(args.symbol):
        raise SystemExit(f"hakuna data ya {args.symbol} kwenye {root}")

    pip = pip_size(args.symbol)
    contracts = cfg_broker.get("contract_size", {"default": 100_000})
    commissions = cfg_broker.get("commission_usd_round_turn", {"default": 7.0})
    contract = float(contracts.get(args.symbol, contracts.get("default", 100_000)))
    if not bool(cfg_broker.get("contract_size_confirmed", False)):
        print("   ONYO: `contract_size_confirmed: false` — `pip_value` inategemea\n"
              "         namba isiyothibitishwa kwa MT5.\n")

    kwa_mkono = dict(
        piece.split("=", 1) for piece in args.pip_value
    )
    if args.symbol in kwa_mkono:
        pipval, njia = float(kwa_mkono[args.symbol]), "--pip-value"
    else:
        pipval, njia = pip_value_usd(args.symbol, contract, inv)
    if pipval is None:
        raise SystemExit(njia)

    print("Kujenga bars…", flush=True)
    t0 = time.time()
    bars, n_ticks = bars_za_dirisha(inv, args.symbol, args.tf, stage,
                                    day_tz=day_tz, months=args.months, pip=pip)
    print(f"   bars {len(bars):,} · ticks {n_ticks:,} · {time.time() - t0:.0f}s\n")

    spec = P.PipelineSpec(
        symbol=args.symbol, timeframe=args.tf,
        broker=BrokerFacts(
            spec=SymbolSpec(symbol=args.symbol, point=pip / 10.0,
                            contract_size=contract, volume_min=0.01,
                            volume_step=0.01, volume_max=50.0),
            pip_value_acct=pipval,
            commission_round_turn=float(
                commissions.get(args.symbol, commissions.get("default", 7.0))),
        ),
        generator=GeneratorSpec(symbols=(args.symbol,),
                                max_conditions=args.max_conditions),
        n_candidates=args.candidates,
        hour_tz=args.hour_tz, day_tz=day_tz,
    )
    run_pipeline = P.for_calibration(spec, cfg_risk=cfg_risk, seed=args.seed)

    # ---- kipimo cha run MOJA kabla ya kujitoa kwenye 150 ----
    print("Kupima run moja…", flush=True)
    sur = S.make(bars, S.BLOCK, seed=args.seed)
    t0 = time.time()
    sampuli = run_pipeline(sur.frame)
    dakika_moja = time.time() - t0
    jumla = dakika_moja * args.replicates * len(S.FAMILIES)
    print(f"   run moja {dakika_moja:.1f}s · variants {sampuli[NF.VARIANTS_KEY]:,}")
    print(f"   TABIRI: runs {args.replicates * len(S.FAMILIES):,} → "
          f"{jumla / 3600:.1f} saa\n")

    walipita = sum(1 for k, v in sampuli.items()
                   if k != NF.VARIANTS_KEY and v == v)
    if walipita == 0:
        print("   ONYO: run hii haikutoa mshindi hata mmoja — metrics zote ni NaN.\n"
              "         Sakafu inahitaji thamani zisizo NaN kwa replicates "
              f"{NF.MIN_REPLICATES}+ kwa kila familia.\n"
              "         Ongeza --candidates, la sivyo kila metric itaishia "
              "`without_floor` na R5 haitafunguka.\n")

    if args.dry_run:
        return 0

    floor = NF.calibrate(
        bars, run_pipeline,
        n_replicates=args.replicates, seed=args.seed,
        source=f"{args.symbol} {args.tf} · bars {len(bars):,} · "
               f"K={args.candidates} · {root}",
    )

    out_path = Path(args.out) if args.out else (
        REPO / "research" / "reports" / "noise_floor.json")
    floor.write(out_path)
    print(f"\nimeandikwa: {out_path}")

    kando = out_path.with_name(out_path.stem + "_spec.json")
    kando.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline": spec.to_json(),
        "n_bars": int(len(bars)), "n_ticks": int(n_ticks),
        "seed": args.seed, "replicates": args.replicates,
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"imeandikwa: {kando}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
