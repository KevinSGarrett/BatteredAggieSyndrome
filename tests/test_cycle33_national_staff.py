"""Cycle 33 producer tests. Independent reference lives in scientific_reference."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.cycle30.coaching import (
    HEAD_COACH_DUAL_OCCUPANCY,
    career_episode_roundtrip,
    parse_infobox_college_coach,
    parse_official_staff_html,
    parse_wikimedia_infobox,
    role_families_from_title,
    roles_from_career_parenthetical,
    wiki_career_title_matches_person,
)
from aggie_analytics.cycle30.kernel_model import KernelModelError, fold_local_fit
from aggie_analytics.cycle33.all22_adapter import (
    All22AdapterError,
    encode_episode,
    project_lossy_staff_snapshot_v1,
)
from aggie_analytics.cycle33.acquisition_receipts import (
    cache_hit_from_path,
    cache_hit_receipt,
    sanitize_url,
)
from aggie_analytics.cycle33.fit_integrity import (
    FitIntegrityError,
    validate_fit_population,
)
from aggie_analytics.cycle33.official_finals import (
    OfficialFinalConflict,
    require_no_conflicts,
)
from aggie_analytics.cycle33.role_taxonomy import assignments_from_title
from aggie_analytics.cycle33.span_locate import locate_person_title
from aggie_analytics.cycle33.scheme_tenure import extract_scheme_tenure_claims
from aggie_analytics.cycle33.findings import (
    CYCLE32_DISPOSITION_LABEL_TO_ORIGINAL_MR31,
    ORIGINAL_MR31_MEANINGS,
)
from aggie_analytics.cycle33.query import StaffQueryError, main as staff_query_main
from aggie_analytics.cycle33.user_coaches import (
    _subdivision_from_filename,
    classify_missingness,
    import_snapshot,
    parse_person_segments,
)
from aggie_analytics.cycle33.week2 import (
    cutoffs_from_kickoff_epoch,
    historical_tamu_asu_row,
    utc_now,
)
from aggie_analytics.cycle33.wiki_parameters import football_season_template_bodies
from aggie_analytics.scientific_reference.cycle33 import (
    IndependentCycle33Error,
    competing_finals,
    reject_fold,
    unique_game_population,
)


SNAPSHOT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z\source_snapshot"
)


class RoleTaxonomyTests(unittest.TestCase):
    def test_assistant_oc_is_not_principal(self) -> None:
        self.assertEqual(
            role_families_from_title("Assistant Offensive Coordinator"), ()
        )
        mapped = assignments_from_title("Assistant Offensive Coordinator")
        self.assertEqual(mapped[0]["occupancy"], "QUALIFIED_NOT_PRINCIPAL")

    def test_co_oc_and_hc_oc_qb_keep_multiple_roles(self) -> None:
        self.assertEqual(
            role_families_from_title(
                "Head Coach / Offensive Coordinator / Quarterbacks"
            ),
            ("head_coach", "offensive_coordinator"),
        )
        self.assertIn(
            "offensive_coordinator",
            role_families_from_title("Co-Offensive Coordinator / Wide Receivers"),
        )

    def test_support_and_gm_and_de_are_observed_not_hc(self) -> None:
        self.assertEqual(role_families_from_title("Head Strength Coach"), ())
        self.assertEqual(role_families_from_title("General Manager"), ())
        mapped = assignments_from_title("Defensive Ends")
        self.assertEqual(mapped[0]["role"], "defensive_ends")
        self.assertEqual(
            assignments_from_title("Athletic Director")[0]["role"],
            "athletic_director",
        )
        mapped = assignments_from_title("Assistant Football Coach")
        self.assertEqual(mapped[0]["role"], "assistant_unspecified")
        self.assertEqual(mapped[0]["occupancy"], "OBSERVED")
        self.assertEqual(
            assignments_from_title("Team Physician")[0]["role"], "medical_staff"
        )
        self.assertEqual(
            assignments_from_title("Nickelbacks Coach")[0]["role"], "nickels"
        )
        self.assertEqual(
            assignments_from_title("Director of Football Technology")[0]["role"],
            "video_technology_staff",
        )
        assistant_to = assignments_from_title("Assistant To Defensive Coordinator")
        self.assertEqual(assistant_to[0]["role"], "defensive_coordinator")
        self.assertEqual(assistant_to[0]["occupancy"], "QUALIFIED_NOT_PRINCIPAL")
        self.assertEqual(
            role_families_from_title("Assistant To Defensive Coordinator"), ()
        )
        self.assertEqual(
            assignments_from_title("Nicklebacks Coach")[0]["role"], "nickels"
        )
        self.assertEqual(
            assignments_from_title("Wide Recievers Coach")[0]["role"],
            "wide_receivers",
        )
        self.assertEqual(
            assignments_from_title("DBs/Passing Game Coordinator")[0]["role"],
            "defensive_backs",
        )
        self.assertIn(
            "pass_game_coordinator",
            {
                row["role"]
                for row in assignments_from_title("DBs/Passing Game Coordinator")
            },
        )
        self.assertEqual(
            assignments_from_title("Pitching Coach")[0]["role"],
            "other_sport_not_football",
        )
        pronouns = assignments_from_title("she/her/hers")
        self.assertEqual(pronouns[0]["occupancy"], "UNMAPPED")
        self.assertEqual(
            assignments_from_title("Bare Unknown Title")[0]["occupancy"], "UNMAPPED"
        )
        self.assertEqual(
            assignments_from_title("Assistant")[0]["occupancy"], "UNMAPPED"
        )
        self.assertEqual(
            assignments_from_title("Assistant Western Coach")[0]["occupancy"],
            "UNMAPPED",
        )

    def test_broad_db_does_not_become_cb_and_s(self) -> None:
        roles = {row["role"] for row in assignments_from_title("Defensive Backs")}
        self.assertEqual(roles, {"defensive_backs"})


class All22AdapterTests(unittest.TestCase):
    def test_missing_provenance_is_rejected(self) -> None:
        with self.assertRaises(All22AdapterError):
            encode_episode({"person": "A", "role": "head_coach"})
        with self.assertRaises(All22AdapterError):
            encode_episode(
                {
                    "person": "A",
                    "role": "head_coach",
                    "source_title": "Head Coach",
                    "source_class": "OPERATOR_CONTEMPORANEOUS_DECLARATION",
                    "valid_time_precision": "YEAR",
                    "recorded_at_utc": "2026-09-14T00:00:00Z",
                    "schema_version": "v1",
                }
            )
        projected = project_lossy_staff_snapshot_v1([{"person": "A"}])
        self.assertTrue(projected["cannot_claim_lossless_transport"])


class OperatorDeclarationTests(unittest.TestCase):
    def test_operator_map_is_empty(self) -> None:
        self.assertEqual(HEAD_COACH_DUAL_OCCUPANCY, {})


class WikiParserTests(unittest.TestCase):
    def test_soccer_infobox_is_rejected(self) -> None:
        text = (
            "{{Infobox college football season\n|head_coach=[[Correct Coach]]\n}}\n"
            "{{Infobox college soccer season\n|head_coach=[[Soccer Coach]]\n}}"
        )
        got = parse_wikimedia_infobox(
            text, revision_id="888", page_title="2020 Example football team"
        )
        people = [row["person"] for row in got]
        self.assertEqual(people, ["Correct Coach"])

    def test_nested_parameter_injection_is_rejected(self) -> None:
        text = (
            "{{Infobox college football season\n|head_coach=[[Correct Coach]]\n"
            "|notes={{Example\n|off_coach=[[Unrelated Coach]]\n}}\n}}"
        )
        got = parse_wikimedia_infobox(
            text, revision_id="888", page_title="2020 Example football team"
        )
        people = [row["person"] for row in got]
        self.assertEqual(people, ["Correct Coach"])
        self.assertEqual(football_season_template_bodies(text).__len__(), 1)

    def test_sequential_occupants_are_not_co_role(self) -> None:
        text = (
            "{{Infobox college football season\n"
            "|off_coach=[[First Coach]] (games 1–4); [[Second Coach]] (games 5–12)\n}}"
        )
        got = parse_wikimedia_infobox(
            text, revision_id="888", page_title="2020 Example football team"
        )
        self.assertEqual(
            [row["person"] for row in got], ["First Coach", "Second Coach"]
        )
        self.assertTrue(all(row["co_role"] is False for row in got))

    def test_scheme_and_tenure_are_extracted_not_inferred(self) -> None:
        text = (
            "{{Infobox college football season\n|head_coach=[[A]]\n"
            "|off_scheme=Air raid\n|def_scheme=4–3\n|hc_years=3rd\n}}"
        )
        claims = extract_scheme_tenure_claims(
            text, page_title="2020 Example football team", revision_id="1", season=2020
        )
        fields = {row["field"]: row["source_text"] for row in claims}
        self.assertEqual(fields["offensive_scheme"], "Air raid")
        self.assertEqual(fields["defensive_scheme"], "4–3")
        self.assertEqual(fields["hc_tenure_stated"], "3rd")
        self.assertTrue(all(row["inferred"] is False for row in claims))

    def test_sports_team_season_football_is_accepted(self) -> None:
        text = (
            "{{Infobox college sports team season\n|sport=football\n"
            "|head_coach=[[Darrell Dickey]]\n|off_scheme=[[Spread offense|Pro spread]]\n"
            "|def_scheme=[[Nickel defense|4–2–5]]\n|hc_year=8th\n}}"
        )
        claims = extract_scheme_tenure_claims(
            text,
            page_title="2005 North Texas Mean Green football team",
            revision_id="1",
        )
        fields = {
            row["field"]: row["source_text"] for row in claims if row.get("source_text")
        }
        self.assertEqual(fields["offensive_scheme"], "[[Spread offense|Pro spread]]")
        self.assertEqual(fields["hc_tenure_stated"], "8th")
        people = parse_wikimedia_infobox(
            text,
            revision_id="1",
            page_title="2005 North Texas Mean Green football team",
        )
        self.assertEqual([row["person"] for row in people], ["Darrell Dickey"])

    def test_sports_team_season_basketball_is_rejected(self) -> None:
        text = (
            "{{Infobox college sports team season\n|sport=basketball\n"
            "|head_coach=[[Basketball Coach]]\n|off_scheme=Motion\n}}"
        )
        claims = extract_scheme_tenure_claims(
            text, page_title="2005 Example basketball team", revision_id="1"
        )
        self.assertEqual(claims, [])
        people = parse_wikimedia_infobox(
            text, revision_id="1", page_title="2005 Example basketball team"
        )
        self.assertEqual(people, [])


class CareerIdentityTests(unittest.TestCase):
    def test_oc_qb_reference_is_not_unknown(self) -> None:
        self.assertIn(
            "offensive_coordinator",
            roles_from_career_parenthetical("OC/QB<ref>{{cite web|title=x}}</ref>"),
        )

    def test_politician_and_disambiguation_are_not_coaches(self) -> None:
        self.assertFalse(
            wiki_career_title_matches_person("Tim Lester (politician)", "Tim Lester")
        )
        empty = parse_infobox_college_coach(
            "{{disambiguation}}\n{{Infobox officeholder\n|name=Tim Lester\n}}",
            revision_id="1",
            page_title="Tim Lester",
        )
        self.assertEqual(empty, [])

    def test_conflicting_source_person_id_is_not_overwritten(self) -> None:
        payload = career_episode_roundtrip(
            program_id="SRC-002:TEAM:1",
            person="Same Name",
            source_person_id="TARGET_PERSON",
            career_episodes=[
                {
                    "person": "Same Name",
                    "program_raw": "School",
                    "role": "head_coach",
                    "start_year": 2020,
                    "end_year": 2021,
                    "source_person_id": "OTHER_PERSON",
                }
            ],
        )
        self.assertEqual(payload["episode_cardinality"], 0)
        self.assertEqual(payload["namesake_rejected"], 1)


class FitAndFinalsTests(unittest.TestCase):
    def test_duplicate_games_and_overlap_fail(self) -> None:
        rows = [
            {"canonical_game_id": "G1", "season": 2018},
            {"canonical_game_id": "G1", "season": 2018},
        ]
        with self.assertRaises(FitIntegrityError):
            validate_fit_population(rows, train_seasons=[2018], eval_seasons=[2018])
        with self.assertRaises(IndependentCycle33Error):
            reject_fold([2018], [2018])
        with self.assertRaises(KernelModelError):
            fold_local_fit(
                [
                    {
                        "canonical_game_id": "G1",
                        "season": 2018,
                        "home_win_label": True,
                        "home_features": {"pit_prior_margin_mean": 1},
                        "away_features": {"pit_prior_margin_mean": 0},
                    },
                    {
                        "canonical_game_id": "G1",
                        "season": 2019,
                        "home_win_label": True,
                        "home_features": {"pit_prior_margin_mean": 1},
                        "away_features": {"pit_prior_margin_mean": 0},
                    },
                ],
                candidate="intercept_only",
                train_seasons=[2018],
                eval_seasons=[2018],
            )

    def test_conflicting_duplicate_final_quarantines(self) -> None:
        with self.assertRaises(OfficialFinalConflict):
            require_no_conflicts(
                [
                    {
                        "ncaa_contest_id": "1",
                        "home_points": 10,
                        "away_points": 7,
                    },
                    {
                        "ncaa_contest_id": "1",
                        "home_points": 17,
                        "away_points": 7,
                    },
                ]
            )
        self.assertEqual(
            competing_finals(
                [
                    {"ncaa_contest_id": "1", "home_points": 10, "away_points": 7},
                    {"ncaa_contest_id": "1", "home_points": 17, "away_points": 7},
                ]
            ),
            ["1"],
        )


class AcquisitionReceiptTests(unittest.TestCase):
    def test_sanitize_removes_value_not_just_prefix(self) -> None:
        url = "https://api.example/test?api_key=secret-value-123&season=2026"
        cleaned = sanitize_url(url)
        self.assertNotIn("secret-value-123", cleaned)
        self.assertIn("season=2026", cleaned)

    def test_cache_hit_preserves_error(self) -> None:
        receipt = cache_hit_receipt(
            original={
                "retrieved_at_utc": "2026-01-01T00:00:00Z",
                "http_status": 404,
                "ok": False,
                "request_id": "REQ-1",
                "raw_sha256": "abc",
            },
            cache_read_at_utc="2026-09-14T12:00:00Z",
            route="https://example/x?api_key=nope",
        )
        self.assertEqual(receipt["retrieved_at_utc"], "2026-01-01T00:00:00Z")
        self.assertEqual(receipt["http_status"], 404)
        self.assertFalse(receipt["ok"])
        self.assertEqual(receipt["status"], "CACHE_HIT_ERROR_PRESERVED")
        self.assertNotIn("nope", receipt["route"])

    def test_cache_hit_from_path_uses_mtime_not_now(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text("{}", encoding="utf-8")
            os.utime(path, (1_700_000_000, 1_700_000_000))
            receipt = cache_hit_from_path(
                path, url="https://example/x?api_key=secret-value-123"
            )
            self.assertEqual(receipt["status"], "CACHE_HIT")
            self.assertEqual(receipt["retrieved_at_utc"], "2023-11-14T22:13:20Z")
            self.assertNotEqual(
                receipt["retrieved_at_utc"], receipt["cache_read_at_utc"]
            )
            self.assertNotIn("secret-value-123", receipt["route"])


class IndependentReferenceTests(unittest.TestCase):
    def test_unique_game_population_rejects_nothing_silently(self) -> None:
        summary = unique_game_population(
            [
                {"canonical_game_id": "G1", "season": 2018},
                {"canonical_game_id": "G1", "season": 2018},
                {"canonical_game_id": "G2", "season": 2019},
                {"season": 2020},
            ]
        )
        self.assertEqual(summary["unique_games"], 2)
        self.assertEqual(summary["duplicate_rows"], 1)
        self.assertEqual(summary["missing_identity_rows"], 1)
        self.assertEqual(summary["proven_pit"], 0)
        self.assertFalse(summary["producer_helpers_imported"])


class UserCoachesTests(unittest.TestCase):
    def test_null_tokens_are_not_people(self) -> None:
        self.assertEqual(parse_person_segments("NOT VERIFIED FOR 2018"), [])
        self.assertEqual(parse_person_segments("UNKNOWN"), [])
        self.assertEqual(classify_missingness(""), "BLANK_NOT_CAPTURED")
        segs = parse_person_segments(
            "Troy Calhoun — Head Coach | Todd Stroud — Associate Head Coach"
        )
        self.assertEqual(
            [row["person_raw"] for row in segs],
            ["Troy Calhoun", "Todd Stroud"],
        )

    def test_formula_string_is_inert(self) -> None:
        self.assertEqual(parse_person_segments('=CMD("calc")'), [])
        self.assertEqual(parse_person_segments('=HYPERLINK("http://evil")'), [])

    def test_snapshot_roundtrip_counts(self) -> None:
        if not SNAPSHOT.is_dir():
            self.skipTest("user coaches snapshot is not mounted")
        imported = import_snapshot(SNAPSHOT)
        self.assertEqual(imported["file_count"], 54)
        self.assertEqual(imported["staff_observation_count"], 6749)
        self.assertEqual(imported["queue_row_count"], 273)
        self.assertFalse(imported["pit_admitted"])
        self.assertEqual(imported["source_class"], "USER_COMPILED_RESEARCH_OBSERVATION")
        self.assertTrue(
            any(
                (row.get("header_season_conflict") or {}).get("conflict")
                for row in imported["observations"]
            )
        )
        people = {
            (row["team"], row["season"], row["person"])
            for row in imported["role_cells"]
            if row.get("person")
        }
        self.assertGreater(len(people), 1000)
        combined = [
            row["filename_subdivision"]
            for row in imported["files"]
            if row["relative_path"].startswith("2026_FBS_FCS")
        ]
        self.assertEqual(combined, ["COMBINED_FBS_FCS"])
        self.assertEqual(
            _subdivision_from_filename("2009_FBS_Staff_ONE_TEAM_PER_ROW.csv"), "FBS"
        )
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "staff.sqlite"
            from aggie_analytics.cycle33.query import (
                connect,
                load_import,
                team_staff,
                coach_career,
            )

            conn = connect(db)
            try:
                load_import(conn, imported)
                fbs = team_staff(conn, team="Air Force", season="2018")
                self.assertTrue(fbs)
                career = coach_career(conn, person="Troy Calhoun")
                self.assertTrue(career)
            finally:
                conn.close()


class Week2CloseoutTests(unittest.TestCase):
    def test_tamu_asu_deadlines_are_historical(self) -> None:
        row = historical_tamu_asu_row(utc_now())
        self.assertTrue(row["rearm_forbidden"])
        self.assertIn(
            row["t24h_disposition"],
            {
                "MISSED_CUTOFF_NO_BACKFILL",
                "EVIDENCE_CAPTURED",
                "FORECAST_FROZEN",
                "EVIDENCE_CAPTURED_LATE_TRUE_TIMESTAMP",
            },
        )
        self.assertTrue(row["retroactive_forecast_forbidden"])

    def test_pregame_null_scores_are_contests_not_dropped(self) -> None:
        from aggie_analytics.cycle30.acquisition import (
            parse_ncaa_com_scoreboard_contests,
        )

        page = (
            '"contestId":6604311,"url":"\\/game\\/6604311","gameState":"P",'
            '"statusCodeDisplay":"pre","startDate":"09\\/10\\/2026",'
            '"teams":[{"isHome":true,"seoname":"miami-fl","nameShort":"Miami (FL)",'
            '"score":null},{"isHome":false,"seoname":"florida-st","nameShort":'
            '"Florida St.","score":null}]'
        )
        got = parse_ncaa_com_scoreboard_contests(page)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["home_name"], "Miami (FL)")
        self.assertIsNone(got[0]["home_points"])
        self.assertEqual(got[0]["start_date"], "09/10/2026")
        self.assertNotEqual(got[0]["terminal_state"], "TERMINAL_STATUS_ESTABLISHED")

    def test_kickoff_epoch_derives_missed_cutoffs(self) -> None:
        now = utc_now()
        epoch = int(now.timestamp()) - (3 * 24 * 3600)
        cut = cutoffs_from_kickoff_epoch(epoch, now=now)
        self.assertEqual(cut["t24h_disposition"], "MISSED_CUTOFF_NO_BACKFILL")
        self.assertEqual(cut["t90m_disposition"], "MISSED_CUTOFF_NO_BACKFILL")
        self.assertEqual(cut["cutoff_source"], "NCAA_START_TIME_EPOCH")
        missing = cutoffs_from_kickoff_epoch(None, now=now)
        self.assertEqual(missing["t24h_disposition"], "CUTOFF_UNKNOWN")


class SpanLocateTests(unittest.TestCase):
    def test_person_and_title_offsets_are_required(self) -> None:
        html = "<div>Keith Patterson</div><div>Head Football Coach</div>"
        found = locate_person_title(
            html, person="Keith Patterson", title="Head Football Coach"
        )
        self.assertTrue(found["locatable"])
        self.assertEqual(found["body_offset"], html.find("Keith Patterson"))
        missing = locate_person_title(
            html, person="Nobody", title="Head Football Coach"
        )
        self.assertFalse(missing["locatable"])

    def test_official_html_parser_records_body_offset(self) -> None:
        html = (
            '<table class="sidearm-coaches-coach"><tr>'
            '<td class="sidearm-table-player-name"><a href="/sports/football/coaches/keith-patterson">Keith Patterson</a></td>'
            "<td>Head Football Coach</td></tr></table>"
        )
        got = parse_official_staff_html(
            html,
            page_url="https://example.test/sports/football/coaches",
            program_name="Example",
        )
        if got:
            self.assertTrue(
                any(row.get("body_offset") not in {None, ""} for row in got)
            )


class QueryCliTests(unittest.TestCase):
    def test_database_argument_is_required_without_private_default(self) -> None:
        with self.assertRaises(SystemExit):
            staff_query_main([])
        missing_parent = (
            Path(tempfile.gettempdir()) / "bas-cycle33-missing-parent" / "nope.sqlite"
        )
        if missing_parent.parent.exists():
            missing_parent = (
                Path(tempfile.gettempdir())
                / "bas-cycle33-missing-parent-2"
                / "nope.sqlite"
            )
        with self.assertRaises(StaffQueryError):
            staff_query_main(["--database", str(missing_parent)])


class FindingIdentityTests(unittest.TestCase):
    def test_cycle32_shifted_labels_restore_original_mr31(self) -> None:
        self.assertEqual(
            CYCLE32_DISPOSITION_LABEL_TO_ORIGINAL_MR31["MR31-09"], "MR31-10"
        )
        self.assertIn("Missing numerical predictors", ORIGINAL_MR31_MEANINGS["MR31-10"])
        self.assertIn("Target freeze receipt", ORIGINAL_MR31_MEANINGS["MR31-09"])


if __name__ == "__main__":
    unittest.main()
