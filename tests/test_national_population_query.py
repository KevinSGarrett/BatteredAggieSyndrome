"""BAT-710 installed read-only national population query (Cycle #38 TP38-A01-07), on a tiny synthetic database."""
from __future__ import annotations

import ast
import contextlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data import national_di_population as pop  # noqa: E402
from aggie_analytics.national_population import query  # noqa: E402

CONTRACT_SHA = "c" * 64


def contest(key, season, date, a, b, a_label, b_label, disposition, state, a_pts=21, b_pts=14):
    return {"contest_key": key, "ncaa_contest_id": key.split(":")[1], "season": season, "term": "FALL",
            "a_key": f"org:{a[0]}", "b_key": f"org:{b[0]}",
            "contest_date": date, "site": "HOME_A", "neutral_site_text": None, "contest_status": "COMPLETED",
            "competitive": True, "a_org_id": a[0], "a_team_season_id": a[1], "a_team_name": a[2],
            "a_division_label": a_label, "a_membership": "DIVISION_I", "a_points": a_pts, "b_org_id": b[0],
            "b_team_season_id": b[1], "b_team_name": b[2], "b_division_label": b_label, "b_membership": "DIVISION_I",
            "b_points": b_pts, "classification_pair": "-".join(sorted((a_label, b_label))), "mirror_observation_count": 2,
            "source": "NCAA_GRAPH", "cfbd_game_ids": [], "reconciliation_state": state, "disposition": disposition,
            "disposition_reason": None, "exposure": "X", "conflict_fields": [], "flags": [], "event_labels": []}


MOST = ("669", "a1", "Missouri St.")
UNI = ("416", "a2", "UNI")
OKST = ("521", "a3", "Oklahoma St.")
SDSU = ("2571", "a4", "South Dakota St.")


def fixture_rows():
    contests = [
        contest("ncaa:1", 2018, "2018-08-30", OKST, MOST, "FBS", "FCS", "VERIFIED_PRESENT", "RECONCILED_2016_2023", 58, 17),
        contest("ncaa:2", 2018, "2018-11-17", UNI, MOST, "FCS", "FCS", "VERIFIED_PRESENT", "RECONCILED_2016_2023", 37, 0),
        contest("ncaa:3", 2018, "2018-11-03", SDSU, MOST, "FCS", "FCS", "CONFLICT", "CONFLICT", 59, 7),
        contest("ncaa:4", 2019, "2019-09-14", UNI, SDSU, "FCS", "FCS", "VERIFIED_PRESENT", "RECONCILED_2016_2023"),
        contest("ncaa:5", 2019, "2019-10-12", MOST, UNI, "FCS", "FCS", "CANDIDATE_ONLY", "SECOND_SOURCE_ABSENT"),
        contest("ncaa:6", 2024, "2024-09-07", MOST, UNI, "FCS", "FCS", "CANDIDATE_ONLY", "SINGLE_SOURCE_UNRECONCILED"),
    ]
    orientations = [row for c in contests for row in pop.orient(dict(c, b_external=False))]
    cells = [{"cell_key": f"org:{org}:{season}", "season": season, "ncaa_org_id": org, "team_name": name,
              "ncaa_team_season_id": ts, "division_code_observed": "12", "division_label": "FCS",
              "division_authority": "GRAPH_PAGE", "disposition": "VERIFIED_PRESENT", "in_division_i_population": True,
              "expected_sources": ["E1"], "flags": [], "observations": {}}
             for season in (2018, 2019, 2024) for org, ts, name in (MOST, UNI, SDSU)]
    return cells, contests, orientations


def build_database(base: Path) -> Path:
    cells, contests, orientations = fixture_rows()
    data = pop.build_query_database(contract_sha256=CONTRACT_SHA, m1_identity="1" * 64, m2_identity="2" * 64,
                                    cells=cells, contests=contests, orientations=orientations,
                                    subsets={"FBS_ESTIMAND_SUBSET": [], "FCS_SUBSET": [c["contest_key"] for c in contests]},
                                    schedule=[])
    # A short population directory keeps temporary paths far below the Windows path limit; the identity layout
    # (<data>/canonical|manifests/<population>/sha256/<id>) is unchanged.
    result = pop.materialize(canonical_root=base / "canonical" / "p",
                             manifest_root=base / "manifests" / "p", stage="query-db",
                             contract_sha256=CONTRACT_SHA, inputs={}, upstream={"program-season": "1" * 64,
                                                                                "contest": "2" * 64},
                             files={pop.DB_FILE_NAME: data}, manifest_extra={})
    return Path(result["data_dir"]) / pop.DB_FILE_NAME


class QueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "d"
        self.db = build_database(self.base)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_main(self, *args: str) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(["--database", str(self.db), *args])
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def test_missouri_state_2018_schedule_with_fcs_opponents(self) -> None:
        code, result, _ = self.run_main("--grain", "contest", "--season", "2018", "--team", "Missouri St.",
                                        "--limit", "50", "--offset", "0")
        self.assertEqual(code, 0)
        self.assertEqual(result["total"], 3)
        self.assertEqual([r["contest_date"] for r in result["rows"]], ["2018-08-30", "2018-11-03", "2018-11-17"])
        self.assertEqual({r["classification_pair"] for r in result["rows"]}, {"FBS-FCS", "FCS-FCS"})
        self.assertEqual({r["disposition"] for r in result["rows"]}, {"VERIFIED_PRESENT", "CONFLICT"})

    def test_fcs_v_fcs_totals_by_disposition(self) -> None:
        with query.NationalPopulationDatabase(self.db) as handle:
            result = handle.query("contest", filters={"season": 2019, "classification_pair": "FCS-FCS"}, all_rows=True)
        self.assertEqual(result["total"], 2)
        self.assertEqual(sorted(r["disposition"] for r in result["rows"]), ["CANDIDATE_ONLY", "VERIFIED_PRESENT"])

    def test_paging_covers_every_grain_exactly(self) -> None:
        with query.NationalPopulationDatabase(self.db) as handle:
            for grain in ("program-season", "contest", "orientation"):
                total = handle.query(grain, limit=0)["total"]
                seen = []
                offset = 0
                while True:
                    page = handle.query(grain, limit=4, offset=offset)
                    if not page["rows"]:
                        break
                    seen.extend(page["rows"])
                    offset += 4
                everything = handle.query(grain, all_rows=True)
                self.assertEqual(len(seen), total, grain)
                self.assertEqual(everything["returned"], total)
                self.assertGreater(total, 0)
                # the pages are exactly the --all rows, in the same stable order, with no duplicate
                key = (lambda r: r["cell_key"]) if grain == "program-season" else (
                    (lambda r: r["contest_key"]) if grain == "contest" else (lambda r: (r["contest_key"], r["side"])))
                self.assertEqual([key(r) for r in seen], [key(r) for r in everything["rows"]])
                self.assertEqual(len({key(r) for r in seen}), total)

    def test_single_source_rows_are_surfaced(self) -> None:
        with query.NationalPopulationDatabase(self.db) as handle:
            rows = handle.query("contest", filters={"season": 2024}, all_rows=True)["rows"]
        self.assertEqual([r["reconciliation_state"] for r in rows], ["SINGLE_SOURCE_UNRECONCILED"])

    def test_out_of_tranche_season_is_not_yet_audited(self) -> None:
        code, result, _ = self.run_main("--grain", "contest", "--season", "2011", "--team", "Howard")
        self.assertEqual(code, 0)
        self.assertEqual((result["season_scope_state"], result["total"], result["rows"]), ("NOT_YET_AUDITED", 0, []))
        code, result, _ = self.run_main("--grain", "contest", "--season", "2026")
        self.assertEqual(result["season_scope_state"], "NOT_YET_AUDITED")

    def test_write_through_the_query_connection_is_refused(self) -> None:
        with query.NationalPopulationDatabase(self.db) as handle:
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("INSERT INTO meta VALUES ('x', 'y')")
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("DELETE FROM contest")

    def test_tampered_rows_or_manifest_are_refused(self) -> None:
        tampered = Path(self.tmp.name) / "work.sqlite"
        shutil.copyfile(self.db, tampered)
        conn = sqlite3.connect(tampered)
        conn.execute("UPDATE contest SET disposition = 'VERIFIED_PRESENT' WHERE season = 2024")
        conn.commit()
        conn.close()
        shutil.copyfile(tampered, self.db)
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.NationalPopulationDatabase(self.db)
        self.assertEqual(ctx.exception.code, "DATABASE_TAMPERED")
        manifest = query.manifest_path_for(self.db)
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["identity_document"]["outputs"][pop.DB_FILE_NAME] = pop.sha256_file(self.db)
        manifest.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.NationalPopulationDatabase(self.db)
        self.assertEqual(ctx.exception.code, "DATABASE_IDENTITY_MISMATCH")

    def test_stale_or_misplaced_identity_is_refused(self) -> None:
        code, _, err = self.run_main("--grain", "contest", "--expect-identity", "0" * 64)
        self.assertEqual(code, 2)
        self.assertIn("STALE_DATABASE_IDENTITY", err)
        moved = Path(self.tmp.name) / "elsewhere" / pop.DB_FILE_NAME
        moved.parent.mkdir()
        shutil.copyfile(self.db, moved)
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.verify_database(moved)
        self.assertEqual(ctx.exception.code, "DATABASE_LOCATION_INVALID")

    def test_negative_offset_unknown_and_abbreviated_flags_are_refused(self) -> None:
        code, _, err = self.run_main("--grain", "contest", "--offset", "-1")
        self.assertEqual(code, 2)
        self.assertIn("NEGATIVE_OFFSET", err)
        self.assertEqual(self.run_main("--grain", "contest", "--limit", "-1")[0], 2)
        self.assertEqual(self.run_main("--grain", "contest", "--unknown-flag", "1")[0], 2)
        self.assertEqual(self.run_main("--grain", "contest", "--seas", "2018")[0], 2)
        self.assertEqual(self.run_main("--grain", "program-season", "--classification-pair", "FCS-FCS")[0], 2)
        # a filter that does not apply to the grain is refused even for an out-of-tranche season
        code, _, err = self.run_main("--grain", "program-season", "--season", "2015", "--classification-pair", "FCS-FCS")
        self.assertEqual(code, 2)
        self.assertIn("FILTER_NOT_APPLICABLE", err)

    def test_console_entrypoint_is_declared(self) -> None:
        scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
        self.assertEqual(scripts["bas-national-population-query"], "aggie_analytics.national_population.query:main")
        self.assertEqual(scripts["bas-staff-query"], "aggie_analytics.cycle33.query:main")

    def test_query_module_uses_the_standard_library_only(self) -> None:
        tree = ast.parse((ROOT / "src" / "aggie_analytics" / "national_population" / "query.py").read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        names.discard("__future__")
        self.assertEqual(sorted(names - set(sys.stdlib_module_names)), [])
        self.assertIn("sqlite3", names)


if __name__ == "__main__":
    unittest.main()
