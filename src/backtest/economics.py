"""Lango la uchumi — DOCTRINE §8.4, §8.1, R20.

> Candidate yenye `gross edge kwa trade < 2 × live_sizing_cost` inakataliwa
> kabla ya takwimu yoyote kuhesabiwa.

Sababu ni ya kihesabu, si ya ladha: gharama ni **thabiti kwa kila trade** —
haibadiliki trade ikiwa kubwa au ndogo. Kwa hiyo tatizo kamwe si trades za bei
ghali; ni **trades ndogo mno**. Edge ya pips 1.2 kwa gharama ya pips 1.0 ni
strategy inayofanya kazi kwa broker, si kwa mmiliki wake.

`2×` na si `1×`: `1×` ingedai makadirio yawe sahihi kabisa. `2×` inaacha nafasi
ya slippage, kuzorota kwa spread, na makosa ya utekelezaji.

---

**Mamlaka ni `live_sizing_cost`, si `research_cost` (R20).**

Swali si *"ilikuwa na uchumi kihistoria?"* bali *"ina uchumi chini ya gharama
ambayo RCE itaitumia kweli kuiweka ukubwa?"* `research_cost` ni ILIYOTOKEA;
`live_sizing_cost` ni ANAYOITUMIA RCE. Kutumia ya matumaini kimya ndiyo aina
hasa ya dhana inayofanya mfumo uonekane wenye faida bila kuwa nao.

Zote mbili zinaripotiwa kwa sababu **tofauti yao ni kipimo cha udhaifu**:
`cost_sensitivity` inaingia kwenye Strategy DNA (§13).

---

**Hili si lango la takwimu, na §8.4 inasema hivyo waziwazi.**

Candidate yenye `1.9×` inaweza kuwa ya kweli; yenye `3×` inaweza kuwa kelele.
Thamani ya lango ni **kupunguza idadi ya majaribio**, ambayo ndiyo inayotawala
§9. Kwa hiyo candidate iliyokataliwa hapa **bado imegusa data** na bado
inahesabika kwenye `variants_tested` (S1) — kuiondoa kungeshusha sakafu kwa
utafutaji ambao ulifanyika kweli.

**`gross_edge` inatoka kwenye utambulisho wa upatanisho wa §11.4**, si kwa
hesabu ya pili: `execution` inathibitisha `net = gross - comm - swap` na
`net = gross_mid - spread - comm - swap`, kwa hiyo `gross_mid = gross + spread`
kwa ujenzi. Kuhesabu mid upya hapa kungekuwa njia ya tatu isiyokaguliwa.

---

**`2×` inapimwa kwa UKINGO WA UHAKIKA, si kwa nukta (2026-08-25).**

Kipimo juu ya data isiyo na edge kilionyesha tatizo ambalo lango la nukta
haliwezi kuliona. Wagombea 1,000 wa nasibu juu ya bars 12,000: **sita** walipita
§8.4, na wote walikuwa na **trades 1–14** (wastani 5.8). Bora kati yao alikuwa
na Sharpe **11.44 kutoka trades MBILI**.

Mgombea wa trade moja ana "wastani wa edge kwa trade" — lakini si wastani, ni
uchunguzi mmoja. Akipita, sakafu ya §9 ingewekwa na bahati ya sarafu moja, na
hakuna strategy halisi ingeivuka.

**Kizidishi `2×` cha doctrine hakijabadilika.** Kilichobadilika ni upande wa
kushoto: badala ya `x̄`, inatumika `x̄ − t·s/√n` — wastani ukiwa umeadhibiwa kwa
kutokuwa na uhakika wake wenyewe. Hakuna namba mpya iliyoingia: `t` inatokana na
`n`, na kiwango cha uhakika ni **p95 ile ile** ya §9.2, §3.1 na Calibration A.

Matokeo yanajipanga yenyewe: `n = 1` haina standard error, kwa hiyo haina
ukingo — inakataliwa kwa ufafanuzi. `n = 2` inadai mara 6.31 ya standard error.
`n = 30` inadai 1.70. Sampuli ikikua, adhabu inafifia hadi karibu sifuri, na
lango linarudi kuwa `2×` ya kawaida — ambapo ndipo lilipokusudiwa kuwa.

Ukingo unawekwa kwenye **edge** pekee, si kwa gharama: gharama kwa kila trade ni
thabiti kwa ujenzi (spread + commission), wakati edge ndiyo yenye mtawanyiko.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from src.stats import CONFIDENCE, mean_lower_bound

# §8.4. Namba hii ni ya doctrine na inaonekana; si ya kupimwa kutoka data —
# ni ukingo ulioamuliwa dhidi ya makosa ya makadirio, si kadirio lenyewe.
KIZIDISHI = 2.0

PASS_ECONOMIC = ""
REJECT_THIN_EDGE = "thin_edge"
REJECT_THIN_SAMPLE = "thin_sample"     # trades chache mno kuwa na ukingo
REJECT_NO_TRADES = "no_trades"


@dataclass(frozen=True)
class Economics:
    """Uchumi wa candidate MMOJA, kwa wastani wa kila trade."""

    n_trades: int
    gross_edge_pips: float          # mid→mid, gharama HAIJAINGIA
    research_cost_pips: float       # ILIYOTOKEA — spread + slip + comm + swap
    live_sizing_cost_pips: float    # ANAYOITUMIA RCE — kadirio kihafidhina
    edge_lower_pips: float = float("nan")   # `x̄ − t·s/√n` — ndio unaopimwa

    @property
    def edge_over_research(self) -> float:
        base = self.research_cost_pips
        return self.gross_edge_pips / base if base > 0 else float("nan")

    @property
    def edge_over_live(self) -> float:
        """Uwiano wa NUKTA. Unaripotiwa, lakini si unaopitisha — ona `ratio_lower`."""
        base = self.live_sizing_cost_pips
        return self.gross_edge_pips / base if base > 0 else float("nan")

    @property
    def ratio_lower(self) -> float:
        """Uwiano WENYE MAMLAKA: ukingo wa chini wa edge ÷ gharama (R20).

        Ndio unaolinganishwa na `KIZIDISHI`. Tofauti yake na `edge_over_live` ni
        **adhabu ya sampuli ndogo**, na inaonekana kwenye ripoti.
        """
        base = self.live_sizing_cost_pips
        return self.edge_lower_pips / base if base > 0 else float("nan")

    @property
    def sample_penalty(self) -> float:
        """`edge_over_live − ratio_lower`. Kubwa = sampuli ndogo mno kuamini."""
        return self.edge_over_live - self.ratio_lower

    @property
    def cost_sensitivity(self) -> float:
        """`(edge ÷ research) ÷ (edge ÷ live)` = `live ÷ research`.

        Kubwa = strategy inategemea gharama kubaki nzuri. Inaingia kwenye DNA
        (§13) kama kipimo cha udhaifu, si kama lango.
        """
        base = self.research_cost_pips
        return self.live_sizing_cost_pips / base if base > 0 else float("nan")

    @property
    def reject_reason(self) -> str:
        if self.n_trades == 0:
            return REJECT_NO_TRADES
        if self.n_trades < 2:
            # Uchunguzi mmoja hauna standard error, kwa hiyo hauna ukingo. Si
            # "edge ndogo" — ni kwamba hakuna kipimo hata kimoja.
            return REJECT_THIN_SAMPLE
        uwiano = self.ratio_lower
        if math.isnan(uwiano):
            # Gharama sifuri si "nafuu" — ni gharama isiyopimwa. Kupitisha hapo
            # kungekuwa kupitisha kwa sababu ya kutokujua.
            return REJECT_THIN_EDGE
        return PASS_ECONOMIC if uwiano >= KIZIDISHI else REJECT_THIN_EDGE

    @property
    def passes(self) -> bool:
        return self.reject_reason == PASS_ECONOMIC

    def render(self) -> str:
        alama = "SAWA" if self.passes else self.reject_reason.upper()
        return (
            f"trades {self.n_trades:>6,} · edge {self.gross_edge_pips:>7.3f} pips "
            f"(ukingo {self.edge_lower_pips:>7.3f}) · "
            f"research {self.research_cost_pips:>6.3f} · "
            f"live {self.live_sizing_cost_pips:>6.3f} · "
            f"uwiano {self.edge_over_live:>5.2f}× → {self.ratio_lower:>5.2f}× "
            f"(dai {KIZIDISHI:.0f}×) · sens {self.cost_sensitivity:>4.2f}×  {alama}"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "n_trades": self.n_trades,
            "gross_edge_pips": self.gross_edge_pips,
            "edge_lower_pips": self.edge_lower_pips,
            "research_cost_pips": self.research_cost_pips,
            "live_sizing_cost_pips": self.live_sizing_cost_pips,
            "edge_over_research": self.edge_over_research,
            "edge_over_live": self.edge_over_live,
            "ratio_lower": self.ratio_lower,
            "sample_penalty": self.sample_penalty,
            "confidence": CONFIDENCE,
            "cost_sensitivity": self.cost_sensitivity,
            "required": KIZIDISHI,
            "passes": self.passes,
            "reject_reason": self.reject_reason,
        }


def measure(result) -> Economics:
    """Uchumi wa `BacktestResult`, kwa wastani wa kila trade iliyofungwa."""
    trades = result.trades
    if not trades:
        return Economics(0, float("nan"), float("nan"), float("nan"))

    n = float(len(trades))
    # §11.4: `gross_mid = gross_pips + spread_pips` kwa utambulisho, si kwa
    # hesabu mpya.
    kila_moja = [t.path.gross_pips + t.path.spread_pips for t in trades]
    edge = sum(kila_moja) / n
    research = sum(
        t.path.spread_pips + abs(t.path.fill_slippage_pips)
        + t.path.commission_pips + t.path.swap_pips
        for t in trades
    ) / n
    live = sum(t.attempt.cost_pips for t in trades) / n

    return Economics(
        n_trades=len(trades), gross_edge_pips=float(edge),
        research_cost_pips=float(research), live_sizing_cost_pips=float(live),
        edge_lower_pips=mean_lower_bound(kila_moja),
    )
