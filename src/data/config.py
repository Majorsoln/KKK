"""Kusoma `config/data.yaml` — chanzo KIMOJA cha vigezo vya data.

Sheria (DoD §1.2 ya IMPLEMENTATION_PLAN, lango G10): hakuna kigezo cha maamuzi
kinachoishi kwenye code. Kila namba inayoathiri data inatoka hapa, na kila
badiliko la config linabadilisha `config_hash` (spec §8 — fingerprint).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .hashing import sha256_bytes

_MISSING = object()
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(RuntimeError):
    """Config haipo, haijakamilika, au ina kigezo kisichoeleweka."""


def repo_root() -> Path:
    """Mzizi wa repo hii (folda yenye `config/` na `docs/`)."""
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return repo_root() / "config" / "data.yaml"


def _expand_env(value: str, env: dict[str, str]) -> str:
    """Panua `${VAR}` kwa environment. VAR isiyopo inabaki kama ilivyo."""

    def _sub(match: re.Match[str]) -> str:
        return env.get(match.group(1), match.group(0))

    return _ENV_PATTERN.sub(_sub, value)


def _has_unresolved_env(value: str) -> bool:
    return bool(_ENV_PATTERN.search(value))


@dataclass(frozen=True)
class DataConfig:
    """Config ya data pamoja na fingerprint yake."""

    raw: dict[str, Any]
    path: Path
    config_hash: str
    env: dict[str, str]

    # ---------- upatikanaji wa jumla ----------

    def get(self, dotted: str, default: Any = _MISSING) -> Any:
        """Soma kigezo kwa njia ya `sehemu.sehemu`. Kikikosekana bila default → ConfigError."""
        node: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is _MISSING:
                    raise ConfigError(
                        f"kigezo `{dotted}` hakipo kwenye {self.path} — PD anaongeza config, si code"
                    )
                return default
            node = node[part]
        if isinstance(node, str):
            node = _expand_env(node, self.env)
        return node

    def path_of(self, dotted: str, default: Any = _MISSING) -> Path:
        """Kigezo cha njia ya faili/folda, likiwa limepanuliwa kwa environment."""
        value = self.get(dotted, default)
        if value is None:
            raise ConfigError(f"kigezo `{dotted}` hakina thamani kwenye {self.path}")
        text = str(value)
        if _has_unresolved_env(text):
            missing = ", ".join(sorted(set(_ENV_PATTERN.findall(text))))
            raise ConfigError(
                f"`{dotted}` inategemea environment isiyowekwa ({missing}). "
                "PD anaamua storage ya research (§9 ya DATA_FEATURE_STANDARD) — weka env hiyo "
                "au andika njia kamili kwenye config/data.yaml."
            )
        return Path(text).expanduser()

    # ---------- vigezo vinavyotumika mara kwa mara ----------

    @property
    def symbols(self) -> list[str]:
        return list(self.get("source.symbols"))

    @property
    def provenance_default(self) -> str:
        return str(self.get("source.provenance"))

    @property
    def schema_variants(self) -> dict[str, dict[str, Any]]:
        return dict(self.get("source.schema_variants"))

    def variant_of_symbol(self, symbol: str) -> str | None:
        """Toleo la schema linalotarajiwa kwa symbol (spec §2.1). None = halijatajwa."""
        for name, spec in self.schema_variants.items():
            listed = spec.get("symbols")
            if listed and symbol in listed:
                return name
        # Toleo lisilo na orodha ya symbols ndilo la default (Toleo A kwa spec §2.1).
        unlisted = [name for name, spec in self.schema_variants.items() if not spec.get("symbols")]
        return unlisted[0] if len(unlisted) == 1 else None

    @property
    def research_root(self) -> Path:
        return self.path_of("storage.research_root")

    @property
    def l0_root(self) -> Path:
        return self.path_of("storage.l0_root")

    @property
    def l0_manifest_path(self) -> Path:
        return self.path_of("storage.l0_manifest")

    @property
    def recorder_symbols(self) -> list[str]:
        listed = self.get("recorder.symbols", None)
        return list(listed) if listed else self.symbols


def load_config(path: str | Path | None = None, env: dict[str, str] | None = None) -> DataConfig:
    """Pakia config na uhesabu `config_hash` (sha256 ya bytes za faili lenyewe)."""
    cfg_path = Path(path) if path is not None else default_config_path()
    if not cfg_path.is_file():
        raise ConfigError(f"config haipo: {cfg_path}")
    payload = cfg_path.read_bytes()
    parsed = yaml.safe_load(payload)
    if not isinstance(parsed, dict):
        raise ConfigError(f"config si mapping ya YAML: {cfg_path}")
    return DataConfig(
        raw=parsed,
        path=cfg_path,
        config_hash=sha256_bytes(payload),
        env=dict(os.environ if env is None else env),
    )
