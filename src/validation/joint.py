"""Lango la PAMOJA — DOCTRINE §9.2, §9.9.

Sakafu ya kila metric ni sahihi peke yake. Kuzidisha ndiko kwenye kasoro.

`noise_floor[metric] = max(p95_A, p95_B, p95_C)` — §9.2 inachukua **upande mgumu
zaidi** kwa makusudi. Kwa hiyo lango moja halipitishi 5% ya null; linapitisha
`p95` ya familia moja kati ya tatu, yaani `2.5/150 ≈ 1.7%`. Hiyo ni sahihi, na
ndiyo iliyopimwa (2026-09-05: 1.3%–3.3% kwa malango matano ya GBPUSD).

Lakini kudai malango matano kwa wakati mmoja kunatumia uangalifu ule ule **mara
tano**, na kila mara kwa replicate tofauti — `p95` ya `sharpe` inatoka kwa
replicate moja, ya `net_pips_month` kwa nyingine. Hakuna mgombea wa null
aliyewahi kulazimika kuvuka zote. Kipimo: washindi 150 wa null dhidi ya sakafu
waliyoijenga wenyewe walipita **0/150**. Lango linalodai `p95` lina kosa la
aina-I chini ya 0.7% — halifanyi kile §9.2 inasema linafanya.

---

**Takwimu:**

```
u_i(c) = (k_i + 1) / (n + 1)      k_i = null ngapi c anazizidi kwenye metric i
T(c)   = min_i u_i(c)             ← mwelekeo DHAIFU zaidi wa mgombea
sakafu = max_familia ( p95 ya T ndani ya familia hiyo )
```

`min`, si wastani. §9.2 inakataa wastani kwa sababu Sharpe kubwa ingeweza
kulipia drawdown mbaya; `min` inakataa hilo hilo — mgombea ana thamani ya
mwelekeo wake dhaifu zaidi, na hakuna metric inayoweza kujificha nyuma ya
nyingine. Kilichoondolewa si sharti la ubora kwenye kila mwelekeo; ni
**mkusanyiko wa uangalifu** uliokuwa ukijilimbikiza bila kupimwa.

`(k+1)/(n+1)` ni fomu ile ile ya p-value ya permutation inayotumika kwenye
`null_check.py`: mgombea mwenyewe yumo kwenye seti ya marejeo. Kwa hiyo
replicate ya null na mgombea halisi wanapimwa kwa kipimo kilekile hasa — bila
hivyo, null ingeweza kufika `149/150` pekee wakati halisi anafika `150/150`, na
lango lingekuwa rahisi kidogo kwa halisi kwa sababu ya hesabu, si ya soko.

---

**Kiwango kinachotarajiwa hakitabiriki — kinapimwa.**

`max` juu ya familia tatu inabaki pale ilipo; inachobadilika ni kwamba sasa
inatumika **mara moja**, kwenye takwimu ya pamoja, badala ya mara tano kimya.
Lakini kiasi cha uangalifu inachoongeza kinategemea **jinsi familia
zinavyotofautiana**, na hicho ni kitu cha soko, si cha hesabu:

- familia zenye ugumu ule ule → `max` hairudishi chochote → kiwango kuelekea **5%**
- familia moja ngumu zaidi kuliko zote → `max` inachukua yake → kuelekea **1.7%**

Hata katika hali ya kwanza kiwango hakifikii 5%: `max` ya makadirio matatu ya
`p95`, kila moja kutoka pointi 50, iko juu ya `p95` halisi kwa sababu ya kelele
ya sampuli pekee. Masafa yanaegemea upande wa chini — upande salama.

Kwa hiyo `null_pass_rate` **inapimwa na kuandikwa kwenye faili** badala ya
kutangazwa hapa. Ikitoka nje ya `[1.7%, 5%]`, si soko — ni ujenzi ulioharibika,
na inaonekana mara moja badala ya kubaki kwenye jedwali ikionekana halali.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

BETTER = "better"

# `p95` ile ile ya §9.2, §3.1 na Calibration A — si kizingiti kipya.
P_JOINT = 0.95


class JointError(RuntimeError):
    """Lango la pamoja haliwezi kujengwa kama ilivyoombwa."""


def u_stat(value: Any, reference: Sequence[float], higher_is: str) -> float:
    """`(k+1)/(n+1)` — nafasi ya `value` ndani ya mgawanyo wa null.

    Thamani isiyohesabika inarudisha `0.0`: kutokuwepo kwa kipimo si ushahidi
    wa kupita (§1.1). Sawa haihesabiwi kama kuzidi — `passes()` ya `FloorEntry`
    inasema *kuvuka ni kuzidi, si kufikia*, na hapa ni sheria ile ile.
    """
    n = len(reference)
    if n == 0:
        raise JointError("seti ya marejeo ni tupu — hakuna cha kulinganisha")
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(x):
        return 0.0
    if higher_is == BETTER:
        k = sum(1 for r in reference if x > r)
    else:
        k = sum(1 for r in reference if x < r)
    return (k + 1) / (n + 1)


@dataclass(frozen=True)
class JointGate:
    """Lango moja lililopimwa juu ya takwimu ya pamoja `T`."""

    floor: float
    by_family: dict[str, float]
    reference: dict[str, tuple[float, ...]]
    higher_is: dict[str, str]
    n_null: int
    null_pass_rate: float
    n_incomplete: int = 0
    # `T` ya kila replicate ya null. `reference` ni NGUZO — upangaji ndani ya
    # replicate umepotea humo, kwa hiyo `T` haiwezi kuhesabiwa upya kutoka kwake.
    # Bila hizi, swali "mgombea huyu yuko karibu kiasi gani" lingehitaji
    # checkpoint, na lango lisiloweza kujieleza si lango kamili.
    t_null: tuple[float, ...] = ()

    @property
    def metrics(self) -> tuple[str, ...]:
        return tuple(self.reference)

    def u(self, values: Mapping[str, Any]) -> dict[str, float]:
        return {
            m: u_stat(values.get(m), self.reference[m], self.higher_is[m])
            for m in self.reference
        }

    def t(self, values: Mapping[str, Any]) -> float:
        u = self.u(values)
        return min(u.values()) if u else 0.0

    def failed(self, values: Mapping[str, Any]) -> tuple[str, ...]:
        """Mielekeo iliyo CHINI ya sakafu ya pamoja, dhaifu kwanza.

        `T = min(u)`, kwa hiyo `T > sakafu` ni sawa kabisa na *hakuna metric
        iliyo chini ya sakafu*. Kurudisha orodha badala ya `bool` kunahifadhi
        swali la §9.5: **lango lipi limekata, na kwa kiasi gani.**
        """
        u = self.u(values)
        chini = [(v, m) for m, v in u.items() if v <= self.floor]
        return tuple(m for _, m in sorted(chini))

    def passes(self, values: Mapping[str, Any]) -> bool:
        return not self.failed(values)

    def p_value(self, values: Mapping[str, Any]) -> float:
        """`(k+1)/(n+1)` ambapo `k` = replicates za null zenye `T` isiyopungua.

        Ndiyo namba inayojibu *"yuko karibu kiasi gani"* bila kizingiti chochote
        kipya. Fomu ni ile ile ya §9.8, na inasoma moja kwa moja: `p = 0.30`
        ni mgombea wa kawaida kabisa chini ya null; `p = 0.07` ni aliyekaribia
        bila kufika.

        `K` ya utafutaji wa null na wa halisi ni ile ile (§9.4), kwa hiyo tatizo
        la `max` ya §9.1 tayari liko ndani ya pande zote mbili.
        """
        if not self.t_null:
            return float("nan")
        t = self.t(values)
        k = sum(1 for x in self.t_null if x >= t)
        return (k + 1) / (len(self.t_null) + 1)

    @property
    def ndani_ya_masafa(self) -> bool:
        """Je kiwango kilichopimwa kiko pale ujenzi unavyokidai kuwa.

        Nje ya `[5%/n_familia, 5%]` si tabia ya soko — ni hesabu iliyoharibika:
        mwelekeo uliogeuzwa, `reference` isiyolingana na metrics, au replicates
        zisizohesabika. Kiasi kidogo cha nafasi kinaachwa pande zote mbili kwa
        ajili ya punje ya `1/n`.
        """
        if not math.isfinite(self.null_pass_rate) or not self.by_family:
            return False
        punje = 1.0 / max(self.n_null, 1)
        chini = (1.0 - P_JOINT) / len(self.by_family) - punje
        return chini <= self.null_pass_rate <= (1.0 - P_JOINT) + punje

    def render(self) -> str:
        fam = " · ".join(f"{k[:5]} {v:.4f}" for k, v in sorted(self.by_family.items()))
        onyo = "" if self.n_incomplete == 0 else (
            f"   [replicates {self.n_incomplete} zenye metric isiyohesabika]"
        )
        nje = "" if self.ndani_ya_masafa else (
            f"\n   KOSA · kiwango kiko NJE ya "
            f"[{(1 - P_JOINT) / max(len(self.by_family), 1):.2%}, "
            f"{1 - P_JOINT:.2%}] — ni hesabu, si soko"
        )
        return (
            f"LANGO LA PAMOJA · T = min(u) juu ya metrics {len(self.reference)}\n"
            f"   sakafu   {self.floor:.4f}   (p{int(P_JOINT * 100)} ya T, "
            f"familia ngumu zaidi)\n"
            f"   kwa familia   {fam}\n"
            f"   null inayopita  {self.null_pass_rate:.2%}  "
            f"(replicates {self.n_null:,}){onyo}{nje}"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "floor": self.floor,
            "by_family": self.by_family,
            "higher_is": self.higher_is,
            "n_null": self.n_null,
            "null_pass_rate": self.null_pass_rate,
            "n_incomplete": self.n_incomplete,
            "reference": {k: list(v) for k, v in self.reference.items()},
            "t_null": list(self.t_null),
        }

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "JointGate":
        return cls(
            floor=float(raw["floor"]),
            by_family={k: float(v) for k, v in raw["by_family"].items()},
            reference={k: tuple(float(x) for x in v)
                       for k, v in raw["reference"].items()},
            higher_is=dict(raw["higher_is"]),
            n_null=int(raw["n_null"]),
            null_pass_rate=float(raw["null_pass_rate"]),
            n_incomplete=int(raw.get("n_incomplete", 0)),
            t_null=tuple(float(x) for x in raw.get("t_null", ())),
        )


def calibrate_joint(
    rows_by_family: Mapping[str, Sequence[Mapping[str, Any]]],
    higher_is: Mapping[str, str],
) -> JointGate:
    """Jenga lango la pamoja kutoka **safu** za null, si nguzo zake.

    `rows_by_family[familia]` ni orodha ya replicates, kila moja ni metrics za
    mshindi wa run ile. Upangaji ndani ya replicate ni muhimu: `T` ni `min` juu
    ya metrics za **mgombea yule yule**. Nguzo zilizotenganishwa (`seen[fam][metric]`)
    zingepoteza upangaji huo, na `T` ingekuwa ya mgombea asiyekuwepo.
    """
    import numpy as np

    metrics = tuple(higher_is)
    if not metrics:
        raise JointError("hakuna metric yenye sakafu — lango la pamoja haliwezekani")

    zote = [row for rows in rows_by_family.values() for row in rows]
    if not zote:
        raise JointError("hakuna replicate hata moja")

    reference = {
        m: tuple(float(r[m]) for r in zote
                 if m in r and _ni_namba(r.get(m)))
        for m in metrics
    }
    for m, ref in reference.items():
        if not ref:
            raise JointError(f"`{m}` haina thamani halali hata moja kwenye null")

    tupu = JointGate(floor=float("-inf"), by_family={}, reference=reference,
                     higher_is=dict(higher_is), n_null=len(zote),
                     null_pass_rate=float("nan"))

    by_family: dict[str, float] = {}
    t_zote: list[float] = []
    for fam in sorted(rows_by_family):
        t_fam = [tupu.t(r) for r in rows_by_family[fam]]
        if not t_fam:
            continue
        by_family[fam] = float(np.quantile(t_fam, P_JOINT))
        t_zote.extend(t_fam)

    if not by_family:
        raise JointError("hakuna familia yenye replicates")

    # `max` juu ya familia — §9.2 ile ile, ikitumika MARA MOJA.
    floor = max(by_family.values())
    kiwango = sum(1 for t in t_zote if t > floor) / len(t_zote)
    pungufu = sum(1 for r in zote if any(not _ni_namba(r.get(m)) for m in metrics))

    return JointGate(
        floor=float(floor), by_family=by_family, reference=reference,
        higher_is=dict(higher_is), n_null=len(zote),
        null_pass_rate=float(kiwango), n_incomplete=int(pungufu),
        t_null=tuple(t_zote),
    )


def _ni_namba(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
