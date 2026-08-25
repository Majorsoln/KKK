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

`--probe` inaendesha runs chache kwanza na kujibu maswali **mawili**: itachukua
muda gani, na — gumu zaidi — **replicates ngapi zitatoa mshindi hata mmoja**.
`calibrate()` inaruka `NaN`, kwa hiyo replicate isiyo na mshindi haihesabiki
kwenye `MIN_REPLICATES`. Bila ukaguzi huu, saa 40 zingeweza kuishia
`without_floor` kwa kila metric — na R5 isingefunguka.

`--dry-run` inasimama baada ya kupima.
"""

from __future__ import annotations

import argparse
import json
import math
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
    ap.add_argument("--tf", default=None,
                    help="chaguo-msingi ni `bars.decision_tf` ya data.yaml (R11)")
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
    ap.add_argument("--probe", type=int, default=3,
                    help="runs za kupima kabla ya kuanza — zinakadiria muda NA "
                         "kiwango cha washindi")
    ap.add_argument("--dry-run", action="store_true",
                    help="pima kisha simama, bila kujitoa kwenye run kamili")
    args = ap.parse_args()

    root = _root(args.root)
    cfg_data = load_config(REPO / "config" / "data.yaml")
    cfg_risk = load_config(REPO / "config" / "risk.yaml")
    cfg_broker = load_config(REPO / "config" / "broker_costs.yaml")

    # Bila default: kigezo hiki KIPO kwenye `data.yaml`, na `.get` yenye default
    # ingerudisha "UTC" kimya kama ufunguo ungeandikwa vibaya — siku ya broker
    # ingehama saa mbili, na hakuna kitu kingelalamika.
    day_tz = str(cfg_data.get("timezone.day_reset_tz"))
    tf = args.tf or str(cfg_data.get("bars.decision_tf"))      # R11
    window = research_window(cfg_data)
    stage = declare("calibration_b", "DOCTRINE §9.2 — sakafu ya kelele",
                    window, cfg=cfg_data)

    print(f"L0: {root}")
    print(f"dirisha: {window.start} → {window.end} · day_tz {day_tz}")
    print(f"symbol {args.symbol} · TF {tf} · hour_tz {args.hour_tz}")
    if args.hour_tz == "UTC" and day_tz != "UTC":
        print(f"   KUMBUKA (§8.6): `hour` inatumia UTC wakati siku ya broker ni "
              f"{day_tz}.\n"
              f"         Feeds mbili hazitumii mkataba mmoja; chaguo hili ni "
              f"lako, si la kimya.")
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
    bars, n_ticks = bars_za_dirisha(inv, args.symbol, tf, stage,
                                    day_tz=day_tz, months=args.months, pip=pip)
    print(f"   bars {len(bars):,} · ticks {n_ticks:,} · {time.time() - t0:.0f}s\n")

    spec = P.PipelineSpec(
        symbol=args.symbol, timeframe=tf,
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

    # ---- kipimo kabla ya kujitoa kwenye saa nyingi ----
    #
    # Runs za sampuli zinajibu maswali MAWILI, na la pili ndilo gumu: si tu
    # "itachukua muda gani" bali "replicates ngapi zitatoa mshindi hata mmoja".
    # `calibrate()` inaruka `NaN`, kwa hiyo replicate isiyo na mshindi
    # HAIHESABIKI — na `MIN_REPLICATES` inahesabu zilizo na thamani, si
    # zilizoendeshwa. Kutoangalia hili kungetoa saa 40 zinazoishia
    # `without_floor` kwa kila metric.
    n_sampuli = max(1, args.probe)
    print(f"Kupima runs {n_sampuli}…", flush=True)
    muda = []
    washindi = 0
    for i in range(n_sampuli):
        sur = S.make(bars, S.BLOCK, seed=NF._seed_of(args.seed, S.BLOCK, i))
        t0 = time.time()
        sampuli = run_pipeline(sur.frame)
        muda.append(time.time() - t0)
        ana_mshindi = any(v == v for k, v in sampuli.items() if k != NF.VARIANTS_KEY)
        washindi += int(ana_mshindi)
        print(f"   {i + 1}/{n_sampuli}  {muda[-1]:>6.1f}s  "
              f"variants {sampuli[NF.VARIANTS_KEY]:>6,}  "
              f"{'mshindi' if ana_mshindi else 'HAKUNA'}", flush=True)

    wastani = sum(muda) / len(muda)
    runs_zote = args.replicates * len(S.FAMILIES)
    print(f"\n   run moja {wastani:.1f}s (wastani wa {n_sampuli})")
    print(f"   TABIRI: runs {runs_zote:,} → {wastani * runs_zote / 3600:.1f} saa")

    kiwango = washindi / n_sampuli
    print(f"   washindi {washindi}/{n_sampuli} = {kiwango:.0%}")
    if kiwango >= 1.0:
        print(f"   replicates {args.replicates} zinatosha "
              f"(dai {NF.MIN_REPLICATES}).\n")
    elif kiwango > 0.0:
        # Replicates zinazohitajika ili `MIN_REPLICATES` ziwe na thamani.
        inahitajika = math.ceil(NF.MIN_REPLICATES / kiwango)
        print(f"   ONYO: kwa kiwango hiki, replicates {args.replicates} "
              f"zingetoa ~{int(args.replicates * kiwango)} zenye thamani, "
              f"chini ya {NF.MIN_REPLICATES}.\n"
              f"         Chaguo: --replicates {inahitajika} "
              f"(~{wastani * inahitajika * len(S.FAMILIES) / 3600:.1f} saa) "
              f"AU --candidates kubwa zaidi.\n")
    else:
        print("   ONYO: hakuna run iliyotoa mshindi hata mmoja.\n"
              "         Kila metric ingeishia `without_floor` na R5 haitafunguka.\n"
              "         Ongeza --candidates kabla ya kuendelea.\n")

    if args.dry_run:
        return 0

    floor = NF.calibrate(
        bars, run_pipeline,
        n_replicates=args.replicates, seed=args.seed,
        source=f"{args.symbol} {tf} · bars {len(bars):,} · "
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
