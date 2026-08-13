from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.queue_cpu_worker_manifest_work import build_packet
from tools.queue_cpu_worker_text_work import build_packet as build_text_packet
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

    def test_builds_exact_line_hash_and_text_dedup_packets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifests = root / "manifests"
            source = manifests / "historical" / "run.json"
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps(
                    {
                        "season": 2022,
                        "teams": ["Texas A&M", "  texas a&m  ", "LSU"],
                        "status": "complete",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            line_packet = build_text_packet(source, manifests, "line-hash")
            dedup_packet = build_text_packet(source, manifests, "exact-text-dedup")

            self.assertEqual("LINE_HASH_MANIFEST", line_packet["task"])
            self.assertEqual("cpu_worker_line_hash_manifest_v1", line_packet["task_format"])
            self.assertEqual(source.read_text(encoding="utf-8").splitlines(), line_packet["payload"]["lines"])
            self.assertEqual("EXACT_TEXT_DEDUP", dedup_packet["task"])
            self.assertEqual("cpu_worker_exact_text_dedup_v1", dedup_packet["task_format"])
            self.assertEqual(
                ["/status", "/teams/0", "/teams/1", "/teams/2"],
                [record["id"] for record in dedup_packet["payload"]["records"]],
            )
            self.assertNotIn(str(root), line_packet["scope"])
            self.assertNotIn(str(root), dedup_packet["scope"])

            for index, packet in enumerate((line_packet, dedup_packet)):
                packet_source = root / f"packet-{index}.json"
                packet_source.write_text(json.dumps(packet), encoding="utf-8")
                destination, digest = queue_packet(packet_source, root / "queue")
                self.assertTrue(destination.is_file())
                self.assertEqual(digest, destination.stem)

    def test_text_routes_reject_outside_empty_and_over_record_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifests = root / "manifests"
            manifests.mkdir()
            outside = root / "outside.json"
            outside.write_text('{"text":"outside"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "OUTSIDE_ALLOWLIST"):
                build_text_packet(outside, manifests, "exact-text-dedup")

            no_strings = manifests / "no-strings.json"
            no_strings.write_text('{"value":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "NO_STRING_RECORDS"):
                build_text_packet(no_strings, manifests, "exact-text-dedup")

            too_many = manifests / "too-many.txt"
            too_many.write_text("\n".join("line" for _ in range(10_001)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "RECORD_LIMIT"):
                build_text_packet(too_many, manifests, "line-hash")

    def test_queue_rejects_cpu_task_format_or_schema_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet = {
                "schema_version": 1,
                "provider": "remote_cpu_worker",
                "task": "EXACT_TEXT_DEDUP",
                "task_format": "cpu_worker_line_hash_manifest_v1",
                "jira_unit": "BAT-563",
                "schema_sha256": "a" * 64,
                "source_hashes": ["b" * 64],
                "pre_routing_effort_points": 1,
                "payload": {"records": [{"id": "one", "text": "Texas A&M"}]},
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            source = root / "packet.json"
            source.write_text(json.dumps(packet), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CPU_PACKET_INVALID"):
                queue_packet(source, root / "queue")
