"""DF-20 — SETUP-v1: decision points kwa sheria mechanical (spec §4.3).

Hili ndilo darasa la TATU la uvujaji: si la wakati (sentinel §4.2) wala la
stacking (S6), bali **la uchaguzi**. Sheria ya setup ikitunwa baada ya kuona
labels, kila namba ya R1+ ni ya baada ya ukweli — na hakuna kinga ya kiufundi
inayoliona. Kinga pekee ni utaratibu: sheria hii ni **pre-registered** (PD
anasaini KABLA ya label yoyote), vigezo vyote viko config, na `rule_id`
inaingia `dataset_id`.

Sheria tatu, zote mechanical na point-in-time (bars zilizofungwa pekee):

1. GHARAMA     `spread_p50` ya bar ≤ `spread_gate_mult` × median ya nyuma
2. VOLATILITY  ATR14 ndani ya percentile band ya rolling (miezi 6 ya nyuma)
3. TRIGGER     |close − close[k]| ≥ `min_atr_mult` × ATR14

**Control sample (§4.3 sheria 3):** 10% ya bars zisizo setup zinapata labels
pia (`is_control=true`). Bila control, hatutajua kamwe kama filter inatupa
trades bora kuliko inazochukua. Uchaguzi ni wa **hash ya (seed, symbol, muda)**
— si RandomState juu ya mpangilio — ili bar ile ile iwe control kila run,
bila kujali subset gani inachakatwa (reproducibility §8).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .indicators import atr, rolling_median, rolling_pct_rank

# Mabadiliko ya MAANA ya matokeo ya setup yanapandisha hii (mfano: sheria ya
# mwelekeo ikibadilika). Inaingia kwenye dataset_id pamoja na rule_id.
SETUP_SCHEMA_VERSION = 1


@dataclass
class SetupResult:
    """Matokeo ya SETUP-v1 kwa symbol moja — kila bar ya H1 iliyohukumiwa."""

    symbol: str
    rule_id: str
    frame: pd.DataFrame  # index: decision_time (close ya bar)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def setups(self) -> pd.DataFrame:
        return self.frame[self.frame["is_setup"]]

    @property
    def controls(self) -> pd.DataFrame:
        return self.frame[self.frame["is_control"]]

    def render(self) -> str:
        s = self.stats
        return (
            f"{self.symbol} · {self.rule_id} · bars {s['bars']} "
            f"(zenye viashiria {s['eligible']}) · setups {s['setups']} "
            f"({s['setup_rate']:.2%}) · control {s['controls']} · "
            f"gates: gharama {s['fail_spread']} · volatility {s['fail_atr_band']} · "
            f"trigger {s['fail_trigger']}"
        )


def _control_pick(seed: int, symbol: str, stamp: pd.Timestamp, frac: float) -> bool:
    """Uchaguzi wa control unaozalishika upya kwa bar MOJA MOJA.

    Hash ya `(seed, symbol, muda)` → sehemu ya [0,1). Bar ile ile inatoa jibu
    lile lile kila run, kwenye kila mashine, bila kujali mpangilio wa
    kuchakata — RandomState juu ya orodha ingebadilika kila subset
    inapobadilika, na control ya leo isingekuwa ya kesho.
    """
    digest = hashlib.sha256(f"{seed}|{symbol}|{stamp.isoformat()}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < frac


def detect_setups(cfg, bars_h1: pd.DataFrame, symbol: str) -> SetupResult:
    """SETUP-v1 juu ya bars za H1 za symbol moja (index = open time ya bar).

    Kila kipimo kinatumia bars ZILIZOFUNGWA pekee, na kila rolling ni ya nyuma
    — kwa hiyo uamuzi wa bar `t` haubadiliki data ya baada ya `t` ikibadilika
    (mali ya prefix; sentinel §4.2 na test vinathibitisha).
    """
    rule_id = str(cfg.get("setups.rule_id"))
    mult = float(cfg.get("setups.spread_gate_mult"))
    spread_window = int(cfg.get("setups.spread_median_window_bars"))
    band_lo, band_hi = (float(x) for x in cfg.get("setups.atr_band_pct"))
    band_months = int(cfg.get("setups.atr_band_window_months"))
    lookback = int(cfg.get("setups.trigger.lookback_bars"))
    min_atr_mult = float(cfg.get("setups.trigger.min_atr_mult"))
    control_frac = float(cfg.get("setups.control_sample_frac"))
    control_seed = int(cfg.get("setups.control_seed"))

    bars = bars_h1.sort_index(kind="stable")
    out = pd.DataFrame(index=bars.index)

    # Uamuzi unafanyika bar inapofungwa — decision_time ni CLOSE, si open.
    # Bars za L2 zina index ya open; H1 → close = open + saa 1. As-of (§4.1)
    # inasema bar isiyofungwa haitumiki; kuweka muda wa open kama decision
    # time kungeruhusu features kusoma bar ambayo "bado haijaisha".
    out["decision_time"] = bars.index + pd.Timedelta(hours=1)

    out["atr"] = atr(bars)
    out["close"] = bars["close"]

    # 1 — GHARAMA: soko lisilolipika si setup (RCE ingelikataa hata hivyo).
    spread_median = rolling_median(bars["spread_p50"], spread_window, min_periods=spread_window // 4)
    out["spread_ratio"] = bars["spread_p50"] / spread_median
    out["spread_ok"] = out["spread_ratio"] <= mult

    # 2 — VOLATILITY: soko lililokufa halina TP inayofikika; la wazimu lina
    # slippage isiyo na cap. Band ya percentile ya rolling, miezi ~6 ya nyuma.
    band_window = band_months * 22 * 24  # miezi → siku za trading → bars za H1
    out["atr_pct"] = rolling_pct_rank(out["atr"], band_window, min_periods=band_window // 4)
    out["atr_ok"] = (out["atr_pct"] >= band_lo) & (out["atr_pct"] <= band_hi)

    # 3 — TRIGGER: impulse ya mwendo, scale-free (units za ATR).
    displacement = bars["close"] - bars["close"].shift(lookback)
    out["impulse_atr"] = displacement / out["atr"]
    out["trigger_ok"] = out["impulse_atr"].abs() >= min_atr_mult

    # Mwelekeo: ishara ya impulse ile ile (config: trigger.direction).
    # +1 = BUY, -1 = SELL, 0 = hakuna mwendo hata kidogo (haiwezi kuwa trade).
    out["direction"] = displacement.apply(
        lambda d: 0 if pd.isna(d) or d == 0 else (1 if d > 0 else -1)
    ).astype("int8")

    eligible = (
        out["atr"].notna()
        & spread_median.notna()
        & out["atr_pct"].notna()
        & out["impulse_atr"].notna()
        & (out["direction"] != 0)
        & bars["is_valid"].fillna(False)
    )
    out["eligible"] = eligible
    out["is_setup"] = eligible & out["spread_ok"] & out["atr_ok"] & out["trigger_ok"]

    # Control: 10% ya bars ZISIZO setup (lakini zenye viashiria kamili).
    non_setup = eligible & ~out["is_setup"]
    picks = [
        bool(non_setup.loc[stamp])
        and _control_pick(control_seed, symbol, out.loc[stamp, "decision_time"], control_frac)
        for stamp in out.index
    ]
    out["is_control"] = pd.Series(picks, index=out.index, dtype=bool)

    n_eligible = int(eligible.sum())
    stats = {
        "rule_id": rule_id,
        "schema": SETUP_SCHEMA_VERSION,
        "bars": int(len(bars)),
        "eligible": n_eligible,
        "setups": int(out["is_setup"].sum()),
        "setup_rate": float(out["is_setup"].sum() / n_eligible) if n_eligible else 0.0,
        "controls": int(out["is_control"].sum()),
        # Kila gate peke yake, miongoni mwa bars zenye viashiria — hizi ndizo
        # namba za KUTUNA KWA RATE (§4.3 sheria 2, kabla ya labels).
        "fail_spread": int((eligible & ~out["spread_ok"]).sum()),
        "fail_atr_band": int((eligible & ~out["atr_ok"]).sum()),
        "fail_trigger": int((eligible & ~out["trigger_ok"]).sum()),
    }
    return SetupResult(symbol=symbol, rule_id=rule_id, frame=out, stats=stats)
