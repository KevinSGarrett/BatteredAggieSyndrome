"""Nameset, taxonomy, bio-card, and independent CS-05 continuation tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from aggie_analytics.cycle33 import (
    cs05_score,
    nameset_adjudication as nameset_mod,
    query,
)
from aggie_analytics.cycle33.nameset_adjudication import (
    adjudicate_person,
    principal_occupants,
)
from aggie_analytics.cycle33.role_taxonomy import principal_role_families
from aggie_analytics.cycle33.span_locate import bind_person_role, iter_staff_records
from aggie_analytics.scientific_reference.cycle33_cs05 import (
    FROZEN_CURRENT_LABELS,
    fact_key,
    independent_wiki_coach_lines,
    score_sets,
)


class TaxonomyRepairTests(unittest.TestCase):
    def test_athletic_performance_head_coach_is_not_program_hc(self) -> None:
        title = "Head Coach of Athletic Performance - Football"
        self.assertEqual(principal_role_families(title), ())
        html = (
            "<table><tr><td>Ken Niumatalolo</td><td>Head Coach</td></tr>"
            f"<tr><td>Nu'u Tafisi</td><td>{title}</td></tr></table>"
        )
        found = bind_person_role(html, person="Nu'u Tafisi", title="Head Coach")
        self.assertTrue(found["person_record_bound"])
        self.assertFalse(found["role_claim_supported"])
        occupants = principal_occupants(html, role="head_coach")
        self.assertEqual([row["person"] for row in occupants], ["Ken Niumatalolo"])

    def test_executive_director_of_football_is_not_head_coach(self) -> None:
        title = "Associate AD, Executive Director of Football"
        self.assertEqual(principal_role_families(title), ())
        html = (
            "<table><tr><td>James Franklin</td><td>Head Coach</td></tr>"
            f"<tr><td>Michael Hazel</td><td>{title}</td></tr></table>"
        )
        found = bind_person_role(html, person="Michael Hazel", title="Head Coach")
        self.assertTrue(found["person_record_bound"])
        self.assertFalse(found["role_claim_supported"])
        frank = bind_person_role(html, person="James Franklin", title="Head Coach")
        self.assertTrue(frank["role_claim_supported"])

    def test_coordinator_typo_and_infield_sport(self) -> None:
        self.assertEqual(
            principal_role_families("Defensive Coordiantor"),
            ("defensive_coordinator",),
        )
        self.assertEqual(
            principal_role_families("Defensive Coordinator/Infield Coach"),
            (),
        )

    def test_assistant_oc_phrase_is_not_principal_oc(self) -> None:
        html = (
            "<table><tr><td>Dan Hunt</td>"
            "<td>Associate Head Coach/Offensive Coordinator/Quarterbacks Coach"
            "</td></tr>"
            "<tr><td>Mike Morita</td>"
            "<td>Assistant Offensive Coordinator/Offensive Line Coach</td></tr>"
            "</table>"
        )
        hunt = bind_person_role(html, person="Dan Hunt", title="Offensive Coordinator")
        self.assertTrue(hunt["role_claim_supported"])
        morita_oc = bind_person_role(
            html, person="Mike Morita", title="Offensive Coordinator"
        )
        self.assertTrue(morita_oc["person_record_bound"])
        self.assertFalse(morita_oc["role_claim_supported"])
        morita_asst = bind_person_role(
            html, person="Mike Morita", title="Assistant Offensive Coordinator"
        )
        self.assertTrue(morita_asst["role_claim_supported"])


class BioCardTests(unittest.TestCase):
    def test_staff_bio_card_binds_subject_not_career_table(self) -> None:
        html = (
            "<title>Ken Niumatalolo - SJSU Athletics</title>"
            '<h1 class="roster-bio-main-info__title">Ken Niumatalolo</h1>'
            '<strong class="roster-bio-main-info__position">Head Coach</strong>'
            "<table><tr><td>Year</td><td>School</td></tr>"
            "<tr><td>2011</td><td>Navy</td></tr></table>"
        )
        found = bind_person_role(html, person="Ken Niumatalolo", title="Head Coach")
        self.assertTrue(found["person_record_bound"])
        self.assertTrue(found["role_claim_supported"])
        self.assertEqual(found["record_kind"], "staff_bio_card")
        tafisi = bind_person_role(html, person="Nu'u Tafisi", title="Head Coach")
        self.assertFalse(tafisi["person_record_bound"])
        people = [row["person"] for row in iter_staff_records(html)]
        self.assertNotIn("2011", people)


class OccupantTests(unittest.TestCase):
    def test_principal_occupants_keep_co_dc_and_reject_analyst(self) -> None:
        html = (
            "<table>"
            "<tr><td>Clayton White</td><td>Defensive Coordinator/LBs</td></tr>"
            "<tr><td>Torrian Gray</td>"
            "<td>Co-Defensive Coordinator/Defensive Backs Coach</td></tr>"
            "<tr><td>Kyle Lindquist</td>"
            "<td>Defensive Coordinator/Infield Coach</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="defensive_coordinator")
        names = {row["person"] for row in occupants}
        self.assertEqual(names, {"Clayton White", "Torrian Gray"})
        by_name = {row["person"]: row["occupancy"] for row in occupants}
        self.assertEqual(by_name["Clayton White"], "PRINCIPAL")
        self.assertEqual(by_name["Torrian Gray"], "CO_SHARED")
        lindquist = adjudicate_person(
            html, person="Kyle Lindquist", role="defensive_coordinator"
        )
        self.assertNotEqual(lindquist["verdict"], "PRINCIPAL_OR_CO_ROLE_SUPPORTED")

    def test_iowa_wallace_is_not_principal_dc(self) -> None:
        html = (
            "<table>"
            "<tr><td>Phil Parker</td><td>Defensive Coordinator/Secondary</td></tr>"
            "<tr><td>Seth Wallace</td>"
            "<td>Asst. Head Coach/Asst. Defensive Coordinator/Linebackers</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="defensive_coordinator")
        self.assertEqual([row["person"] for row in occupants], ["Phil Parker"])

    def test_tamu_hemphill_principal_robinson_co_dc(self) -> None:
        html = (
            "<table>"
            "<tr><td>Lyle Hemphill</td><td>Defensive Coordiantor</td></tr>"
            "<tr><td>Elijah Robinson</td>"
            "<td>Co-Defensive Coordinator/Defensive Line</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="defensive_coordinator")
        by_name = {row["person"]: row["occupancy"] for row in occupants}
        self.assertEqual(by_name["Lyle Hemphill"], "PRINCIPAL")
        self.assertEqual(by_name["Elijah Robinson"], "CO_SHARED")

    def test_princeton_staff_cos_is_not_current_dc(self) -> None:
        coaches = (
            "<table>"
            "<tr><td>Steve Verbit</td>"
            "<td>Senior Associate Head Coach & Defensive Coordinator</td></tr>"
            "<tr><td>Mike Weick</td>"
            "<td>Assistant Head Coach/Inside Linebackers Coach/"
            "Co-Defensive Coordinator</td></tr>"
            "<tr><td>E.J. Henderson</td>"
            "<td>Defensive Backs Coach/Co-Defensive Coordinator</td></tr>"
            "</table>"
        )
        staff = (
            "<table>"
            "<tr><td>Steve Verbit</td><td>Chief of Staff</td></tr>"
            "<tr><td>Mike Weick</td>"
            "<td>Assistant Head Coach/Inside Linebackers Coach/"
            "Co-Defensive Coordinator</td></tr>"
            "<tr><td>E.J. Henderson</td>"
            "<td>Defensive Backs Coach/Co-Defensive Coordinator</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(
            coaches,
            role="defensive_coordinator",
            staff_html=staff,
        )
        names = {row["person"] for row in occupants}
        self.assertNotIn("Steve Verbit", names)
        by_name = {row["person"]: row["occupancy"] for row in occupants}
        self.assertEqual(by_name["Mike Weick"], "CO_SHARED")
        self.assertEqual(by_name["E.J. Henderson"], "CO_SHARED")

    def test_south_carolina_gray_is_co_dc_lindquist_infield_rejected(self) -> None:
        html = (
            "<table>"
            "<tr><td>Clayton White</td><td>Defensive Coordinator</td></tr>"
            "<tr><td>Torrian Gray</td>"
            "<td>Co-Defensive Coordinator/Defensive Pass Game Coordinator/"
            "Defensive Backs</td></tr>"
            "<tr><td>Kyle Lindquist</td>"
            "<td>Defensive Coordinator/Infield Coach</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="defensive_coordinator")
        by_name = {row["person"]: row["occupancy"] for row in occupants}
        self.assertEqual(by_name["Clayton White"], "PRINCIPAL")
        self.assertEqual(by_name["Torrian Gray"], "CO_SHARED")
        self.assertNotIn("Kyle Lindquist", by_name)

    def test_source_supported_dc_is_not_dropped_by_name_map(self) -> None:
        html = (
            "<table>"
            "<tr><td>Mike Weick</td><td>Co-Defensive Coordinator</td></tr>"
            "<tr><td>Seth Wallace</td><td>Defensive Coordinator</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="defensive_coordinator")
        by_name = {row["person"]: row["occupancy"] for row in occupants}
        self.assertEqual(by_name["Mike Weick"], "CO_SHARED")
        self.assertEqual(by_name["Seth Wallace"], "PRINCIPAL")

    def test_tamu_hemphill_principal_robinson_co_dc_from_titles(self) -> None:
        html = (
            "<table>"
            "<tr><td>Lyle Hemphill</td><td>Defensive Coordinator</td></tr>"
            "<tr><td>Elijah Robinson</td>"
            "<td>Co-Defensive Coordinator/Defensive Line</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="defensive_coordinator")
        by_name = {row["person"]: row["occupancy"] for row in occupants}
        self.assertEqual(by_name["Lyle Hemphill"], "PRINCIPAL")
        self.assertEqual(by_name["Elijah Robinson"], "CO_SHARED")

    def test_virginia_tech_hazel_ad_is_not_head_coach(self) -> None:
        html = (
            "<table>"
            "<tr><td>James Franklin</td><td>Head Coach</td></tr>"
            "<tr><td>Michael Hazel</td>"
            "<td>Associate Athletic Director and Executive Director of Football"
            "</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="head_coach")
        names = {row["person"] for row in occupants}
        self.assertEqual(names, {"James Franklin"})

    def test_lehigh_morita_assistant_oc_is_not_principal(self) -> None:
        html = (
            "<table><tr><td>Dan Hunt</td>"
            "<td>Associate Head Coach/Offensive Coordinator/Quarterbacks Coach"
            "</td></tr>"
            "<tr><td>Mike Morita</td>"
            "<td>Assistant Offensive Coordinator/Run Game Coordinator/"
            "Offensive Line Coach</td></tr>"
            "</table>"
        )
        occupants = principal_occupants(html, role="offensive_coordinator")
        self.assertEqual([row["person"] for row in occupants], ["Dan Hunt"])


class IndependentCs05Tests(unittest.TestCase):
    def test_independent_wiki_lines_do_not_use_producer(self) -> None:
        text = (
            "{{Infobox college football team\n"
            "| head_coach = [[Darrell Dickey]]\n"
            "| off_coach = Ramon Flanigan\n"
            "| def_coach = Kenny Evans\n"
            "}}\n"
        )
        labels = independent_wiki_coach_lines(text)
        self.assertEqual(
            {(row["person"], row["role"]) for row in labels},
            {
                ("Darrell Dickey", "head_coach"),
                ("Ramon Flanigan", "offensive_coordinator"),
                ("Kenny Evans", "defensive_coordinator"),
            },
        )

    def test_score_sets_counts_extra_and_missed_inside_boundary(self) -> None:
        expected = [
            {"person": "Dan Hunt", "role": "offensive_coordinator"},
        ]
        extracted = [
            {"person": "Dan Hunt", "role": "offensive_coordinator"},
            {"person": "Mike Morita", "role": "offensive_coordinator"},
        ]
        metrics = score_sets(expected, extracted)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertEqual(metrics["false_negative"], 0)
        self.assertGreaterEqual(len(FROZEN_CURRENT_LABELS), 16)

    def test_score_sets_wrong_school_is_not_true_positive(self) -> None:
        expected = [
            {
                "program": "Lehigh",
                "season": 2026,
                "person": "Dan Hunt",
                "role": "offensive_coordinator",
                "occupancy": "PRINCIPAL",
            }
        ]
        extracted = [
            {
                "program": "Princeton",
                "season": 2026,
                "person": "Dan Hunt",
                "role": "offensive_coordinator",
                "occupancy": "PRINCIPAL",
            }
        ]
        metrics = score_sets(expected, extracted)
        self.assertEqual(metrics["true_positive"], 0)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertEqual(metrics["false_negative"], 1)
        self.assertEqual(metrics["precision"], 0)
        self.assertEqual(metrics["recall"], 0)

    def test_score_sets_wrong_season_is_not_true_positive(self) -> None:
        expected = [
            {
                "program": "Lehigh",
                "season": 2026,
                "person": "Dan Hunt",
                "role": "offensive_coordinator",
            }
        ]
        extracted = [
            {
                "program": "Lehigh",
                "season": 2018,
                "person": "Dan Hunt",
                "role": "offensive_coordinator",
            }
        ]
        metrics = score_sets(expected, extracted)
        self.assertEqual(metrics["true_positive"], 0)
        self.assertEqual(metrics["identity_metrics"]["true_positive"], 0)

    def test_score_sets_principal_vs_co_is_qualifier_error(self) -> None:
        shared = {
            "program": "Princeton",
            "season": 2026,
            "person": "Mike Weick",
            "role": "defensive_coordinator",
        }
        metrics = score_sets(
            [{**shared, "occupancy": "PRINCIPAL"}],
            [{**shared, "occupancy": "CO_SHARED"}],
        )
        self.assertEqual(metrics["role_metrics"]["true_positive"], 1)
        self.assertEqual(metrics["true_positive"], 0)

    def test_score_sets_assistant_vs_principal_is_false_positive(self) -> None:
        expected = [
            {
                "program": "Lehigh",
                "season": 2026,
                "person": "Dan Hunt",
                "role": "offensive_coordinator",
                "occupancy": "PRINCIPAL",
            }
        ]
        extracted = [
            {
                "program": "Lehigh",
                "season": 2026,
                "person": "Mike Morita",
                "role": "offensive_coordinator",
                "occupancy": "PRINCIPAL",
            }
        ]
        metrics = score_sets(expected, extracted)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertEqual(metrics["false_negative"], 1)

    def test_score_sets_sequential_occupants_are_not_concurrent(self) -> None:
        expected = [
            {
                "program": "Iowa",
                "season": 2024,
                "person": "Phil Parker",
                "role": "defensive_coordinator",
                "occupancy": "PRINCIPAL",
            }
        ]
        extracted = [
            {
                "program": "Iowa",
                "season": 2024,
                "person": "Phil Parker",
                "role": "defensive_coordinator",
                "occupancy": "PRINCIPAL",
            },
            {
                "program": "Iowa",
                "season": 2024,
                "person": "Seth Wallace",
                "role": "defensive_coordinator",
                "occupancy": "PRINCIPAL",
            },
        ]
        metrics = score_sets(expected, extracted)
        self.assertEqual(metrics["false_positive"], 1)

    def test_score_sets_duplicate_revisions_do_not_inflate(self) -> None:
        row = {
            "program": "Lehigh",
            "season": 2026,
            "person": "Dan Hunt",
            "role": "offensive_coordinator",
            "occupancy": "PRINCIPAL",
            "revision_id": "1",
        }
        dup = {**row, "revision_id": "2"}
        metrics = score_sets([row], [row, dup])
        self.assertEqual(metrics["extracted_count"], 1)
        self.assertEqual(metrics["true_positive"], 1)

    def test_operator_overlay_is_not_on_admission_path(self) -> None:
        self.assertFalse(hasattr(nameset_mod, "OPERATOR_CURRENT_ROLES"))
        self.assertFalse(hasattr(nameset_mod, "apply_operator_current_roles"))
        source = Path(nameset_mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("OPERATOR_CURRENT_ROLES", source)
        self.assertNotIn("apply_operator_current_roles", source)
        self.assertNotIn(
            "OPERATOR_CURRENT_ROLES",
            Path(cs05_score.__file__).read_text(encoding="utf-8"),
        )
        self.assertNotIn("occupancy", query.SCHEMA_SQL)
        configs = Path(__file__).resolve().parents[1] / "configs"
        for path in configs.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("OPERATOR_CURRENT_ROLES", text)
            self.assertNotIn("apply_operator_current_roles", text)

    def test_cs05_fact_key_includes_program_season_person_role_occupancy(self) -> None:
        row = {
            "program": "Princeton",
            "season": 2026,
            "person": "Mike Weick",
            "role": "defensive_coordinator",
            "occupancy": "CO_SHARED",
            "qualification": "CO_DC",
        }
        self.assertEqual(
            fact_key(row),
            ("princeton", "2026", "mike weick", "defensive_coordinator", "CO_SHARED"),
        )


if __name__ == "__main__":
    unittest.main()
