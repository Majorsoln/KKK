"""DF-01/DF-03 — SHA256 kwa kila partition, manifest, na immutability.

Spec: `docs/DATA_FEATURE_STANDARD.md` §2 (immutable, append-only, hashed) + §8
Rejista: DF-01 (UT + CI hash check kila build), DF-03 (provenance)
"""

from __future__ import annotations

import json

import pytest

from src.data.hashing import is_sha256, sha256_bytes, sha256_file
from src.data.manifest import (
    L0Manifest,
    ManifestError,
    PROVENANCE_AGGREGATOR,
    PROVENANCE_BROKER,
    hash_l0_tree,
    iter_partitions,
    provenance_from_path,
    symbol_from_path,
)
from tests.conftest import variant_a_frame


def test_sha256_ina_muundo_unaotambulika():
    digest = sha256_bytes(b"elitefx")
    assert is_sha256(digest)
    assert digest.startswith("sha256:") and len(digest) == 7 + 64


def test_sha256_ya_faili_ni_thabiti_na_nyeti(tmp_path):
    path = tmp_path / "p.bin"
    path.write_bytes(b"a" * 10_000)
    first = sha256_file(path)
    assert sha256_file(path) == first
    path.write_bytes(b"a" * 9_999 + b"b")
    assert sha256_file(path) != first


def test_njia_ya_partition_inatoa_symbol_na_provenance(cfg, aggregator_partitions, l0_root):
    a_path = aggregator_partitions["A"]
    assert symbol_from_path(a_path, cfg, l0_root) == "EURUSD"
    assert provenance_from_path(a_path, cfg, l0_root) == PROVENANCE_AGGREGATOR
    broker = l0_root / "provenance=broker" / "symbol=GBPJPY" / "date=2026-08-03" / "ticks.parquet"
    assert symbol_from_path(broker, cfg, l0_root) == "GBPJPY"
    assert provenance_from_path(broker, cfg, l0_root) == PROVENANCE_BROKER


def test_provenance_ya_default_inatoka_kwenye_config(cfg, l0_root):
    """Muundo wa §9 (`L0_raw/<symbol>/<year>/...`) hauna tag; default ni `source.provenance`."""
    path = l0_root / "EURUSD" / "2021" / "m1_bidask.parquet"
    assert provenance_from_path(path, cfg, l0_root) == cfg.provenance_default == "aggregator"
    assert symbol_from_path(path, cfg, l0_root) == "EURUSD"


def test_hash_l0_inahash_partitions_zote_na_kuandika_manifest(cfg, aggregator_partitions, l0_root):
    """Kazi ya 3 ya T0: hash partitions ZOTE za L0 zilizopo + rekodi manifest."""
    manifest, result = hash_l0_tree(cfg, l0_root=l0_root, manifest_path=cfg.l0_manifest_path)
    assert result.scanned == len(iter_partitions(l0_root)) == 2
    assert result.added == 2 and result.ok
    assert len(manifest.entries) == 2

    for entry in manifest.entries.values():
        assert is_sha256(entry.sha256)
        assert entry.provenance == PROVENANCE_AGGREGATOR
        assert entry.rows == 6
        assert entry.schema_variant in {"A", "B"}
        assert entry.first_ts and entry.last_ts

    payload = json.loads(cfg.l0_manifest_path.read_text())
    assert payload["config_hash"] == cfg.config_hash
    assert payload["partition_count"] == 2
    assert payload["provenance_counts"] == {"aggregator": 2}


def test_hashing_mara_ya_pili_inathibitisha_bila_kuongeza(cfg, aggregator_partitions, l0_root):
    hash_l0_tree(cfg, l0_root=l0_root)
    _, second = hash_l0_tree(cfg, l0_root=l0_root)
    assert (second.added, second.confirmed) == (0, 2)
    assert second.ok


def test_partition_mpya_inaongezwa_kwa_append(cfg, aggregator_partitions, l0_root):
    hash_l0_tree(cfg, l0_root=l0_root)
    new_path = l0_root / "provenance=aggregator" / "symbol=EURUSD" / "2026" / "2026-08-04.parquet"
    variant_a_frame().to_parquet(new_path, index=False)
    manifest, result = hash_l0_tree(cfg, l0_root=l0_root)
    assert (result.added, result.confirmed) == (1, 2)
    assert len(manifest.entries) == 3


def test_kubadilisha_partition_ni_ukiukaji_wa_df01(cfg, aggregator_partitions, l0_root):
    """L0 haibadilishwi: hash iliyobadilika haiandikwi kimya — ni FAIL."""
    hash_l0_tree(cfg, l0_root=l0_root)
    target = aggregator_partitions["A"]
    frame = variant_a_frame()
    frame.loc[0, "bid"] = 1.5
    frame.to_parquet(target, index=False)

    manifest = L0Manifest.load(cfg.l0_manifest_path)
    with pytest.raises(ManifestError, match="DF-01"):
        manifest.record(target, cfg)

    _, result = hash_l0_tree(cfg, l0_root=l0_root)
    assert not result.ok
    assert manifest.key_for(target) in result.mutated


def test_verify_inagundua_mabadiliko_na_kupotea(cfg, aggregator_partitions, l0_root):
    """Lango la CI: verify inarudisha FAIL kwa partition iliyobadilika au iliyopotea."""
    manifest, _ = hash_l0_tree(cfg, l0_root=l0_root)
    assert manifest.verify().ok

    variant_a_frame().assign(bid=1.23).to_parquet(aggregator_partitions["A"], index=False)
    changed = manifest.verify()
    assert not changed.ok and len(changed.changed) == 1

    aggregator_partitions["B"].unlink()
    after_delete = manifest.verify()
    assert len(after_delete.missing) == 1


def test_verify_inaripoti_partition_isiyohashiwa(cfg, aggregator_partitions, l0_root):
    manifest, _ = hash_l0_tree(cfg, l0_root=l0_root)
    extra = l0_root / "provenance=aggregator" / "symbol=EURUSD" / "2026" / "2026-08-05.parquet"
    variant_a_frame().to_parquet(extra, index=False)
    result = manifest.verify()
    assert result.ok  # zilizopo hazijabadilika...
    assert result.untracked == [manifest.key_for(extra)]  # ...lakini hii bado haijahashiwa


def test_kuandika_juu_ya_hash_kunahitaji_sababu_na_kunaacha_alama(cfg, aggregator_partitions, l0_root):
    manifest, _ = hash_l0_tree(cfg, l0_root=l0_root)
    target = aggregator_partitions["A"]
    variant_a_frame().assign(ask=2.0).to_parquet(target, index=False)

    with pytest.raises(ManifestError, match="sababu"):
        manifest.record(target, cfg, allow_mutation=True)

    manifest.record(target, cfg, allow_mutation=True, mutation_reason="PD: chanzo kilirudiwa")
    assert len(manifest.mutation_log) == 1
    assert manifest.mutation_log[0]["reason"] == "PD: chanzo kilirudiwa"
    manifest.save()
    assert json.loads(cfg.l0_manifest_path.read_text())["mutation_log"][0]["partition"]


def test_manifest_inasomeka_upya_bila_kupoteza_kitu(cfg, aggregator_partitions, l0_root):
    manifest, _ = hash_l0_tree(cfg, l0_root=l0_root)
    reloaded = L0Manifest.load(cfg.l0_manifest_path)
    assert reloaded.entries.keys() == manifest.entries.keys()
    assert reloaded.config_hash == cfg.config_hash
    assert reloaded.verify().ok
