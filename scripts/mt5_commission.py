"""Pima commission kwa kufungua na kufunga lot 0.01 — DOCTRINE §2, §13.10.

```
python scripts\\mt5_commission.py                 # onyesha tu, hakuna order
python scripts\\mt5_commission.py --nakubali      # inatrade kwenye DEMO
```

**Kwa nini kutrade ndiyo njia pekee.** Commission haipo kwenye
`symbol_info` ya MT5. Haipo kwenye `account_info`. Njia pekee ya kuijua ni
`deal.commission` ya deal iliyotekelezwa. `mt5_specs.py` inaisoma kwenye
historia; ikiwa historia ni tupu, ni lazima kuizalisha.

---

**KINGA (hazina swichi ya kuzima):**

```
trade_mode lazima iwe 0 (DEMO). Akaunti halisi INAKATALIWA, siyo kuulizwa.
volume ni 0.01 daima. Hakuna hoja ya kuipandisha.
kila position inafungwa MARA MOJA baada ya kufunguliwa.
bila `--nakubali` hakuna order inayotumwa hata moja.
```

**Kinachopimwa ni akaunti HII.** Broker wengi wanaweka commission ya demo
tofauti na ya live — mara nyingi sifuri. Kwa hiyo jibu la `0.00` hapa
**halithibitishi** kwamba live ni bure; linamaanisha demo hii ni bure.
Ripoti inaandika `trade_mode` pamoja na namba ili hilo lisisahaulike, na
§10 hatua ya 5 inahitaji kupimwa upya kwenye akaunti halisi kabla ya lot
yoyote ya kweli.

**Gharama ya kipimo:** spread ya lot 0.01 kwa kila symbol — chini ya dola
moja kwa jumla, na ni pesa ya demo.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.mt5_specs import (RIPOTI, SYMBOLS, anzisha,   # noqa: E402
                               subiri_tick, tafuta_symbol)

VOLUME = 0.01          # haibadiliki
DEVIATION = 20         # points; kujaza kwenye demo, si utafiti


def fungua_na_funga(mt5, jina: str, *, magic: int) -> dict:
    """Buy 0.01, kisha funga papo hapo. Inarudisha deals mbili."""
    tick = subiri_tick(mt5, jina)
    if tick is None:
        return {"ok": False, "sababu": "hakuna quote"}

    ombi = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": jina, "volume": VOLUME,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask,
        "deviation": DEVIATION, "magic": magic,
        "comment": "elitefx cost probe",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    r = mt5.order_send(ombi)
    if r is None or r.retcode != mt5.TRADE_RETCODE_DONE:
        kod = r.retcode if r else mt5.last_error()
        # IOC haikubaliki kwa broker wote; FOK ndiyo mbadala wa kawaida.
        ombi["type_filling"] = mt5.ORDER_FILLING_FOK
        r = mt5.order_send(ombi)
        if r is None or r.retcode != mt5.TRADE_RETCODE_DONE:
            return {"ok": False,
                    "sababu": f"kufungua kumeshindwa: {kod} / "
                              f"{r.retcode if r else mt5.last_error()}"}

    ticket_in = r.order
    time.sleep(0.5)

    nafasi = [p for p in (mt5.positions_get(symbol=jina) or ())
              if p.magic == magic]
    if not nafasi:
        return {"ok": False, "sababu": "position haikupatikana baada ya kufungua"}

    p = nafasi[0]
    tick = subiri_tick(mt5, jina)
    funga = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": jina, "volume": p.volume,
        "type": mt5.ORDER_TYPE_SELL, "position": p.ticket,
        "price": tick.bid if tick else 0.0,
        "deviation": DEVIATION, "magic": magic,
        "comment": "elitefx cost probe close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": ombi["type_filling"],
    }
    r2 = mt5.order_send(funga)
    if r2 is None or r2.retcode != mt5.TRADE_RETCODE_DONE:
        return {"ok": False, "ticket": p.ticket,
                "sababu": f"KUFUNGA KUMESHINDWA: "
                          f"{r2.retcode if r2 else mt5.last_error()} — "
                          f"funga kwa mkono kwenye MT5!"}
    return {"ok": True, "ticket_in": ticket_in, "position": p.ticket}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nakubali", action="store_true",
                    help="tuma orders kweli (DEMO pekee)")
    ap.add_argument("--symbols", default=None,
                    help="orodha kwa koma; chaguo-msingi ni zote 12")
    ap.add_argument("--terminal", default=None)
    ap.add_argument("--out", default=str(RIPOTI / "mt5_commission.json"))
    args = ap.parse_args()

    try:
        import MetaTrader5 as mt5                              # noqa: N813
    except ImportError:
        print("MetaTrader5 haijasakinishwa.  pip install MetaTrader5")
        return 2

    ok, chanzo = anzisha(mt5, args.terminal)
    if not ok:
        print(f"mt5.initialize() imeshindwa.\n   {chanzo}")
        return 2
    print(f"MT5: {chanzo}")

    acc = mt5.account_info()
    if acc is None:
        print("account_info() ni tupu.")
        mt5.shutdown()
        return 2

    # ---- KINGA: demo pekee ----
    if acc.trade_mode != 0:
        aina = {1: "contest", 2: "HALISI"}.get(int(acc.trade_mode),
                                               str(acc.trade_mode))
        print(f"\nAKAUNTI SI DEMO ({aina}). Script hii inakataa kutrade.")
        print("Commission ya akaunti halisi inapimwa kwa deals ZAKO ZA")
        print("KAWAIDA: `python scripts/mt5_specs.py --deals-since <tarehe>`.")
        mt5.shutdown()
        return 3
    if not acc.trade_allowed:
        print("\nAkaunti haina ruhusa ya kutrade (`trade_allowed` ni False).")
        print("MT5 → Tools → Options → Expert Advisors → "
              "Allow algorithmic trading.")
        mt5.shutdown()
        return 2

    teule = ([s.strip().upper() for s in args.symbols.split(",")]
             if args.symbols else list(SYMBOLS))
    print(f"   demo · {acc.currency} · symbols {len(teule)} · "
          f"volume {VOLUME} kwa kila moja")

    if not args.nakubali:
        print("\n--nakubali HAIJATOLEWA: hakuna order itakayotumwa.")
        print("Ikitolewa, script itafungua na kufunga BUY ya lot 0.01 kwa")
        print(f"kila symbol kati ya {len(teule)}, kisha itasoma commission")
        print("kutoka kwenye deals zilizotokea. Ni pesa ya demo.")
        mt5.shutdown()
        return 0

    magic = int(time.time()) % 1_000_000
    tangu = datetime.now(timezone.utc) - timedelta(minutes=5)
    print(f"\n   magic {magic}\n")

    zilizofanyika, zilizoshindwa = [], []
    for msingi in teule:
        jina = tafuta_symbol(mt5, msingi)
        if jina is None:
            zilizoshindwa.append((msingi, "haipo kwa broker huyu"))
            print(f"   {msingi:<8} haipo")
            continue
        mt5.symbol_select(jina, True)
        r = fungua_na_funga(mt5, jina, magic=magic)
        if r["ok"]:
            zilizofanyika.append((msingi, jina))
            print(f"   {msingi:<8} imefunguliwa na kufungwa")
        else:
            zilizoshindwa.append((msingi, r["sababu"]))
            print(f"   {msingi:<8} {r['sababu']}")

    if not zilizofanyika:
        print("\nHAKUNA DEAL. Commission haijapimwa.")
        mt5.shutdown()
        return 2

    # ---- soma commission kutoka kwenye deals zilizotokea ----
    time.sleep(1.0)
    deals = mt5.history_deals_get(
        tangu, datetime.now(timezone.utc) + timedelta(minutes=1)) or ()
    zetu = [d for d in deals if d.magic == magic]

    kwa_symbol: dict[str, dict] = {}
    for d in zetu:
        j = kwa_symbol.setdefault(d.symbol, {"commission": 0.0, "vol_in": 0.0,
                                             "n": 0, "profit": 0.0})
        j["commission"] += float(d.commission)
        j["profit"] += float(d.profit)
        j["n"] += 1
        if d.entry in (0, 2):
            j["vol_in"] += float(d.volume)

    print("\n" + "=" * 74)
    print("COMMISSION ILIYOPIMWA (round-turn kwa lot 1)")
    print("=" * 74)
    print(f"   {'symbol':<16} {'$/lot RT':>10} {'deals':>7} {'spread $':>10}")
    matokeo = {}
    for sym, j in sorted(kwa_symbol.items()):
        if j["vol_in"] <= 0:
            continue
        rt = abs(j["commission"]) / j["vol_in"]
        matokeo[sym] = {"commission_usd_round_turn": rt, "deals": j["n"],
                        "spread_cost_usd": j["profit"]}
        print(f"   {sym:<16} {rt:>10.2f} {j['n']:>7} {j['profit']:>10.2f}")

    jumla = sum(v["commission_usd_round_turn"] for v in matokeo.values())
    if jumla == 0:
        print("\n   ZOTE NI SIFURI.")
        print("   Hii ni akaunti ya DEMO. Broker wengi wanaweka commission ya")
        print("   demo kuwa sifuri hata pale live inatoza. Spread ya EURUSD ya")
        print("   pips 0.40 ni ya aina ya akaunti ya raw/ECN, na hizo karibu")
        print("   daima zinatoza commission — kwa hiyo sifuri hapa ni ya")
        print("   MASHAKA, si uthibitisho.")
        print("   `broker_costs.yaml` HAIBADILIKI kwa jibu hili.")

    matokeo_yote = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "trade_mode": int(acc.trade_mode), "currency": acc.currency,
        "volume": VOLUME, "magic": magic,
        "per_symbol": matokeo,
        "failed": [{"symbol": s, "reason": r} for s, r in zilizoshindwa],
        "all_zero": jumla == 0,
        "warning": ("demo pekee — inahitaji kupimwa upya kwenye akaunti "
                    "halisi kabla ya §10 hatua ya 5"),
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matokeo_yote, indent=2, default=str) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"\nimeandikwa: {path}")

    wazi = mt5.positions_get() or ()
    zetu_wazi = [p for p in wazi if p.magic == magic]
    if zetu_wazi:
        print(f"\nONYO: positions {len(zetu_wazi)} bado ZIKO WAZI — "
              f"zifunge kwa mkono kwenye MT5:")
        for p in zetu_wazi:
            print(f"   ticket {p.ticket} · {p.symbol} · {p.volume}")
    else:
        print("Hakuna position iliyobaki wazi.")

    mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
