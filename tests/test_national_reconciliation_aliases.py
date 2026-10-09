"""BAT-720 (Cycle #48 — Attempt #1, TP48-A01): the explicit alias successor on tiny owned worlds.

The producer is the repository builder (tools/build_national_reconciliation_aliases.py) and the consumer is the query
module (``main`` and its verified handle). The predecessor is the accepted V1 builder's sidecar over the same world.
Evidence negatives mutate one rule at a time and must refuse for that rule's own code; database forgeries are
coordinated (bytes, counts, identity document, identity directory and manifest rewritten consistently) so each must be
refused by its semantic rule, never by a stale outer hash.

One test uses only accepted behaviour and passes on the unfixed base (BEFORE_REPRODUCTION): the accepted V1 sidecar
leaves every alias-universe participant without a documented name link and unpromoted.
"""
from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(ROOT / "src"), str(Path(__file__).resolve().parent)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from aggie_analytics.national_population import query  # noqa: E402
import national_reconciliation_aliases_fixture as fx  # noqa: E402

WINDOWS = os.name == "nt"
EXT = "\\\\?\\"
CONTRACT = ROOT / "configs" / "national_reconciliation_aliases_2024_2025_contract.json"
#: universe participants of the tiny world: (org, season) -> SUPPORTED/UNSUPPORTED
UNIVERSE = {("657", 2024): "SUPPORTED", ("657", 2025): "SUPPORTED", ("277", 2024): "SUPPORTED",
            ("277", 2025): "SUPPORTED", ("665", 2025): "SUPPORTED", ("725", 2024): "SUPPORTED",
            ("725", 2025): "UNSUPPORTED", ("655", 2024): "UNSUPPORTED", ("655", 2025): "UNSUPPORTED"}
PROMOTED_BY_ALIAS = {"ncaa:3001", "ncaa:3002", "ncaa:3003", "ncaa:3004", "ncaa:4001", "ncaa:4002"}
STILL_INCOMPLETE = {"ncaa:3005", "ncaa:4003", "ncaa:4004"}


def native(path: str | Path) -> str:
    text = os.path.abspath(str(path)) if not str(path).startswith(EXT) else str(path)
    return EXT + text if WINDOWS and not text.startswith(EXT) else text


def long_root(base: str) -> str:
    return os.path.join(base, "long " + "x" * 120, "deeper # % é ' " + "y" * 120, "tail " + "z" * 40)


class AcceptedV1Tests(unittest.TestCase):
    """Accepted behaviour only (the BEFORE_REPRODUCTION positive on the unfixed base): no successor is involved."""

    def test_the_v1_sidecar_leaves_every_alias_universe_participant_unlinked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            world = fx.build_world(work / "d")
            v1 = fx.build_v1(work / "d", world, work)
            parent = query.NationalPopulationDatabase(world["parent_db"])
            try:
                with query.ReconciliationSidecar(v1["database"], parent=parent, parent_database=world["parent_db"],
                                                 anchors=v1["anchors"]) as handle:
                    records = handle.records["parent-reconciliation"]
            finally:
                parent.close()
        unlinked = {(p["org_id"], r["season"]) for r in records for p in r["participants"].values()
                    if p["name_link"]["state"] == "NO_DOCUMENTED_NAME_LINK"}
        self.assertEqual(unlinked, set(UNIVERSE))
        self.assertEqual({r["contest_key"] for r in records if r["disposition"] ==
                          "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE"}, PROMOTED_BY_ALIAS | STILL_INCOMPLETE)
        self.assertTrue(all("alias_assertion" not in p["name_link"] for r in records for p in r["participants"].values()))


