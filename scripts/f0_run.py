"""Endesha F0 kwenye ticks halisi — DOCTRINE §4, §6, §7, §9.

```
diski → madirisha (dakika 20/siku) → mwendo → stop → RCE → trades
      → LANGO LA §6 → curve ya siku → block bootstrap → `p`
```

**Mpangilio si wa bahati.** Malango ya §6 yanapimwa na kutangazwa **kabla**
`p` haijahesabiwa, na yakishindwa script inasimama bila kuhesabu `p` kabisa.
Kuona `p` kisha kuamua kama symbol inastahili ni jinsi toleo la kwanza
lilivyoshindwa.

---

**Kusoma.** Dirisha ZIMA la kushikilia linasomwa (§11, uamuzi wa PD
2026-09-09): `runner.execute` inahitaji njia ili kujua kama stop iligongwa.
Kipande cha siku tano kinasomwa, kinatumika, kinatupwa — kwa hiyo kumbukumbu
inabaki chini ya rows milioni 2.5 hata kwa miaka minane.

**Stop haina lookahead.** Mwendo wa siku unaingia kwenye historia **baada**
ya kikapu cha siku hiyo kujengwa.

**Kugongwa kwa stop kunaripotiwa kwa kila trade**, si kwa sampuli. Toleo la
kwanza lilikuwa na `--angalia-stop` iliyopima sampuli kwa code yake yenyewe —
na code hiyo ndiyo iliyokuwa na kasoro ya upande (bid kwa SELL badala ya ask).
Sasa kuna njia MOJA: `runner.excursion`, inayotumiwa na kila trade.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analysis import bootstrap as BS                       # noqa: E402
from src.analysis.curve import daily_r                         # noqa: E402
from src.backtest.runner import execute                        # noqa: E402
from src.data import ticks as TK                               # noqa: E402
from src.events.clock import quotes                            # noqa: E402
from src.families import f0                                    # noqa: E402
from src.families.qualify import qualify                       # noqa: E402
from src.rce.budget import AccountState                        # noqa: E402
from src.rce.config import load_config                         # noqa: E402
from src.rce.cost import SymbolSpec                            # noqa: E402

RIPOTI = REPO / "research" / "reports"
PIP = 0.0001


# ===========================================================================
# Muktadha wa soko
# ===========================================================================


def market(args, spread_pips: float) -> dict:
    """Kila kitu RCE inachohitaji kwa EURUSD.

    `h1_spreads`/`m5_spreads` ni kadirio la RCE la gharama, si iliyolipwa.
    Tofauti kati yao na spread ya ticks ndiyo `spread_gap_pips` — namba
    inayoamua kama RCE v2 inahitajika (Lango 3).
    """
    return {
        "spec": SymbolSpec(symbol=f0.SYMBOL, point=0.00001,
                           contract_size=args.contract_size,
                           volume_min=0.01, volume_step=0.01, volume_max=50.0),
        "account": AccountState(current_balance=args.balance, today_profit=0.0,
                                today_loss=0.0, open_positions=0),
        "h1_spreads": [spread_pips] * 120,
        "m5_spreads": [spread_pips] * 300,
        "pip_value_acct": args.pip_value,
        "commission_round_turn": args.commission,
        "pip": PIP,
    }


def vipande(siku, *, kwa_kipande: int = 5):
    """Siku zilizopangwa kwa vipande vidogo, kwa mpangilio.

    Toleo la kwanza lilipanga kwa MWEZI. Sasa tunasoma **dirisha zima** la
    kushikilia (masaa 13.4 kwa siku badala ya dakika 20), kwa hiyo mwezi
    mmoja ungekuwa rows milioni 10+. Kipande cha siku tano kinabaki chini
    ya milioni 2.5, na **hakuna faili inayosomwa mara mbili** — kila siku iko
    kwenye kipande kimoja tu.
    """
    return [list(siku[i:i + kwa_kipande])
            for i in range(0, len(siku), kwa_kipande)]


# ===========================================================================
# Kupitia data
# ===========================================================================


def sweep(inv, siku, args, *, cfg, verbose=False):
    """Pita vipande vyote: quotes → mwendo → stop → kikapu → trade.

    **Dirisha zima linasomwa**, si ncha pekee: `runner.execute` inahitaji njia
    ili kujua kama stop iligongwa (§11, uamuzi wa PD 2026-09-09). Bila hiyo,
    trade iliyogusa stop kisha ikapona inarekodiwa kama iliyomalizika kwa saa,
    na upendeleo unaotokana nayo ni mkubwa kuliko athari tunayoipima.

    Inarudisha `(trades, mwendo, zilizokosekana, zilizokataliwa)`.
    """
    partitions = inv.of(f0.SYMBOL)
    trades, mwendo = [], {}
    historia: dict[str, list[float]] = {}
    kukosekana, kukataliwa = [], []

    for kundi in vipande(siku):
        maombi = []
        for d in kundi:
            for s in f0.sessions_for(d):
                # Kuingia → kutoka + dirisha la kutoka, ikiwa ombi MOJA.
                urefu = int((s.exit_at - s.entry_at).total_seconds())
                maombi.append((s.entry_at, urefu + f0.WINDOW_SECONDS))
        frame = TK.read_windows(inv, f0.SYMBOL, maombi, partitions=partitions)

        for d in kundi:
            for s in f0.sessions_for(d):
                try:
                    ndani = quotes(frame, s.entry_at, f0.WINDOW_SECONDS)
                    nje = quotes(frame, s.exit_at, f0.WINDOW_SECONDS)
                except Exception as exc:                       # noqa: BLE001
                    kukosekana.append((d, s.leg, str(exc)[:80]))
                    continue

                # Stop ya leo inatoka kwenye historia ya JANA. Inasomwa kabla
                # ya mwendo wa leo kuongezwa — hapo ndipo lookahead ingeingia.
                nyuma = historia.setdefault(s.leg, [])
                m = f0.stop_from_history(nyuma)
                if m is not None:
                    kikapu = f0.baskets([d], move_pips={(d, s.leg): m})
                    if kikapu:
                        soko = {f0.SYMBOL: market(args, ndani.spread_pips(PIP))}
                        out = execute(kikapu[0], cfg=cfg,
                                      ticks_by_symbol={f0.SYMBOL: frame},
                                      market=soko,
                                      window_seconds=f0.WINDOW_SECONDS,
                                      path_ticks={f0.SYMBOL: frame})
                        if out.executed:
                            trades.extend(out.trades)
                        else:
                            kukataliwa.append((d, s.leg, out.reason))

                kiasi = f0.session_move_pips(ndani, nje, pip=PIP)
                mwendo[(d, s.leg)] = kiasi
                nyuma.append(kiasi)

        if verbose:
            kufa = sum(1 for t in trades if t.stopped)
            print(f"   {kundi[0]:%Y-%m-%d}  siku {len(kundi):>2}  "
                  f"trades {len(trades):>5,}  stop {kufa:>4,}", flush=True)
    return trades, mwendo, kukosekana, kukataliwa


# ===========================================================================
# Ripoti
# ===========================================================================


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None,
                    help="L0 root (chaguo-msingi: $ELITEFX_RESEARCH_ROOT/data/L0_raw)")
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--balance", type=float, default=10_000.0)
    ap.add_argument("--pip-value", type=float, default=10.0)
    ap.add_argument("--commission", type=float, default=7.0)
    ap.add_argument("--contract-size", type=float, default=100_000.0)
    ap.add_argument("--edge-pips", type=float, default=3.4,
                    help="edge iliyotangazwa kwa leg (§9) — kwa lango la 6.3")
    ap.add_argument("--B", type=int, default=BS.B_DEVELOPMENT)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    import os
    root = args.root or os.path.join(
        os.environ.get("ELITEFX_RESEARCH_ROOT", str(REPO / "research")),
        "data", "L0_raw")

    anza = date.fromisoformat(args.start)
    mwisho = date.fromisoformat(args.end)
    zote, d = [], anza
    while d <= mwisho:
        zote.append(d)
        d += timedelta(days=1)
    siku = f0.eligible_days(zote)

    print("F0 — mtiririko wa saa za nchi")
    print(f0.DECLARATION.render())
    print(f"\n   dirisha {anza} → {mwisho} · siku zinazostahili {len(siku):,} "
          f"· legs {2 * len(siku):,}")

    inv = TK.discover(root, symbols=[f0.SYMBOL], provenance=args.provenance)
    print("\n" + inv.render())

    if args.dry_run:
        print("\n--dry-run: hakuna tick iliyosomwa.")
        return 0

    t0 = time.time()
    print(f"\n   kusoma madirisha {4 * len(siku):,} "
          f"(dakika {20 * len(siku) / 60:,.0f} kati ya "
          f"{1440 * len(siku) / 60:,.0f})…\n", flush=True)
    trades, mwendo, kukosekana, kukataliwa = sweep(
        inv, siku, args, cfg=load_config(REPO / "config" / "risk.yaml"),
        verbose=args.verbose)
    print(f"\n   trades {len(trades):,} · muda {time.time() - t0:.0f}s")
    if kukosekana:
        print(f"   madirisha bila tick: {len(kukosekana):,} "
              f"({len(kukosekana) / (2 * len(siku)):.1%})")
        for d, leg, sababu in kukosekana[:3]:
            print(f"      {d} {leg}: {sababu}")
    if kukataliwa:
        print(f"   vikapu vilivyokataliwa na RCE: {len(kukataliwa):,}")
        for d, leg, sababu in kukataliwa[:3]:
            print(f"      {d} {leg}: {sababu}")
    if not trades:
        print("\nHAKUNA TRADE. Angalia `--root` na `--provenance`.")
        return 2

    # ---- vipimo ----
    import statistics as st

    # Trade iliyogongwa stop haikutumia dirisha la kutoka, kwa hiyo haina
    # spread ya kwenda-na-kurudi. Vipimo vya gharama vinapimwa kwa
    # zilizomaliza kwa saa PEKEE; kugongwa kunaripotiwa kando.
    zilizomaliza = [t for t in trades if not t.stopped]
    zilizogongwa = [t for t in trades if t.stopped]
    pengo = sorted(t.spread_gap_pips for t in zilizomaliza)
    curve = daily_r(trades, days=siku)

    # Kwa KILA leg peke yake. Leg A ni masaa 9, leg B ni 4.4 — `σ` yao si moja,
    # kwa hiyo uwiano wa gharama si mmoja. Kuchanganya kungefanya leg fupi
    # ijifiche nyuma ya ndefu, na §6.2 inasema "σ ya dirisha la kushikilia",
    # si "σ ya wastani wa familia".
    kwa_leg = {}
    for leg in (f0.LEG_A, f0.LEG_B):
        m = [v for (_, l), v in mwendo.items() if l == leg]
        t_leg = [t for t in zilizomaliza if t.basket_id.endswith(f":{leg}")]
        if not m or not t_leg:
            continue
        wastani = st.fmean(m)
        kwa_leg[leg] = {
            "move_pips": wastani,
            "sigma_pips": wastani * f0.MOVE_TO_SIGMA,
            "cost_pips": st.fmean(t.spread_realised_pips + t.commission_pips
                                  for t in t_leg),
            "n": len(t_leg),
        }
        kwa_leg[leg]["ratio"] = (kwa_leg[leg]["cost_pips"]
                                 / kwa_leg[leg]["sigma_pips"])

    # Lango linapimwa kwa leg MBAYA kabisa. Familia ni yote-au-hakuna.
    mbaya = max(kwa_leg, key=lambda k: kwa_leg[k]["ratio"])
    wastani_mwendo = kwa_leg[mbaya]["move_pips"]
    sigma_dirisha = kwa_leg[mbaya]["sigma_pips"]
    gharama = kwa_leg[mbaya]["cost_pips"]

    # Sharpe-kwa-siku ILIYOTANGAZWA — inatokana na edge ya §9 na volatility
    # ILIYOPIMWA, si kwenye faida iliyopatikana. Ikiwa ingetoka kwenye faida,
    # lango la 6.3 lingekuwa likijipima lenyewe.
    sl = f0.SL_MOVE_MULT * wastani_mwendo
    edge_R_leg = args.edge_pips / (sl + gharama)
    sigma_R_leg = sigma_dirisha / (sl + gharama)
    s_siku = (2 * edge_R_leg) / (sigma_R_leg * (2 ** 0.5))

    print("\n" + "=" * 74)
    print("VIPIMO")
    print("=" * 74)
    print(f"   {'leg':<5} {'trades':>7} {'mwendo':>8} {'σ':>8} {'gharama':>8} "
          f"{'gharama/σ':>10}")
    for leg, v in sorted(kwa_leg.items()):
        alama = "  ← inayopimwa" if leg == mbaya else ""
        print(f"   {leg:<5} {v['n']:>7,} {v['move_pips']:>8.2f} "
              f"{v['sigma_pips']:>8.2f} {v['cost_pips']:>8.2f} "
              f"{v['ratio']:>9.1%}{alama}")
    print(f"   stop (× {f0.SL_MOVE_MULT}) kwa leg mbaya          {sl:>8.2f} pips")
    print(f"   pengo la spread (RCE dhidi ya ticks, zilizomaliza kwa saa): "
          f"wastani {st.fmean(pengo):+.3f}p · "
          f"p50 {pengo[len(pengo) // 2]:+.3f}p · "
          f"p95 {pengo[int(0.95 * len(pengo))]:+.3f}p")
    print(f"   siku hai {curve.n_active:,}/{curve.n:,}")

    # Kugongwa kwa stop — dhana iliyokuwa ikidhaniwa, sasa inapimwa kwa KILA
    # trade. Kila moja ni −1R hasa (§11).
    kiwango = len(zilizogongwa) / len(trades)
    print(f"\n   STOP ILIGONGWA: {len(zilizogongwa):,}/{len(trades):,} "
          f"({kiwango:.2%})")
    if zilizogongwa:
        mae = sorted(t.mae_pips for t in trades)
        print(f"      MAE p50 {mae[len(mae) // 2]:.1f}p · "
              f"p95 {mae[int(0.95 * len(mae))]:.1f}p · "
              f"kubwa {mae[-1]:.1f}p")
        kwa_mwaka = {}
        for t in zilizogongwa:
            kwa_mwaka[t.entry_at.year] = kwa_mwaka.get(t.entry_at.year, 0) + 1
        print("      kwa mwaka: " + " · ".join(
            f"{y} {n}" for y, n in sorted(kwa_mwaka.items())))
    assert all(t.path_modelled for t in trades), "njia haikupimwa!"

    # ---- LANGO LA §6, kabla ya `p` ----
    q = qualify(
        f0.FAMILY, f0.SYMBOL,
        mechanism_ok=True, mechanism_note=f0.DECLARATION.source,
        cost_pips=gharama, sigma_pips=sigma_dirisha,
        n_events=curve.n_active, sharpe_per_event=s_siku,
    )
    print("\n" + "=" * 74)
    print("LANGO LA §6 — linaamuliwa KABLA ya `p`")
    print("=" * 74)
    print(q.render())

    matokeo = {
        "family": f0.FAMILY, "symbol": f0.SYMBOL,
        "declaration": f0.DECLARATION.to_json(),
        "window": {"start": args.start, "end": args.end,
                   "eligible_days": len(siku), "trades": len(trades)},
        "measured": {"worst_leg": mbaya, "per_leg": kwa_leg,
                     "move_pips": wastani_mwendo, "sigma_pips": sigma_dirisha,
                     "sl_pips": sl, "cost_pips": gharama,
                     "spread_gap_mean": st.fmean(pengo),
                     "spread_gap_p95": pengo[int(0.95 * len(pengo))],
                     "n_days": curve.n, "n_active": curve.n_active,
                     "sharpe_per_day_declared": s_siku,
                     "stopped": len(zilizogongwa), "stop_rate": kiwango,
                     "path_modelled": True},
        "qualification": q.to_json(),
    }

    if not q.passed:
        print("\nF0 × EURUSD HAIINGII. `p` haihesabiwi — symbol iliyokataliwa\n"
              "   haiingii kwenye hesabu ya majaribio wala kwenye pooling (§6).")
        _andika(args, matokeo)
        return 3

    # ---- `p`, sasa tu ----
    r = BS.test_mean_positive(curve, B=args.B, seed=args.seed)
    print("\n" + "=" * 74)
    print("JIBU")
    print("=" * 74)
    print("   " + r.render())
    print(f"   kizingiti cha §9 (majaribio 8, α 0.020): p ≤ 0.0025")
    matokeo["result"] = r.to_json() if hasattr(r, "to_json") else {
        "p_value": r.p_value, "mean": r.mean,
        "ci_low": r.ci_low, "ci_high": r.ci_high, "block": r.block}

    _andika(args, matokeo)
    hukumu = "IMENUSURIKA" if r.p_value <= 0.0025 else "HAIJANUSURIKA"
    print(f"\nF0 {hukumu} kizingiti cha mzunguko wa kwanza.")
    return 0 if r.p_value <= 0.0025 else 1


def _andika(args, matokeo) -> None:
    path = Path(args.out) if args.out else (RIPOTI / "f0.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matokeo, indent=2, default=str) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
