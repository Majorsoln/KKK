"""Je TF ndogo inatoa USHAHIDI zaidi bila gharama kuula? — DOCTRINE §9.1, §8.4, R5.

§9.10 iliisha na namba moja iliyoeleza kila lango tulilogonga:

```
n_trades = 38    kwenye miezi 99
```

Trade moja kila miezi 2.6. Kwa sampuli hiyo, `§8.4.1` inaadhibu vikali
(`t·s/√n`), Sharpe ya miezi ni kelele, na `profitable_month_fraction` ina dari
ya `38/99 = 0.384`. Sakafu haikuwa kali — **ushahidi ulikuwa mwembamba.**

R11 inafunga entry kwenye `bars.decision_tf`, na tumekuwa H1 tangu mwanzo bila
kuuliza. Swali ni: je TF ndogo inaongeza ushahidi kwa kiasi kinachostahili
gharama?

Ni swali la **pande mbili**, na moja peke yake haitoshi:

1. **Ushahidi** — trades ngapi, na miezi mingapi inatradiwa?
2. **Gharama** — je spread inaula faida kwenye mienendo midogo?

TF ndogo inayoongeza trades lakini ikafanya §8.4 ikatae kila mtu haijasaidia.

---

**Kile script hii HAIRIPOTI, na kwa nini.**

Hakuna `select_by`. Hakuna mgombea bora. Hakuna `sharpe`, `net_pips_month`,
wala return yoyote.

R5: generator haifunguki bila Calibration B ya **substrate hiyo**. Hakuna sakafu
ya M15. Kwa hiyo namba yoyote ya utendaji kutoka hapa isingekuwa na maana —
ingekuwa `max` juu ya wagombea bila kizingiti chochote, ndicho hasa §9.1
inachoonya dhidi yake. Kuiripoti kungekuwa kuweka kishawishi mezani.

Kinachoripotiwa ni cha **uwezekano**, si cha utendaji: idadi ya trades, miezi
iliyotradiwa, gharama kwa kila trade, na hukumu ya §8.4.

Na chote ni **wastani (median) juu ya wagombea WOTE**, si kilele. Tatizo la
§9.1 ni tabia ya `max`; median haipandishwi na utafutaji — ni sababu ile ile
iliyofanya `fill_rate` iwe diagnostic halali (§9.5).

---

**Jinsi jibu litakavyosomwa — imeandikwa KABLA ya kuliona (§9.10).**

Masharti **mawili** lazima yatimie:

* trades kwa kila mgombea na **miezi iliyotradiwa** zipande kwa kiasi
  kinachoonekana, NA
* kiwango cha kupita §8.4 kisianguke.

Zikipanda trades lakini §8.4 ikaanguka → gharama imeula ushahidi; TF ndogo si
jibu. Zisipopanda trades → dhana yangu ilikuwa batili. Yote mawili yakitimia →
Calibration B ya TF hiyo inastahili saa zake.

---

**Tahadhari moja ya uaminifu.** Features ni za **idadi ya bars**, si za saa.
`EMA(20)` kwenye M15 ni saa 5, si saa 20. Kwa hiyo DNA ileile kwenye TF mbili
ni **strategy mbili tofauti**. Hii si kulinganisha strategy zilezile kwenye TF
nyingine; ni kuuliza *generator yuleyule anazalisha nini kwenye kila TF.*
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.backtest.engine import BrokerFacts  # noqa: E402
from src.data.bars import TIMEFRAMES, build  # noqa: E402
from src.data.load import discover, iter_months, load_exclusions  # noqa: E402
from src.data.window import declare, research_window  # noqa: E402
from src.discovery import pipeline as P  # noqa: E402
from src.discovery.generator import GeneratorSpec  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import SymbolSpec, pip_size  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from calibrate_a import _root, pip_value_usd  # noqa: E402
from calibrate_b import _hakikisha_chanzo_kimoja  # noqa: E402


def bars_za_TF_zote(inv, symbol, timeframes, stage, *, day_tz, months, pip):
    """Bars za TF zote kwa **kupitia ticks MARA MOJA**.

    `bars_za_dirisha` inasoma ticks kwa kila wito. TF tatu zingesoma GB zilezile
    mara tatu — na muda huo ni wa kusoma diski, si wa kupima chochote.
    """
    import pandas as pd

    vipande = {tf: [] for tf in timeframes}
    n_ticks = 0
    for i, (label, chunk, _report) in enumerate(
        iter_months(inv, symbol, stage, max_spread_pips=None, pip=pip, strict=False)
    ):
        if months and i >= months:
            break
        n_ticks += len(chunk)
        kwa_mwezi = []
        for tf in timeframes:
            bars = build(chunk, tf, stage, day_tz=day_tz).bars
            if len(bars):
                vipande[tf].append(bars)
            kwa_mwezi.append(f"{tf} {len(bars):>5,}")
        print(f"   {symbol} {label}  ticks {len(chunk):>9,}  "
              + " · ".join(kwa_mwezi), flush=True)

    out = {}
    for tf in timeframes:
        if not vipande[tf]:
            raise SystemExit(f"hakuna bars za {symbol} {tf}")
        frame = pd.concat(vipande[tf]).sort_index()
        frame = frame[~frame.index.duplicated(keep="first")]
        frame.attrs["symbol"] = symbol
        out[tf] = frame
    return out, n_ticks


def _q(x, p):
    import numpy as np

    a = np.asarray([v for v in x if v == v], dtype=float)
    return float(np.quantile(a, p)) if a.size else float("nan")


def pima_tf(bars, spec, cfg_risk, seed):
    """Kupitia wagombea wote, kukusanya **uwezekano** pekee."""
    zote: list[dict] = []

    def kwa_kila(_record, _strategy, result, eco, sababu):
        kwa_mwezi = result.monthly()
        zilizotradiwa = int((kwa_mwezi["n_trades"] > 0).sum()) if len(kwa_mwezi) else 0
        n_miezi = int(len(kwa_mwezi))
        zote.append({
            "n_trades": float(result.n_trades),
            "miezi_zilizotradiwa": float(zilizotradiwa),
            "n_months": float(n_miezi),
            "dari_pmf": (zilizotradiwa / n_miezi) if n_miezi else float("nan"),
            "fill_rate": float(result.ledger.fill_rate),
            "gross_edge_pips": float(eco.gross_edge_pips),
            "live_cost_pips": float(eco.live_sizing_cost_pips),
            "ratio_lower": float(eco.ratio_lower),
            "sababu": sababu or "SAWA",
        })

    out = P.search(bars, spec, cfg_risk=cfg_risk, seed=seed, on_result=kwa_kila)
    return zote, out.by_reason, out.variants_tested


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbol", default="GBPUSD")
    ap.add_argument("--tf", nargs="+", default=["H1", "M30", "M15"])
    ap.add_argument("--candidates", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--months", type=int, default=0, help="0 = zote")
    ap.add_argument("--max-conditions", type=int, default=4)
    ap.add_argument("--hour-tz", default="UTC")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pip-value", nargs="*", default=[], metavar="SYM=VAL")
    args = ap.parse_args()

    mbaya = [t for t in args.tf if t not in TIMEFRAMES]
    if mbaya:
        raise SystemExit(f"TF hazijulikani: {mbaya} — zinazoruhusiwa {TIMEFRAMES}")

    root = _root(args.root)
    cfg_data = load_config(REPO / "config" / "data.yaml")
    cfg_risk = load_config(REPO / "config" / "risk.yaml")
    cfg_broker = load_config(REPO / "config" / "broker_costs.yaml")

    day_tz = str(cfg_data.get("timezone.day_reset_tz"))
    window = research_window(cfg_data)
    stage = declare("tf_probe", "DOCTRINE §9.1 — ushahidi dhidi ya gharama",
                    window, cfg=cfg_data)

    print(f"dirisha: {window.start} → {window.end} (HOLDOUT haiguswi, §16)")
    print(f"symbol {args.symbol} · TF {' '.join(args.tf)} · "
          f"wagombea {args.candidates:,} · seed {args.seed}")
    print(f"decision_tf ya config ni {cfg_data.get('bars.decision_tf')} (R11) — "
          f"hii ni KIPIMO, si utafutaji.\n")

    inv = discover(root, provenance=args.provenance,
                   exclusions=load_exclusions(cfg_data))
    _hakikisha_chanzo_kimoja(inv, args.symbol, window)
    if not inv.of(args.symbol):
        raise SystemExit(f"hakuna data ya {args.symbol} kwenye {root}")

    pip = pip_size(args.symbol)
    contracts = cfg_broker.get("contract_size", {"default": 100_000})
    commissions = cfg_broker.get("commission_usd_round_turn", {"default": 7.0})
    contract = float(contracts.get(args.symbol, contracts.get("default", 100_000)))
    if not bool(cfg_broker.get("contract_size_confirmed", False)):
        print("   ONYO: `contract_size_confirmed: false` — `pip_value` "
              "inategemea namba isiyothibitishwa kwa MT5.\n")

    kwa_mkono = dict(piece.split("=", 1) for piece in args.pip_value)
    if args.symbol in kwa_mkono:
        pipval, njia = float(kwa_mkono[args.symbol]), "--pip-value"
    else:
        pipval, njia = pip_value_usd(args.symbol, contract, inv)
    if pipval is None:
        raise SystemExit(njia)

    print("Kujenga bars (ticks zinasomwa MARA MOJA kwa TF zote)…", flush=True)
    t0 = time.time()
    kwa_tf, n_ticks = bars_za_TF_zote(inv, args.symbol, args.tf, stage,
                                      day_tz=day_tz, months=args.months, pip=pip)
    print(f"   ticks {n_ticks:,} · {time.time() - t0:.0f}s")
    for tf in args.tf:
        print(f"      {tf:<4} bars {len(kwa_tf[tf]):>8,}")
    print()

    matokeo: dict[str, dict] = {}
    for tf in args.tf:
        spec = P.PipelineSpec(
            symbol=args.symbol, timeframe=tf,
            broker=BrokerFacts(
                spec=SymbolSpec(symbol=args.symbol, point=pip / 10.0,
                                contract_size=contract, volume_min=0.01,
                                volume_step=0.01, volume_max=50.0),
                pip_value_acct=pipval,
                commission_round_turn=float(
                    commissions.get(args.symbol,
                                    commissions.get("default", 7.0))),
            ),
            generator=GeneratorSpec(symbols=(args.symbol,),
                                    max_conditions=args.max_conditions),
            n_candidates=args.candidates,
            hour_tz=args.hour_tz, day_tz=day_tz,
        )
        t0 = time.time()
        zote, kwa_sababu, variants = pima_tf(kwa_tf[tf], spec, cfg_risk, args.seed)
        matokeo[tf] = {"zote": zote, "by_reason": kwa_sababu,
                       "variants_tested": variants, "muda": time.time() - t0,
                       "n_bars": int(len(kwa_tf[tf]))}
        print(f"   {tf:<4} waliofanyiwa backtest {len(zote):>4} · "
              f"{matokeo[tf]['muda']:>5.0f}s", flush=True)

    # ---------------- ripoti ----------------
    print("\n" + "=" * 72)
    print("USHAHIDI — wastani juu ya wagombea WOTE (si kilele; §9.1 ni tabia "
          "ya `max`)")
    print("=" * 72)
    print(f"   {'TF':<5} {'bars':>9} {'trades p10':>11} {'kati':>7} {'p90':>7}"
          f" {'miezi/jumla':>12} {'dari pmf':>9}")
    for tf in args.tf:
        z = matokeo[tf]["zote"]
        trades = [r["n_trades"] for r in z]
        miezi = [r["miezi_zilizotradiwa"] for r in z]
        jumla = _q([r["n_months"] for r in z], 0.5)
        print(f"   {tf:<5} {matokeo[tf]['n_bars']:>9,} {_q(trades, 0.10):>11.0f} "
              f"{_q(trades, 0.5):>7.0f} {_q(trades, 0.90):>7.0f} "
              f"{_q(miezi, 0.5):>6.0f}/{jumla:<5.0f} "
              f"{_q([r['dari_pmf'] for r in z], 0.5):>9.4f}")

    print("\n" + "=" * 72)
    print("GHARAMA — §8.4, na hukumu yake")
    print("=" * 72)
    print(f"   {'TF':<5} {'edge pips':>10} {'live cost':>10} {'ratio_lower':>12}"
          f" {'fill_rate':>10}")
    for tf in args.tf:
        z = matokeo[tf]["zote"]
        print(f"   {tf:<5} {_q([r['gross_edge_pips'] for r in z], 0.5):>10.3f} "
              f"{_q([r['live_cost_pips'] for r in z], 0.5):>10.3f} "
              f"{_q([r['ratio_lower'] for r in z], 0.5):>12.3f} "
              f"{_q([r['fill_rate'] for r in z], 0.5):>10.4f}")

    print(f"\n   hukumu ya §8.4 (kati ya wagombea {args.candidates:,}):")
    sababu_zote = sorted({s for tf in args.tf
                          for s in matokeo[tf]["by_reason"]})
    print(f"      {'sababu':<24}" + "".join(f"{tf:>12}" for tf in args.tf))
    for s in sababu_zote:
        # Denominator ni wagombea WALIOZALISHWA, si `variants_tested`: kila
        # mgombea anapata sababu MOJA, kwa hiyo safu hizi zinajumlika 100%.
        # `variants_tested` inatoa `DUPLICATE`, na ingevunja jumla hiyo.
        safu = "".join(
            f"{matokeo[tf]['by_reason'].get(s, 0):>7,}"
            f"{matokeo[tf]['by_reason'].get(s, 0) / max(1, args.candidates):>5.0%}"
            for tf in args.tf)
        print(f"      {s:<24}{safu}")

    out_path = Path(args.out) if args.out else (
        REPO / "research" / "reports" / f"tf_probe_{args.symbol}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "window": {"start": str(window.start), "end": str(window.end)},
        "symbol": args.symbol, "seed": args.seed,
        "n_candidates": args.candidates, "n_ticks": int(n_ticks),
        "hour_tz": args.hour_tz, "max_conditions": args.max_conditions,
        "per_tf": {tf: {k: v for k, v in matokeo[tf].items() if k != "zote"}
                   | {"candidates": matokeo[tf]["zote"]} for tf in args.tf},
    }, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {out_path}")

    print("\nR5: hakuna sakafu ya TF hizi isipokuwa iliyopo. Namba zilizo hapo "
          "juu\n"
          "    ni za UWEZEKANO, si za utendaji — hakuna mgombea hapa "
          "aliyegunduliwa,\n"
          "    na hakuna anayeweza kuwa hadi Calibration B ya substrate hiyo "
          "iendeshwe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
