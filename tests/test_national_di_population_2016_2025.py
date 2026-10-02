"""BAT-710 national Division I population 2016-2025 (Cycle #38 TP38-A01-01..06).

Unmounted tests use tiny synthetic fixtures only (no lake copies). Mounted tests (``AGGIE_ANALYTICS_DATA_ROOT`` set
and the committed successor gate present) read the delivered content-addressed outputs read-only.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import gzip
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data import national_di_population as pop  # noqa: E402

CONTRACT = ROOT / "configs" / "national_di_population_2016_2025_contract.json"
VALIDATOR = ROOT / "tools" / "validate_national_di_population_2016_2025.py"
BUILDER = ROOT / "tools" / "build_national_di_population_2016_2025.py"
GATE = ROOT / "artifacts" / "data_lake" / "national_di_population_2016_2025_gate.json"


def contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def page_html(*, org: str = "669", ts: str = "100", label: str = "2018-19", name: str = "Missouri St.",
              record: str = "(4-7)", codes: tuple[str, ...] = ("12", "12.0"), rows: tuple[str, ...] = (),
              navbar_record: str = "2026-27 Football (0-0)", extra_links: str = "") -> str:
    year = int(label[:4]) + 1
    rankings = "".join(f'<a href="/rankings/ranking_summary?academic_year={year}&amp;division={c}&amp;org_id={org}">r</a>'
                       for c in codes) + extra_links
    return (f'<ul><li><a href="/teams/999">{navbar_record}</a></li></ul>'
            f'<a href="/teams/history/MFB/{org}">History</a>'
            f'<div class="card"><div class="card-header"> <img class="logo_image" alt="{name}" '
            f'src="https://web2.ncaa.org/ncaa_style/img/All_Logos/sm//{org}.gif"> <a href="http://x">{name} Bears</a> '
            f'{record} </div></div>'
            f'<select name="year_id" id="year_list"><option value="777">2019-20</option>'
            f'<option selected="selected" value="{ts}">{label}</option><option value="55">2017-18</option></select>'
            f'{rankings}'
            f'<div class="card m-2"><div class="card-header">Schedule/Results</div><div class="card-body"><table>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div>')


def row(date: str, opponent: str, result: str, attendance: str = "1,000") -> str:
    return f'<tr class="underline_rows"><td>{date}</td><td>{opponent}</td><td nowrap="">{result}</td><td align="right">{attendance}</td></tr>'


def opp(ts: str, name: str, org: str, away: bool = False, suffix: str = "") -> str:
    return (("@" if away else "") + f'<a href="/teams/{ts}"><img class="logo_image" alt="{name}" '
            f'src="https://web2.ncaa.org/ncaa_style/img/All_Logos/sm//{org}.gif"> {name}</a>' + (f" <br>{suffix}" if suffix else ""))


def box(contest: str, text: str, star: bool = False) -> str:
    return f'<a target="BOX_SCORE_WINDOW" href="/contests/{contest}/box_score">{text}</a>' + ("*" if star else "")


def manifest(identity: str, state: str = "COMPLETE_GRAPH_EXHAUSTED", captures: int = 3, issued: str = "2026-08-13T10:00:00Z",
             pairs: list[tuple[str, str]] | None = None, discovery_identity: str | None = None,
             declared: int | None = None) -> dict:
    pairs = pairs if pairs is not None else [(str(i), f"sha{i}") for i in range(captures)]
    caps = [{"team_season_id": ts, "raw_sha256": sha, "raw_relative_path": f"raw/x/{sha}.html"} for ts, sha in pairs]
    return {"path": f"m/{identity}", "directory_identity": identity, "sha256": "f" * 64, "state": state,
            "issued_at_utc": issued, "discovery_identity": discovery_identity or identity, "season": 2022,
            "captures": caps, "failures": [], "discovered_team_season_ids": [p[0] for p in pairs],
            "capture_count": len(caps), "declared_capture_count": len(caps) if declared is None else declared,
            "pairs": sorted(set(pairs))}


class ContractTests(unittest.TestCase):
    """R38A01-01-A: contract-first and refusals."""

    def test_committed_contract_loads_and_is_valid(self) -> None:
        loaded, sha = pop.load_contract(CONTRACT)
        self.assertEqual(loaded["delivery_seasons"], list(range(2016, 2026)))
        self.assertEqual(len(sha), 64)

    def test_builder_refuses_without_the_contract(self) -> None:
        spec = importlib.util.spec_from_file_location("bas_population_builder", BUILDER)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "r.json"
            argv = ["--stage", "program-season", "--contract", str(Path(tmp) / "absent.json"), "--data-root", tmp,
                    "--output-canonical-root", str(Path(tmp) / "c"), "--output-manifest-root", str(Path(tmp) / "m"),
                    "--issued-at-utc", "2026-10-02T00:00:00Z", "--receipt", str(receipt)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(builder.main(argv), 2)
            written = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual((written["result"], written["refusal"]), ("REFUSED", "CONTRACT_MISSING"))
            self.assertFalse((Path(tmp) / "c").exists())
            before = receipt.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(builder.main(argv), 2)
            self.assertIn("RECEIPT_EXISTS", out.getvalue())
            self.assertEqual(receipt.read_bytes(), before)

    def test_contract_parameter_block_must_equal_the_implementation(self) -> None:
        for path, value in ((("parameters", "forward_match_days"), 2), (("parameters", "spring_2020_from"), "2021-01-15"),
                            (("parameters", "binding_thresholds", "name_confirmed_min_games"), 2)):
            bad = contract()
            target = bad
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.assertRaises(pop.PopulationRefused) as ctx:
                pop.validate_contract(bad)
            self.assertEqual(ctx.exception.code, "CONTRACT_PARAMETERS_MISMATCH")

    def test_delivery_season_2015_or_2026_is_refused(self) -> None:
        for seasons in ([2015, *range(2016, 2026)], [*range(2016, 2026), 2026], list(range(2016, 2025))):
            bad = contract()
            bad["delivery_seasons"] = seasons
            with self.assertRaises(pop.PopulationRefused) as ctx:
                pop.validate_contract(bad)
            self.assertEqual(ctx.exception.code, "CONTRACT_SEASONS_INVALID")

    def test_code_3_mapped_to_proven_division_iii_is_refused(self) -> None:
        for change in ({"proof_state": "PROVEN"}, {"label": "D-III"}):
            bad = contract()
            bad["division_decoding"]["table"]["3"].update(change)
            with self.assertRaises(pop.PopulationRefused):
                pop.validate_contract(bad)

    def test_denominator_from_observed_cfbd_rows_is_refused(self) -> None:
        for field in ("observed_rows_define_denominator", "cfbd_rows_define_denominator"):
            bad = contract()
            bad["denominator_authority"][field] = True
            with self.assertRaises(pop.PopulationRefused) as ctx:
                pop.validate_contract(bad)
            self.assertEqual(ctx.exception.code, "CONTRACT_DENOMINATOR_FROM_OBSERVATIONS")
        bad = contract()
        bad["observation_only_sources"] = ["E3", "E5"]
        with self.assertRaises(pop.PopulationRefused):
            pop.validate_contract(bad)

    def test_single_source_seasons_cannot_be_promoted(self) -> None:
        bad = contract()
        bad["reconciliation"]["single_source_pass_or_verified"] = "ALLOWED"
        with self.assertRaises(pop.PopulationRefused):
            pop.validate_contract(bad)
        bad = contract()
        bad["reconciliation"]["two_source_seasons"] = list(range(2016, 2026))
        with self.assertRaises(pop.PopulationRefused):
            pop.validate_contract(bad)


class BindingRuleTests(unittest.TestCase):
    """R38A01-02-A/B: one bound manifest per season under the declared rule."""

    def test_most_captures_then_latest_issued_at(self) -> None:
        bound = pop.bind_season_manifests([manifest("a", captures=3), manifest("b", captures=5),
                                           manifest("c", captures=5, issued="2026-08-14T17:18:28Z")])["bound"]
        self.assertEqual(bound["directory_identity"], "c")

    def test_partial_manifest_is_never_eligible(self) -> None:
        result = pop.bind_season_manifests([manifest("p", state="PARTIAL_MAXIMUM_TEAM_LIMIT_REACHED", captures=9),
                                            manifest("c", captures=3)])
        self.assertEqual(result["bound"]["directory_identity"], "c")

    def test_relabelled_partial_or_bumped_issued_at_changes_the_binding_and_is_refused(self) -> None:
        declared = {"identity": "c", "sha256": "f" * 64, "captures": 3}
        relabelled = pop.bind_season_manifests([manifest("p", captures=9), manifest("c", captures=3)])["bound"]
        with self.assertRaises(pop.PopulationRefused) as ctx:
            pop.verify_bound_against_contract(relabelled, declared, 2022)
        self.assertEqual(ctx.exception.code, "INPUT_BINDING_MISMATCH")
        bumped = pop.bind_season_manifests([manifest("c", captures=3),
                                            manifest("e", captures=3, issued="2026-09-30T00:00:00Z")])["bound"]
        with self.assertRaises(pop.PopulationRefused):
            pop.verify_bound_against_contract(bumped, declared, 2022)

    def test_inflated_capture_count_and_identity_mismatch_are_ineligible(self) -> None:
        result = pop.bind_season_manifests([manifest("x", captures=9, declared=12), manifest("y", captures=9,
                                            discovery_identity="other"), manifest("c", captures=3)])
        self.assertEqual(result["bound"]["directory_identity"], "c")
        problems = {row["identity"]: row["problems"] for row in result["census"]}
        self.assertEqual(problems["x"], ["CAPTURE_COUNT_MISMATCH"])
        self.assertEqual(problems["y"], ["DISCOVERY_IDENTITY_MISMATCH"])

    def test_unbreakable_tie_is_refused(self) -> None:
        with self.assertRaises(pop.PopulationRefused) as ctx:
            pop.bind_season_manifests([manifest("a", captures=4), manifest("b", captures=4)])
        self.assertEqual(ctx.exception.code, "REFUSED_UNBREAKABLE_TIE")

    def test_superseded_relations_and_absent_pairs_are_explicit_conflicts(self) -> None:
        bound = [(str(i), f"s{i}") for i in range(4)]
        census = pop.bind_season_manifests([
            manifest("b", pairs=bound), manifest("sub", pairs=bound[:2], issued="2026-08-12T00:00:00Z"),
            manifest("eq", pairs=bound, issued="2026-08-12T00:00:00Z"),
            manifest("x", pairs=[("9", "s9")], state="PARTIAL_MAXIMUM_TEAM_LIMIT_REACHED")])["census"]
        relations = {row["identity"]: row["relation"] for row in census}
        self.assertEqual(relations, {"b": "BOUND", "sub": "SUBSET", "eq": "EQUAL", "x": "DISJOINT"})
        x = [row for row in census if row["identity"] == "x"][0]
        self.assertEqual(x["pairs_absent_from_bound"], [["9", "s9"]])
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            raw = data / "raw" / "x"
            raw.mkdir(parents=True)
            in_season = page_html(ts="9", label="2022-23").encode("utf-8")
            sha = pop.sha256_bytes(in_season)
            (raw / f"{sha}.html").write_bytes(in_season)
            binding = {"census": [{"identity": "x", "pairs_absent_from_bound": [["9", sha]]}]}
            manifests = [manifest("x", pairs=[("9", sha)])]
            pop.classify_absent_pairs(binding, manifests, data, 2022)
            entry = binding["census"][0]["pairs_absent_classified"][0]
            self.assertEqual((entry["classification"], entry["state"]), ("IN_SEASON_TEAM_SEASON_ABSENT_FROM_BOUND", "CONFLICT"))
            self.assertTrue(entry["page_team_season_id_matches_pair"])
            other_id = page_html(ts="10", label="2022-23").encode("utf-8")
            sha3 = pop.sha256_bytes(other_id)
            (raw / f"{sha3}.html").write_bytes(other_id)
            binding = {"census": [{"identity": "x", "pairs_absent_from_bound": [["9", sha3]]}]}
            pop.classify_absent_pairs(binding, [manifest("x", pairs=[("9", sha3)])], data, 2022)
            entry = binding["census"][0]["pairs_absent_classified"][0]
            self.assertEqual(entry["classification"], "IN_SEASON_TEAM_SEASON_ABSENT_FROM_BOUND")
            self.assertFalse(entry["page_team_season_id_matches_pair"])
            cell = {"cell_key": "org:669:2022", "season": 2022, "ncaa_org_id": "669", "provider_key": None,
                    "flags": [f"SUPERSEDED_PAIR_ABSENT_FROM_BOUND:x:{sha3}"], "expected_sources": ["E1"], "e2": None,
                    "graph": None}
            pop.assign_program_season_disposition(cell)
            self.assertEqual((cell["disposition"], cell["disposition_reason"]),
                             ("CONFLICT", f"SUPERSEDED_PAIR_ABSENT_FROM_BOUND:x:{sha3}"))
            out_season = page_html(ts="9", label="2026-27").encode("utf-8")
            sha2 = pop.sha256_bytes(out_season)
            (raw / f"{sha2}.html").write_bytes(out_season)
            binding = {"census": [{"identity": "x", "pairs_absent_from_bound": [["9", sha2]]}]}
            pop.classify_absent_pairs(binding, [manifest("x", pairs=[("9", sha2)])], data, 2022)
            entry = binding["census"][0]["pairs_absent_classified"][0]
            self.assertEqual(entry["classification"], "OUT_OF_SEASON_PAGE_IN_SUPERSEDED_MANIFEST")
            self.assertEqual(entry["state"], "CONFLICT")

    def test_rehash_failure_cell_is_payload_missing_without_a_division(self) -> None:
        cell = {"cell_key": "org:1:2022", "season": 2022, "ncaa_org_id": "1", "provider_key": None, "flags": [],
                "expected_sources": ["E1"], "e2": None, "graph": {"rehash_ok": False, "raw_sha256": "x"}}
        pop.assign_program_season_disposition(cell)
        self.assertEqual((cell["disposition"], cell["disposition_reason"]), ("PAYLOAD_MISSING", "RAW_REHASH_MISMATCH"))
        self.assertIsNone(cell["division_code_observed"])


def season_label(season: int) -> str:
    return f"{season}-{(season + 1) % 100:02d}"


class GraphLoadTests(unittest.TestCase):
    """load_graph over a tiny synthetic lake: rehash, discovered-id accounting and duplicate captures."""

    def lake(self, tmp: str, *, flip: int | None = None, extra_discovered: int | None = None,
             duplicate: int | None = None) -> tuple[Path, dict]:
        data = Path(tmp) / "d"
        raw = data / "raw" / "SRC-015" / "ncaa_team_season_discovery"
        raw.mkdir(parents=True)
        bindings = {}
        for season in range(2015, 2026):
            payload = page_html(ts=f"{season}1", label=season_label(season)).encode("utf-8")
            sha = pop.sha256_bytes(payload)
            (raw / f"{sha}.html").write_bytes(payload if season != flip else payload[:-1] + b"X")
            capture = {"team_season_id": f"{season}1", "raw_sha256": sha,
                       "raw_relative_path": f"raw/SRC-015/ncaa_team_season_discovery/{sha}.html", "link_schema": 1}
            captures = [capture, capture] if season == duplicate else [capture]
            discovered = [f"{season}1"] + ([f"{season}9"] if season == extra_discovered else [])
            identity = f"m{season}"
            doc = {"state": "COMPLETE_GRAPH_EXHAUSTED", "issued_at_utc": "2026-08-13T10:00:00Z",
                   "discovery_identity": identity, "season": season, "captures": captures, "failures": [],
                   "discovered_team_season_ids": discovered, "team_page_capture_count": len(captures)}
            folder = data / pop.DISCOVERY_REL / str(season) / "sha256" / identity
            folder.mkdir(parents=True)
            text = json.dumps(doc).encode("utf-8")
            (folder / "ncaa_team_graph_discovery_manifest.json").write_bytes(text)
            bindings[str(season)] = {"identity": identity, "sha256": pop.sha256_bytes(text), "captures": len(captures)}
        bound = copy.deepcopy(contract())
        bound["input_bindings"]["bound_manifests"] = bindings
        return data, bound

    def test_rehash_failure_is_payload_missing_and_never_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data, bound = self.lake(tmp, flip=2018)
            graph = pop.load_graph(bound, data)
            flipped = graph["seasons"][2018]["pages"]["20181"]
            self.assertFalse(flipped["rehash_ok"])
            self.assertNotIn("page", flipped)
            good = graph["seasons"][2019]["pages"]["20191"]
            self.assertTrue(good["rehash_ok"] and good["identity_ok"])
            self.assertEqual(good["page"]["decode"]["code"], "12")
            self.assertEqual(good["page"]["ranking_links_identity_mismatched"], 0)

    def test_undiscovered_accounting_and_duplicate_capture_are_refused(self) -> None:
        for kwargs, code in (({"extra_discovered": 2020}, "DISCOVERED_ID_NOT_ACCOUNTED"),
                             ({"duplicate": 2021}, "DUPLICATE_CAPTURE_IN_BOUND_MANIFEST")):
            with tempfile.TemporaryDirectory() as tmp:
                data, bound = self.lake(tmp, **kwargs)
                with self.assertRaises(pop.PopulationRefused) as ctx:
                    pop.load_graph(bound, data)
                self.assertEqual(ctx.exception.code, code)


class DecoderTests(unittest.TestCase):
    """R38A01-03-A/B: division-code decoding and the target-season header record."""

    TABLE = contract()["division_decoding"]["table"]

    def test_accepted_forms(self) -> None:
        for codes, expected in ((["11"], "11"), (["11.0"], "11"), (["12", "12.0"], "12"), (["2"], "2"), (["3.0"], "3")):
            decoded = pop.decode_division(codes, self.TABLE)
            self.assertEqual((decoded["decode_state"], decoded["code"]), ("DECODED", expected))
        self.assertEqual(pop.decode_division(["3"], self.TABLE)["label"], "OUTSIDE_DI_CODE_3")

    def test_unknown_malformed_multiple_and_absent_codes_are_unresolved(self) -> None:
        cases = {("1",): "UNKNOWN_CODE", ("13",): "UNKNOWN_CODE", ("11.5",): "MALFORMED_CODE", ("",): "MALFORMED_CODE",
                 ("abc",): "MALFORMED_CODE", ("011",): "MALFORMED_CODE", ("11", "12"): "MULTIPLE_CODES",
                 (): "NO_CODE"}
        for codes, state in cases.items():
            self.assertEqual(pop.decode_division(list(codes), self.TABLE)["decode_state"], state, codes)
            cell = {"cell_key": "org:1:2018", "season": 2018, "ncaa_org_id": "1", "provider_key": None, "flags": [],
                    "expected_sources": ["E1"], "e2": None,
                    "graph": {"rehash_ok": True, "identity_ok": True,
                              "page": {"decode": pop.decode_division(list(codes), self.TABLE), "header_record": None}}}
            pop.assign_program_season_disposition(cell)
            self.assertEqual(cell["disposition"], "IDENTITY_UNRESOLVED")

    def test_page_parse_reads_codes_selector_and_target_header_record_only(self) -> None:
        page = pop.parse_graph_page(page_html(record="(4-7)", navbar_record="2026-27 Football (0-0)"))
        self.assertEqual(page["org_id"], "669")
        self.assertEqual(page["header_record"]["text"], "4-7")
        self.assertEqual(page["selected_team_season_id"], "100")
        self.assertEqual(page["selected_season_label"], "2018-19")
        self.assertEqual(page["season_options"]["2019-20"], "777")
        self.assertEqual(sorted(page["raw_division_codes"]), ["12", "12.0"])
        self.assertEqual(page["team_name"], "Missouri St.")
        header_free = page_html(record="", navbar_record="2026-27 Football (0-0)")
        self.assertIsNone(pop.parse_graph_page(header_free)["header_record"])

    def test_tie_record_and_note(self) -> None:
        page = pop.parse_graph_page(page_html(record='(2-9-1) <span class="italic">*COI vacated 5 wins</span>'))
        self.assertEqual(page["header_record"], {"wins": 2, "losses": 9, "ties": 1, "text": "2-9-1"})
        self.assertTrue(page["header_note"].startswith("*COI"))

    def test_ranking_links_count_only_for_the_page_organization_and_academic_year(self) -> None:
        foreign = ('<a href="/rankings/ranking_summary?academic_year=2019&amp;division=11&amp;org_id=999">x</a>'
                   '<a href="/rankings/ranking_summary?academic_year=2025&amp;division=11.0&amp;org_id=669">y</a>')
        page = pop.parse_graph_page(page_html(codes=("12",), extra_links=foreign))
        codes, mismatched = pop.page_division_codes(page, 2018)
        self.assertEqual((codes, mismatched), (["12"], 2))
        self.assertEqual(pop.decode_division(codes, self.TABLE)["code"], "12")
        self.assertEqual(pop.decode_division(page["raw_division_codes"], self.TABLE)["decode_state"], "MULTIPLE_CODES")
        only_foreign = pop.parse_graph_page(page_html(codes=(), extra_links=foreign))
        self.assertEqual(pop.page_division_codes(only_foreign, 2018), ([], 2))

    def test_code_mapping_never_comes_from_team_name(self) -> None:
        page = pop.parse_graph_page(page_html(name="Missouri St. FCS", codes=()))
        self.assertEqual(pop.decode_division(page["raw_division_codes"], self.TABLE)["decode_state"], "NO_CODE")


class ScheduleRowTests(unittest.TestCase):
    """Site, status and anomaly flags stated on the page's own rows."""

    def parse(self, *rows: str) -> list[dict]:
        return pop.parse_graph_page(page_html(rows=rows))["schedule_rows"]

    def test_home_away_neutral_and_event(self) -> None:
        rows = self.parse(row("09/01/2018", opp("1", "Oklahoma St.", "521", away=True), box("10", "L 17-58 ")),
                          row("09/08/2018", opp("2", "Arkansas", "31", suffix="@Arlington, Texas"), box("11", "W 45-24 ")),
                          row("12/01/2018", opp("3", "UNI", "416", away=True, suffix="FCS Championship"), box("12", "L 0-37 ")),
                          row("09/15/2018", opp("4", "Lincoln (MO)", "380"), box("13", "W 52-24 ")))
        self.assertEqual([r["page_team_marked_away"] for r in rows], [True, False, True, False])
        self.assertEqual(rows[1]["neutral_site"], "Arlington, Texas")
        self.assertIsNone(rows[2]["neutral_site"])
        self.assertEqual(rows[2]["event_label"], "FCS Championship")
        self.assertEqual([r["ncaa_contest_id"] for r in rows], ["10", "11", "12", "13"])
        self.assertEqual((rows[0]["team_points"], rows[0]["opponent_points"]), (17, 58))

    def test_canceled_postponed_plain_text_exempted_and_anomalies(self) -> None:
        rows = self.parse(row("04/03/2021", opp("5", "North Dakota", "493", away=True), "Canceled", ""),
                          row("11/21/2020", opp("6", "Ole Miss", "433"), "Ppd", ""),
                          row("09/10/2016", "@ Edward Waters ", box("14", "W 30-3 ")),
                          row("10/10/2020", opp("7", "Rice", "574"), box("15", "L 13-16 ", star=True)),
                          row("10/10/2018", opp("8", "Alcorn", "17"), box("16", "W 17-0 (-2 OT)")),
                          row("10/12/2016", opp("9", "Rice", "574"), box("17", "L 48-34 ")))
        self.assertEqual([r["status"] for r in rows], ["CANCELED", "UNSCORED", "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED"])
        self.assertIn("NO_CONTEST_LINK", rows[0]["flags"])
        self.assertFalse(rows[2]["opponent_linked"])
        self.assertEqual(rows[2]["opponent_name"], "Edward Waters")
        self.assertTrue(rows[2]["page_team_marked_away"])
        self.assertIn("EXEMPTED_NOT_COUNTED", rows[3]["flags"])
        self.assertIn("NEGATIVE_OVERTIME_MARKER", rows[4]["flags"])
        self.assertIn("RESULT_LETTER_CONTRADICTS_SCORE", rows[5]["flags"])

    def test_forfeit_text_outranks_a_stated_score(self) -> None:
        rows = self.parse(row("10/03/2020", opp("5", "Alcorn", "17"), box("20", "W 2-0 ") + " (Forfeit)"),
                          row("10/10/2020", opp("6", "Rice", "574"), "No Contest", ""))
        self.assertEqual([r["status"] for r in rows], ["FORFEIT", "NO_CONTEST"])
        self.assertEqual((rows[0]["team_points"], rows[0]["opponent_points"]), (2, 0))  # kept as an observation

    def test_contest_id_comes_from_the_document_link(self) -> None:
        rows = self.parse(row("09/01/2018", opp("1", "Rice", "574"), box("4242", "W 1-0 ")))
        self.assertEqual(rows[0]["ncaa_contest_id"], "4242")


