from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.data.adapters import AcquisitionFailure
from aggie_analytics.data.cfbd import (
    CFBDTransport,
    acquisition_request,
    inspect_json_rows,
    load_dotenv_value,
    public_uri,
)
from aggie_analytics.data.http import PublicHTTPTransport
from aggie_analytics.data.roster_reconciliation import normalize_identity_text, resolve_roster_identity


class CFBDHistoricalAcquisitionTests(unittest.TestCase):
    def test_public_uri_and_request_identity_are_stable_and_credential_free(self) -> None:
        uri = public_uri("/roster", {"year": 2025, "classification": "fbs"})
        self.assertEqual(
            "https://api.collegefootballdata.com/roster?classification=fbs&year=2025", uri
        )
        first = acquisition_request(
            endpoint_id="CFBD-GetRoster",
            path="/roster",
            parameters={"year": 2025, "classification": "fbs"},
            run_id="bounded-test-v1",
        )
        second = acquisition_request(
            endpoint_id="CFBD-GetRoster",
            path="/roster",
            parameters={"classification": "fbs", "year": 2025},
            run_id="bounded-test-v1",
        )
        self.assertEqual(first.identity_sha256, second.identity_sha256)
        self.assertNotIn("token", first.source_uri.lower())
        self.assertNotIn("key", first.source_uri.lower())

    def test_json_population_and_schema_are_measured_not_assumed(self) -> None:
        rows, fields = inspect_json_rows(b'[{"id":1,"team":"A"},{"id":2,"position":"QB"}]')
        self.assertEqual(2, rows)
        self.assertEqual(("id", "position", "team"), fields)
        with self.assertRaisesRegex(AcquisitionFailure, "object array"):
            inspect_json_rows(b'{"id":1}')
        with self.assertRaisesRegex(AcquisitionFailure, "valid JSON"):
            inspect_json_rows(b'not-json')

    def test_dotenv_reads_only_requested_nonempty_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OTHER_SECRET=do-not-read\nCFBD_API_KEY='configured'\n", encoding="utf-8")
            self.assertEqual("configured", load_dotenv_value(path, "CFBD_API_KEY"))
            with self.assertRaisesRegex(RuntimeError, "not configured"):
                load_dotenv_value(path, "MISSING")
            path.write_text("CFBD_API_KEY=\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "empty"):
                load_dotenv_value(path, "CFBD_API_KEY")

    def test_transport_requires_nonempty_token_and_never_serializes_it(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonempty"):
            CFBDTransport("")
        transport = CFBDTransport("secret-value")
        request = acquisition_request(
            endpoint_id="CFBD-GetRoster",
            path="/roster",
            parameters={"year": 2025},
            run_id="bounded-test-v1",
        )
        self.assertNotIn("secret-value", repr(transport))
        self.assertNotIn("secret-value", repr(request))
        self.assertNotIn("secret-value", json.dumps(request.identity_components))

    def test_public_transport_has_no_credential_surface(self) -> None:
        transport = PublicHTTPTransport(timeout_seconds=15)
        self.assertEqual(15, transport.timeout_seconds)
        self.assertNotIn("token", repr(transport).lower())
        with self.assertRaisesRegex(ValueError, "positive"):
            PublicHTTPTransport(timeout_seconds=0)

    def test_roster_reconciliation_requires_source_id_name_and_membership(self) -> None:
        mappings = {"42": {"player_42"}}
        names = {"player_42": {("jose", "o neal")}}
        memberships = {("42", 2025, "texas a m"): {("player_42", "team_tamu")}}
        exact = resolve_roster_identity(
            athlete_id=42, season=2025, first_name="José", last_name="O'Neal",
            team_label="Texas A&M", source_mappings=mappings, canonical_names=names,
            memberships=memberships,
        )
        self.assertEqual("CANDIDATE_EXACT_SOURCE_ID_NAME_AND_CANONICAL_MEMBERSHIP", exact.disposition)
        self.assertEqual("player_42", exact.canonical_player_id)
        self.assertEqual("team_tamu", exact.canonical_team_id)
        self.assertFalse(exact.quarantine)

        conflict = resolve_roster_identity(
            athlete_id=42, season=2025, first_name="Different", last_name="Person",
            team_label="Texas A&M", source_mappings=mappings, canonical_names=names,
            memberships=memberships,
        )
        self.assertEqual("QUARANTINE_SOURCE_ID_NAME_CONFLICT", conflict.disposition)
        self.assertTrue(conflict.quarantine)

    def test_roster_source_level_rows_remain_candidates_not_name_merges(self) -> None:
        result = resolve_roster_identity(
            athlete_id=99, season=2025, first_name="Same", last_name="Name",
            team_label="Example", source_mappings={}, canonical_names={}, memberships={},
        )
        self.assertEqual("CANDIDATE_SOURCE_LEVEL_ONLY", result.disposition)
        self.assertIsNone(result.canonical_player_id)
        self.assertFalse(result.quarantine)
        self.assertEqual("texas a m", normalize_identity_text("Texas A&M"))


if __name__ == "__main__":
    unittest.main()