class Fixture(unittest.TestCase):
    """One world per class: parent, inputs, the V1 predecessor, the evidence bundle, the contract and a canonical
    successor build (read only for the tests)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.setup_error = None
        try:
            cls.work = Path(cls._tmp.name)
            cls.base = cls.work / "d"
            cls.world = fx.build_world(cls.base)
            cls.parent_db = cls.world["parent_db"]
            cls.v1 = fx.build_v1(cls.base, cls.world, cls.work)
            cls.ev = fx.evidence()
            cls.evidence_dir = cls.work / "ev"
            cls.pins = fx.write_evidence(cls.evidence_dir, cls.ev)
            cls.contract = cls.work / "contract.json"
            cls.anchors = fx.successor_contract(cls.contract, cls.world, cls.v1, cls.pins,
                                                cls.ev["assertions"]["universe"])
            cls.builder = fx.load_module(fx.BUILDER, "build_national_reconciliation_aliases_fixture")
            code, cls.built, err = cls.build(cls.contract, cls.base)
            if code != 0:
                raise AssertionError(f"fixture build refused: {err}")
            cls.successor = Path(cls.built["database"]["data_dir"]) / fx.DB_NAME
        except Exception as exc:  # noqa: BLE001 - each test then fails on its own identity (unfixed-base proof)
            cls.setup_error = f"{type(exc).__name__}: {exc}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    @classmethod
    def build(cls, contract: Path, out: Path, *extra: str, evidence: Path | None = None) -> tuple[int, dict, str]:
        return fx.run_builder(cls.builder, [
            "--contract", str(contract), "--predecessor-contract", str(cls.v1["contract"]),
            "--parent-database", str(cls.parent_db), "--evidence-source", str(evidence or cls.evidence_dir),
            "--output-root", str(out / "canonical" / fx.POPULATION),
            "--manifest-root", str(out / "manifests" / fx.POPULATION), *extra])

    def setUp(self) -> None:
        if self.setup_error:
            self.fail(f"fixture unavailable: {self.setup_error}")

    def open(self, successor: Path | None = None, *, anchors: dict | None = None,
             **kwargs) -> query.AliasReconciliationSuccessor:
        parent = query.NationalPopulationDatabase(self.parent_db)
        try:
            return query.AliasReconciliationSuccessor(successor or self.successor, parent=parent,
                                                      parent_database=self.parent_db, anchors=anchors or self.anchors,
                                                      **kwargs)
        finally:
            parent.close()

    def refused(self, code: str, successor: Path | None = None, **kwargs) -> None:
        with self.assertRaises(query.NationalQueryError) as ctx:
            self.open(successor, **kwargs).close()
        self.assertEqual(ctx.exception.code, code, str(ctx.exception))

    def run_main(self, *args: str, anchors: dict | None = None, v1_anchors: dict | None = None
                 ) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(query, "ALIAS_ANCHORS", anchors if anchors is not None else self.anchors), \
                mock.patch.object(query, "RECONCILIATION_ANCHORS", v1_anchors or self.v1["anchors"]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(["--database", str(self.parent_db), *args])
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def v1_records(self) -> dict[str, dict]:
        parent = query.NationalPopulationDatabase(self.parent_db)
        try:
            with query.ReconciliationSidecar(self.v1["database"], parent=parent, parent_database=self.parent_db,
                                             anchors=self.v1["anchors"]) as handle:
                return {"parent": {r["contest_key"]: r for r in handle.records["parent-reconciliation"]},
                        "provider": {r["provider_row_key"]: r for r in handle.records["provider-reconciliation"]}}
        finally:
            parent.close()

    def successor_records(self) -> dict[str, dict]:
        with self.open() as handle:
            return {"parent": {r["contest_key"]: r for r in handle.records["parent-reconciliation"]},
                    "provider": {r["provider_row_key"]: r for r in handle.records["provider-reconciliation"]}}


class DerivationTests(Fixture):
    def test_supported_aliases_link_exactly_the_proved_program_seasons(self) -> None:
        records = self.successor_records()["parent"]
        states = {}
        for record in records.values():
            for p in record["participants"].values():
                if "alias_assertion" in p["name_link"]:
                    states[(p["org_id"], record["season"])] = (p["name_link"]["state"],
                                                               p["name_link"]["alias_assertion"]["disposition"])
        expected = {key: ((query.ALIAS_NAME_LINK if d == "SUPPORTED" else "NO_DOCUMENTED_NAME_LINK"), d)
                    for key, d in UNIVERSE.items()}
        self.assertEqual(states, expected)
        self.assertEqual({k for k, r in records.items() if r["disposition"] == "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE"},
                         STILL_INCOMPLETE)
        for key in PROMOTED_BY_ALIAS:
            self.assertTrue(records[key]["relation"]["promoted"], key)
            self.assertIn(records[key]["disposition"], ("RECONCILED_FIELDS_AGREE", "RECONCILED_FIELD_CONFLICT"))
        # the season-scoped provider: Army 2024 is proved, its 2025 side never borrows that season's evidence
        army = {r["season"]: next(p for p in r["participants"].values() if p["org_id"] == "725")
                for r in records.values() if any(p["org_id"] == "725" for p in r["participants"].values())}
        self.assertEqual(army[2024]["name_link"]["alias_assertion"]["assertion_id"], "A-725-9349-2024")
        self.assertEqual(army[2025]["name_link"]["alias_assertion"],
                         {"key": "org:725|cfbdteam:9349|2025", "disposition": "UNSUPPORTED", "assertion_id": None,
                          "reason": "PROVIDER_NAME_NOT_IN_OFFICIAL_SEASON_DOCUMENT"})
        # collision controls: South Carolina and Georgia Southern keep their own V1 evidence, never an assertion
        for record in records.values():
            for p in record["participants"].values():
                if p["org_id"] in ("648", "253", "100"):
                    self.assertEqual(p["name_link"]["state"], "NAME_EQUAL")
                    self.assertNotIn("alias_assertion", p["name_link"])

    def test_records_outside_the_universe_equal_v1_and_no_comparison_or_conflict_changes(self) -> None:
        v1, now = self.v1_records(), self.successor_records()
        self.assertEqual(sorted(v1["parent"]), sorted(now["parent"]))
        self.assertEqual(sorted(v1["provider"]), sorted(now["provider"]))
        for key, record in now["parent"].items():
            before = v1["parent"][key]
            for field in ("parent", "candidates", "comparisons", "field_conflicts", "route_scope", "season",
                          "contest_date"):
                self.assertEqual(record[field], before[field], (key, field))
            touched = any("alias_assertion" in p["name_link"] for p in record["participants"].values())
            if not touched:
                self.assertEqual(query.reconciliation_line(record), query.reconciliation_line(before), key)
            else:
                self.assertEqual({k: v for k, v in (record["relation"] or {}).items() if k != "promoted"},
                                 {k: v for k, v in (before["relation"] or {}).items() if k != "promoted"})
        for key, record in now["provider"].items():
            before = v1["provider"][key]
            for field in ("provider", "raw_row_sha256", "capture", "candidates", "participants", "candidate_local_dates"):
                self.assertEqual(record[field], before[field], (key, field))

    def test_the_summary_and_the_alias_dispositions_account_for_the_universe(self) -> None:
        with self.open() as handle:
            summary = handle.summary
            rows = handle.alias_rows
        block = summary["alias_universe"]
        self.assertEqual(block["program_seasons"], 9)
        self.assertEqual(block["by_disposition"], {"SUPPORTED": 6, "UNSUPPORTED": 3})
        self.assertEqual(block["sides_linked_by_assertion"], 7)  # ncaa:4002 links both USC and Hawaii
        self.assertEqual(block["sides_unsupported"], 3)
        self.assertEqual(block["relations_promoted_with_assertion_link"], len(PROMOTED_BY_ALIAS))
        self.assertEqual(summary["name_links"].get(query.ALIAS_NAME_LINK), 7)
        self.assertEqual(summary["name_links"].get("NO_DOCUMENTED_NAME_LINK"), 3)
        self.assertEqual([(r["org_id"], r["season"], r["disposition"]) for r in rows],
                         sorted([(o, s, d) for (o, s), d in UNIVERSE.items()],
                                key=lambda t: query.alias_key(t[0], fx.TEAMS[t[0]][2], t[1])))
        self.assertTrue(all(r["documents"] for r in rows))


class EvidenceRuleTests(Fixture):
    """Each rule refuses for its own code; every other part of the evidence stays valid."""

    def verify(self, ev: dict) -> str | None:
        try:
            query.verify_alias_assertions({"assertions": ev["assertions"], "bodies": ev["bodies"],
                                           "bundle_identity": "x" * 64,
                                           "outputs": {query.ALIAS_ASSERTIONS_FILE: "y" * 64}})
        except query.NationalQueryError as exc:
            return exc.code
        return None

    def mutated(self) -> dict:
        return copy.deepcopy(self.ev)

    @staticmethod
    def assertion(ev: dict, aid: str) -> dict:
        return next(a for a in ev["assertions"]["assertions"] if a["assertion_id"] == aid)

    @staticmethod
    def witness(a: dict, role: str) -> dict:
        return next(w for w in a["witnesses"] if w["role"] == role)

    def test_the_genuine_evidence_verifies(self) -> None:
        self.assertIsNone(self.verify(self.mutated()))

    def test_institution_and_organization_record_rules(self) -> None:
        ev = self.mutated()  # the organization id of another institution (Georgia Southern's object)
        w = self.witness(self.assertion(ev, "A-657-9030-2024"), "NCAA_ORGANIZATION_ID")
        w["path"][0], w["value"] = [o for o, _ in sorted(fx.INSTITUTIONS.items(), key=lambda kv: int(kv[0]))].index("253"), "253"
        self.assertEqual(self.verify(ev), "ALIAS_INSTITUTION_UNPROVEN")
        ev = self.mutated()  # members of two different objects
        a = self.assertion(ev, "A-657-9030-2024")
        url = self.witness(a, "NCAA_OFFICIAL_ATHLETICS_URL")
        other = self.witness(self.assertion(ev, "A-665-9582-2025"), "NCAA_OFFICIAL_ATHLETICS_URL")
        url.update(path=list(other["path"]), value=other["value"])
        self.assertEqual(self.verify(ev), "ALIAS_INSTITUTION_UNPROVEN")
        ev = self.mutated()  # the institution name names another institution
        self.assertion(ev, "A-657-9030-2024")["institution"]["name"] = "University of South Carolina"
        self.assertEqual(self.verify(ev), "ALIAS_INSTITUTION_UNPROVEN")
        ev = self.mutated()  # an NCAA-looking record from a host that is not an NCAA publication
        record = next(d for d in ev["assertions"]["documents"] if d["role"] == "NCAA_ORGANIZATION_RECORD")
        record["hops"][0]["url"] = record["request_url"] = record["final_url"] = "https://ncaa.org.example.com/x"
        self.assertEqual(self.verify(ev), "ALIAS_INSTITUTION_UNPROVEN")
        ev = self.mutated()  # the NCAA short name names another program than the asserted parent name
        a = self.assertion(ev, "A-657-9030-2024")
        a["parent_name"] = "South Carolina"
        next(r for r in ev["assertions"]["universe"] if r["assertion_id"] == a["assertion_id"])["parent_name"] = \
            "South Carolina"
        self.assertNotEqual(self.witness(a, "NCAA_PROGRAM_NAME")["value"], "South Carolina")
        self.assertEqual(self.verify(ev), "ALIAS_INSTITUTION_UNPROVEN")

    def test_official_site_rules(self) -> None:
        ev = self.mutated()  # the season document of another institution's site
        a = self.assertion(ev, "A-657-9030-2024")
        a["institution"]["official_domain"] = "gseagles.com"
        self.assertEqual(self.verify(ev), "ALIAS_DOMAIN_UNPROVEN")
        ev = self.mutated()  # a redirect away from the official host family
        doc = next(d for d in ev["assertions"]["documents"] if d["request_url"].startswith("https://www.goarmy"))
        doc["hops"][0]["location"] = doc["hops"][1]["url"] = doc["final_url"] = \
            "https://goarmywestpoint.example.net/sports/football/schedule/2024"
        self.assertEqual(self.verify(ev), "ALIAS_DOMAIN_UNPROVEN")

    def test_season_rules(self) -> None:
        ev = self.mutated()  # the 2024 assertion proved with the 2025 season document
        a24, a25 = self.assertion(ev, "A-657-9030-2024"), self.assertion(ev, "A-657-9030-2025")
        for role in ("OFFICIAL_SEASON", "OFFICIAL_PROGRAM_NAME"):
            self.witness(a24, role).update(copy.deepcopy(self.witness(a25, role)))
        self.assertEqual(self.verify(ev), "ALIAS_SEASON_UNPROVEN")
        ev = self.mutated()  # no season witness at all
        a = self.assertion(ev, "A-665-9582-2025")
        a["witnesses"] = [w for w in a["witnesses"] if w["role"] != "OFFICIAL_SEASON"]
        self.assertEqual(self.verify(ev), "ALIAS_SEASON_UNPROVEN")

    def test_name_rules_never_admit_another_program_or_a_fuzzy_form(self) -> None:
        ev = self.mutated()  # the provider name of another participant (South Carolina) asserted for USC
        a = self.assertion(ev, "A-657-9030-2024")
        a["provider_name"] = "South Carolina"
        row = next(r for r in ev["assertions"]["universe"] if r["assertion_id"] == "A-657-9030-2024")
        row["provider_name"] = "South Carolina"
        self.assertEqual(self.verify(ev), "ALIAS_NAME_UNPROVEN")
        ev = self.mutated()  # an exact assertion cannot use the okina form
        self.assertion(ev, "A-277-9062-2024")["name_equivalence"] = "EXACT"
        self.assertEqual(self.verify(ev), "ALIAS_NAME_UNPROVEN")
        ev = self.mutated()  # the apostrophe rule maps forms; it never deletes the apostrophe
        a = self.assertion(ev, "A-277-9062-2025")
        body = ev["bodies"][self.witness(a, "OFFICIAL_PROGRAM_NAME")["document"]]
        replaced = body.replace(f"Hawai{fx.OKINA}i".encode("utf-8"), b"Hawaiiii", 1)
        self._replace_body(ev, self.witness(a, "OFFICIAL_PROGRAM_NAME")["document"], replaced)
        w = self.witness(a, "OFFICIAL_PROGRAM_NAME")
        w["value"], w["byte_end"] = "Hawaiiii", w["byte_start"] + len(b"Hawaiiii")
        self.assertEqual(self.verify(ev), "ALIAS_NAME_UNPROVEN")
        ev = self.mutated()  # a declared equivalence that is never used
        self.assertion(ev, "A-657-9030-2024")["name_equivalence"] = "APOSTROPHE_FORMS"
        self.assertEqual(self.verify(ev), "ALIAS_ASSERTION_INVALID")

    def test_witnesses_are_complete_delimited_fields_at_their_exact_bytes(self) -> None:
        ev = self.mutated()  # "Hawaiʻi" inside "Georgia Hawaiʻi": a substring, not a field
        a = self.assertion(ev, "A-277-9062-2024")
        w = self.witness(a, "OFFICIAL_PROGRAM_NAME")
        body = ev["bodies"][w["document"]]
        sub = fx.field_witness(w["document"], body, "OFFICIAL_PROGRAM_NAME", "Georgia ", f"Hawai{fx.OKINA}i", "</p>",
                               "paragraph")
        w.update(sub)
        self.assertEqual(self.verify(ev), "ALIAS_WITNESS_NOT_DELIMITED")
        ev = self.mutated()  # the locator moved off its field
        w = self.witness(self.assertion(ev, "A-277-9062-2024"), "OFFICIAL_SEASON")
        w["byte_start"] += 1
        self.assertEqual(self.verify(ev), "ALIAS_WITNESS_MISMATCH")
        ev = self.mutated()  # a changed raw witness, every document hash recomputed (coordinated)
        a = self.assertion(ev, "A-657-9030-2024")
        doc = self.witness(a, "OFFICIAL_PROGRAM_NAME")["document"]
        self._replace_body(ev, doc, ev["bodies"][doc].replace(b'"USC"', b'"UCS"', 1))
        self.assertEqual(self.verify(ev), "ALIAS_WITNESS_MISMATCH")
        ev = self.mutated()  # a JSON path that resolves to another member
        w = self.witness(self.assertion(ev, "A-665-9582-2025"), "OFFICIAL_PROGRAM_NAME")
        w["path"] = [2, "title"]
        self.assertEqual(self.verify(ev), "ALIAS_WITNESS_MISMATCH")

    def test_receipts_must_be_a_200_hop_chain(self) -> None:
        ev = self.mutated()
        doc = next(d for d in ev["assertions"]["documents"] if d["role"] == "OFFICIAL_SEASON_DOCUMENT")
        doc["hops"][-1]["status"] = 404
        self.assertEqual(self.verify(ev), "ALIAS_EVIDENCE_RECEIPT_INVALID")
        ev = self.mutated()
        doc = next(d for d in ev["assertions"]["documents"] if len(d["hops"]) == 2)
        doc["hops"][0]["location"] = "https://goarmywestpoint.com/elsewhere"
        self.assertEqual(self.verify(ev), "ALIAS_EVIDENCE_RECEIPT_INVALID")
        ev = self.mutated()
        doc = next(d for d in ev["assertions"]["documents"])
        doc["retrieved_at"] = "2026-10-09 20:00:00"
        self.assertEqual(self.verify(ev), "ALIAS_EVIDENCE_RECEIPT_INVALID")

    def test_omitted_extra_and_duplicate_assertions(self) -> None:
        ev = self.mutated()  # a supported row whose assertion is omitted
        ev["assertions"]["assertions"] = [a for a in ev["assertions"]["assertions"]
                                          if a["assertion_id"] != "A-665-9582-2025"]
        self.assertEqual(self.verify(ev), "ALIAS_ASSERTION_INVALID")
        ev = self.mutated()  # an assertion no universe row uses
        extra = copy.deepcopy(self.assertion(ev, "A-657-9030-2024"))
        extra["assertion_id"] = "A-EXTRA"
        ev["assertions"]["assertions"].append(extra)
        self.assertEqual(self.verify(ev), "ALIAS_ASSERTION_INVALID")
        ev = self.mutated()  # a duplicated universe row
        ev["assertions"]["universe"].append(copy.deepcopy(ev["assertions"]["universe"][0]))
        self.assertEqual(self.verify(ev), "ALIAS_ASSERTION_INVALID")
        ev = self.mutated()  # an unsupported row that claims an assertion
        row = next(r for r in ev["assertions"]["universe"] if r["disposition"] == "UNSUPPORTED")
        row["assertion_id"] = "A-657-9030-2024"
        self.assertEqual(self.verify(ev), "ALIAS_ASSERTION_INVALID")

    @staticmethod
    def _replace_body(ev: dict, old: str, body: bytes) -> None:
        """Coordinated rehash: the body, its document entry and every witness naming it move to the new digest."""
        new = hashlib.sha256(body).hexdigest()
        ev["bodies"][new] = body
        for doc in ev["assertions"]["documents"]:
            if doc["sha256"] == old:
                doc.update(sha256=new, file=new + ".gz", bytes=len(body))
        for a in ev["assertions"]["assertions"]:
            for w in a["witnesses"]:
                if w["document"] == old:
                    w["document"] = new
        for row in ev["assertions"]["universe"]:
            row["attempted_documents"] = [new if d == old else d for d in row["attempted_documents"]]


class UniverseAndBundleTests(Fixture):
    """The universe must be exactly the unlinked participants; the bundle must be exactly the pinned one."""

    def setUp(self) -> None:
        super().setUp()
        self._scratch = tempfile.TemporaryDirectory()
        self.scratch = Path(self._scratch.name)

    def tearDown(self) -> None:
        self._scratch.cleanup()

    def rebuild(self, change, name: str) -> tuple[int, str]:
        """A changed evidence bundle and a contract pinning exactly it; returns the builder's refusal."""
        ev = copy.deepcopy(self.ev)
        change(ev)
        directory = self.scratch / f"ev-{name}"
        pins = fx.write_evidence(directory, ev)
        contract = self.scratch / f"contract-{name}.json"
        fx.successor_contract(contract, self.world, self.v1, pins, sorted(ev["assertions"]["universe"],
                                                                         key=lambda r: r["key"]))
        code, _built, err = self.build(contract, self.scratch / f"out-{name}", evidence=directory)
        return code, err

    def test_an_omitted_extra_or_misnamed_universe_row_refuses(self) -> None:
        def omit(ev):
            ev["assertions"]["universe"] = [r for r in ev["assertions"]["universe"]
                                            if r["key"] != "org:655|cfbdteam:9545|2025"]
        code, err = self.rebuild(omit, "omit")
        self.assertEqual(code, 2)
        self.assertIn("ALIAS_UNIVERSE_MISMATCH", err)

        def extra(ev):  # South Carolina is never unlinked; adding it (with "USC") is no universe member
            ev["assertions"]["universe"].append({
                "key": query.alias_key("648", "9579", 2024), "org_id": "648", "provider_team_id": "9579",
                "season": 2024, "parent_name": "South Carolina", "provider_name": "USC", "disposition": "UNSUPPORTED",
                "assertion_id": None, "reason": "NOT_A_GAP", "attempted_documents": []})
        code, err = self.rebuild(extra, "extra")
        self.assertEqual(code, 2)
        self.assertIn("ALIAS_UNIVERSE_MISMATCH", err)

        def borrowed(ev):  # a 2024 row for the provider observed only in 2025
            ev["assertions"]["universe"].append({
                "key": query.alias_key("665", "9582", 2024), "org_id": "665", "provider_team_id": "9582",
                "season": 2024, "parent_name": "Southern U.", "provider_name": "Southern", "disposition": "UNSUPPORTED",
                "assertion_id": None, "reason": "NO_2024_OBSERVATION", "attempted_documents": []})
        code, err = self.rebuild(borrowed, "borrowed")
        self.assertEqual(code, 2)
        self.assertIn("ALIAS_UNIVERSE_MISMATCH", err)

    def test_the_contract_must_declare_the_verified_universe_and_pin_the_bundle(self) -> None:
        bad = json.loads(self.contract.read_text(encoding="utf-8"))
        bad["alias_universe"] = bad["alias_universe"][:-1]
        (self.scratch / "bad-universe.json").write_text(json.dumps(bad), encoding="utf-8")
        code, _b, err = self.build(self.scratch / "bad-universe.json", self.scratch / "out-u")
        self.assertEqual(code, 2)
        self.assertIn("ALIAS_UNIVERSE_NOT_DECLARED", err)
        other = json.loads(self.contract.read_text(encoding="utf-8"))
        other["alias_evidence"] = {"bundle_identity": "a" * 64, "assertions_sha256": self.pins["assertions_sha256"]}
        other["content_scope"] = query.alias_scope({**self.anchors, "alias_evidence": other["alias_evidence"]})
        (self.scratch / "other-pin.json").write_text(json.dumps(other), encoding="utf-8")
        code, _b, err = self.build(self.scratch / "other-pin.json", self.scratch / "out-p")
        self.assertEqual(code, 2)
        self.assertIn("EVIDENCE_NOT_PINNED", err)

    def bundle_copy(self, name: str) -> Path:
        """The successor population root copied (its evidence bundle, content and database) with its manifests."""
        out = self.scratch / name
        for kind in ("canonical", "manifests"):
            shutil.copytree(self.base / kind / fx.POPULATION, out / kind / fx.POPULATION)
        return out

    def test_bundle_bytes_listing_and_pins(self) -> None:
        bundle_id = self.pins["bundle_identity"]
        out = self.bundle_copy("bytes")
        body = next(p for p in (out / "canonical" / fx.POPULATION / "sha256" / bundle_id).iterdir() if p.suffix == ".gz")
        data = gzip.decompress(body.read_bytes())
        body.write_bytes(gzip.compress(data.replace(b"Football", b"Footbalx", 1), mtime=0))
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_alias_evidence(out / "canonical" / fx.POPULATION, self.anchors)
        self.assertEqual(ctx.exception.code, "ALIAS_EVIDENCE_BYTES_MISMATCH")
        out = self.bundle_copy("listing")
        (out / "canonical" / fx.POPULATION / "sha256" / bundle_id / "extra.gz").write_bytes(b"x")
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_alias_evidence(out / "canonical" / fx.POPULATION, self.anchors)
        self.assertEqual(ctx.exception.code, "ALIAS_EVIDENCE_LISTING_MISMATCH")
        out = self.bundle_copy("manifest")
        manifest = out / "manifests" / fx.POPULATION / "sha256" / bundle_id / "run_manifest.json"
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        doc["identity_document"]["assertions_sha256"] = "b" * 64
        manifest.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_alias_evidence(out / "canonical" / fx.POPULATION, self.anchors)
        self.assertEqual(ctx.exception.code, "ALIAS_EVIDENCE_IDENTITY_MISMATCH")
        for pins, code in (({"bundle_identity": "not-hex", "assertions_sha256": "c" * 64}, "ALIAS_EVIDENCE_PIN_INVALID"),
                           ({"bundle_identity": "d" * 64, "assertions_sha256": self.pins["assertions_sha256"]},
                            "ALIAS_EVIDENCE_MISSING")):
            with self.assertRaises(query.NationalQueryError) as ctx:
                query.load_alias_evidence(self.base / "canonical" / fx.POPULATION, {**self.anchors, "alias_evidence": pins})
            self.assertEqual(ctx.exception.code, code)


