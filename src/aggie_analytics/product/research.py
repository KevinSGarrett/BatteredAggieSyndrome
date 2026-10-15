r"""Private retrospective research profiles for the BAS product API (BAT-728, Cycle #57 TP57-A01).

An operator may configure the existing FastAPI application with explicit research profiles; HTTP clients can only
name a registered profile ID and typed selectors. Nothing here is a forecast: every response is
RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED and predictive skill NOT_ESTABLISHED.

Configuration (``BAS-RESEARCH-PROFILE-CONFIG-1``) is a JSON object read once at application start::

    {"schema": "BAS-RESEARCH-PROFILE-CONFIG-1",
     "profiles": [{"profile_id": "national-retrospective-reference-2016-2023",
                   "display_label": "...",                       # optional
                   "reference_database": "<abs>/national_retrospective_reference_2016_2023/sha256/<id>/national_retrospective_reference.sqlite",
                   "reference_manifest": "<abs>/run_manifest.json",  # optional; default: the canonical manifest layout
                   "history_database": "<abs>/.../national_history.sqlite",
                   "population_database": "<abs>/.../national_population.sqlite",
                   "expected": {"database_identity": "...", "content_identity": "...", "database_sha256": "...",
                                "contract_sha256": "...", "history_identity": "...", "population_identity": "..."}}]}

The whole configuration is validated before any named path is opened: the exact key sets, JSON types (strings only;
no number, boolean or duplicate key), profile IDs, lowercase 64-hex identities equal to the packaged accepted pins
(:data:`aggie_analytics.retrospective_baseline.reference.REFERENCE_PROFILE` and the reader's anchors), and every
location by :func:`validate_location` (absolute local paths only; network shares, device and namespace spellings,
``.``/``..`` traversal and spellings Windows would silently rewrite are refused lexically). A profile is then
verified once, in a background thread, by the accepted reader
(:class:`~aggie_analytics.retrospective_baseline.reference.ReferenceComparison`: inputs verified and pinned, every
record, the refit and both identities re-derived); until it completes the profile answers
``RESEARCH_PROFILE_VERIFYING``. A refused profile is ``UNAVAILABLE`` with the reader's own refusal code and serves
nothing; a profile whose files change after verification becomes ``UNAVAILABLE`` (``RESEARCH_PROFILE_STALE``) and is
never silently re-opened or substituted.

Serving delegates the record selection to the accepted reader's query (the same season, team, game, model, partition
and slice semantics, refusals and summary selection rule) and adds only: the canonical game catalog, a game detail,
both-team prior-game exclusion lineage from the accepted history views, exact paging bounds, comparisons against a
chosen probability baseline on the reader-verified common support, and controlled errors that never carry a path,
traceback, credential or raw page. Ridge stays margin-only; no probability, interval, confidence band or new aggregate
is invented.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics import readonly_sqlite

CONFIG_SCHEMA = "BAS-RESEARCH-PROFILE-CONFIG-1"
API_SCHEMA = "BAS-RESEARCH-API-1"
API_VERSION = "v1"
PROFILE_KIND = "NATIONAL_RETROSPECTIVE_REFERENCE_2016_2023"
PROFILE_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,63}\Z")
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
SEASON_RE = re.compile(r"[0-9]{4}\Z")
LIMIT_RE = re.compile(r"[0-9]{1,4}\Z")
OFFSET_RE = re.compile(r"[0-9]{1,9}\Z")
DEFAULT_LIMIT = 50
MAX_LIMIT = 500
MAX_TEXT = 120
MAX_PROFILES = 8
REFERENCE_DB_FILE = "national_retrospective_reference.sqlite"
REFERENCE_POPULATION = "national_retrospective_reference_2016_2023"
HISTORY_DB_FILE = "national_history.sqlite"
POPULATION_DB_FILE = "national_population.sqlite"
MANIFEST_FILE = "run_manifest.json"
EXPECTED_KEYS = ("database_identity", "content_identity", "database_sha256", "contract_sha256", "history_identity",
                 "population_identity")
REQUIRED_PROFILE_KEYS = ("profile_id", "reference_database", "history_database", "population_database", "expected")
OPTIONAL_PROFILE_KEYS = ("display_label", "reference_manifest")
#: Labels carried by every research response and view (TP57 section 1).
SURFACE_LABELS = {"research_surface": "RETROSPECTIVE_RESEARCH", "trust_state": "UNTRUSTED_SHADOW",
                  "pit_admission": "PIT_NOT_ADMITTED", "predictive_skill": "NOT_ESTABLISHED",
                  "forecast_status": "NOT_A_FORECAST_RETROSPECTIVE_RESEARCH_ONLY",
                  "activation": "EXPLICIT_OPERATOR_PROFILE_ONLY_NEVER_A_DEFAULT",
                  "comparison_2023": "ALREADY_EXPOSED_OUT_OF_FIT_DEVELOPMENT_COMPARISON_NOT_BLIND"}
#: Grains served for a profile and the selectors applicable to each (anything else is FILTER_NOT_APPLICABLE).
GRAIN_FILTERS = {
    "games": ("season", "team", "game", "partition"),
    "features": ("season", "team", "game", "partition"),
    "estimates": ("season", "team", "game", "model", "partition"),
    "scores": ("season", "team", "game", "model", "partition"),
    "parameters": ("model",),
    "summary": ("season", "team", "game", "model", "partition", "slice"),
    "comparisons": ("season", "team", "game", "model", "partition", "slice", "baseline"),
}
PAGING = ("limit", "offset")
ALL_SELECTORS = ("season", "team", "game", "model", "partition", "slice", "baseline")
READER_GRAIN = {"features": "reference-feature", "estimates": "reference-estimate", "scores": "reference-score",
                "parameters": "reference-parameter", "summary": "reference-summary",
                "comparisons": "reference-summary"}
#: Windows device names (a path component naming one opens the device, not a file).
_WINDOWS_DEVICES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10)),
                    "conin$", "conout$"}
_POSIX_DEVICE_ROOTS = ("dev", "proc", "sys")
_LONG_PATH = 240


class ResearchError(Exception):
    """A controlled research refusal: a stable code, an HTTP status and a fixed message (never a path or traceback)."""

    def __init__(self, code: str, message: str, status: int = 400, retry_after: int | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.status = status
        self.retry_after = retry_after

    def payload(self) -> dict[str, Any]:
        return {"api_version": API_VERSION, "schema": API_SCHEMA, "labels": dict(SURFACE_LABELS),
                "error": {"code": self.code, "message": self.message, "status": self.status}}


class ResearchConfigError(ResearchError):
    """A refused operator configuration (raised by the application factory; the server does not start)."""


# --------------------------------------------------------------------------------------------- locations

def validate_location(text: Any, *, os_name: str | None = None) -> str:
    """The validated spelling of one configured local file location, refused lexically before any filesystem access.

    Windows: an absolute drive path ``X:\\...`` (``/`` accepted as a separator) or its native extended-length form
    ``\\\\?\\X:\\...``; UNC shares (``\\\\server``, ``//server``, ``\\\\?\\UNC``), every ``\\\\.\\`` device spelling,
    other ``\\\\?\\`` namespaces, reserved device names, alternate data streams, ``.``/``..`` components, empty
    components and components Windows would silently rewrite (a trailing dot or space) are refused. POSIX: an absolute
    path whose components are not ``.``/``..`` and that is not under /dev, /proc or /sys; every other character
    (backslash, colon, ``?``, ``#``, spaces, non-ASCII) is an ordinary filename character there."""
    os_name = os.name if os_name is None else os_name
    if not isinstance(text, str):
        raise ResearchConfigError("RESEARCH_LOCATION_INVALID", "a configured location must be a JSON string")
    if not text or len(text) > 32000 or any(ord(ch) < 32 for ch in text):
        raise ResearchConfigError("RESEARCH_LOCATION_INVALID", "a configured location is empty, too long or holds a "
                                                               "control character")
    if os_name == "nt":
        if text.startswith(("\\\\", "//", "\\/", "/\\")):
            if text.startswith("\\\\?\\") and re.match(r"\\\\\?\\[A-Za-z]:\\", text):
                body = text[4:]
                if "/" in body:
                    raise ResearchConfigError("RESEARCH_LOCATION_NOT_LITERAL", "an extended-length location may not "
                                                                               "hold a forward slash")
                parts = body[3:].split("\\")
            elif text.startswith("\\\\.\\"):
                raise ResearchConfigError("RESEARCH_LOCATION_UNSUPPORTED", "a device namespace location is not "
                                                                           "supported")
            else:
                raise ResearchConfigError("RESEARCH_LOCATION_UNSUPPORTED", "a network share or namespace location is "
                                                                           "not supported")
        elif re.match(r"[A-Za-z]:[\\/]", text):
            parts = re.split(r"[\\/]", text[3:])
        else:
            raise ResearchConfigError("RESEARCH_LOCATION_NOT_ABSOLUTE", "a configured location must be an absolute "
                                                                        "local drive path")
        for part in parts:
            if part in ("", ".", ".."):
                raise ResearchConfigError("RESEARCH_LOCATION_TRAVERSAL" if part in (".", "..") else
                                          "RESEARCH_LOCATION_NOT_LITERAL",
                                          "a configured location holds an empty, '.' or '..' component")
            if part[-1] in (".", " ") or ":" in part:
                raise ResearchConfigError("RESEARCH_LOCATION_NOT_LITERAL", "a component ends in a dot or space or "
                                                                           "names a stream")
            if part.split(".")[0].rstrip(" ").lower() in _WINDOWS_DEVICES:
                raise ResearchConfigError("RESEARCH_LOCATION_UNSUPPORTED", "a component names a device")
        return text
    if not text.startswith("/"):
        raise ResearchConfigError("RESEARCH_LOCATION_NOT_ABSOLUTE", "a configured location must be an absolute path")
    parts = text[1:].split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ResearchConfigError("RESEARCH_LOCATION_TRAVERSAL" if any(p in (".", "..") for p in parts) else
                                  "RESEARCH_LOCATION_NOT_LITERAL",
                                  "a configured location holds an empty, '.' or '..' component")
    if parts[0] in _POSIX_DEVICE_ROOTS:
        raise ResearchConfigError("RESEARCH_LOCATION_UNSUPPORTED", "a device or kernel namespace location is not "
                                                                   "supported")
    return text


def io_location(text: str) -> str:
    """The spelling every file API (and SQLite) opens for a validated location: on Windows a long ordinary location
    becomes its native extended-length form (the same file, since the spelling holds no component Windows rewrites)."""
    if os.name == "nt" and not text.startswith("\\\\?\\") and len(text) >= _LONG_PATH:
        return "\\\\?\\" + os.path.abspath(text)
    return text


def _layout(path: str, *, os_name: str, file_name: str, identity: str | None = None,
            population: str | None = None) -> None:
    """The configured file name, identity directory and population root of a location (lexical), read under the same
    interpretation ``os_name`` that validated its spelling, whatever the host: a Windows ``/`` is a separator, a POSIX
    backslash an ordinary filename character."""
    parts = re.split(r"[\\/]", path) if os_name == "nt" else path.split("/")
    if parts[-1] != file_name:
        raise ResearchConfigError("RESEARCH_PROFILE_LAYOUT_INVALID", f"the location must name {file_name}")
    if identity is not None and (len(parts) < 4 or parts[-2] != identity or parts[-3] != "sha256"):
        raise ResearchConfigError("RESEARCH_PROFILE_LAYOUT_INVALID", "the location's identity directory differs from "
                                                                     "the expected identity")
    if population is not None and parts[-4] != population:
        raise ResearchConfigError("RESEARCH_PROFILE_LAYOUT_INVALID", "the location is not in the reference population "
                                                                     "layout")


# --------------------------------------------------------------------------------------------- configuration

@dataclass(frozen=True)
class ProfileConfig:
    profile_id: str
    display_label: str
    reference_database: str
    reference_manifest: str | None
    history_database: str
    population_database: str
    expected: Mapping[str, str]


def accepted_pins() -> dict[str, str]:
    """The packaged accepted pins a JSON operator configuration must name exactly (independently validated by the
    Cycle 56 manager and packaged with the reader; never the configuration's own claims)."""
    from aggie_analytics.retrospective_baseline import reference as rc  # noqa: PLC0415 - configured profiles only
    profile = rc.REFERENCE_PROFILE or {}
    return {"database_identity": profile.get("database_identity"), "content_identity": profile.get("content_identity"),
            "database_sha256": profile.get("database_sha256"), "contract_sha256": rc.ANCHORS["contract_sha256"],
            "history_identity": rc.ANCHORS["history"]["database_identity"],
            "population_identity": rc.ANCHORS["population"]["database_identity"]}


def _strict_json(data: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [k for k, _v in items]
        if len(keys) != len(set(keys)):
            raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "the configuration repeats a JSON key")
        return dict(items)

    def number(_text: str) -> Any:
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "the configuration holds a JSON number")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_float=number, parse_int=number,
                          parse_constant=number)
    except ResearchConfigError:
        raise
    except (UnicodeDecodeError, ValueError) as exc:
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "the configuration is not UTF-8 JSON") from exc