class TeamHistoryTests(unittest.TestCase):
    """E2: blank-record rows survive as membership rows."""

    def history(self, rows: str) -> str:
        return ('<input type="hidden" name="org_id" id="org_id_search" value="17">'
                '<select name="org_id" id="org_id_select"><option selected="selected" value="17">Alcorn</option></select>'
                f'<table id="team_history_data_table"><thead><tr><th>Year</th></tr></thead><tbody>{rows}</tbody>'
                '<tfoot><tr><td></td><td></td><td></td><td></td><td>1</td><td>1</td><td>0</td><td>.5</td><td></td></tr></tfoot></table>')

    def test_blank_2020_row_is_kept(self) -> None:
        cells = lambda *v: "<tr>" + "".join(f"<td>{x}</td>" for x in v) + "</tr>"  # noqa: E731
        doc = self.history(cells('<a href="/teams/499">2020-21</a>', "Fred McNair", "FCS", "SWAC", "", "", "", ".000", "opt out")
                           + cells('<a href="/teams/400">2019-20</a>', "Fred McNair", "FCS", "SWAC", "9", "4", "0", ".692", ""))
        parsed = pop.parse_team_history_page(doc)
        self.assertEqual(parsed["org_id"], "17")
        self.assertEqual(parsed["team_name"], "Alcorn")
        by_season = {r["season"]: r for r in parsed["rows"]}
        self.assertEqual(by_season[2020]["record_state"], "UNPLAYED_OR_BLANK")
        self.assertIsNone(by_season[2020]["wins"])
        self.assertEqual(by_season[2020]["team_season_id"], "499")
        self.assertEqual(by_season[2019]["wins"], 9)

    def test_page_without_table_is_rejected_on_content(self) -> None:
        self.assertIsNone(pop.parse_team_history_page("<html>Loading.... Terms and Conditions</html>"))


