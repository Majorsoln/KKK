"""Wapi pa kutafuta? — DOCTRINE §9.2, §9.7.

EURUSD H1 ilijibu *"haitofautiki"*: mgombea bora wa data halisi alikuwa ndani ya
mgawanyo wa surrogate. Swali linalofuata si "tuboreshe sakafu" bali **"tutafute
wapi"** — na kuendesha Calibration B ya saa 30 kwa kila symbol ili kujua ni
kutumia siku kujibu swali la dakika 30.

Script hii inaendesha kipimo cha §9.7 kwa symbols zote na kupanga matokeo:

```
symbol   halisi   bandia kati   percentile   hukumu
XAUUSD   0.0180        0.0061         100%   SOKO LINA MUUNDO
GBPJPY   0.0090        0.0072          67%   haitofautiki
EURUSD   0.0035        0.0048          40%   haitofautiki
```

Zilizo juu ndizo zinazostahili Calibration B. Zilizo chini kabisa zinasema
kwamba nafasi hii ya kutafuta haipati chochote hapo — jibu la thamani vilevile.

---

**Percentile si uthibitisho.** Kwa surrogate `n`, azimio ni `1/(n+1)`; symbol
inayoongoza inaweza kuwa ya bahati. Hii ni **kuchuja**, si hukumu ya mwisho —
inayofuata ni Calibration B kamili juu ya symbol iliyoongoza.

`--resume` ni ya lazima, si ya starehe: run ni saa kadhaa, na symbol
iliyokwisha pimwa haipimwi tena.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.backtest.engine import BrokerFacts  # noqa: E402
from src.data.load import discover as gundua  # noqa: E402
from src.data.load import load_exclusions  # noqa: E402
from src.data.window import declare, research_window  # noqa: E402
from src.discovery import pipeline as P  # noqa: E402
from src.discovery.generator import GeneratorSpec  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import SymbolSpec, pip_size  # noqa: E402
from src.validation import null_check as NC  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from calibrate_a import _root, pip_value_usd  # noqa: E402
from calibrate_b import _hakikisha_chanzo_kimoja, bars_za_dirisha  # noqa: E402

RIPOTI = REPO / "research" / "reports"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbols", nargs="*", default=None, help="chaguo-msingi: zote")
    ap.add_argument("--tf", default=None)
    ap.add_argument("--candidates", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--surrogate-seeds", type=int, default=2)
    ap.add_argument("--months", type=int, default=0)
    ap.add_argument("--hour-tz", default="UTC")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pip-value", nargs="*", default=[], metavar="SYM=VAL")
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()

    root = _root(args.root)
    cfg_data = load_config(REPO / "config" / "data.yaml")
    cfg_risk = load_config(REPO / "config" / "risk.yaml")
    cfg_broker = load_config(REPO / "config" / "broker_costs.yaml")

    day_tz = str(cfg_data.get("timezone.day_reset_tz"))
    tf = args.tf or str(cfg_data.get("bars.decision_tf"))
    window = research_window(cfg_data)
    stage = declare("scan_symbols", "DOCTRINE §9.7 — wapi pa kutafuta",
                    window, cfg=cfg_data)

    inv = gundua(root, provenance=args.provenance,
                 exclusions=load_exclusions(cfg_data))
    symbols = args.symbols or sorted(inv.symbols)
    print(f"symbols {len(symbols)} · TF {tf} · K {args.candidates:,} · "
          f"surrogate {args.surrogate_seeds * 3} kwa kila moja")
    print(f"dirisha: {window.start} → {window.end}\n")

    out_path = Path(args.out) if args.out else (RIPOTI / f"scan_{tf}.json")
    ck_path = out_path.with_name(out_path.stem + "_checkpoint.jsonl")
    zilizopimwa = _soma_checkpoint(ck_path) if not args.no_resume else {}
    if zilizopimwa:
        print(f"checkpoint: symbols {len(zilizopimwa)} zimehifadhiwa "
              f"({ck_path.name})\n")

    contracts = cfg_broker.get("contract_size", {"default": 100_000})
    commissions = cfg_broker.get("commission_usd_round_turn", {"default": 7.0})
    kwa_mkono = dict(piece.split("=", 1) for piece in args.pip_value)

    matokeo: list[NC.Comparison] = []
    for n, symbol in enumerate(symbols, 1):
        if symbol in zilizopimwa:
            matokeo.append(_kutoka_json(zilizopimwa[symbol]))
            print(f"[{n}/{len(symbols)}] {symbol}  (imehifadhiwa)")
            continue

        print(f"[{n}/{len(symbols)}] {symbol}", flush=True)
        try:
            _hakikisha_chanzo_kimoja(inv, symbol, window)
        except SystemExit as kosa:
            print(f"   IMERUKWA: {str(kosa).splitlines()[0]}\n")
            continue

        pip = pip_size(symbol)
        contract = float(contracts.get(symbol, contracts.get("default", 100_000)))
        if symbol in kwa_mkono:
            pipval = float(kwa_mkono[symbol])
        else:
            pipval, njia = pip_value_usd(symbol, contract, inv)
            if pipval is None:
                print(f"   IMERUKWA: {njia}\n")
                continue

        t0 = time.time()
        bars, n_ticks = bars_za_dirisha(inv, symbol, tf, stage, day_tz=day_tz,
                                        months=args.months, pip=pip, verbose=False)
        print(f"   bars {len(bars):,} · ticks {n_ticks:,} · "
              f"{time.time() - t0:.0f}s", flush=True)

        spec = P.PipelineSpec(
            symbol=symbol, timeframe=tf,
            broker=BrokerFacts(
                spec=SymbolSpec(symbol=symbol, point=pip / 10.0,
                                contract_size=contract, volume_min=0.01,
                                volume_step=0.01, volume_max=50.0),
                pip_value_acct=pipval,
                commission_round_turn=float(
                    commissions.get(symbol, commissions.get("default", 7.0))),
            ),
            generator=GeneratorSpec(symbols=(symbol,)),
            n_candidates=args.candidates, hour_tz=args.hour_tz, day_tz=day_tz,
        )

        linganisho = NC.compare(bars, spec, cfg_risk=cfg_risk, seed=args.seed,
                                n_surrogate_seeds=args.surrogate_seeds,
                                progress=print)
        print(f"   → {NC.UJUMBE[linganisho.hukumu]}\n", flush=True)
        matokeo.append(linganisho)
        if not args.no_resume:
            _andika_checkpoint(ck_path, linganisho)

    if not matokeo:
        print("Hakuna symbol iliyopimwa.")
        return 1

    print("\n" + NC.render_table(matokeo))

    bora = NC.rank(matokeo)[0]
    print()
    if bora.hukumu == NC.HAKUNA:
        # Hakuna symbol hata moja iliyotoa mshindi pande zote mbili. Kusema
        # "nafasi ya kutafuta haipati chochote" hapa kungekuwa hitimisho kutoka
        # kwenye kutokuwepo kwa data — si sawa na jibu la "hapana".
        print(f"HAKUNA SYMBOL ILIYOPIMIKA. Hakuna iliyotoa mshindi pande zote\n"
              f"   mbili, kwa hiyo hakuna cha kulinganisha. Ongeza "
              f"--candidates.")
        return 1
    if bora.hukumu == NC.MUUNDO:
        print(f"{bora.symbol} imezidi surrogate ZOTE ({bora.percentile:.0%}, "
              f"azimio ±{bora.azimio:.0%}).\n"
              f"   Ndipo pa kuelekeza Calibration B. Kumbuka: kwa surrogate "
              f"{bora.n_bandia}, hii\n"
              f"   ni KUCHUJA, si uthibitisho — inayofuata ni Calibration B "
              f"kamili.")
    else:
        print(f"Hakuna symbol iliyozidi surrogate zake zote. Ya juu ni "
              f"{bora.symbol} ({bora.percentile:.0%}).\n"
              f"   Nafasi hii ya kutafuta — masharti manne ya nasibu, TF moja "
              f"— haipati chochote\n"
              f"   kwenye symbols hizi. Kinachofuata ni kupanua nafasi "
              f"(§10.4 evolution, TF nyingine),\n"
              f"   si kushusha sakafu.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timeframe": tf, "n_candidates": args.candidates, "seed": args.seed,
        "surrogate_seeds": args.surrogate_seeds,
        "symbols": [c.to_json() for c in NC.rank(matokeo)],
    }, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {out_path}")
    return 0


# ===========================================================================
# Checkpoint — run ni saa kadhaa
# ===========================================================================


def _soma_checkpoint(path: Path) -> dict:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue                      # mstari uliokatika mashine ikizimika
        out[row["symbol"]] = row
    return out


def _andika_checkpoint(path: Path, linganisho: NC.Comparison) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(linganisho.to_json(), default=str) + "\n")
        fh.flush()


def _kutoka_json(row: dict) -> NC.Comparison:
    def run(r):
        return NC.Run(jina=r["jina"], n_passed=int(r["n_passed"]),
                      metrics={k: float(v) for k, v in r["metrics"].items()},
                      seconds=float(r.get("seconds", 0.0)))

    return NC.Comparison(
        symbol=row["symbol"], timeframe=row["timeframe"],
        n_bars=int(row["n_bars"]), n_candidates=int(row["n_candidates"]),
        seed=int(row["seed"]), halisi=run(row["halisi"]),
        bandia=[run(r) for r in row["bandia"]],
    )


if __name__ == "__main__":
    raise SystemExit(main())
