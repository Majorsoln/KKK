"""Backtest Engine — DOCTRINE §11, §1.2, R12, R13, R17, R19.

Inaunganisha vipande vilivyokwisha jengwa:

```
signals (evaluate) → RCE CHECK (rce_stage) → EXECUTION (execution) → ledger
                            │
                     salio linabadilika
                            │
                     budget ya signal INAYOFUATA
```

---

**Kwa nini ni mfuatano, si vectorised.**

§1.2: `net_pips_month` haitegemei mpangilio; `net_account_return_month`
**inategemea**, kupitia mnyororo wa RCE:

```
DD ↑  →  budget ↓  →  risk_per_trade ↓  →  lots ↓
```

Seti ile ile ya trades — 25 za −30 pips na 13 za +60 pips, jumla +30 pips —
inatoa **−$72.21** au **+$52.68** kutegemea mpangilio pekee. Ishara inageuka.

Kwa hiyo salio linahesabiwa trade baada ya trade, na kila trade inaulizwa RCE
kwa hali ya akaunti **ya wakati huo**. Kuhesabu lots mara moja kwa salio la
mwanzo kungefanya `net_account_return_month` isiwe na maana yoyote — na ndiyo
metric yenye mamlaka (R17).

---

**Trade zinazopishana zinahesabiwa kwa RCE, si kwa sheria yangu.**

Signal ikiwaka wakati trade nyingine iko wazi, idadi ya positions wazi
inapelekwa kwa RCE, na `max_open_trades` yake inaamua. Kuamua hapa kungekuwa
sheria ya pili ya hatari inayoshindana na ya kwanza (R12).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from src.rce.budget import AccountState
from src.rce.cost import SymbolSpec
from src.rce.engine import MarketContext, Proposal

from .execution import ExecSpec, TradePath, execute
from .ledger import FILL, NO_FILL, PASS, Attempt, Ledger
from .rce_stage import check


class BacktestError(RuntimeError):
    """Backtest haiwezi kuendeshwa kama ilivyoombwa."""


@dataclass(frozen=True)
class BrokerFacts:
    """Ukweli wa broker — unatoka MT5 na `broker_costs.yaml`, si kubuniwa."""

    spec: SymbolSpec
    pip_value_acct: float
    commission_round_turn: float
    swap_pips_per_night: float = 0.0

    @property
    def symbol(self) -> str:
        return self.spec.symbol


@dataclass(frozen=True)
class Trade:
    """Trade moja iliyofungwa: path yake, ukubwa wake, na athari yake kwa salio."""

    attempt: Attempt
    path: TradePath
    lots: float
    pnl_account: float
    balance_after: float

    @property
    def net_pips(self) -> float:
        return self.path.net_pips


@dataclass
class BacktestResult:
    """Matokeo ya strategy MOJA. Vipimo vyote vya §21 vinatoka hapa."""

    strategy_id: str
    symbol: str
    ledger: Ledger
    trades: list[Trade] = field(default_factory=list)
    starting_balance: float = 0.0
    n_signals_raw: int = 0

    # ---------------- mfululizo ----------------

    def monthly(self):
        """Mwezi kwa mwezi: pips, pesa, idadi ya trades (R8)."""
        import pandas as pd

        if not self.trades:
            return pd.DataFrame(columns=["net_pips", "pnl_account", "n_trades",
                                         "return_pct"])
        rows = pd.DataFrame({
            "muda": [t.path.exit_time for t in self.trades],
            "net_pips": [t.net_pips for t in self.trades],
            "pnl_account": [t.pnl_account for t in self.trades],
            "balance_before": [t.balance_after - t.pnl_account for t in self.trades],
        })
        # Mwezi unahesabiwa kwa UTC kwa makusudi (R8). `tz_localize(None)` baada
        # ya `tz_convert` ni kutupa tz **baada** ya kuitumia, si kuipuuza.
        rows["mwezi"] = (pd.DatetimeIndex(rows["muda"])
                         .tz_convert("UTC").tz_localize(None).to_period("M"))

        out = rows.groupby("mwezi").agg(
            net_pips=("net_pips", "sum"),
            pnl_account=("pnl_account", "sum"),
            n_trades=("net_pips", "size"),
            balance_open=("balance_before", "first"),
        )
        out["return_pct"] = out["pnl_account"] / out["balance_open"]
        return out

    def equity(self):
        import pandas as pd

        if not self.trades:
            return pd.Series(dtype=float)
        return pd.Series(
            [t.balance_after for t in self.trades],
            index=pd.DatetimeIndex([t.path.exit_time for t in self.trades]),
        )

    # ---------------- vipimo (§21, §1.2) ----------------

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def total_pips(self) -> float:
        return float(sum(t.net_pips for t in self.trades))

    @property
    def total_account(self) -> float:
        return float(sum(t.pnl_account for t in self.trades))

    def metrics(self) -> dict[str, float]:
        """Vipimo vya §21 pamoja na PRIMARY mbili za §1.2."""
        import numpy as np

        kwa_mwezi = self.monthly()
        if kwa_mwezi.empty:
            return {
                "net_pips_month": float("nan"),
                "net_account_return_month": float("nan"),
                "profitable_month_fraction": float("nan"),
                "sharpe": float("nan"), "profit_factor": float("nan"),
                "max_drawdown": float("nan"), "fill_rate": self.ledger.fill_rate,
                "n_trades": 0, "n_months": 0, "path_dependence": False,
                "variants_tested": 1,
            }

        pips = kwa_mwezi["net_pips"].to_numpy(dtype=float)
        ret = kwa_mwezi["return_pct"].to_numpy(dtype=float)

        sd = float(ret.std(ddof=1)) if len(ret) > 1 else 0.0
        sharpe = float(ret.mean() / sd * np.sqrt(12)) if sd > 0 else 0.0

        faida = float(sum(t.pnl_account for t in self.trades if t.pnl_account > 0))
        hasara = float(-sum(t.pnl_account for t in self.trades if t.pnl_account < 0))
        pf = faida / hasara if hasara > 0 else float("inf") if faida > 0 else 0.0

        return {
            "net_pips_month": float(pips.mean()),
            "net_account_return_month": float(ret.mean()),
            "profitable_month_fraction": float((pips > 0).mean()),
            "sharpe": sharpe,
            "profit_factor": pf,
            "max_drawdown": self.max_drawdown(),
            "fill_rate": self.ledger.fill_rate,
            "n_trades": self.n_trades,
            "n_months": len(kwa_mwezi),
            # §1.2: onyo lililoandikwa, si kufeli peke yake.
            "path_dependence": bool(
                (self.total_pips > 0) != (self.total_account > 0)
            ),
            "variants_tested": 1,
        }

    def max_drawdown(self) -> float:
        """Kushuka kukubwa zaidi kutoka kilele, kwa **pesa**. Chanya = kushuka."""
        import numpy as np

        eq = self.equity()
        if eq.empty:
            return float("nan")
        thamani = np.concatenate([[self.starting_balance], eq.to_numpy(dtype=float)])
        kilele = np.maximum.accumulate(thamani)
        return float((kilele - thamani).max())

    # ---------------- kuripoti ----------------

    def render(self) -> str:
        m = self.metrics()
        onyo = "  PATH_DEPENDENCE" if m["path_dependence"] else ""
        return (
            f"{self.strategy_id}  signals {self.n_signals_raw:,} → "
            f"trades {self.n_trades:,}\n"
            f"   pips/mwezi {m['net_pips_month']:>8.2f} · "
            f"return/mwezi {m['net_account_return_month']:>7.3%} · "
            f"miezi yenye faida {m['profitable_month_fraction']:>5.1%}{onyo}\n"
            f"   sharpe {m['sharpe']:>5.2f} · PF {m['profit_factor']:>5.2f} · "
            f"DD ${m['max_drawdown']:>8.2f} · fill_rate {m['fill_rate']:>5.1%}\n"
            f"   {self.ledger.render()}"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id, "symbol": self.symbol,
            "starting_balance": self.starting_balance,
            "n_signals_raw": self.n_signals_raw,
            "metrics": self.metrics(),
            "by_outcome": self.ledger.by_outcome(),
        }


# ===========================================================================
# Uendeshaji
# ===========================================================================


def run(strategy, features, ticks, *, cfg_risk, broker: BrokerFacts,
        timeframe: str, day_tz: str = "UTC",
        starting_balance: float | None = None,
        h1_spreads: Sequence[float] | None = None,
        m5_spreads: Sequence[float] | None = None) -> BacktestResult:
    """Endesha strategy moja juu ya features na ticks zake.

    `h1_spreads`/`m5_spreads` zinapelekwa kwa RCE kama zilivyo — RCE ndiyo
    inayoamua jinsi ya kuzitumia (R12).
    """
    import numpy as np
    import pandas as pd

    from src.discovery.evaluate import signals as tafuta_signals

    sig = tafuta_signals(strategy, features, timeframe=timeframe, day_tz=day_tz)
    matokeo = BacktestResult(
        strategy_id=strategy.strategy_id, symbol=strategy.symbol,
        ledger=Ledger(),
        starting_balance=float(
            starting_balance if starting_balance is not None
            else cfg_risk.get("base_balance")
        ),
        n_signals_raw=sig.n_signals,
    )
    if sig.n_signals == 0:
        return matokeo

    stamps = pd.DatetimeIndex(pd.to_datetime(ticks["timestamp"], utc=True)).as_unit("ns")
    stamps_ns = stamps.view("int64")

    spreads_h1 = list(h1_spreads) if h1_spreads is not None else [1.0] * 100
    spreads_m5 = list(m5_spreads) if m5_spreads is not None else [1.0] * 288

    # ATR ya kila bar inahitajika kwa SL/TP za `atr_mult`; index ni mwanzo wa bar
    # wakati signal ni mwisho wake, kwa hiyo tunaunganisha kwa nafasi.
    atr_pips = features["ATR_pips"] if "ATR_pips" in features.columns else None
    ends = pd.DatetimeIndex(_bar_ends_for(features, timeframe, day_tz))
    atr_kwa_muda = (
        pd.Series(atr_pips.to_numpy(dtype=float), index=ends) if atr_pips is not None
        else None
    )

    salio = matokeo.starting_balance
    wazi: list[Trade] = []
    zilizofungwa: list[Trade] = []
    leo = None
    faida_leo = hasara_leo = 0.0

    for muda in sig.times:
        # ---- funga trades zilizofika mwisho kabla ya signal hii ----
        bado: list[Trade] = []
        for t in sorted(wazi, key=lambda x: x.path.exit_time):
            if t.path.exit_time <= muda:
                salio += t.pnl_account
                zilizofungwa.append(t)
                faida_leo, hasara_leo, leo = _sasisha_siku(
                    t.path.exit_time, t.pnl_account, faida_leo, hasara_leo, leo, day_tz
                )
            else:
                bado.append(t)
        wazi = bado

        # ---- SL/TP kwa pips ----
        atr = float(atr_kwa_muda.get(muda, float("nan"))) if atr_kwa_muda is not None \
            else float("nan")
        sl_pips = _kwa_pips(strategy.sl_type, strategy.sl_param, atr, None)
        tp_pips = _kwa_pips(strategy.tp_type, strategy.tp_param, atr, sl_pips)
        if not (sl_pips > 0 and tp_pips > 0):
            continue                       # ATR haijulikani bado — hakuna trade

        # ---- bei iliyoombwa: quote ya mwisho KABLA ya uamuzi ----
        idx = int(np.searchsorted(stamps_ns, muda.value, side="left"))
        if idx == 0 or idx >= len(stamps):
            continue
        bid = float(ticks["bid"].iloc[idx - 1])
        ask = float(ticks["ask"].iloc[idx - 1])
        entry = ask if strategy.direction.upper() == "BUY" else bid

        # ---- hatua 1: RCE CHECK (R19) ----
        ctx = MarketContext(
            account=AccountState(
                current_balance=salio, today_profit=faida_leo, today_loss=hasara_leo,
                open_positions=len(wazi),
            ),
            spec=broker.spec, h1_spreads=spreads_h1, m5_spreads=spreads_m5,
            pip_value_acct=broker.pip_value_acct,
            commission_round_turn=broker.commission_round_turn,
            open_symbols=tuple(t.attempt.symbol for t in wazi),
            now=muda.to_pydatetime(),
        )
        proposal = Proposal(symbol=strategy.symbol, direction=strategy.direction,
                            entry=entry, sl_pips=sl_pips, tp_pips=tp_pips)
        attempt = check(cfg_risk, proposal, ctx, signal_time=muda, requested_price=entry)

        if attempt.rce_outcome != PASS:
            matokeo.ledger.add(attempt)
            continue

        # ---- hatua 2: EXECUTION ----
        spec_exec = ExecSpec(
            symbol=strategy.symbol, direction=strategy.direction,
            sl_pips=sl_pips, tp_pips=tp_pips,
            deviation_pips=_cap(cfg_risk, strategy.symbol),
            commission_pips=_commission_pips(broker),
            time_stop_minutes=_time_stop_minutes(strategy, timeframe),
            swap_pips_per_night=broker.swap_pips_per_night,
        )
        kipande = _slice(ticks, stamps_ns, muda, spec_exec.time_stop_minutes)
        path = execute(kipande, spec_exec, signal_time=muda, requested_price=entry)

        matokeo.ledger.add(_na_utekelezaji(attempt, path))
        if path.outcome != FILL or not path.resolved:
            continue

        pnl = path.net_pips * broker.pip_value_acct * attempt.allowed_lots
        wazi.append(Trade(attempt=attempt, path=path, lots=attempt.allowed_lots,
                          pnl_account=pnl, balance_after=float("nan")))

    # `balance_after` inahesabiwa upya baada ya kupanga kwa muda wa KUFUNGWA —
    # trades zinazopishana zinafunguliwa kwa mpangilio mmoja na kufungwa kwa
    # mwingine, na equity ni ya wakati wa kufungwa.
    matokeo.trades = _panga_upya(matokeo, zilizofungwa + wazi)
    return matokeo


# ===========================================================================
# Ndani
# ===========================================================================


def _bar_ends_for(features, timeframe: str, day_tz: str):
    from src.data.bars import bar_ends

    return bar_ends(features.index, timeframe, day_tz)


def _kwa_pips(aina: str, param: float, atr: float, sl_pips: float | None) -> float:
    """SL/TP kwa pips. `rr` inategemea SL, kwa hiyo SL inahesabiwa kwanza."""
    import math

    if aina == "fixed_pips":
        return float(param)
    if aina == "atr_mult":
        return float(param) * atr if atr == atr else float("nan")   # NaN-safe
    if aina == "rr":
        return float(param) * sl_pips if sl_pips and not math.isnan(sl_pips) else float("nan")
    raise BacktestError(f"aina {aina!r} haijulikani")


def _cap(cfg_risk, symbol: str) -> float:
    from src.rce.cost import slippage_cap_pips

    return slippage_cap_pips("market", cfg_risk, symbol=symbol)


def _commission_pips(broker: BrokerFacts) -> float:
    from src.rce.cost import commission_pips

    return commission_pips(broker.commission_round_turn, broker.pip_value_acct)


def _time_stop_minutes(strategy, timeframe: str) -> int:
    from src.data.bars import DAILY, INTRADAY

    import pandas as pd

    urefu = pd.Timedelta(days=1) if timeframe == DAILY else pd.Timedelta(
        INTRADAY[timeframe])
    return int(strategy.time_stop_bars * urefu.total_seconds() / 60)


def _slice(ticks, stamps_ns, muda, time_stop_minutes: int):
    """Ticks za dirisha la trade pekee.

    Bila hii, kila trade ingetembea hadi mwisho wa data: `O(n)` kwa kila signal,
    yaani `O(n²)` kwa run nzima. Dirisha linaishia tick MOJA baada ya `deadline`
    ili `TIME_STOP` iweze kupatikana — ikikatwa kabla yake, trade ingeonekana
    `UNRESOLVED` badala ya kufungwa kwa muda.
    """
    import numpy as np

    lo = int(np.searchsorted(stamps_ns, muda.value, side="left"))
    deadline = muda.value + time_stop_minutes * 60 * 1_000_000_000
    hi = int(np.searchsorted(stamps_ns, deadline, side="left")) + 1
    return ticks.iloc[max(0, lo - 1): min(len(ticks), hi + 1)]


def _na_utekelezaji(attempt: Attempt, path: TradePath) -> Attempt:
    from dataclasses import replace

    return replace(
        attempt,
        execution_outcome=path.outcome,
        reject_reason=path.reject_reason,
        fill_price=path.entry_price,
        slippage_pips=path.fill_slippage_pips,
    )


def _sasisha_siku(muda, pnl: float, faida: float, hasara: float, leo, day_tz: str):
    """Faida/hasara ya leo zinarudishwa sifuri siku ya broker inapobadilika."""
    siku = muda.tz_convert(day_tz).date() if day_tz.upper() != "UTC" else muda.date()
    if leo is None or siku != leo:
        faida = hasara = 0.0
        leo = siku
    if pnl >= 0:
        faida += pnl
    else:
        hasara += -pnl
    return faida, hasara, leo


def _panga_upya(matokeo: BacktestResult, zote: list[Trade]) -> list[Trade]:
    """Trades zote kwa mpangilio wa KUFUNGWA, na salio likihesabiwa upya.

    Trade zinazopishana zinafunguliwa kwa mpangilio wa signal lakini zinafungwa
    kwa mpangilio mwingine. Equity ni ya wakati wa **kufungwa**, kwa hiyo
    `balance_after` inahesabiwa hapa — la sivyo `max_drawdown` ingekuwa ya
    mfuatano usiowahi kutokea.
    """
    zote = sorted(zote, key=lambda t: t.path.exit_time)
    salio = matokeo.starting_balance
    out: list[Trade] = []
    for t in zote:
        salio += t.pnl_account
        out.append(Trade(attempt=t.attempt, path=t.path, lots=t.lots,
                         pnl_account=t.pnl_account, balance_after=salio))
    return out
