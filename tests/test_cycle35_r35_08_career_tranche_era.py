"""R35-08 tests for MF35-08: the predeclared 48-key career tranche must
classify each key by its OWN season's source classification, never by a
program's most recent (or otherwise collapsed) classification.

The Cycle #35 manager follow-up independently checked all 48 predeclared
keys against the same-season membership source and found two wrong:
Massachusetts is labeled FBS at key K02 (season 2002) while the source says
FCS for 2002 (real-world accurate: UMass moved to FBS in 2012); Sacramento
State is labeled FBS at key K16 (season 2023) while the source says FCS for
2023. Both were correct about the program's CURRENT (2026) classification --
`load_population()` collapsed every season's classification to whichever
membership file's row for that program was read LAST, so a program's most
recent subdivision silently became its classification for every season it
ever played.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.cycle35.r35_05_career_tranche as tranche  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


class LoadPopulationTests(unittest.TestCase):
    def _load_with_files(self, early: list[dict], late: list[dict], current: list[dict]):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            early_path, late_path, current_path = (
                tmp / "early.jsonl", tmp / "late.jsonl", tmp / "current.jsonl"
            )
            _write_jsonl(early_path, early)
            _write_jsonl(late_path, late)
            _write_jsonl(current_path, current)
            originals = (
                tranche.HISTORICAL_EARLY, tranche.HISTORICAL_LATE, tranche.CURRENT_PROGRAMS
            )
            tranche.HISTORICAL_EARLY = early_path
            tranche.HISTORICAL_LATE = late_path
            tranche.CURRENT_PROGRAMS = current_path
            try:
                return tranche.load_population()
            finally:
                (
                    tranche.HISTORICAL_EARLY,
                    tranche.HISTORICAL_LATE,
                    tranche.CURRENT_PROGRAMS,
                ) = originals

    def test_stable_classification_program_is_unaffected(self) -> None:
        programs = self._load_with_files(
            early=[{"program_id": "P:A", "display_name": "Stable U", "classification": "fbs", "season": 2001}],
            late=[{"program_id": "P:A", "display_name": "Stable U", "classification": "fbs", "season": 2015}],
            current=[{"program_id": "P:A", "display_name": "Stable U", "classification": "fbs", "season": 2026}],
        )
        entry = programs["P:A"]
        self.assertEqual(tranche.same_season_classification(entry, 2001), "fbs")
        self.assertEqual(tranche.same_season_classification(entry, 2015), "fbs")
        self.assertEqual(tranche.same_season_classification(entry, 2026), "fbs")

    def test_transitioning_program_keeps_each_seasons_own_classification(self) -> None:
        """Reproduces the exact Massachusetts pattern: FCS in an early
        season, FBS by the current season. The early season's classification
        must not be overwritten by the later file's row."""
        programs = self._load_with_files(
            early=[{"program_id": "P:UMASS", "display_name": "Massachusetts", "classification": "fcs", "season": 2002}],
            late=[{"program_id": "P:UMASS", "display_name": "Massachusetts", "classification": "fbs", "season": 2015}],
            current=[{"program_id": "P:UMASS", "display_name": "Massachusetts", "classification": "fbs", "season": 2026}],
        )
        entry = programs["P:UMASS"]
        self.assertEqual(tranche.same_season_classification(entry, 2002), "fcs")
        self.assertEqual(tranche.same_season_classification(entry, 2015), "fbs")
        self.assertEqual(tranche.same_season_classification(entry, 2026), "fbs")

    def test_unstated_season_has_no_classification(self) -> None:
        """A season the source never mentions must not silently inherit
        some other season's classification."""
        programs = self._load_with_files(
            early=[{"program_id": "P:X", "display_name": "X", "classification": "fcs", "season": 2001}],
            late=[], current=[],
        )
        entry = programs["P:X"]
        self.assertIsNone(tranche.same_season_classification(entry, 1999))

    def test_real_massachusetts_and_sacramento_state_are_correctly_split(self) -> None:
        """Direct reproduction against the actual production membership
        files, matching the manager's independent same-season check."""
        programs = tranche.load_population()
        umass = next(
            (e for e in programs.values() if e.get("display_name") == "Massachusetts"),
            None,
        )
        sac_state = next(
            (e for e in programs.values() if e.get("display_name") == "Sacramento State"),
            None,
        )
        if umass is None or sac_state is None:
            self.skipTest("production membership files not present in this environment")
        self.assertEqual(tranche.same_season_classification(umass, 2002), "fcs")
        self.assertEqual(tranche.same_season_classification(sac_state, 2023), "fcs")


