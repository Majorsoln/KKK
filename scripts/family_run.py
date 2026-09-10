"""Endesha familia moja kwenye ticks halisi — DOCTRINE §4, §6, §7, §9.

```
python scripts/family_run.py --family gotobi --root <L0> --provenance aggregator
python scripts/family_run.py --family f0     --dry-run
```

Kila kitu cha maana kiko `src/backtest/driver.py`; hapa ni kuchagua familia,
kuchapisha, na kuandika ripoti. **Lango la §6 linaamuliwa na kutangazwa kabla
`p` haijahesabiwa**, na likishindwa hii inasimama bila kuihesabu.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analysis import bootstrap as BS                       # noqa: E402
from src.backtest import driver as D                           # noqa: E402
from src.data import ticks as TK                               # noqa: E402
from src.data import indices as IX                             # noqa: E402
from src.families import f0, f1, gotobi                        # noqa: E402
from src.families import f1_signal as SIG                      # noqa: E402
from src.rce.config import load_config                         # noqa: E402

FAMILIES = {"f0": f0, "gotobi": gotobi, "f1": f1}
RIPOTI = REPO / "research" / "reports"

# §9: majaribio 8 kwenye α = 0.020 → 0.0025.
KIZINGITI = 0.0025


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=sorted(FAMILIES))
    ap.add_argument("--root", default=None)
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--balance", type=float, default=10_000.0)
    ap.add_argument("--commission", type=float, default=7.0)
    ap.add_argument("--edge-pips", type=float, default=None,
                    help="edge iliyotangazwa (§9); chaguo-msingi ni ya familia")
    ap.add_argument("--B", type=int, default=BS.B_DEVELOPMENT)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--indices", default=None,
                    help="folda ya faharasa (F1 pekee)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    fam = FAMILIES[args.family]
    edge = args.edge_pips if args.edge_pips is not None else fam.DECLARED_EDGE_PIPS
    root = args.root or os.path.join(
        os.environ.get("ELITEFX_RESEARCH_ROOT", str(REPO / "research")),
        "data", "L0_raw")

    anza, mwisho = date.fromisoformat(args.start), date.fromisoformat(args.end)
    zote, d = [], anza
    while d <= mwisho:
        zote.append(d)
        d += timedelta(days=1)
    siku = fam.eligible_days(zote)
    n_legs = len(fam.measurements(siku[0])) if siku else 0

    print(f"{fam.FAMILY} — {'/'.join(fam.DECLARATION.symbols)}")
    print(fam.DECLARATION.render())
    print(f"\n   dirisha {anza} → {mwisho} · siku zinazostahili {len(siku):,} "
          f"· legs {n_legs} kwa siku · matukio {n_legs * len(siku):,}")
    print(f"   edge iliyotangazwa {edge} pips · kizingiti p ≤ {KIZINGITI}")

    zote_symbols = list(getattr(fam, "SYMBOLS", (getattr(fam, "SYMBOL", ""),)))
    inv = TK.discover(root, symbols=zote_symbols, provenance=args.provenance)
    print("\n" + inv.render())
    if args.dry_run:
        print("\n--dry-run: hakuna tick iliyosomwa.")
        return 0
    if not siku:
        print("\nHAKUNA SIKU INAYOSTAHILI kwenye dirisha hili.")
        return 2

    # ---- ishara ya F1 ----
    ziada = {}
    if fam is f1:
        folda = Path(args.indices) if args.indices else (
            REPO / "research" / "data" / "indices")
        inahitajika = {SIG.INDEX_FOR[s] for s in f1.QUALIFIED}
        try:
            series = IX.load({j: folda / f"{j}.csv" for j in inahitajika})
        except IX.IndexError_ as exc:
            print(f"\nISHARA HAIPO: {exc}\n   Endesha "
                  f"`python scripts/fetch_indices.py` kwanza (§4 ya f1.py: "
                  f"F1 haiwezi kuendeshwa bila ishara ya hisa).")
            return 2
        ishara = SIG.signals(siku, series)
        print(f"\n   ishara kamili: {len(ishara)}/{len(siku)} "
              f"({len(ishara) / max(1, len(siku)):.0%})")
        if not ishara:
            print("   HAKUNA ISHARA HATA MOJA.")
            return 2
        ziada["signal"] = lambda d: ishara.get(d)

    spec = D.RunSpec(balance=args.balance, commission_round_turn=args.commission)
    print(f"\n   kusoma vipande {len(D.chunks(siku)):,}…\n", flush=True)
    sw = D.sweep(fam, inv, siku, spec,
                 cfg=load_config(REPO / "config" / "risk.yaml"),
                 progress=print if args.verbose else None, **ziada)

    print(f"\n   trades {len(sw.trades):,} · muda {sw.seconds:.0f}s")
    if sw.missing:
        print(f"   madirisha bila tick: {len(sw.missing):,} "
              f"({len(sw.missing) / max(1, n_legs * len(siku)):.1%})")
        for d, leg, sababu in sw.missing[:3]:
            print(f"      {d} {leg}: {sababu}")
    if sw.rejected:
        print(f"   vikapu vilivyokataliwa na RCE: {len(sw.rejected):,}")
        for d, leg, sababu in sw.rejected[:3]:
            print(f"      {d} {leg}: {sababu}")
    if not sw.trades:
        print("\nHAKUNA TRADE. Angalia `--root` na `--provenance`.")
        return 2

    mz = D.measure(fam, sw, siku)
    print("\n" + "=" * 74)
    print("VIPIMO")
    print("=" * 74)
    print(f"   {'leg':<5} {'trades':>7} {'mwendo':>8} {'σ':>8} {'σ norm':>8} "
          f"{'gharama':>8} {'gh/σ':>7} {'gh/σn':>7}")
    for leg, v in sorted(mz.per_leg.items()):
        alama = "  ←" if leg == mz.worst_leg else ""
        print(f"   {leg:<5} {v['n']:>7,} {v['move_pips']:>8.2f} "
              f"{v['sigma_pips']:>8.2f} {v['sigma_normal_pips']:>8.2f} "
              f"{v['cost_pips']:>8.2f} {v['ratio']:>6.1%} "
              f"{v['ratio_normal']:>6.1%}{alama}")
    # §13.10: `σ` inapimwa. `σ norm` ni ile ya dhana ya normal, inachapishwa
    # ili tofauti ionekane. Uwiano > 1.0 = mikia minene kuliko normal.
    mbaya = mz.per_leg[mz.worst_leg]
    print(f"   σ iliyopimwa ÷ σ ya normal = {mbaya['kurtosis_hint']:.3f} "
          f"kwa leg mbaya · drift {mbaya['drift_pips']:+.2f}p")
    sl = fam.SL_MOVE_MULT * mz.move_pips
    print(f"   stop (× {fam.SL_MOVE_MULT}) kwa leg mbaya          {sl:>8.2f} pips")
    print(f"   pengo la spread (zilizomaliza kwa saa): "
          f"wastani {sum(mz.gap) / len(mz.gap):+.3f}p · "
          f"p50 {mz.gap[len(mz.gap) // 2]:+.3f}p · "
          f"p95 {mz.gap[int(0.95 * len(mz.gap))]:+.3f}p")
    print(f"   siku hai {mz.curve.n_active:,}/{mz.curve.n:,}")

    kiwango = len(sw.stopped) / len(sw.trades)
    print(f"\n   STOP ILIGONGWA: {len(sw.stopped):,}/{len(sw.trades):,} "
          f"({kiwango:.2%})")
    if sw.stopped:
        mae = sorted(t.mae_pips for t in sw.trades)
        kwa_mwaka: dict[int, int] = {}
        for t in sw.stopped:
            kwa_mwaka[t.entry_at.year] = kwa_mwaka.get(t.entry_at.year, 0) + 1
        print(f"      MAE p50 {mae[len(mae) // 2]:.1f}p · "
              f"p95 {mae[int(0.95 * len(mae))]:.1f}p · kubwa {mae[-1]:.1f}p")
        print("      kwa mwaka: " + " · ".join(
            f"{y} {n}" for y, n in sorted(kwa_mwaka.items())))
    assert all(t.path_modelled for t in sw.trades), "njia haikupimwa!"

    q, s = D.gate(fam, mz, edge_pips=edge, n_legs=max(1, n_legs))
    print("\n" + "=" * 74)
    print("LANGO LA §6 — linaamuliwa KABLA ya `p`")
    print("=" * 74)
    print(q.render())

    matokeo = {
        "family": fam.FAMILY, "symbols": list(fam.DECLARATION.symbols),
        "declaration": fam.DECLARATION.to_json(),
        "window": {"start": args.start, "end": args.end,
                   "eligible_days": len(siku), "legs_per_day": n_legs,
                   "trades": len(sw.trades)},
        "measured": {"worst_leg": mz.worst_leg, "per_leg": mz.per_leg,
                     "sl_pips": sl, "declared_edge_pips": edge,
                     "spread_gap_mean": sum(mz.gap) / len(mz.gap),
                     "spread_gap_p95": mz.gap[int(0.95 * len(mz.gap))],
                     "n_days": mz.curve.n, "n_active": mz.curve.n_active,
                     "sharpe_per_day_declared": s,
                     "stopped": len(sw.stopped), "stop_rate": kiwango,
                     "path_modelled": True},
        "qualification": q.to_json(),
    }

    if not q.passed:
        print(f"\n{fam.FAMILY} HAIINGII. `p` haihesabiwi — "
              f"symbol iliyokataliwa\n   haiingii kwenye hesabu ya majaribio "
              f"wala kwenye pooling (§6).")
        _andika(args, fam, matokeo)
        return 3

    # `PLACEHOLDER` ni ya lango pekee (§4 ya f1.py). Trade yoyote
    # iliyoizalishwa haiwezi kuzalisha `p`.
    if fam is f1 and any(getattr(ziada.get("signal")(d), "placeholder", False)
                         for d in siku if ziada.get("signal")
                         and ziada["signal"](d) is not None):
        print("\nISHARA NI `PLACEHOLDER` — `p` haihesabiwi.")
        _andika(args, fam, matokeo)
        return 2

    r = BS.test_mean_positive(mz.curve, B=args.B, seed=args.seed)
    print("\n" + "=" * 74)
    print("JIBU")
    print("=" * 74)
    print("   " + r.render())
    print(f"   kizingiti cha §9 (majaribio 8, α 0.020): p ≤ {KIZINGITI}")
    matokeo["result"] = {"p_value": r.p_value, "mean": r.mean,
                         "ci_low": r.ci_low, "ci_high": r.ci_high,
                         "block": r.block, "B": args.B}
    _andika(args, fam, matokeo)

    hukumu = "IMENUSURIKA" if r.p_value <= KIZINGITI else "HAIJANUSURIKA"
    print(f"\n{fam.FAMILY} {hukumu} kizingiti cha mzunguko wa kwanza.")
    return 0 if r.p_value <= KIZINGITI else 1


def _andika(args, fam, matokeo) -> None:
    path = Path(args.out) if args.out else (
        RIPOTI / f"{fam.FAMILY.lower()}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matokeo, indent=2, default=str) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
