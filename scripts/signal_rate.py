"""Je null inatoa NAFASI nyingi zaidi za kutrade? — DOCTRINE §9.2, §9.7, §9.8.

Discovery ya GBPUSD ilikataliwa 84/84 na malango matatu, kwa kauli moja:
`net_pips_month`, `profitable_month_fraction`, `sharpe`. Malango mengine mawili
yaliruhusu wagombea kupita. Matatu yaliyokataa kwa umoja ni yale yale
yanayotegemea **mzunguko wa kutrade**:

* `net_pips_month` = `trades × pips kwa trade ÷ miezi`
* `profitable_month_fraction` — mwezi usio na trade ni mwezi usio na faida
* `sharpe` — miezi mingi ya sifuri inapunguza wastani

Bora wa GBPUSD alikuwa na **trades 48 kwa miezi 99**, edge ya pips 68.6. Sakafu
inadai pips 381 kwa mwezi — ingehitaji trades ~580, mara 12 zaidi.

**Swali:** je surrogate zinatoa signals nyingi zaidi kuliko soko halisi?

Ikiwa ndiyo, malango hayo matatu hayalinganishi "ubora dhidi ya kelele" bali
"mzunguko dhidi ya mzunguko" — na sakafu ingekuwa juu kupita kiasi kwa sababu
ambayo si ya strategy.

---

**Kipimo hiki hakiendeshi backtest.** Kinahesabu **signals** pekee: features →
`evaluate.signals()`. Hakuna kutembea kwenye ticks, hakuna RCE. Kwa hiyo ni
dakika badala ya saa, na kinajibu swali moja kwa usahihi.

Familia za §9.2 zinadai kuhifadhi/kuvunja mambo mahususi. **Hakuna inayodai
kuhifadhi idadi ya nafasi za kutrade.** Kama ni tofauti, ni athari ya pembeni
isiyokuwa imepimwa — kama drift ya §9.7 ilivyokuwa.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.features import build as build_features  # noqa: E402
from src.data.load import discover as gundua  # noqa: E402
from src.data.load import load_exclusions  # noqa: E402
from src.data.window import declare, research_window  # noqa: E402
from src.discovery.evaluate import EvaluateError, signals  # noqa: E402
from src.discovery.generator import GeneratorSpec, generate  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import pip_size  # noqa: E402
from src.validation import noise_floor as NF  # noqa: E402
from src.validation import surrogates as S  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from calibrate_a import _root  # noqa: E402
from calibrate_b import _hakikisha_chanzo_kimoja, bars_za_dirisha  # noqa: E402


def _hesabu(feats, wagombea, tf: str, day_tz: str) -> dict[str, float]:
    """Signals kwa kila mgombea juu ya features hizi.

    `NO_SIGNALS`/`ALWAYS_IN` zinahesabiwa kando: mgombea asiyewaka kamwe na
    anayewaka kila bar wote wana `n_signals` isiyo na maana, lakini kwa sababu
    tofauti kabisa.
    """
    idadi: list[int] = []
    hakuna = daima = imeshindwa = 0
    for c in wagombea:
        try:
            out = signals(c, feats, timeframe=tf, day_tz=day_tz)
        except EvaluateError:
            imeshindwa += 1
            continue
        if out.degenerate == "NO_SIGNALS":
            hakuna += 1
        elif out.degenerate == "ALWAYS_IN":
            daima += 1
        else:
            idadi.append(out.n_signals)

    return {
        "n_halali": len(idadi),
        "kati": float(statistics.median(idadi)) if idadi else float("nan"),
        "wastani": float(statistics.fmean(idadi)) if idadi else float("nan"),
        "jumla": float(sum(idadi)),
        "hakuna_signals": hakuna, "daima_ndani": daima,
        "haikutathminika": imeshindwa,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbol", default="GBPUSD")
    ap.add_argument("--tf", default=None)
    ap.add_argument("--candidates", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--surrogate-seeds", type=int, default=2)
    ap.add_argument("--months", type=int, default=0)
    ap.add_argument("--hour-tz", default="UTC")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = _root(args.root)
    cfg_data = load_config(REPO / "config" / "data.yaml")
    day_tz = str(cfg_data.get("timezone.day_reset_tz"))
    tf = args.tf or str(cfg_data.get("bars.decision_tf"))
    window = research_window(cfg_data)
    stage = declare("signal_rate", "DOCTRINE §9.2 — nafasi za kutrade",
                    window, cfg=cfg_data)

    inv = gundua(root, provenance=args.provenance,
                 exclusions=load_exclusions(cfg_data))
    _hakikisha_chanzo_kimoja(inv, args.symbol, window)

    print(f"symbol {args.symbol} · TF {tf} · wagombea {args.candidates:,}")
    print("Kujenga bars…", flush=True)
    bars, n_ticks = bars_za_dirisha(inv, args.symbol, tf, stage, day_tz=day_tz,
                                    months=args.months,
                                    pip=pip_size(args.symbol), verbose=False)
    print(f"   bars {len(bars):,} · ticks {n_ticks:,}\n")

    # Wagombea WALE WALE kwa kila frame — ndiyo maana orodha, si iterator.
    spec = GeneratorSpec(symbols=(args.symbol,))
    wagombea = list(generate(spec, args.candidates, seed=args.seed))

    print(f"{'':<26} {'wenye signals':>13} {'kati':>8} {'jumla':>10} "
          f"{'hakuna':>7} {'daima':>6}")

    def ripoti(jina: str, frame) -> dict:
        t0 = time.time()
        feats = build_features(frame, symbol=args.symbol, hour_tz=args.hour_tz)
        out = _hesabu(feats, wagombea, tf, day_tz)
        print(f"{jina:<26} {out['n_halali']:>13,} {out['kati']:>8,.0f} "
              f"{out['jumla']:>10,.0f} {out['hakuna_signals']:>7,} "
              f"{out['daima_ndani']:>6,}  ({time.time() - t0:.0f}s)", flush=True)
        return out

    halisi = ripoti("HALISI", bars)
    bandia: dict[str, list] = {}
    for fam in S.FAMILIES:
        bandia[fam] = []
        for i in range(max(1, args.surrogate_seeds)):
            sur = S.make(bars, fam, seed=NF._seed_of(args.seed, fam, i))
            bandia[fam].append(ripoti(f"{fam} #{i}", sur.frame))

    zote = [r for rows in bandia.values() for r in rows]
    kati_b = statistics.median([r["kati"] for r in zote if r["kati"] == r["kati"]])
    n_b = statistics.median([r["n_halali"] for r in zote])

    print(f"\n{'kipimo':<26} {'HALISI':>12} {'bandia kati':>12}   uwiano")
    for jina, h, b in (("signals kwa mgombea", halisi["kati"], kati_b),
                       ("wagombea wenye signals", halisi["n_halali"], n_b)):
        uwiano = b / h if h else float("nan")
        print(f"{jina:<26} {h:>12,.0f} {b:>12,.0f}   {uwiano:>6.2f}×")

    uwiano = kati_b / halisi["kati"] if halisi["kati"] else float("nan")
    print()
    if uwiano == uwiano and uwiano > 1.25:
        print(f"NULL INATOA NAFASI NYINGI ZAIDI ({uwiano:.2f}×).\n"
              f"   Malango yanayotegemea mzunguko — `net_pips_month`,\n"
              f"   `profitable_month_fraction`, `sharpe` — yanalinganisha\n"
              f"   mzunguko dhidi ya mzunguko, si ubora dhidi ya kelele.\n"
              f"   Familia za §9.2 hazidai kuhifadhi idadi ya nafasi za kutrade;\n"
              f"   ni athari ya pembeni isiyokuwa imepimwa, kama drift ya §9.7.")
        alama = "null_ina_nafasi_nyingi"
    elif uwiano == uwiano and uwiano < 0.8:
        print(f"NULL INATOA NAFASI CHACHE ZAIDI ({uwiano:.2f}×).\n"
              f"   Malango ya mzunguko yangekuwa RAHISI kupita kuliko "
              f"inavyostahili.")
        alama = "null_ina_nafasi_chache"
    else:
        print(f"NAFASI ZINALINGANA ({uwiano:.2f}×).\n"
              f"   Malango matatu yaliyokataa 84/84 hayakukataa kwa sababu ya\n"
              f"   mzunguko. Chanzo kingine kinahitaji kutafutwa.")
        alama = "zinalingana"

    out_path = Path(args.out) if args.out else (
        REPO / "research" / "reports" / f"signal_rate_{args.symbol}_{tf}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "symbol": args.symbol, "timeframe": tf, "n_bars": int(len(bars)),
        "n_candidates": args.candidates, "seed": args.seed,
        "halisi": halisi, "bandia": bandia, "uwiano": uwiano, "hukumu": alama,
    }, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
