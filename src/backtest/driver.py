"""Kuendesha familia yoyote kwenye ticks halisi — DOCTRINE §4, §6, §7, §9.

```
diski → madirisha → mwendo → stop → RCE → trades
      → LANGO LA §6 → curve ya siku → block bootstrap → `p`
```

**Mpangilio si wa bahati.** Malango ya §6 yanapimwa na kutangazwa **kabla**
`p` haijahesabiwa, na yakishindwa hii inasimama bila kuihesabu kabisa. Kuona
`p` kisha kuamua kama symbol inastahili ni jinsi toleo la kwanza lilivyoshindwa.

---

**Familia moja, code moja.** F0 ilikuwa na script yake; Gotobi ingekuwa na
yake, na baada ya miezi mitatu zingekuwa zimetofautiana kwa vitu vidogo
visivyoonekana — dirisha la MAE, mpangilio wa historia, mahali gharama
inapopimwa. Kila familia inatoa **sehemu chache zilizotangazwa**; kila kitu
kingine kiko hapa, mara moja.

Familia inatakiwa kutoa:

```
FAMILY · SYMBOL · PIP · POINT · CONTRACT_SIZE · WINDOW_SECONDS
DECLARATION · SL_MOVE_MULT · DECLARED_EDGE_PIPS
pip_value(mid) · eligible_days(days) · sessions_for(day) · baskets(days, move_pips=)
```

**`pip_value` ni function, si namba.** Kwa EURUSD ni `$10` daima; kwa USDJPY
ni `1000 ÷ bei`, inayobadilika kwa 37% kwenye sampuli yetu. Kuiweka namba
kungebadilisha `commission_pips` kwa kiasi kile kile, na lango la gharama
lingeamua kwa namba isiyo sahihi.

---

**Dirisha zima linasomwa**, si ncha pekee (§11): `runner.execute` inahitaji
njia ili kujua kama stop iligongwa. Kipande cha siku tano kinasomwa,
kinatumika, kinatupwa.
"""

from __future__ import annotations

import statistics as st
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Sequence

from src.analysis.curve import daily_r
from src.backtest.runner import execute
from src.data import ticks as TK
from src.events.clock import quotes
from src.families.qualify import Qualification, qualify
from src.rce.budget import AccountState
from src.rce.cost import SymbolSpec

# Siku kwa kila kipande. Dirisha zima linasomwa sasa (masaa 13 kwa siku kwa
# F0), kwa hiyo mwezi mmoja ungekuwa rows milioni 10+. Tano zinabaki chini ya
# milioni 2.5, na hakuna faili inayosomwa mara mbili — kila siku iko kwenye
# kipande kimoja tu.
DAYS_PER_CHUNK = 5


@dataclass
class RunSpec:
    """Vigezo vya akaunti na broker. Vinaingia kwenye ripoti kama vilivyo."""

    balance: float = 10_000.0
    # Commission ya broker kwa lot, round-turn, kwa sarafu ya **MSINGI**
    # (§13.10). `commission_usd` inaibadilisha kuwa dola kwa bei ya trade.
    commission_base_round_turn: float = 7.0
    volume_min: float = 0.01
    volume_step: float = 0.01
    volume_max: float = 50.0


@dataclass
class Sweep:
    """Kila kitu kilichotokea wakati wa kupita kwenye data."""

    trades: list = field(default_factory=list)
    moves: dict = field(default_factory=dict)
    signed: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    key_of: dict = field(default_factory=dict)
    seconds: float = 0.0

    @property
    def stopped(self) -> list:
        return [t for t in self.trades if t.stopped]

    @property
    def finished(self) -> list:
        """Zilizomaliza kwa saa. Ndizo pekee zenye spread ya kwenda-na-kurudi."""
        return [t for t in self.trades if not t.stopped]


def chunks(days: Sequence[date], *, size: int = DAYS_PER_CHUNK):
    return [list(days[i:i + size]) for i in range(0, len(days), size)]


def symbols_of(family) -> tuple[str, ...]:
    """Symbols zinazotradiwa — kutoka **tangazo**, si kutoka moduli.

    F1 ina `SYMBOLS` sita (mekanizimu, §6.1) lakini inatradia nne
    (`QUALIFIED`, §6.2). Tangazo ndilo lenye mamlaka: ndilo lililo-hash na
    kufungwa, na ndilo linalosema ni nini kilichoendeshwa. Kusoma `SYMBOLS`
    kungejaribu kusoma ticks za symbols zilizokataliwa na lango.
    """
    return tuple(family.DECLARATION.symbols)


