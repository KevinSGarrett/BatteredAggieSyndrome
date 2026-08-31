"""Fail-closed coverage for the Week 1 2026 official schedule and identity universe."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.data.week1_2026_official_schedule_identity import (
    ADMITTED_MODEL_ELIGIBLE,
    AMBIGUOUS_KICKOFF,
    CONTRACT_RELATIVE,
    SOURCE_DATE_SUBSTITUTION,
    UNSUPPORTED_ENTITY,
    Week1ScheduleIdentityViolation,
    build_contest_rows,
    build_participant_rows,
    index_predecessor_identities,
    index_team_season_authority,
    load_contract,
    summarize,
    validate_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((REPO_ROOT / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig"))
EXECUTION_TIME = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def card(
    *,
    contest_id: str,
    header_date: str,
    clock: str = "07:00 PM",
    away: tuple[str, str] = ("100", "Away State"),
    home: tuple[str, str] = ("200", "Home Tech"),
    neutral: str = "",
) -> str:
    neutral_row = (
        f'<tr><td colspan="10" valign="middle">@{neutral}</td></tr>' if neutral else ""
    )
    return (
        '<div class="card m-2">'
        f'<div class="col-6 p-0">{header_date} {clock} Network</div>'
        "<div><div><table>"
        f"{neutral_row}"
        f'<tr id="contest_{contest_id}">'
        f'<td><a href="/teams/{away[0]}">{away[1]} (0-0)</a></td></tr>'
        f'<tr id="contest_{contest_id}">'
        f'<td><a href="/teams/{home[0]}">{home[1]} (0-0)</a></td></tr>'
        "</table></div></div></div>"
    )


def document(*cards: str) -> str:
    return "<html><body>" + "".join(cards) + "</body></html>"


def capture(game_date: str) -> dict:
    return {
        "requested_game_date": game_date,
        "raw_sha256": "0" * 64,
        "request_identity_sha256": "1" * 64,
        "retrieved_at_utc": "2026-08-31T06:16:12Z",
        "route_id": "scrapfly_rendering",
        "state": "CAPTURED",
    }


PREDECESSOR = index_predecessor_identities(
    [
        {
            "participants": [
                {
                    "source_team_id": "100",
                    "source_display_name": "Away State",
                    "canonical_team_id": "SRC-002:TEAM:1",
                    "normalized_name_key": "away state",
                    "resolution_state": "EXACT_NORMALIZED_NAME_RESOLVED",
                },
                {
                    "source_team_id": "200",
                    "source_display_name": "Home Tech",
                    "canonical_team_id": "SRC-002:TEAM:2",
                    "official_organization_id": 42,
                    "resolution_state": "RESOLVED_BY_OFFICIAL_RECORD_TUPLE",
                    "resolution_evidence": "OFFICIAL_NCAA_ORGANIZATION_RECORD_TUPLE",
                },
                {
                    "source_team_id": "300",
                    "source_display_name": "Unresolved A&M",
                    "canonical_team_id": None,
                    "resolution_state": "UNRESOLVED_SOURCE_ENTITY",
                },
            ]
        }
    ]
)

AUTHORITY_MANIFEST = {
    "memberships": [
        {
            "source_team_id": team_id,
            "subdivision": subdivision,
            "division_code": division,
            "conference_id": "911",
            "conference_name": conference,
            "source_capture_sha256": "2" * 64,
            "retrieved_at_utc": "2026-08-31T10:05:00Z",
            "source_uri": "https://stats.ncaa.org/team/inst_team_list",
        }
        for team_id, subdivision, division, conference in (
            ("100", "FBS", "11", "SEC"),
            ("200", "FBS", "11", "SEC"),
            ("300", "FCS", "12", "SWAC"),
        )
    ]
}
AUTHORITY = index_team_season_authority(AUTHORITY_MANIFEST)


def build(documents: dict[str, str], *, contract: dict | None = None) -> list[dict]:
    return build_contest_rows(
        contract=contract or CONTRACT,
        captures=[capture(date) for date in documents],
        documents=documents,
        predecessor=PREDECESSOR,
        authority=AUTHORITY,
    )


def full_window(**overrides: str) -> dict[str, str]:
    documents = {date: document() for date in CONTRACT["requested_game_dates"]}
    documents.update(overrides)
    return documents


class ContractTests(unittest.TestCase):
    def test_contract_keeps_identity_and_lane_protections(self) -> None:
        contract = load_contract(REPO_ROOT)
        self.assertFalse(contract["identity_rules"]["fuzzy_auto_accept_enabled"])
        self.assertFalse(contract["identity_rules"]["name_only_resolution_permitted"])
        self.assertFalse(contract["authority"]["protected_evaluation_admission"])
        self.assertEqual(contract["protected_lane"], "RETAIN_PROTECTED_LANE_BLOCKED")

    def test_protected_lane_opening_is_rejected(self) -> None:
        opened = {
            **CONTRACT,
            "authority": {**CONTRACT["authority"], "protected_training_admission": True},
        }
        with self.assertRaises(Week1ScheduleIdentityViolation):
            validate_contract(opened)

    def test_fuzzy_threshold_reduction_is_rejected(self) -> None:
        reduced = {
            **CONTRACT,
            "identity_rules": {
                **CONTRACT["identity_rules"],
                "fuzzy_threshold_reduction_permitted": True,
            },
        }
        with self.assertRaises(Week1ScheduleIdentityViolation):
            validate_contract(reduced)

    def test_historical_conference_inference_is_rejected(self) -> None:
        inherited = {
            **CONTRACT,
            "sources": {
                **CONTRACT["sources"],
                "team_season_authority": {
                    **CONTRACT["sources"]["team_season_authority"],
                    "historical_conference_inference_permitted": True,
                },
            },
        }
        with self.assertRaises(Week1ScheduleIdentityViolation):
            validate_contract(inherited)

    def test_outcome_extraction_claim_is_rejected(self) -> None:
        leaking = {
            **CONTRACT,
            "outcome_exclusion": {**CONTRACT["outcome_exclusion"], "outcome_fields_extracted": True},
        }
        with self.assertRaises(Week1ScheduleIdentityViolation):
            validate_contract(leaking)


class UniverseTests(unittest.TestCase):
    def test_admitted_contest_binds_identity_orientation_and_authority(self) -> None:
        rows = build(full_window(**{"2026-09-05": document(card(contest_id="1", header_date="09/05/2026"))}))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["disposition"], ADMITTED_MODEL_ELIGIBLE)
        self.assertEqual(row["away_team"]["source_team_id"], "100")
        self.assertEqual(row["home_team"]["source_team_id"], "200")
        self.assertEqual(row["away_team"]["conference_name"], "SEC")
        self.assertEqual(row["kickoff_utc_conservative_lower_bound"], "2026-09-05T23:00:00Z")
        self.assertFalse(row["outcome_fields_extracted"])
        self.assertIn("WEEK1_MODEL_ELIGIBLE", row["universe_membership"])

    def test_source_date_substitution_cannot_be_presented_as_the_requested_date(self) -> None:
        rows = build(
            full_window(**{"2026-09-05": document(card(contest_id="1", header_date="09/04/2026"))})
        )
        self.assertEqual(rows[0]["disposition"], SOURCE_DATE_SUBSTITUTION)
        self.assertNotIn("WEEK1_MODEL_ELIGIBLE", rows[0]["universe_membership"])

    def test_duplicate_contest_identifier_fails_closed(self) -> None:
        duplicated = document(
            card(contest_id="1", header_date="09/05/2026"),
            card(contest_id="1", header_date="09/05/2026"),
        )
        with self.assertRaises(Week1ScheduleIdentityViolation):
            build(full_window(**{"2026-09-05": duplicated}))

    def test_participant_swap_changes_the_contest_identity(self) -> None:
        straight = build(
            full_window(**{"2026-09-05": document(card(contest_id="1", header_date="09/05/2026"))})
        )
        swapped = build(
            full_window(
                **{
                    "2026-09-05": document(
                        card(
                            contest_id="1",
                            header_date="09/05/2026",
                            away=("200", "Home Tech"),
                            home=("100", "Away State"),
                        )
                    )
                }
            )
        )
        self.assertNotEqual(straight[0]["contest_identity"], swapped[0]["contest_identity"])
        self.assertEqual(swapped[0]["away_team"]["source_team_id"], "200")

    def test_unsupported_entity_is_recorded_rather_than_dropped(self) -> None:
        rows = build(
            full_window(
                **{
                    "2026-09-05": document(
                        card(
                            contest_id="1",
                            header_date="09/05/2026",
                            home=("300", "Unresolved A&M"),
                        )
                    )
                }
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["disposition"], UNSUPPORTED_ENTITY)
        self.assertEqual(rows[0]["unresolved_participant_source_team_ids"], ["300"])

    def test_team_name_alone_never_resolves_an_identity(self) -> None:
        rows = build(
            full_window(
                **{
                    "2026-09-05": document(
                        card(
                            contest_id="1",
                            header_date="09/05/2026",
                            home=("999", "Home Tech"),
                        )
                    )
                }
            )
        )
        self.assertIsNone(rows[0]["home_team"]["canonical_team_id"])
        self.assertEqual(rows[0]["disposition"], UNSUPPORTED_ENTITY)

    def test_unpublished_kickoff_is_ambiguous_rather_than_assumed(self) -> None:
        rows = build(
            full_window(
                **{
                    "2026-09-05": document(
                        card(contest_id="1", header_date="09/05/2026", clock="TBA")
                    )
                }
            )
        )
        self.assertEqual(rows[0]["disposition"], AMBIGUOUS_KICKOFF)
        self.assertIsNone(rows[0]["kickoff_utc_conservative_lower_bound"])

    def test_neutral_site_annotation_is_the_only_site_evidence(self) -> None:
        rows = build(
            full_window(
                **{
                    "2026-09-05": document(
                        card(contest_id="1", header_date="09/05/2026", neutral="Neutral Field")
                    )
                }
            )
        )
        self.assertEqual(rows[0]["site_state"], "NEUTRAL")
        self.assertEqual(rows[0]["venue_identity_state"], "NEUTRAL_SITE_ANNOTATION_ONLY")
        self.assertIsNone(rows[0]["venue_identity"])

    def test_conference_from_a_conflicting_season_authority_fails_closed(self) -> None:
        conflicting = {
            "memberships": AUTHORITY_MANIFEST["memberships"]
            + [
                {
                    **AUTHORITY_MANIFEST["memberships"][0],
                    "conference_id": "827",
                    "conference_name": "Big Ten",
                }
            ]
        }
        with self.assertRaises(Week1ScheduleIdentityViolation):
            index_team_season_authority(conflicting)

    def test_missing_season_authority_is_not_silently_defaulted(self) -> None:
        rows = build_contest_rows(
            contract=CONTRACT,
            captures=[capture(date) for date in CONTRACT["requested_game_dates"]],
            documents=full_window(
                **{"2026-09-05": document(card(contest_id="1", header_date="09/05/2026"))}
            ),
            predecessor=PREDECESSOR,
            authority={},
        )
        self.assertIsNone(rows[0]["away_team"]["conference_name"])
        self.assertEqual(rows[0]["away_team"]["season_authority_state"], "SOURCE_EVIDENCE_ABSENT")
        self.assertEqual(rows[0]["disposition"], "SOURCE_EVIDENCE_ABSENT")

    def test_window_must_match_the_declared_dates(self) -> None:
        with self.assertRaises(Week1ScheduleIdentityViolation):
            build({"2026-09-05": document()})

    def test_reconstruction_is_deterministic(self) -> None:
        documents = full_window(
            **{"2026-09-05": document(card(contest_id="1", header_date="09/05/2026"))}
        )
        first = build(documents)
        second = build(documents)
        self.assertEqual(first, second)
        self.assertEqual(build_participant_rows(first), build_participant_rows(second))


class SummaryTests(unittest.TestCase):
    def test_summary_counts_every_disposition_and_identity_state(self) -> None:
        rows = build(
            full_window(
                **{
                    "2026-09-05": document(
                        card(contest_id="1", header_date="09/05/2026"),
                        card(
                            contest_id="2",
                            header_date="09/05/2026",
                            away=("300", "Unresolved A&M"),
                            home=("200", "Home Tech"),
                        ),
                    )
                }
            )
        )
        participants = build_participant_rows(rows)
        summary = summarize(rows, participants)
        self.assertEqual(summary["contest_count"], 2)
        self.assertEqual(summary["disposition_counts"][ADMITTED_MODEL_ELIGIBLE], 1)
        self.assertEqual(summary["disposition_counts"][UNSUPPORTED_ENTITY], 1)
        self.assertEqual(summary["participants_unresolved"], 1)
        self.assertEqual(summary["universe_counts"]["WEEK1_SOURCE_UNIVERSE"], 2)

    def test_participant_rows_preserve_aliases_as_evidence_only(self) -> None:
        rows = build(
            full_window(
                **{
                    "2026-09-05": document(
                        card(contest_id="1", header_date="09/05/2026", away=("100", "Away St."))
                    )
                }
            )
        )
        participants = {row["source_team_id"]: row for row in build_participant_rows(rows)}
        self.assertEqual(participants["100"]["source_display_names"], ["Away St."])
        self.assertEqual(participants["100"]["canonical_team_id"], "SRC-002:TEAM:1")


if __name__ == "__main__":
    unittest.main()
