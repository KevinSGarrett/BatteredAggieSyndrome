"""BAT-728 (Cycle #57 TP57-A01): private research API cases for the existing hosted product test profile.

Not a test module (no ``test`` prefix): tests/test_w22_product_serving.py imports these classes, so they run in the
hosted product job (``python -m unittest tests.test_w22_product_serving tests.test_w23_operations``) without a workflow
change. Requests go through the raw ASGI interface (the hosted product runtime installs only requirements/product.lock,
which has no HTTP client). Every world is real: a tiny national world built by the accepted builders
(tests/retrospective_reference_fixture.py) and verified by the accepted reader; the profile is registered with that
world's own pins through the operator's Python API. When AGGIE_ANALYTICS_DATA_ROOT names the private lake, the genuine
accepted reference is also served through a JSON operator configuration bound to the packaged accepted pins.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (str(HERE), str(ROOT / "src"), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from aggie_analytics.product import research  # noqa: E402

PID = "fixture-world"
BASE_ROUTES = ["/", "/api/docs", "/api/v1/games", "/api/v1/games/{game_id}/forecast",
               "/api/v1/games/{game_id}/snapshots", "/api/v1/games/{game_id}/snapshots/{snapshot_id}/lineage",
               "/api/v1/openapi.json", "/docs/oauth2-redirect", "/health", "/static"]


def asgi_get(app, path, query="", *, offline=False):
    """One GET through the raw ASGI interface: (status, headers, body bytes). ``offline`` forbids every socket
    connection and DNS lookup while the request runs (patched inside the running event loop, which itself needs a
    local socket pair on Windows)."""
    async def run():
        if offline:
            with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("unexpected network")), \
                    mock.patch.object(socket, "getaddrinfo", side_effect=AssertionError("unexpected DNS")):
                return await request()
        return await request()

    async def request():
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)
        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1",
                 "method": "GET", "scheme": "http", "path": path, "raw_path": path.encode("utf-8"),
                 "query_string": query.encode("utf-8"), "root_path": "", "headers": [(b"host", b"testserver")],
                 "client": ("127.0.0.1", 1234), "server": ("127.0.0.1", 80)}
        await asyncio.wait_for(app(scope, receive, send), 120)
        start = next(m for m in messages if m["type"] == "http.response.start")
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        return start["status"], {k.decode(): v.decode() for k, v in start["headers"]}, body
    return asyncio.run(run())


def get_json(app, path, query=""):
    status, headers, body = asgi_get(app, path, query)
    return status, headers, json.loads(body.decode("utf-8"))


def require_product():
    try:
        import fastapi  # noqa: F401 - optional product environment
    except ImportError as exc:
        raise unittest.SkipTest("FastAPI product extra is not installed") from exc


def build_fixture(base: Path):
    """A tiny real world, its reader-verified reference and its pins and anchors."""
    import retrospective_reference_fixture as rfx  # noqa: PLC0415 - test helper
    from aggie_analytics.retrospective_baseline import reference as rc  # noqa: PLC0415
    world = rfx.build_world(base / "w")
    contract = rfx.write_contract(base / "rc.json", rfx.contract_for(world))
    code, result, stderr = rfx.run_build(contract, world, base / "out")
    if code != 0:
        raise AssertionError(f"fixture reference build refused: {stderr}")
    anchors = rfx.anchors_for(contract, world)
    db = rfx.database_of(result)
    with rc.ReferenceComparison(db, history_database=world["history_db"],
                                population_database=world["parent"]["database"], anchors=anchors) as ref:
        pins = {"database_identity": ref.database_identity, "content_identity": ref.content_identity,
                "database_sha256": ref.binding["sha256"], "contract_sha256": anchors["contract_sha256"],
                "history_identity": ref.history_identity, "population_identity": ref.population_identity}
        derived = ref.derived
    return {"world": world, "anchors": anchors, "db": db, "pins": pins, "derived": derived, "rc": rc}


def profile_doc(fx, profile_id=PID, db=None):
    return {"profile_id": profile_id, "reference_database": str(db or fx["db"]),
            "history_database": str(fx["world"]["history_db"]),
            "population_database": str(fx["world"]["parent"]["database"]), "expected": dict(fx["pins"])}


def registry_for(fx, *profiles):
    configs = research.load_config({"schema": research.CONFIG_SCHEMA, "profiles": list(profiles)}, pins=fx["pins"])
    return research.ResearchRegistry(configs, anchors=fx["anchors"])


def rehouse(fx, root: Path) -> Path:
    """A byte copy of the fixture reference (database and content identity directories, both manifests) under root."""
    db = Path(fx["db"])
    population = db.parent.parent.parent
    for kind, ident in (("canonical", db.parent.name), ("canonical", fx["pins"]["content_identity"]),
                        ("manifests", db.parent.name), ("manifests", fx["pins"]["content_identity"])):
        source = population.parent.parent / kind / population.name / "sha256" / ident
        if source.is_dir():
            shutil.copytree(source, root / kind / population.name / "sha256" / ident)
    return root / "canonical" / population.name / "sha256" / db.parent.name / db.name


class ResearchApiCases(unittest.TestCase):
    """The configured research surface on a verified fixture profile through the actual ASGI application."""

    @classmethod
    def setUpClass(cls):
        require_product()
        from aggie_analytics.api import create_app  # noqa: PLC0415
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.fx = build_fixture(base)
        cls.registry = registry_for(cls.fx, profile_doc(cls.fx))
        cls.app = create_app(snapshot_root=base / "snap", research_config=cls.registry)
        cls.assert_state = cls.registry.get(PID).wait(120)
        cls.base = str(base)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def api(self, tail, query=""):
        return get_json(self.app, f"/api/v1/research/profiles/{PID}{tail}", query)

    def test_profile_listing_and_detail(self):
        self.assertEqual("AVAILABLE", self.assert_state)
        status, headers, doc = get_json(self.app, "/api/v1/research/profiles")
        self.assertEqual(200, status)
        self.assertEqual("no-store", headers["cache-control"])
        self.assertEqual([PID], [p["profile_id"] for p in doc["profiles"]])
        self.assertEqual("AVAILABLE", doc["profiles"][0]["state"])
        verified = doc["profiles"][0]["verified_identities"]
        self.assertEqual(self.fx["pins"], {k: verified[k] for k in self.fx["pins"]})
        status, _h, detail = self.api("")
        self.assertEqual(200, status)
        derived = self.fx["derived"]
        self.assertEqual(len(derived["targets"]), detail["coverage"]["games"])
        self.assertEqual(len(derived["estimates"]), detail["coverage"]["estimates"])
        self.assertEqual("PIT_NOT_ADMITTED", detail["labels"]["pit_admission"])
        self.assertEqual("NOT_ESTABLISHED", detail["labels"]["predictive_skill"])
        ridge = next(m for m in detail["models"] if m["model_id"] == "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1")
        self.assertFalse(ridge["probability_served"])
        self.assertEqual("MARGIN", ridge["metric_kind"])
        self.assertNotIn(self.base, json.dumps(detail))

    def test_catalog_is_complete_and_pages_conserve_order(self):
        derived = self.fx["derived"]
        keys, offset = [], 0
        while True:
            status, _h, doc = self.api("/games", f"limit=7&offset={offset}")
            self.assertEqual(200, status)
            self.assertEqual(len(derived["targets"]), doc["total"])
            keys += [r["game_key"] for r in doc["rows"]]
            if doc["next_offset"] is None:
                break
            self.assertEqual(offset + doc["returned"], doc["next_offset"])
            offset = doc["next_offset"]
        self.assertEqual([t["contest_key"] for t in derived["targets"]], keys)
        status, _h, doc = self.api("/games", f"offset={len(keys)}")
        self.assertEqual((200, 0, 0, None), (status, doc["returned"], len(doc["rows"]), doc["next_offset"]))

    def test_selectors_intersect_exactly_like_the_accepted_reader(self):
        from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: PLC0415
        derived = self.fx["derived"]
        names = bm.team_name_index(derived["targets"])
        for season, team in ((2023, "org:697"), (2022, "Texas A&M"), (2021, "Charlie St."), (2022, "org:3")):
            want = [s["contest_key"] + "|" + s["model_id"] for s in derived["scores"]
                    if s["season"] == season and s["model_id"] == "NULL_HALF_V1" and
                    any(bm.team_matches(team, s["season"], side, names) for side in (s["a_key"], s["b_key"]))]
            status, _h, doc = self.api("/scores", f"season={season}&team={team.replace('&', '%26').replace(' ', '%20')}"
                                                  "&model=NULL_HALF_V1&limit=500")
            self.assertEqual(200, status)
            self.assertEqual(want, [r["contest_key"] + "|" + r["model_id"] for r in doc["rows"]])
            games = [t["contest_key"] for t in derived["targets"] if t["season"] == season and any(
                bm.team_matches(team, season, side, names) for side in (t["a_key"], t["b_key"]))]
            status, _h, doc = self.api("/games", f"season={season}&team={team.replace('&', '%26').replace(' ', '%20')}"
                                                 "&limit=500")
            self.assertEqual(games, [r["game_key"] for r in doc["rows"]])

    def test_unknown_disjoint_protected_and_forward_selectors_answer_empty(self):
        target = self.fx["derived"]["targets"][0]
        other_season = next(s for s in (2020, 2021, 2022, 2023) if s != target["season"])
        for query, scope in (("team=No%20Such%20Team", "RETROSPECTIVE_2016_2023"),
                             ("team=org:999999999", "RETROSPECTIVE_2016_2023"),
                             ("game=ncaa:999999999999", "RETROSPECTIVE_2016_2023"),
                             (f"game={target['contest_key']}&season={other_season}", "RETROSPECTIVE_2016_2023"),
                             ("season=2024", "PROTECTED_SEASON_NOT_IN_REFERENCE"),
                             ("season=2031", "FORWARD_SEASON_NOT_IN_REFERENCE"),
                             ("season=2015", "OUTSIDE_REFERENCE_SCOPE")):
            for grain in ("/games", "/features", "/estimates", "/scores", "/summary", "/comparisons"):
                with self.subTest(grain=grain, query=query):
                    status, _h, doc = self.api(grain, query)
                    self.assertEqual(200, status)
                    self.assertEqual((0, 0, [], None), (doc["total"], doc["returned"], doc["rows"], doc["next_offset"]))
                    self.assertEqual(scope, doc["season_scope_state"])

    def test_features_carry_both_team_prior_lineage(self):
        status, _h, doc = self.api("/features", "limit=500")
        self.assertEqual(200, status)
        self.assertEqual(len(self.fx["derived"]["features"]), doc["total"])
        excluded = 0
        for row in doc["rows"]:
            for side in ("team", "opponent"):
                block = row[side]
                self.assertEqual(block["games"], len(block["contributing"]))
                for item in block["contributing"]:
                    self.assertLess(item["contest_date"], row["contest_date"])
                    self.assertNotEqual(row["contest_key"], item["contest_key"])
                for item in row["excluded_prior_inputs"][side]:
                    self.assertTrue(item["reasons"])
                    self.assertLessEqual(item["contest_date"] or "", row["contest_date"])
                    excluded += 1
            self.assertEqual("ACCEPTED_HISTORY_VIEW_EXCLUDED_INPUTS", row["excluded_prior_inputs_source"])
        self.assertGreater(excluded, 0)

    def test_game_detail_both_orientations_estimates_and_scores(self):
        key = self.fx["derived"]["targets"][5]["contest_key"]
        status, _h, doc = self.api(f"/games/{key}")
        self.assertEqual(200, status)
        self.assertEqual(["A", "B"], [f["view"] for f in doc["features"]])
        self.assertEqual(10, len(doc["estimates"]))
        self.assertEqual(5, len(doc["scores"]))
        for e in doc["estimates"]:
            if e["model_id"] == "PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1":
                self.assertNotIn("probability", e)
                self.assertIn("margin", e)
        status, _h, digits = self.api(f"/games/{key.split(':')[1]}")
        self.assertEqual((200, key), (status, digits["game"]["game_key"]))
        status, _h, missing = self.api("/games/ncaa:999999999999")
        self.assertEqual((404, "GAME_NOT_IN_PROFILE"), (status, missing["error"]["code"]))
        status, _h, bad = self.api("/games/bad-key")
        self.assertEqual((400, "CONTEST_KEY_INVALID"), (status, bad["error"]["code"]))

    def test_parameters_and_inapplicable_selectors(self):
        status, _h, doc = self.api("/parameters")
        self.assertEqual((200, 5), (status, doc["total"]))
        status, _h, doc = self.api("/parameters", "model=PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1")
        self.assertEqual(["PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1"], [r["model_id"] for r in doc["rows"]])
        for query in ("season=2022", "team=org:697", "game=ncaa:1", "partition=SPLIT-DEV-SEL", "slice=NATIONAL"):
            status, _h, doc = self.api("/parameters", query)
            self.assertEqual((400, "FILTER_NOT_APPLICABLE"), (status, doc["error"]["code"]))

    def test_summary_selection_and_no_phantom_rows(self):
        status, _h, doc = self.api("/summary", "team=org:697&limit=500")
        self.assertEqual(200, status)
        self.assertGreater(doc["total"], 0)
        self.assertIn("summary_selection", doc)
        self.assertTrue(all(r["record_type"] == "reference_summary_row" for r in doc["rows"]))
        status, _h, empty = self.api("/summary", "team=No%20Such%20Team")
        self.assertEqual((200, 0, []), (status, empty["total"], empty["rows"]))
        self.assertEqual(0, empty["summary_selection"]["canonical_games"])
        status, _h, full = self.api("/summary", "limit=500")
        self.assertEqual(len(self.fx["derived"]["summary"]["rows"]), full["total"])

    def test_baseline_comparisons_are_exact_differences_of_served_means(self):
        status, _h, rows = self.api("/summary", "season=2023&slice=NATIONAL")
        means = {r["model_id"]: r for r in rows["rows"]}
        status, _h, doc = self.api("/comparisons", "season=2023&slice=NATIONAL&baseline=SMOOTHED_HISTORY_ODDS_V1")
        self.assertEqual(200, status)
        base = means["SMOOTHED_HISTORY_ODDS_V1"]
        for row in doc["rows"]:
            other = means[row["model_id"]]
            want = Fraction(other["brier_mean"]["numerator"], other["brier_mean"]["denominator"]) - \
                Fraction(base["brier_mean"]["numerator"], base["brier_mean"]["denominator"])
            got = Fraction(row["brier_mean_difference"]["numerator"], row["brier_mean_difference"]["denominator"])
            self.assertEqual(want, got)
            self.assertEqual(repr(float(other["log_loss_mean"]) - float(base["log_loss_mean"])),
                             row["log_loss_mean_difference"])
            self.assertEqual("SMOOTHED_HISTORY_ODDS_V1", row["baseline_model_id"])
        self.assertEqual({"NULL_HALF_V1", "SITE_BLIND_ELO_REFERENCE_V1", "PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1"},
                         {r["model_id"] for r in doc["rows"]})
        status, _h, null = self.api("/comparisons", "season=2023&slice=NATIONAL")
        self.assertEqual({"reference_comparison_row"}, {r["record_type"] for r in null["rows"]})
        status, _h, bad = self.api("/comparisons", "baseline=PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1")
        self.assertEqual((400, "BASELINE_NOT_PROBABILITY"), (status, bad["error"]["code"]))
        status, _h, bad = self.api("/comparisons", "baseline=ELO")
        self.assertEqual((400, "BASELINE_INVALID"), (status, bad["error"]["code"]))

    def test_strict_parameters_and_inert_strings(self):
        for query, code in (("path=C:%5Cdata%5Cother.sqlite", "UNKNOWN_PARAMETER"),
                            ("database=x", "UNKNOWN_PARAMETER"), ("season=2022&season=2023", "PARAMETER_REPEATED"),
                            ("season=20x2", "SEASON_INVALID"), ("limit=501", "LIMIT_INVALID"),
                            ("limit=-1", "LIMIT_INVALID"), ("offset=1e9", "OFFSET_INVALID"),
                            ("model=ELO", "MODEL_UNKNOWN"), ("partition=SPLIT-PROTECTED", "PARTITION_UNKNOWN"),
                            ("game=bad%01key", "GAME_INVALID")):
            status, headers, doc = self.api("/scores", query)
            with self.subTest(query=query):
                self.assertEqual((400, code), (status, doc["error"]["code"]))
                self.assertEqual("RETROSPECTIVE_RESEARCH", doc["labels"]["research_surface"])
        for team in ("%3Cscript%3Ealert(1)%3C%2Fscript%3E", "x%27%3B%20DROP%20TABLE%20blocks%3B--"):
            status, headers, body = asgi_get(self.app, f"/api/v1/research/profiles/{PID}/games", f"team={team}")
            self.assertEqual(200, status)
            self.assertTrue(headers["content-type"].startswith("application/json"))
            doc = json.loads(body)
            self.assertEqual((0, []), (doc["total"], doc["rows"]))
        status, _h, doc = get_json(self.app, "/api/v1/research/profiles", "x=1")
        self.assertEqual((400, "UNKNOWN_PARAMETER"), (status, doc["error"]["code"]))
        status, _h, doc = get_json(self.app, "/api/v1/research/profiles/no-such-profile/games")
        self.assertEqual((404, "RESEARCH_PROFILE_UNKNOWN"), (status, doc["error"]["code"]))

    def test_errors_never_carry_paths_tracebacks_or_credentials(self):
        bodies = []
        for path, query in ((f"/api/v1/research/profiles/{PID}/scores", "season=bad"),
                            (f"/api/v1/research/profiles/{PID}/games/ncaa:999999999999", ""),
                            (f"/api/v1/research/profiles/{PID}/parameters", "season=2022"),
                            ("/api/v1/research/profiles/zz-unknown/summary", "")):
            bodies.append(asgi_get(self.app, path, query)[2].decode("utf-8"))
        for text in bodies:
            self.assertNotIn(self.base, text)
            self.assertNotIn("Traceback", text)
            self.assertNotIn(":\\\\", text)
            self.assertNotIn("sqlite", text.lower())

    def test_research_page_and_packaged_assets(self):
        status, headers, body = asgi_get(self.app, "/research")
        self.assertEqual(200, status)
        self.assertIn("default-src 'self'", headers["content-security-policy"])
        html = body.decode("utf-8")
        for phrase in ("RETROSPECTIVE_RESEARCH", "UNTRUSTED_SHADOW", "PIT_NOT_ADMITTED", "not a forecast",
                       "/static/research.js", 'role="tablist"', 'aria-live="polite"'):
            self.assertIn(phrase, html)
        for asset in ("/static/research.js", "/static/research.css"):
            self.assertEqual(200, asgi_get(self.app, asset)[0])
        script = asgi_get(self.app, "/static/research.js")[2].decode("utf-8")
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("eval(", script)

    def test_requests_use_no_network(self):
        for tail, query in (("/games", "limit=3"), ("/summary", "slice=TEXAS_AM"), ("", ""),
                            ("/comparisons", "baseline=SMOOTHED_HISTORY_ODDS_V1")):
            status = asgi_get(self.app, f"/api/v1/research/profiles/{PID}{tail}", query, offline=True)[0]
            self.assertEqual(200, status, tail)


class ResearchProfileLifecycleCases(unittest.TestCase):
    """Unconfigured absence, verifying, unavailable (reader refusal) and stale profiles (fail closed)."""

    @classmethod
    def setUpClass(cls):
        require_product()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.fx = build_fixture(cls.root / "fx")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_unconfigured_app_is_unchanged_and_has_no_research(self):
        from aggie_analytics.api import create_app  # noqa: PLC0415
        app = create_app(snapshot_root=self.root / "plain")
        self.assertEqual(BASE_ROUTES, sorted(getattr(r, "path", "") for r in app.routes))
        for path in ("/research", "/api/v1/research/profiles", f"/api/v1/research/profiles/{PID}/games",
                     "/static/research.html"):
            status = asgi_get(app, path)[0]
            self.assertEqual(404 if path != "/static/research.html" else 200, status, path)
        openapi = json.loads(asgi_get(app, "/api/v1/openapi.json")[2])
        self.assertFalse([p for p in openapi["paths"] if "research" in p])

    def test_verifying_profile_serves_nothing(self):
        from aggie_analytics.api import create_app  # noqa: PLC0415
        gate = threading.Event()
        original = research.ResearchProfile._verify

        def held(profile):
            gate.wait(60)
            original(profile)
        with mock.patch.object(research.ResearchProfile, "_verify", held):
            registry = registry_for(self.fx, profile_doc(self.fx, "held-profile"))
            app = create_app(snapshot_root=self.root / "held", research_config=registry)
            status, headers, doc = get_json(app, "/api/v1/research/profiles/held-profile/games")
            self.assertEqual((503, "RESEARCH_PROFILE_VERIFYING"), (status, doc["error"]["code"]))
            self.assertEqual("2", headers["retry-after"])
            listing = get_json(app, "/api/v1/research/profiles")[2]
            self.assertEqual("VERIFYING", listing["profiles"][0]["state"])
            gate.set()
            self.assertEqual("AVAILABLE", registry.get("held-profile").wait(120))
        self.assertEqual(200, get_json(app, "/api/v1/research/profiles/held-profile/games")[0])

    def test_tampered_copy_is_unavailable_with_the_reader_code(self):
        from aggie_analytics.api import create_app  # noqa: PLC0415
        db = rehouse(self.fx, self.root / "tamper")
        data = bytearray(db.read_bytes())
        data[-100] ^= 1
        db.write_bytes(bytes(data))
        registry = registry_for(self.fx, profile_doc(self.fx, "tampered-copy", db))
        app = create_app(snapshot_root=self.root / "tsnap", research_config=registry)
        self.assertEqual("UNAVAILABLE", registry.get("tampered-copy").wait(120))
        status, _h, doc = get_json(app, "/api/v1/research/profiles/tampered-copy/scores")
        self.assertEqual((503, "REFERENCE_DATABASE_TAMPERED"), (status, doc["error"]["code"]))
        listing = get_json(app, "/api/v1/research/profiles")[2]["profiles"][0]
        self.assertEqual(("UNAVAILABLE", "REFERENCE_DATABASE_TAMPERED"), (listing["state"], listing["refusal_code"]))
        self.assertNotIn(str(self.root), json.dumps(listing))

    def test_missing_file_is_unavailable_and_never_created(self):
        from aggie_analytics.api import create_app  # noqa: PLC0415
        missing = self.root / "absent" / "canonical" / research.REFERENCE_POPULATION / "sha256" / \
            self.fx["pins"]["database_identity"] / research.REFERENCE_DB_FILE
        registry = registry_for(self.fx, profile_doc(self.fx, "missing-file", missing))
        create_app(snapshot_root=self.root / "msnap", research_config=registry)
        self.assertEqual("UNAVAILABLE", registry.get("missing-file").wait(120))
        self.assertEqual("RESEARCH_PROFILE_FILE_MISSING", registry.get("missing-file").summary()["refusal_code"])
        self.assertFalse(missing.parent.exists())

    def test_changed_file_after_verification_closes_the_profile(self):
        from aggie_analytics.api import create_app  # noqa: PLC0415
        db = rehouse(self.fx, self.root / "stale")
        registry = registry_for(self.fx, profile_doc(self.fx, "stale-copy", db))
        app = create_app(snapshot_root=self.root / "ssnap", research_config=registry)
        self.assertEqual("AVAILABLE", registry.get("stale-copy").wait(120))
        self.assertEqual(200, get_json(app, "/api/v1/research/profiles/stale-copy/games")[0])
        stat = db.stat()
        os.utime(db, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        for _ in range(2):
            status, _h, doc = get_json(app, "/api/v1/research/profiles/stale-copy/games")
            self.assertEqual(503, status)
            self.assertIn(doc["error"]["code"], ("RESEARCH_PROFILE_STALE",))

    def test_json_operator_configuration_binds_the_packaged_pins(self):
        from aggie_analytics.api import create_app  # noqa: PLC0415
        path = self.root / "operator.json"
        path.write_text(json.dumps({"schema": research.CONFIG_SCHEMA, "profiles": [profile_doc(self.fx)]}),
                        encoding="utf-8")
        with self.assertRaises(research.ResearchConfigError) as caught:
            create_app(snapshot_root=self.root / "jsnap", research_config=str(path))
        self.assertEqual("RESEARCH_PROFILE_PIN_UNACCEPTED", caught.exception.code)


class GenuineResearchProfileCases(unittest.TestCase):
    """The accepted C56 reference through a JSON operator configuration bound to the packaged pins (mounted only)."""

    @classmethod
    def setUpClass(cls):
        require_product()
        root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
        pins = research.accepted_pins()
        if not root:
            raise unittest.SkipTest("AGGIE_ANALYTICS_DATA_ROOT is not set (no private lake mounted)")
        data = Path(root)
        cls.locations = {
            "reference_database": data / "canonical" / research.REFERENCE_POPULATION / "sha256" /
            pins["database_identity"] / research.REFERENCE_DB_FILE,
            "history_database": data / "canonical" / "national_history_prefix_2016_2023" / "sha256" /
            pins["history_identity"] / research.HISTORY_DB_FILE,
            "population_database": data / "canonical" / "national_di_population_2016_2025" / "sha256" /
            pins["population_identity"] / research.POPULATION_DB_FILE}
        if not all(p.is_file() for p in cls.locations.values()):
            raise unittest.SkipTest("the accepted reference, history and parent are not in the mounted lake")
        from aggie_analytics.api import create_app  # noqa: PLC0415
        cls.tmp = tempfile.TemporaryDirectory()
        path = Path(cls.tmp.name) / "operator.json"
        path.write_text(json.dumps({"schema": research.CONFIG_SCHEMA, "profiles": [{
            "profile_id": "national-retrospective-reference-2016-2023",
            **{k: str(v) for k, v in cls.locations.items()}, "expected": pins}]}), encoding="utf-8")
        cls.app = create_app(snapshot_root=Path(cls.tmp.name) / "snap", research_config=str(path))
        cls.state = cls.app.state.research_registry.get("national-retrospective-reference-2016-2023").wait(600)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_genuine_accepted_reference_is_served(self):
        self.assertEqual("AVAILABLE", self.state)
        tail = "/api/v1/research/profiles/national-retrospective-reference-2016-2023"
        status, _h, detail = get_json(self.app, tail)
        self.assertEqual(200, status)
        self.assertEqual(research.accepted_pins()["database_identity"],
                         detail["verified_identities"]["database_identity"])
        self.assertEqual((5875, 11750, 58750, 29375, 5), (
            detail["coverage"]["games"], detail["coverage"]["feature_records"], detail["coverage"]["estimates"],
            detail["coverage"]["scores"], detail["coverage"]["parameters"]))
        self.assertEqual(5875, get_json(self.app, tail + "/games", "limit=1")[2]["total"])
        self.assertEqual(["PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1", "SITE_BLIND_ELO_REFERENCE_V1"],
                         sorted(detail["adverse_2023"]["new_probability_references_not_beating_comparator"]))
