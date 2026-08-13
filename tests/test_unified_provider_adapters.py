from __future__ import annotations

import unittest

from aggie_analytics.assistive_plane.provider_adapters import (
    BGE_MODEL_DIGEST,
    BGE_POLICY_VERSION,
    BGE_PROMPT_VERSION,
    BGE_SCHEMA_SHA256,
    BGE_SCHEMA_VERSION,
    BGE_TASK_FORMAT,
    BgeM3CandidateAdapter,
)


class UnifiedProviderAdapterTests(unittest.TestCase):
    def packet(self) -> dict[str, object]:
        return {
            "task_format": BGE_TASK_FORMAT,
            "model": "bge-m3:latest",
            "model_digest": BGE_MODEL_DIGEST,
            "policy_version": BGE_POLICY_VERSION,
            "prompt_version": BGE_PROMPT_VERSION,
            "route_schema_version": BGE_SCHEMA_VERSION,
            "schema_sha256": BGE_SCHEMA_SHA256,
            "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            "query": "Texas A&M",
            "candidates": [
                {"candidate_id": "aggies", "text": "Texas A&M Aggies football"},
                {"candidate_id": "other", "text": "unrelated weather station"},
            ],
        }

    def test_exact_qualified_bge_route_returns_candidate_rankings(self) -> None:
        def transport(path: str, _body: dict[str, object] | None) -> dict[str, object]:
            if path == "/api/tags":
                return {"models": [{"name": "bge-m3:latest", "digest": BGE_MODEL_DIGEST}]}
            return {"embeddings": [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]}

        result = BgeM3CandidateAdapter(transport=transport).run(self.packet())
        self.assertEqual("aggies", result.result["rankings"][0]["candidate_id"])
        self.assertEqual("REVIEW_ONLY", result.disposition)
        self.assertEqual(0, result.result["canonical_writes"])
        self.assertEqual(0, result.result["protected_decisions"])

    def test_model_digest_change_fails_closed_before_embedding(self) -> None:
        calls = 0

        def transport(_path: str, _body: dict[str, object] | None) -> dict[str, object]:
            nonlocal calls
            calls += 1
            return {}

        packet = self.packet()
        packet["model_digest"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "BGE_EXACT_ROUTE_IDENTITY_MISMATCH:model_digest"):
            BgeM3CandidateAdapter(transport=transport).run(packet)
        self.assertEqual(0, calls)

    def test_live_digest_mismatch_fails_closed(self) -> None:
        def transport(path: str, _body: dict[str, object] | None) -> dict[str, object]:
            if path == "/api/tags":
                return {"models": [{"name": "bge-m3:latest", "digest": "0" * 64}]}
            raise AssertionError("embedding must not execute after live identity mismatch")

        with self.assertRaisesRegex(RuntimeError, "BGE_LIVE_MODEL_DIGEST_NOT_QUALIFIED"):
            BgeM3CandidateAdapter(transport=transport).run(self.packet())


if __name__ == "__main__":
    unittest.main()