class DispositionTests(unittest.TestCase):
    """R38A01-04-A/C: one disposition per expected key."""

    TABLE = contract()["division_decoding"]["table"]

    def cell(self, codes=("12",), e2=None, rehash=True, identity=True, header=True, provider=None, graph=True,
             failure=None):
        page = {"decode": pop.decode_division(list(codes), self.TABLE),
                "header_record": {"wins": 4, "losses": 7, "ties": None, "text": "4-7"} if header else None,
                "team_name": "Missouri St."}
        return {"cell_key": "org:669:2018", "season": 2018, "ncaa_org_id": "669", "provider_key": provider,
                "flags": [], "expected_sources": ["E1"], "e2": e2,
                "graph": ({"rehash_ok": rehash, "identity_ok": identity, "page": page, "raw_sha256": "s"} if graph else None),
                **({"capture_failure": failure} if failure else {})}

    def assign(self, c):
        pop.assign_program_season_disposition(c)
        return c["disposition"], c["in_division_i_population"]

    def test_vocabulary(self) -> None:
        self.assertEqual(self.assign(self.cell()), ("VERIFIED_PRESENT", True))
        self.assertEqual(self.assign(self.cell(codes=("2",))), ("NOT_APPLICABLE", False))
        self.assertEqual(self.assign(self.cell(header=False)), ("CANDIDATE_ONLY", True))
        self.assertEqual(self.assign(self.cell(identity=False))[0], "IDENTITY_UNRESOLVED")
        self.assertEqual(self.assign(self.cell(e2={"division_label": "FBS"}))[0], "CONFLICT")
        self.assertEqual(self.assign(self.cell(codes=("3",), e2={"division_label": "D-III"}))[0], "NOT_APPLICABLE")
        self.assertEqual(self.assign(self.cell(graph=False, failure={"condition": "TIMEOUT"}))[0], "PAYLOAD_MISSING")
        self.assertEqual(self.assign(self.cell(provider="SRC-002:TEAM:1", graph=False))[0], "IDENTITY_UNRESOLVED")

    def test_source_absent_keeps_official_division_and_never_projects(self) -> None:
        official = self.cell(graph=False, e2={"division_label": "FCS", "conference": "SWAC", "record_state": "UNPLAYED_OR_BLANK"})
        self.assertEqual(self.assign(official), ("SOURCE_ABSENT", True))
        self.assertEqual(official["division_authority"], "OFFICIAL_TEAM_HISTORY_ROW")
        self.assertEqual(official["division_label"], "FCS")
        self.assertIsNone(official["division_code_observed"])
        unknown = self.cell(graph=False)
        unknown["e4"] = [{"team_season_id": "1", "adjacent_codes": ["12"]}]
        self.assertEqual(self.assign(unknown), ("SOURCE_ABSENT", None))
        self.assertEqual(unknown["division_label"], "UNKNOWN_NOT_PROJECTED")

    def test_official_labels_map_to_the_contract_vocabulary(self) -> None:
        for raw, label, in_di in (("D-II", "DII", False), ("D-III", "DIII", False), ("FBS", "FBS", True)):
            c = self.cell(graph=False, e2={"division_label": raw})
            self.assertEqual(self.assign(c), ("SOURCE_ABSENT", in_di))
            self.assertEqual((c["division_label"], c["observations"]["team_history_label"]), (label, raw))
        odd = self.cell(graph=False, e2={"division_label": "I-AA"})
        self.assertEqual(self.assign(odd), ("IDENTITY_UNRESOLVED", None))
        d3 = self.cell(codes=("3",), e2={"division_label": "D-III"})
        self.assertEqual(self.assign(d3), ("NOT_APPLICABLE", False))
        self.assertIn("OFFICIAL_D_III_OVER_CODE_3", d3["flags"])

    def test_conflict_rules_use_the_triggering_flag(self) -> None:
        for flag in ("OFFICIAL_HISTORY_VARIANT_CONFLICT", "FAILED_CAPTURE_FOR_ORGANIZATION_WITH_PAGE:9",
                     "DUPLICATE_TEAM_SEASON_PAGES:1,2"):
            c = self.cell()
            c["flags"] = ["TRANSITION_ACROSS_UNOBSERVED_SEASON", flag]
            self.assertEqual(self.assign(c)[0], "CONFLICT")
            self.assertEqual(c["disposition_reason"], flag)
        self.assertIsNone(c["division_code_observed"])  # duplicate pages record no division code

    def test_cfbd_classification_never_overrides_the_official_code(self) -> None:
        c = self.cell(codes=("12",))
        c["e3"] = {"classification": "fbs"}
        self.assertEqual(self.assign(c), ("VERIFIED_PRESENT", True))
        self.assertEqual(c["division_label"], "FCS")
        self.assertEqual(c["observations"]["cfbd_e3_classification"], "fbs")

    def test_transitions_are_contemporaneous(self) -> None:
        cells = {}
        for season, code in ((2017, "12"), (2018, "11"), (2019, "11")):
            c = self.cell(codes=(code,))
            c["season"], c["cell_key"] = season, f"org:669:{season}"
            pop.assign_program_season_disposition(c)
            cells[c["cell_key"]] = c
        consecutive, across = pop.observe_transitions(cells)
        self.assertEqual(consecutive, {("669", 2018): {"from_code": "12", "to_code": "11", "from_season": 2017,
                                                       "rule": "contemporaneous codes on each season's own page"}})
        self.assertEqual(across, {})
        gap = {}
        for season, code in ((2019, "3"), (2021, "12")):  # 2020 has no decoded page
            c = self.cell(codes=(code,))
            c["season"], c["cell_key"] = season, f"org:669:{season}"
            pop.assign_program_season_disposition(c)
            gap[c["cell_key"]] = c
        consecutive, across = pop.observe_transitions(gap)
        self.assertEqual(consecutive, {})
        self.assertEqual(across[("669", 2021)]["unobserved_seasons"], [2020])
        self.assertEqual((across[("669", 2021)]["from_code"], across[("669", 2021)]["to_code"]), ("3", "12"))

    def test_summary_is_recomputed_from_cells(self) -> None:
        a, b = self.cell(), self.cell(codes=("2",))
        for c in (a, b):
            pop.assign_program_season_disposition(c)
            c.update(expected_sources=["E1"], e4=[])
        summary = pop.program_season_summary([a, b], [])["2018"]
        self.assertEqual(summary["cells"], 2)
        self.assertEqual(summary["by_disposition"], {"NOT_APPLICABLE": 1, "VERIFIED_PRESENT": 1})


