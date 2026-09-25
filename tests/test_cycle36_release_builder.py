"""R36-07: the release must be deterministic, and its invalidations must bite.

Two builds from identical frozen inputs must be identical at scientific
content grain while the audit clock differs. Removing a support row, changing
a raw input's bytes, or pointing a program at the wrong school must each
change the release rather than pass unnoticed.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.release_builder import (  # noqa: E402
    CANDIDATE,
    CONFIRMED,
    NO_EVIDENCE,
    SCIENTIFIC_TABLES,
    ReleaseInputs,
    build_release,
    compare_releases,
    table_digest,
)

CROSSWALK = {
    "crosswalk_version": "test-v1",
    "programs": [
        {
            "canonical_program_id": "SRC-002:TEAM:245",
            "source_namespace": "SRC-002",
            "source_entity_id": "245",
            "display_names": ["Texas A&M"],
            "in_football_population": True,
        },
        {
            "canonical_program_id": "SRC-002:TEAM:2837",
            "source_namespace": "SRC-002",
            "source_entity_id": "2837",
            "display_names": ["East Texas A&M", "Texas A&M-Commerce"],
            "in_football_population": False,
        },
    ],
    "aliases": {
        "texas a m": [
            {
                "canonical_program_id": "SRC-002:TEAM:245",
                "original_alias": "Texas A&M",
                "normalized_alias": "texas a m",
                "alias_basis": "SOURCE_SCHOOL_NAME",
                "effective_state": "EFFECTIVE_INTERVAL_UNKNOWN_FROM_THIS_SOURCE",
            }
        ],
        "texas a m commerce": [
            {
                "canonical_program_id": "SRC-002:TEAM:2837",
                "original_alias": "Texas A&M-Commerce",
                "normalized_alias": "texas a m commerce",
                "alias_basis": "SOURCE_ALTERNATE_NAME",
                "effective_state": "EFFECTIVE_INTERVAL_FROM_CITED_RENAME_SOURCE",
                "effective_end": "2024-11-07",
                "rename_source_url": "https://example.invalid/rename",
            }
        ],
    },
    "rename_evidence": {},
    "conflicts": {"collisions": []},
}

POPULATION = {
    "declared_scope": [2025, 2026],
    "program_season_keys": 2,
    "population_by_season": [
        {
            "season": 2025,
            "programs": 1,
            "rows": 1,
            "FBS": 1,
            "FCS": 0,
            "PRE_CLASSIFICATION_ERA": 0,
            "OTHER_DIVISION": 0,
            "UNKNOWN": 0,
            "state": "MEMBERSHIP_PRESENT",
        },
        {
            "season": 2026,
            "programs": 1,
            "rows": 1,
            "FBS": 1,
            "FCS": 0,
            "PRE_CLASSIFICATION_ERA": 0,
            "OTHER_DIVISION": 0,
            "UNKNOWN": 0,
            "state": "MEMBERSHIP_PRESENT",
        },
    ],
    "unresolved_program_names": [
        {
            "raw_name": "Albany",
            "state": "UNRESOLVED_NAME_MATCHES_MORE_THAN_ONE_CANONICAL_PROGRAM",
            "seasons": [2025],
            "candidate_program_ids": ["SRC-002:TEAM:399", "SRC-002:TEAM:2013"],
            "detail": "ambiguous",
        }
    ],
}

MEMBERSHIP = [
    {
        "program_id": "SRC-002:TEAM:245",
        "season": 2025,
        "classification": "fbs",
        "era": "FBS_PLUS_FCS",
        "membership_authority": "PER_ROW_DECLARED_SEASON",
    },
    {
        "program_id": "SRC-002:TEAM:245",
        "season": 2026,
        "classification": "fbs",
        "era": "FBS_PLUS_FCS",
        "membership_authority": "EXACT_TRANSFORM_REPRODUCTION",
    },
]

OBSERVATIONS = [
    {
        "capture_path": "cache://a.html",
        "payload_sha256": "a" * 64,
        "program_id": "SRC-002:TEAM:245",
        "display_name": "Texas A&M",
        "person": "A Person",
        "source_title": "Head Football Coach",
        "record_selector": "tr[0]",
        "person_body_offset": 100,
        "person_record_bound": True,
        "role_claim_supported": True,
        "evidence_tier": "OFFICIAL_HTML_RECORD_BOUND",
        "season": 2026,
        "season_state": "SEASON_BOUND_BY_GOVERNING_SECTION_HEADING",
        "source_class": "OFFICIAL_STAFF_HTML",
        "pit_admitted": False,
        "assignments": [
            {
                "role": "head_coach",
                "unit": "TEAM",
                "qualifiers": [],
                "occupancy": "PRINCIPAL",
                "taxonomy_version": "t1",
                "play_caller_inferred": False,
            }
        ],
    },
    {
        "capture_path": "cache://a.html",
        "payload_sha256": "a" * 64,
        "program_id": "SRC-002:TEAM:245",
        "display_name": "Texas A&M",
        "person": "B Person",
        "source_title": "Director of Player Personnel",
        "record_selector": "tr[1]",
        "person_body_offset": 200,
        "person_record_bound": True,
        "role_claim_supported": True,
        "evidence_tier": "OFFICIAL_HTML_RECORD_BOUND",
        "season": 2026,
        "season_state": "SEASON_BOUND_BY_GOVERNING_SECTION_HEADING",
        "source_class": "OFFICIAL_STAFF_HTML",
        "pit_admitted": False,
        "assignments": [
            {
                "role": "player_personnel",
                "unit": "PROGRAM",
                "qualifiers": [],
                "occupancy": "OBSERVED",
                "taxonomy_version": "t1",
                "play_caller_inferred": False,
            }
        ],
    },
]

SCHEMES = [
    {
        "canonical_program_id": "SRC-002:TEAM:245",
        "season": 2026,
        "side": "OFFENSE",
        "source_text": "[[Air raid offense|Air raid]]",
        "normalized_families": ["AIR_RAID"],
        "source_disposition": "SOURCE_REPORTED_FAMILY_TAGGED",
        "state": "ADMITTED_CANDIDATE_SCHEME_ASSERTION",
        "evidence_tier": "CANDIDATE_SINGLE_SOURCE_NOT_OFFICIAL",
        "official_corroboration": "WIKIPEDIA_ONLY_NOT_OFFICIAL",
        "page_title": "2026 Texas A&M Aggies football team",
        "wikimedia_revision": "1",
        "pit_admitted": False,
        "inferred_from_title": False,
    }
]

CONFLICTS = [
    {
        "page_title": "Somewhere under a coach",
        "season": None,
        "side": "OFFENSE",
        "conflict_texts": ["Run and shoot", "West Coast"],
        "program_resolution_state": "UNRESOLVED_NO_DECLARED_NAME_MATCHES_THIS_QUERY",
    }
]

RESPONSIBILITY = [
    {
        "person": "A Person",
        "program_id": "SRC-002:TEAM:245",
        "season": 2026,
        "source_title": "Head Football Coach",
        "evidence_code": "HEAD_COACH_TITLE_IS_NOT_PLAY_CALLING",
        "disposition": "REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT",
        "inferred_from_role_title": False,
        "pit_admitted": False,
    }
]


class ReleaseFixture:
    def __init__(self) -> None:
        self.holder = tempfile.TemporaryDirectory()
        self.root = Path(self.holder.name)
        self.write()

    def write(self, observations=None, crosswalk=None) -> None:
        def jsonl(name: str, rows) -> Path:
            path = self.root / name
            path.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
                newline="\n",
            )
            return path

        def js(name: str, payload) -> Path:
            path = self.root / name
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
            )
            return path

        self.inputs = ReleaseInputs(
            population=js("population.json", POPULATION),
            membership_rows=jsonl("membership.jsonl", MEMBERSHIP),
            crosswalk=js("crosswalk.json", crosswalk or CROSSWALK),
            staff_observations=jsonl(
                "observations.jsonl", observations if observations is not None else OBSERVATIONS
            ),
            staff_captures=jsonl("captures.jsonl", [{"capture_path": "cache://a.html"}]),
            scheme_assertions=jsonl("schemes.jsonl", SCHEMES),
            scheme_conflicts=jsonl("conflicts.jsonl", CONFLICTS),
            responsibility_assertions=jsonl("responsibility.jsonl", RESPONSIBILITY),
            career_episodes=jsonl("career.jsonl", CAREER_EPISODES),
        )

    def build(self, name: str, label: str = "r1", audit=None) -> Path:
        destination = self.root / name
        build_release(
            self.inputs,
            destination,
            build_label=label,
            audit=audit or {"built_at_utc": f"clock-{label}"},
        )
        return destination

    def close(self) -> None:
        self.holder.cleanup()


class DeterminismTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ReleaseFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_two_builds_are_identical_at_scientific_grain(self) -> None:
        first = self.fixture.build("a.sqlite", "r1", {"built_at_utc": "one"})
        second = self.fixture.build("b.sqlite", "replay", {"built_at_utc": "two"})
        comparison = compare_releases(first, second)
        self.assertTrue(
            comparison["all_identical_at_scientific_grain"],
            [name for name, row in comparison["per_table"].items() if not row["identical"]],
        )

    def test_the_audit_clock_really_does_differ(self) -> None:
        """The exclusion must be needed, not a way to make replay look clean."""

        first = self.fixture.build("a.sqlite", "r1", {"built_at_utc": "one"})
        second = self.fixture.build("b.sqlite", "replay", {"built_at_utc": "two"})
        self.assertNotEqual(
            table_digest(first, "audit_execution"),
            table_digest(second, "audit_execution"),
        )
        self.assertIn("audit_execution", compare_releases(first, second)["excluded_tables"])

    def test_removing_a_support_row_changes_the_release(self) -> None:
        first = self.fixture.build("a.sqlite")
        self.fixture.write(observations=OBSERVATIONS[:1])
        second = self.fixture.build("b.sqlite")
        comparison = compare_releases(first, second)
        self.assertFalse(comparison["all_identical_at_scientific_grain"])
        self.assertFalse(comparison["per_table"]["staff_observation"]["identical"])

    def test_changed_raw_bytes_change_the_source_digest(self) -> None:
        first = self.fixture.build("a.sqlite")
        (self.fixture.root / "membership.jsonl").write_text(
            (self.fixture.root / "membership.jsonl").read_text(encoding="utf-8")
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        second = self.fixture.build("b.sqlite")
        self.assertFalse(
            compare_releases(first, second)["per_table"]["source_file"]["identical"]
        )

    def test_pointing_a_program_at_the_wrong_school_changes_identity(self) -> None:
        first = self.fixture.build("a.sqlite")
        wrong = json.loads(json.dumps(CROSSWALK))
        wrong["aliases"]["texas a m"][0]["canonical_program_id"] = "SRC-002:TEAM:2837"
        self.fixture.write(crosswalk=wrong)
        second = self.fixture.build("b.sqlite")
        self.assertFalse(
            compare_releases(first, second)["per_table"]["program_alias"]["identical"]
        )


#: Two episodes: one that resolves an employer, a specific role and an
#: interval, and one refused because its employer is a high school. Both must
#: reach the release -- a table holding only the joinable one would make the
#: corpus look far cleaner than it is.
CAREER_EPISODES = [
    {
        "span_id": "wikimedia:A Coach:1:career:0:head_coach",
        "pageid": "1",
        "page_title": "A Coach",
        "episode_index": 0,
        "person_display_name": "A Coach",
        "employer_raw": "Texas A&M",
        "employer_resolution_state": "RESOLVED_SINGLE_CANONICAL_PROGRAM",
        "employer_program_id": "SRC-002:TEAM:245",
        "source_title": "head coach",
        "role_codes": ["head_coach"],
        "start_year": 2015,
        "end_year": 2017,
        "ongoing": False,
        "evidence_class": "RETROSPECTIVE_CANDIDATE_ONLY",
        "state": "CANDIDATE_CAREER_EPISODE_RETAINED_NOT_JOINED",
        "flags": [],
        "joined": False,
        "pit_admitted": False,
    },
    {
        "span_id": "wikimedia:A Coach:1:career:1:UNKNOWN",
        "pageid": "1",
        "page_title": "A Coach",
        "episode_index": 1,
        "person_display_name": "A Coach",
        "employer_raw": "Stamford HS",
        "employer_resolution_state": "UNRESOLVED_NO_DECLARED_NAME_MATCHES_THIS_QUERY",
        "employer_program_id": None,
        "source_title": "TX",
        "role_codes": [],
        "start_year": 1967,
        "end_year": 1968,
        "ongoing": False,
        "evidence_class": "RETROSPECTIVE_CANDIDATE_ONLY",
        "state": "REFUSED_EMPLOYER_RESOLVES_TO_NO_DECLARED_PROGRAM",
        "flags": ["SOURCE_PARSE_ARTIFACT_TITLE_LOOKS_LIKE_AN_EMPLOYER_QUALIFIER"],
        "joined": False,
        "pit_admitted": False,
    },
]


class ContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ReleaseFixture()
        self.database = self.fixture.build("release.sqlite")
        self.connection = sqlite3.connect(
            f"file:{self.database.as_posix()}?mode=ro", uri=True
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.fixture.close()

    def scalar(self, sql: str, params=()) -> object:
        return self.connection.execute(sql, params).fetchone()[0]

    def test_coverage_comes_from_rows(self) -> None:
        delivered = self.scalar(
            "SELECT value FROM coverage_summary "
            "WHERE grain='PROGRAM_SEASON' AND bucket='DELIVERED_MEMBERSHIP_ROWS'"
        )
        actual = self.scalar("SELECT COUNT(*) FROM program_season_membership")
        self.assertEqual(delivered, actual)

    def test_non_core_roles_survive_into_the_release(self) -> None:
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM staff_role_assignment WHERE role_code='player_personnel'"
            ),
            1,
        )

    def test_nothing_was_promoted_to_a_core_role(self) -> None:
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM staff_role_assignment "
                "WHERE is_core_role=1 AND role_code<>'head_coach'"
            ),
            0,
        )

    def test_a_season_less_conflict_is_still_a_row(self) -> None:
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM scheme_conflict"), 1)
        self.assertIsNone(self.scalar("SELECT season FROM scheme_conflict"))

    def test_a_rejected_responsibility_candidate_is_kept(self) -> None:
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM responsibility_assertion "
                "WHERE disposition LIKE 'REJECTED%'"
            ),
            1,
        )

    def test_no_row_is_pit_admitted(self) -> None:
        for table in ("staff_observation", "scheme_assertion", "responsibility_assertion"):
            with self.subTest(table=table):
                self.assertEqual(
                    self.scalar(f"SELECT COUNT(*) FROM {table} WHERE pit_admitted=1"), 0
                )

    def test_a_refused_career_episode_is_still_a_row(self) -> None:
        """The refusals are the finding, so they must be in the release."""

        self.assertEqual(self.scalar("SELECT COUNT(*) FROM career_episode"), 2)
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM career_episode WHERE state=?",
                ("REFUSED_EMPLOYER_RESOLVES_TO_NO_DECLARED_PROGRAM",),
            ),
            1,
        )

    def test_no_career_episode_is_joined_or_admitted(self) -> None:
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM career_episode WHERE joined=1"), 0
        )
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM career_episode WHERE pit_admitted=1"), 0
        )

    def test_a_career_episode_keeps_its_source_flags(self) -> None:
        flags = self.scalar(
            "SELECT flags FROM career_episode WHERE employer_raw=?", ("Stamford HS",)
        )
        self.assertIn("SOURCE_PARSE_ARTIFACT", flags)

    def test_unresolved_names_are_rows_not_omissions(self) -> None:
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM unresolved_program_name"), 1)

    def test_core_cells_cover_every_membership_row_times_three_roles(self) -> None:
        memberships = self.scalar("SELECT COUNT(*) FROM program_season_membership")
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM core_role_cell"), memberships * 3
        )

    def test_confirmed_candidate_and_no_evidence_partition_the_cells(self) -> None:
        total = self.scalar("SELECT COUNT(*) FROM core_role_cell")
        parts = sum(
            self.scalar(
                "SELECT COUNT(*) FROM core_role_cell WHERE coverage_state=?", (state,)
            )
            for state in (CONFIRMED, CANDIDATE, NO_EVIDENCE)
        )
        self.assertEqual(total, parts)

    def test_every_scientific_table_exists(self) -> None:
        names = {
            row[0]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in SCIENTIFIC_TABLES:
            with self.subTest(table=table):
                self.assertIn(table, names)

    def test_declared_inputs_are_rehashed_into_the_release(self) -> None:
        rows = self.scalar("SELECT COUNT(*) FROM source_file WHERE sha256 IS NOT NULL")
        self.assertEqual(rows, len(self.fixture.inputs.as_pairs()))


if __name__ == "__main__":
    unittest.main()