def _profile(item: Any, pins: Mapping[str, str], os_name: str) -> ProfileConfig:
    if not isinstance(item, dict):
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "a profile must be a JSON object")
    keys = set(item)
    if not set(REQUIRED_PROFILE_KEYS) <= keys or not keys <= set(REQUIRED_PROFILE_KEYS) | set(OPTIONAL_PROFILE_KEYS):
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "a profile has missing or unknown members")
    pid = item["profile_id"]
    if not isinstance(pid, str) or not PROFILE_ID_RE.match(pid):
        raise ResearchConfigError("RESEARCH_PROFILE_ID_INVALID", "a profile ID must be 3-64 lowercase letters, digits "
                                                                 "or hyphens")
    label = item.get("display_label", "National retrospective reference 2016-2023")
    if not isinstance(label, str) or not label.strip() or len(label) > MAX_TEXT or any(ord(c) < 32 for c in label):
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "a display label must be short printable text")
    expected = item["expected"]
    if not isinstance(expected, dict) or set(expected) != set(EXPECTED_KEYS):
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "expected must name exactly the six identities")
    for key in EXPECTED_KEYS:
        value = expected[key]
        if not isinstance(value, str) or not HEX64_RE.match(value):
            raise ResearchConfigError("RESEARCH_IDENTITY_INVALID", "an identity must be 64 lowercase hex characters")
        if value != pins.get(key):
            raise ResearchConfigError("RESEARCH_PROFILE_PIN_UNACCEPTED", f"{key} differs from the accepted pin")
    locations = {}
    for key in ("reference_database", "history_database", "population_database", "reference_manifest"):
        if key in item:
            locations[key] = validate_location(item[key], os_name=os_name)
    _layout(locations["reference_database"], os_name=os_name, file_name=REFERENCE_DB_FILE,
            identity=expected["database_identity"], population=REFERENCE_POPULATION)
    _layout(locations["history_database"], os_name=os_name, file_name=HISTORY_DB_FILE,
            identity=expected["history_identity"])
    _layout(locations["population_database"], os_name=os_name, file_name=POPULATION_DB_FILE,
            identity=expected["population_identity"])
    if "reference_manifest" in locations:
        _layout(locations["reference_manifest"], os_name=os_name, file_name=MANIFEST_FILE,
                identity=expected["database_identity"])
    return ProfileConfig(profile_id=pid, display_label=label.strip(),
                         reference_database=locations["reference_database"],
                         reference_manifest=locations.get("reference_manifest"),
                         history_database=locations["history_database"],
                         population_database=locations["population_database"], expected=dict(expected))


