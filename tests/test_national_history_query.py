"""BAT-711 installed read-only national history-prefix query (Cycle #39 TP39-A01), on the synthetic fixture build."""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_history_fixture as fx  # noqa: E402

from aggie_analytics.national_history import query  # noqa: E402

LABELS = {"observation_authority": "RETROSPECTIVE_OBSERVATION_ONLY",
          "pit_eligibility": "PIT_ELIGIBILITY_NOT_ESTABLISHED",
          "temporal_basis": "CALENDAR_DATE_ORDER_ONLY_NOT_PUBLICATION_TIME"}


class QueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        parent = fx.build_parent(cls.base / "parent")
        contract = fx.write_contract(cls.base / "contract.json", fx.contract_for(parent))
        code, cls.result, err = fx.run_build(contract, parent, cls.base / "out")
        assert code == 0, err
        cls.db = Path(cls.result["database"]["data_dir"]) / query.DB_FILE_NAME
        cls.data_dir = Path(cls.result["content"]["data_dir"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def run_main(self, *args: str, database: Path | None = None) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(["--database", str(database or self.db), *args])
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def payload_lines(self, name: str) -> list[dict]:
        return [json.loads(line) for line in (self.data_dir / name).read_text(encoding="utf-8").splitlines()]

    def test_team_history_query_returns_exact_payload_records(self) -> None:
        code, result, _ = self.run_main("--grain", "history", "--season", "2018", "--team", "org:1", "--all")
        self.assertEqual(code, 0)
        self.assertEqual([(r["target_contest_key"], r["view"]) for r in result["rows"]],
                         [("ncaa:103", "A"), ("ncaa:105", "B"), ("ncaa:111", "A")])
        expected = {(r["target_contest_key"], r["view"]): r for r in self.payload_lines("history.jsonl")}
        self.assertEqual(result["rows"], [expected[(r["target_contest_key"], r["view"])] for r in result["rows"]])
        self.assertEqual({k: result[k] for k in LABELS}, LABELS)
        self.assertEqual(result["season_scope_state"], "RETROSPECTIVE_2016_2023")
        self.assertEqual(result["rows"][2]["team_history"]["win_rate"], {"numerator": 3, "denominator": 3})

    def test_contest_query_and_bare_identifiers(self) -> None:
        code, result, _ = self.run_main("--grain", "history", "--contest", "111", "--all")
        self.assertEqual((code, [r["view"] for r in result["rows"]]), (0, ["A", "B"]))
        code, result, _ = self.run_main("--grain", "targets", "--team", "5", "--season", "2018", "--all")
        self.assertEqual([r["contest_key"] for r in result["rows"]],
                         ["ncaa:102", "ncaa:104", "ncaa:107", "ncaa:111", "ncaa:114"])
        code, result, _ = self.run_main("--grain", "exclusions", "--contest", "ncaa:108")
        self.assertEqual(result["rows"][0]["target_exclusion_reasons"][0], "DISPOSITION_NOT_VERIFIED_PRESENT")

    def test_paging_of_every_grain_equals_the_immutable_payload_keys(self) -> None:
        files = {"targets": "targets.jsonl", "history": "history.jsonl", "exclusions": "exclusions.jsonl"}
        with query.NationalHistoryDatabase(self.db) as handle:
            for grain, name in files.items():
                key = (lambda r: (r["target_contest_key"], r["view"])) if grain == "history" else \
                    (lambda r: r["contest_key"])
                payload = [key(r) for r in self.payload_lines(name)]
                seen, offset = [], 0
                while True:
                    page = handle.query(grain, limit=5, offset=offset)
                    if not page["rows"]:
                        break
                    self.assertEqual(page["total"], len(payload))
                    seen.extend(key(r) for r in page["rows"])
                    offset += 5
                self.assertEqual(seen, payload, grain)
                self.assertEqual(len(set(seen)), len(seen))
                self.assertEqual([key(r) for r in handle.query(grain, all_rows=True)["rows"]], payload)
                self.assertEqual(handle.query(grain, limit=0)["returned"], 0)

    def test_out_of_range_seasons_are_not_yet_audited(self) -> None:
        for season in ("2015", "2024", "2025", "2026"):
            for grain in ("targets", "history", "exclusions"):
                code, result, _ = self.run_main("--grain", grain, "--season", season)
                self.assertEqual((code, result["season_scope_state"], result["total"], result["rows"]),
                                 (0, "NOT_YET_AUDITED", 0, []))

    def test_require_pit_is_always_refused(self) -> None:
        code, result, err = self.run_main("--grain", "history", "--require-pit")
        self.assertEqual((code, result), (2, None))
        self.assertIn("PIT_ELIGIBILITY_NOT_ESTABLISHED", err)

    def test_target_labels_are_never_served(self) -> None:
        self.assertEqual(sorted(query.GRAINS), ["exclusions", "history", "targets"])
        self.assertEqual(self.run_main("--grain", "labels")[0], 2)
        with query.NationalHistoryDatabase(self.db) as handle:
            for grain in query.GRAINS:
                for row in handle.query(grain, all_rows=True)["rows"]:
                    self.assertFalse({"a_points", "b_points", "a_result", "b_result", "a_margin"} & set(row))
                    self.assertEqual({k: row[k] for k in LABELS}, LABELS)

    def test_bad_filters_paging_and_flags_are_refused(self) -> None:
        for args, code_text in ((["--team", "Alpha"], "TEAM_KEY_INVALID"), (["--team", "org:x"], "TEAM_KEY_INVALID"),
                                (["--contest", "../etc"], "CONTEST_KEY_INVALID"),
                                (["--offset", "-1"], "NEGATIVE_OFFSET"), (["--limit", "-5"], "NEGATIVE_LIMIT")):
            code, _r, err = self.run_main("--grain", "history", *args)
            self.assertEqual(code, 2, args)
            self.assertIn(code_text, err)
        self.assertEqual(self.run_main("--grain", "history", "--season", "twenty")[0], 2)
        self.assertEqual(self.run_main("--grain", "history", "--unknown-flag", "1")[0], 2)
        self.assertEqual(self.run_main("--grain", "history", "--seas", "2018")[0], 2)

    def test_stale_identity_is_refused(self) -> None:
        code, _r, err = self.run_main("--grain", "targets", "--expect-identity", "0" * 64)
        self.assertEqual(code, 2)
        self.assertIn("STALE_DATABASE_IDENTITY", err)
        code, result, _ = self.run_main("--grain", "targets", "--expect-identity", self.result["database_identity"])
        self.assertEqual((code, result["database_identity"]), (0, self.result["database_identity"]))

    def test_write_through_the_query_connection_is_refused(self) -> None:
        with query.NationalHistoryDatabase(self.db) as handle:
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("DELETE FROM history")
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("INSERT INTO meta VALUES ('x', 'y')")

    def copy_tree(self, name: str) -> tuple[Path, Path]:
        root = self.base / name
        shutil.copytree(self.base / "out", root)
        db = Path(str(self.db).replace(str(self.base / "out"), str(root)))
        return root, db

    def test_mutated_database_or_manifest_is_refused(self) -> None:
        _root, db = self.copy_tree("t1")
        conn = sqlite3.connect(db)
        conn.execute("UPDATE history SET record = replace(record, '\"wins\":3', '\"wins\":4')")
        conn.commit()
        conn.close()
        code, _r, err = self.run_main("--grain", "history", database=db)
        self.assertEqual(code, 2)
        self.assertIn("DATABASE_TAMPERED", err)
        manifest = query.manifest_path_for(db)
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["identity_document"]["outputs"][query.DB_FILE_NAME] = hashlib.sha256(db.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(document), encoding="utf-8")
        code, _r, err = self.run_main("--grain", "history", database=db)
        self.assertIn("DATABASE_IDENTITY_MISMATCH", err)

    def rehoused(self, name: str, mutate_meta: dict[str, str] | None = None, counts: dict | None = None) -> Path:
        """A copy whose manifest identity is recomputed consistently and that sits in its own identity directory."""
        _root, db = self.copy_tree(name)
        if mutate_meta:
            conn = sqlite3.connect(db)
            for key, value in mutate_meta.items():
                conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
            conn.commit()
            conn.close()
        manifest = query.manifest_path_for(db)
        document = json.loads(manifest.read_text(encoding="utf-8"))
        doc = document["identity_document"]
        doc["outputs"][query.DB_FILE_NAME] = hashlib.sha256(db.read_bytes()).hexdigest()
        if counts:
            doc["table_counts"].update(counts)
        identity = hashlib.sha256(query.canonical_json_bytes(doc)).hexdigest()
        document["identity"] = identity
        new_db = db.parent.parent / identity / query.DB_FILE_NAME
        new_db.parent.mkdir()
        shutil.copyfile(db, new_db)
        new_manifest = query.manifest_path_for(new_db)
        new_manifest.parent.mkdir()
        new_manifest.write_text(json.dumps(document), encoding="utf-8")
        return new_db

    def test_unknown_schema_or_count_disagreement_is_refused_even_when_rehashed(self) -> None:
        db = self.rehoused("t2", mutate_meta={"schema_version": "BAS-NATIONAL-HISTORY-PREFIX-DB-9"})
        code, _r, err = self.run_main("--grain", "targets", database=db)
        self.assertEqual(code, 2)
        self.assertIn("DATABASE_SCHEMA_UNSUPPORTED", err)
        db = self.rehoused("t3", counts={"history": 1})
        code, _r, err = self.run_main("--grain", "targets", database=db)
        self.assertIn("DATABASE_COUNT_MISMATCH", err)
        db = self.rehoused("t4", mutate_meta={"row_labels": json.dumps(dict(LABELS, pit_eligibility="PIT_ELIGIBLE"),
                                                                        sort_keys=True)})
        code, _r, err = self.run_main("--grain", "targets", database=db)
        self.assertIn("DATABASE_SCHEMA_UNSUPPORTED", err)

    def test_misplaced_database_is_refused(self) -> None:
        moved = self.base / "elsewhere" / query.DB_FILE_NAME
        moved.parent.mkdir()
        shutil.copyfile(self.db, moved)
        code, _r, err = self.run_main("--grain", "targets", database=moved)
        self.assertEqual(code, 2)
        self.assertIn("DATABASE_LOCATION_INVALID", err)

    def test_console_entrypoints_are_declared_and_preserved(self) -> None:
        scripts = tomllib.loads((fx.ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
        self.assertEqual(scripts["bas-national-history-query"], "aggie_analytics.national_history.query:main")
        self.assertEqual(scripts["bas-national-population-query"], "aggie_analytics.national_population.query:main")
        self.assertEqual(scripts["bas-staff-query"], "aggie_analytics.cycle33.query:main")

    def test_query_module_uses_the_standard_library_only(self) -> None:
        tree = ast.parse((fx.ROOT / "src" / "aggie_analytics" / "national_history" / "query.py").read_text(encoding="utf-8"))
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
