"""Config ya RCE — ndogo, na haitegemei kitu chochote nje ya RCE.

RCE ni mamlaka huru ya gharama, ukubwa, na ruhusa (DOCTRINE §18). Kwa hiyo
haiwezi kutegemea loader ya sehemu nyingine ya mfumo: sehemu hiyo ikibadilika
au ikiondolewa, RCE ingevunjika pamoja nayo.

Kinachohitajika ni kidogo: `get(dotted, default)` kwa moduli za RCE, pamoja na
`raw` na `config_hash` kwa ushahidi. Hakuna kingine.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_MISSING = object()


class ConfigError(RuntimeError):
    """Config haipo, si YAML, au kigezo kinachohitajika hakipo."""


@dataclass
class RiskConfig:
    """Config pamoja na fingerprint yake.

    `config_hash` ni sha256 ya **bytes za faili lenyewe**, si ya dict
    iliyochambuliwa. Faili likibadilika kwa namna yoyote — hata nafasi —
    fingerprint inabadilika, na kila log inayoiandika inaonyesha tofauti.
    """

    raw: dict[str, Any]
    path: Path
    config_hash: str

    def get(self, dotted: str, default: Any = _MISSING) -> Any:
        """Soma kigezo kwa `sehemu.sehemu`. Kikikosekana bila default → ConfigError."""
        node: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is _MISSING:
                    raise ConfigError(
                        f"kigezo `{dotted}` hakipo kwenye {self.path} — "
                        "PD anaongeza config, si code"
                    )
                return default
            node = node[part]
        return node


def load_config(path: str | Path) -> RiskConfig:
    cfg_path = Path(path)
    if not cfg_path.is_file():
        raise ConfigError(f"config haipo: {cfg_path}")
    payload = cfg_path.read_bytes()
    parsed = yaml.safe_load(payload)
    if not isinstance(parsed, dict):
        raise ConfigError(f"config si mapping ya YAML: {cfg_path}")
    return RiskConfig(
        raw=parsed,
        path=cfg_path,
        config_hash=hashlib.sha256(payload).hexdigest(),
    )