def _pip(family, symbol: str) -> float:
    pips = getattr(family, "PIPS", None)
    return pips[symbol] if pips else family.PIP


def _point(family, symbol: str) -> float:
    points = getattr(family, "POINTS", None)
    return points[symbol] if points else family.POINT


def _pip_value(family, symbol: str, mid: float) -> float:
    try:
        return family.pip_value(symbol, mid)
    except TypeError:
        return family.pip_value(mid)


def commission_usd(symbol: str, mid: float, base_round_turn: float) -> float:
    """Commission ya round-turn kwa lot, kwa **dola**, kwa bei ya sasa.

    Broker anatoza kiasi kisichobadilika kwa sarafu ya **MSINGI**, si kwa
    dola (kipimo 2026-09-10, §13.10):

    ```
    USDJPY · USDCHF · USDCAD   msingi ni USD  →  7.00 hasa
    EURUSD                     msingi ni EUR  →  7.00 × EURUSD
    GBPUSD                     msingi ni GBP  →  7.00 × GBPUSD
    AUDUSD                     msingi ni AUD  →  7.00 × AUDUSD
    ```

    Kwa pairs zinazonukuliwa kwa dola, bei ya msingi **ni `mid` yenyewe** —
    hakuna data ya ziada inayohitajika. Ndiyo maana sheria hii inaweza
    kutumika ndani ya backtest bila kuongeza chanzo kipya.

    Namba iliyogandishwa ingekuwa imepitwa na wakati mara moja: EURUSD
    ilianzia 1.04 na kufika 1.25 kwenye sampuli yetu, tofauti ya **20%**
    kwenye commission.

    Cross (EURGBP, GBPJPY) inahitaji bei ya tatu ambayo backtest haisomi,
    kwa hiyo inakataliwa waziwazi badala ya kukadiriwa kimya. Hakuna
    familia inayoitrade.
    """
    if mid <= 0:
        raise ValueError(f"{symbol}: bei si chanya ({mid})")
    if symbol.startswith("USD"):
        return base_round_turn
    if symbol.endswith("USD"):
        return base_round_turn * mid
    raise ValueError(
        f"{symbol}: cross — commission inahitaji bei ya kubadilisha "
        f"{symbol[:3]} → USD, ambayo backtest haisomi")


def market(family, spec: RunSpec, *, symbol: str, spread_pips: float,
           mid: float) -> dict:
    """Kila kitu RCE inachohitaji, kikiwa kimepimwa kwenye bei ya sasa."""
    return {
        "spec": SymbolSpec(symbol=symbol, point=_point(family, symbol),
                           contract_size=family.CONTRACT_SIZE,
                           volume_min=spec.volume_min,
                           volume_step=spec.volume_step,
                           volume_max=spec.volume_max),
        "account": AccountState(current_balance=spec.balance, today_profit=0.0,
                                today_loss=0.0, open_positions=0),
        "h1_spreads": [spread_pips] * 120,
        "m5_spreads": [spread_pips] * 300,
        "pip_value_acct": _pip_value(family, symbol, mid),
        # Commission inahesabiwa HAPA, kabla ya RCE. RCE inapokea namba ya
        # dola iliyokwisha kubadilishwa — haijui chochote kuhusu sarafu ya
        # msingi, na haihitaji kujua.
        "commission_round_turn": commission_usd(
            symbol, mid, spec.commission_base_round_turn),
        "pip": _pip(family, symbol),
    }


