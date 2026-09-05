"""Je data bandia ni RAHISI kwa sheria ileile? — DOCTRINE §9.5, §9.7, §2.

`why_rejected.py` kwenye GBPUSD ilionyesha kitu ambacho p-value peke yake
haikusema. Wagombea halisi hawakuwa **wa kawaida** chini ya null; walikuwa
chini kabisa yake kwenye vipimo vitatu kati ya vitano:

```
                              kati ya u   maana
profitable_month_fraction        0.0132   anazidi 1 kati ya 150 za null
sharpe                           0.0331   anazidi 4
net_pips_month                   0.1722   anazidi 25
max_drawdown                     0.3742   ya kawaida
net_account_return_month         0.3411   ya kawaida
```

"Hakuna edge" kunatabiri `u` sawia, kati ≈ 0.50. Kati ya 0.0132 si hivyo. Ni
ama soko halisi ni gumu zaidi kwa utaratibu, ama **data bandia ni rahisi zaidi
kwa utaratibu** — na hilo la pili limetokea mara mbili tayari: `fill_rate`
(§9.5) na drift ya `block_resample` (§9.7).

---

**Kipimo: sheria ILEILE, substrate mbili.**

`null_vs_real.py` na scan zinalinganisha **washindi** wa utafutaji — `max` ya
K juu ya kila upande. Kipimo hiki hakina uteuzi hata kidogo: kila mgombea
aliyefanyiwa backtest anahesabiwa, na wale walioishi pande zote mbili
wanalinganishwa **kwa kuoanisha**. Hakuna `max`, kwa hiyo hakuna tatizo la §9.1.

Kama surrogate inatoa `profitable_month_fraction` kubwa zaidi kwa sheria
zilezile, metric ni sifa ya ujenzi wa null. Utaratibu wa §9.5 unafuata:
inakuwa diagnostic, si lango.

Kama haitoi tofauti, dhana imekufa na `profitable_month_fraction` ni hukumu
halali kuhusu GBPUSD.

---

`acf1` ni uhusiano wa mfululizo wa faida ya **mwezi na mwezi uliotangulia**.
Ndicho kipimo cha moja kwa moja cha dhana: soko halisi lina misimu ambapo
sheria inapoteza mwezi baada ya mwezi, na `profitable_month_fraction` ndiyo
metric inayoathirika zaidi na hilo. Surrogate zinazovunja muundo wa ngazi ya
mwezi zingeondoa mfululizo huo — `acf1` ikishuka kuelekea sifuri wakati fungu
la miezi yenye faida linapanda.
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
from src.data.load import discover, load_exclusions  # noqa: E402
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

HALISI = "halisi"

# Vipimo vinavyolinganishwa. Vitatu vya kwanza ndivyo vilivyoonyesha upungufu;
# viwili vya mwisho ni **udhibiti** — vilikuwa vya kawaida (u ≈ 0.35), kwa hiyo
# tofauti kubwa hapo ingemaanisha kasoro ya jumla, si ya metric fulani.
VIPIMO = ("profitable_month_fraction", "sharpe", "net_pips_month",
          "max_drawdown", "net_account_return_month")


def acf1(monthly) -> float:
    """Uhusiano wa faida ya mwezi na ya mwezi uliotangulia."""
    import numpy as np

    x = np.asarray(monthly["net_pips"], dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 4:
        return float("nan")
    x = x - x.mean()
    chini = float((x * x).sum())
    if chini == 0.0:
        return float("nan")
    return float((x[1:] * x[:-1]).sum() / chini)


def _kusanya(bars, spec, cfg_risk, seed):
    """{candidate_id: {metric: thamani}} kwa KILA aliyefanyiwa backtest."""
    out: dict[str, dict[str, float]] = {}

    def kwa_kila(record, _strategy, result, _eco, _sababu):
        m = result.metrics()
        zake = {k: float(m.get(k, float("nan"))) for k in VIPIMO}
        zake["acf1"] = acf1(result.monthly())
        zake["n_trades"] = float(result.n_trades)
        out[record.candidate_id] = zake

    P.search(bars, spec, cfg_risk=cfg_risk, seed=seed, on_result=kwa_kila)
    return out


def _wastani(x):
    import numpy as np

    a = np.asarray([v for v in x if v == v], dtype=float)
    return float(np.median(a)) if a.size else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbol", default="GBPUSD")
    ap.add_argument("--tf", default=None)
    ap.add_argument("--candidates", type=int, default=120,
                    help="hakuna uteuzi hapa — WOTE wanahesabiwa, si bora")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--surrogate-seed", type=int, default=20260825,
                    help="chaguo-msingi: seed ya Calibration B, kwa hiyo "
                         "surrogate ni ZILEZILE zilizojenga sakafu")
    ap.add_argument("--months", type=int, default=0)
    ap.add_argument("--max-conditions", type=int, default=4)
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
    stage = declare("month_structure", "DOCTRINE §9.5 — je null ni rahisi",
                    window, cfg=cfg_data)

    print(f"dirisha: {window.start} → {window.end} (HOLDOUT haiguswi, §16)")
    print(f"symbol {args.symbol} · TF {tf} · wagombea {args.candidates:,} · "
          f"seed {args.seed} · surrogate-seed {args.surrogate_seed}\n")

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

    print("Kujenga bars…", flush=True)
    bars, n_ticks = bars_za_dirisha(inv, args.symbol, tf, stage,
                                    day_tz=day_tz, months=args.months, pip=pip)
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
        generator=GeneratorSpec(symbols=(args.symbol,),
                                max_conditions=args.max_conditions),
        n_candidates=args.candidates,
        hour_tz=args.hour_tz, day_tz=day_tz,
    )

    # ---- substrate zote, sheria zilezile ----
    kwa_substrate: dict[str, dict[str, dict[str, float]]] = {}
    for jina in (HALISI,) + tuple(S.FAMILIES):
        t0 = time.time()
        if jina == HALISI:
            frame = bars
        else:
            frame = S.make(bars, jina,
                           seed=NF._seed_of(args.surrogate_seed, jina, 0)).frame
        kwa_substrate[jina] = _kusanya(frame, spec, cfg_risk, args.seed)
        print(f"   {jina:<18} wagombea {len(kwa_substrate[jina]):>4} · "
              f"{time.time() - t0:>5.0f}s", flush=True)

    # Kuoanisha: wagombea walioishi kwenye substrate ZOTE. Sheria iliyokufa
    # upande mmoja (`DEGENERATE_ENTRY`) haiwezi kulinganishwa, na kuijaza kwa
    # thamani yoyote kungekuwa kubuni matokeo.
    wote = set(kwa_substrate[HALISI])
    for jina in S.FAMILIES:
        wote &= set(kwa_substrate[jina])
    wote = sorted(wote)
    print(f"\nWALIOOANISHWA: {len(wote)} kati ya {len(kwa_substrate[HALISI])} "
          f"waliofanyiwa backtest kwenye data halisi\n")
    if not wote:
        print("Hakuna sheria iliyoishi kwenye substrate zote — hakuna "
              "ulinganisho.")
        return 2

    vyote = VIPIMO + ("acf1", "n_trades")
    for kipimo in vyote:
        halisi = [kwa_substrate[HALISI][c][kipimo] for c in wote]
        kati_halisi = _wastani(halisi)
        print(f"   {kipimo}")
        print(f"      {'halisi':<18} {kati_halisi:>12.4f}")
        for fam in S.FAMILIES:
            zake = [kwa_substrate[fam][c][kipimo] for c in wote]
            kati = _wastani(zake)
            # Kuoanisha: ni sheria NGAPI ambazo surrogate iliwapa thamani
            # kubwa zaidi. Ndiyo namba yenye nguvu — haitegemei mgawanyo.
            juu = sum(1 for c in wote
                      if kwa_substrate[fam][c][kipimo]
                      > kwa_substrate[HALISI][c][kipimo])
            hai = sum(1 for c in wote
                      if kwa_substrate[fam][c][kipimo] ==
                      kwa_substrate[fam][c][kipimo]
                      and kwa_substrate[HALISI][c][kipimo] ==
                      kwa_substrate[HALISI][c][kipimo])
            print(f"      {fam:<18} {kati:>12.4f}   bandia juu "
                  f"{juu:>4}/{hai:<4} ({juu / max(hai, 1):>5.1%})")
        print()

    out_path = Path(args.out) if args.out else (
        REPO / "research" / "reports" /
        f"month_structure_{args.symbol}_{tf}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "window": {"start": str(window.start), "end": str(window.end)},
        "symbol": args.symbol, "timeframe": tf, "seed": args.seed,
        "surrogate_seed": args.surrogate_seed,
        "n_bars": int(len(bars)), "n_paired": len(wote),
        "paired": {c: {j: kwa_substrate[j][c] for j in kwa_substrate}
                   for c in wote},
    }, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"imeandikwa: {out_path}")

    # Hukumu inasomwa kwenye safu ya "bandia juu": 50% ni sarafu isiyo na
    # upendeleo — hakuna tofauti ya substrate. Karibu na 100% ni upendeleo wa
    # utaratibu, si bahati.
    kiini = "profitable_month_fraction"
    juu = {fam: sum(1 for c in wote
                    if kwa_substrate[fam][c][kiini]
                    > kwa_substrate[HALISI][c][kiini]) / len(wote)
           for fam in S.FAMILIES}
    print(f"\n{kiini}: bandia juu kwa " +
          " · ".join(f"{f[:5]} {v:.0%}" for f, v in juu.items()))
    if min(juu.values()) >= 0.70:
        print("   FAMILIA ZOTE TATU zinatoa fungu kubwa zaidi kwa sheria "
              "ZILEZILE.\n"
              "   Hiyo ni sifa ya ujenzi wa null, si ya soko — utaratibu wa "
              "§9.5 unafuata.")
        return 1
    if max(juu.values()) <= 0.60:
        print("   Hakuna upendeleo wa utaratibu. Dhana imekufa: "
              f"`{kiini}` ni hukumu halali kuhusu {args.symbol}.")
        return 0
    print("   Familia zinatofautiana — si sifa ya jumla ya ujenzi wa null.\n"
          "   Ona safu ya `acf1` kwa familia zenye upendeleo mkubwa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