def load_config(source: str | os.PathLike[str] | Mapping[str, Any], *, pins: Mapping[str, str] | None = None,
                os_name: str | None = None) -> list[ProfileConfig]:
    """Validate a complete operator configuration (a JSON file location or an in-memory mapping) before any profile
    location is opened. ``pins`` defaults to the packaged accepted pins; only the operator's own Python code can
    supply others (fixture worlds), never a request. ``os_name`` (``"nt"`` Windows, otherwise POSIX; default the
    host's, which the server always uses) is resolved once and governs every spelling and layout check; files are
    always opened by the host."""
    os_name = os.name if os_name is None else os_name
    if isinstance(source, Mapping):
        doc: Any = json.loads(json.dumps(source))
        _reject_numbers(doc)
    else:
        spelling = validate_location(os.fspath(source), os_name=os_name)
        try:
            data = Path(io_location(spelling)).read_bytes()
        except OSError as exc:
            raise ResearchConfigError("RESEARCH_CONFIG_UNREADABLE", "the configuration file cannot be read") from exc
        doc = _strict_json(data)
    if not isinstance(doc, dict) or set(doc) != {"schema", "profiles"}:
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "the configuration must hold exactly schema and profiles")
    if doc["schema"] != CONFIG_SCHEMA:
        raise ResearchConfigError("RESEARCH_CONFIG_SCHEMA_UNSUPPORTED", f"the configuration schema must be "
                                                                        f"{CONFIG_SCHEMA}")
    profiles = doc["profiles"]
    if not isinstance(profiles, list) or not profiles or len(profiles) > MAX_PROFILES:
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", f"profiles must be a list of 1 to {MAX_PROFILES} objects")
    accepted = dict(pins) if pins is not None else accepted_pins()
    out = [_profile(item, accepted, os_name) for item in profiles]
    ids = [p.profile_id for p in out]
    if len(ids) != len(set(ids)):
        raise ResearchConfigError("RESEARCH_PROFILE_ID_DUPLICATE", "profile IDs must be unique")
    return out


