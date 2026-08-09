from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the optional W22 FastAPI snapshot-serving product")
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--freshness-seconds", type=float)
    args = parser.parse_args()
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit('Product extra is not installed. Run: pip install -e ".[product]"') from exc
    from aggie_analytics.api import create_app
    app = create_app(snapshot_root=args.snapshot_root, freshness_seconds=args.freshness_seconds)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
