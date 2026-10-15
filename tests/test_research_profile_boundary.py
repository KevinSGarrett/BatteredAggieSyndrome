"""BAT-728 (Cycle #57 TP57-A01): the private research profile boundary, without FastAPI.

Configuration locations are refused lexically before any filesystem access (Windows and POSIX semantics are both
exercised on every host through the ``os_name`` parameter, and each against a simulated host of the other kind; no
share or device is ever contacted), the operator
configuration is validated completely with exact JSON types and the packaged accepted pins, and request selectors are
parsed strictly (unknown, repeated, inapplicable and malformed parameters refuse with their own codes).
"""
from __future__ import annotations

import builtins
import io
import os
import socket
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.product import research  # noqa: E402

HEX = {k: c * 64 for k, c in zip(research.EXPECTED_KEYS, "abcdef")}
DB_ID, HIST_ID, POP_ID = HEX["database_identity"], HEX["history_identity"], HEX["population_identity"]
REF_POP, REF_FILE = "national_retrospective_reference_2016_2023", "national_retrospective_reference.sqlite"
MARKER = "MF57A01-02"


def win_profile(**patch):
    base = {"profile_id": "fixture-profile",
            "reference_database": f"C:\\data\\canonical\\national_retrospective_reference_2016_2023\\sha256\\{DB_ID}"
                                  "\\national_retrospective_reference.sqlite",
            "history_database": f"C:\\data\\canonical\\h\\sha256\\{HIST_ID}\\national_history.sqlite",
            "population_database": f"C:\\data\\canonical\\p\\sha256\\{POP_ID}\\national_population.sqlite",
            "expected": dict(HEX)}
    base.update(patch)
    return base


def posix_profile(**patch):
    base = {"profile_id": "fixture-profile",
            "reference_database": f"/data/canonical/national_retrospective_reference_2016_2023/sha256/{DB_ID}"
                                  "/national_retrospective_reference.sqlite",
            "history_database": f"/data/canonical/h/sha256/{HIST_ID}/national_history.sqlite",
            "population_database": f"/data/canonical/p/sha256/{POP_ID}/national_population.sqlite",
            "expected": dict(HEX)}
    base.update(patch)
    return base


def config(*profiles):
    return {"schema": research.CONFIG_SCHEMA, "profiles": list(profiles)}


def spelled(rule, **patch):
    return win_profile(**patch) if rule == "nt" else posix_profile(**patch)


def located(rule, *parts):
    return "C:\\" + "\\".join(parts) if rule == "nt" else "/" + "/".join(parts)


class AccessSentinel:
    """Any filesystem, SQLite or socket access raises (the boundary must refuse before reaching one)."""

    def __enter__(self):
        def refuse(*_args, **_kwargs):
            raise AssertionError("filesystem, SQLite or network access before refusal")
        self.stack = [mock.patch.object(os, "stat", refuse), mock.patch.object(os, "lstat", refuse),
                      mock.patch.object(os, "open", refuse), mock.patch.object(os.path, "exists", refuse),
                      mock.patch.object(os.path, "isfile", refuse), mock.patch.object(builtins, "open", refuse),
                      mock.patch.object(io, "open", refuse), mock.patch.object(sqlite3, "connect", refuse),
                      mock.patch.object(socket, "getaddrinfo", refuse),
                      mock.patch.object(socket.socket, "connect", refuse)]
        for item in self.stack:
            item.start()
        return self

    def __exit__(self, *exc):
        for item in reversed(self.stack):
            item.stop()
        return False


class SimulatedHostOs:
    """The research module's view of ``os`` on a simulated host: only ``name`` differs from the real module (every
    real access still reaches the sentinels)."""

    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        return getattr(os, attr)


