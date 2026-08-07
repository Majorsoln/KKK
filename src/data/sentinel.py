"""DF-08 — SENTINEL YA UVUJAJI: test ya lazima kwa kila build ya L3 (spec §4.2).

```
Chukua dataset. Badilisha (shuffle) data YOTE baada ya t.
Feature zote za decision point t lazima zibaki ZILE ZILE, bit kwa bit.
Ikibadilika hata moja → uvujaji umegunduliwa → build inasimama.
```

Test hii **si hiari**. Ni lango `G1` la §4.2 ya IMPLEMENTATION_PLAN.

**Mipaka yake (uwazi):** sentinel inagundua uvujaji wa *point-in-time* — feature
inayosoma bar isiyofungwa au data ya baadaye. **Haigundui** uvujaji wa
*stacking* (model iliyofundishwa kwenye data yote ikitumika kutoa meta-feature)
kwa sababu model iliyoshafundishwa haibadilishi output zake data ya baadaye
ikichanganywa. Huo ni S6 (cross-fitting) — kinga tofauti kabisa.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd


@dataclass
class SentinelResult:
    """Matokeo ya sentinel — na **jina la feature iliyovuja**, si "imefeli" tu."""

    checked_points: int = 0
    features: int = 0
    leaked: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.leaked

    def summary(self) -> str:
        status = "PASS" if self.passed else "UVUJAJI UMEGUNDULIWA"
        return (
            f"sentinel: {status} · points={self.checked_points} "
            f"features={self.features} leaked={len(self.leaked)}"
        )

    def raise_if_leaked(self) -> None:
        if self.leaked:
            names = sorted({item["feature"] for item in self.leaked})
            raise AssertionError(
                f"UKIUKAJI WA §4.2 (sentinel): features zinasoma data ya baadaye — "
                f"{names}. Build inasimama."
            )


def _fingerprint(value: Any) -> str:
    """Alama ya thamani **bit kwa bit** (spec inasema hivyo, si 'karibu sawa')."""
    if isinstance(value, (pd.Series, pd.DataFrame)):
        payload = pd.util.hash_pandas_object(value, index=True).values.tobytes()
    elif isinstance(value, np.ndarray):
        payload = np.ascontiguousarray(value).tobytes()
    elif isinstance(value, float):
        payload = np.float64(value).tobytes()
    else:
        payload = repr(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def shuffle_future(
    frame: pd.DataFrame, t: pd.Timestamp, seed: int = 0
) -> pd.DataFrame:
    """Changanya rows ZOTE zilizo baada ya `t`; zilizo kabla hazibadiliki.

    Values ndizo zinazochanganywa, si index — kwa hiyo muundo wa muda unabaki
    ule ule na tofauti pekee ni **maudhui ya baadaye**.
    """
    out = frame.copy()
    future = out.index > t
    count = int(future.sum())
    if count > 1:
        rng = np.random.default_rng(seed)
        order = rng.permutation(count)
        out.loc[future, :] = out.loc[future, :].to_numpy()[order]
    return out


def run_sentinel(
    bars_by_tf: dict[str, pd.DataFrame],
    decision_times: Sequence[pd.Timestamp],
    feature_fn: Callable[[dict[str, pd.DataFrame], pd.Timestamp], dict[str, Any]],
    seed: int = 0,
) -> SentinelResult:
    """Sentinel ya §4.2 kwa kila decision point.

    `feature_fn(bars_by_tf, t)` inarudisha `{jina_la_feature: thamani}`. Kila
    feature inahesabiwa mara mbili: kwa data halisi, na kwa data iliyochanganywa
    baada ya `t`. Ikitofautiana, jina lake linaingia kwenye ripoti.
    """
    result = SentinelResult()
    for t in decision_times:
        baseline = feature_fn(bars_by_tf, t)
        shuffled_bars = {
            tf: shuffle_future(bars, t, seed=seed + index)
            for index, (tf, bars) in enumerate(bars_by_tf.items())
        }
        after = feature_fn(shuffled_bars, t)

        result.checked_points += 1
        result.features = max(result.features, len(baseline))
        for name, value in baseline.items():
            if _fingerprint(value) != _fingerprint(after.get(name)):
                result.leaked.append(
                    {
                        "feature": name,
                        "decision_time": str(t),
                        "before": str(value)[:80],
                        "after": str(after.get(name))[:80],
                    }
                )
    return result