class ForgeryTests(Fixture):
    """Coordinated successor forgeries: bytes, counts, identity document, identity directory and manifest consistent;
    the evidence bundle travels with each copy, so only the forged member can explain the refusal."""

    def setUp(self) -> None:
        super().setUp()
        self._work = tempfile.TemporaryDirectory()
        self.forge_root = Path(self._work.name)
        self.count = 0

    def tearDown(self) -> None:
        self._work.cleanup()

    def forge(self, statements: list[tuple[str, tuple]], document: dict | None = None) -> Path:
        self.count += 1
        root = self.forge_root / f"f{self.count}"
        bundle = self.pins["bundle_identity"]
        for kind in ("canonical", "manifests"):
            shutil.copytree(self.base / kind / fx.POPULATION / "sha256" / bundle,
                            root / kind / fx.POPULATION / "sha256" / bundle)
        work = root / "work.sqlite"
        shutil.copyfile(self.successor, work)
        conn = sqlite3.connect(work)
        for sql, params in statements:
            changed = conn.execute(sql, params).rowcount
            if not sql.lstrip().upper().startswith("CREATE"):
                self.assertGreater(changed, 0, sql)
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in query.ALIAS_TABLES}
        conn.close()
        manifest = json.loads((self.base / "manifests" / fx.POPULATION / "sha256" / self.successor.parent.name /
                               "run_manifest.json").read_text(encoding="utf-8"))
        doc = copy.deepcopy(manifest["identity_document"])
        doc["outputs"] = {fx.DB_NAME: fx.sha(work)}
        doc["table_counts"] = counts
        doc.update(document or {})
        identity = hashlib.sha256(query.canonical_json_bytes(doc)).hexdigest()
        target = root / "canonical" / fx.POPULATION / "sha256" / identity / fx.DB_NAME
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = root / "manifests" / fx.POPULATION / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps({"identity": identity, "identity_document": doc, "provenance": {}}), encoding="utf-8")
        return target

    def record_update(self, table: str, key_column: str, key: str, mutate) -> tuple[str, tuple]:
        conn = sqlite3.connect(self.successor.as_uri() + "?mode=ro", uri=True)
        text = conn.execute(f"SELECT record FROM {table} WHERE {key_column} = ?", (key,)).fetchone()[0]
        conn.close()
        record = json.loads(text)
        mutate(record)
        return f"UPDATE {table} SET record = ? WHERE {key_column} = ?", (query.reconciliation_line(record), key)

    def test_a_forged_alias_link_promotion_or_disposition_refuses(self) -> None:
        def link_unsupported(r):  # relabel the unsupported SE Louisiana side's name link only
            for p in r["participants"].values():
                if p["org_id"] == "655":
                    p["name_link"]["state"] = query.ALIAS_NAME_LINK
                    p["verified"] = True
        self.refused("RECONCILIATION_PARTICIPANT_MISMATCH", self.forge([
            self.record_update("parent_reconciliation", "contest_key", "ncaa:3005", link_unsupported)]))

        def promote(r):  # the whole coordinated promotion: link, relation, disposition
            link_unsupported(r)
            r["relation"]["promoted"] = True
            r["disposition"], r["disposition_reason"] = "RECONCILED_FIELDS_AGREE", None
        self.refused("RECONCILIATION_RELATION_MISMATCH", self.forge([
            self.record_update("parent_reconciliation", "contest_key", "ncaa:3005", promote)]))

        def mirror(r):
            r["relation"]["promoted"] = True
            r["disposition"], r["disposition_reason"] = "RECONCILED_FIELDS_AGREE", None
        self.refused("RECONCILIATION_RELATION_MISMATCH", self.forge([
            self.record_update("provider_reconciliation", "contest_key", "ncaa:3005", mirror)]))

        def support(r):
            r["disposition"], r["reason"] = "SUPPORTED", None
        self.refused("RECONCILIATION_DISPOSITION_MISMATCH", self.forge([
            self.record_update("alias_disposition", "alias_key", "org:655|cfbdteam:9545|2024", support)]))
        self.refused("RECONCILIATION_ALIAS_ROW_MISSING", self.forge([
            ("DELETE FROM alias_disposition WHERE alias_key = ?", ("org:725|cfbdteam:9349|2025",))]))

    def test_rehashed_claims_and_identity_documents_refuse(self) -> None:
        def meta(key, value):
            return "UPDATE meta SET value = ? WHERE key = ?", (json.dumps(value, sort_keys=True, separators=(",", ":")),
                                                               key)
        self.refused("ALIAS_EVIDENCE_PIN_MISMATCH", self.forge([meta("alias_evidence", {
            "bundle_identity": "e" * 64, "assertions_sha256": self.pins["assertions_sha256"]})]))
        labels = dict(query.ALIAS_LABELS, pit_eligibility="PIT_ELIGIBLE")
        self.refused("RECONCILIATION_PIT_CLAIM_INVALID", self.forge([meta("labels", labels)]))
        counts = json.loads((self.base / "manifests" / fx.POPULATION / "sha256" / self.successor.parent.name /
                             "run_manifest.json").read_text(encoding="utf-8"))["identity_document"]["table_counts"]
        self.refused("RECONCILIATION_IDENTITY_DOCUMENT_MISMATCH",
                     self.forge([], {"table_counts": {k: float(v) for k, v in counts.items()}}))
        self.refused("RECONCILIATION_SCHEMA_UNSUPPORTED", self.forge([("CREATE TABLE extra (x TEXT)", ())]))

    def test_a_successor_without_its_evidence_or_with_another_pin_refuses(self) -> None:
        copy_root = self.forge_root / "no-evidence"
        identity = self.successor.parent.name
        for kind, name in (("canonical", fx.DB_NAME), ("manifests", "run_manifest.json")):
            target = copy_root / kind / fx.POPULATION / "sha256" / identity / name
            target.parent.mkdir(parents=True)
            shutil.copyfile(self.base / kind / fx.POPULATION / "sha256" / identity / name, target)
        self.refused("ALIAS_EVIDENCE_MISSING", copy_root / "canonical" / fx.POPULATION / "sha256" / identity / fx.DB_NAME)
        other = dict(self.anchors, alias_evidence={"bundle_identity": "f" * 64,
                                                   "assertions_sha256": self.pins["assertions_sha256"]})
        self.refused("ALIAS_EVIDENCE_PIN_MISMATCH", anchors=other)


