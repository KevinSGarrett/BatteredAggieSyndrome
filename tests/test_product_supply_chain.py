from __future__ import annotations

import importlib.metadata
import tempfile
import unittest
from pathlib import Path

from tools.validate_dependency_policy import dependency_policy_errors
from tools.validate_product_supply_chain import (
    LockEntry,
    build_installed_inventory,
    parse_lock,
    parse_lock_text,
)


ROOT = Path(__file__).resolve().parents[1]
VALID_HASH_A = "a" * 64
VALID_HASH_B = "b" * 64


class _Metadata(dict):
    def get_all(self, key: str):
        return self.get(key, [])


class _Distribution:
    def __init__(self, version: str, metadata: _Metadata, files: list[str]):
        self.version = version
        self.metadata = metadata
        self.files = files


class ProductSupplyChainTests(unittest.TestCase):
    def test_repository_lock_is_exact_hash_pinned(self) -> None:
        entries = parse_lock(ROOT / "requirements" / "product.lock")
        self.assertEqual(14, len(entries))
        self.assertEqual(len(entries), len({entry.normalized_name for entry in entries}))
        self.assertTrue(all(entry.hashes for entry in entries))
        self.assertTrue(
            all(len(value) == 64 for entry in entries for value in entry.hashes)
        )

    def test_missing_hash_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing --hash"):
            parse_lock_text("example==1.0\n")

    def test_malformed_hash_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "malformed SHA-256"):
            parse_lock_text("example==1.0 --hash=sha256:not-a-digest\n")

    def test_duplicate_package_is_rejected(self) -> None:
        payload = (
            f"Example_Pkg==1.0 --hash=sha256:{VALID_HASH_A}\n"
            f"example-pkg==1.0 --hash=sha256:{VALID_HASH_B}\n"
        )
        with self.assertRaisesRegex(ValueError, "duplicate package"):
            parse_lock_text(payload)

    def test_direct_product_pins_match_lock(self) -> None:
        direct_count, lock_count, failures = dependency_policy_errors(ROOT)
        self.assertEqual(2, direct_count)
        self.assertEqual(14, lock_count)
        self.assertEqual([], failures)

    def test_installed_inventory_is_sorted_and_requires_license_evidence(self) -> None:
        entries = [
            LockEntry("Zulu", "2.0", None, (VALID_HASH_A,)),
            LockEntry("alpha", "1.0", None, (VALID_HASH_B,)),
            LockEntry(
                "windows-only",
                "1.0",
                'platform_system == "Windows"',
                (VALID_HASH_A,),
            ),
        ]
        distributions = {
            "alpha": _Distribution(
                "1.0",
                _Metadata({"License-Expression": "MIT"}),
                ["alpha-1.0.dist-info/licenses/LICENSE"],
            ),
            "Zulu": _Distribution("2.0", _Metadata({}), []),
        }

        def get_distribution(name: str):
            if name not in distributions:
                raise importlib.metadata.PackageNotFoundError(name)
            return distributions[name]

        packages, errors = build_installed_inventory(
            entries,
            distribution_getter=get_distribution,
            platform_system="Linux",
        )
        self.assertEqual(["alpha", "zulu"], [item["name"] for item in packages])
        self.assertEqual("SPDX_EXPRESSION", packages[0]["license_metadata_kind"])
        self.assertEqual(2, len(errors))
        self.assertTrue(any("missing license metadata" in item for item in errors))
        self.assertTrue(any("missing installed license/notice" in item for item in errors))

    def test_lock_parser_rejects_interrupted_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "product.lock"
            lock.write_text(
                f"example==1.0 \\\n\n  --hash=sha256:{VALID_HASH_A}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "continuation interrupted"):
                parse_lock(lock)


if __name__ == "__main__":
    unittest.main()