class BindingTests(unittest.TestCase):
    """Identity binding: name candidates confirmed by schedule; never name-only."""

    EXP = contract()["reconciliation"]["participant_resolution"]["token_expansions"]

    def games(self, team: str, results: list[tuple[str, int, int]]) -> list[dict]:
        return [{"local_dates": [d], "home_id": team, "away_id": "x" + d, "home_points": p, "away_points": q}
                for d, p, q in results]

    def test_name_confirmed_collision_disambiguated_fingerprint_only_and_refusals(self) -> None:
        sched = [("2018-09-01", 30, 10), ("2018-09-08", 21, 14), ("2018-09-15", 7, 3), ("2018-09-22", 28, 0),
                 ("2018-09-29", 35, 17)]
        cfbd = self.games("2623", sched) + self.games("9999", [("2018-10-06", 1, 0)])
        names = {"2623": {"Missouri State"}, "193": {"Miami (OH)"}, "2390": {"Miami (FL)"}}
        result = pop.bind_organizations({"669": sched}, {"669": {"Missouri St."}}, cfbd, names, self.EXP)
        self.assertEqual((result["669"]["cfbd_team_id"], result["669"]["rule"]), ("2623", "NAME_CONFIRMED_BY_SCHEDULE"))
        name_only = pop.bind_organizations({"669": [("2019-09-01", 1, 2)]}, {"669": {"Missouri St."}}, cfbd, names, self.EXP)
        self.assertIsNone(name_only["669"]["cfbd_team_id"])
        self.assertEqual(name_only["669"]["reason"], "NAME_CANDIDATE_NOT_CONFIRMED_BY_SCHEDULE")
        collide = {"2623": {"Miami"}, "193": {"Miami"}}
        disamb = pop.bind_organizations({"669": sched}, {"669": {"Miami"}}, cfbd, collide, self.EXP)
        self.assertEqual(disamb["669"]["rule"], "NAME_COLLISION_DISAMBIGUATED_BY_SCHEDULE")
        nameless = pop.bind_organizations({"669": sched}, {"669": {"MSU Bears"}}, cfbd, names, self.EXP)
        self.assertEqual(nameless["669"]["rule"], "SCHEDULE_FINGERPRINT_ONLY")
        none = pop.bind_organizations({"669": []}, {"669": {"Missouri St."}}, cfbd, names, self.EXP)
        self.assertEqual(none["669"]["reason"], "NO_SCHEDULE_EVIDENCE")

    def test_one_to_one_violation_leaves_both_unresolved(self) -> None:
        sched = [("2018-09-0%d" % i, 10 + i, i) for i in range(1, 8)]
        cfbd = self.games("2623", sched)
        names = {"2623": {"Missouri State"}}
        result = pop.bind_organizations({"669": sched, "670": sched}, {"669": {"Missouri St."}, "670": {"Missouri State"}},
                                        cfbd, names, self.EXP)
        self.assertEqual({o: r["reason"] for o, r in result.items()},
                         {"669": "BINDING_NOT_ONE_TO_ONE", "670": "BINDING_NOT_ONE_TO_ONE"})

    def test_alias_collisions_do_not_resolve_by_name(self) -> None:
        for left, right in (("Ohio", "Ohio St."), ("FIU", "FAU"), ("Miami (FL)", "Miami (OH)"),
                            ("North Dakota", "North Dakota St."), ("South Dakota", "South Dakota St.")):
            self.assertNotEqual(pop.normalize_name(left, self.EXP), pop.normalize_name(right, self.EXP))