class PredeclareKeysTests(unittest.TestCase):
    def test_a_key_is_classified_by_its_own_seasons_source_not_the_programs_latest(self) -> None:
        """Directly exercises predeclare_keys with a hand-built population:
        one program whose EARLY-band seasons are FCS and whose LATE/CURRENT
        seasons are FBS. Any key predeclared at an early-band season for
        this program must come out classified fcs, and any key at a
        late/current season must come out fbs -- never the same value for
        both just because one program record was collapsed."""
        entry = {
            "program_id": "P:TRANSITION",
            "display_name": "Transition State",
            "seasons": set(tranche.SEASON_LADDER),
            "classification_by_season": {},
        }
        for season in tranche.SEASON_LADDER:
            entry["classification_by_season"][season] = "fcs" if season <= 2005 else "fbs"
        programs = {"P:TRANSITION": entry}

        keys = tranche.predeclare_keys(programs)
        by_season = {k["season"]: k for k in keys}
        for season, key in by_season.items():
            expected = "fcs" if season <= 2005 else "fbs"
            self.assertEqual(
                key["classification"], expected,
                f"season {season} should be {expected}, got {key['classification']}",
            )

    def test_program_never_appears_in_a_division_its_source_never_states(self) -> None:
        """A program with ONLY fcs-classified seasons must never produce an
        fbs key, and vice versa -- proves the division loop doesn't fall
        back to accepting a mismatched program when its pool runs dry."""
        entry_fcs_only = {
            "program_id": "P:ONLY_FCS",
            "display_name": "Only FCS",
            "seasons": set(tranche.SEASON_LADDER),
            "classification_by_season": {s: "fcs" for s in tranche.SEASON_LADDER},
        }
        keys = tranche.predeclare_keys({"P:ONLY_FCS": entry_fcs_only})
        classifications = {k["classification"] for k in keys}
        self.assertEqual(classifications, {"fcs"})

    def test_every_key_names_its_classification_authority(self) -> None:
        entry = {
            "program_id": "P:A",
            "display_name": "A",
            "seasons": set(tranche.SEASON_LADDER),
            "classification_by_season": {s: "fbs" for s in tranche.SEASON_LADDER},
        }
        keys = tranche.predeclare_keys({"P:A": entry})
        self.assertTrue(keys)
        for key in keys:
            self.assertEqual(key["classification_authority"], "SAME_SEASON_MEMBERSHIP_ROW")

    def test_real_population_still_reaches_48_keys(self) -> None:
        """The fix must not shrink the tranche below its required size just
        because classification is now checked more strictly."""
        programs = tranche.load_population()
        if not programs:
            self.skipTest("production membership files not present in this environment")
        keys = tranche.predeclare_keys(programs)
        self.assertEqual(len(keys), 2 * tranche.TARGET_PER_DIVISION)


