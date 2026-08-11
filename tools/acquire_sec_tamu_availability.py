from __future__ import annotations

"""Acquire immutable official and timestamped SEC/A&M availability evidence."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.sec_availability import sha256_bytes, stable_hash, utc_now  # noqa: E402


USER_AGENT = "AggieAnalyticsEngine-private-research/1.0"


def fetch(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            return {
                "ok": True,
                "url": response.geturl(),
                "status": int(response.status),
                "content_type": response.headers.get("Content-Type", "application/octet-stream"),
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "url": url,
            "status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "error": f"HTTP_{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "url": url,
            "status": None,
            "content_type": "",
            "error": type(exc).__name__,
        }


def extension_for(content_type: str, url: str) -> str:
    normalized = content_type.lower()
    if "json" in normalized:
        return ".json"
    if "html" in normalized:
        return ".html"
    if "pdf" in normalized or urllib.parse.urlparse(url).path.lower().endswith(".pdf"):
        return ".pdf"
    return ".bin"


def atomic_write(path: Path, body: bytes) -> None:
    if path.is_file():
        if path.read_bytes() != body:
            raise RuntimeError(f"immutable payload collision: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(body)
        os.replace(temporary, path)
    finally:
        if temporary.is_file():
            temporary.unlink()


def preserve_response(data_root: Path, source_id: str, captured_at: str, response: dict[str, Any]) -> dict[str, Any]:
    body = response.pop("body")
    digest = sha256_bytes(body)
    extension = extension_for(response["content_type"], response["url"])
    path = data_root / "raw" / "historical_known_at" / "sec_availability" / "sha256" / digest / f"payload{extension}"
    atomic_write(path, body)
    return {
        "source_record_id": source_id,
        "captured_at_utc": captured_at,
        "response_url": response["url"],
        "http_status": response["status"],
        "content_type": response["content_type"],
        "response_bytes": len(body),
        "response_sha256": digest,
        "immutable_path": path.relative_to(data_root).as_posix(),
    }


def acquire_archive(data_root: Path, source: dict[str, Any], captured_at: str) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    page = fetch(source["url"])
    if not page["ok"]:
        return {"source_record_id": source["source_record_id"], "route_type": source["route_type"], "state": "ACQUISITION_FAILED", "failure": page}
    page_body = page["body"]
    stages.append(preserve_response(data_root, source["source_record_id"] + "-PAGE", captured_at, page))
    text = page_body.decode("utf-8", errors="replace")
    iframe_match = re.search(r"https://confinjrepxyz\.hdintelligence-app\.com[^\"'< ]*", text)
    if not iframe_match:
        return {"source_record_id": source["source_record_id"], "route_type": source["route_type"], "state": "ARCHIVE_ROUTE_DISCOVERY_FAILED", "captures": stages}
    iframe_url = iframe_match.group(0).replace("&amp;", "&").replace("&quot;", "").replace("\\&", "&")
    shell = fetch(iframe_url)
    if not shell["ok"]:
        return {"source_record_id": source["source_record_id"], "route_type": source["route_type"], "state": "ARCHIVE_SHELL_FAILED", "captures": stages, "failure": shell}
    shell_body = shell["body"]
    stages.append(preserve_response(data_root, source["source_record_id"] + "-SHELL", captured_at, shell))
    shell_text = shell_body.decode("utf-8", errors="replace")
    main_match = re.search(r'src=["\']([^"\']*?/static/js/main\.[^"\']+?\.js)["\']', shell_text)
    if not main_match:
        return {"source_record_id": source["source_record_id"], "route_type": source["route_type"], "state": "ARCHIVE_BUNDLE_DISCOVERY_FAILED", "captures": stages}
    origin = "https://confinjrepxyz.hdintelligence-app.com"
    main_url = urllib.parse.urljoin(origin, main_match.group(1))
    main = fetch(main_url)
    if not main["ok"]:
        return {"source_record_id": source["source_record_id"], "route_type": source["route_type"], "state": "ARCHIVE_MAIN_BUNDLE_FAILED", "captures": stages, "failure": main}
    main_body = main.pop("body")
    main_text = main_body.decode("utf-8", errors="replace")
    chunk_match = re.search(r'228:["\']([a-f0-9]+)["\']', main_text)
    if not chunk_match:
        return {
            "source_record_id": source["source_record_id"],
            "route_type": source["route_type"],
            "state": "ARCHIVE_CHUNK_DISCOVERY_FAILED",
            "captures": stages,
            "transient_main_bundle_sha256": sha256_bytes(main_body),
            "transient_main_bundle_bytes": len(main_body),
        }
    chunk_url = f"{origin}/static/js/228.{chunk_match.group(1)}.chunk.js"
    chunk = fetch(chunk_url)
    if not chunk["ok"]:
        return {"source_record_id": source["source_record_id"], "route_type": source["route_type"], "state": "ARCHIVE_CHUNK_FAILED", "captures": stages, "failure": chunk}
    chunk_body = chunk.pop("body")
    chunk_text = chunk_body.decode("utf-8", errors="replace")
    key_match = re.search(r'headers:\{["\']x-api-key["\']:["\']([^"\']+)["\']\}', chunk_text)
    endpoint_match = re.search(r'\.get\(["\'](/api/archive)["\']', chunk_text)
    if not key_match or not endpoint_match:
        return {
            "source_record_id": source["source_record_id"],
            "route_type": source["route_type"],
            "state": "ARCHIVE_API_DISCOVERY_FAILED",
            "captures": stages,
            "transient_main_bundle_sha256": sha256_bytes(main_body),
            "transient_main_bundle_bytes": len(main_body),
            "transient_chunk_sha256": sha256_bytes(chunk_body),
            "transient_chunk_bytes": len(chunk_body),
        }
    # The public browser-client token is deliberately held only in memory and is never serialized or logged.
    api = fetch(urllib.parse.urljoin(origin, endpoint_match.group(1)), headers={"x-api-key": key_match.group(1)})
    if not api["ok"]:
        return {"source_record_id": source["source_record_id"], "route_type": source["route_type"], "state": "ARCHIVE_API_FAILED", "captures": stages, "failure": api}
    api_body = api["body"]
    stages.append(preserve_response(data_root, source["source_record_id"] + "-API", captured_at, api))
    try:
        archive_payload = json.loads(api_body)
        archive_records = len(archive_payload) if isinstance(archive_payload, (list, dict)) else None
    except json.JSONDecodeError:
        archive_records = None
    return {
        "source_record_id": source["source_record_id"],
        "route_type": source["route_type"],
        "state": "CAPTURED_EMPTY_ARCHIVE" if archive_records == 0 else "CAPTURED_ARCHIVE",
        "archive_records": archive_records,
        "captures": stages,
        "transient_main_bundle_sha256": sha256_bytes(main_body),
        "transient_main_bundle_bytes": len(main_body),
        "transient_chunk_sha256": sha256_bytes(chunk_body),
        "transient_chunk_bytes": len(chunk_body),
        "public_client_token_persisted": False,
    }


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=REPO_ROOT / "configs" / "sec_tamu_availability_recovery_contract.json")
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    args = parser.parse_args()
    contract_path = args.contract.resolve()
    data_root = args.data_root.resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    captured_at = utc_now()
    records: list[dict[str, Any]] = []
    for source in contract["sources"]:
        if source["route_type"] == "OFFICIAL_ARCHIVE_ROUTE":
            records.append(acquire_archive(data_root, source, captured_at))
            continue
        response = fetch(source["url"])
        if response["ok"]:
            records.append(
                {
                    "source_record_id": source["source_record_id"],
                    "route_type": source["route_type"],
                    "state": "CAPTURED",
                    "captures": [preserve_response(data_root, source["source_record_id"], captured_at, response)],
                }
            )
        else:
            records.append(
                {
                    "source_record_id": source["source_record_id"],
                    "route_type": source["route_type"],
                    "state": "ACQUISITION_FAILED",
                    "failure": response,
                }
            )
    core = {
        "schema_version": "1.0.0",
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256_bytes(contract_path.read_bytes()),
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "producer_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "captured_at_utc": captured_at,
        "sources": records,
        "source_states": {record["source_record_id"]: record["state"] for record in records},
        "credentials_persisted": False,
    }
    identity = stable_hash(core)
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / "sec_tamu_availability_acquisition_manifest.json"
    manifest = {**core, "acquisition_identity": identity}
    atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(
        json.dumps(
            {
                "acquisition_identity": identity,
                "manifest_path": str(manifest_path),
                "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
                "source_states": core["source_states"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
