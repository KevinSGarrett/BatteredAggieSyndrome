from __future__ import annotations

import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "annotated-types": "0.8.0",
    "anyio": "4.14.2",
    "certifi": "2026.7.22",
    "colorama": "0.4.6",
    "distro": "1.9.0",
    "h11": "0.16.0",
    "httpcore": "1.0.9",
    "httpx": "0.28.1",
    "idna": "3.18",
    "jiter": "0.16.0",
    "openai": "2.53.0",
    "pydantic": "2.13.4",
    "pydantic-core": "2.46.4",
    "sniffio": "1.3.1",
    "tqdm": "4.70.0",
    "typing-extensions": "4.16.0",
    "typing-inspection": "0.4.2",
}


def release_hashes(name: str, version: str) -> list[str]:
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    request = urllib.request.Request(url, headers={"User-Agent": "BAS-lock-generator/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    hashes = sorted({item["digests"]["sha256"] for item in payload["urls"]})
    if not hashes or any(len(value) != 64 for value in hashes):
        raise RuntimeError(f"missing or invalid PyPI hashes for {name}=={version}")
    return hashes


def main() -> int:
    lines = [
        "# OpenAI assistive-plane optional dependency lock.",
        "# Exact versions and all published PyPI release-file SHA-256 identities.",
        "# Install with: python -m pip install --require-hashes -r requirements/openai-assist.lock",
    ]
    for name, version in PINS.items():
        hashes = release_hashes(name, version)
        lines.append(f"{name}=={version} \\")
        for index, digest in enumerate(hashes):
            suffix = " \\" if index + 1 < len(hashes) else ""
            lines.append(f"    --hash=sha256:{digest}{suffix}")
    destination = ROOT / "requirements" / "openai-assist.lock"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {destination} packages={len(PINS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
