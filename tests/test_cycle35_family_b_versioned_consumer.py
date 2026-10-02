"""Cycle #35 closeout review (20260921T025300Z), section 5: the isolated
Family B consumer.

"`R35_10_FAMILY_B_CANDIDATE.json` still explicitly reports
code_sidecar_matches_live_gate=false and describes the stale BAT-637
consumer constant as a separate unimplemented change... A JSON
`successor_pair` declaration and repeated child hashes are not a wired,
passing consumer."

The consumer now resolves its BAT-637 dependency through a versioned
authority. LEGACY is the default and reproduces the canonical
predecessor exactly, including its disagreement with the live gate;
SUCCESSOR derives the pin from the contract that declares it. The Done
predecessor gate is not edited and the stale constant is not overwritten
with the observed live hash.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_1998_rejection_complete import (  # noqa: E402
    LEGACY_BAT637_GATE_IDENTITY,
    PIN_AUTHORITY_LEGACY,
    PIN_AUTHORITY_SUCCESSOR,
    PINNED_BAT637_GATE_IDENTITY,
    SUCCESSOR_CONTRACT_PIN_FIELD,
    SUCCESSOR_CONTRACT_RELATIVE,
    AuthorityViolation,
    resolve_bat637_pin,
)

LIVE_GATE = ROOT / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json"
DECLARING_CONTRACT = ROOT / SUCCESSOR_CONTRACT_RELATIVE


class PinAuthorityTests(unittest.TestCase):
    def test_the_default_authority_is_legacy(self) -> None:
        """Importing this module must never silently activate the
        successor. Activation is a separate explicit approval."""
        resolved = resolve_bat637_pin(repo_root=ROOT)
        self.assertEqual(resolved["pin_authority"], PIN_AUTHORITY_LEGACY)
        self.assertEqual(resolved["gate_identity"], LEGACY_BAT637_GATE_IDENTITY)

    def test_the_historical_constant_is_preserved_not_overwritten(self) -> None:
        """The stale pin keeps its recorded value. Pasting the observed
        live hash over it would destroy the evidence that they differed."""
        self.assertEqual(
            PINNED_BAT637_GATE_IDENTITY,
            "c1d2220943342e02bd55efdac6bf3a4992f5fcd4a00059e94cc21ea56581db4a",
        )
        if LIVE_GATE.is_file():
            live = json.loads(LIVE_GATE.read_text(encoding="utf-8-sig"))
            self.assertNotEqual(live.get("gate_identity"), PINNED_BAT637_GATE_IDENTITY)

    def test_the_successor_pin_comes_from_the_declaring_contract(self) -> None:
        if not DECLARING_CONTRACT.is_file():
            self.skipTest("declaring contract is absent")
        declared = json.loads(DECLARING_CONTRACT.read_text(encoding="utf-8-sig"))[
            SUCCESSOR_CONTRACT_PIN_FIELD
        ]
        resolved = resolve_bat637_pin(
            repo_root=ROOT, pin_authority=PIN_AUTHORITY_SUCCESSOR
        )
        self.assertEqual(resolved["gate_identity"], declared)
        self.assertIn(SUCCESSOR_CONTRACT_RELATIVE, resolved["declared_by"])

    def test_the_successor_pin_matches_the_live_gate(self) -> None:
        """The successor's declared dependency is the one the live gate
        actually carries -- which is why the successor path can pass while
        the legacy one cannot."""
        if not (DECLARING_CONTRACT.is_file() and LIVE_GATE.is_file()):
            self.skipTest("declaring contract or live gate is absent")
        resolved = resolve_bat637_pin(
            repo_root=ROOT, pin_authority=PIN_AUTHORITY_SUCCESSOR
        )
        live = json.loads(LIVE_GATE.read_text(encoding="utf-8-sig"))
        self.assertEqual(resolved["gate_identity"], live.get("gate_identity"))

    def test_an_unknown_authority_is_rejected_not_defaulted(self) -> None:
        with self.assertRaises(AuthorityViolation):
            resolve_bat637_pin(repo_root=ROOT, pin_authority="SOMETHING_ELSE")

    def test_an_absent_declaring_contract_is_an_authority_violation(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(AuthorityViolation):
                resolve_bat637_pin(
                    repo_root=Path(tmp), pin_authority=PIN_AUTHORITY_SUCCESSOR
                )

    def test_a_malformed_declared_pin_is_rejected_not_silently_accepted(self) -> None:
        for bogus in ("", "not-a-digest", "abc", "g" * 64, None):
            with self.subTest(bogus=bogus):
                with TemporaryDirectory() as tmp:
                    target = Path(tmp) / SUCCESSOR_CONTRACT_RELATIVE
                    target.parent.mkdir(parents=True, exist_ok=True)
                    payload = {} if bogus is None else {
                        SUCCESSOR_CONTRACT_PIN_FIELD: bogus
                    }
                    target.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(AuthorityViolation):
                        resolve_bat637_pin(
                            repo_root=Path(tmp),
                            pin_authority=PIN_AUTHORITY_SUCCESSOR,
                        )

    def test_a_malformed_pin_never_falls_back_to_the_stale_constant(self) -> None:
        """A silent fallback would make the successor path quietly become
        the legacy one."""
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / SUCCESSOR_CONTRACT_RELATIVE
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps({SUCCESSOR_CONTRACT_PIN_FIELD: "bad"}), encoding="utf-8"
            )
            try:
                resolved = resolve_bat637_pin(
                    repo_root=Path(tmp), pin_authority=PIN_AUTHORITY_SUCCESSOR
                )
            except AuthorityViolation:
                return
            self.fail(f"expected rejection, got {resolved}")


class CanonicalSeparationTests(unittest.TestCase):
    def test_the_legacy_pin_still_disagrees_with_the_live_gate(self) -> None:
        """The inherited canonical failure is real and must not be
        concealed by the successor work."""
        if not LIVE_GATE.is_file():
            self.skipTest("live gate is absent")
        live = json.loads(LIVE_GATE.read_text(encoding="utf-8-sig"))
        self.assertNotEqual(
            live.get("gate_identity"),
            resolve_bat637_pin(repo_root=ROOT, pin_authority=PIN_AUTHORITY_LEGACY)[
                "gate_identity"
            ],
        )

    def test_legacy_and_successor_pins_are_different_values(self) -> None:
        if not DECLARING_CONTRACT.is_file():
            self.skipTest("declaring contract is absent")
        legacy = resolve_bat637_pin(repo_root=ROOT, pin_authority=PIN_AUTHORITY_LEGACY)
        successor = resolve_bat637_pin(
            repo_root=ROOT, pin_authority=PIN_AUTHORITY_SUCCESSOR
        )
        self.assertNotEqual(legacy["gate_identity"], successor["gate_identity"])


if __name__ == "__main__":
    unittest.main()
