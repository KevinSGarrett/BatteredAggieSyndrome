from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_product_supply_chain import lock_policy_errors, normalize_name  # noqa: E402


_DIRECT_PIN_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)$"
)


def dependency_policy_errors(root: Path) -> tuple[int, int, list[str]]:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    base = data["project"].get("dependencies", [])
    product = data["project"].get("optional-dependencies", {}).get("product", [])
    failures: list[str] = []
    direct: dict[str, str] = {}
    if base:
        failures.append("base dependencies must remain empty at W23")
    for dependency in product:
        match = _DIRECT_PIN_RE.fullmatch(str(dependency).strip())
        if not match:
            failures.append(f"product dependency is not one exact pin: {dependency}")
            continue
        name, version = match.groups()
        normalized = normalize_name(name)
        if normalized in direct:
            failures.append(f"duplicate direct product dependency: {normalized}")
        direct[normalized] = version

    entries, lock_failures = lock_policy_errors(root / "requirements" / "product.lock")
    failures.extend(f"product lock: {failure}" for failure in lock_failures)
    locked = {entry.normalized_name: entry.version for entry in entries}
    for name, version in sorted(direct.items()):
        if name not in locked:
            failures.append(f"missing lock pin for {name}=={version}")
        elif locked[name] != version:
            failures.append(
                f"direct/lock version mismatch for {name}: {version} != {locked[name]}"
            )
    return len(direct), len(entries), failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    direct_count, lock_count, failures = dependency_policy_errors(args.repo_root.resolve())
    if failures:
        print("FAIL: dependency policy")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "PASS: dependency policy "
        f"({direct_count} direct product pins; {lock_count} hash-locked entries)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
