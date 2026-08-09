from __future__ import annotations

import json
import tempfile
from pathlib import Path

from aggie_analytics.operations.environment import (
    provision_external_operational_paths,
    resolve_external_operational_paths,
)
from tools.validate_external_storage_policy import EXPECTED_OPERATIONAL_ROOTS, validate


ROOT = Path(__file__).resolve().parents[1]


def test_external_operational_roots_are_exact_and_disjoint() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        repository = base / "repository"
        data_root = base / "external-data"
        repository.mkdir()
        resolved = resolve_external_operational_paths(repo_root=repository, value=data_root)
        assert set(resolved) == set(EXPECTED_OPERATIONAL_ROOTS)
        assert {path.relative_to(data_root).as_posix() for path in resolved.values()} == set(EXPECTED_OPERATIONAL_ROOTS.values())
        provisioned = provision_external_operational_paths(repo_root=repository, value=data_root)
        assert all(path.is_dir() for path in provisioned.values())
        assert all(repository not in path.parents for path in provisioned.values())


def test_external_storage_policy_is_machine_validated() -> None:
    assert validate(ROOT) == []
    policy = json.loads((ROOT / "configs" / "external_storage_policy.json").read_text(encoding="utf-8"))
    assert policy["legacy_sibling_root_policy"] == "NO_NEW_PROJECT_SPECIFIC_SIBLING_ROOTS"
    assert policy["historical_manifest_policy"] == "PRESERVE_ORIGINAL_IDENTITY_AND_LOCATION"