class ConsumerTests(Fixture):
    def keys(self, *argv: str) -> list[str]:
        code, result, err = self.run_main("--reconciliation", str(self.successor), *argv)
        self.assertEqual(code, 0, err)
        field = "contest_key" if "parent-reconciliation" in argv else "provider_row_key"
        return [r[field] for r in result["rows"]]

    def test_both_grains_serve_verified_records_with_exact_paging_and_the_universe(self) -> None:
        for grain, total in (("parent-reconciliation", 10), ("provider-reconciliation", 10)):
            code, everything, err = self.run_main("--grain", grain, "--reconciliation", str(self.successor), "--all")
            self.assertEqual(code, 0, err)
            self.assertEqual(everything["total"], total)
            self.assertEqual(everything["reconciliation_identity"], self.successor.parent.name)
            self.assertEqual(everything["alias_authority"], query.ALIAS_LABELS["alias_authority"])
            self.assertEqual(everything["pit_eligibility"], "PIT_ELIGIBILITY_NOT_ESTABLISHED")
            self.assertEqual(len(everything["alias_universe"]), 9)
            self.assertEqual(everything["predecessor"]["database_identity"], self.v1["built"]["database_identity"])
            self.assertTrue(everything["verification"]["alias_evidence_verified"])
            seen, offset = [], 0
            while True:
                code, page, _ = self.run_main("--grain", grain, "--reconciliation", str(self.successor), "--limit", "3",
                                              "--offset", str(offset))
                seen.extend(page["rows"])
                if page["next_offset"] is None:
                    break
                offset = page["next_offset"]
            self.assertEqual(seen, everything["rows"])

    def test_names_ids_and_seasons_select_the_same_records_on_both_sources(self) -> None:
        for grain in query.RECONCILIATION_GRAINS:
            by_org = self.keys("--grain", grain, "--team", "org:657", "--all")
            self.assertEqual(len(by_org), 3)
            for team in ("Southern California", "USC", "usc", "657", "cfbdteam:9030"):
                with self.subTest(grain=grain, team=team):
                    self.assertEqual(self.keys("--grain", grain, "--team", team, "--all"), by_org)
            self.assertEqual(self.keys("--grain", grain, "--team", "Hawai'i", "--season", "2025", "--all"),
                             self.keys("--grain", grain, "--team", "org:277", "--season", "2025", "--all"))
        # Southern is a provider name of 2025 only; Georgia Southern is its own program
        self.assertEqual(self.keys("--grain", "parent-reconciliation", "--team", "Southern", "--all"), ["ncaa:4001"])
        self.assertEqual(self.keys("--grain", "parent-reconciliation", "--team", "Southern", "--season", "2024",
                                   "--all"), [])
        self.assertEqual(sorted(self.keys("--grain", "parent-reconciliation", "--team", "Georgia Southern", "--all")),
                         ["ncaa:3004", "ncaa:3006", "ncaa:4001"])
        self.assertEqual(self.keys("--grain", "parent-reconciliation", "--disposition",
                                   "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE", "--all"), sorted(STILL_INCOMPLETE))

    def test_v1_and_defaults_are_unchanged_and_refusals_hold(self) -> None:
        code, v1, err = self.run_main("--reconciliation", str(self.v1["database"]), "--grain", "parent-reconciliation",
                                      "--all")
        self.assertEqual(code, 0, err)
        self.assertNotIn("alias_universe", v1)
        self.assertEqual(v1["filtered_by_disposition"]["CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE"], 9)
        for argv, refusal in (
                (("--grain", "parent-reconciliation", "--require-pit"), "PIT_ELIGIBILITY_NOT_ESTABLISHED"),
                (("--grain", "contest"), "RECONCILIATION_GRAIN_REQUIRED"),
                (("--grain", "parent-reconciliation", "--expect-reconciliation-identity", "0" * 64),
                 "STALE_RECONCILIATION_IDENTITY"),
                (("--grain", "parent-reconciliation", "--division", "FBS"), "FILTER_NOT_APPLICABLE")):
            with self.subTest(refusal=refusal):
                code, _r, err = self.run_main("--reconciliation", str(self.successor), *argv)
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(err.strip().splitlines()[-1])["refused"], refusal)
        out, err = io.StringIO(), io.StringIO()  # an unpinned reader serves no successor at all
        with mock.patch.object(query, "ALIAS_ANCHORS", None), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            code = query.main(["--database", str(self.parent_db), "--reconciliation", str(self.successor), "--grain",
                               "parent-reconciliation"])
        self.assertEqual((code, out.getvalue()), (2, ""))
        self.assertEqual(json.loads(err.getvalue().strip().splitlines()[-1])["refused"], "ALIAS_SUCCESSOR_NOT_PINNED")

    def test_the_successor_connection_is_read_only(self) -> None:
        with self.open() as handle:
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("DELETE FROM alias_disposition")

    def test_short_and_long_extended_locations_serve_the_same_rows(self) -> None:
        if not WINDOWS:
            self.skipTest("extended-length spellings are Windows locations")
        holder = tempfile.TemporaryDirectory()
        tmp = os.path.realpath(holder.name)
        try:
            far_root = long_root(tmp)
            identities = (self.successor.parent.name, self.pins["bundle_identity"])
            for kind in ("canonical", "manifests"):
                for identity in identities:
                    source = self.base / kind / fx.POPULATION / "sha256" / identity
                    for name in os.listdir(source):
                        target = native(os.path.join(far_root, kind, fx.POPULATION, "sha256", identity, name))
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        shutil.copyfile(source / name, target)
            far = native(os.path.join(far_root, "canonical", fx.POPULATION, "sha256", identities[0], fx.DB_NAME))
            self.assertGreater(len(far), 300)
            with self.open() as near, self.open(Path(far)) as distant:
                self.assertEqual(near.records, distant.records)
                self.assertEqual(near.alias_rows, distant.alias_rows)
            code, result, err = self.run_main("--reconciliation", far, "--grain", "parent-reconciliation", "--all")
            self.assertEqual(code, 0, err)
            self.assertEqual(result["content_identity"], self.built["content_identity"])
        finally:
            shutil.rmtree(native(tmp))
            holder.cleanup()


