from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--claims-path", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo_root.resolve() / "src"))
    from aggie_analytics.validation.evaluation_exposure import (
        build_ledger,
        canonical_json,
        validate_claims,
        validate_ledger,
    )

    data_root = args.data_root.resolve()
    ledger = build_ledger(data_root)
    failures = validate_ledger(ledger)
    claims = []
    if args.claims_path:
        claims = json.loads(args.claims_path.read_text(encoding="utf-8"))
        failures.extend(validate_claims(claims, ledger))
    output = (
        data_root
        / "manifests/evaluation_exposure/sha256"
        / ledger["ledger_identity"]
        / "evaluation_exposure_ledger.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_bytes(output, canonical_json(ledger) + b"\n")
    result = {
        "result": "PASS" if not failures else "FAIL",
        "ledger_identity": ledger["ledger_identity"],
        "record_count": ledger["record_count"],
        "ledger_path": str(output),
        "failures": failures,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
