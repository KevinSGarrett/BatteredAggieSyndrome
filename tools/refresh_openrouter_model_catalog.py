from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.storage import ContentAddressedStore  # noqa: E402


CATALOG_URL = "https://openrouter.ai/api/v1/models"
ENDPOINTS_URL = "https://openrouter.ai/api/v1/models/qwen/qwen3-coder-next/endpoints"
ZDR_ENDPOINTS_URL = "https://openrouter.ai/api/v1/endpoints/zdr"
DOC_URLS = {
    "responses": "https://openrouter.ai/docs/api_reference/responses/overview",
    "structured_outputs": "https://openrouter.ai/docs/guides/features/structured-outputs",
    "provider_routing": "https://openrouter.ai/docs/guides/routing/provider-selection",
    "zdr": "https://openrouter.ai/docs/guides/features/zdr",
    "usage": "https://openrouter.ai/docs/cookbook/administration/usage-accounting",
    "batch_beta": "https://openrouter.ai/docs/batch-quickstart"
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "AggieAnalytics/0.25 capability-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, default=Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter"))
    args = parser.parse_args()
    store = ContentAddressedStore(args.external_root)
    store.initialize()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    captures: dict[str, dict[str, object]] = {}
    catalog = fetch(CATALOG_URL)
    path, digest, size = store.put_json("runtime", json.loads(catalog))
    captures["model_catalog"] = {"url": CATALOG_URL, "path": str(path), "sha256": digest, "bytes": size}
    endpoint_payload = fetch(ENDPOINTS_URL)
    endpoint_json = json.loads(endpoint_payload)
    path, digest, size = store.put_json("runtime", endpoint_json)
    captures["candidate_endpoints"] = {"url": ENDPOINTS_URL, "path": str(path), "sha256": digest, "bytes": size}
    zdr_payload = fetch(ZDR_ENDPOINTS_URL)
    zdr_json = json.loads(zdr_payload)
    path, digest, size = store.put_json("runtime", zdr_json)
    captures["zdr_endpoints"] = {"url": ZDR_ENDPOINTS_URL, "path": str(path), "sha256": digest, "bytes": size}
    for name, url in DOC_URLS.items():
        payload = fetch(url)
        digest = hashlib.sha256(payload).hexdigest()
        directory = args.external_root / "runtime" / "official_docs" / digest
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{name}.html"
        if not destination.exists():
            destination.write_bytes(payload)
        captures[name] = {"url": url, "path": str(destination), "sha256": digest, "bytes": len(payload)}
    models = json.loads(catalog).get("data", [])
    candidate = next((item for item in models if item.get("id") == "qwen/qwen3-coder-next"), None)
    exact_endpoints = [item for item in endpoint_json.get("data", {}).get("endpoints", []) if item.get("model_id") == "qwen/qwen3-coder-next"]
    exact_zdr = [item for item in zdr_json.get("data", []) if item.get("model_id") == "qwen/qwen3-coder-next"]
    strict_zdr = [item for item in exact_zdr if "structured_outputs" in item.get("supported_parameters", [])]
    manifest = {
        "schema_version": 1,
        "retrieved_at": retrieved_at,
        "paid_provider_calls": 0,
        "paid_spend_usd": "0.000000",
        "captures": captures,
        "candidate_model": "qwen/qwen3-coder-next",
        "candidate_found": candidate is not None,
        "candidate_endpoints": len(exact_endpoints),
        "candidate_zdr_endpoints": len(exact_zdr),
        "candidate_strict_structured_output_zdr_endpoints": len(strict_zdr),
        "candidate_state": "PAID_CAPABILITY_PILOT_AUTHORIZED_NOT_ROUTE_APPROVED",
        "route_approval_pending": ["STRICT_SCHEMA_CAPABILITY_PROBE", "EMPIRICAL_PILOT"],
        "batch_state": "DISABLED_PENDING_SEPARATE_BETA_PRIVACY_ZDR_RETENTION_SCHEMA_ACCOUNTING_EMPIRICAL_GATE"
    }
    manifest_path, manifest_sha, _ = store.put_json("manifests", manifest)
    print(json.dumps({"manifest_path": str(manifest_path), "manifest_sha256": manifest_sha, "candidate_found": candidate is not None}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
