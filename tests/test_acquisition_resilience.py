from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.data.adapters import (
    AcquisitionFailure,
    AcquisitionRequest,
    AcquisitionRoute,
    FetchResponse,
    ResilientAcquirer,
    RetryPolicy,
)
from aggie_analytics.data.snapshots import RawSnapshotStore


NOW = datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)


class AcquisitionResilienceTests(unittest.TestCase):
    def request(self, source_id: str = "SRC-PRIMARY", uri: str = "https://data.example.test/games"):
        return AcquisitionRequest(
            source_id=source_id,
            dataset="games",
            source_uri=uri,
            identity_components={"season": 2025, "season_type": "regular"},
            extension=".json",
        )

    def test_rate_limit_retry_honors_retry_after_with_bounded_backoff(self) -> None:
        calls = 0
        delays: list[float] = []

        def transport(_request: AcquisitionRequest) -> FetchResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                return FetchResponse(b"", status_code=429, headers={"Retry-After": "12"})
            return FetchResponse(b'[{"game_id":1}]', row_count=1, schema_fields=("game_id",))

        with tempfile.TemporaryDirectory() as directory:
            result = ResilientAcquirer(
                RawSnapshotStore(Path(directory)),
                retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=1, maximum_delay_seconds=5),
                sleeper=delays.append,
            ).acquire(
                (AcquisitionRoute("primary", self.request(), transport),),
                retrieved_at=NOW,
            )

        self.assertEqual(2, calls)
        self.assertEqual([5.0], delays)
        self.assertEqual("RATE_LIMITED", result.attempt_evidence[0]["condition"])
        self.assertEqual(5.0, result.attempt_evidence[0]["delay_seconds"])
        self.assertEqual("SUCCESS", result.attempt_evidence[1]["condition"])

    def test_request_cache_is_immutable_integrity_checked_and_skips_transport(self) -> None:
        request = self.request()
        body = b'[{"game_id":2}]'
        calls = 0

        def transport(_request: AcquisitionRequest) -> FetchResponse:
            nonlocal calls
            calls += 1
            return FetchResponse(body)

        with tempfile.TemporaryDirectory() as directory:
            store = RawSnapshotStore(Path(directory))
            acquirer = ResilientAcquirer(store, sleeper=lambda _delay: None)
            first = acquirer.acquire((AcquisitionRoute("primary", request, transport),), retrieved_at=NOW)
            second = acquirer.acquire((AcquisitionRoute("primary", request, transport),), retrieved_at=NOW)
            payload_path = Path(directory) / first.snapshot.relative_path
            self.assertEqual(hashlib.sha256(body).hexdigest(), first.snapshot.raw_sha256)
            self.assertEqual(body, payload_path.read_bytes())
            self.assertEqual(1, calls)
            self.assertFalse(first.from_cache)
            self.assertTrue(second.from_cache)
            self.assertEqual(first.snapshot.snapshot_id, second.snapshot.snapshot_id)

            different = store.ingest_bytes(
                request.source_id,
                request.dataset,
                b"different",
                retrieved_at=NOW,
                source_uri=request.source_uri,
            )
            with self.assertRaisesRegex(RuntimeError, "immutable request cache collision"):
                store.bind_request(request.identity_sha256, different)

            equivalent_bytes_other_source = store.ingest_bytes(
                "SRC-SUBSTITUTE",
                request.dataset,
                body,
                retrieved_at=NOW,
                source_uri="https://archive.example.test/games",
            )
            self.assertNotEqual(first.snapshot.snapshot_id, equivalent_bytes_other_source.snapshot_id)
            self.assertEqual(first.snapshot.raw_sha256, equivalent_bytes_other_source.raw_sha256)

    def test_fallback_requires_documented_condition_and_preserves_provenance(self) -> None:
        fallback_calls = 0

        def unavailable(_request: AcquisitionRequest) -> FetchResponse:
            return FetchResponse(b"", status_code=404)

        def fallback(_request: AcquisitionRequest) -> FetchResponse:
            nonlocal fallback_calls
            fallback_calls += 1
            return FetchResponse(b'[{"game_id":3}]')

        primary = AcquisitionRoute(
            "primary",
            self.request(),
            unavailable,
            fallback_conditions=frozenset({"HTTP_404"}),
        )
        substitute = AcquisitionRoute(
            "documented-substitute",
            self.request("SRC-SUBSTITUTE", "https://archive.example.test/games"),
            fallback,
        )
        with tempfile.TemporaryDirectory() as directory:
            result = ResilientAcquirer(
                RawSnapshotStore(Path(directory)), sleeper=lambda _delay: None
            ).acquire((primary, substitute), retrieved_at=NOW)

        self.assertEqual(1, fallback_calls)
        self.assertEqual("documented-substitute", result.selected_route_id)
        self.assertEqual("SRC-SUBSTITUTE", result.snapshot.source_id)
        self.assertEqual(("primary",), tuple(result.snapshot.metadata["fallback_from_route_ids"]))
        self.assertEqual("HTTP_404", result.attempt_evidence[0]["condition"])

    def test_undocumented_fallback_condition_fails_the_route(self) -> None:
        fallback_calls = 0

        def fallback(_request: AcquisitionRequest) -> FetchResponse:
            nonlocal fallback_calls
            fallback_calls += 1
            return FetchResponse(b"unexpected")

        routes = (
            AcquisitionRoute("primary", self.request(), lambda _request: FetchResponse(b"", status_code=404)),
            AcquisitionRoute(
                "substitute",
                self.request("SRC-SUBSTITUTE", "https://archive.example.test/games"),
                fallback,
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(AcquisitionFailure, "status 404"):
                ResilientAcquirer(RawSnapshotStore(Path(directory))).acquire(routes, retrieved_at=NOW)
        self.assertEqual(0, fallback_calls)

    def test_request_identity_rejects_credential_material(self) -> None:
        unsafe_uri = self.request(uri="https://data.example.test/games?api_key=not-safe")
        with self.assertRaisesRegex(ValueError, "sensitive query material"):
            _ = unsafe_uri.identity_sha256

        unsafe_component = AcquisitionRequest(
            source_id="SRC-PRIMARY",
            dataset="games",
            source_uri="https://data.example.test/games",
            identity_components={"authorization_token": "not-safe"},
        )
        with self.assertRaisesRegex(ValueError, "sensitive keys"):
            _ = unsafe_component.identity_sha256

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "safe path segment"):
                RawSnapshotStore(Path(directory)).ingest_bytes(
                    "../escape",
                    "games",
                    b"unsafe",
                    retrieved_at=NOW,
                    source_uri="https://data.example.test/games",
                )


if __name__ == "__main__":
    unittest.main()
