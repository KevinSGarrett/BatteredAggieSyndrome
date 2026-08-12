from __future__ import annotations

"""Acquire bounded official NCAA contest evidence into the immutable external lake."""

import argparse
import hashlib
import html
import importlib.metadata
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.adapters import (  # noqa: E402
    AcquisitionFailure,
    AcquisitionRequest,
    FetchResponse,
)
from aggie_analytics.data.snapshots import RawSnapshotStore  # noqa: E402


OFFICIAL_HOST = "stats.ncaa.org"
TRANSIENT_CONDITIONS = frozenset({"CONNECTION_ERROR", "RATE_LIMITED", "SERVER_ERROR", "TIMEOUT"})
SAFE_RESPONSE_HEADERS = frozenset({"content-length", "content-type", "etag", "last-modified", "retry-after"})


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("issued-at timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def write_immutable_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    if path.is_file():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable manifest collision: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install_content_addressed_manifest(
    path: Path,
    manifest: dict[str, Any],
    *,
    core: Mapping[str, Any],
    identity_key: str,
    identity: str,
) -> dict[str, Any]:
    """Preserve the first issuance time when identical content is replayed."""

    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get(identity_key) != identity or any(existing.get(key) != value for key, value in core.items()):
            raise RuntimeError(f"content-addressed manifest collision: {path}")
        return existing
    write_immutable_json(path, manifest)
    return manifest


def load_optional_dotenv_value(path: Path, name: str) -> str | None:
    """Read one dotenv field and return None when absent or empty."""

    if not path.is_file():
        return None
    seen = 0
    resolved: str | None = None
    with path.open(encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() != name:
                continue
            seen += 1
            candidate = value.strip()
            if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {"'", '"'}:
                candidate = candidate[1:-1]
            resolved = candidate or None
    if seen > 1:
        raise RuntimeError(f"{name} appears more than once in the authoritative dotenv file")
    return resolved


def validate_official_uri(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != OFFICIAL_HOST:
        raise ValueError("source URI must use the official HTTPS stats.ncaa.org host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("source URI must not contain credentials, a query, or a fragment")
    if not (
        re.fullmatch(r"/contests/[0-9]+/[a-z_]+", parsed.path)
        or re.fullmatch(r"/teams/[0-9]+", parsed.path)
    ):
        raise ValueError("source URI is not an allowed NCAA official endpoint")


def normalized_text(body: bytes) -> str:
    decoded = body.decode("utf-8", "replace")
    without_scripts = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", decoded)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip().lower()


def inspect_ncaa_html(
    body: bytes,
    *,
    contest_id: str,
    endpoint_id: str,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    validation = contract["content_validation"]
    text = normalized_text(body)
    lowered_html = body.decode("utf-8", "replace").lower()
    matched_reject_markers = sorted(
        marker for marker in validation["reject_case_insensitive_markers"] if marker.lower() in lowered_html
    )
    if matched_reject_markers:
        raise AcquisitionFailure(
            "ANTI_BOT_INTERSTITIAL",
            "official response contained a configured anti-bot or access interstitial",
        )
    if len(body) < int(validation["minimum_html_bytes"]):
        raise AcquisitionFailure("CONTENT_TOO_SMALL", "official response was below the minimum HTML size")
    if "<html" not in lowered_html and "<table" not in lowered_html:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "official response was not recognizable HTML")
    missing_generic = [marker for marker in validation["generic_required_markers"] if marker.lower() not in text]
    if missing_generic:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "official response lacked required NCAA page markers")
    groups = validation["endpoint_required_marker_groups"].get(endpoint_id)
    if not groups:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "endpoint lacks a configured validation marker group")
    missing_groups = [group for group in groups if not any(marker.lower() in text for marker in group)]
    if missing_groups:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "official response lacked endpoint-specific markers")
    headers = tuple(
        sorted(
            {
                re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))).strip()
                for raw in re.findall(r"(?is)<th\b[^>]*>(.*?)</th>", lowered_html)
                if re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))).strip()
            }
        )
    )
    row_count = len(re.findall(r"(?i)<tr\b", lowered_html))
    table_count = len(re.findall(r"(?i)<table\b", lowered_html))
    endpoint = next(row for row in contract["endpoints"] if row["endpoint_id"] == endpoint_id)
    return {
        "contest_id": str(contest_id),
        "endpoint_id": endpoint_id,
        "domains": list(endpoint["domains"]),
        "html_bytes": len(body),
        "row_count": row_count,
        "table_count": table_count,
        "schema_fields": list(headers),
        "schema_sha256": stable_hash(list(headers)),
        "content_validation": "PASS",
    }


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return json_safe(value.item())
    return str(value)


def frame_records(frame: Any) -> list[dict[str, Any]]:
    if hasattr(frame, "to_dicts"):
        rows = frame.to_dicts()
    elif hasattr(frame, "to_dict"):
        rows = frame.to_dict(orient="records")
    else:
        raise TypeError("unsupported parser frame type")
    return [json_safe(dict(row)) for row in rows]