class DeterminismTests(Fixture):
    def test_orders_chunks_and_a_resumed_build_give_identical_bytes(self) -> None:
        reference = (self.built["content_identity"], self.built["database_sha256"])
        work = self.work
        variants = [("reverse", ["--input-order", "reverse"]), ("shuffle", ["--input-order", "shuffle:48"]),
                    ("chunk2", ["--chunk-size", "2", "--checkpoint-dir", str(work / "ck2")]),
                    ("chunk7", ["--chunk-size", "7", "--checkpoint-dir", str(work / "ck7")])]
        for name, extra in variants:
            with self.subTest(variant=name):
                code, built, err = self.build(self.contract, work / f"v-{name}", *extra)
                self.assertEqual(code, 0, err)
                self.assertEqual((built["content_identity"], built["database_sha256"]), reference)
        checkpoint = work / "ck3"
        code, first, _ = self.build(self.contract, work / "v-resume", "--chunk-size", "3", "--checkpoint-dir",
                                    str(checkpoint), "--stop-after-chunks", "3")
        self.assertEqual((code, first["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"))
        code, resumed, err = self.build(self.contract, work / "v-resume", "--chunk-size", "3", "--checkpoint-dir",
                                        str(checkpoint), "--resume")
        self.assertEqual(code, 0, err)
        self.assertEqual((resumed["content_identity"], resumed["database_sha256"]), reference)

    def test_materialization_is_create_only(self) -> None:
        code, again, err = self.build(self.contract, self.base)
        self.assertEqual((code, again.get("state"), again.get("database", {}).get("state"),
                          again.get("evidence", {}).get("state")),
                         (0, "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL"), err)
        collide = self.work / "collide"
        shutil.copytree(self.base / "canonical" / fx.POPULATION, collide / "canonical" / fx.POPULATION)
        target = collide / "canonical" / fx.POPULATION / "sha256" / self.built["content_identity"] / "summary.json"
        target.write_bytes(target.read_bytes() + b" ")
        code, _b, err = self.build(self.contract, collide)
        self.assertEqual(code, 2)
        self.assertIn("REFUSED_IMMUTABLE_COLLISION", err)

    def test_a_contract_with_other_rules_or_another_predecessor_is_refused(self) -> None:
        for name, change in (("parameters", lambda c: c["parameters"].update(alias_ncaa_hosts=["example.org"])),
                             ("predecessor", lambda c: c["predecessor"].update(contract_sha256="9" * 64)),
                             ("labels", lambda c: c["labels"].update(alias_authority="PIT"))):
            with self.subTest(change=name):
                bad = json.loads(self.contract.read_text(encoding="utf-8"))
                change(bad)
                path = self.work / f"bad-{name}.json"
                path.write_text(json.dumps(bad), encoding="utf-8")
                code, _b, err = self.build(path, self.work / f"v-bad-{name}")
                self.assertEqual(code, 2)
                self.assertIn("CONTRACT_INVALID", err)


class ContractPinTests(unittest.TestCase):
    """The reader pins the committed successor contract once it exists; until then no successor is served."""

    def test_the_reader_pins_the_committed_successor_contract_or_nothing(self) -> None:
        if not CONTRACT.is_file():
            self.assertIsNone(query.ALIAS_ANCHORS)
            return
        raw = CONTRACT.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        anchors = query.ALIAS_ANCHORS
        self.assertEqual(anchors["contract_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(anchors["contract_id"], contract["contract_id"])
        self.assertEqual((anchors["parent"], anchors["inputs"]), (contract["parent"], contract["inputs"]))
        self.assertEqual(anchors["alias_evidence"], contract["alias_evidence"])
        self.assertEqual(anchors["predecessor"], contract["predecessor"])
        self.assertEqual((anchors["parent"], anchors["inputs"]),
                         (query.RECONCILIATION_ANCHORS["parent"], query.RECONCILIATION_ANCHORS["inputs"]))
        self.assertEqual(anchors["predecessor"]["contract_sha256"], query.RECONCILIATION_ANCHORS["contract_sha256"])


if __name__ == "__main__":
    unittest.main()