def sweep(family, inv, days: Sequence[date], spec: RunSpec, *, cfg,
          progress=None, **basket_kwargs) -> Sweep:
    """Pita vipande vyote: quotes → mwendo → stop → kikapu → trade.

    `basket_kwargs` inapitishwa kwa `family.baskets` — ndipo F1 inapopokea
    `signal` yake. Familia zisizohitaji kitu cha ziada hazibadiliki.

    **Kikapu kinajengwa MARA MOJA kwa siku**, baada ya stop za `Measurement`
    zote kupatikana. Kwa F1 hilo ni la lazima: legs nne ni kikapu kimoja, na
    kujenga kwa kila leg peke yake kungetoa vikapu vinne vya leg moja —
    strategy tofauti kabisa, isiyosawazishwa.
    """
    zote = symbols_of(family)
    partitions = {s: inv.of(s) for s in zote}
    out = Sweep()
    historia: dict[str, list[float]] = {}
    t0 = time.time()

    for kundi in chunks(days):
        maombi: dict[str, list] = {s: [] for s in zote}
        for d in kundi:
            for m in family.measurements(d):
                urefu = int((m.exit_at - m.entry_at).total_seconds())
                maombi[m.symbol].append(
                    (m.entry_at, urefu + family.WINDOW_SECONDS))
        frames = {s: TK.read_windows(inv, s, maombi[s], partitions=partitions[s])
                  for s in zote if maombi[s]}

        for d in kundi:
            stops, mwendo_leo, kwa_dirisha = {}, {}, {}
            for m in family.measurements(d):
                frame = frames.get(m.symbol)
                if frame is None:
                    out.missing.append((d, m.key, "hakuna frame"))
                    continue
                try:
                    ndani = quotes(frame, m.entry_at, family.WINDOW_SECONDS)
                    nje = quotes(frame, m.exit_at, family.WINDOW_SECONDS)
                except Exception as exc:                       # noqa: BLE001
                    out.missing.append((d, m.key, str(exc)[:80]))
                    continue
                # Stop ya leo inatoka kwenye historia ya JANA. Inasomwa kabla
                # ya mwendo wa leo kuongezwa — hapo ndipo lookahead ingeingia.
                nyuma = historia.setdefault(m.key, [])
                stop = family.stop_from_history(nyuma)
                if stop is not None:
                    stops[(d, m.key)] = stop
                pip_hii = _pip(family, m.symbol)
                mwendo_leo[m.key] = (
                    family.session_move_pips(ndani, nje, pip=pip_hii),
                    family.signed_move_pips(ndani, nje, pip=pip_hii))
                # Ufunguo unatafutwa kwa DIRISHA, si kwa symbol: F0 ina legs
                # mbili za symbol ILE ILE kwa madirisha tofauti, na kutafuta
                # kwa symbol kungechagua leg A kwa vikapu vyote viwili.
                kwa_dirisha[(m.symbol, m.entry_at, m.exit_at)] = (m.key, ndani)

            if stops:
                vikapu = family.baskets([d], move_pips=stops, **basket_kwargs)
                for k in vikapu:
                    soko, ticks = {}, {}
                    for leg in k.legs:
                        pata = kwa_dirisha.get(
                            (leg.symbol, k.entry_at, k.planned_exit_at))
                        if pata is None:
                            continue
                        key, rejea = pata
                        soko[leg.symbol] = market(
                            family, spec, symbol=leg.symbol,
                            spread_pips=rejea.spread_pips(_pip(family, leg.symbol)),
                            mid=rejea.mid)
                        ticks[leg.symbol] = frames[leg.symbol]
                        out.key_of[(k.basket_id, leg.symbol)] = key
                    if len(soko) != len(k.legs):
                        out.rejected.append((d, k.basket_id, "quotes hazipo"))
                        continue
                    jibu = execute(k, cfg=cfg, ticks_by_symbol=ticks,
                                   market=soko,
                                   window_seconds=family.WINDOW_SECONDS,
                                   path_ticks=ticks)
                    if jibu.executed:
                        out.trades.extend(jibu.trades)
                    else:
                        out.rejected.append((d, k.basket_id, jibu.reason))

            for key, (kiasi, ishara) in mwendo_leo.items():
                out.moves[(d, key)] = kiasi
                out.signed[(d, key)] = ishara
                historia.setdefault(key, []).append(kiasi)

        if progress:
            progress(f"   {kundi[0]:%Y-%m-%d}  siku {len(kundi):>2}  "
                     f"trades {len(out.trades):>5,}  stop {len(out.stopped):>4,}")
    out.seconds = time.time() - t0
    return out


# ===========================================================================
# Vipimo na lango
# ===========================================================================


@dataclass
class Measured:
    """Vipimo vyote vinavyoingia kwenye lango la §6, kwa kila leg."""

    per_leg: dict
    worst_leg: str
    curve: Any
    gap: list

    @property
    def move_pips(self) -> float:
        return self.per_leg[self.worst_leg]["move_pips"]

    @property
    def sigma_pips(self) -> float:
        return self.per_leg[self.worst_leg]["sigma_pips"]

    @property
    def cost_pips(self) -> float:
        return self.per_leg[self.worst_leg]["cost_pips"]