def missingness_profile(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = sorted({str(key) for row in records for key in row})
    return {
        "field_count": len(fields),
        "fields": fields,
        "missing_by_field": {
            field: sum(row.get(field) is None or row.get(field) == "" for row in records)
            for field in fields
        },
    }


def _unique_records(records: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    observed: set[bytes] = set()
    result: list[dict[str, Any]] = []
    for row in records:
        candidate = {field: row.get(field) for field in fields}
        if all(value is None or value == "" for value in candidate.values()):
            continue
        encoded = canonical_json_bytes(candidate)
        if encoded not in observed:
            observed.add(encoded)
            result.append(candidate)
    return result


def normalize_ncaa_capture(
    *,
    raw_path: Path,
    raw_sha256: str,
    contest_id: str,
    endpoint_id: str,
    source_uri: str,
    retrieved_at_utc: str,
    contract: Mapping[str, Any],
    data_root: Path,
) -> list[dict[str, Any]]:
    """Apply the pinned SportsDataverse parsers and write candidate JSON payloads."""

    try:
        from sportsdataverse.cfb import cfb_ncaa_box, cfb_ncaa_pbp
    except ImportError:
        return [
            {
                "domain": domain,
                "state": "PARSER_RUNTIME_UNAVAILABLE",
                "row_count": 0,
                "parser_repository_commit": contract["source"]["upstream_parser_commit"],
            }
            for domain in next(row["domains"] for row in contract["endpoints"] if row["endpoint_id"] == endpoint_id)
        ]
    parser_by_endpoint = {
        "box_score": cfb_ncaa_box.parse_cfb_ncaa_linescore,
        "play_by_play": cfb_ncaa_pbp.parse_cfb_ncaa_pbp,
        "drives": cfb_ncaa_box.parse_cfb_ncaa_drives,
        "team_stats": cfb_ncaa_box.parse_cfb_ncaa_team_stats,
        "individual_stats": cfb_ncaa_box.parse_cfb_ncaa_player_stats,
        "officials": cfb_ncaa_box.parse_cfb_ncaa_officials,
    }
    parser_function = parser_by_endpoint[endpoint_id]
    parsed = parser_function(raw_path.read_text(encoding="utf-8", errors="replace"), contest_id)
    domain_records: dict[str, list[dict[str, Any]]]
    if endpoint_id == "box_score":
        linescore = frame_records(parsed)
        domain_records = {
            "linescore_game_info": linescore,
            "venue": _unique_records(linescore, ("contest_id", "game_date", "venue")),
            "attendance": _unique_records(linescore, ("contest_id", "game_date", "attendance")),
        }
    elif endpoint_id == "individual_stats":
        player_rows: list[dict[str, Any]] = []
        for category, frame in sorted(parsed.items()):
            player_rows.extend({"stat_category": category, **row} for row in frame_records(frame))
        domain_records = {"player_stats": player_rows}
    else:
        domain = {
            "play_by_play": "play_by_play",
            "drives": "drives",
            "team_stats": "team_stats_by_period",
            "officials": "officials",
        }[endpoint_id]
        domain_records = {domain: frame_records(parsed)}
    parser_module = sys.modules[parser_function.__module__]
    parser_path = Path(parser_module.__file__).resolve()
    try:
        runtime_version = importlib.metadata.version("sportsdataverse")
    except importlib.metadata.PackageNotFoundError:
        runtime_version = "UNKNOWN"
    outputs: list[dict[str, Any]] = []
    for domain, records in sorted(domain_records.items()):
        profile = missingness_profile(records)
        payload_core = {
            "schema_version": "1.0.0",
            "artifact_type": "NCAA_OFFICIAL_GAMEBOOK_NORMALIZED_CANDIDATE",
            "decision_unit": contract["decision_unit"],
            "jira_key": contract["jira_key"],
            "classification": contract["classification"],
            "contest_id": contest_id,
            "endpoint_id": endpoint_id,
            "domain": domain,
            "data_grain": contract["domain_grain"][domain],
            "source_uri": source_uri,
            "source_raw_sha256": raw_sha256,
            "source_capture_known_at_utc": retrieved_at_utc,
            "historical_publication_time_proved": False,
            "historical_pit_eligible": False,
            "canonical_identity_promoted": False,
            "parser": {
                "repository": contract["source"]["upstream_parser_repository"],
                "repository_commit": contract["source"]["upstream_parser_commit"],
                "function": f"{parser_function.__module__}.{parser_function.__name__}",
                "installed_distribution_version": runtime_version,
                "module_sha256": sha256_file(parser_path),
            },
            "row_count": len(records),
            "missingness": profile,
            "records": records,
        }
        identity = stable_hash(payload_core)
        payload = {**payload_core, "normalization_identity": identity}
        path = (
            data_root
            / "quarantine"
            / "ncaa_official_gamebooks"
            / "sha256"
            / identity
            / f"{domain}.json"
        )
        write_immutable_json(path, payload)
        outputs.append(
            {
                "domain": domain,
                "state": "PARSED_CANDIDATE" if records else "PARSED_EMPTY_DOMAIN",
                "row_count": len(records),
                "schema_fields": profile["fields"],
                "missing_by_field": profile["missing_by_field"],
                "normalization_identity": identity,
                "payload_relative_path": path.relative_to(data_root).as_posix(),
                "payload_sha256": sha256_file(path),
                "payload_bytes": path.stat().st_size,
                "parser_repository_commit": contract["source"]["upstream_parser_commit"],
                "parser_module_sha256": sha256_file(parser_path),
            }
        )
    return outputs


def request_for(contract: Mapping[str, Any], contest: Mapping[str, Any], endpoint: Mapping[str, Any]) -> AcquisitionRequest:
    contest_id = str(contest["contest_id"])
    if not contest_id.isdigit():
        raise ValueError("contest ID must be numeric")
    path = endpoint["path_template"].format(contest_id=contest_id)
    uri = f"https://{contract['source']['official_host']}{path}"
    validate_official_uri(uri)
    return AcquisitionRequest(
        source_id=contract["source"]["capture_source_id"],
        dataset=f"ncaa_contest_{endpoint['endpoint_id']}",
        source_uri=uri,
        identity_components={
            "contest_id": contest_id,
            "endpoint_id": endpoint["endpoint_id"],
            "run_id": contract["run_id"],
            "sport_code": contract["source"]["sport_code"],
        },
        extension=".html",
    )


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in headers.items() if key.lower() in SAFE_RESPONSE_HEADERS}


def _status_failure(status: int) -> AcquisitionFailure:
    if status == 429:
        condition = "RATE_LIMITED"
    elif status in {408, 425}:
        condition = "TIMEOUT"
    elif 500 <= status < 600:
        condition = "SERVER_ERROR"
    else:
        condition = f"HTTP_{status}"
    return AcquisitionFailure(condition, f"route returned HTTP {status}", status_code=status)


@dataclass(frozen=True)
class DirectHTTPTransport:
    timeout_seconds: float = 60.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        validate_official_uri(request.source_uri)
        wire = urllib.request.Request(
            request.source_uri,
            headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": self.user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(wire, timeout=self.timeout_seconds) as response:
                return FetchResponse(
                    body=response.read(), status_code=int(response.status), headers=_safe_headers(response.headers)
                )
        except urllib.error.HTTPError as error:
            return FetchResponse(
                body=error.read(), status_code=int(error.code), headers=_safe_headers(error.headers)
            )
        except TimeoutError as error:
            raise AcquisitionFailure("TIMEOUT", "direct NCAA request timed out") from error
        except urllib.error.URLError as error:
            raise AcquisitionFailure("CONNECTION_ERROR", "direct NCAA connection failed") from error


@dataclass(frozen=True)
class ScrapflyTransport:
    access_token: str = field(repr=False)
    api_url: str = "https://api.scrapfly.io/scrape"
    proxy_pool: str = "public_residential_pool"
    country: str = "us"
    rendering_wait_milliseconds: int = 8000
    cost_budget: int = 55
    timeout_seconds: float = 155.0

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("Scrapfly credential must be nonempty")

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        validate_official_uri(request.source_uri)
        wire_url = self.api_url + "?" + urllib.parse.urlencode(
            {
                "key": self.access_token,
                "url": request.source_uri,
                "asp": "true",
                "render_js": "true",
                "proxy_pool": self.proxy_pool,
                "country": self.country,
                "rendering_wait": str(self.rendering_wait_milliseconds),
                "cost_budget": str(self.cost_budget),
            }
        )
        try:
            with urllib.request.urlopen(
                urllib.request.Request(wire_url, headers={"Accept": "application/json"}),
                timeout=self.timeout_seconds,
            ) as response:
                provider_body = response.read()
                provider_status = int(response.status)
        except urllib.error.HTTPError as error:
            return FetchResponse(body=b"", status_code=int(error.code), headers=_safe_headers(error.headers))
        except TimeoutError as error:
            raise AcquisitionFailure("TIMEOUT", "Scrapfly request timed out") from error
        except urllib.error.URLError as error:
            raise AcquisitionFailure("CONNECTION_ERROR", "Scrapfly connection failed") from error
        if not 200 <= provider_status < 300:
            return FetchResponse(body=b"", status_code=provider_status)
        try:
            envelope = json.loads(provider_body)
            content = envelope["result"]["content"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "Scrapfly response envelope was invalid") from error
        if not isinstance(content, str):
            raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "Scrapfly content was not text")
        return FetchResponse(body=content.encode("utf-8"), status_code=200, headers={"content-type": "text/html"})


@dataclass(frozen=True)
class ScraperAPITransport:
    access_token: str = field(repr=False)
    api_url: str = "https://api.scraperapi.com/"
    timeout_seconds: float = 155.0

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("ScraperAPI credential must be nonempty")

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        validate_official_uri(request.source_uri)
        wire_url = self.api_url + "?" + urllib.parse.urlencode(
            {
                "api_key": self.access_token,
                "url": request.source_uri,
                "render": "true",
                "country_code": "us",
            }
        )
        try:
            with urllib.request.urlopen(wire_url, timeout=self.timeout_seconds) as response:
                return FetchResponse(
                    body=response.read(), status_code=int(response.status), headers=_safe_headers(response.headers)
                )
        except urllib.error.HTTPError as error:
            return FetchResponse(body=error.read(), status_code=int(error.code), headers=_safe_headers(error.headers))
        except TimeoutError as error:
            raise AcquisitionFailure("TIMEOUT", "ScraperAPI request timed out") from error
        except urllib.error.URLError as error:
            raise AcquisitionFailure("CONNECTION_ERROR", "ScraperAPI connection failed") from error


@dataclass(frozen=True)
class LocalChromeTransport:
    executable_path: Path | None
    profile_root: Path
    user_agent: str
    browser_installation_root: Path | None = None
    wait_after_load_milliseconds: int = 8000
    timeout_seconds: float = 90.0
    solve_attempts: int = 3

    def __post_init__(self) -> None:
        if self.executable_path is not None and not self.executable_path.is_file():
            raise ValueError("local Chrome executable is absent")
        if self.executable_path is None and (
            self.browser_installation_root is None or not self.browser_installation_root.is_dir()
        ):
            raise ValueError("Patchright browser installation is absent")
        if self.wait_after_load_milliseconds < 0 or self.timeout_seconds <= 0 or self.solve_attempts < 1:
            raise ValueError("browser waits and timeout must be valid")

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        validate_official_uri(request.source_uri)
        self.profile_root.mkdir(parents=True, exist_ok=True)
        try:
            from patchright.sync_api import sync_playwright
        except ImportError:
            return self._subprocess_fallback(request)
        try:
            if self.browser_installation_root is not None:
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(self.browser_installation_root)
            with tempfile.TemporaryDirectory(prefix="ncaa_pw_", dir=self.profile_root) as profile:
                with sync_playwright() as playwright:
                    launch: dict[str, Any] = {
                        "user_data_dir": profile,
                        "headless": False,
                        "args": ["--headless=new"],
                        "no_viewport": True,
                        "user_agent": self.user_agent,
                    }
                    if self.executable_path is not None:
                        launch["executable_path"] = str(self.executable_path)
                    context = playwright.chromium.launch_persistent_context(
                        **launch,
                    )
                    page = context.pages[0] if context.pages else context.new_page()
                    result: Mapping[str, Any] = {"status": 0, "text": ""}
                    for _ in range(self.solve_attempts):
                        page.goto(
                            request.source_uri,
                            wait_until="domcontentloaded",
                            timeout=int(self.timeout_seconds * 1000),
                        )
                        page.wait_for_timeout(self.wait_after_load_milliseconds)
                        result = page.evaluate(
                            "async ({url, timeout}) => { const c = new AbortController(); "
                            "const timer = setTimeout(() => c.abort(), timeout); try { "
                            "const r = await fetch(url, {credentials:'include', signal:c.signal}); "
                            "return {status:r.status, text:await r.text()}; } finally { clearTimeout(timer); } }",
                            {"url": request.source_uri, "timeout": int(self.timeout_seconds * 1000)},
                        )
                        body = str(result["text"]).encode("utf-8")
                        lowered = body.lower()
                        if len(body) >= 1000 and b"bm-verify" not in lowered and b"_abck" not in lowered:
                            context.close()
                            return FetchResponse(
                                body=body,
                                status_code=int(result["status"]),
                                headers={"content-type": "text/html"},
                            )
                    context.close()
                    return FetchResponse(
                        body=str(result["text"]).encode("utf-8"),
                        status_code=int(result["status"]),
                        headers={"content-type": "text/html"},
                    )
        except Exception as error:
            name = type(error).__name__.lower()
            condition = "TIMEOUT" if "timeout" in name else "BROWSER_ROUTE_FAILED"
            raise AcquisitionFailure(condition, "local Patchright/Chrome route failed") from error

    def _subprocess_fallback(self, request: AcquisitionRequest) -> FetchResponse:
        if self.executable_path is None:
            raise AcquisitionFailure("ROUTE_UNAVAILABLE", "Patchright is required for the bundled browser")
        command = [
            str(self.executable_path),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={self.profile_root}",
            f"--virtual-time-budget={self.wait_after_load_milliseconds}",
            "--dump-dom",
            request.source_uri,
        ]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise AcquisitionFailure("TIMEOUT", "local Chrome route timed out") from error
        if result.returncode != 0:
            raise AcquisitionFailure("BROWSER_ROUTE_FAILED", "local Chrome route returned a failure")
        return FetchResponse(body=result.stdout, status_code=200, headers={"content-type": "text/html"})


class StatefulPatchrightSession:
    """Reuse one anti-detect browser context for bounded official-page discovery."""

    def __init__(
        self,
        *,
        executable_path: Path | None,
        browser_installation_root: Path | None,
        runtime_root: Path,
        user_agent: str,
        challenge_wait_milliseconds: int = 8000,
        timeout_seconds: float = 90.0,
        solve_attempts: int = 3,
    ) -> None:
        self.executable_path = executable_path
        self.browser_installation_root = browser_installation_root
        self.runtime_root = runtime_root
        self.user_agent = user_agent
        self.challenge_wait_milliseconds = challenge_wait_milliseconds
        self.timeout_seconds = timeout_seconds
        self.solve_attempts = solve_attempts
        self._temporary: Any = None
        self._playwright: Any = None
        self._context: Any = None
        self._page: Any = None
        self._challenge_solved = False

    def __enter__(self) -> "StatefulPatchrightSession":
        from patchright.sync_api import sync_playwright

        self.runtime_root.mkdir(parents=True, exist_ok=True)
        if self.browser_installation_root is not None:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(self.browser_installation_root)
        self._temporary = tempfile.TemporaryDirectory(prefix="ncaa_session_", dir=self.runtime_root)
        self._playwright = sync_playwright().start()
        launch: dict[str, Any] = {
            "user_data_dir": self._temporary.name,
            "headless": False,
            "args": ["--headless=new"],
            "no_viewport": True,
            "user_agent": self.user_agent,
        }
        if self.executable_path is not None:
            launch["executable_path"] = str(self.executable_path)
        self._context = self._playwright.chromium.launch_persistent_context(**launch)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        return self

    def __exit__(self, *_exc: object) -> None:
        try:
            if self._context is not None:
                self._context.close()
        finally:
            if self._playwright is not None:
                self._playwright.stop()
            if self._temporary is not None:
                self._temporary.cleanup()
            self._context = self._page = self._playwright = self._temporary = None

    @staticmethod
    def _unsolved(body: bytes) -> bool:
        lowered = body.lower()
        return len(body) < 1000 or b"bm-verify" in lowered or b"_abck" in lowered

    def fetch(self, source_uri: str) -> FetchResponse:
        validate_official_uri(source_uri)
        if self._page is None:
            raise RuntimeError("browser session is not open")
        result: Mapping[str, Any] = {"status": 0, "text": ""}
        for _ in range(self.solve_attempts):
            if not self._challenge_solved:
                try:
                    self._page.goto(
                        source_uri,
                        wait_until="domcontentloaded",
                        timeout=int(self.timeout_seconds * 1000),
                    )
                    self._page.wait_for_timeout(self.challenge_wait_milliseconds)
                except Exception as error:
                    name = type(error).__name__.lower()
                    condition = "TIMEOUT" if "timeout" in name else "BROWSER_ROUTE_FAILED"
                    raise AcquisitionFailure(condition, "stateful browser navigation failed") from error
                self._challenge_solved = True
            try:
                result = self._page.evaluate(
                    "async ({url, timeout}) => { const c = new AbortController(); "
                    "const timer = setTimeout(() => c.abort(), timeout); try { "
                    "const r = await fetch(url, {credentials:'include', signal:c.signal}); "
                    "return {status:r.status, text:await r.text()}; } finally { clearTimeout(timer); } }",
                    {"url": source_uri, "timeout": int(self.timeout_seconds * 1000)},
                )
            except Exception as error:
                name = type(error).__name__.lower()
                condition = "TIMEOUT" if "timeout" in name or "abort" in str(error).lower() else "BROWSER_ROUTE_FAILED"
                raise AcquisitionFailure(condition, "stateful browser fetch failed") from error
            body = str(result["text"]).encode("utf-8")
            if not self._unsolved(body):
                return FetchResponse(
                    body=body,
                    status_code=int(result["status"]),
                    headers={"content-type": "text/html"},
                )
            self._challenge_solved = False
        return FetchResponse(
            body=str(result["text"]).encode("utf-8"),
            status_code=int(result["status"]),
            headers={"content-type": "text/html"},
        )


@dataclass(frozen=True)
class StatefulDiscoveryTransport:
    """Adapt the reusable browser session to the acquisition transport contract."""

    browser: StatefulPatchrightSession

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        return self.browser.fetch(request.source_uri)


def inspect_ncaa_team_page(body: bytes, *, contract: Mapping[str, Any]) -> dict[str, Any]:
    text = body.decode("utf-8", "replace")
    lowered = text.lower()
    matched = sorted(
        marker
        for marker in contract["content_validation"]["reject_case_insensitive_markers"]
        if marker.lower() in lowered
    )
    if matched:
        raise AcquisitionFailure("ANTI_BOT_INTERSTITIAL", "team page contained an access interstitial")
    if len(body) < int(contract["discovery"]["minimum_team_page_bytes"]):
        raise AcquisitionFailure("CONTENT_TOO_SMALL", "team page was below the minimum content size")
    if "<html" not in lowered or "ncaa" not in normalized_text(body):
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "team page lacked official NCAA HTML markers")
    all_rows = re.findall(r"(?is)<tr\b[^>]*>.*?</tr>", text)
    contest_rows = [
        row
        for row in all_rows
        if re.search(r"/contests/[0-9]+/box_score", row)
    ]
    legacy_schedule_rows = [
        row
        for row in all_rows
        if not contest_rows
        and re.search(r"/teams/[0-9]+", row)
        and re.search(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", row)
        and re.search(r">\s*(?:(?:W|L|T)\s+)?[0-9]+\s*-\s*[0-9]+\s*<", row, re.IGNORECASE)
    ]
    traversal_rows = contest_rows or legacy_schedule_rows
    team_ids = sorted(
        {
            identifier
            for row in traversal_rows
            for identifier in re.findall(r"/teams/([0-9]+)(?:[\"'/])", row)
        }
    )
    contest_ids = sorted(
        {
            identifier
            for row in contest_rows
            for identifier in re.findall(r"/contests/([0-9]+)/box_score", row)
        }
    )
    season_options = {
        label.strip(): identifier
        for identifier, label in re.findall(
            r"(?is)<option[^>]*value=[\"']([0-9]+)[\"'][^>]*>([^<]+)</option>", text
        )
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}", label.strip())
    }
    return {
        "team_season_ids": team_ids,
        "contest_ids": contest_ids,
        "season_options": dict(sorted(season_options.items())),
        "html_bytes": len(body),
        "team_link_count": len(team_ids),
        "contest_link_count": len(contest_ids),
        "link_schema": "MODERN_CONTEST_ROW" if contest_rows else "LEGACY_SCHEDULE_RESULT_ROW",
    }


