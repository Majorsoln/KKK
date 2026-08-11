"""DF-09/10/11/21 + K1-07 — L4: labels nne kwa PATH YA TICKS (spec §5).

Kwa nini ticks: bar inaonyesha kwamba high na low zote ziligusa — **haisemi ipi
iligusa kwanza**. Hata ndani ya M1 moja mpangilio wa touch unaweza kugeuza
label. Ticks ndizo pekee zinazoutatua kwa uhakika.

Mikataba ya bei (DF-21, PD 2026-08-07):
* **Barrier path (L-B):** bei ya TRADE. BUY inafunga kwa bid → SL na TP zote
  kwa **bid**; SELL kwa **ask**. Entry ni upande wa kununulia (BUY: ask).
  Spread inaingia kwenye path **mara moja** — hapa.
* **Quantile (L-A):** **MID** entry na exit. L-A inapendekeza, haihukumu (S1);
  spread ishaingia kwenye path (hapa juu) na kwenye malipo (RCE §3) — kuiweka
  pia L-A ni kuihesabu mara tatu.
* **Tie-break:** bei ya kwanza baada ya gap ikifunika SL na TP kwa pamoja →
  **SL kwanza.** Live, bei inayoruka mipaka yote miwili inakutana na stop
  order upande mbaya kabla ya chochote. Mzunguko unarekodiwa (R1: >1% → PD).
* **Gap-honest:** stop ni TOUCH kwenye bei ya kwanza baada ya gap, si close.

Utekelezaji: prefix min/max ya path + searchsorted — O(n) mara moja kwa kila
decision point, kisha O(log n) kwa kila barrier. Grid nzima ya 5×5 inasoma
path ILE ILE moja; hakuna mzunguko wa Python kwenye ticks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

# Madarasa ya matokeo ya barrier (§5.2): timeout si takataka — ni darasa.
TP_FIRST = 1
SL_FIRST = 0
TIMEOUT = 2

# Muundo wa matokeo ya labels — unaingia dataset_id (§8).
LABEL_SCHEMA_VERSION = 1


@dataclass
class BarrierCell:
    """Matokeo ya cell moja ya grid (sl_atr, tp_atr) kwa decision point moja."""

    sl_atr: float
    tp_atr: float
    outcome: int                      # TP_FIRST · SL_FIRST · TIMEOUT
    tie_break: bool = False           # gap ilifunika zote mbili → SL kwanza
    touch_index: int | None = None    # tick iliyotatua (None kwa timeout)
    timeout_return_r: float | None = None  # E[R|timeout] — R units (÷ sl_atr)

    def to_json(self) -> dict[str, Any]:
        return {
            "sl_atr": self.sl_atr,
            "tp_atr": self.tp_atr,
            "outcome": self.outcome,
            "tie_break": self.tie_break,
            "timeout_return_r": self.timeout_return_r,
        }


@dataclass
class PointLabels:
    """Labels ZOTE za decision point moja — grid ya L-B + L-A + malighafi."""

    decision_time: pd.Timestamp
    direction: int                    # +1 BUY · −1 SELL
    entry_trade: float                # BUY: ask ya tick ya kwanza · SELL: bid
    entry_mid: float
    atr_price: float                  # ATR14 units za bei (mid)
    horizon_end: pd.Timestamp
    terminal_mid: float | None        # mid ya mwisho ndani ya horizon
    quantile_y: float | None          # L-A: log(midH/mid0) ÷ (ATR/mid0) — MID
    terminal_atr: float | None        # mwendo wa horizon kwa ATR, ISHARA ya trade
    cells: list[BarrierCell] = field(default_factory=list)
    ticks_seen: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "decision_time": self.decision_time.isoformat(),
            "direction": self.direction,
            "entry_trade": self.entry_trade,
            "entry_mid": self.entry_mid,
            "atr_price": self.atr_price,
            "horizon_end": self.horizon_end.isoformat(),
            "quantile_y": self.quantile_y,
            "terminal_atr": self.terminal_atr,
            "ticks_seen": self.ticks_seen,
            "cells": [c.to_json() for c in self.cells],
        }


def _first_leq(prefix_min: np.ndarray, price: float) -> int:
    """Index ya kwanza ambapo `prefix_min ≤ price` (len = haipo).

    `prefix_min` haipandi kamwe, kwa hiyo `-prefix_min` haishuki — na
    searchsorted inafanya kazi. O(log n) badala ya scan.
    """
    return int(np.searchsorted(-prefix_min, -price, side="left"))


def _first_geq(prefix_max: np.ndarray, price: float) -> int:
    """Index ya kwanza ambapo `prefix_max ≥ price` (len = haipo)."""
    return int(np.searchsorted(prefix_max, price, side="left"))


def epoch_us(stamps: pd.Series) -> np.ndarray:
    """Timestamps → µs za epoch (int64).

    Ulinganisho unafanyika kwa int64, si datetime64: timestamps za tz-aware
    hazilinganishwi na numpy moja kwa moja (T2 ilianguka hapa siku ya kwanza),
    na int64 ni sawa kwa matoleo yote mawili ya precision (§2.1).
    """
    return stamps.astype("datetime64[us, UTC]").astype("int64").to_numpy()


def resolve_point(
    ticks: pd.DataFrame,
    decision_time: pd.Timestamp,
    horizon_end: pd.Timestamp,
    direction: int,
    atr_price: float,
    sl_grid: list[float],
    tp_grid: list[float],
) -> PointLabels | None:
    """Grid nzima ya barrier + L-A kwa decision point MOJA (njia ya DataFrame).

    Rahisi kusoma na kujaribu. Kwa kazi ya decision points 52,000 tumia
    `resolve_arrays` — hii inabadilisha timestamps kuwa int64 **kila wito**,
    ambayo ni O(n) juu ya buffer nzima; kwa buffer ya ticks milioni 13 na
    points 4,400 hiyo peke yake ingekuwa siku, si masaa.
    """
    return resolve_arrays(
        epoch_us(ticks["timestamp"]),
        ticks["bid"].to_numpy(),
        ticks["ask"].to_numpy(),
        decision_time,
        horizon_end,
        direction,
        atr_price,
        sl_grid,
        tp_grid,
    )


def resolve_arrays(
    stamps: np.ndarray,
    bid_all: np.ndarray,
    ask_all: np.ndarray,
    decision_time: pd.Timestamp,
    horizon_end: pd.Timestamp,
    direction: int,
    atr_price: float,
    sl_grid: list[float],
    tp_grid: list[float],
) -> PointLabels | None:
    """Kiini: arrays zilizoshaandaliwa mara moja kwa buffer nzima.

    `stamps` ni µs za epoch (`epoch_us`), zikiwa zimepangwa. Dirisha ni
    `[decision_time, horizon_end]`; hakuna tick humo → None (hakuna soko =
    hakuna label; §5.5 inakataza data baada ya t+H, na kubuni entry ni
    marufuku).
    """
    if direction not in (1, -1):
        raise ValueError(f"direction lazima iwe +1/-1, si {direction!r}")
    if not atr_price or atr_price <= 0 or np.isnan(atr_price):
        return None

    lo = int(np.searchsorted(stamps, pd.Timestamp(decision_time).value // 1_000, side="left"))
    hi = int(np.searchsorted(stamps, pd.Timestamp(horizon_end).value // 1_000, side="right"))
    if lo >= hi:
        return None

    bid = bid_all[lo:hi]
    ask = ask_all[lo:hi]

    entry_trade = float(ask[0] if direction == 1 else bid[0])
    entry_mid = float((bid[0] + ask[0]) / 2.0)
    terminal_mid = float((bid[-1] + ask[-1]) / 2.0)

    # Path ya kufungia: BUY unafunga kwa BID (SL na TP zote); SELL kwa ASK.
    path = bid if direction == 1 else ask
    prefix_min = np.minimum.accumulate(path)
    prefix_max = np.maximum.accumulate(path)

    cells: list[BarrierCell] = []
    # Mwendo wa mwisho kwa ATR, ukiwa na ISHARA ya trade: +1 = trade ilishinda.
    terminal_atr = direction * (terminal_mid - entry_mid) / atr_price
    for sl_atr in sl_grid:
        if direction == 1:
            sl_idx = _first_leq(prefix_min, entry_trade - sl_atr * atr_price)
        else:
            sl_idx = _first_geq(prefix_max, entry_trade + sl_atr * atr_price)
        for tp_atr in tp_grid:
            if direction == 1:
                tp_idx = _first_geq(prefix_max, entry_trade + tp_atr * atr_price)
            else:
                tp_idx = _first_leq(prefix_min, entry_trade - tp_atr * atr_price)

            n = len(path)
            if sl_idx >= n and tp_idx >= n:
                cells.append(
                    BarrierCell(
                        sl_atr, tp_atr, TIMEOUT,
                        timeout_return_r=float(terminal_atr / sl_atr),
                    )
                )
            elif tp_idx < sl_idx:
                cells.append(BarrierCell(sl_atr, tp_atr, TP_FIRST, touch_index=tp_idx))
            elif sl_idx < tp_idx:
                cells.append(BarrierCell(sl_atr, tp_atr, SL_FIRST, touch_index=sl_idx))
            else:
                # Tick ILE ILE inafunika zote mbili — gap ya wikendi/habari.
                # SL kwanza (DF-21): live, stop inatekelezwa upande mbaya kwanza.
                cells.append(
                    BarrierCell(sl_atr, tp_atr, SL_FIRST, tie_break=True, touch_index=sl_idx)
                )

    # L-A (§5.1): MID pekee, bila mwelekeo — kipimo cha MWENDO WA SOKO.
    # ATR inagawanywa kwa bei ili yote yawe scale-free (log-return ÷ ATR-return).
    quantile_y = float(np.log(terminal_mid / entry_mid) / (atr_price / entry_mid))

    return PointLabels(
        decision_time=pd.Timestamp(decision_time),
        direction=direction,
        entry_trade=entry_trade,
        entry_mid=entry_mid,
        atr_price=float(atr_price),
        horizon_end=pd.Timestamp(horizon_end),
        terminal_mid=terminal_mid,
        quantile_y=quantile_y,
        terminal_atr=float(terminal_atr),
        cells=cells,
        ticks_seen=hi - lo,
    )


# --------------------------------------------------------------------------
# L-C — FILL bootstrap (K1-07, spec §5.3)
# --------------------------------------------------------------------------

MARKET_FILL_PRIOR = 0.98  # §5.3: market orders — latency ya live haikisiki kwa historia


@dataclass
class FillProbe:
    filled: bool
    slippage_pips: float | None = None
    at_index: int | None = None
    source: str = "tick_path"  # au "prior" kwa market


def fill_probe(
    ticks: pd.DataFrame,
    side: int,                 # +1 BUY · −1 SELL
    order_type: str,           # market · stop · limit
    price: float,
    cap_pips: float,
    pip: float,
) -> FillProbe:
    """Je order ingejazwa ndani ya `price ± cap` kabla ya bei kupita? (§5.3)

    Stop/limit: path ya ticks inajibu swali sahihi. Market: kutojazwa live
    kunatokana na latency/liquidity ya wakati ule — historia haiwezi kukisia;
    prior ya juu + calibration ya demo/live (§5.3, kwa makusudi si path).
    """
    if order_type == "market":
        return FillProbe(filled=True, slippage_pips=0.0, source="prior")
    if order_type not in ("stop", "limit"):
        raise ValueError(f"aina ya order haijulikani: {order_type!r}")

    # BUY inajazwa kwa ASK, SELL kwa BID — upande unaonunulika.
    path = ticks["ask"].to_numpy() if side == 1 else ticks["bid"].to_numpy()
    if len(path) == 0:
        return FillProbe(filled=False)

    if order_type == "limit":
        # BUY limit @X: bei ipatikane ≤ X (SELL: ≥ X). Slippage haiwezi kuwa chanya.
        hit = path <= price if side == 1 else path >= price
        if not hit.any():
            return FillProbe(filled=False)
        idx = int(np.argmax(hit))
        slip = (float(path[idx]) - price) / pip * side
        return FillProbe(filled=True, slippage_pips=slip, at_index=idx)

    # STOP: BUY stop @X inachochewa ask ≥ X; fill ni tick ILE ILE (gap-honest) —
    # slippage = umbali bei ilivyoruka juu ya X. Cap inaamua kama ni fill halali.
    hit = path >= price if side == 1 else path <= price
    if not hit.any():
        return FillProbe(filled=False)
    idx = int(np.argmax(hit))
    slip = (float(path[idx]) - price) / pip * side
    return FillProbe(filled=slip <= cap_pips, slippage_pips=slip, at_index=idx)


# --------------------------------------------------------------------------
# L-D — QUALITY buckets (spec §5.4)
# --------------------------------------------------------------------------


def quality_bucket(r_net: float, thresholds: dict[str, float]) -> str:
    """R_net → A+ / A / B / reject. Mipaka inatoka config (§5.4), si hapa."""
    if r_net >= float(thresholds["a_plus"]):
        return "A+"
    if r_net >= float(thresholds["a"]):
        return "A"
    if r_net >= float(thresholds["b"]):
        return "B"
    return "reject"


def r_net(outcome: int, tp_atr: float, sl_atr: float, cost_pips: float, sl_pips: float) -> float:
    """R halisi baada ya gharama (§5.4): matokeo ya barrier kwa R − cost/SL.

    TP_FIRST inalipa `tp/sl` R; SL_FIRST inapoteza 1 R. Timeout inapimwa na
    `timeout_return_r` ya cell (si hapa — hii ni kwa matokeo yaliyotatuliwa).
    """
    if sl_pips <= 0:
        raise ValueError("sl_pips lazima iwe chanya")
    gross = (tp_atr / sl_atr) if outcome == TP_FIRST else -1.0
    return gross - cost_pips / sl_pips
