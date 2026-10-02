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
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo_root.resolve() / "src"))
    from aggie_analytics.validation.retraining_admission import canonical_json, decide, validate_decision

    request = json.loads(args.request.read_text(encoding="utf-8"))
    decision = decide(request)
    failures = validate_decision(decision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_bytes(args.output, canonical_json(decision) + b"\n")
    print(json.dumps({"result": "PASS" if not failures else "FAIL", "action": decision["action"], "decision_identity": decision["decision_identity"], "output": str(args.output.resolve()), "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
