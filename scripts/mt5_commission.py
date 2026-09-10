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
volume ina kikomo kigumu cha 1.00 lot; chaguo-msingi 0.10.
position moja kwa wakati — inafungwa KABLA ya inayofuata kufunguliwa.
bila `--nakubali` hakuna order inayotumwa hata moja.
```

**Kuhusu volume.** Toleo la kwanza lilikuwa `0.01` lisilobadilika, na
niliandika *"hakuna hoja ya kuipandisha"*. **Hoja ipo.** MT5 inaandika
`deal.commission` kwa senti, kwa hiyo kugawa kwa volume kunazidisha
mviringo kwa `1/volume`: kwa `0.01` ukungu ni **$2.00 kwa lot**, na run
ya kwanza ilitoa namba shufwa zote (4, 6, 8, 10) — saini ya ukungu, si
bei ya broker. `0.10` inaupunguza hadi $0.20; `1.00` hadi $0.02.

**Kinachopimwa ni akaunti HII.** Broker wengi wanaweka commission ya demo
tofauti na ya live — mara nyingi sifuri. Kwa hiyo jibu la `0.00` hapa
**halithibitishi** kwamba live ni bure; linamaanisha demo hii ni bure.
Ripoti inaandika `trade_mode` pamoja na namba ili hilo lisisahaulike, na
§10 hatua ya 5 inahitaji kupimwa upya kwenye akaunti halisi kabla ya lot
yoyote ya kweli.

**Gharama ya kipimo:** spread ya volume iliyochaguliwa kwa kila symbol.
Ni pesa ya demo. Endesha soko likiwa wazi: spread ya kufungwa/kufunguliwa
ni pana mara nyingi, na ingawa **haiathiri commission hata kidogo**
(commission ni bei ya broker, si ya soko), inapoteza pesa ya demo bure.
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

# Volume ya chaguo-msingi. **Si suala la usalama — ni la UKUBWA WA KIPIMO.**
#
# MT5 inaandika `deal.commission` kwa senti. Kugawa kwa volume kunazidisha
# mviringo huo kwa `1/volume`:
#
#     volume 0.01  →  ukungu $2.00 kwa lot     (senti 0.01 × 2 ÷ 0.01)
#     volume 0.10  →  ukungu $0.20 kwa lot
#     volume 1.00  →  ukungu $0.02 kwa lot
#
# Run ya kwanza kwa 0.01 ilitoa namba SHUFWA zote — 4, 6, 8, 10 — ambayo
# ndiyo saini ya ukungu huo, si ya bei ya broker. Kwa uamuzi wa Gotobi
# unaotegemea 9.3% kushuka hadi 8.0%, $1 kwa lot ni ~0.13 pips kwenye
# USDJPY: ukungu mkubwa kuliko tofauti inayoamuliwa.
VOLUME_DEFAULT = 0.10
VOLUME_MAX = 1.00      # kikomo kigumu; demo au la
DEVIATION = 20         # points; kujaza kwenye demo, si utafiti

# Retcodes zinazorudi mara nyingi. MT5 inarudisha namba pekee, na namba
# peke yake haisemi la kufanya — ndiyo maana jedwali hili lipo.
RETCODE = {
    10004: "REQUOTE — bei imebadilika; jaribu tena",
    10006: "REJECT — broker amekataa ombi",
    10013: "INVALID — ombi lina kigezo kisicho sahihi",
    10014: "INVALID_VOLUME — 0.01 haikubaliki kwa symbol hii",
    10015: "INVALID_PRICE",
    10016: "INVALID_STOPS",
    10018: "MARKET_CLOSED — soko limefungwa kwa symbol hii",
    10019: "NO_MONEY — salio halitoshi",
    10026: "SERVER_DISABLES_AT — AlgoTrading imezimwa na SERVER",
    10027: "CLIENT_DISABLES_AT — AlgoTrading imezimwa kwenye TERMINAL "
           "(kitufe cha toolbar, si Options)",
    10030: "INVALID_FILL — hakuna aina ya kujaza inayokubalika",
    10031: "CONNECTION — hakuna muunganisho na server",
}


def eleza(kod) -> str:
    return RETCODE.get(kod, str(kod))


def fungua_na_funga(mt5, jina: str, *, magic: int,
                    volume: float) -> dict:
    """Buy, kisha funga papo hapo. Inarudisha ticket ya position."""
    tick = subiri_tick(mt5, jina)
    if tick is None:
        return {"ok": False, "sababu": "hakuna quote"}

    ombi = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": jina, "volume": volume,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask,
        "deviation": DEVIATION, "magic": magic,
        "comment": "elitefx cost probe",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    r = mt5.order_send(ombi)
    if r is None or r.retcode != mt5.TRADE_RETCODE_DONE:
        kod = r.retcode if r else mt5.last_error()
        # IOC haikubaliki kwa broker wote; FOK na RETURN ndio mbadala.
        for mbadala in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
            ombi["type_filling"] = mbadala
            r = mt5.order_send(ombi)
            if r is not None and r.retcode == mt5.TRADE_RETCODE_DONE:
                break
        else:
            kod2 = r.retcode if r else mt5.last_error()
            return {"ok": False, "retcode": kod2,
                    "sababu": f"kufungua kumeshindwa: {eleza(kod)}"
                              + (f" · kisha {eleza(kod2)}"
                                 if kod2 != kod else "")}

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
                          f"{eleza(r2.retcode if r2 else mt5.last_error())} — "
                          f"funga ticket {p.ticket} kwa mkono kwenye MT5!"}
    return {"ok": True, "ticket_in": ticket_in, "position": p.ticket}


def deals_za_position(mt5, ticket: int):
    """Deals za position moja, **bila kutegemea saa**.

    `history_deals_get(from, to)` inachuja kwa saa ya SERVER. Kuuliza kwa
    dirisha la UTC kunakosa deals zote pale server iko UTC+2/+3: alama ya
    saa ya deal iko baada ya mwisho wa dirisha. Run ya kwanza ilipata deals
    22 na kuripoti jedwali tupu kwa sababu hii, na ikaita utupu huo
    "commission ni sifuri" — kutokupata data kukiripotiwa kama kipimo.

    `position=` haichuji kwa saa hata kidogo.
    """
    return mt5.history_deals_get(position=ticket) or ()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nakubali", action="store_true",
                    help="tuma orders kweli (DEMO pekee)")
    ap.add_argument("--volume", type=float, default=VOLUME_DEFAULT,
                    help=f"lots kwa kila symbol (kikomo {VOLUME_MAX}); "
                         "kubwa = kipimo sahihi zaidi")
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
    # Ruhusa MBILI tofauti, na moja ilitosha kupitisha orders 12 zilizokufa:
    #   account_info.trade_allowed   — ruhusa ya SERVER kwa akaunti hii
    #   terminal_info.trade_allowed  — kitufe cha "Algo Trading" cha TOOLBAR
    # Ya pili ndiyo iliyorudisha 10027 kwenye run ya kwanza. Zinaangaliwa
    # KABLA ya order yoyote: kutuma 12 zinazojulikana zitakataliwa si kipimo,
    # ni kelele.
    term = mt5.terminal_info()
    if term is not None and not term.trade_allowed:
        print("\nALGO TRADING IMEZIMWA KWENYE TERMINAL (retcode 10027).")
        print("Bonyeza kitufe cha **Algo Trading** kwenye toolbar ya MT5")
        print("(au Ctrl+E). Kikiwa kimewashwa ni cha kijani, kikiwa kimezimwa")
        print("kina duara jekundu. Si kisanduku cha Tools → Options —")
        print("hicho ni kingine, na kinaweza kuwa kimewashwa tayari.")
        mt5.shutdown()
        return 2
    if not acc.trade_allowed:
        print("\nAkaunti haina ruhusa ya kutrade kutoka kwa SERVER")
        print("(`account_info.trade_allowed` ni False). Akaunti ya kusoma")
        print("pekee, au investor password badala ya ya kawaida.")
        mt5.shutdown()
        return 2

    vol = round(float(args.volume), 2)
    if not 0 < vol <= VOLUME_MAX:
        print(f"\nvolume {vol} iko nje ya (0, {VOLUME_MAX}]. Kikomo ni kigumu.")
        mt5.shutdown()
        return 2

    teule = ([s.strip().upper() for s in args.symbols.split(",")]
             if args.symbols else list(SYMBOLS))
    print(f"   demo · {acc.currency} · symbols {len(teule)} · "
          f"volume {vol} kwa kila moja")
    print(f"   ukungu wa kipimo: ${0.02 / vol:.2f} kwa lot "
          f"(senti moja ÷ {vol})")
    print(f"   salio la bure ${acc.margin_free:,.2f} · position MOJA kwa "
          f"wakati (inafungwa kabla ya inayofuata)")

    if not args.nakubali:
        print("\n--nakubali HAIJATOLEWA: hakuna order itakayotumwa.")
        print(f"Ikitolewa, script itafungua na kufunga BUY ya lot {vol} kwa")
        print(f"kila symbol kati ya {len(teule)}, kisha itasoma commission")
        print("kutoka kwenye deals zake kwa ticket. Ni pesa ya demo.")
        mt5.shutdown()
        return 0

    magic = int(time.time()) % 1_000_000
    print(f"\n   magic {magic}\n")

    zilizofanyika, zilizoshindwa = [], []
    for msingi in teule:
        jina = tafuta_symbol(mt5, msingi)
        if jina is None:
            zilizoshindwa.append((msingi, "haipo kwa broker huyu"))
            print(f"   {msingi:<8} haipo")
            continue
        mt5.symbol_select(jina, True)
        # Margin inaangaliwa KABLA ya kutuma: NO_MONEY baada ya order
        # inachanganya "hatujui" na "haiwezekani".
        tick = subiri_tick(mt5, jina)
        if tick is not None:
            lazima = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, jina, vol,
                                           tick.ask)
            hai = mt5.account_info().margin_free
            if lazima is not None and lazima > hai:
                zilizoshindwa.append(
                    (msingi, f"margin ${lazima:,.0f} > bure ${hai:,.0f} — "
                             f"punguza --volume"))
                print(f"   {msingi:<8} margin haitoshi (${lazima:,.0f})")
                continue
        r = fungua_na_funga(mt5, jina, magic=magic, volume=vol)
        if r["ok"]:
            zilizofanyika.append((msingi, jina, r["position"]))
            print(f"   {msingi:<8} imefunguliwa na kufungwa "
                  f"(position {r['position']})")
        else:
            zilizoshindwa.append((msingi, r["sababu"]))
            print(f"   {msingi:<8} {r['sababu']}")

    if not zilizofanyika:
        print("\nHAKUNA DEAL. Commission haijapimwa.")
        # Symbols zote zikishindwa kwa sababu ile ile, tatizo ni la mfumo
        # (ruhusa, muunganisho, soko), si la symbol.
        sababu = {s for _, s in zilizoshindwa}
        if len(sababu) == 1:
            print(f"   Zote 12 kwa sababu ile ile: {sababu.pop()}")
            print("   Tatizo ni la mfumo, si la symbol.")
        mt5.shutdown()
        return 2

    # ---- soma commission kwa POSITION, si kwa saa ----
    time.sleep(1.0)
    kwa_symbol: dict[str, dict] = {}
    jumla_deals = 0
    for msingi, jina, ticket in zilizofanyika:
        j = kwa_symbol.setdefault(msingi, {"commission": 0.0, "vol_in": 0.0,
                                           "n": 0, "profit": 0.0,
                                           "swap": 0.0, "position": ticket})
        for d in deals_za_position(mt5, ticket):
            jumla_deals += 1
            j["commission"] += float(d.commission)
            j["profit"] += float(d.profit)
            j["swap"] += float(d.swap)
            j["n"] += 1
            if d.entry in (0, 2):
                j["vol_in"] += float(d.volume)

    # **Utupu si sifuri.** Hii ndiyo tofauti iliyokosekana kwenye run ya
    # kwanza: jedwali tupu liliripotiwa kama "commission ni sifuri".
    if jumla_deals == 0:
        print("\n" + "=" * 74)
        print("HAKUNA DEAL ILIYOSOMEKA")
        print("=" * 74)
        print(f"   Positions {len(zilizofanyika)} zilifunguliwa na kufungwa,")
        print("   lakini `history_deals_get` haikurudisha deal hata moja.")
        print("   HII SI KIPIMO CHA SIFURI — ni kushindwa kusoma historia.")
        print("   Commission INABAKI HAIJAPIMWA.")
        mt5.shutdown()
        return 2

    print("\n" + "=" * 74)
    print("COMMISSION ILIYOPIMWA (round-turn kwa lot 1)")
    print("=" * 74)
    print(f"   {'symbol':<10} {'$/lot RT':>10} {'deals':>7} {'lots':>7} "
          f"{'spread $':>10} {'swap $':>8}")
    matokeo = {}
    for sym, j in sorted(kwa_symbol.items()):
        if j["vol_in"] <= 0:
            print(f"   {sym:<10} {'—':>10} {j['n']:>7} "
                  f"{'hakuna deal ya kufungua':>26}")
            continue
        rt = abs(j["commission"]) / j["vol_in"]
        matokeo[sym] = {"commission_usd_round_turn": rt, "deals": j["n"],
                        "lots_in": j["vol_in"], "spread_cost_usd": j["profit"],
                        "swap_usd": j["swap"], "position": j["position"]}
        print(f"   {sym:<10} {rt:>10.2f} {j['n']:>7} {j['vol_in']:>7.2f} "
              f"{j['profit']:>10.2f} {j['swap']:>8.2f}")

    jumla = sum(v["commission_usd_round_turn"] for v in matokeo.values())
    hatua = 0.02 / vol
    print(f"\n   deals zilizosomwa {jumla_deals} · "
          f"symbols zenye kipimo {len(matokeo)}")
    print(f"   ukungu wa kipimo ±${hatua / 2:.2f} kwa lot "
          f"(hatua ${hatua:.2f})")
    if hatua >= 0.5:
        print("   ONYO: ukungu ni mkubwa. Endesha kwa --volume kubwa zaidi")
        print("   kabla ya kutumia namba hizi kwenye uamuzi wowote.")
    if jumla == 0:
        print("\n   COMMISSION NI SIFURI KWENYE AKAUNTI HII YA DEMO.")
        print(f"   Ni kipimo halisi: deals {jumla_deals} zimesomwa na kila")
        print("   moja ina `commission` ya 0.00.")
        print("\n   LAKINI HAITHIBITISHI LIVE. Broker wengi wanaweka")
        print("   commission ya demo kuwa sifuri hata pale live inatoza.")
        print("   Kwa sheria ya §13.10 iliyoandikwa kabla ya kuendesha:")
        print("   `broker_costs.yaml` HAIBADILIKI, `7.0` inabaki DHANA, na")
        print("   Gotobi inabaki `UNCERTAIN`.")
    else:
        print("\n   Ni kipimo cha AINA HII ya akaunti (demo). Inahitaji")
        print("   kuthibitishwa kwenye akaunti halisi kabla ya §10 hatua 5.")

    matokeo_yote = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "trade_mode": int(acc.trade_mode), "currency": acc.currency,
        "volume": vol, "magic": magic,
        "resolution_usd_per_lot": 0.02 / vol,
        "deals_read": jumla_deals,
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