def _reject_numbers(value: Any) -> None:
    if isinstance(value, bool) or isinstance(value, (int, float)):
        raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "the configuration holds a non-string scalar")
    if isinstance(value, dict):
        for item in value.values():
            _reject_numbers(item)
    elif isinstance(value, list):
        for item in value:
            _reject_numbers(item)


# --------------------------------------------------------------------------------------------- selectors

def parse_query(grain: str, items: list[tuple[str, str]]) -> dict[str, Any]:
    """Typed selectors and paging from the raw query items: unknown or repeated names, inapplicable selectors and
    malformed values refuse with their own codes; values are never paths, SQL or expressions."""
    if grain not in GRAIN_FILTERS:
        raise ResearchError("UNKNOWN_GRAIN", "unknown research grain", 404)
    seen: dict[str, str] = {}
    for name, value in items:
        if name not in ALL_SELECTORS and name not in PAGING:
            raise ResearchError("UNKNOWN_PARAMETER", "the request names a parameter this API does not accept")
        if name in seen:
            raise ResearchError("PARAMETER_REPEATED", "a parameter may appear at most once")
        seen[name] = value
    for name in seen:
        if name in ALL_SELECTORS and name not in GRAIN_FILTERS[grain]:
            raise ResearchError("FILTER_NOT_APPLICABLE", f"{name} does not apply to the {grain} grain")
    out: dict[str, Any] = {}
    if "season" in seen:
        if not SEASON_RE.match(seen["season"]):
            raise ResearchError("SEASON_INVALID", "season must be a four-digit year")
        out["season"] = int(seen["season"])
    for name, code in (("team", "TEAM_INVALID"), ("game", "GAME_INVALID")):
        if name in seen:
            text = seen[name].strip()
            if not text or len(text) > MAX_TEXT or any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
                raise ResearchError(code, f"{name} must be 1-{MAX_TEXT} printable characters")
            out[name] = text
    for name in ("model", "partition", "slice", "baseline"):
        if name in seen:
            out[name] = seen[name]
    limit = seen.get("limit")
    if limit is None:
        out["limit"] = DEFAULT_LIMIT
    elif not LIMIT_RE.match(limit) or not 1 <= int(limit) <= MAX_LIMIT:
        raise ResearchError("LIMIT_INVALID", f"limit must be an integer from 1 to {MAX_LIMIT}")
    else:
        out["limit"] = int(limit)
    offset = seen.get("offset")
    if offset is None:
        out["offset"] = 0
    elif not OFFSET_RE.match(offset):
        raise ResearchError("OFFSET_INVALID", "offset must be a non-negative integer below one billion")
    else:
        out["offset"] = int(offset)
    return out


def _page(rows: list[Any], offset: int, limit: int) -> tuple[list[Any], int | None]:
    page = rows[offset:offset + limit]
    return page, offset + len(page) if offset + len(page) < len(rows) else None


# --------------------------------------------------------------------------------------------- one profile

STATE_NOT_STARTED, STATE_VERIFYING, STATE_AVAILABLE, STATE_UNAVAILABLE = (
    "NOT_STARTED", "VERIFYING", "AVAILABLE", "UNAVAILABLE")


@dataclass
class _Served:
    ref: Any
    rc: Any
    bm: Any
    catalog: list[dict[str, Any]]
    by_key: dict[str, dict[str, Any]]
    labels: dict[str, dict[str, Any]]
    exclusions: dict[tuple[str, str, str], list[dict[str, Any]]]
    features: dict[tuple[str, str], dict[str, Any]]
    estimates: dict[str, list[dict[str, Any]]]
    scores: dict[str, list[dict[str, Any]]]
    stats: dict[str, tuple[str, tuple[int, int]]]
    identities: dict[str, Any]
    seconds: float
    adverse: dict[str, Any] = field(default_factory=dict)