class LocationPolicyTests(unittest.TestCase):
    def assertRefused(self, spelling, code, os_name):
        with self.subTest(os_name=os_name, spelling=spelling), AccessSentinel():
            with self.assertRaises(research.ResearchConfigError) as caught:
                research.validate_location(spelling, os_name=os_name)
            self.assertEqual(code, caught.exception.code)
            if spelling:
                self.assertNotIn(spelling, caught.exception.message)

    def test_windows_accepts_local_drive_and_extended_spellings(self):
        long_tail = "\\".join(["segment-" + "x" * 40] * 8) + "\\national_population.sqlite"
        for spelling in ("C:\\data\\file.sqlite", "c:/data/file.sqlite", "D:\\a b\\#%'\u00e9\\file.sqlite",
                         "\\\\?\\C:\\data\\file.sqlite", "C:\\" + long_tail, "\\\\?\\C:\\" + long_tail):
            with self.subTest(spelling=spelling), AccessSentinel():
                self.assertEqual(spelling, research.validate_location(spelling, os_name="nt"))
        self.assertGreater(len("\\\\?\\C:\\" + long_tail), 300)

    def test_windows_refuses_network_device_namespace_and_traversal(self):
        for spelling, code in (
                ("\\\\server\\share\\file.sqlite", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("//server/share/file.sqlite", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("\\/server\\share", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("\\\\?\\UNC\\server\\share\\file.sqlite", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("\\\\?\\GLOBALROOT\\Device\\Null", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("\\\\?\\Volume{00000000-0000-0000-0000-000000000000}\\f", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("\\\\.\\NUL", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("\\\\.\\PIPE\\name", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("\\\\.\\C:\\data\\file.sqlite", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("C:\\data\\NUL\\file.sqlite", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("C:\\data\\com1.txt", "RESEARCH_LOCATION_UNSUPPORTED"),
                ("C:\\data\\..\\secret\\file.sqlite", "RESEARCH_LOCATION_TRAVERSAL"),
                ("C:\\data\\.\\file.sqlite", "RESEARCH_LOCATION_TRAVERSAL"),
                ("\\\\?\\C:\\data\\..\\file.sqlite", "RESEARCH_LOCATION_TRAVERSAL"),
                ("C:\\data\\\\file.sqlite", "RESEARCH_LOCATION_NOT_LITERAL"),
                ("C:\\data.\\file.sqlite", "RESEARCH_LOCATION_NOT_LITERAL"),
                ("C:\\data \\file.sqlite", "RESEARCH_LOCATION_NOT_LITERAL"),
                ("C:\\data\\file.sqlite:stream", "RESEARCH_LOCATION_NOT_LITERAL"),
                ("\\\\?\\C:\\data/file.sqlite", "RESEARCH_LOCATION_NOT_LITERAL"),
                ("data\\file.sqlite", "RESEARCH_LOCATION_NOT_ABSOLUTE"),
                ("C:data\\file.sqlite", "RESEARCH_LOCATION_NOT_ABSOLUTE"),
                ("\\data\\file.sqlite", "RESEARCH_LOCATION_NOT_ABSOLUTE"),
                ("", "RESEARCH_LOCATION_INVALID"), ("C:\\data\\fi\x00le", "RESEARCH_LOCATION_INVALID"),
                ("C:\\data\\fi\nle", "RESEARCH_LOCATION_INVALID")):
            self.assertRefused(spelling, code, "nt")

    def test_posix_names_are_ordinary_and_traversal_refused(self):
        for spelling in ("/data/file.sqlite", "/data/a\\b:c?d#e%f/file.sqlite", "/data/\u00e9 '\\\\server/file.sqlite",
                         "/data/" + "/".join(["d" * 60] * 6) + "/file.sqlite"):
            with self.subTest(spelling=spelling), AccessSentinel():
                self.assertEqual(spelling, research.validate_location(spelling, os_name="posix"))
        for spelling, code in (("data/file.sqlite", "RESEARCH_LOCATION_NOT_ABSOLUTE"),
                               ("\\\\server\\share\\file", "RESEARCH_LOCATION_NOT_ABSOLUTE"),
                               ("/data/../etc/file", "RESEARCH_LOCATION_TRAVERSAL"),
                               ("/data/./file", "RESEARCH_LOCATION_TRAVERSAL"),
                               ("/data//file", "RESEARCH_LOCATION_NOT_LITERAL"),
                               ("/dev/null", "RESEARCH_LOCATION_UNSUPPORTED"),
                               ("/proc/self/fd/0", "RESEARCH_LOCATION_UNSUPPORTED")):
            self.assertRefused(spelling, code, "posix")

    def test_non_string_location_refused(self):
        for value in (None, 7, True, ["C:\\x"], {"path": "C:\\x"}, b"C:\\x"):
            with self.subTest(value=value), self.assertRaises(research.ResearchConfigError) as caught:
                research.validate_location(value, os_name="nt")
            self.assertEqual("RESEARCH_LOCATION_INVALID", caught.exception.code)

    @unittest.skipUnless(os.name == "nt", "the extended-length I/O form is a Windows spelling")
    def test_long_windows_location_uses_the_native_extended_form(self):
        long_path = "C:\\" + "\\".join(["p" * 50] * 6) + "\\national_population.sqlite"
        self.assertEqual("\\\\?\\" + long_path, research.io_location(long_path))
        self.assertEqual("C:\\short\\x.sqlite", research.io_location("C:\\short\\x.sqlite"))


class ConfigurationTests(unittest.TestCase):
    def load(self, doc, os_name="nt"):
        return research.load_config(doc, pins=HEX, os_name=os_name)

    def assertCode(self, doc, code, os_name="nt"):
        with self.subTest(code=code), AccessSentinel():
            with self.assertRaises(research.ResearchConfigError) as caught:
                self.load(doc, os_name)
            self.assertEqual(code, caught.exception.code)

    def test_valid_configuration_on_both_semantics(self):
        with AccessSentinel():
            win = self.load(config(win_profile()))
            posix = self.load(config(posix_profile()), "posix")
        self.assertEqual(["fixture-profile"], [p.profile_id for p in win])
        self.assertEqual(HEX, dict(posix[0].expected))
        self.assertIsNone(win[0].reference_manifest)

    def test_shape_types_and_identities_refused(self):
        self.assertCode({"schema": research.CONFIG_SCHEMA}, "RESEARCH_CONFIG_INVALID")
        self.assertCode({**config(win_profile()), "extra": "x"}, "RESEARCH_CONFIG_INVALID")
        self.assertCode({"schema": "OTHER", "profiles": [win_profile()]}, "RESEARCH_CONFIG_SCHEMA_UNSUPPORTED")
        self.assertCode(config(), "RESEARCH_CONFIG_INVALID")
        self.assertCode(config(*[win_profile(profile_id=f"p-{i:02d}") for i in range(9)]), "RESEARCH_CONFIG_INVALID")
        self.assertCode(config(win_profile(), win_profile()), "RESEARCH_PROFILE_ID_DUPLICATE")
        self.assertCode(config(win_profile(profile_id="Bad ID")), "RESEARCH_PROFILE_ID_INVALID")
        self.assertCode(config(win_profile(profile_id="../x")), "RESEARCH_PROFILE_ID_INVALID")
        self.assertCode(config(win_profile(extra="x")), "RESEARCH_CONFIG_INVALID")
        self.assertCode(config({k: v for k, v in win_profile().items() if k != "history_database"}),
                        "RESEARCH_CONFIG_INVALID")
        self.assertCode(config(win_profile(display_label="bad\nlabel")), "RESEARCH_CONFIG_INVALID")
        self.assertCode(config(win_profile(history_database=7)), "RESEARCH_CONFIG_INVALID")
        self.assertCode(config(win_profile(reference_manifest=True)), "RESEARCH_CONFIG_INVALID")
        for key in research.EXPECTED_KEYS:
            upper = dict(HEX, **{key: HEX[key].upper()})
            self.assertCode(config(win_profile(expected=upper)), "RESEARCH_IDENTITY_INVALID")
            short = dict(HEX, **{key: HEX[key][:63]})
            self.assertCode(config(win_profile(expected=short)), "RESEARCH_IDENTITY_INVALID")
            other = dict(HEX, **{key: "0" * 64})
            self.assertCode(config(win_profile(expected=other)), "RESEARCH_PROFILE_PIN_UNACCEPTED")
        self.assertCode(config(win_profile(expected={**HEX, "extra": "1" * 64})), "RESEARCH_CONFIG_INVALID")

    def test_layout_literals_refused_before_access(self):
        wrong_dir = win_profile(reference_database=f"C:\\data\\canonical\\national_retrospective_reference_2016_2023"
                                                   f"\\sha256\\{'1' * 64}\\national_retrospective_reference.sqlite")
        self.assertCode(config(wrong_dir), "RESEARCH_PROFILE_LAYOUT_INVALID")
        wrong_name = win_profile(history_database=f"C:\\data\\h\\sha256\\{HIST_ID}\\other.sqlite")
        self.assertCode(config(wrong_name), "RESEARCH_PROFILE_LAYOUT_INVALID")
        wrong_population = win_profile(reference_database=f"C:\\data\\canonical\\other\\sha256\\{DB_ID}"
                                                          "\\national_retrospective_reference.sqlite")
        self.assertCode(config(wrong_population), "RESEARCH_PROFILE_LAYOUT_INVALID")
        self.assertCode(config(win_profile(reference_manifest="C:\\m\\sha256\\" + DB_ID + "\\other.json")),
                        "RESEARCH_PROFILE_LAYOUT_INVALID")
        self.assertCode(config(win_profile(history_database="\\\\server\\share\\sha256\\" + HIST_ID +
                                           "\\national_history.sqlite")), "RESEARCH_LOCATION_UNSUPPORTED")
        self.assertCode(config(win_profile(population_database="C:\\p\\..\\sha256\\" + POP_ID +
                                           "\\national_population.sqlite")), "RESEARCH_LOCATION_TRAVERSAL")

    def test_configuration_file_is_strict_json(self):
        with tempfile.TemporaryDirectory() as td:
            for name, text, code in (
                    ("dupe.json", '{"schema": "a", "schema": "b", "profiles": []}', "RESEARCH_CONFIG_INVALID"),
                    ("number.json", '{"schema": "%s", "profiles": [1]}' % research.CONFIG_SCHEMA,
                     "RESEARCH_CONFIG_INVALID"),
                    ("nan.json", '{"schema": NaN, "profiles": []}', "RESEARCH_CONFIG_INVALID"),
                    ("broken.json", '{"schema": ', "RESEARCH_CONFIG_INVALID")):
                path = Path(td) / name
                path.write_text(text, encoding="utf-8")
                with self.subTest(name=name), self.assertRaises(research.ResearchConfigError) as caught:
                    research.load_config(str(path), pins=HEX)
                self.assertEqual(code, caught.exception.code)
            binary = Path(td) / "binary.json"
            binary.write_bytes(b"\xff\xfe\x00")
            with self.assertRaises(research.ResearchConfigError) as caught:
                research.load_config(str(binary), pins=HEX)
            self.assertEqual("RESEARCH_CONFIG_INVALID", caught.exception.code)
            with self.assertRaises(research.ResearchConfigError) as caught:
                research.load_config(str(Path(td) / "absent.json"), pins=HEX)
            self.assertEqual("RESEARCH_CONFIG_UNREADABLE", caught.exception.code)
            self.assertNotIn(td, caught.exception.message)

    def test_configuration_location_refused_before_reading(self):
        spelling = "\\\\bas-research-sentinel-host\\share\\config.json" if os.name == "nt" else "/dev/stdin"
        with AccessSentinel(), self.assertRaises(research.ResearchConfigError) as caught:
            research.load_config(spelling, pins=HEX)
        self.assertEqual("RESEARCH_LOCATION_UNSUPPORTED", caught.exception.code)

    def test_packaged_pins_are_the_accepted_reference(self):
        pins = research.accepted_pins()
        self.assertEqual("ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8", pins["database_identity"])
        self.assertEqual("fe303a90d8753956b914d3c7c2adfe2d33d9816bfb45689b0361f8e36e2e6cc0", pins["content_identity"])
        self.assertEqual("17a0776587eb30918903dc0d38c736958b1984feb4b40379bbfc80425035785d", pins["database_sha256"])
        self.assertEqual("aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b", pins["history_identity"])
        self.assertEqual("3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27", pins["population_identity"])
        # a self-consistent configuration naming other identities is not authority: the packaged pins decide
        with self.assertRaises(research.ResearchConfigError) as caught:
            research.load_config(config(win_profile()))
        self.assertEqual("RESEARCH_PROFILE_PIN_UNACCEPTED", caught.exception.code)


class SelectorTests(unittest.TestCase):
    def assertCode(self, grain, items, code):
        with self.subTest(grain=grain, items=items), self.assertRaises(research.ResearchError) as caught:
            research.parse_query(grain, items)
        self.assertEqual(code, caught.exception.code)
        self.assertEqual(400 if code != "UNKNOWN_GRAIN" else 404, caught.exception.status)

    def test_valid_selectors(self):
        self.assertEqual({"limit": 50, "offset": 0}, research.parse_query("games", []))
        q = research.parse_query("scores", [("season", "2019"), ("team", " Texas A&M "), ("game", "ncaa:1"),
                                           ("model", "NULL_HALF_V1"), ("partition", "SPLIT-DEV-HIST"),
                                           ("limit", "500"), ("offset", "999999999")])
        self.assertEqual({"season": 2019, "team": "Texas A&M", "game": "ncaa:1", "model": "NULL_HALF_V1",
                          "partition": "SPLIT-DEV-HIST", "limit": 500, "offset": 999999999}, q)
        self.assertEqual("<script>alert(1)</script>", research.parse_query(
            "games", [("team", "<script>alert(1)</script>")])["team"])
        self.assertEqual("x'; DROP TABLE blocks;--", research.parse_query(
            "games", [("team", "x'; DROP TABLE blocks;--")])["team"])

    def test_strict_refusals(self):
        self.assertCode("games", [("path", "C:\\x")], "UNKNOWN_PARAMETER")
        self.assertCode("games", [("database", "x")], "UNKNOWN_PARAMETER")
        self.assertCode("games", [("season", "2019"), ("season", "2020")], "PARAMETER_REPEATED")
        self.assertCode("games", [("model", "NULL_HALF_V1")], "FILTER_NOT_APPLICABLE")
        self.assertCode("features", [("slice", "NATIONAL")], "FILTER_NOT_APPLICABLE")
        self.assertCode("parameters", [("season", "2019")], "FILTER_NOT_APPLICABLE")
        self.assertCode("parameters", [("team", "org:697")], "FILTER_NOT_APPLICABLE")
        self.assertCode("summary", [("baseline", "NULL_HALF_V1")], "FILTER_NOT_APPLICABLE")
        for bad in ("19", "2019.0", "+2019", " 2019", "2019 ", "２０１９", "", "1e3"):
            self.assertCode("games", [("season", bad)], "SEASON_INVALID")
        for bad in ("0", "501", "-1", "1.5", "", "abc", "10000"):
            self.assertCode("games", [("limit", bad)], "LIMIT_INVALID")
        for bad in ("-1", "1000000000", "1e2", "", "x"):
            self.assertCode("games", [("offset", bad)], "OFFSET_INVALID")
        for bad in ("", "   ", "a" * 121, "bad\x01team", "bad\x7fteam"):
            self.assertCode("games", [("team", bad)], "TEAM_INVALID")
        self.assertCode("games", [("game", "x" * 121)], "GAME_INVALID")
        self.assertCode("bogus", [], "UNKNOWN_GRAIN")

    def test_paging_conserves_order_membership_and_next_offset(self):
        rows = list(range(23))
        pages, offset = [], 0
        while True:
            page, following = research._page(rows, offset, 5)
            pages.append(page)
            if following is None:
                break
            self.assertEqual(offset + len(page), following)
            offset = following
        self.assertEqual(rows, [x for page in pages for x in page])
        self.assertEqual(([], None), research._page(rows, 23, 5))
        self.assertEqual(([], None), research._page(rows, 400, 5))
        self.assertEqual(([20, 21, 22], None), research._page(rows, 20, 5))


class RegistryTests(unittest.TestCase):
    def test_unknown_profile_ids_are_refused_without_echo(self):
        registry = research.ResearchRegistry(research.load_config(config(win_profile()), pins=HEX, os_name="nt"))
        for value in ("other", "../etc", "", "x" * 100, "FIXTURE-PROFILE"):
            with self.subTest(value=value), self.assertRaises(research.ResearchError) as caught:
                registry.get(value)
            self.assertEqual(("RESEARCH_PROFILE_UNKNOWN", 404), (caught.exception.code, caught.exception.status))
            self.assertNotIn(value or "\x00", caught.exception.payload()["error"]["message"])

    def test_error_payload_carries_labels_and_no_location(self):
        payload = research.ResearchError("X_CODE", "fixed message", 503).payload()
        self.assertEqual("RETROSPECTIVE_RESEARCH", payload["labels"]["research_surface"])
        self.assertEqual("PIT_NOT_ADMITTED", payload["labels"]["pit_admission"])
        self.assertEqual({"code": "X_CODE", "message": "fixed message", "status": 503}, payload["error"])


class HostIndependentSemanticsTests(unittest.TestCase):
    """MF57A01-02: one Windows or POSIX interpretation -- the selected ``os_name``, or the host's when it is omitted --
    governs a profile's spelling and its file-name, identity-directory and population layout on every host. The host
    is simulated for the research module only, so both directions run on every real host."""

    HOSTS = ("nt", "posix")

    def outcome(self, doc, *, host, os_name, select=None):
        with mock.patch.object(research, "os", SimulatedHostOs(host)), AccessSentinel():
            try:
                configs = research.load_config(doc, pins=HEX, os_name=os_name)
                if select is not None:
                    research.ResearchRegistry(configs).get(select)
            except research.ResearchError as exc:
                return exc.code
        return "ACCEPTED"

    def assertEveryHost(self, expected, build):
        """``build(rule)`` gives the (configuration, profile ID to select) spelled for one interpretation; selecting
        that interpretation must give ``expected[rule]`` on both simulated hosts."""
        for rule in ("nt", "posix"):
            doc, select = build(rule)
            for host in self.HOSTS:
                with self.subTest(host=host, os_name=rule):
                    self.assertEqual(expected[rule], self.outcome(doc, host=host, os_name=rule, select=select),
                                     f"{MARKER} host={host} os_name={rule}")

    def test_selected_semantics_accept_valid_profiles_and_manifests_on_every_host(self):
        accepted = dict.fromkeys(self.HOSTS, "ACCEPTED")
        self.assertEveryHost(accepted, lambda rule: (config(spelled(rule)), None))
        self.assertEveryHost(accepted, lambda rule: (config(spelled(rule, reference_manifest=located(
            rule, "data", "manifests", REF_POP, "sha256", DB_ID, "run_manifest.json"))), None))

    def test_selected_semantics_keep_duplicate_and_unknown_profile_codes_on_every_host(self):
        self.assertEveryHost(dict.fromkeys(self.HOSTS, "RESEARCH_PROFILE_ID_DUPLICATE"),
                             lambda rule: (config(spelled(rule), spelled(rule)), None))
        self.assertEveryHost(dict.fromkeys(self.HOSTS, "RESEARCH_PROFILE_UNKNOWN"),
                             lambda rule: (config(spelled(rule)), "not-registered"))

    def test_selected_semantics_read_literal_separators_on_every_host(self):
        # POSIX: a backslash is an ordinary filename character, so it never splits off the file name, the identity
        # directory or the population root; Windows: '/' and '\' both separate components.
        separators = {"nt": "ACCEPTED", "posix": "RESEARCH_PROFILE_LAYOUT_INVALID"}
        self.assertEveryHost(separators, lambda rule: (config(posix_profile(
            reference_database=f"/data/canonical/{REF_POP}/sha256/{DB_ID}\\{REF_FILE}")) if rule == "posix" else
            config({k: (v.replace("\\", "/") if k.endswith("_database") else v) for k, v in win_profile().items()}),
            None))
        self.assertEveryHost(separators, lambda rule: (config(spelled(rule, history_database=(
            f"/data/canonical/h/sha256\\{HIST_ID}/national_history.sqlite" if rule == "posix" else
            f"C:\\data/canonical\\h/sha256\\{HIST_ID}/national_history.sqlite"))), None))
        self.assertEveryHost(separators, lambda rule: (config(spelled(rule, reference_database=(
            f"/data/canonical/{REF_POP}\\sha256/{DB_ID}/{REF_FILE}" if rule == "posix" else
            f"C:/data/canonical/{REF_POP}\\sha256/{DB_ID}\\{REF_FILE}"))), None))
        # the same '..' between backslashes is one ordinary POSIX component but Windows traversal
        self.assertEveryHost({"nt": "RESEARCH_LOCATION_TRAVERSAL", "posix": "ACCEPTED"}, lambda rule: (config(spelled(
            rule, history_database=(f"/data/a\\..\\b/canonical/h/sha256/{HIST_ID}/national_history.sqlite"
                                    if rule == "posix" else
                                    f"C:\\data\\a\\..\\b\\canonical\\h\\sha256\\{HIST_ID}\\national_history.sqlite")
        )), None))

    def test_layout_location_and_type_refusals_hold_on_every_host(self):
        other = {"nt": "posix", "posix": "nt"}
        for code, build in (
                ("RESEARCH_PROFILE_LAYOUT_INVALID", lambda rule: spelled(rule, history_database=located(
                    rule, "data", "canonical", "h", "sha256", HIST_ID, "other.sqlite"))),
                ("RESEARCH_PROFILE_LAYOUT_INVALID", lambda rule: spelled(rule, history_database=located(
                    rule, "data", "canonical", "h", "sha256", "1" * 64, "national_history.sqlite"))),
                ("RESEARCH_PROFILE_LAYOUT_INVALID", lambda rule: spelled(rule, reference_database=located(
                    rule, "data", "canonical", "other", "sha256", DB_ID, REF_FILE))),
                ("RESEARCH_PROFILE_LAYOUT_INVALID", lambda rule: spelled(rule, reference_manifest=located(
                    rule, "data", "manifests", REF_POP, "sha256", DB_ID, "other.json"))),
                ("RESEARCH_LOCATION_UNSUPPORTED", lambda rule: spelled(rule, history_database=(
                    f"\\\\server\\share\\sha256\\{HIST_ID}\\national_history.sqlite" if rule == "nt" else
                    "/dev/stdin"))),
                ("RESEARCH_LOCATION_TRAVERSAL", lambda rule: spelled(rule, history_database=located(
                    rule, "data", "..", "h", "sha256", HIST_ID, "national_history.sqlite"))),
                ("RESEARCH_CONFIG_INVALID", lambda rule: spelled(rule, history_database=7)),
                ("RESEARCH_PROFILE_PIN_UNACCEPTED", lambda rule: spelled(
                    rule, expected=dict(HEX, history_identity="0" * 64))),
                ("RESEARCH_LOCATION_NOT_ABSOLUTE", lambda rule: spelled(other[rule]))):
            self.assertEveryHost(dict.fromkeys(self.HOSTS, code), lambda rule, build=build: (config(build(rule)), None))

    def test_omitted_os_name_follows_the_host(self):
        for host in self.HOSTS:
            other = "posix" if host == "nt" else "nt"
            with self.subTest(host=host):
                self.assertEqual("ACCEPTED", self.outcome(config(spelled(host)), host=host, os_name=None), MARKER)
                self.assertEqual("RESEARCH_PROFILE_ID_DUPLICATE", self.outcome(
                    config(spelled(host), spelled(host)), host=host, os_name=None), MARKER)
                self.assertEqual("RESEARCH_LOCATION_NOT_ABSOLUTE", self.outcome(
                    config(spelled(other)), host=host, os_name=None), MARKER)


if __name__ == "__main__":
    unittest.main()