def measure(family, sw: Sweep, days: Sequence[date]) -> Measured:
    """Vipimo kwa KILA leg peke yake.

    Legs za urefu tofauti zina `σ` tofauti (F0: masaa 9 dhidi ya 4.4), kwa
    hiyo uwiano wa gharama si mmoja. Kuchanganya kungefanya leg fupi ijifiche
    nyuma ya ndefu, na §6.2 inasema *"σ ya dirisha la kushikilia"*, si *"σ ya
    wastani wa familia"*.

    **`σ` inapimwa, haidhaniwi** (§13.10). Hadi 2026-09-10 ilihesabiwa kama
    `1.2533 × E|mwendo|` — kweli kwa normal pekee. Kwa mikia minene kigezo
    halisi ni kikubwa zaidi, kwa hiyo `σ` ilikuwa ndogo na lango la §6.2
    lilikuwa **kali kuliko lilivyotangazwa**. Namba zote mbili zinarudishwa
    ili tofauti ionekane; **iliyopimwa ndiyo inayoingia kwenye lango**.
    """
    kwa_leg: dict[str, dict] = {}
    for leg in sorted({l for (_, l) in sw.moves}):
        m = [v for (_, l), v in sw.moves.items() if l == leg]
        ishara = [v for (_, l), v in sw.signed.items() if l == leg]
        t_leg = [t for t in sw.finished
                 if sw.key_of.get((t.basket_id, t.symbol)) == leg]
        if not m or not t_leg:
            continue
        wastani = st.fmean(m)
        gharama = st.fmean(t.spread_realised_pips + t.commission_pips
                           for t in t_leg)
        # `σ` INAPIMWA, haihesabiwi kutoka `E|X|` (§13.10). Kigezo cha normal
        # `1.2533` kinabaki kama rejea pekee ili upotoshaji uonekane: uwiano
        # `kurtosis_hint` chini ya 1.0 ungemaanisha data nyembamba kuliko
        # normal, juu ya 1.0 ni mikia minene — na mikia minene ndiyo tuliyo
        # nayo (kugongwa kwa stop 1.83% dhidi ya 0.3% ya normal).
        sigma = st.stdev(ishara) if len(ishara) > 1 else float("nan")
        sigma_normal = wastani * family.MOVE_TO_SIGMA
        kwa_leg[leg] = {"move_pips": wastani, "sigma_pips": sigma,
                        "sigma_normal_pips": sigma_normal,
                        "kurtosis_hint": sigma / sigma_normal,
                        "drift_pips": st.fmean(ishara),
                        "cost_pips": gharama, "n": len(t_leg),
                        "n_moves": len(ishara),
                        "ratio": gharama / sigma,
                        "ratio_normal": gharama / sigma_normal}
    if not kwa_leg:
        raise RuntimeError("hakuna leg yenye trade — hakuna cha kupima")

    return Measured(
        per_leg=kwa_leg,
        worst_leg=max(kwa_leg, key=lambda k: kwa_leg[k]["ratio"]),
        curve=daily_r(sw.trades, days=list(days)),
        gap=sorted(t.spread_gap_pips for t in sw.finished),
    )


def sharpe_per_day(family, mz: Measured, *, edge_pips: float,
                   n_legs: int) -> float:
    """Sharpe-kwa-siku **ILIYOTANGAZWA**, si iliyopatikana.

    Inatokana na edge ya §9 (iliyoandikwa kabla) na volatility **iliyopimwa**
    — si kwenye faida iliyotokea. Ikitoka kwenye faida, lango la 6.3
    lingekuwa likijipima lenyewe: familia iliyofanya vizuri ingedai kwamba
    ilihitaji matukio machache, na kila kitu kingepita.
    """
    sl = family.SL_MOVE_MULT * mz.move_pips
    kikomo = sl + mz.cost_pips
    edge_R = edge_pips / kikomo
    sigma_R = mz.sigma_pips / kikomo
    return (n_legs * edge_R) / (sigma_R * (n_legs ** 0.5))


def gate(family, mz: Measured, *, edge_pips: float, n_legs: int
         ) -> tuple[Qualification, float]:
    """Lango la §6, likiwa limepimwa kwa leg mbaya kabisa."""
    s = sharpe_per_day(family, mz, edge_pips=edge_pips, n_legs=n_legs)
    q = qualify(
        family.FAMILY, mz.worst_leg,
        mechanism_ok=True, mechanism_note=family.DECLARATION.source,
        cost_pips=mz.cost_pips, sigma_pips=mz.sigma_pips,
        n_events=mz.curve.n_active, sharpe_per_event=s,
    )
    return q, s


__all__ = ["DAYS_PER_CHUNK", "RunSpec", "Sweep", "Measured", "chunks",
           "symbols_of",
           "market", "sweep", "measure", "sharpe_per_day", "gate"]