class ResearchProfile:
    """One registered profile: validated configuration, background verification by the accepted reader, serving."""

    def __init__(self, config: ProfileConfig, *, anchors: Mapping[str, Any] | None = None) -> None:
        self.config = config
        self._anchors = anchors
        self._lock = threading.Lock()
        self._state = STATE_NOT_STARTED
        self._code: str | None = None
        self._served: _Served | None = None
        self._thread: threading.Thread | None = None
        self._started_at: float | None = None

    # ---- lifecycle
    def start(self) -> None:
        with self._lock:
            if self._state != STATE_NOT_STARTED:
                return
            self._state = STATE_VERIFYING
            self._started_at = time.time()
            self._thread = threading.Thread(target=self._verify, name=f"research-verify-{self.config.profile_id}",
                                            daemon=True)
            self._thread.start()

    def wait(self, timeout: float | None = None) -> str:
        """Start verification if needed and wait for it to settle (operator and test use)."""
        self.start()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return self.state

    @property
    def state(self) -> str:
        return self._state

    def _fail(self, code: str) -> None:
        with self._lock:
            self._state, self._code, self._served = STATE_UNAVAILABLE, code, None

    def _verify(self) -> None:
        from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: PLC0415
        from aggie_analytics.retrospective_baseline import reference as rc  # noqa: PLC0415
        cfg, t0 = self.config, time.time()
        paths = {"reference_database": io_location(cfg.reference_database),
                 "history_database": io_location(cfg.history_database),
                 "population_database": io_location(cfg.population_database)}
        if cfg.reference_manifest is not None:
            paths["reference_manifest"] = io_location(cfg.reference_manifest)
        anchors = dict(self._anchors) if self._anchors is not None else rc.ANCHORS
        try:
            for key, location in paths.items():
                readonly_sqlite.literal_path(location)
                if not Path(location).is_file():
                    self._fail("RESEARCH_PROFILE_FILE_MISSING")
                    return
            manifest = Path(paths["reference_manifest"]) if "reference_manifest" in paths else None
            ref = rc.ReferenceComparison(Path(paths["reference_database"]),
                                         history_database=Path(paths["history_database"]),
                                         population_database=Path(paths["population_database"]), manifest=manifest,
                                         expect_identity=cfg.expected["database_identity"], anchors=anchors)
            try:
                inputs = rc.load_inputs(Path(paths["history_database"]), Path(paths["population_database"]), anchors)
                manifest_path = Path(ref.binding["manifest"])
                verified = {"database_identity": ref.database_identity, "content_identity": ref.content_identity,
                            "database_sha256": ref.binding["sha256"], "contract_sha256": anchors["contract_sha256"],
                            "history_identity": ref.history_identity, "population_identity": ref.population_identity}
                if verified != dict(cfg.expected) or \
                        inputs["history"]["binding"]["database_identity"] != cfg.expected["history_identity"] or \
                        inputs["pool"]["binding"]["database_identity"] != cfg.expected["population_identity"]:
                    self._fail("RESEARCH_PROFILE_IDENTITY_MISMATCH")
                    return
                served = self._index(ref, rc, bm, inputs)
                stats_paths = dict(paths, reference_manifest=str(manifest_path))
                served.stats = {k: (v, _stat(v)) for k, v in stats_paths.items()}
                served.identities = {**verified, "manifest_sha256": rc.sha256_file(manifest_path),
                                     "contract_id": anchors["contract_id"],
                                     "benchmark_identity": anchors["benchmark"]["database_identity"]}
                served.seconds = round(time.time() - t0, 3)
            finally:
                ref.close()
        except rc.ReferenceError as exc:
            self._fail(exc.code)
            return
        except readonly_sqlite.DatabaseLocationError as exc:
            self._fail(exc.code)
            return
        except Exception:  # noqa: BLE001 - any other failure is a closed, codeless refusal (never exposed)
            self._fail("RESEARCH_PROFILE_VERIFICATION_FAILED")
            return
        with self._lock:
            self._served, self._state, self._code = served, STATE_AVAILABLE, None

    @staticmethod
    def _index(ref: Any, rc: Any, bm: Any, inputs: dict[str, Any]) -> _Served:
        derived = ref.derived
        labels = {lab["contest_key"]: lab for lab in derived["labels"]}
        features = {(f["contest_key"], f["view"]): f for f in derived["features"]}
        exclusions: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for row in inputs["history"]["views"]:
            record = json.loads(row[7])
            for side, block in (("team", record.get("team_history")), ("opponent", record.get("opponent_history"))):
                exclusions[(row[1], row[2], side)] = [
                    {"contest_key": e.get("contest_key"), "contest_date": e.get("contest_date"),
                     "opponent_key": e.get("opponent_key"), "reasons": list(e.get("reasons") or [])}
                    for e in (block or {}).get("excluded_inputs") or []]
        estimates: dict[str, list[dict[str, Any]]] = {}
        for e in derived["estimates"]:
            estimates.setdefault(e["contest_key"], []).append(e)
        scores: dict[str, list[dict[str, Any]]] = {}
        for s in derived["scores"]:
            scores.setdefault(s["contest_key"], []).append(s)
        catalog, by_key = [], {}
        for target in derived["targets"]:
            key = target["contest_key"]
            a_feature = features[(key, "A")]
            label = labels[key]
            row = {"record_type": "research_game", "game_key": key, "season": target["season"],
                   "contest_date": target["contest_date"], "partition": a_feature["partition"],
                   "fit_role": a_feature["fit_role"], "site": target["site"],
                   "a_key": target["a_key"], "a_name": target["a_team_name"], "a_org_id": target["a_org_id"],
                   "b_key": target["b_key"], "b_name": target["b_team_name"], "b_org_id": target["b_org_id"],
                   "a_prior_games": a_feature["team"]["games"], "b_prior_games": a_feature["opponent"]["games"],
                   "texas_am_target": a_feature["texas_am_target"],
                   "first_four_team_games": a_feature["first_four_team_games"], "cold_start": a_feature["cold_start"],
                   "label": {"a_points": label.get("a_points"), "b_points": label.get("b_points"),
                             "a_result": label.get("a_result"), "label_state": label.get("label_state"),
                             "y_a": label.get("y_a")},
                   "orientations": ["A", "B"], "label_authority": label.get("label_authority")}
            catalog.append(row)
            by_key[key] = row
        served = _Served(ref=ref, rc=rc, bm=bm, catalog=catalog, by_key=by_key, labels=labels,
                         exclusions=exclusions, features=features, estimates=estimates, scores=scores, stats={},
                         identities={}, seconds=0.0)
        served.adverse = _adverse_2023(derived["summary"]["rows"], rc)
        return served

    # ---- serving
    def _available(self) -> _Served:
        if self._state == STATE_NOT_STARTED:
            self.start()
        state, code, served = self._state, self._code, self._served
        if state == STATE_VERIFYING or state == STATE_NOT_STARTED:
            raise ResearchError("RESEARCH_PROFILE_VERIFYING", "the profile is being verified by the accepted reader",
                                503, retry_after=2)
        if state != STATE_AVAILABLE or served is None:
            raise ResearchError(code or "RESEARCH_PROFILE_UNAVAILABLE", "the profile is unavailable; nothing is served",
                                503)
        for location, recorded in served.stats.values():
            if _stat(location) != recorded:
                self._fail("RESEARCH_PROFILE_STALE")
                raise ResearchError("RESEARCH_PROFILE_STALE", "a profile file changed after verification; the profile "
                                                              "is closed until the server restarts", 503)
        return served

    def summary(self) -> dict[str, Any]:
        """The profile's identity, state and limitations (never a location)."""
        state = self._state
        out = {"profile_id": self.config.profile_id, "display_label": self.config.display_label, "kind": PROFILE_KIND,
               "state": state, "refusal_code": self._code if state == STATE_UNAVAILABLE else None,
               "expected_identities": dict(self.config.expected), "labels": dict(SURFACE_LABELS)}
        if state == STATE_AVAILABLE and self._served is not None:
            out["verified_identities"] = dict(self._served.identities)
            out["verification_seconds"] = self._served.seconds
        return out

    def detail(self) -> dict[str, Any]:
        served = self._available()
        rc = served.rc
        derived = served.ref.derived
        pop = derived["summary"]["population"]
        return {**self.summary(), "reference_labels": dict(rc.LABELS),
                "coverage": {"games": len(served.catalog), "feature_records": len(derived["features"]),
                             "estimates": len(derived["estimates"]), "scores": len(derived["scores"]),
                             "labels": len(derived["labels"]), "parameters": len(derived["parameters"]),
                             "summary_rows": len(derived["summary"]["rows"]),
                             "comparison_rows": len(derived["summary"]["comparisons"]),
                             "training_targets": pop["training_targets"],
                             "comparison_targets": pop["comparison_targets"], "pool_games": pop["pool_games"],
                             "texas_am_targets": pop["texas_am_targets"], "cold_start_targets": pop["cold_start_targets"],
                             "first_four_team_games_targets": pop["first_four_team_games_targets"],
                             "label_states": pop["label_states"]},
                "seasons": list(rc.TARGET_SEASONS), "protected_seasons": list(rc.PROTECTED_SEASONS),
                "partitions": [{"partition_id": p["split_id"], "role": p["role"], "seasons": list(p["seasons"])}
                               for p in rc.SPLIT["partitions"]],
                "slices": dict(rc.SLICES),
                "models": [{"model_id": m, "family": rc.MODELS[m].get("family"),
                            "definition_output": rc.MODELS[m].get("output"), "role": rc.MODELS[m].get("role"),
                            "fitted": rc.MODELS[m].get("fitted"),
                            "metric_kind": "PROBABILITY" if m in rc.PROBABILITY_MODELS else "MARGIN",
                            "probability_served": m in rc.PROBABILITY_MODELS} for m in rc.MODEL_IDS],
                "grains": {g: {"selectors": list(f), "paging": {"default_limit": DEFAULT_LIMIT, "max_limit": MAX_LIMIT}}
                           for g, f in GRAIN_FILTERS.items()},
                "adverse_2023": served.adverse,
                "limitations": ["Retrospective research over accepted 2016-2023 targets only; not a forecast.",
                                "Calendar-date order only: no publication-time (PIT) admission.",
                                "Predictive skill, calibration and a champion are not established.",
                                "2023 is an already-exposed out-of-fit comparison, never a blind test.",
                                "The ridge reference serves an expected margin only; no probability or interval.",
                                "2024/2025 protected labels and future shadow values are not reachable here."]}

    def query(self, grain: str, items: list[tuple[str, str]]) -> dict[str, Any]:
        q = parse_query(grain, items)
        served = self._available()
        rc = served.rc
        filters = {k: q[k] for k in ALL_SELECTORS if k in q}
        result: dict[str, Any] = {"api_version": API_VERSION, "schema": API_SCHEMA,
                                  "profile_id": self.config.profile_id, "grain": grain, "labels": dict(SURFACE_LABELS),
                                  "reference_identity": served.identities["database_identity"],
                                  "content_identity": served.identities["content_identity"],
                                  "offset": q["offset"], "limit": q["limit"]}
        if grain == "games":
            rows, normalized, scope = self._catalog(served, filters)
            result.update(filters=normalized, season_scope_state=scope)
        else:
            rows, normalized, scope, selection = self._records(served, grain, filters)
            result.update(filters=normalized, season_scope_state=scope)
            if selection is not None:
                result["summary_selection"] = selection
        page, next_offset = _page(rows, q["offset"], q["limit"])
        if grain == "features":
            page = [self._with_lineage(served, r) for r in page]
        result.update(total=len(rows), returned=len(page), next_offset=next_offset, rows=page)
        return result

    def game(self, game_key: str) -> dict[str, Any]:
        served = self._available()
        text = (game_key or "").strip()
        if not text or len(text) > MAX_TEXT or any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
            raise ResearchError("GAME_INVALID", f"game must be 1-{MAX_TEXT} printable characters")
        try:
            key = served.ref.filters("reference-score", contest=text)["contest"]
        except served.rc.ReferenceError as exc:
            raise ResearchError(exc.code, "the game key is not a parent contest key") from exc
        row = served.by_key.get(key)
        if row is None:
            raise ResearchError("GAME_NOT_IN_PROFILE", "no accepted 2016-2023 target has this game key", 404)
        return {"api_version": API_VERSION, "schema": API_SCHEMA, "profile_id": self.config.profile_id,
                "labels": dict(SURFACE_LABELS), "reference_identity": served.identities["database_identity"],
                "game": row, "label": served.labels[key],
                "features": [self._with_lineage(served, served.features[(key, v)]) for v in ("A", "B")],
                "estimates": served.estimates.get(key, []), "scores": served.scores.get(key, [])}

    # ---- grain helpers
    @staticmethod
    def _scope(rc: Any, season: int | None) -> str:
        if season is None or season in rc.TARGET_SEASONS:
            return "RETROSPECTIVE_2016_2023"
        if season in rc.PROTECTED_SEASONS:
            return "PROTECTED_SEASON_NOT_IN_REFERENCE"
        return "FORWARD_SEASON_NOT_IN_REFERENCE" if season >= rc.FORWARD_SEASONS_FROM else "OUTSIDE_REFERENCE_SCOPE"

    def _catalog(self, served: _Served, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
        rc, bm = served.rc, served.bm
        try:
            normalized = served.ref.filters("reference-score", season=filters.get("season"), team=filters.get("team"),
                                            contest=filters.get("game"), partition=filters.get("partition"))
        except rc.ReferenceError as exc:
            raise ResearchError(exc.code, "a selector is not valid for this profile") from exc
        scope = self._scope(rc, normalized.get("season"))
        out_filters = {("game" if k == "contest" else k): v for k, v in normalized.items()}
        if scope != "RETROSPECTIVE_2016_2023":
            return [], out_filters, scope
        rows = []
        for row in served.catalog:
            if "season" in normalized and row["season"] != normalized["season"]:
                continue
            if "partition" in normalized and row["partition"] != normalized["partition"]:
                continue
            if "contest" in normalized and row["game_key"] != normalized["contest"]:
                continue
            if "team" in normalized and not any(bm.team_matches(normalized["team"], row["season"], side,
                                                                served.ref.names)
                                                for side in (row["a_key"], row["b_key"])):
                continue
            rows.append(row)
        return rows, out_filters, scope

    def _records(self, served: _Served, grain: str, filters: dict[str, Any]
                 ) -> tuple[list[dict[str, Any]], dict[str, Any], str, dict[str, Any] | None]:
        rc = served.rc
        baseline = filters.get("baseline")
        if grain == "comparisons" and baseline is not None and baseline not in rc.PROBABILITY_MODELS:
            raise ResearchError("BASELINE_INVALID" if baseline not in rc.MODEL_IDS else "BASELINE_NOT_PROBABILITY",
                                "baseline must be one of the four probability models")
        model = filters.get("model")
        reader_model = None if grain == "comparisons" else model
        try:
            doc = served.ref.query(READER_GRAIN[grain], season=filters.get("season"), team=filters.get("team"),
                                   contest=filters.get("game"), model=reader_model,
                                   partition=filters.get("partition"), slice_id=filters.get("slice"), limit=None,
                                   offset=0, all_rows=True)
        except rc.ReferenceError as exc:
            raise ResearchError(exc.code, "a selector is not valid for this profile") from exc
        normalized = {("game" if k == "contest" else k): v for k, v in (doc.get("filters") or {}).items()}
        if model is not None:
            if model not in rc.MODEL_IDS:
                raise ResearchError("MODEL_UNKNOWN", "model must be one of the five declared models")
            normalized["model"] = model
        if baseline is not None:
            normalized["baseline"] = baseline
        rows = list(doc.get("rows") or [])
        if grain == "summary":
            rows = [r for r in rows if r.get("record_type") == "reference_summary_row"]
        elif grain == "comparisons":
            summary_rows = [r for r in rows if r.get("record_type") == "reference_summary_row"]
            if baseline is None or baseline == rc.MODEL_NULL:
                rows = [r for r in rows if r.get("record_type") == "reference_comparison_row"]
            else:
                rows = _baseline_comparisons(summary_rows, baseline, rc)
            if model is not None:
                rows = [r for r in rows if r.get("model_id") == model]
        return rows, normalized, doc.get("season_scope_state") or "RETROSPECTIVE_2016_2023", \
            ({k: v for k, v in doc["summary_selection"].items()} if "summary_selection" in doc else None)

    @staticmethod
    def _with_lineage(served: _Served, record: dict[str, Any]) -> dict[str, Any]:
        """A served feature record unchanged plus the accepted history's excluded prior inputs of both sides."""
        key, view = record["contest_key"], record["view"]
        return {**record, "excluded_prior_inputs": {"team": served.exclusions.get((key, view, "team"), []),
                                                    "opponent": served.exclusions.get((key, view, "opponent"), [])},
                "excluded_prior_inputs_source": "ACCEPTED_HISTORY_VIEW_EXCLUDED_INPUTS"}


def _stat(location: str) -> tuple[int, int]:
    try:
        st = os.stat(location)
    except OSError:
        return (-1, -1)
    return (st.st_size, st.st_mtime_ns)


def _frac(value: Mapping[str, int]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def _baseline_comparisons(summary_rows: list[dict[str, Any]], baseline: str, rc: Any) -> list[dict[str, Any]]:
    """Model-minus-baseline differences of the served summary means on the reader-verified common support (the reader
    refuses a summary whose four probability families differ in scored game keys), built exactly as the reader builds
    its model-minus-NULL comparisons: an exact rational Brier difference and the binary64 difference of the served log
    loss means."""
    out = []
    groups: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in summary_rows:
        groups.setdefault((row["slice"], row["scope_id"]), {})[row["model_id"]] = row
    for (slice_id, scope_id), by_model in groups.items():
        base = by_model.get(baseline)
        if base is None:
            continue
        for model_id in rc.PROBABILITY_MODELS:
            if model_id == baseline or model_id not in by_model:
                continue
            other = by_model[model_id]
            entry = {"record_type": "research_comparison_row", "slice": slice_id, "scope_kind": other["scope_kind"],
                     "scope_id": scope_id, "model_id": model_id, "baseline_model_id": baseline,
                     "scored_games": other["scored_games"], "common_support": "IDENTICAL_SCORED_GAME_KEYS_READER_VERIFIED"}
            if other["brier_mean"] is not None and base["brier_mean"] is not None:
                diff = _frac(other["brier_mean"]) - _frac(base["brier_mean"])
                entry.update(brier_mean_difference=rc.rational(diff), brier_mean_difference_decimal=rc.decimal_text(diff),
                             log_loss_mean_difference=repr(float(other["log_loss_mean"]) - float(base["log_loss_mean"])),
                             reading=f"descriptive retrospective difference (model minus {baseline}) on identical game "
                                     "keys; negative favours the model, positive the baseline; no significance, skill, "
                                     "calibration or champion claim; adverse and null results retained")
            else:
                entry.update(brier_mean_difference=None, brier_mean_difference_decimal=None,
                             log_loss_mean_difference=None, reading="no scored game in this scope")
            out.append(entry)
    return out


def _adverse_2023(summary_rows: list[dict[str, Any]], rc: Any) -> dict[str, Any]:
    """The exposed 2023 comparison as served (NATIONAL, SPLIT-DEV-SEL): every probability model's Brier and log-loss
    means and which models do not beat the fixed C47 smoothed comparator (exact Brier comparison; adverse results are
    retained, never hidden)."""
    rows = {r["model_id"]: r for r in summary_rows if r["slice"] == "NATIONAL" and r["scope_id"] == "SPLIT-DEV-SEL"}
    smoothed = rows.get(rc.MODEL_SMOOTHED)
    models = []
    not_beating = []
    for model_id in rc.PROBABILITY_MODELS:
        row = rows.get(model_id)
        if row is None or row.get("brier_mean") is None:
            continue
        models.append({"model_id": model_id, "scored_games": row["scored_games"],
                       "brier_mean": row["brier_mean"], "brier_mean_decimal": row["brier_mean_decimal"],
                       "log_loss_mean": row["log_loss_mean"]})
        if smoothed is not None and smoothed.get("brier_mean") is not None and model_id not in (
                rc.MODEL_NULL, rc.MODEL_SMOOTHED) and _frac(row["brier_mean"]) >= _frac(smoothed["brier_mean"]):
            not_beating.append(model_id)
    return {"slice": "NATIONAL", "scope_id": "SPLIT-DEV-SEL", "season": 2023, "models": models,
            "comparator": rc.MODEL_SMOOTHED, "new_probability_references_not_beating_comparator": not_beating,
            "rule": "exact Brier mean comparison on the identical scored 2023 games; descriptive only, already exposed"}


# --------------------------------------------------------------------------------------------- the registry

class ResearchRegistry:
    """The server-side registry of configured research profiles (the only addressable research objects)."""

    def __init__(self, configs: list[ProfileConfig], *, anchors: Mapping[str, Any] | None = None) -> None:
        if not configs:
            raise ResearchConfigError("RESEARCH_CONFIG_INVALID", "a registry needs at least one profile")
        self.profiles = {c.profile_id: ResearchProfile(c, anchors=anchors) for c in configs}

    @classmethod
    def from_source(cls, source: str | os.PathLike[str] | Mapping[str, Any]) -> "ResearchRegistry":
        """The registry of a JSON operator configuration bound to the packaged accepted pins."""
        return cls(load_config(source))

    def start(self) -> None:
        for profile in self.profiles.values():
            profile.start()

    def get(self, profile_id: str) -> ResearchProfile:
        if not isinstance(profile_id, str) or not PROFILE_ID_RE.match(profile_id) or profile_id not in self.profiles:
            raise ResearchError("RESEARCH_PROFILE_UNKNOWN", "no registered research profile has this ID", 404)
        return self.profiles[profile_id]

    def listing(self) -> dict[str, Any]:
        self.start()
        return {"api_version": API_VERSION, "schema": API_SCHEMA, "labels": dict(SURFACE_LABELS),
                "profiles": [p.summary() for p in self.profiles.values()]}
