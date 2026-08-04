"""CLI ya T0 — ndiyo uso wa milango ya CI (DF-01 hash check, DF-04 alert).

Exit codes ndizo mkataba: 0 = sawa/skipped · 1 = ONYO au ukiukaji · 2 = hitilafu.
"""

from __future__ import annotations

import json

import pytest

from src.data.cli import main
from tests.conftest import REPO_ROOT, variant_a_frame

CONFIG = str(REPO_ROOT / "config" / "data.yaml")


@pytest.fixture
def storage_env(monkeypatch, research_root):
    monkeypatch.setenv("ELITEFX_RESEARCH_ROOT", str(research_root))
    monkeypatch.setenv("ELITEFX_HOLDOUT_ROOT", str(research_root / "_holdout"))
    return research_root


def test_init_research_inasimamisha_muundo_wa_spec_9(storage_env, capsys):
    assert main(["--config", CONFIG, "init-research"]) == 0
    assert (storage_env / "data" / "L5_datasets").is_dir()
    assert "muundo wa research" in capsys.readouterr().out


def test_hash_l0_kisha_verify_l0_zinapita(storage_env, capsys):
    main(["--config", CONFIG, "init-research"])
    partition = storage_env / "data" / "L0_raw" / "symbol=EURUSD" / "2026-08-03.parquet"
    partition.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(partition, index=False)

    assert main(["--config", CONFIG, "hash-l0"]) == 0
    out = capsys.readouterr().out
    assert "scanned=1" in out and "added=1" in out

    assert main(["--config", CONFIG, "verify-l0", "--require-storage"]) == 0
    assert "verify-l0: PASS" in capsys.readouterr().out


def test_verify_l0_inafelisha_build_partition_ikibadilika(storage_env, capsys):
    main(["--config", CONFIG, "init-research"])
    partition = storage_env / "data" / "L0_raw" / "symbol=EURUSD" / "2026-08-03.parquet"
    partition.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(partition, index=False)
    main(["--config", CONFIG, "hash-l0"])
    capsys.readouterr()

    variant_a_frame().assign(bid=9.9).to_parquet(partition, index=False)
    assert main(["--config", CONFIG, "verify-l0"]) == 1
    captured = capsys.readouterr()
    assert "verify-l0: FAIL" in captured.out
    assert "IMEBADILIKA (DF-01)" in captured.err


def test_verify_l0_inaruka_pale_storage_haipo(monkeypatch, capsys):
    monkeypatch.delenv("ELITEFX_RESEARCH_ROOT", raising=False)
    assert main(["--config", CONFIG, "verify-l0"]) == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_check_freshness_inaruka_bila_storage(monkeypatch, capsys):
    monkeypatch.delenv("ELITEFX_RESEARCH_ROOT", raising=False)
    assert main(["--config", CONFIG, "check-freshness"]) == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_check_freshness_inatoa_json_na_exit_code(storage_env, tmp_path, capsys):
    main(["--config", CONFIG, "init-research"])
    out_file = tmp_path / "freshness.json"
    code = main(["--config", CONFIG, "check-freshness", "--json", "--out", str(out_file)])
    payload = json.loads(out_file.read_text())
    assert payload["status"] in {"SKIPPED", "NOT_STARTED"}
    assert code == (0 if payload["status"] == "SKIPPED" else 1)
    capsys.readouterr()


def test_inspect_inaonyesha_schema_moja(storage_env, capsys):
    partition = storage_env / "data" / "L0_raw" / "symbol=EURUSD" / "2026-08-03.parquet"
    partition.parent.mkdir(parents=True, exist_ok=True)
    variant_a_frame().to_parquet(partition, index=False)
    assert main(["--config", CONFIG, "inspect", str(partition)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_variant"] == "A"
    assert payload["rows"] == 6


def test_config_hash_inatoka_kwenye_faili_la_config(capsys):
    assert main(["--config", CONFIG, "config-hash"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["config_hash"].startswith("sha256:")


def test_hitilafu_ya_config_inarudisha_exit_2(capsys):
    assert main(["--config", "/haipo/data.yaml", "config-hash"]) == 2
    assert "HITILAFU" in capsys.readouterr().err
