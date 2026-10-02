"""Cycle #37 - Attempt #2 - ACTUAL_STATE

One bounded, receipted GET against a free public page, for the named rework
attempt's declared request classes.

Before a request is made the class ceiling in ``COST_AND_AUTHORITY_LEDGER.json``
is read and enforced, and a route (scheme, host and path) that has already
failed twice is refused: the assignment says to stop an equivalent failing
route after two tries. The response body is stored privately under the
attempt's ``private/acquisition/<class>/`` by its SHA-256 with a metadata
record, and the ledger gains one request entry and one count. Nothing here
bypasses an access control: a 401, 403 or challenge page is recorded as what
it is and not retried around.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
LEDGER = ATTEMPT / "COST_AND_AUTHORITY_LEDGER.json"
CLASSES = ("coaching", "availability", "games", "metadata")
USER_AGENT = "BAS-research/37 (one read of a public page; contact via repository owner)"


class FetchRefused(RuntimeError):
    """The request would exceed a ceiling or repeat a twice-failed route."""


def route_of(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc.lower()}{parts.path}"


def fetch(url: str, request_class: str, purpose: str, *, ledger_path: Path = LEDGER,
          timeout: float = 30.0) -> dict[str, Any]:
    if request_class not in CLASSES:
        raise FetchRefused(f"unknown request class {request_class!r}")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    network = ledger.setdefault("network", {})
    used = int(network.get(f"{request_class}_requests") or 0)
    ceiling = int(network.get(f"{request_class}_ceiling") or 0)
    if used >= ceiling:
        raise FetchRefused(f"{request_class} ceiling {ceiling} reached ({used} used)")
    failures = network.setdefault("failed_routes", {})
    route = route_of(url)
    if int(failures.get(route, 0)) >= 2:
        raise FetchRefused(f"route {route} already failed twice; not retried")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    started = datetime.now(timezone.utc).isoformat()
    status: int | None = None
    body = b""
    error = None
    headers: dict[str, str] = {}
    final_url = url
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
            headers = {k.lower(): v for k, v in response.headers.items()}
            final_url = response.geturl()
    except urllib.error.HTTPError as http_error:
        status = http_error.code
        body = http_error.read() or b""
        error = f"HTTP {http_error.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as other:
        error = f"{type(other).__name__}: {other}"
    ok = status is not None and 200 <= status < 300 and body
    if not ok:
        failures[route] = int(failures.get(route, 0)) + 1
    digest = hashlib.sha256(body).hexdigest() if body else None
    store = ATTEMPT / "private" / "acquisition" / request_class
    store.mkdir(parents=True, exist_ok=True)
    if body:
        _bas_atomic.write_bytes(store / f"{digest}.bin", body)
    record = {"url": url, "final_url": final_url, "route": route, "class": request_class, "purpose": purpose,
              "requested_at_utc": started, "http_status": status, "error": error,
              "content_type": headers.get("content-type"), "last_modified": headers.get("last-modified"),
              "bytes": len(body), "sha256": digest, "stored": str(store / f"{digest}.bin") if body else None,
              "read_only": True}
    _bas_atomic.write_text(store / f"{(digest or hashlib.sha256(url.encode()).hexdigest())}.meta.json", 
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    network[f"{request_class}_requests"] = used + 1
    network.setdefault("requests", []).append(record)
    _bas_atomic.write_text(ledger_path, json.dumps(ledger, indent=1) + "\n", encoding="utf-8")
    return record


def record_render(url: str, request_class: str, purpose: str, payload: bytes, *, rendered_utc: str,
                  ledger_path: Path = LEDGER, method: str = "BROWSER_RENDER_DOM_TEXT") -> dict[str, Any]:
    """Receipt one browser render of a public page as one request of its class.

    The built-in browser loads the page as any reader would; what is stored is
    the rendered text the page displayed, read from its DOM. A render counts
    against the same ceiling as a GET and a page that shows no content counts
    as a failure of its route. ``method`` names another read-only reader
    (an authenticated CLI read of the project's own repository) receipted the
    same way.
    """

    if request_class not in CLASSES:
        raise FetchRefused(f"unknown request class {request_class!r}")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    network = ledger.setdefault("network", {})
    used = int(network.get(f"{request_class}_requests") or 0)
    ceiling = int(network.get(f"{request_class}_ceiling") or 0)
    if used >= ceiling:
        raise FetchRefused(f"{request_class} ceiling {ceiling} reached ({used} used)")
    route = route_of(url)
    failures = network.setdefault("failed_routes", {})
    if int(failures.get(route, 0)) >= 2:
        raise FetchRefused(f"route {route} already failed twice; not retried")
    if not payload:
        failures[route] = int(failures.get(route, 0)) + 1
    digest = hashlib.sha256(payload).hexdigest() if payload else None
    store = ATTEMPT / "private" / "acquisition" / request_class
    store.mkdir(parents=True, exist_ok=True)
    if payload:
        _bas_atomic.write_bytes(store / f"{digest}.bin", payload)
    record = {"url": url, "final_url": url, "route": route, "class": request_class, "purpose": purpose,
              "method": method, "requested_at_utc": rendered_utc, "http_status": None,
              "error": None if payload else "rendered page showed no content", "content_type": "application/json",
              "bytes": len(payload), "sha256": digest, "stored": str(store / f"{digest}.bin") if payload else None,
              "read_only": True}
    _bas_atomic.write_text(store / f"{(digest or hashlib.sha256(url.encode()).hexdigest())}.meta.json", 
        json.dumps(record, indent=2) + "\n", encoding="utf-8")
    network[f"{request_class}_requests"] = used + 1
    network.setdefault("requests", []).append(record)
    _bas_atomic.write_text(ledger_path, json.dumps(ledger, indent=1) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url")
    parser.add_argument("--class", dest="request_class", required=True, choices=CLASSES)
    parser.add_argument("--purpose", required=True)
    args = parser.parse_args(argv)
    try:
        record = fetch(args.url, args.request_class, args.purpose)
    except FetchRefused as refused:
        print(json.dumps({"refused": str(refused)}))
        return 2
    print(json.dumps({k: record[k] for k in ("http_status", "error", "bytes", "sha256", "content_type",
                                               "final_url", "stored")}, indent=1))
    return 0 if record["http_status"] and 200 <= record["http_status"] < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
