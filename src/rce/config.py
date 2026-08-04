"""Config ya RCE — `config/risk.yaml` (+ `config/broker_costs.yaml`).

Spec §1: "PD anabadilisha yaml bila code". Kwa hiyo module hii haina thamani
yoyote ya maamuzi iliyoandikwa ndani yake: kila kigezo kinasomwa, na kigezo
kisipokuwepo ni **hitilafu**, si default ya kubuni (lango G10).

`fingerprint` ni sha256 ya bytes za config zote mbili — inaingia kwenye kila
rekodi ya REJECT (§5: "config-fingerprint kwenye log").
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_MISSING = object()


class RiskConfigError(RuntimeError):
    """Config haipo, au kigezo cha spec hakipo ndani yake."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_risk_path() -> Path:
    return repo_root() / "config" / "risk.yaml"


def default_broker_costs_path() -> Path:
    return repo_root() / "config" / "broker_costs.yaml"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class RiskConfig:
    """Vigezo vya risk/cost + fingerprint yao."""

    raw: dict[str, Any]
    path: Path
    broker_costs: dict[str, Any]
    broker_costs_path: Path | None
    fingerprint: str

    # ---------- upatikanaji ----------

    def get(self, dotted: str, default: Any = _MISSING) -> Any:
        node: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is _MISSING:
                    raise RiskConfigError(
                        f"kigezo `{dotted}` hakipo kwenye {self.path} — "
                        "kigezo cha maamuzi hakiandikwi kwenye code (G10)"
                    )
                return default
            node = node[part]
        return node

    def number(self, dotted: str, default: Any = _MISSING) -> float:
        return float(self.get(dotted, default))

    @property
    def short_fingerprint(self) -> str:
        """Alama fupi ya kusoma kwenye log/dashboard."""
        return self.fingerprint[:12]

    # ---------- §2 bajeti ----------

    @property
    def base_balance(self) -> float:
        return self.number("base_balance")

    @property
    def base_percentage(self) -> float:
        return self.number("base_percentage")

    @property
    def penalty_factor(self) -> float:
        return self.number("penalty_factor")

    @property
    def win_factor(self) -> float:
        return self.number("win_factor")

    @property
    def loss_factor(self) -> float:
        return self.number("loss_factor")

    @property
    def day_reset_tz(self) -> str:
        return str(self.get("day_reset_tz"))

    # ---------- §5 gate ----------

    @property
    def max_open_trades(self) -> int:
        return int(self.get("max_open_trades"))

    @property
    def max_correlated(self) -> int:
        return int(self.get("max_correlated"))

    @property
    def daily_loss_stop_frac(self) -> float:
        return self.number("daily_loss_stop_frac")

    @property
    def max_total_dd(self) -> float:
        return self.number("max_total_dd")

    @property
    def trade_news(self) -> bool:
        return bool(self.get("trade_news"))

    @property
    def max_spread(self) -> dict[str, float]:
        return {str(k): float(v) for k, v in dict(self.get("max_spread")).items()}

    @property
    def correlation_groups(self) -> dict[str, list[str]]:
        return {str(k): list(v) for k, v in dict(self.get("correlation_groups")).items()}

    def groups_of(self, symbol: str) -> list[str]:
        """Makundi YOTE yanayomhusu symbol (§5 check 2)."""
        return sorted(name for name, members in self.correlation_groups.items() if symbol in members)

    # ---------- §3 gharama ----------

    @property
    def slippage_cap_pips(self) -> dict[str, float]:
        return {str(k): float(v) for k, v in dict(self.get("slippage_cap_pips")).items()}

    @property
    def slippage_cap_dynamic(self) -> bool:
        return bool(self.get("slippage_cap_dynamic"))

    @property
    def fill_rate_min(self) -> float:
        return self.number("fill_rate_min")

    @property
    def commission_side(self) -> str:
        return str(self.get("commission_side"))

    @property
    def swap_enabled(self) -> bool:
        return bool(self.get("swap.enabled"))

    @property
    def swap_triple_day(self) -> str:
        return str(self.get("swap.triple_day"))

    @property
    def swap_rollover_hour(self) -> int:
        return int(self.get("swap.server_rollover_hour"))

    # ---------- §3.1 spread ----------

    @property
    def spread_base_window(self) -> int:
        return int(self.get("spread_model.base_window"))

    @property
    def spread_spike_window(self) -> int:
        return int(self.get("spread_model.spike_window"))

    @property
    def spread_spike_quantile(self) -> float:
        return self.number("spread_model.spike_quantile")

    @property
    def spread_combine(self) -> str:
        return str(self.get("spread_model.combine"))


def load_risk_config(
    path: str | Path | None = None,
    broker_costs_path: str | Path | None = None,
) -> RiskConfig:
    """Pakia risk.yaml (+ broker_costs.yaml ikiwepo) na uhesabu fingerprint."""
    cfg_path = Path(path) if path is not None else default_risk_path()
    if not cfg_path.is_file():
        raise RiskConfigError(f"config haipo: {cfg_path}")
    parsed = yaml.safe_load(cfg_path.read_bytes())
    if not isinstance(parsed, dict):
        raise RiskConfigError(f"config si mapping ya YAML: {cfg_path}")

    costs_path = Path(broker_costs_path) if broker_costs_path is not None else default_broker_costs_path()
    costs: dict[str, Any] = {}
    fingerprint_parts = [_sha256_file(cfg_path)]
    if costs_path.is_file():
        loaded = yaml.safe_load(costs_path.read_bytes())
        costs = loaded if isinstance(loaded, dict) else {}
        fingerprint_parts.append(_sha256_file(costs_path))
    else:
        costs_path = None  # type: ignore[assignment]

    fingerprint = hashlib.sha256("|".join(fingerprint_parts).encode()).hexdigest()
    return RiskConfig(
        raw=parsed,
        path=cfg_path,
        broker_costs=costs,
        broker_costs_path=costs_path,
        fingerprint=fingerprint,
    )
