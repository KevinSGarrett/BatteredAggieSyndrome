"""Report contracts whose pinned repo-relative input digests have gone stale.

A contract pins an input by pairing a "<name>_relative_path" key with a
"<name>_sha256" key. When a later cycle legitimately supersedes one of those
tracked inputs, the pin has to be rebound in the same change. If it is not, the
drift surfaces far from its cause -- as a setUpClass error in whichever suite
happens to load the contract -- so this validator reports it directly instead.

Only pins that resolve under a tracked repository directory are checked. Pins
that address the external data root are reported separately and are not
failures, because the data root is not present in every checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
PATH_SUFFIXES = ("_relative_path", "_relative", "_path")
REPO_PREFIXES = (
    "artifacts/",
    "configs/",
    "docs/",
    "jira/",
    "provenance/",
    "src/",
    "tests/",
    "tools/",
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_pins(node: Any) -> Iterator[tuple[str, str]]:
    """Yield (relative_path, pinned_sha256) for every paired pin in the document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key.endswith("_sha256") and isinstance(value, str):
                stem = key[: -len("_sha256")]
                for suffix in PATH_SUFFIXES:
                    relative = node.get(stem + suffix)
                    if isinstance(relative, str):
                        yield relative.replace("\\", "/"), value
                        break
            yield from iter_pins(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_pins(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    repo_root: Path = args.repo_root.resolve()

    checked = 0
    external = 0
    drifted: list[str] = []
    absent: list[str] = []

    for contract in sorted((repo_root / "configs").rglob("*.json")):
        try:
            document = json.loads(contract.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for relative, pinned in iter_pins(document):
            if not relative.startswith(REPO_PREFIXES):
                external += 1
                continue
            target = repo_root / relative
            name = contract.relative_to(repo_root).as_posix()
            if not target.is_file():
                absent.append(f"{name}: pinned repository input is missing: {relative}")
                continue
            checked += 1
            actual = sha256_of(target)
            if actual != pinned:
                drifted.append(
                    f"{name}: {relative}\n      pinned : {pinned}\n      actual : {actual}"
                )

    print(f"repository-relative input pins checked: {checked}")
    print(f"data-root input pins skipped: {external}")

    if absent or drifted:
        for message in absent:
            print(f"- MISSING {message}")
        for message in drifted:
            print(f"- DRIFTED {message}")
        print(f"FAIL: {len(absent) + len(drifted)} stale contract input pin(s)")
        return 1

    print("PASS: every pinned repository input digest matches its tracked file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
