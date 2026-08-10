from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.controller import AssistiveController  # noqa: E402


PLAY_TYPE_CODES = {
    "Pass Completion": "PASS_COMPLETION",
    "Rush": "RUSH",
    "Punt Return": "PUNT_RETURN",
    "Blocked Field Goal": "BLOCKED_FIELD_GOAL",
    "Interception Return Touchdown": "INTERCEPTION_RETURN_TOUCHDOWN",
}


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lookup(payload: dict[str, Any], dotted_path: str) -> Any:
    value: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise SystemExit(f"missing configured JSON field: {dotted_path}")
        value = value[part]
    return value


def _transform(value: Any, name: str | None) -> Any:
    if name is None or name == "STRING":
        return value
    if name == "PLAY_TYPE_CODE":
        if value not in PLAY_TYPE_CODES:
            raise SystemExit(f"unregistered play type in deterministic gold: {value}")
        return PLAY_TYPE_CODES[value]
    if name == "INT":
        return int(value)
    if name == "INT_COMMAS":
        return int(str(value).replace(",", ""))
    raise SystemExit(f"unsupported deterministic transform: {name}")


def _source_paths(controller: AssistiveController, config: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key, source in config["sources"].items():
        path = controller.store.root.parent / source["external_relative_path"]
        if not path.is_file():
            raise SystemExit(f"configured gamebook pilot source is absent: {key}")
        if _sha(path) != source["sha256"]:
            raise SystemExit(f"gamebook pilot source capture hash mismatch: {key}")
        paths[key] = path
    return paths


def _parquet_rows(samples: list[dict[str, Any]], paths: dict[str, Path]) -> dict[str, dict[int, dict[str, Any]]]:
    parquet_samples = [sample for sample in samples if sample["extractor"]["type"] == "parquet_play"]
    if not parquet_samples:
        return {}
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pyarrow is required to prepare the external gamebook pilot corpus") from exc
    grouped: dict[str, list[dict[str, Any]]] = {}
    for sample in parquet_samples:
        grouped.setdefault(sample["source"], []).append(sample)
    result: dict[str, dict[int, dict[str, Any]]] = {}
    for source_key, group in grouped.items():
        wanted = {int(sample["extractor"]["play_id"]) for sample in group}
        columns = {"id", "text"}
        for sample in group:
            columns.update(fact["column"] for fact in sample["facts"])
        rows = pq.read_table(paths[source_key], columns=sorted(columns)).to_pylist()
        selected = {int(row["id"]): row for row in rows if int(row["id"]) in wanted}
        if set(selected) != wanted:
            raise SystemExit(f"one or more configured play IDs are absent from {source_key}")
        result[source_key] = selected
    return result


def _extract_case(
    sample: dict[str, Any],
    path: Path,
    parquet_rows: dict[str, dict[int, dict[str, Any]]],
) -> tuple[str, Any]:
    extractor = sample["extractor"]
    kind = extractor["type"]
    if kind == "parquet_play":
        row = parquet_rows[sample["source"]][int(extractor["play_id"])]
        return str(row["text"]), row
    if kind == "pdf_page_lines":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise SystemExit("pypdf is required to prepare the official gamebook gold") from exc
        reader = PdfReader(path)
        page_number = int(extractor["page"])
        if page_number < 1 or page_number > len(reader.pages):
            raise SystemExit(f"configured PDF page is absent: {page_number}")
        lines = (reader.pages[page_number - 1].extract_text() or "").splitlines()
        start = int(extractor["start_line"])
        end = int(extractor["end_line"])
        if start < 0 or end < start or end >= len(lines):
            raise SystemExit(f"configured PDF line range is invalid: {sample['case_id']}")
        return "\n".join(lines[start : end + 1]), None
    if kind == "html_text_range":
        parser = _VisibleTextParser()
        parser.feed(path.read_text(encoding="utf-8", errors="strict"))
        text = "\n".join(parser.parts)
        start = text.find(extractor["start"])
        if start < 0:
            raise SystemExit(f"configured HTML start anchor is absent: {sample['case_id']}")
        end = text.find(extractor["end"], start + len(extractor["start"]))
        if end < 0:
            raise SystemExit(f"configured HTML end anchor is absent: {sample['case_id']}")
        return text[start:end].rstrip(), None
    if kind == "json_fields":
        payload = json.loads(path.read_text(encoding="utf-8"))
        selected = {field: _lookup(payload, field) for field in extractor["fields"]}
        return json.dumps(selected, indent=2, ensure_ascii=False, sort_keys=True), payload
    raise SystemExit(f"unsupported gamebook pilot extractor: {kind}")


def _expected_fact(fact: dict[str, Any], excerpt: str, context: Any) -> Any:
    if "column" in fact:
        value = context[fact["column"]]
    elif "regex" in fact:
        match = re.search(fact["regex"], excerpt, flags=re.MULTILINE)
        if match is None or match.lastindex != 1:
            raise SystemExit(f"configured fact regex did not yield one group: {fact['field']}")
        value = match.group(1)
    elif "json_path" in fact:
        value = _lookup(context, fact["json_path"])
    elif "value" in fact:
        required = fact.get("require_regex")
        if required and re.search(required, excerpt, flags=re.MULTILINE) is None:
            raise SystemExit(f"configured literal fact lacks source evidence: {fact['field']}")
        value = fact["value"]
    else:
        raise SystemExit(f"fact has no deterministic gold route: {fact['field']}")
    return _transform(value, fact.get("transform"))


def main() -> int:
    config = json.loads((ROOT / "configs" / "openai_gamebook_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    paths = _source_paths(controller, config)
    parquet_rows = _parquet_rows(config["samples"], paths)
    gold: list[dict[str, Any]] = []
    covered_domains: set[str] = set()
    for sample in config["samples"]:
        source = config["sources"][sample["source"]]
        excerpt, context = _extract_case(sample, paths[sample["source"]], parquet_rows)
        capture_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        expected = [
            {
                "field": fact["field"],
                "value": _expected_fact(fact, excerpt, context),
                "status": "SUPPORTED",
                "evidence_locators": ["text:1"],
            }
            for fact in sample["facts"]
        ]
        domains = sorted(set(sample["domains"]))
        covered_domains.update(domains)
        gold.append(
            {
                "case_id": sample["case_id"],
                "category": sample["category"],
                "domains": domains,
                "source_key": sample["source"],
                "source_url": source["source_url"],
                "source_payload_sha256": source["sha256"],
                "source_capture_sha256": capture_sha256,
                "source_excerpt": excerpt,
                "expected_facts": expected,
            }
        )
    required_domains = set(config["required_domains"])
    if covered_domains != required_domains:
        raise SystemExit(
            "gamebook pilot domain coverage mismatch: "
            f"missing={sorted(required_domains - covered_domains)} extra={sorted(covered_domains - required_domains)}"
        )
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for row in gold
    ).encode("utf-8")
    artifact = controller.store.put_bytes("evals", payload, suffix=".gamebook-gold.jsonl")
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 2,
            "artifact_type": "openai_gamebook_pilot_gold",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "sources": [
                {
                    "source_key": key,
                    "source_id": source["source_id"],
                    "source_url": source["source_url"],
                    "source_capture_sha256": source["sha256"],
                    "source_acquired_at_utc": source["acquired_at_utc"],
                }
                for key, source in sorted(config["sources"].items())
            ],
            "gold_sha256": artifact.sha256,
            "gold_bytes": artifact.bytes,
            "sample_count": len(gold),
            "case_ids": sorted(row["case_id"] for row in gold),
            "categories": sorted({row["category"] for row in gold}),
            "required_domains": sorted(required_domains),
            "covered_domains": sorted(covered_domains),
            "raw_source_and_excerpts_outside_git": True,
            "final_disposition": "SHADOW_GOLD_ONLY",
        },
    )
    print(
        json.dumps(
            {
                "gold_path": str(artifact.path),
                "gold_sha256": artifact.sha256,
                "manifest_path": str(manifest.path),
                "manifest_sha256": manifest.sha256,
                "samples": len(gold),
                "covered_domains": sorted(covered_domains),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
