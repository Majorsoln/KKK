"""Gharama kwa SAA ya siku, kwenye H1 — DOCTRINE §8.3, R11.

Calibration A ilionyesha spread ya mpaka wa D1 ni mara 1.6–4.4 ya ya H1 kwenye
symbols ZOTE 12. Sababu ni saa, si timeframe. Amri hii inauliza swali linalofuata:
**jambo lile lile linatokea kiasi gani ndani ya H1?**

    python scripts/cost_by_hour.py --provenance aggregator
    python scripts/cost_by_hour.py --provenance aggregator --symbols EURUSD --months 12

Rollover haidhaniwi. Inapimwa kwa saa za UTC, kisha kwa saa za
`broker_server_tz`; ile inayotoa mgawanyo **mkali zaidi** ndiyo inayoungwa mkono
na data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.bars import build  # noqa: E402
from src.data.load import discover, iter_months, load_exclusions  # noqa: E402
from src.data.window import declare, research_window  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import pip_size  # noqa: E402
from src.validation import cost_by_hour as CH  # noqa: E402


def _root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env = os.environ.get("ELITEFX_L0_ROOT") or os.environ.get("ELITEFX_RESEARCH_ROOT")
    if not env:
        raise SystemExit("Weka `ELITEFX_RESEARCH_ROOT` au tumia --root")
    path = Path(env)
    return path if path.name == "L0_raw" else path / "data" / "L0_raw"


def main() -> int:
    ap = argparse.ArgumentParser(description="Gharama kwa saa ya siku")
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None)
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--months", type=int, default=0, help="0 = zote")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg_data = load_config(REPO / "config" / "data.yaml")
    root = _root(args.root)
    symbols = args.symbols or list(cfg_data.get("source.symbols"))

    tf = str(cfg_data.get("bars.decision_tf", "H1"))
    day_tz = str(cfg_data.get("timezone.day_reset_tz", "UTC"))
    broker_tz = str(cfg_data.get("timezone.broker_server_tz", "UTC"))
    stage = declare("cost_by_hour", "DOCTRINE §8.3 — gharama kwa saa ya siku",
                    research_window(cfg_data), cfg=cfg_data)

    print(f"GHARAMA KWA SAA · {tf} · {stage.window.start} -> {stage.window.end}")
    print(f"   tz zinazolinganishwa: UTC dhidi ya {broker_tz}")
    print(f"   symbols {len(symbols)}\n")

    inv = discover(root, provenance=args.provenance,
                   exclusions=load_exclusions(cfg_data))
    symbols = [s for s in symbols if s in inv.symbols]
    if not symbols:
        raise SystemExit("hakuna symbol yenye data")

    gaps = cfg_data.get("quality.max_gap_seconds", {})
    matokeo: dict[str, Any] = {}

    for symbol in symbols:
        anza = time.time()
        pip = pip_size(symbol)
        max_gap = float(gaps.get(symbol, gaps.get("default", 3600)))
        wapimaji = {
            tzname: CH.HourSamples(symbol=symbol, timeframe=tf, tz=tzname,
                                   max_gap_seconds=max_gap)
            for tzname in ("UTC", broker_tz)
        }

        n = 0
        for label, chunk, _ in iter_months(inv, symbol, stage, pip=pip):
            bars = build(chunk, tf, stage, day_tz=day_tz).bars
            if len(bars) == 0:
                continue
            for mpimaji in wapimaji.values():
                mpimaji.add(chunk, bars, day_tz=day_tz)
            n += 1
            print(f"   {symbol} {label}  ticks {len(chunk):>9,}", flush=True)
            if args.months and n >= args.months:
                break

        if n == 0:
            print(f"   {symbol}: hakuna mwezi wenye data\n")
            continue

        matokeo[symbol] = {}
        for tzname, mpimaji in wapimaji.items():
            rows = mpimaji.table()
            muhtasari = CH.summarise(rows)
            matokeo[symbol][tzname] = {"rows": rows, **muhtasari}

        utc, ndani = (matokeo[symbol]["UTC"], matokeo[symbol][broker_tz])
        print(f"\n{CH.render(symbol, ndani['rows'], broker_tz)}")
        print(f"   ukali: {broker_tz} {ndani['ukali']:.2f}x (saa {ndani['saa_mbaya']}) · "
              f"UTC {utc['ukali']:.2f}x (saa {utc['saa_mbaya']}) · "
              f"{time.time() - anza:.0f}s\n", flush=True)

    if not matokeo:
        raise SystemExit("hakuna kilichopimwa")

    print("=" * 78)
    print(f"MUHTASARI — ukali wa saa mbaya kuliko zote (spread ÷ median)")
    print(f"   {'symbol':<8} {'UTC':>18} {'':>4} {broker_tz:>22}")
    kali_ndani = kali_utc = 0
    for symbol, kwa_tz in matokeo.items():
        u, b = kwa_tz["UTC"], kwa_tz[broker_tz]
        kali_ndani += b["ukali"] > u["ukali"]
        kali_utc += u["ukali"] > b["ukali"]
        print(f"   {symbol:<8} saa {u['saa_mbaya']:>2} · {u['ukali']:>5.2f}x     "
              f"saa {b['saa_mbaya']:>2} · {b['ukali']:>5.2f}x")

    print()
    if kali_ndani > kali_utc:
        print(f"   {broker_tz} inatoa mgawanyo MKALI zaidi kwenye symbols "
              f"{kali_ndani}/{len(matokeo)} — `broker_server_tz` inaungwa mkono na data.")
    elif kali_utc > kali_ndani:
        print(f"   UTC inatoa mgawanyo mkali zaidi kwenye symbols {kali_utc}/{len(matokeo)} "
              f"— `broker_server_tz: {broker_tz}` HAIJATHIBITISHWA na data.")
    else:
        print("   tz mbili zinatoa ukali sawa — data haitofautishi.")

    out = Path(args.out) if args.out else Path(
        os.environ.get("ELITEFX_RESEARCH_ROOT", REPO / "research")
    ) / "reports" / "cost_by_hour.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "timeframe": tf, "broker_tz": broker_tz,
            "config_hash": cfg_data.config_hash,
            "symbols": matokeo,
        }, indent=2, default=str) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"\nushahidi: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
