"""HATUA 2 — KUTAFUTA (DOCTRINE §3, §10, §11, §8.4, §9.2, R5, S1).

```
bars halisi → features → generator → backtest → §8.4 → SAKAFU YA §9 → walionusurika
```

Ni `search()` ILE ILE iliyopima sakafu (`discovery/pipeline.py`), ikiendeshwa
juu ya data **halisi** badala ya bandia. Hilo si urahisi; ni sharti la §9.4:
sakafu inahukumu utafutaji ule ule uliopimwa, si mwingine unaofanana nao.

---

**R5 ni lango, si ukaguzi.**

Script hii inaita `open_generator()` — ambayo inalipuka ikiwa Calibration A au B
haipo. Hakuna njia ya kuzalisha candidate hapa bila jedwali la sakafu mkononi,
kwa sababu jedwali hilo ndilo linalorudishwa na mlango wenyewe.

---

**Hakuna screening ya hatua (§12), kwa makusudi.**

§12 inapendekeza madirisha A/B/C/D ili kupunguza gharama. Lakini sakafu yako
ilipimwa kwa `search()` inayoendesha dirisha **zima**, na §9.4 inadai substrate
ile ile. Screening ingebadilisha mchakato unaozalisha "bora", na ulinganisho
ungevunjika **kimya**.

Kwa `K` ya maelfu, gharama ni dakika — screening haihitajiki. Ikifika mahali
inahitajika, **Calibration B itabidi ipimwe upya nayo**, si kuongezwa hapa
peke yake.

---

**Dirisha ni la utafiti pekee.** `research_window` inaishia kabla ya HOLDOUT
(§16), na `declare()` inakagua hilo — si nidhamu, ni assertion (R18).
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
from src.discovery import survivors as SV  # noqa: E402
from src.discovery.generator import GeneratorSpec, open_generator  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import SymbolSpec, pip_size  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from calibrate_a import _root, pip_value_usd  # noqa: E402
from calibrate_b import _hakikisha_chanzo_kimoja, bars_za_dirisha  # noqa: E402

RIPOTI = REPO / "research" / "reports"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--tf", default=None)
    ap.add_argument("--candidates", type=int, default=1000,
                    help="K — lazima ilingane na ile ya Calibration B (§9.4)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--months", type=int, default=0, help="0 = zote")
    ap.add_argument("--max-conditions", type=int, default=4)
    ap.add_argument("--hour-tz", default="UTC")
    ap.add_argument("--noise-floor", default=None)
    ap.add_argument("--cost-calibration", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--pip-value", nargs="*", default=[], metavar="SYM=VAL")
    ap.add_argument("--verbose", action="store_true",
                    help="chapisha uamuzi wa KILA aliyepita §8.4")
    args = ap.parse_args()

    # ---- R5: mlango, si ukaguzi ----
    floor = open_generator(
        noise_floor_path=Path(args.noise_floor) if args.noise_floor
        else RIPOTI / "noise_floor.json",
        cost_calibration_path=Path(args.cost_calibration) if args.cost_calibration
        else RIPOTI / "calibration_a.json",
    )
    print(f"R5 imefunguka · malango {len(floor.entries)} · {floor.source}")
    if floor.haipitiki:
        raise SystemExit(
            f"sakafu zisizopitika: {', '.join(floor.haipitiki)} — §13 ingebaki tupu"
        )

    # `K` ya utafutaji lazima ilingane na iliyopima sakafu. Kutafuta zaidi ni
    # kutafuta kwa bahati kubwa kuliko sakafu inavyojua (§9.1); kutafuta pungufu
    # ni kutumia bar iliyo juu kuliko inavyostahili.
    kwenye_sakafu = floor.variants_tested_min
    if args.candidates != kwenye_sakafu:
        print(f"   ONYO: K={args.candidates:,} lakini sakafu ilipimwa kwa "
              f"{kwenye_sakafu:,} (§9.1).\n"
              f"         Kubwa zaidi = bahati kubwa kuliko sakafu inavyojua; "
              f"ndogo zaidi = bar ya juu kupita kiasi.")

    root = _root(args.root)
    cfg_data = load_config(REPO / "config" / "data.yaml")
    cfg_risk = load_config(REPO / "config" / "risk.yaml")
    cfg_broker = load_config(REPO / "config" / "broker_costs.yaml")

    day_tz = str(cfg_data.get("timezone.day_reset_tz"))
    tf = args.tf or str(cfg_data.get("bars.decision_tf"))
    window = research_window(cfg_data)
    stage = declare("discovery", "DOCTRINE §3 HATUA 2 — kutafuta",
                    window, cfg=cfg_data)

    print(f"dirisha: {window.start} → {window.end} (HOLDOUT haiguswi, §16)")
    print(f"symbol {args.symbol} · TF {tf} · hour_tz {args.hour_tz} · "
          f"wagombea {args.candidates:,} · seed {args.seed}\n")

    inv = gundua(root, provenance=args.provenance,
                 exclusions=load_exclusions(cfg_data))
    _hakikisha_chanzo_kimoja(inv, args.symbol, window)
    if not inv.of(args.symbol):
        raise SystemExit(f"hakuna data ya {args.symbol} kwenye {root}")

    pip = pip_size(args.symbol)
    contracts = cfg_broker.get("contract_size", {"default": 100_000})
    commissions = cfg_broker.get("commission_usd_round_turn", {"default": 7.0})
    contract = float(contracts.get(args.symbol, contracts.get("default", 100_000)))
    if not bool(cfg_broker.get("contract_size_confirmed", False)):
        print("   ONYO: `contract_size_confirmed: false` — `pip_value` inategemea\n"
              "         namba isiyothibitishwa kwa MT5.\n")

    kwa_mkono = dict(piece.split("=", 1) for piece in args.pip_value)
    if args.symbol in kwa_mkono:
        pipval = float(kwa_mkono[args.symbol])
    else:
        pipval, njia = pip_value_usd(args.symbol, contract, inv)
        if pipval is None:
            raise SystemExit(njia)

    print("Kujenga bars…", flush=True)
    t0 = time.time()
    bars, n_ticks = bars_za_dirisha(inv, args.symbol, tf, stage, day_tz=day_tz,
                                    months=args.months, pip=pip, verbose=False)
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
        n_candidates=args.candidates, hour_tz=args.hour_tz, day_tz=day_tz,
    )

    # Kila aliyepita §8.4 anapimwa dhidi ya sakafu MARA MOJA, hapo hapo.
    # Kushikilia `BacktestResult` 1,000 ili kuzipima baadaye kungejaza kumbukumbu
    # bila sababu — wanaohitajika ni walionusurika pekee.
    uchujaji = SV.Screening()

    def kwa_aliyepita(rekodi, strategy, result, eco):
        m = result.metrics()
        uamuzi = SV.screen(rekodi.candidate_id, rekodi.variant_hash, m, floor)
        mnusurika = None
        if uamuzi.passed:
            mnusurika = SV.Survivor(
                verdict=uamuzi, strategy=strategy, economics=eco,
                n_trades=result.n_trades, n_months=int(m.get("n_months", 0)),
            )
        uchujaji.add(uamuzi, mnusurika)
        if args.verbose or uamuzi.passed:
            print(f"   {uamuzi.render(floor)}", flush=True)

    print(f"Kutafuta wagombea {args.candidates:,}…", flush=True)
    t0 = time.time()
    matokeo = P.search(bars, spec, cfg_risk=cfg_risk, seed=args.seed,
                       on_pass=kwa_aliyepita)
    muda = time.time() - t0

    print(f"\n{matokeo.render()}")
    print(f"\n{uchujaji.render(floor)}")
    print(f"\nmuda {muda:.0f}s · {muda / max(1, args.candidates) * 1000:.0f}ms "
          f"kwa mgombea")

    # S3 (§9.3) — Sharpe inayoripotiwa hapa ni GHAFI. Deflation kwa
    # `variants_tested` inakuja na §13; kuiacha bila kutajwa ingekuwa kuripoti
    # namba kubwa kuliko inavyostahili bila kusema hivyo.
    print(f"\n   S3: Sharpe hapo juu ni GHAFI. `variants_tested` = "
          f"{matokeo.variants_tested:,}; deflation inakuja na §13.")

    out_path = Path(args.out) if args.out else (
        RIPOTI / f"discovery_{args.symbol}_{tf}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": {"start": str(window.start), "end": str(window.end)},
        "n_bars": int(len(bars)), "n_ticks": int(n_ticks),
        "seed": args.seed, "search": matokeo.to_json(),
        "noise_floor": {
            "source": floor.source, "created_at": floor.created_at,
            "variants_tested_min": floor.variants_tested_min,
            "entries": {k: v.to_json() for k, v in floor.entries.items()},
        },
        "screening": uchujaji.to_json(),
        "sharpe_is_raw": True,          # S3 — bado haijafanyiwa deflation
    }, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {out_path}")

    ledger_path = out_path.with_name(out_path.stem + "_ledger.json")
    matokeo.ledger.write(ledger_path)          # S1 — ledger kamili, si muhtasari
    print(f"imeandikwa: {ledger_path}")

    if not uchujaji.survivors:
        print("\nHAKUNA ALIYENUSURIKA.\n"
              "   Si kosa: ndilo jibu la kawaida chini ya sakafu iliyopimwa.\n"
              "   Lango lililokata zaidi liko kwenye ripoti hapo juu.")
        return 1
    print(f"\nWALIONUSURIKA {len(uchujaji.survivors):,} — wanaenda §12 "
          f"(walk-forward, robustness).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