def m1_fixture() -> dict:
    """Two FCS teams (669, 702), an FBS team (521), a D-II team (380) and a 2024 FCS pair, all synthetic."""
    def cell(org, season, code, ts):
        label = {"11": "FBS", "12": "FCS", "2": "DII"}[code]
        return {"cell_key": f"org:{org}:{season}", "season": season, "ncaa_org_id": org, "ncaa_team_season_id": ts,
                "division_code_observed": code, "division_authority": "GRAPH_PAGE", "division_label": label,
                "in_division_i_population": code in ("11", "12"), "disposition": "VERIFIED_PRESENT", "team_name": org}
    pages = [{"season": s, "team_season_id": ts, "org_id": org, "team_name": org,
              "header_record": {"wins": 1, "losses": 0, "ties": None, "text": "1-0"}}
             for s, ts, org in ((2018, "a1", "669"), (2018, "a2", "702"), (2018, "a3", "521"), (2018, "a4", "380"),
                                (2020, "c1", "669"), (2020, "c2", "702"), (2024, "b1", "669"), (2024, "b2", "702"))]
    cells = [cell("669", 2018, "12", "a1"), cell("702", 2018, "12", "a2"), cell("521", 2018, "11", "a3"),
             cell("380", 2018, "2", "a4"), cell("669", 2020, "12", "c1"), cell("702", 2020, "12", "c2"),
             cell("669", 2024, "12", "b1"), cell("702", 2024, "12", "b2")]

    def obs(season, ts, org, date, cid, opp_ts, away, pts, opp_pts, status="COMPLETED", neutral=None):
        return {"season": season, "page_team_season_id": ts, "page_org_id": org, "page_team_name": org,
                "ncaa_contest_id": cid, "opponent_team_season_id": opp_ts, "opponent_logo_org_id": None,
                "opponent_name": "x", "opponent_linked": True, "page_team_marked_away": away, "neutral_site": neutral,
                "event_label": None, "date": date, "status": status, "team_points": pts, "opponent_points": opp_pts,
                "flags": [] if cid else ["NO_CONTEST_LINK"]}
    observations = [
        obs(2018, "a1", "669", "2018-09-15", "1", "a2", False, 40, 8), obs(2018, "a2", "702", "2018-09-15", "1", "a1", True, 8, 40),
        obs(2018, "a1", "669", "2018-08-30", "2", "a3", True, 17, 58), obs(2018, "a3", "521", "2018-08-30", "2", "a1", False, 58, 17),
        obs(2018, "a1", "669", "2018-09-06", "3", "a4", True, 52, 24), obs(2018, "a4", "380", "2018-09-06", "3", "a1", False, 24, 52),
        obs(2018, "a1", "669", "2018-10-06", None, "a2", True, None, None, status="CANCELED"),
        dict(obs(2018, "a1", "669", "2018-09-22", "6", None, False, 66, 0), opponent_name="Edward Waters",
             opponent_linked=False),
        obs(2020, "c1", "669", "2021-03-06", "5", "c2", False, 30, 24), obs(2020, "c2", "702", "2021-03-06", "5", "c1", True, 24, 30),
        obs(2024, "b1", "669", "2024-09-07", "4", "b2", False, 21, 14, neutral="Frisco, TX"),
        obs(2024, "b2", "702", "2024-09-07", "4", "b1", False, 14, 21, neutral="Frisco, TX"),
    ]
    bindings = [{"org_id": "669", "cfbd_team_id": "2623"}, {"org_id": "702", "cfbd_team_id": "2460"},
                {"org_id": "521", "cfbd_team_id": "197"}, {"org_id": "380", "cfbd_team_id": None}]
    return {"pages": pages, "cells": cells, "observations": observations, "bindings": bindings}


def cfbd_game(gid, season, date, home, away, hp, ap, neutral=False, completed=True, start=None,
              home_cls="fcs", away_cls="fcs"):
    local = pop.cfbd_local_dates(start) if start else [date]
    return {"cfbd_game_id": gid, "season": season, "local_dates": local, "start_utc": start, "home_id": home,
            "away_id": away, "home_points": hp, "away_points": ap, "neutral_site": neutral, "completed": completed,
            "home_team": home, "away_team": away, "home_classification": home_cls, "away_classification": away_cls,
            "season_type": "regular", "week": 1, "routes": ["CYCLE30_FCS"]}


