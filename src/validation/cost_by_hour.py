"""Gharama kwa SAA ya siku — DOCTRINE §8.3, R11.

Calibration A ilionyesha kitu kimoja kwa symbols zote 12: spread kwenye mpaka wa
**D1** ni mara 1.6–4.4 ya spread kwenye mpaka wa **H1**. Sababu si timeframe; ni
**saa**. Mpaka wa D1 unaangukia rollover ya kila siku, na hapo ndipo spread ni
pana zaidi.

Hilo lina maana ambayo D1 pekee haiwezi kuionyesha: **jambo lile lile linatokea
ndani ya H1.** Bar ya H1 inayoishia saa ya rollover ina gharama ile ile pana, na
jedwali linalochukua wastani wa saa 24 linaificha kabisa.

Moduli hii inapima gharama kwa kila saa, ikitumia **sampuli zile zile** za
Calibration A (`execution_samples`). Si kipimo kipya; ni kipimo kile kile
kikiwa hakijaviringishwa.

---

**Rollover haidhaniwi — inapimwa.**

`data.yaml` ina `broker_server_tz: "Europe/Berlin"`, na maoni yake yenyewe
yanasema **"KUTHIBITISHWA kwa broker, si kudhaniwa"**. Kwa hiyo hatuanzii hapo.

Tunahesabu kwa **saa za UTC** — ndicho data inachokibeba, na hakuna dhana ndani
yake. Saa yenye spread pana kuliko zote ndiyo jibu la data lenyewe.

Kisha tunahesabu **mara ya pili** kwa saa za `broker_server_tz`. Rollover ni
tukio la seva, kwa hiyo linakaa saa ile ile ya **ndani** mwaka mzima, lakini
linahama kati ya UTC 21:00 na 22:00 kwa DST. Mgawanyo wa ndani ukiwa
**mkali zaidi** kuliko wa UTC, tz iliyoandikwa inathibitishwa na data. Ukiwa
butu zaidi, haijathibitishwa — na hilo ni jibu pia.

`ukali` = spread ya saa mbaya kuliko zote ÷ median ya saa zote.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cost_calibration import execution_samples


@dataclass
class HourSamples:
    """Sampuli za symbol moja zikiwa zimepangwa kwa saa, kwa tz mbili."""

    symbol: str
    timeframe: str
    tz: str
    max_gap_seconds: float | None = None
    _spread: dict = field(default_factory=dict)
    _slippage: dict = field(default_factory=dict)

    def add(self, ticks, bars, *, day_tz: str = "UTC") -> "HourSamples":
        import numpy as np

        spread, slippage, _, ends = execution_samples(
            ticks, bars, self.timeframe, symbol=self.symbol, day_tz=day_tz,
            max_gap_seconds=self.max_gap_seconds,
        )
        if len(spread) == 0:
            return self

        saa = (ends.tz_convert(self.tz) if self.tz.upper() != "UTC" else ends).hour
        for h in np.unique(saa):
            m = saa == h
            self._spread.setdefault(int(h), []).append(spread[m])
            self._slippage.setdefault(int(h), []).append(slippage[m])
        return self

    def table(self) -> list[dict[str, Any]]:
        """Row moja kwa kila saa yenye sampuli."""
        import numpy as np

        rows = []
        for h in sorted(self._spread):
            spread = np.concatenate(self._spread[h])
            slip = np.concatenate(self._slippage[h])
            rows.append({
                "hour": h,
                "n": int(spread.size),
                "spread_mean": float(spread.mean()),
                "spread_p95": float(np.quantile(spread, 0.95)),
                "slip_mean": float(slip.mean()),
                "slip_p95": float(np.quantile(slip, 0.95)),
            })
        return rows


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Saa mbaya kuliko zote, na jinsi inavyojitokeza."""
    import numpy as np

    if not rows:
        return {"ukali": float("nan"), "saa_mbaya": None, "median": float("nan")}
    spreads = np.array([r["spread_mean"] for r in rows])
    median = float(np.median(spreads))
    idx = int(np.argmax(spreads))
    return {
        "saa_mbaya": rows[idx]["hour"],
        "spread_mbaya": float(spreads[idx]),
        "saa_nzuri": rows[int(np.argmin(spreads))]["hour"],
        "spread_nzuri": float(spreads.min()),
        "median": median,
        # Ukali: mara ngapi saa mbaya inazidi saa ya kawaida. Namba moja
        # inayolinganisha tz mbili bila kutegemea vipimo vyao.
        "ukali": float(spreads[idx] / median) if median > 0 else float("nan"),
    }


def render(symbol: str, rows: list[dict[str, Any]], tz: str,
           research_base: float | None = None) -> str:
    """Jedwali la saa 24, na alama kwenye saa zinazozidi median mara 1.5."""
    import numpy as np

    if not rows:
        return f"{symbol} ({tz}): hakuna sampuli"
    median = float(np.median([r["spread_mean"] for r in rows]))
    lines = [
        f"{symbol} · saa za {tz} · median ya spread {median:.3f} pips",
        f"   {'saa':>3} {'n':>7} {'spread':>8} {'p95':>8} {'slip':>7} "
        f"{'uwiano':>7}",
    ]
    for r in rows:
        uwiano = r["spread_mean"] / median if median > 0 else float("nan")
        alama = "  <<" if uwiano >= 1.5 else ""
        lines.append(
            f"   {r['hour']:>3} {r['n']:>7,} {r['spread_mean']:>8.3f} "
            f"{r['spread_p95']:>8.3f} {r['slip_mean']:>7.3f} {uwiano:>6.2f}x{alama}"
        )
    return "\n".join(lines)
