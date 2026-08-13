from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.queue_cpu_worker_manifest_work import build_packet
from tools.queue_unified_assistive_work import queue_packet


class CpuWorkerManifestQueueTests(unittest.TestCase):
    def test_builds_content_addressed_candidate_only_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifests = root / "manifests"
            source = manifests / "acquisition" / "2021" / "ncaa_team_graph_discovery_manifest.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps({"season": 2021, "teams": 653}), encoding="utf-8")
            packet = build_packet(source, manifests)
            packet_source = root / "packet.json"
            packet_source.write_text(json.dumps(packet), encoding="utf-8")
            destination, digest = queue_packet(packet_source, root / "queue")

            self.assertTrue(destination.is_file())
            self.assertEqual(digest, destination.stem)
            self.assertEqual("remote_cpu_worker", packet["provider"])
            self.assertEqual("CANONICAL_JSON", packet["task"])
            self.assertEqual("BAT-563", packet["jira_unit"])
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(), packet["source_hashes"][0]
            )
            self.assertNotIn(str(root), packet["scope"])
            self.assertEqual(
                "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES", packet["authority"]
            )

    def test_rejects_manifest_outside_allowlisted_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifests = root / "manifests"
            manifests.mkdir()
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "OUTSIDE_ALLOWLIST"):
                build_packet(outside, manifests)

    def test_queue_rejects_broadened_cpu_task(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet = {
                "schema_version": 1,
                "provider": "remote_cpu_worker",
                "task": "SHELL",
                "task_format": "cpu_worker_canonical_manifest_v1",
                "jira_unit": "BAT-563",
                "schema_sha256": "a" * 64,
                "source_hashes": ["b" * 64],
                "pre_routing_effort_points": 1,
                "payload": {"value": {}},
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            source = root / "packet.json"
            source.write_text(json.dumps(packet), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CPU_PACKET_INVALID"):
                queue_packet(source, root / "queue")