class SampleReconciliationTests(unittest.TestCase):
    """Cycle #35 follow-up item 5: the corrected era-fixed 48-key sample
    changes 40 of 48 semantic keys relative to the original predeclaration
    (only 8 overlap). Reconciling by mutable key_id (K01, K02, ...) would
    compare the wrong rows at a shared id and miss matching rows that
    happen to land at different ids after a cascading reindex; these tests
    exercise reconciliation by the stable (program_id, season, role)
    semantic key instead.
    """

    def _key(self, **overrides) -> dict:
        row = {
            "key_id": "K01", "program_id": "P:A", "season": 2020, "role": "head_coach",
            "classification": "fbs", "disposition": "ACCEPTED_SINGLE_SOURCE",
        }
        row.update(overrides)
        return row

    def test_semantic_key_ignores_key_id(self) -> None:
        a = self._key(key_id="K01")
        b = self._key(key_id="K47")
        self.assertEqual(tranche.semantic_key(a), tranche.semantic_key(b))

    def test_semantic_key_differs_on_program_season_or_role(self) -> None:
        base = tranche.semantic_key(self._key())
        self.assertNotEqual(base, tranche.semantic_key(self._key(program_id="P:B")))
        self.assertNotEqual(base, tranche.semantic_key(self._key(season=2021)))
        self.assertNotEqual(
            base, tranche.semantic_key(self._key(role="defensive_coordinator"))
        )

    def test_identical_key_at_different_ids_is_retained(self) -> None:
        old = [self._key(key_id="K02")]
        new = [self._key(key_id="K28")]
        result = tranche.reconcile_tranche_samples(old, new)
        self.assertEqual(result["status_counts"], {"RETAINED": 1})
        self.assertEqual(result["entries"][0]["old_key_id"], "K02")
        self.assertEqual(result["entries"][0]["new_key_id"], "K28")

    def test_key_present_only_in_old_is_superseded(self) -> None:
        old = [self._key(program_id="P:GONE")]
        new: list[dict] = []
        result = tranche.reconcile_tranche_samples(old, new)
        self.assertEqual(result["status_counts"], {"SUPERSEDED": 1})

    def test_key_present_only_in_new_is_added(self) -> None:
        old: list[dict] = []
        new = [self._key(program_id="P:NEW")]
        result = tranche.reconcile_tranche_samples(old, new)
        self.assertEqual(result["status_counts"], {"ADDED": 1})

    def test_changed_classification_is_reclassified_not_superseded_plus_added(
        self,
    ) -> None:
        """The exact Massachusetts/Sacramento State pattern: same program,
        season and role, but the classification correction changed which
        division it belongs to. This must be ONE reclassified entry, never
        two separate supersede/add entries that hide the connection."""
        old = [self._key(classification="fbs")]
        new = [self._key(classification="fcs")]
        result = tranche.reconcile_tranche_samples(old, new)
        self.assertEqual(result["status_counts"], {"RECLASSIFIED": 1})
        entry = result["entries"][0]
        self.assertEqual(entry["old_classification"], "fbs")
        self.assertEqual(entry["new_classification"], "fcs")

    def test_changed_disposition_same_classification_is_disposition_changed(self) -> None:
        old = [self._key(disposition="MISSING_NO_EVIDENCE")]
        new = [self._key(disposition="ACCEPTED_SINGLE_SOURCE")]
        result = tranche.reconcile_tranche_samples(old, new)
        self.assertEqual(result["status_counts"], {"DISPOSITION_CHANGED": 1})

    def test_union_count_matches_status_counts(self) -> None:
        old = [self._key(program_id="P:SHARED"), self._key(program_id="P:OLD_ONLY")]
        new = [self._key(program_id="P:SHARED"), self._key(program_id="P:NEW_ONLY")]
        result = tranche.reconcile_tranche_samples(old, new)
        self.assertEqual(result["union_distinct_semantic_key_count"], 3)
        self.assertEqual(sum(result["status_counts"].values()), 3)

    def test_never_claims_either_sample_is_fully_verified(self) -> None:
        result = tranche.reconcile_tranche_samples([self._key()], [self._key()])
        self.assertTrue(result["neither_sample_is_all_48_verified"])
        self.assertTrue(result["no_acquisition_performed_no_budget_requested"])

    def test_real_old_and_new_samples_reconcile_to_manager_reported_counts(self) -> None:
        """Direct reproduction of the manager's own independently-computed
        numbers: 8 retained, union of 88 distinct semantic keys."""
        old_path = Path(
            r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
            r"\implementation_output\R35_05_CAREER_TRANCHE_FINAL.json"
        )
        new_path = Path(
            r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
            r"\20260920T215454Z_mf35_08_era_fix\implementation_output"
            r"\R35_05_CAREER_TRANCHE_FINAL.json"
        )
        if not old_path.is_file() or not new_path.is_file():
            self.skipTest("real resolved tranche artifacts not present in this environment")
        old_payload = json.loads(old_path.read_text(encoding="utf-8"))
        new_payload = json.loads(new_path.read_text(encoding="utf-8"))
        result = tranche.reconcile_tranche_samples(
            old_payload["final_keys"], new_payload["final_keys"]
        )
        self.assertEqual(result["union_distinct_semantic_key_count"], 88)
        self.assertEqual(result["status_counts"].get("RETAINED"), 8)


if __name__ == "__main__":
    unittest.main()