class ContestTests(unittest.TestCase):
    """R38A01-05-A/B/C and R38A01-06-A/B."""

    EXP = contract()["reconciliation"]["participant_resolution"]["token_expansions"]

    def build(self, games_2018=None, m1=None):
        games = {s: [] for s in pop.TWO_SOURCE_SEASONS}
        games[2018] = games_2018 if games_2018 is not None else [
            cfbd_game("g1", 2018, "2018-09-15", "2623", "2460", 40, 8),
            cfbd_game("g2", 2018, "2018-08-31", "197", "2623", 58, 17),
            cfbd_game("g3", 2018, "2018-09-06", "999", "2623", 24, 52)]
        games[2020] = [cfbd_game("g5", 2020, "2021-03-06", "2623", "2460", 30, 24)]
        built = pop.build_contests(m1 or m1_fixture(), games, self.EXP)
        return {c["contest_key"]: c for c in built["contests"]}, built["orientations"]

    def test_game_grain_two_orientations_and_external_opponents(self) -> None:
        contests, orientations = self.build()
        self.assertEqual(len(orientations), 2 * len(contests))
        self.assertEqual(contests["ncaa:1"]["classification_pair"], "FCS-FCS")
        self.assertEqual(contests["ncaa:1"]["mirror_observation_count"], 2)
        self.assertEqual(contests["ncaa:3"]["classification_pair"], "FCS-DII")
        mirror_site = {"HOME": "AWAY", "AWAY": "HOME", "NEUTRAL": "NEUTRAL", "UNKNOWN": "UNKNOWN"}
        for c in contests.values():
            pair = sorted((o for o in orientations if o["contest_key"] == c["contest_key"]), key=lambda o: o["side"])
            self.assertEqual([o["side"] for o in pair], [0, 1])
            for me, them in ((pair[0], pair[1]), (pair[1], pair[0])):
                self.assertEqual(me["team_points"], them["opponent_points"])
                self.assertEqual(me["team_key"], them["opponent_key"])
                self.assertEqual(mirror_site[me["site_for_team"]], them["site_for_team"])
            if c["competitive"] and c["a_points"] is not None:
                self.assertEqual(pair[0]["margin"] + pair[1]["margin"], 0)
                self.assertIn({pair[0]["result"], pair[1]["result"]}, ({"W", "L"}, {"T"}))
        views = {(o["contest_key"], o["team_key"]): o["view"] for o in orientations}
        self.assertEqual(views[("ncaa:3", "org:380")], "EXTERNAL_OPPONENT_VIEW")  # D-II participant
        self.assertEqual(views[("ncaa:3", "org:669")], "PARTICIPANT_VIEW")
        self.assertEqual(views[("ncaa:6", "ext:edward waters")], "EXTERNAL_OPPONENT_VIEW")  # plain-text opponent
        self.assertEqual(contests["ncaa:6"]["classification_pair"], "FCS-NON_NCAA")

    def test_canceled_contest_is_retained_and_never_competitive(self) -> None:
        contests, orientations = self.build()
        canceled = [c for c in contests.values() if c["contest_status"] == "CANCELED"]
        self.assertEqual(len(canceled), 1)
        self.assertFalse(canceled[0]["competitive"])
        self.assertEqual(canceled[0]["disposition"], "CANDIDATE_ONLY")
        self.assertTrue(all(o["result"] is None for o in orientations if o["contest_key"] == canceled[0]["contest_key"]))

    def test_site_comes_from_page_markers(self) -> None:
        contests, _ = self.build()

        def home_org(c):
            return {"HOME_A": c["a_org_id"], "HOME_B": c["b_org_id"]}.get(c["site"], c["site"])
        self.assertEqual(home_org(contests["ncaa:1"]), "669")  # 669's page: no '@' -> 669 is home
        self.assertEqual(home_org(contests["ncaa:2"]), "521")  # 669's page: '@' -> Oklahoma St. (521) is home
        self.assertEqual(home_org(contests["ncaa:3"]), "380")
        self.assertEqual(contests["ncaa:4"]["site"], "NEUTRAL")

    def test_two_source_reconciliation_and_single_bound_participant(self) -> None:
        contests, _ = self.build()
        self.assertEqual((contests["ncaa:1"]["disposition"], contests["ncaa:1"]["reconciliation_state"]),
                         ("VERIFIED_PRESENT", "RECONCILED_2016_2023"))
        self.assertEqual(contests["ncaa:2"]["reconciliation_state"], "RECONCILED_2016_2023")
        self.assertEqual(contests["ncaa:3"]["disposition_reason"], "OPPONENT_IDENTITY_NOT_BOUND")
        self.assertEqual(contests["ncaa:3"]["disposition"], "CANDIDATE_ONLY")

    def test_score_and_date_disagreements_keep_both_values(self) -> None:
        games = [cfbd_game("g1", 2018, "2018-09-15", "2623", "2460", 40, 9),
                 cfbd_game("g2", 2018, "2018-09-02", "197", "2623", 58, 17)]
        contests, orientations = self.build(games)
        self.assertEqual(contests["ncaa:1"]["disposition"], "CONFLICT")
        self.assertEqual(contests["ncaa:1"]["conflict_fields"], [{"field": "score", "ncaa": [40, 8], "cfbd": [40, 9]}])
        # g2 is three days from the page date with the same pair and score: CONFLICT on date, never a second contest
        self.assertNotIn("cfbd:g2", contests)
        self.assertEqual((contests["ncaa:2"]["disposition"], contests["ncaa:2"]["cfbd_game_ids"]), ("CONFLICT", ["g2"]))
        self.assertEqual(contests["ncaa:2"]["conflict_fields"][0]["field"], "date")
        self.assertEqual(sum(1 for o in orientations if o["contest_key"] == "ncaa:2"), 2)

    def test_cfbd_utc_evening_kickoff_matches_the_local_page_date(self) -> None:
        # NCAA page 2018-08-30; CFBD 2018-08-31T02:30Z is 2018-08-30 in every US zone (its UTC date is 08-31)
        self.assertEqual(pop.cfbd_local_dates("2018-08-31T02:30:00.000Z"), ["2018-08-30"])
        self.assertEqual(pop.cfbd_local_dates("2023-09-02T04:00:00.000Z"), ["2023-09-01", "2023-09-02"])
        games = [cfbd_game("g1", 2018, None, "2623", "2460", 40, 8, start="2018-09-16T03:00:00.000Z"),
                 cfbd_game("g2", 2018, None, "197", "2623", 58, 17, start="2018-08-31T02:30:00.000Z"),
                 cfbd_game("g3", 2018, "2018-09-06", "999", "2623", 24, 52)]
        contests, _ = self.build(games)
        self.assertEqual(contests["ncaa:1"]["cfbd_game_ids"], ["g1"])
        self.assertEqual(contests["ncaa:2"]["disposition"], "VERIFIED_PRESENT")
        self.assertFalse([k for k in contests if k.startswith("cfbd:")])

    def test_mirror_disagreements_null_the_value_and_conflict(self) -> None:
        m1 = m1_fixture()
        for o in m1["observations"]:
            if o["ncaa_contest_id"] == "1" and o["page_org_id"] == "702":
                o["opponent_points"] = 41  # 702's page says 8-41, 669's page says 40-8
            if o["ncaa_contest_id"] == "5" and o["page_org_id"] == "702":
                o["date"] = "2021-01-10"  # the mirrors straddle the 2021-01-16 term boundary
        contests, orientations = self.build(m1=m1)
        c1 = contests["ncaa:1"]
        self.assertEqual((c1["a_points"], c1["b_points"], c1["disposition"]), (None, None, "CONFLICT"))
        self.assertEqual(c1["mirror_scores_observed"], [[40, 8], [41, 8]])
        self.assertTrue(all(o["result"] is None for o in orientations if o["contest_key"] == "ncaa:1"))
        c5 = contests["ncaa:5"]
        self.assertEqual((c5["contest_date"], c5["term"], c5["disposition"]), (None, "UNRESOLVED", "CONFLICT"))
        self.assertEqual(c5["contest_dates_observed"], ["2021-01-10", "2021-03-06"])
        self.assertEqual(c5["cfbd_game_ids"], ["g5"])  # still claimed: never re-emitted as a cfbd: contest
        self.assertNotIn("cfbd:g5", contests)

    def test_duplicate_pair_dates_and_lone_participants_are_kept_as_conflicts(self) -> None:
        m1 = m1_fixture()
        extra = [dict(o, ncaa_contest_id="8") for o in m1["observations"] if o["ncaa_contest_id"] == "4"]
        lone = dict(m1["observations"][0], ncaa_contest_id="9", opponent_team_season_id="a1", date="2018-11-03")
        m1["observations"] += extra + [lone]
        contests, orientations = self.build(m1=m1)
        for key in ("ncaa:4", "ncaa:8"):
            self.assertEqual((contests[key]["disposition"], contests[key]["reconciliation_state"]),
                             ("CONFLICT", "SINGLE_SOURCE_UNRECONCILED"))
            self.assertIn("DUPLICATE_PAIR_DATE", contests[key]["flags"])
        self.assertEqual(contests["ncaa:9"]["disposition"], "CONFLICT")
        self.assertTrue(contests["ncaa:9"]["b_key"].startswith("unresolved:") or contests["ncaa:9"]["a_key"].startswith("unresolved:"))
        self.assertEqual(sum(1 for o in orientations if o["contest_key"] == "ncaa:9"), 2)

    def test_non_competitive_on_both_sources_is_reconciled_not_conflict(self) -> None:
        canceled = {False: "NON_COMPETITIVE_BOTH_SOURCES", True: "NON_COMPETITIVE_STATUS_BUT_CFBD_GAME"}
        for completed, reason in canceled.items():
            games = [cfbd_game("g1", 2018, "2018-09-15", "2623", "2460", 40, 8),
                     cfbd_game("g7", 2018, "2018-10-06", "2460", "2623", None, None, completed=completed)]
            contests, _ = self.build(games)
            nolink = [c for k, c in contests.items() if k.startswith("nolink:")][0]
            self.assertEqual((nolink["disposition_reason"], nolink["cfbd_game_ids"]), (reason, ["g7"]))

    def test_cfbd_only_scope_comes_from_ncaa_membership(self) -> None:
        m1 = m1_fixture()
        m1["bindings"] = [b if b["org_id"] != "380" else {"org_id": "380", "cfbd_team_id": "38"} for b in m1["bindings"]]
        games = [cfbd_game("g1", 2018, "2018-09-15", "2623", "2460", 40, 8),
                 cfbd_game("x1", 2018, "2018-11-10", "38", "77", 10, 7, home_cls="fcs", away_cls="ii"),
                 cfbd_game("x2", 2018, "2018-11-17", "38", "78", 10, 7, home_cls="ii", away_cls="fcs")]
        contests, _ = self.build(games, m1=m1)
        self.assertNotIn("cfbd:x1", contests)  # D-II by NCAA page; the provider's fcs label never includes it
        x2 = contests["cfbd:x2"]
        self.assertEqual(x2["disposition"], "IDENTITY_UNRESOLVED")
        self.assertIn("INCLUDED_FOR_UNRESOLVED_DIVISION_I_MEMBERSHIP", x2["flags"])

    def test_many_to_one_is_conflict(self) -> None:
        games = [cfbd_game("g1", 2018, "2018-09-15", "2623", "2460", 40, 8),
                 cfbd_game("g9", 2018, "2018-09-16", "2623", "2460", 40, 8)]
        contests, _ = self.build(games)
        self.assertEqual((contests["ncaa:1"]["disposition"], contests["ncaa:1"]["disposition_reason"]),
                         ("CONFLICT", "NOT_ONE_TO_ONE"))

    def test_spring_2020_keeps_season_label(self) -> None:
        contests, _ = self.build()
        self.assertEqual((contests["ncaa:5"]["season"], contests["ncaa:5"]["term"]), (2020, "SPRING"))
        self.assertEqual(contests["ncaa:5"]["reconciliation_state"], "RECONCILED_2016_2023")
        self.assertEqual(pop.contest_term(2020, "2020-10-10"), "FALL")
        self.assertEqual(pop.contest_term(2021, "2022-01-01"), "FALL")

    def test_2024_contests_are_single_source_and_never_verified(self) -> None:
        contests, _ = self.build()
        c = contests["ncaa:4"]
        self.assertEqual((c["reconciliation_state"], c["exposure"], c["disposition"]),
                         ("SINGLE_SOURCE_UNRECONCILED", "EXPOSED_NOT_PROTECTED", "CANDIDATE_ONLY"))
        self.assertEqual(c["cfbd_game_ids"], [])

    def test_deleting_fcs_rows_or_dropping_a_non_division_i_opponent_is_visible(self) -> None:
        full, _ = self.build()
        m1 = m1_fixture()
        m1["observations"] = [o for o in m1["observations"] if o["ncaa_contest_id"] not in ("1", "3")]
        reduced, orientations = self.build(m1=m1)
        self.assertEqual(set(full) - set(reduced), {"ncaa:1", "ncaa:3"})
        g1 = reduced["cfbd:g1"]
        self.assertEqual((g1["disposition"], g1["site"], g1["contest_status"], g1["competitive"]),
                         ("SOURCE_ABSENT", "UNKNOWN", "NOT_OFFICIALLY_OBSERVED", False))
        self.assertEqual((g1["a_key"], g1["b_key"], g1["a_points"], g1["b_points"]), ("org:669", "org:702", None, None))
        self.assertEqual((g1["cfbd_observation"]["home_points"], g1["cfbd_observation"]["away_points"]), (40, 8))
        self.assertTrue(all(o["result"] is None and o["site_for_team"] == "UNKNOWN"
                            for o in orientations if o["contest_key"] == "cfbd:g1"))
        g3 = reduced["cfbd:g3"]  # 999 is unbound with CFBD class fcs: in scope through the bound FCS side
        self.assertEqual((g3["disposition"], g3["a_key"], g3["b_key"]), ("IDENTITY_UNRESOLVED", "cfbdteam:999", "org:669"))

    def test_duplicate_routes_merge_and_conflicting_routes_are_reported(self) -> None:
        a = {"cfbd_game_id": "1", "route": "SRC-002", "home_points": 3}
        merged, conflicts = pop.union_cfbd([[a], [dict(a, route="CYCLE30_FCS")]])
        self.assertEqual((len(merged), merged[0]["routes"], conflicts), (1, ["CYCLE30_FCS", "SRC-002"], []))
        merged, conflicts = pop.union_cfbd([[a], [dict(a, route="CYCLE30_FCS", home_points=4)]])
        self.assertEqual(len(conflicts), 1)

    def test_schedule_cardinality_and_record(self) -> None:
        contests, orientations = self.build()
        rows = {r["cell_key"]: r for r in pop.schedule_reconciliation(m1_fixture(), list(contests.values()), orientations)}
        self.assertEqual(rows["org:669:2018"]["page_rows"], 5)
        self.assertEqual(rows["org:669:2018"]["contest_rows"], 5)
        self.assertEqual(rows["org:669:2018"]["orientation_rows"], 5)
        self.assertEqual(rows["org:669:2018"]["derived_record"], {"wins": 3, "losses": 1, "ties": 0})
        self.assertIn("HEADER_RECORD_MISMATCH", rows["org:669:2018"]["state"])

    def test_subsets_are_derived_from_the_parent_both_ways(self) -> None:
        contests, _ = self.build()
        parent = list(contests.values())
        subsets = pop.derive_subsets(parent)
        self.assertEqual(sorted(subsets["FCS_SUBSET"]), sorted(k for k, c in contests.items()
                                                                if "12" in (c["a_division_code"], c["b_division_code"])))
        self.assertEqual(subsets["FBS_ESTIMAND_SUBSET"], [])
        bad = copy.deepcopy(subsets)
        bad["FCS_SUBSET"].append("cfbd:not-in-parent")
        self.assertTrue(any("absent from the parent" in p for p in pop.prove_subsets(parent, bad)))
        bad = copy.deepcopy(subsets)
        bad["FCS_SUBSET"].remove("ncaa:1")
        self.assertTrue(any("missing" in p for p in pop.prove_subsets(parent, bad)))
        bad = copy.deepcopy(subsets)
        bad["FBS_ESTIMAND_SUBSET"] = ["ncaa:1"]
        self.assertTrue(any("does not satisfy" in p for p in pop.prove_subsets(parent, bad)))