def discover_season(
    *,
    season: int,
    contract: Mapping[str, Any],
    store: RawSnapshotStore,
    browser: StatefulPatchrightSession | None = None,
    routes: list[tuple[str, Any]] | None = None,
    retrieved_at: datetime,
    maximum_teams: int,
) -> dict[str, Any]:
    seed_map = contract["discovery"]["seed_team_season_ids"]
    if str(season) not in seed_map:
        raise ValueError(f"season {season} lacks a configured official team-season seed")
    queue = [str(seed_map[str(season)])]
    queued = set(queue)
    visited: set[str] = set()
    contest_ids: set[str] = set()
    captures: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    if routes is None:
        if browser is None:
            raise ValueError("discovery requires at least one acquisition route")
        routes = [("local_patchright_chrome", StatefulDiscoveryTransport(browser))]
    if not routes:
        raise ValueError("discovery requires at least one available acquisition route")
    while queue and len(visited) < maximum_teams:
        team_season_id = queue.pop(0)
        if team_season_id in visited:
            continue
        source_uri = f"https://{contract['source']['official_host']}" + contract["discovery"][
            "path_template"
        ].format(team_season_id=team_season_id)
        validate_official_uri(source_uri)
        request = AcquisitionRequest(
            source_id=contract["source"]["capture_source_id"],
            dataset="ncaa_team_season_discovery",
            source_uri=source_uri,
            identity_components={
                "decision_unit": contract["decision_unit"],
                "season": season,
                "team_season_id": team_season_id,
                "discovery_contract": "NCAA_TEAM_GRAPH_V1",
            },
            extension=".html",
        )
        snapshot = store.lookup_request(request.identity_sha256)
        if snapshot is None:
            attempts: list[dict[str, Any]] = []
            for route_id, transport in routes:
                try:
                    response = transport(request)
                    if not 200 <= int(response.status_code) < 300:
                        raise _status_failure(int(response.status_code))
                    profile = inspect_ncaa_team_page(response.body, contract=contract)
                    attempts.append({"route_id": route_id, "condition": "SUCCESS"})
                    snapshot = store.ingest_bytes(
                        request.source_id,
                        request.dataset,
                        response.body,
                        retrieved_at=retrieved_at,
                        source_uri=source_uri,
                        extension=request.extension,
                        row_count=profile["contest_link_count"],
                        schema_fields=("team_season_ids", "contest_ids", "season_options"),
                        metadata={
                            "decision_unit": contract["decision_unit"],
                            "jira_key": contract["jira_key"],
                            "request_identity_sha256": request.identity_sha256,
                            "selected_route_id": route_id,
                            "attempts": attempts,
                            "candidate_only": True,
                        },
                    )
                    store.bind_request(request.identity_sha256, snapshot)
                    break
                except AcquisitionFailure as error:
                    attempts.append(
                        {
                            "route_id": route_id,
                            "condition": error.condition,
                            "status_code": error.status_code,
                        }
                    )
            if snapshot is None:
                final_attempt = attempts[-1] if attempts else {}
                failures.append(
                    {
                        "team_season_id": team_season_id,
                        "source_uri": source_uri,
                        "condition": final_attempt.get("condition", "NO_AVAILABLE_ROUTE"),
                        "status_code": final_attempt.get("status_code"),
                        "attempts": attempts,
                    }
                )
                visited.add(team_season_id)
                continue
        raw_path = store.root / snapshot.relative_path
        try:
            profile = inspect_ncaa_team_page(raw_path.read_bytes(), contract=contract)
        except AcquisitionFailure as error:
            failures.append(
                {
                    "team_season_id": team_season_id,
                    "source_uri": source_uri,
                    "condition": error.condition,
                    "status_code": error.status_code,
                }
            )
            visited.add(team_season_id)
            continue
        visited.add(team_season_id)
        target_season_label = f"{season}-{(season + 1) % 100:02d}"
        selected_team_id = profile["season_options"].get(target_season_label)
        if selected_team_id is not None and selected_team_id != team_season_id:
            failures.append(
                {
                    "team_season_id": team_season_id,
                    "source_uri": source_uri,
                    "condition": "CROSS_SEASON_TEAM_LINK_EXCLUDED",
                    "status_code": None,
                    "selected_team_season_id_for_target_season": selected_team_id,
                }
            )
            continue
        contest_ids.update(profile["contest_ids"])
        for discovered in profile["team_season_ids"]:
            if discovered not in queued and discovered not in visited:
                queued.add(discovered)
                queue.append(discovered)
        captures.append(
            {
                "team_season_id": team_season_id,
                "source_uri": source_uri,
                "request_identity_sha256": request.identity_sha256,
                "snapshot_id": snapshot.snapshot_id,
                "raw_relative_path": snapshot.relative_path,
                "raw_sha256": snapshot.raw_sha256,
                "raw_bytes": raw_path.stat().st_size,
                "retrieved_at_utc": iso_utc(snapshot.retrieved_at),
                **profile,
            }
        )
        interval = int(contract["discovery"]["progress_interval"])
        if interval and len(visited) % interval == 0:
            print(
                json.dumps(
                    {
                        "event": "NCAA_DISCOVERY_PROGRESS",
                        "season": season,
                        "teams_visited": len(visited),
                        "teams_queued": len(queue),
                        "contest_ids": len(contest_ids),
                        "failures": len(failures),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    state = "COMPLETE_GRAPH_EXHAUSTED" if not queue else "PARTIAL_MAXIMUM_TEAM_LIMIT_REACHED"
    core = {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_OFFICIAL_TEAM_GRAPH_DISCOVERY_MANIFEST",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "season": season,
        "seed_team_season_id": str(seed_map[str(season)]),
        "seed_provenance": contract["discovery"]["seed_provenance"],
        "state": state,
        "team_page_capture_count": len(captures),
        "team_failure_count": len(failures),
        "discovered_team_season_ids": sorted(visited, key=int),
        "discovered_contest_ids": sorted(contest_ids, key=int),
        "captures": sorted(captures, key=lambda row: int(row["team_season_id"])),
        "failures": sorted(failures, key=lambda row: int(row["team_season_id"])),
        "remaining_queue": sorted(queue, key=int),
        "authority": contract["authority"],
    }
    identity = stable_hash(core)
    manifest = {
        **core,
        "discovery_identity": identity,
        "issued_at_utc": iso_utc(retrieved_at),
        "credentials_logged_or_persisted": False,
    }
    path = (
        store.root
        / "manifests"
        / "acquisition"
        / contract["run_id"]
        / "discovery"
        / str(season)
        / "sha256"
        / identity
        / "ncaa_team_graph_discovery_manifest.json"
    )
    manifest = install_content_addressed_manifest(
        path,
        manifest,
        core=core,
        identity_key="discovery_identity",
        identity=identity,
    )
    return {
        "season": season,
        "state": state,
        "discovery_identity": identity,
        "manifest_path": str(path),
        "manifest_sha256": sha256_file(path),
        "team_page_capture_count": len(captures),
        "team_failure_count": len(failures),
        "discovered_team_count": len(visited),
        "discovered_contest_count": len(contest_ids),
        "remaining_queue_count": len(queue),
    }


@dataclass(frozen=True)
class ValidatingTransport:
    transport: Any
    contest_id: str
    endpoint_id: str
    contract: Mapping[str, Any] = field(repr=False)

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        response = self.transport(request)
        if not 200 <= int(response.status_code) < 300:
            raise _status_failure(int(response.status_code))
        profile = inspect_ncaa_html(
            response.body,
            contest_id=self.contest_id,
            endpoint_id=self.endpoint_id,
            contract=self.contract,
        )
        return FetchResponse(
            body=response.body,
            status_code=response.status_code,
            headers=response.headers,
            row_count=int(profile["row_count"]),
            schema_fields=tuple(profile["schema_fields"]),
        )


def select_browser_runtime(
    contract: Mapping[str, Any], runtime_root: Path
) -> tuple[Path | None, Path | None] | None:
    browser_config = contract["transport"]["local_patchright_chrome"]
    if browser_config.get("prefer_external_patchright_browser"):
        matches = sorted(runtime_root.glob(browser_config["external_patchright_browser_glob"]), reverse=True)
        if matches:
            return None, runtime_root / "patchright-browsers"
    for candidate in browser_config["browser_executable_candidates"]:
        path = Path(candidate)
        if path.is_file():
            return path, None
    return None


def build_routes(
    *,
    contract: Mapping[str, Any],
    env_file: Path,
    runtime_root: Path,
    contest_id: str,
    endpoint_id: str,
) -> tuple[list[tuple[str, Any]], list[dict[str, Any]]]:
    available: dict[str, Any] = {"direct_http": DirectHTTPTransport()}
    states: list[dict[str, Any]] = [
        {"route_id": "direct_http", "availability": "AVAILABLE", "credential_state": "NOT_REQUIRED"}
    ]
    browser_runtime = select_browser_runtime(contract, runtime_root)
    if browser_runtime is not None:
        browser_config = contract["transport"]["local_patchright_chrome"]
        available["local_patchright_chrome"] = LocalChromeTransport(
            executable_path=browser_runtime[0],
            profile_root=runtime_root / "chrome-profile",
            user_agent=str(browser_config["user_agent"]),
            browser_installation_root=browser_runtime[1],
            wait_after_load_milliseconds=int(browser_config["wait_after_load_milliseconds"]),
        )
        states.append(
            {"route_id": "local_patchright_chrome", "availability": "AVAILABLE", "credential_state": "NOT_REQUIRED"}
        )
    else:
        states.append(
            {"route_id": "local_patchright_chrome", "availability": "UNAVAILABLE_BROWSER_ABSENT", "credential_state": "NOT_REQUIRED"}
        )
    for route_id, transport_type in (("scrapfly", ScrapflyTransport), ("scraperapi", ScraperAPITransport)):
        route_config = contract["transport"][route_id]
        variable = route_config["credential_environment_variable"]
        credential = load_optional_dotenv_value(env_file, variable)
        if credential:
            if route_id == "scrapfly":
                available[route_id] = transport_type(
                    credential,
                    api_url=route_config["api_url"],
                    proxy_pool=route_config["proxy_pool"],
                    country=route_config["country"],
                    rendering_wait_milliseconds=int(route_config["rendering_wait_milliseconds"]),
                    cost_budget=int(route_config["cost_budget"]),
                )
            else:
                available[route_id] = transport_type(credential, api_url=route_config["api_url"])
            states.append(
                {"route_id": route_id, "availability": "AVAILABLE", "credential_state": "CONFIGURED_NONEMPTY"}
            )
        else:
            states.append(
                {"route_id": route_id, "availability": "UNAVAILABLE_CREDENTIAL_EMPTY_OR_ABSENT", "credential_state": "EMPTY_OR_ABSENT"}
            )
    ordered = [
        (
            route_id,
            ValidatingTransport(available[route_id], contest_id, endpoint_id, contract),
        )
        for route_id in contract["transport"]["route_order"]
        if route_id in available
    ]
    return ordered, states


def build_discovery_routes(
    *,
    contract: Mapping[str, Any],
    env_file: Path,
    browser: StatefulPatchrightSession | None,
    selected_route_ids: list[str] | None = None,
) -> tuple[list[tuple[str, Any]], list[dict[str, Any]]]:
    """Build a secret-safe route cascade for official team-page discovery."""

    available: dict[str, Any] = {"direct_http": DirectHTTPTransport()}
    states: list[dict[str, Any]] = [
        {"route_id": "direct_http", "availability": "AVAILABLE", "credential_state": "NOT_REQUIRED"}
    ]
    if browser is not None:
        available["local_patchright_chrome"] = StatefulDiscoveryTransport(browser)
        states.append(
            {"route_id": "local_patchright_chrome", "availability": "AVAILABLE", "credential_state": "NOT_REQUIRED"}
        )
    else:
        states.append(
            {
                "route_id": "local_patchright_chrome",
                "availability": "NOT_SELECTED_OR_BROWSER_ABSENT",
                "credential_state": "NOT_REQUIRED",
            }
        )
    for route_id, transport_type in (("scrapfly", ScrapflyTransport), ("scraperapi", ScraperAPITransport)):
        route_config = contract["transport"][route_id]
        variable = route_config["credential_environment_variable"]
        credential = load_optional_dotenv_value(env_file, variable)
        if credential:
            if route_id == "scrapfly":
                available[route_id] = transport_type(
                    credential,
                    api_url=route_config["api_url"],
                    proxy_pool=route_config["proxy_pool"],
                    country=route_config["country"],
                    rendering_wait_milliseconds=int(route_config["rendering_wait_milliseconds"]),
                    cost_budget=int(route_config["cost_budget"]),
                )
            else:
                available[route_id] = transport_type(credential, api_url=route_config["api_url"])
            states.append(
                {"route_id": route_id, "availability": "AVAILABLE", "credential_state": "CONFIGURED_NONEMPTY"}
            )
        else:
            states.append(
                {
                    "route_id": route_id,
                    "availability": "UNAVAILABLE_CREDENTIAL_EMPTY_OR_ABSENT",
                    "credential_state": "EMPTY_OR_ABSENT",
                }
            )
    requested = selected_route_ids or list(contract["discovery"]["route_order"])
    ordered = [(route_id, available[route_id]) for route_id in requested if route_id in available]
    return ordered, states


def acquire_one(
    *,
    store: RawSnapshotStore,
    request: AcquisitionRequest,
    routes: list[tuple[str, Any]],
    retrieved_at: datetime,
    maximum_attempts: int,
) -> dict[str, Any]:
    cached = store.lookup_request(request.identity_sha256)
    if cached is not None:
        payload = store.root / cached.relative_path
        return {
            "state": "CAPTURED",
            "from_cache": True,
            "route_id": "IMMUTABLE_REQUEST_CACHE",
            "snapshot_id": cached.snapshot_id,
            "raw_sha256": cached.raw_sha256,
            "raw_relative_path": cached.relative_path,
            "raw_bytes": payload.stat().st_size,
            "capture_retrieved_at_utc": iso_utc(cached.retrieved_at),
            "row_count": cached.row_count,
            "schema_fields": list(cached.schema_fields),
            "request_identity_sha256": request.identity_sha256,
            "attempts": [{"route_id": "IMMUTABLE_REQUEST_CACHE", "attempt": 0, "condition": "CACHE_HIT"}],
        }
    attempts: list[dict[str, Any]] = []
    for route_id, transport in routes:
        for attempt in range(1, maximum_attempts + 1):
            try:
                response = transport(request)
            except AcquisitionFailure as error:
                attempts.append(
                    {
                        "route_id": route_id,
                        "attempt": attempt,
                        "condition": error.condition,
                        "status_code": error.status_code,
                    }
                )
                if error.condition in TRANSIENT_CONDITIONS and attempt < maximum_attempts:
                    continue
                break
            metadata = {
                "decision_unit": "POST-SUBTASK-197",
                "jira_key": "BAT-554",
                "request_identity_sha256": request.identity_sha256,
                "selected_route_id": route_id,
                "attempts": attempts + [{"route_id": route_id, "attempt": attempt, "condition": "SUCCESS"}],
                "candidate_only": True,
            }
            snapshot = store.ingest_bytes(
                request.source_id,
                request.dataset,
                response.body,
                retrieved_at=retrieved_at,
                source_uri=request.source_uri,
                extension=request.extension,
                row_count=response.row_count,
                schema_fields=response.schema_fields,
                metadata=metadata,
            )
            store.bind_request(request.identity_sha256, snapshot)
            payload = store.root / snapshot.relative_path
            attempts.append({"route_id": route_id, "attempt": attempt, "condition": "SUCCESS"})
            return {
                "state": "CAPTURED",
                "from_cache": False,
                "route_id": route_id,
                "snapshot_id": snapshot.snapshot_id,
                "raw_sha256": snapshot.raw_sha256,
                "raw_relative_path": snapshot.relative_path,
                "raw_bytes": payload.stat().st_size,
                "capture_retrieved_at_utc": iso_utc(snapshot.retrieved_at),
                "row_count": snapshot.row_count,
                "schema_fields": list(snapshot.schema_fields),
                "request_identity_sha256": request.identity_sha256,
                "attempts": attempts,
            }
    return {
        "state": "TECHNICALLY_UNAVAILABLE",
        "from_cache": False,
        "request_identity_sha256": request.identity_sha256,
        "attempts": attempts,
        "failure_condition": attempts[-1]["condition"] if attempts else "NO_AVAILABLE_ROUTE",
    }


def acquisition_core(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    captures: list[dict[str, Any]],
    route_states: list[dict[str, Any]],
) -> dict[str, Any]:
    captured = [row for row in captures if row["state"] == "CAPTURED"]
    failures = [row for row in captures if row["state"] != "CAPTURED"]
    domain_counts: dict[str, int] = {}
    normalized_domain_counts: dict[str, int] = {}
    normalized_row_counts: dict[str, int] = {}
    for row in captured:
        for domain in row["domains"]:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        for normalized in row.get("normalization", []):
            if normalized["state"] == "PARSED_CANDIDATE":
                domain = normalized["domain"]
                normalized_domain_counts[domain] = normalized_domain_counts.get(domain, 0) + 1
                normalized_row_counts[domain] = normalized_row_counts.get(domain, 0) + int(normalized["row_count"])
    return {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_OFFICIAL_GAMEBOOK_ACQUISITION_MANIFEST",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "run_id": contract["run_id"],
        "contract_sha256": contract_sha256,
        "pinned_source": contract["source"],
        "route_states": route_states,
        "captures": captures,
        "request_count": len(captures),
        "captured_count": len(captured),
        "technical_failure_count": len(failures),
        "total_raw_bytes": sum(int(row["raw_bytes"]) for row in captured),
        "domain_capture_counts": dict(sorted(domain_counts.items())),
        "normalized_domain_counts": dict(sorted(normalized_domain_counts.items())),
        "normalized_row_counts": dict(sorted(normalized_row_counts.items())),
        "authority": contract["authority"],
    }


def build_gate(
    *,
    contract: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_path: Path,
    manifest_sha256: str,
    discovery_manifest: Mapping[str, Any] | None = None,
    discovery_manifest_path: Path | None = None,
    discovery_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    captured = [row for row in manifest["captures"] if row["state"] == "CAPTURED"]
    contest_ids = sorted({row["contest_id"] for row in captured})
    endpoint_ids = sorted({row["endpoint_id"] for row in captured})
    all_domains = sorted(contract["domain_grain"])
    captured_domains = sorted(manifest.get("normalized_domain_counts", manifest["domain_capture_counts"]))
    missing_domains = sorted(set(all_domains) - set(captured_domains))
    result = "PASS_BOUNDED_CANDIDATE_CAPTURE" if captured else "PRESERVED_NEGATIVE_NO_VALID_CAPTURE"
    gate = {
        "schema_version": "1.0.0",
        "artifact_type": "NCAA_OFFICIAL_GAMEBOOK_ACQUISITION_GATE",
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": contract["classification"],
        "result": result,
        "manifest": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "acquisition_identity": manifest["acquisition_identity"],
        },
        "bounded_population": {
            "requested": manifest["request_count"],
            "captured": manifest["captured_count"],
            "technical_failures": manifest["technical_failure_count"],
            "contest_ids": contest_ids,
            "endpoint_ids": endpoint_ids,
            "captured_domains": captured_domains,
            "missing_domains": missing_domains,
            "domain_capture_counts": manifest["domain_capture_counts"],
            "normalized_domain_counts": manifest.get("normalized_domain_counts", {}),
            "normalized_row_counts": manifest.get("normalized_row_counts", {}),
        },
        "identity_gate": {
            "official_contest_ids_pinned": bool(contest_ids),
            "canonical_game_identity_promoted": False,
            "name_only_match_promoted": False,
            "state": "CANONICAL_RECONCILIATION_PENDING",
        },
        "pit_gate": {
            "capture_time_recorded": bool(captured),
            "historical_publication_time_proved": False,
            "historical_pit_eligible": False,
            "same_game_pregame_eligible": False,
            "target_game_outcome_excluded": True,
        },
        "scale_out_gate": {
            "automatic_national_scale_out_enabled": False,
            "reason": "BOUNDED_ROUTE_AND_SCHEMA_EVIDENCE_REQUIRES_CANONICAL_IDENTITY_AND_COVERAGE_VALIDATION",
            "partial_domain_does_not_block_unrelated_valid_domains": True,
        },
        "authority": contract["authority"],
        "negative_findings": [
            "A bounded source-route success does not establish national historical completeness.",
            "NCAA contest IDs remain candidate mappings until deterministic canonical game/team reconciliation passes.",
            "Capture time does not prove historical publication time or same-game pregame eligibility.",
            "Missing endpoints and partial games remain explicit and do not invalidate unrelated captured domains.",
        ],
        "scientific_nonclaims": {
            "historical_population_ready": False,
            "gap_002_resolved": False,
            "production_model_ready": False,
            "protected_performance_claimed": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_claimed": False,
        },
    }
    if discovery_manifest is not None:
        if discovery_manifest_path is None or discovery_manifest_sha256 is None:
            raise ValueError("discovery manifest path and hash are required with discovery evidence")
        gate["discovery_population"] = {
            "season": discovery_manifest["season"],
            "state": discovery_manifest["state"],
            "team_page_capture_count": discovery_manifest["team_page_capture_count"],
            "team_failure_count": discovery_manifest["team_failure_count"],
            "discovered_contest_count": len(discovery_manifest["discovered_contest_ids"]),
            "remaining_queue_count": len(discovery_manifest["remaining_queue"]),
            "manifest": {
                "path": str(discovery_manifest_path),
                "sha256": discovery_manifest_sha256,
                "discovery_identity": discovery_manifest["discovery_identity"],
            },
            "canonical_identity_promoted": False,
            "historical_pit_eligible": False,
        }
    return gate


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--env-file", type=Path, required=True)
    result.add_argument("--contract", type=Path, required=True)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--runtime-root", type=Path)
    result.add_argument("--gate-output", type=Path)
    result.add_argument("--discovery-manifest", type=Path)
    result.add_argument("--contest-id", action="append", default=[])
    result.add_argument("--endpoint-id", action="append", default=[])
    result.add_argument("--route-id", action="append", default=[])
    result.add_argument("--maximum-requests", type=int)
    result.add_argument("--maximum-attempts", type=int, default=2)
    result.add_argument("--discover-season", type=int, action="append", default=[])
    result.add_argument("--discovery-only", action="store_true")
    result.add_argument("--maximum-discovery-teams", type=int)
    result.add_argument("--discovery-route-id", action="append", default=[])
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract_path = args.contract.resolve()
    if repo_root not in contract_path.parents:
        raise ValueError("contract must be versioned in the repository")
    if (
        args.maximum_attempts < 1
        or (args.maximum_requests is not None and args.maximum_requests < 1)
        or (args.maximum_discovery_teams is not None and args.maximum_discovery_teams < 1)
    ):
        raise ValueError("attempt and request limits must be positive")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    unknown_routes = sorted(set(args.route_id) - set(contract["transport"]["route_order"]))
    if unknown_routes:
        raise ValueError(f"unknown route filters: {','.join(unknown_routes)}")
    unknown_discovery_routes = sorted(
        set(args.discovery_route_id) - set(contract["discovery"]["route_order"])
    )
    if unknown_discovery_routes:
        raise ValueError(f"unknown discovery route filters: {','.join(unknown_discovery_routes)}")
    retrieved_at = parse_utc(args.issued_at_utc)
    runtime_root = (args.runtime_root or data_root / "runtime" / "BAT-554").resolve()
    store = RawSnapshotStore(data_root)
    discovery_results: list[dict[str, Any]] = []
    if args.discover_season:
        maximum_teams = args.maximum_discovery_teams or int(contract["discovery"]["maximum_teams_per_season"])
        selected_discovery_routes = args.discovery_route_id or list(contract["discovery"]["route_order"])

        def execute_discovery(browser: StatefulPatchrightSession | None) -> None:
            routes, _route_states = build_discovery_routes(
                contract=contract,
                env_file=args.env_file.resolve(),
                browser=browser,
                selected_route_ids=selected_discovery_routes,
            )
            if not routes:
                raise RuntimeError("no selected NCAA discovery route is available")
            for season in sorted(set(args.discover_season)):
                discovery_results.append(
                    discover_season(
                        season=season,
                        contract=contract,
                        store=store,
                        routes=routes,
                        retrieved_at=retrieved_at,
                        maximum_teams=maximum_teams,
                    )
                )

        if "local_patchright_chrome" in selected_discovery_routes:
            browser_runtime = select_browser_runtime(contract, runtime_root)
            if browser_runtime is None:
                raise RuntimeError("selected local Patchright/Chrome discovery runtime is unavailable")
            browser_config = contract["transport"]["local_patchright_chrome"]
            with StatefulPatchrightSession(
                executable_path=browser_runtime[0],
                browser_installation_root=browser_runtime[1],
                runtime_root=runtime_root,
                user_agent=str(browser_config["user_agent"]),
                challenge_wait_milliseconds=int(browser_config["wait_after_load_milliseconds"]),
                timeout_seconds=float(contract["discovery"]["request_timeout_seconds"]),
            ) as browser:
                execute_discovery(browser)
        else:
            execute_discovery(None)
        if args.discovery_only:
            print(json.dumps({"result": "NCAA_DISCOVERY_COMPLETE", "seasons": discovery_results}, indent=2, sort_keys=True))
            return 0 if all(row["discovered_contest_count"] > 0 for row in discovery_results) else 2
    elif args.discovery_only:
        raise ValueError("--discovery-only requires at least one --discover-season")
    selected_contests = [
        row for row in contract["seed_contests"] if not args.contest_id or str(row["contest_id"]) in args.contest_id
    ]
    selected_endpoints = [
        row for row in contract["endpoints"] if not args.endpoint_id or row["endpoint_id"] in args.endpoint_id
    ]
    if not selected_contests or not selected_endpoints:
        raise ValueError("contest and endpoint filters must select configured values")
    work = [(contest, endpoint) for contest in selected_contests for endpoint in selected_endpoints]
    if args.maximum_requests is not None:
        work = work[: args.maximum_requests]
    captures: list[dict[str, Any]] = []
    route_state_map: dict[str, dict[str, Any]] = {}
    for contest, endpoint in work:
        contest_id = str(contest["contest_id"])
        endpoint_id = endpoint["endpoint_id"]
        request = request_for(contract, contest, endpoint)
        routes, route_states = build_routes(
            contract=contract,
            env_file=args.env_file.resolve(),
            runtime_root=runtime_root,
            contest_id=contest_id,
            endpoint_id=endpoint_id,
        )
        for state in route_states:
            route_state_map[state["route_id"]] = state
        if args.route_id:
            routes = [row for row in routes if row[0] in args.route_id]
        result = acquire_one(
            store=store,
            request=request,
            routes=routes,
            retrieved_at=retrieved_at,
            maximum_attempts=args.maximum_attempts,
        )
        normalization: list[dict[str, Any]] = []
        if result["state"] == "CAPTURED":
            normalization = normalize_ncaa_capture(
                raw_path=data_root / result["raw_relative_path"],
                raw_sha256=result["raw_sha256"],
                contest_id=contest_id,
                endpoint_id=endpoint_id,
                source_uri=request.source_uri,
                retrieved_at_utc=result["capture_retrieved_at_utc"],
                contract=contract,
                data_root=data_root,
            )
        captures.append(
            {
                **result,
                "normalization": normalization,
                "contest_id": contest_id,
                "season": contest["season"],
                "season_type": contest["season_type"],
                "observed_matchup": contest["observed_matchup"],
                "observed_game_date": contest["observed_game_date"],
                "canonical_game_id": contest["canonical_game_id"],
                "identity_state": contest["identity_state"],
                "endpoint_id": endpoint_id,
                "domains": list(endpoint["domains"]),
                "domain_grains": {domain: contract["domain_grain"][domain] for domain in endpoint["domains"]},
                "source_uri": request.source_uri,
                "retrieved_at_utc": result.get("capture_retrieved_at_utc", iso_utc(retrieved_at)),
            }
        )
    captures.sort(key=lambda row: (int(row["contest_id"]), row["endpoint_id"]))
    core = acquisition_core(
        contract=contract,
        contract_sha256=sha256_file(contract_path),
        captures=captures,
        route_states=[route_state_map[key] for key in sorted(route_state_map)],
    )
    identity = stable_hash(core)
    manifest = {
        **core,
        "acquisition_identity": identity,
        "issued_at_utc": iso_utc(retrieved_at),
        "credentials_logged_or_persisted": False,
    }
    manifest_path = (
        data_root
        / "manifests"
        / "acquisition"
        / contract["run_id"]
        / "sha256"
        / identity
        / "ncaa_official_gamebook_acquisition_manifest.json"
    )
    manifest = install_content_addressed_manifest(
        manifest_path,
        manifest,
        core=core,
        identity_key="acquisition_identity",
        identity=identity,
    )
    manifest_sha256 = sha256_file(manifest_path)
    discovery_manifest = None
    discovery_manifest_path = None
    discovery_manifest_sha256 = None
    if args.discovery_manifest:
        discovery_manifest_path = args.discovery_manifest.resolve()
        if data_root != discovery_manifest_path and data_root not in discovery_manifest_path.parents:
            raise ValueError("discovery manifest is outside the configured external data root")
        discovery_manifest = json.loads(discovery_manifest_path.read_text(encoding="utf-8"))
        discovery_manifest_sha256 = sha256_file(discovery_manifest_path)
    gate = build_gate(
        contract=contract,
        manifest=manifest,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        discovery_manifest=discovery_manifest,
        discovery_manifest_path=discovery_manifest_path,
        discovery_manifest_sha256=discovery_manifest_sha256,
    )
    if args.gate_output:
        gate_path = args.gate_output.resolve()
        if repo_root not in gate_path.parents:
            raise ValueError("gate output must be versioned in the repository")
        write_json(gate_path, gate)
    print(
        json.dumps(
            {
                "result": gate["result"],
                "acquisition_identity": identity,
                "manifest_path": str(manifest_path),
                "manifest_sha256": manifest_sha256,
                "request_count": core["request_count"],
                "captured_count": core["captured_count"],
                "technical_failure_count": core["technical_failure_count"],
                "domain_capture_counts": core["domain_capture_counts"],
                "normalized_domain_counts": core["normalized_domain_counts"],
                "normalized_row_counts": core["normalized_row_counts"],
                "credentials_logged_or_persisted": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if core["captured_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
