"""Amri 2 — Calibration A: injini inapima gharama yake yenyewe (§8.3, R5, R16).

Kwa kila `(pair, TF)`: gharama **iliyotokea** kutoka ticks, na gharama ambayo
RCE **itaitumia** kusizisha lots. Zote mbili, kando, pamoja na ukaguzi
`live ≥ research`.

Endesha jaribio dogo kwanza:

    python scripts/calibrate_a.py --symbols EURUSD --tf H1 --months 6

Kisha kamili:

    python scripts/calibrate_a.py

Data inasomwa **mwezi kwa mwezi**. Miaka 10 ya ticks za symbol moja haitoshei
kwenye kumbukumbu, na mashine iliyosimama haitoi jibu lolote — wala si la
kukosea.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.data.bars import TIMEFRAMES, build  # noqa: E402
from src.data.load import LoadError, discover, iter_months, read_partition  # noqa: E402
from src.data.window import declare, research_window  # noqa: E402
from src.rce.config import load_config  # noqa: E402
from src.rce.cost import SymbolSpec, pip_size  # noqa: E402
from src.validation import cost_calibration as CA  # noqa: E402


def _root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env = os.environ.get("ELITEFX_L0_ROOT") or os.environ.get("ELITEFX_RESEARCH_ROOT")
    if not env:
        raise SystemExit("Weka `ELITEFX_RESEARCH_ROOT` au tumia --root")
    path = Path(env)
    return path if path.name == "L0_raw" else path / "data" / "L0_raw"


def _median_mid(inv, symbol: str) -> float | None:
    """Bei ya kati ya symbol — kwa kubadilisha `pip_value` kuwa USD.

    Inasoma partition MOJA ya katikati ya historia. Kiwango cha ubadilishaji
    kinatoka kwenye data yenyewe, si kwenye jedwali la nje.
    """
    chunks = inv.of(symbol)
    if not chunks:
        return None
    try:
        frame = read_partition(chunks[len(chunks) // 2].path)
    except LoadError:
        return None
    if frame.empty:
        return None
    return float(((frame["bid"] + frame["ask"]) / 2.0).median())


def pip_value_usd(symbol: str, contract_size: float, inv) -> tuple[float, str]:
    """Thamani ya pip 1 kwa lot 1, kwa USD. Rudi na thamani NA njia iliyotumika."""
    pip = pip_size(symbol)
    quote = symbol[3:6].upper()
    kwa_quote = pip * contract_size

    if quote == "USD":
        return kwa_quote, "quote=USD"

    rate = _median_mid(inv, f"USD{quote}")
    if rate:
        return kwa_quote / rate, f"USD{quote}={rate:.5f}"

    rate = _median_mid(inv, f"{quote}USD")
    if rate:
        return kwa_quote * rate, f"{quote}USD={rate:.5f}"

    raise SystemExit(
        f"{symbol}: hakuna data ya kubadilisha {quote} kuwa USD. "
        f"Pakia USD{quote} au {quote}USD, au toa --pip-value {symbol}=<thamani>"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibration A")
    ap.add_argument("--root", default=None)
    ap.add_argument("--provenance", default=None,
                    help="chagua chanzo kimoja, mf. aggregator au broker")
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--tf", nargs="*", default=None)
    ap.add_argument("--months", type=int, default=0, help="0 = zote")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pip-value", nargs="*", default=[], metavar="SYM=VAL")
    ap.add_argument("--strict-quality", action="store_true",
                    help="simamisha ikiwa ukaguzi wa §4.3 unashindwa kwa mwezi wowote")
    args = ap.parse_args()

    cfg_data = load_config(REPO / "config" / "data.yaml")
    cfg_risk = load_config(REPO / "config" / "risk.yaml")
    cfg_broker = load_config(REPO / "config" / "broker_costs.yaml")

    root = _root(args.root)
    symbols = args.symbols or list(cfg_data.get("source.symbols"))
    tfs = args.tf or list(cfg_data.get("bars.timeframes"))
    mbaya = [t for t in tfs if t not in TIMEFRAMES]
    if mbaya:
        raise SystemExit(f"TF hazijulikani: {mbaya} — zinazoruhusiwa {TIMEFRAMES}")

    day_tz = str(cfg_data.get("timezone.day_reset_tz", "UTC"))
    stage = declare("calibration_a", "DOCTRINE §8.3 — gharama halisi dhidi ya kadirio",
                    research_window(cfg_data), cfg=cfg_data)

    print(f"CALIBRATION A · {stage.window.start} -> {stage.window.end}")
    print(f"   root {root}")
    print(f"   symbols {len(symbols)} · TF {tfs} · day_tz {day_tz}")
    print(f"   config_hash data {cfg_data.config_hash} · risk {cfg_risk.config_hash}\n")

    inv = discover(root, provenance=args.provenance)
    hazipo = [s for s in symbols if s not in inv.symbols]
    if hazipo:
        print(f"   HAZIPO kwenye L0: {hazipo}")
        symbols = [s for s in symbols if s in inv.symbols]
    if not symbols:
        raise SystemExit("hakuna symbol yenye data")

    overrides = dict(
        (piece.split("=", 1)[0].upper(), float(piece.split("=", 1)[1]))
        for piece in args.pip_value
    )
    contracts = cfg_broker.get("contract_size", {"default": 100_000})
    commissions = cfg_broker.get("commission_usd_round_turn", {"default": 7.0})
    confirmed = bool(cfg_broker.get("contract_size_confirmed", False))
    if not confirmed:
        print("   ONYO: `contract_size_confirmed: false` kwenye broker_costs.yaml.\n"
              "         `pip_value` inategemea namba isiyothibitishwa kwa MT5.\n")

    rows = []
    for symbol in symbols:
        anza = time.time()
        pip = pip_size(symbol)
        contract = float(contracts.get(symbol, contracts.get("default", 100_000)))
        if symbol in overrides:
            pipval, njia = overrides[symbol], "--pip-value"
        else:
            pipval, njia = pip_value_usd(symbol, contract, inv)

        # Kizingiti cha pengo: mpaka wa bar unapoangukia soko lililofungwa,
        # "tick inayofuata" ni ya Jumapili usiku. Tofauti yake si slippage.
        # Namba inatoka `data.yaml`, si hapa.
        gaps = cfg_data.get("quality.max_gap_seconds", {})
        max_gap = float(gaps.get(symbol, gaps.get("default", 3600)))

        samples = {
            tf: CA.CellSamples(symbol=symbol, timeframe=tf, max_gap_seconds=max_gap)
            for tf in tfs
        }
        spreads_h1: list = []
        spreads_m5: list = []
        n_miezi = n_ticks = 0
        onyo = 0

        for label, chunk, report in iter_months(
            inv, symbol, stage, max_spread_pips=None, pip=pip, strict=args.strict_quality
        ):
            n_miezi += 1
            n_ticks += len(chunk)
            onyo += len(report.warnings)

            # Upande wa live unahitaji H1 (msingi) na M5 (spike-guard) DAIMA,
            # hata kama TF hizo hazipo kwenye `--tf`.
            zinazohitajika = list(dict.fromkeys([*tfs, "H1", "M5"]))
            bars_za_mwezi = {
                tf: build(chunk, tf, stage, day_tz=day_tz).bars for tf in zinazohitajika
            }

            for tf in tfs:
                bars = bars_za_mwezi[tf]
                if len(bars) > CA.ATR_WINDOW:
                    samples[tf].add(chunk, bars, day_tz=day_tz)

            for tf, sink, column in (("H1", spreads_h1, "spread_mean"),
                                     ("M5", spreads_m5, "spread_p95")):
                bars = bars_za_mwezi[tf]
                if len(bars):
                    sink.append(bars[column])

            print(f"   {symbol} {label}  ticks {len(chunk):>9,}  onyo {len(report.warnings)}",
                  flush=True)
            if args.months and n_miezi >= args.months:
                break

        if not n_miezi:
            print(f"   {symbol}: hakuna mwezi wenye data ndani ya dirisha\n")
            continue

        import pandas as pd

        h1 = pd.concat(spreads_h1).sort_index() if spreads_h1 else pd.Series(dtype=float)
        m5 = pd.concat(spreads_m5).sort_index() if spreads_m5 else pd.Series(dtype=float)
        live_spread = CA.live_spread_median(h1, m5, cfg_risk)

        broker = CA.Broker(
            spec=SymbolSpec(symbol=symbol, point=pip / 10.0, contract_size=contract,
                            volume_min=0.01, volume_step=0.01, volume_max=50.0),
            pip_value_acct=pipval,
            commission_round_turn=float(
                commissions.get(symbol, commissions.get("default", 7.0))
            ),
        )

        print(f"   {symbol}: miezi {n_miezi} · ticks {n_ticks:,} · onyo {onyo} · "
              f"max_gap {max_gap:.0f}s · "
              f"pip_value ${pipval:.4f} ({njia}) · live_spread {live_spread:.3f} pips "
              f"· {time.time() - anza:.0f}s")

        for tf in tfs:
            if samples[tf].n_chunks == 0:
                print(f"      {tf}: hakuna kipande chenye bars za kutosha")
                continue
            row = CA.calibrate_cell(
                timeframe=tf, cfg_risk=cfg_risk, broker=broker,
                samples=samples[tf], live_spread=live_spread, day_tz=day_tz,
            )
            rows.append(row)
            print("      " + row.render())
        print(flush=True)

    if not rows:
        raise SystemExit("hakuna cell iliyopimwa")

    table = CA.CostTable(
        rows=tuple(rows),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=f"L0 {root} · stage {stage.name}",
        config_hash=f"data={cfg_data.config_hash} risk={cfg_risk.config_hash}",
    )

    out = Path(args.out) if args.out else Path(
        os.environ.get("ELITEFX_RESEARCH_ROOT", REPO / "research")
    ) / "reports" / "calibration_a.json"
    payload = table.to_json()
    payload["contract_size_confirmed"] = confirmed
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, default=str) + "\n",
        encoding="utf-8", newline="\n",
    )

    print("=" * 78)
    print(table.render())
    print("=" * 78)
    print(f"ushahidi: {out}")
    if table.broken:
        print("R16 IMEVUNJIKA — injini haiendelei hadi hii itatuliwe.")
        return 2
    print("R16 sawa: `live >= research` kwenye kila cell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
