"""Je data bandia ni RAHISI kuliko soko halisi? (DOCTRINE §9.2, R15)

Sakafu ya kelele inasimama juu ya dhana moja isiyokuwa imepimwa: kwamba data
bandia ina **ugumu ule ule** wa soko halisi, ikiwa imeondolewa utabirikaji
pekee. Ikiwa ni rahisi zaidi, sakafu iko juu kupita kiasi na inakataa kila kitu;
ikiwa ni ngumu zaidi, sakafu iko chini na inapitisha kelele.

Dhana hiyo haijawahi kupimwa moja kwa moja. Script hii inaipima.

---

**Muundo: generator ILE ILE, data TOFAUTI.**

```
seed ile ile ya generator  →  wagombea WALE WALE
                              ├── juu ya bars HALISI
                              └── juu ya surrogate ya bars zile zile
```

Kwa kuwa wagombea ni wale wale, tofauti yoyote ya matokeo **inatoka kwenye data
pekee**. Hilo ndilo swali: je surrogate inatoa strategies bora kuliko soko
lililoizaa?

**Kinachotarajiwa ikiwa null ni sahihi:** surrogate inapaswa kuwa **ngumu au
sawa** — imeondolewa utabirikaji, kwa hiyo strategies zinapaswa kufanya vibaya
zaidi, si vizuri zaidi.

**Ikiwa surrogate ni rahisi kwa kiasi kikubwa**, sakafu si sakafu ya "soko bila
edge"; ni sakafu ya soko lingine. §9.2 inaonya juu ya hili yenyewe: *sakafu ya
familia moja ni nusu tabia ya soko, nusu tabia ya generator.*

---

Gharama: runs `1 + familia × seeds`. Kwa `K` ndogo, ni dakika chache — na jibu
lake linaamua kama sakafu ya saa 30 ni halali au la.
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
from src.validation import noise_floor as NF  # noqa: E402
from src.validation import surrogates as S  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from calibrate_a import _root, pip_value_usd  # noqa: E402
from calibrate_b import _hakikisha_chanzo_kimoja, bars_za_dirisha  # noqa: E402

VIPIMO = ("net_account_return_month", "net_pips_month", "sharpe",
          "profitable_month_fraction", "profit_factor", "max_drawdown")


def _endesha(bars, spec, cfg_risk, seed, jina: str):
    t0 = time.time()
    out = P.search(bars, spec, cfg_risk=cfg_risk, seed=seed,
                   starting_balance=10_000.0)
    m = out.metrics()
    print(f"   {jina:<26} walipita §8.4 {out.n_passed_economics:>4} · "
          f"return/mwezi {m['net_account_return_month']:>8.4f} · "
          f"pips/mwezi {m['net_pips_month']:>9.1f} · "
          f"sharpe {m['sharpe']:>7.2f}  ({time.time() - t0:.0f}s)", flush=True)
    return {"n_passed": out.n_passed_economics,
            **{k: m.get(k, float("nan")) for k in VIPIMO}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--tf", default=None)
    ap.add_argument("--candidates", type=int, default=200,
                    help="K ndogo inatosha: swali ni ULINGANISHO, si sakafu")
    ap.add_argument("--seed", type=int, default=1, help="seed ya GENERATOR")
    ap.add_argument("--surrogate-seeds", type=int, default=2)
    ap.add_argument("--months", type=int, default=0)
    ap.add_argument("--hour-tz", default="UTC")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pip-value", nargs="*", default=[], metavar="SYM=VAL")
    args = ap.parse_args()

    root = _root(args.root)
    cfg_data = load_config(REPO / "config" / "data.yaml")
    cfg_risk = load_config(REPO / "config" / "risk.yaml")
    cfg_broker = load_config(REPO / "config" / "broker_costs.yaml")

    day_tz = str(cfg_data.get("timezone.day_reset_tz"))
    tf = args.tf or str(cfg_data.get("bars.decision_tf"))
    window = research_window(cfg_data)
    stage = declare("null_vs_real", "DOCTRINE §9.2 — je null ni rahisi?",
                    window, cfg=cfg_data)

    inv = gundua(root, provenance=args.provenance,
                 exclusions=load_exclusions(cfg_data))
    _hakikisha_chanzo_kimoja(inv, args.symbol, window)

    pip = pip_size(args.symbol)
    contracts = cfg_broker.get("contract_size", {"default": 100_000})
    commissions = cfg_broker.get("commission_usd_round_turn", {"default": 7.0})
    contract = float(contracts.get(args.symbol, contracts.get("default", 100_000)))
    kwa_mkono = dict(piece.split("=", 1) for piece in args.pip_value)
    if args.symbol in kwa_mkono:
        pipval = float(kwa_mkono[args.symbol])
    else:
        pipval, njia = pip_value_usd(args.symbol, contract, inv)
        if pipval is None:
            raise SystemExit(njia)

    print(f"symbol {args.symbol} · TF {tf} · K {args.candidates:,} · "
          f"seed ya generator {args.seed}")
    print("Kujenga bars…", flush=True)
    bars, n_ticks = bars_za_dirisha(inv, args.symbol, tf, stage, day_tz=day_tz,
                                    months=args.months, pip=pip, verbose=False)
    print(f"   bars {len(bars):,} · ticks {n_ticks:,}\n")

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
        generator=GeneratorSpec(symbols=(args.symbol,)),
        n_candidates=args.candidates, hour_tz=args.hour_tz, day_tz=day_tz,
    )

    print("Wagombea WALE WALE, data tofauti:")
    halisi = _endesha(bars, spec, cfg_risk, args.seed, "HALISI")

    bandia: dict[str, list] = {}
    for fam in S.FAMILIES:
        bandia[fam] = []
        for i in range(max(1, args.surrogate_seeds)):
            sur = S.make(bars, fam, seed=NF._seed_of(args.seed, fam, i))
            bandia[fam].append(
                _endesha(sur.frame, spec, cfg_risk, args.seed, f"{fam} #{i}"))

    # ---- hukumu ----
    print(f"\n{'kipimo':<28} {'HALISI':>12} {'bandia (kati)':>14}   uwiano")
    hukumu: dict[str, float] = {}
    zote = [r for rows in bandia.values() for r in rows]
    for jina in VIPIMO:
        h = halisi[jina]
        b = sorted(r[jina] for r in zote if r[jina] == r[jina])
        if not b:
            continue
        kati = b[len(b) // 2]
        uwiano = (kati / h) if h not in (0.0,) and h == h else float("nan")
        hukumu[jina] = uwiano
        print(f"{jina:<28} {h:>12.4f} {kati:>14.4f}   {uwiano:>6.2f}×")

    n_h = halisi["n_passed"]
    n_b = sorted(r["n_passed"] for r in zote)[len(zote) // 2]
    print(f"{'walipita §8.4':<28} {n_h:>12,} {n_b:>14,}")


    # ---- hukumu: PERCENTILE, si uwiano dhidi ya kizingiti nilichobuni ----
    #
    # Uwiano wa wastani unahitaji kizingiti ("1.5× ni kubwa mno") ambacho ni
    # namba isiyopimwa — §2 inaikataa. Percentile haihitaji chochote: inauliza
    # **surrogate ngapi zilishindwa na data halisi**, na jibu lake linajieleza.
    print()
    jina = "net_account_return_month"
    thamani_b = sorted(r[jina] for r in zote if r[jina] == r[jina])
    h = halisi[jina]

    if halisi["n_passed"] == 0 or not thamani_b or h != h:
        print(f"HAKUNA ULINGANISHO. Washindi: halisi {halisi['n_passed']}, "
              f"bandia zenye thamani {len(thamani_b)}.\n"
              f"   Upande usio na mshindi hauwezi kulinganishwa. Ongeza "
              f"--candidates au --surrogate-seeds.")
        return _andika(args, tf, bars, halisi, bandia, hukumu,
                       "hakuna_ulinganisho", None)

    chini = sum(1 for x in thamani_b if x < h)
    pct = chini / len(thamani_b)
    ukingo = 1.0 / (len(thamani_b) + 1)

    print(f"`{jina}` ya data HALISI dhidi ya surrogate:")
    print(f"   surrogate: {' · '.join(f'{x:.4f}' for x in thamani_b)}")
    print(f"   halisi:    {h:.4f}   →  imezidi {chini}/{len(thamani_b)} "
          f"= {pct:.0%}")
    print(f"   ukingo wa kipimo: ±{ukingo:.0%} (surrogate {len(thamani_b)})\n")

    if pct <= ukingo:
        print("NULL NI RAHISI KULIKO SOKO. Kila surrogate — au karibu kila moja —\n"
              "   imeshinda data halisi. Sakafu iko juu kupita kiasi na si halali.")
        alama = "bandia_ni_rahisi"
    elif pct >= 1.0 - ukingo:
        print("SOKO LINA MUUNDO AMBAO NULL HAINA. Data halisi imezidi karibu kila\n"
              "   surrogate — ndicho kinachotafutwa. Sakafu ni halali na kali.")
        alama = "halisi_ina_muundo"
    else:
        print("HAITOFAUTIKI. Data halisi iko NDANI ya mgawanyo wa surrogate.\n"
              "   Null haionekani kuwa na kasoro — lakini pia data halisi\n"
              "   haionyeshi muundo unaozidi kelele kwa nafasi hii ya kutafuta.\n"
              f"   Kwa surrogate {len(thamani_b)}, kipimo kinaweza kuona tofauti\n"
              f"   kubwa pekee. Ongeza --surrogate-seeds kwa jibu jembamba zaidi.")
        alama = "haitofautiki"
    return _andika(args, tf, bars, halisi, bandia, hukumu, alama, pct)


def _andika(args, tf, bars, halisi, bandia, hukumu, alama, pct):

    out_path = Path(args.out) if args.out else (
        REPO / "research" / "reports" / f"null_vs_real_{args.symbol}_{tf}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "symbol": args.symbol, "timeframe": tf, "n_bars": int(len(bars)),
        "n_candidates": args.candidates, "generator_seed": args.seed,
        "halisi": halisi, "bandia": bandia, "uwiano": hukumu,
        "percentile": pct, "hukumu": alama,
    }, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