class ImmutabilityTests(unittest.TestCase):
    """R38A01-01-A / R38A01-09-A: content-addressed, create-only outputs."""

    def roots(self, tmp: str) -> tuple[Path, Path]:
        base = Path(tmp) / "d"
        return base / "canonical" / "p", base / "manifests" / "p"

    def test_identical_rebuild_is_verified_not_rewritten_and_divergence_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outc, outm = self.roots(tmp)
            kwargs = dict(canonical_root=outc, manifest_root=outm, stage="program-season", contract_sha256="c" * 64,
                          inputs={}, upstream={}, manifest_extra={"issued_at_utc": "2026-10-02T00:00:00Z"})
            first = pop.materialize(files={"a.json": b"1\n"}, **kwargs)
            self.assertEqual(first["state"], "MATERIALIZED")
            manifest_bytes = Path(first["manifest"]).read_bytes()
            stamp = (Path(first["data_dir"]) / "a.json").stat().st_mtime_ns
            again = pop.materialize(files={"a.json": b"1\n"}, **dict(kwargs, manifest_extra={"issued_at_utc": "2026-10-03T00:00:00Z"}))
            self.assertEqual((again["state"], again["identity"], again["written_bytes"]),
                             ("ALREADY_PRESENT_IDENTICAL", first["identity"], 0))
            self.assertEqual(Path(first["manifest"]).read_bytes(), manifest_bytes)  # issued_at of the first run kept
            self.assertEqual((Path(first["data_dir"]) / "a.json").stat().st_mtime_ns, stamp)
            self.assertIn("runtime", json.loads(manifest_bytes))
            self.assertEqual([p.name for p in Path(first["data_dir"]).parent.iterdir() if p.name.startswith(".partial")], [])
            Path(first["manifest"]).unlink()
            completed = pop.materialize(files={"a.json": b"1\n"}, **kwargs)
            self.assertEqual(completed["state"], "MANIFEST_COMPLETED")
            (Path(first["data_dir"]) / "extra.json").write_bytes(b"x")
            with self.assertRaises(pop.PopulationRefused) as ctx:
                pop.materialize(files={"a.json": b"1\n"}, **kwargs)
            self.assertEqual(ctx.exception.code, "IMMUTABLE_COLLISION")
            (Path(first["data_dir"]) / "extra.json").unlink()
            target = Path(first["data_dir"]) / "a.json"
            target.write_bytes(b"2\n")
            with self.assertRaises(pop.PopulationRefused) as ctx:
                pop.materialize(files={"a.json": b"1\n"}, **kwargs)
            self.assertEqual(ctx.exception.code, "IMMUTABLE_COLLISION")
            other = pop.materialize(files={"a.json": b"1\n"}, **dict(kwargs, contract_sha256="d" * 64))
            self.assertNotEqual(other["identity"], first["identity"])

    def test_upstream_manifest_under_another_contract_or_tampered_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outc, outm = self.roots(tmp)
            first = pop.materialize(canonical_root=outc, manifest_root=outm, stage="program-season",
                                    contract_sha256="c" * 64, inputs={}, upstream={}, files={"a.json": b"1\n"},
                                    manifest_extra={})
            with self.assertRaises(pop.PopulationRefused) as ctx:
                pop.load_stage_manifest(Path(first["manifest"]), stage="program-season", contract_sha256="d" * 64)
            self.assertEqual(ctx.exception.code, "CONTRACT_IDENTITY_MISMATCH")
            self.assertEqual(pop.load_stage_manifest(Path(first["manifest"]), stage="program-season",
                                                     contract_sha256="c" * 64)["identity"], first["identity"])
            (Path(first["data_dir"]) / "a.json").write_bytes(b"9\n")
            with self.assertRaises(pop.PopulationRefused) as ctx:
                pop.load_stage_manifest(Path(first["manifest"]), stage="program-season", contract_sha256="c" * 64)
            self.assertEqual(ctx.exception.code, "UPSTREAM_OUTPUT_TAMPERED")

    def test_gzip_jsonl_is_deterministic_and_carries_the_contract(self) -> None:
        one = pop.gzip_jsonl_bytes({"contract_sha256": "c"}, [{"b": 1, "a": 2}])
        self.assertEqual(one, pop.gzip_jsonl_bytes({"contract_sha256": "c"}, [{"a": 2, "b": 1}]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.jsonl.gz"
            path.write_bytes(one)
            header, rows = pop.read_gzip_jsonl(path)
            self.assertEqual((header["contract_sha256"], rows), ("c", [{"a": 2, "b": 1}]))


class IndependenceTests(unittest.TestCase):
    """AGENTS rule 9: the validator imports no producer or repository module."""

    def test_validator_imports_standard_library_only(self) -> None:
        tree = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                imported.add((node.module or "").split(".")[0])
        imported.discard("__future__")
        self.assertTrue(imported)
        self.assertEqual(sorted(imported - set(sys.stdlib_module_names)), [])
        text = VALIDATOR.read_text(encoding="utf-8")
        for forbidden in ("aggie_analytics", "data.national_di_population", "import national_di_population",
                          "ncaa_contest_reconciliation", "build_national_di_population", "importlib", "__import__",
                          "runpy", "exec("):
            self.assertNotIn(forbidden, text)


def _data_root() -> Path | None:
    value = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    return Path(value) if value and Path(value).is_dir() else None


@unittest.skipUnless(_data_root() and GATE.is_file(), "mounted: needs AGGIE_ANALYTICS_DATA_ROOT and the committed gate")
class MountedDeliveredPopulationTests(unittest.TestCase):
    """Read the delivered content-addressed outputs named by the committed gate (read-only)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = _data_root()
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.contract, cls.contract_sha = pop.load_contract(CONTRACT)
        ids = cls.gate["identities"]
        manifests = cls.data / "manifests" / pop.POPULATION / "sha256"
        cls.m1 = pop.load_stage_manifest(manifests / ids["program_season"] / "run_manifest.json",
                                         stage="program-season", contract_sha256=cls.contract_sha)
        cls.m2 = pop.load_stage_manifest(manifests / ids["contest"] / "run_manifest.json", stage="contest",
                                         contract_sha256=cls.contract_sha)
        out = pop.read_stage_outputs(cls.m1, ["program_season_cells.jsonl.gz", "observation_diffs.json"])
        cls.cells = out["program_season_cells.jsonl.gz"]
        cls.diffs = out["observation_diffs.json"]
        out2 = pop.read_stage_outputs(cls.m2, ["contests.jsonl.gz", "season_summary.json"])
        cls.contests = out2["contests.jsonl.gz"]

    def test_gate_identities_match_the_contract(self) -> None:
        self.assertEqual(self.gate["identities"]["contract_sha256"], self.contract_sha)
        self.assertEqual(self.gate["state"], "PARTIAL_TRANCHE_RECONCILED_2016_2023_SINGLE_SOURCE_2024_2025")

    def test_missouri_state_every_season_explicit(self) -> None:
        seasons = {c["season"]: c for c in self.cells if c["ncaa_org_id"] == "669"}
        self.assertEqual(sorted(seasons), list(range(2016, 2026)))
        self.assertTrue(all(c["disposition"] in pop.PROGRAM_SEASON_DISPOSITIONS for c in seasons.values()))

    def test_named_transition_seasons_use_their_own_pages(self) -> None:
        by_org = {}
        for c in self.cells:
            if c.get("division_authority") == "GRAPH_PAGE" and c["ncaa_org_id"]:
                by_org.setdefault(c["ncaa_org_id"], {})[c["season"]] = c["division_code_observed"]
        for name, season in (("Liberty", 2018), ("James Madison", 2022), ("Kennesaw St.", 2024)):
            rows = [c for c in self.cells if c["season"] == season and c.get("team_name") == name]
            self.assertEqual(len(rows), 1, name)
            self.assertEqual(rows[0]["division_authority"], "GRAPH_PAGE")
            self.assertEqual(rows[0]["graph_page"]["decode_state"], "DECODED")
            self.assertIn(rows[0]["division_code_observed"], ("11", "12"))
        # every consecutive-season code change is a TRANSITION_OBSERVED cell, and nothing else is
        expected = {(org, s) for org, codes in by_org.items() for s in codes if s - 1 in codes and codes[s] != codes[s - 1]}
        flagged = {(c["ncaa_org_id"], c["season"]) for c in self.cells if c.get("transition_observed")}
        self.assertEqual(flagged, expected)

    def test_explicit_unresolved_and_missing_cells(self) -> None:
        missing = [c for c in self.cells if c["disposition"] == "PAYLOAD_MISSING"]
        self.assertEqual(sorted(c["season"] for c in missing), [2016] * 4 + [2017] * 4)
        none_pages = [c for c in self.cells if (c.get("graph_page") or {}).get("decode_state") == "NO_CODE"]
        self.assertEqual(len(none_pages), 6)
        self.assertTrue(all(c["disposition"] == "IDENTITY_UNRESOLVED" for c in none_pages))
        adjacent = [c for c in self.cells if c["season"] == 2020 and c["e4"] and
                    any(x in ("11", "12") for e in c["e4"] for x in e["adjacent_codes"])]
        self.assertEqual(len(adjacent), 31)

    def test_decoding_proof_over_team_history(self) -> None:
        proof = self.diffs["decoding_proof_against_team_history"]
        self.assertEqual(proof["overlap_by_label"], {"FBS": 380, "FCS": 163, "D-II": 19})
        self.assertEqual(proof["agreement_by_label"], proof["overlap_by_label"])

    def test_fcs_v_fcs_every_season_and_single_source_2024_2025(self) -> None:
        for season in pop.DELIVERY_SEASONS:
            self.assertGreater(sum(1 for c in self.contests if c["season"] == season and
                                   c["classification_pair"] == "FCS-FCS"), 0, season)
        recent = [c for c in self.contests if c["season"] in (2024, 2025)]
        self.assertTrue(recent)
        self.assertTrue(all(c["reconciliation_state"] == "SINGLE_SOURCE_UNRECONCILED" and
                            c["disposition"] != "VERIFIED_PRESENT" for c in recent))

    def test_predecessors_unchanged(self) -> None:
        for rel, sha in self.contract["successor_gates"]["predecessors_byte_unchanged"].items():
            self.assertEqual(pop.sha256_file(ROOT / rel), sha, rel)


if __name__ == "__main__":
    unittest.main()
