# Private national retrospective research API and browser (BAT-728)

Cycle #57 (TP57-A01). A private, explicitly configured, read-only research surface in the existing BAS FastAPI app over
the accepted, unchanged Cycle 56 national retrospective reference (database
`ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8`, content
`fe303a90d8753956b914d3c7c2adfe2d33d9816bfb45689b0361f8e36e2e6cc0`): 5,875 accepted 2016–2023 targets, both
orientations and the five declared models (`NULL_HALF_V1`, `SMOOTHED_HISTORY_ODDS_V1`, `SITE_BLIND_ELO_REFERENCE_V1`,
`PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1`, and the margin-only `PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1`).

Every response and view is **RETROSPECTIVE_RESEARCH / UNTRUSTED_SHADOW / PIT_NOT_ADMITTED / predictive skill
NOT_ESTABLISHED**. It is not a forecast, a calibrated champion or a default product view. 2023 is an already-exposed
out-of-fit comparison (never blind); adverse results are served unchanged. The ridge reference serves an expected
margin only; no probability, interval or confidence band is derived from it. 2024/2025 protected labels and future
shadow values are not reachable through a profile. It completes neither BAT-423, BAT-466, BAT-468 nor F1.

## Activation (operator only)

```python
from aggie_analytics.api import create_app
app = create_app(snapshot_root=..., research_config="<operator profile file>")   # or a ResearchRegistry
```

Without `research_config` the application is unchanged: no research route, page or module exists (`/research` and
`/api/v1/research/...` answer 404; the static `research.html` shows "unconfigured"). There is no default profile and no
automatic data discovery.

The operator file (`BAS-RESEARCH-PROFILE-CONFIG-1`, strict JSON: strings only, no duplicate keys):

```json
{"schema": "BAS-RESEARCH-PROFILE-CONFIG-1",
 "profiles": [{"profile_id": "national-retrospective-reference-2016-2023",
               "display_label": "National retrospective reference 2016-2023",
               "reference_database": "<abs>/national_retrospective_reference_2016_2023/sha256/<database identity>/national_retrospective_reference.sqlite",
               "reference_manifest": "<abs>/sha256/<database identity>/run_manifest.json",
               "history_database": "<abs>/sha256/<history identity>/national_history.sqlite",
               "population_database": "<abs>/sha256/<population identity>/national_population.sqlite",
               "expected": {"database_identity": "...", "content_identity": "...", "database_sha256": "...",
                            "contract_sha256": "...", "history_identity": "...", "population_identity": "..."}}]}
```

* `profile_id`: 3–64 lowercase letters, digits or hyphens; `reference_manifest` and `display_label` are optional
  (the manifest defaults to the canonical `manifests/<population>/sha256/<identity>/run_manifest.json` layout).
* Every identity is 64 lowercase hex characters and must equal the packaged accepted pins
  (`reference.REFERENCE_PROFILE` and the reader's anchors); a self-consistent configuration naming other identities is
  refused (`RESEARCH_PROFILE_PIN_UNACCEPTED`) and the application is not created.
* Every location is validated lexically before any access: absolute local paths only. Windows: `X:\...` or the native
  extended form `\\?\X:\...`; UNC shares, every `\\.\` device spelling, other `\\?\` namespaces, reserved device
  names, streams, `.`/`..` traversal, empty components and components ending in a dot or space are refused. POSIX:
  absolute paths; `.`/`..` traversal and `/dev`, `/proc`, `/sys` are refused; backslashes, colons, `?`, `#`, spaces
  and non-ASCII are ordinary filename characters. The file names and identity directories must match the declared
  identities. Long Windows locations are opened through the extended form (the same file).
* Each profile is then verified once by the accepted reader (`ReferenceComparison`: inputs verified and pinned,
  every record, the refit and both identities re-derived; about 12–15 s for the accepted reference). Until it
  completes the profile answers `RESEARCH_PROFILE_VERIFYING` (503, `Retry-After: 2`). A refused profile is
  `UNAVAILABLE` with the reader's own code and serves nothing. If a profile file changes after verification the
  profile closes (`RESEARCH_PROFILE_STALE`) until the server restarts; another database is never substituted.

## Routes (all GET, read-only)

| Route | Answer |
| --- | --- |
| `/research` | The packaged private browser (Content-Security-Policy `default-src 'self'`). |
| `/api/v1/research/profiles` | Registered profiles: ID, label, state, refusal code, expected/verified identities, labels. |
| `/api/v1/research/profiles/{id}` | Identities (database, content, database SHA-256, manifest SHA-256, contract, history, population), coverage, seasons, partitions, slices, models (probability or margin), grains and their selectors, limitations, the exposed 2023 comparison. |
| `/api/v1/research/profiles/{id}/games` | Canonical game catalog (one row per accepted target). |
| `/api/v1/research/profiles/{id}/games/{game}` | One target: catalog row, label, both oriented feature records with both-team lineage, 10 estimates, 5 game-level scores. |
| `/api/v1/research/profiles/{id}/features` | Both oriented feature records per target, each with `excluded_prior_inputs` (team and opponent) from the accepted history views. |
| `/api/v1/research/profiles/{id}/estimates` | Model estimates (two per target and model). |
| `/api/v1/research/profiles/{id}/scores` | One A-oriented game-level score per target and model. |
| `/api/v1/research/profiles/{id}/parameters` | The five parameter records. |
| `/api/v1/research/profiles/{id}/summary` | Summary rows (`reference_summary_row`). |
| `/api/v1/research/profiles/{id}/comparisons` | Model-minus-baseline comparisons on the reader-verified common support. |

Selectors per grain (anything else answers `FILTER_NOT_APPLICABLE`): games and features `season, team, game,
partition`; estimates and scores add `model`; parameters `model` only; summary `season, team, game, model, partition,
slice`; comparisons add `baseline` (`NULL_HALF_V1` by default, which serves the reader's own comparison rows; another
probability model serves `research_comparison_row` differences built exactly as the reader builds its comparisons).
Paging: `limit` 1–500 (default 50), `offset` 0–999,999,999. Unknown or repeated parameters refuse; there is no file,
path, SQL or expression parameter. `team` matches either participant by `org:<digits>`, digits or a name that team
carries in that season; `game` is a parent contest key (bare digits read as `ncaa:<digits>`). At the summary and
comparison grains `team`/`game` select canonical games and the rows are re-derived over exactly those games (the
accepted reader's rule). Valid unknown or disjoint selectors answer zero rows; an empty summary has no row; a season
outside 2016–2023 answers zero rows with `season_scope_state` (`PROTECTED_SEASON_NOT_IN_REFERENCE`,
`FORWARD_SEASON_NOT_IN_REFERENCE` or `OUTSIDE_REFERENCE_SCOPE`).

List envelope: `api_version, schema (BAS-RESEARCH-API-1), profile_id, grain, labels, reference_identity,
content_identity, filters, season_scope_state, [summary_selection], offset, limit, total, returned, next_offset, rows`.
`next_offset` is `offset + returned` while rows remain, otherwise `null`.

Errors: `{"api_version", "schema", "labels", "error": {"code", "message", "status"}}` with a fixed message — never a
path, traceback, credential or raw page. Codes include `UNKNOWN_PARAMETER`, `PARAMETER_REPEATED`,
`FILTER_NOT_APPLICABLE`, `SEASON_INVALID`, `TEAM_INVALID`, `GAME_INVALID`, `LIMIT_INVALID`, `OFFSET_INVALID`,
`MODEL_UNKNOWN`, `PARTITION_UNKNOWN`, `SLICE_UNKNOWN`, `BASELINE_INVALID`, `BASELINE_NOT_PROBABILITY`,
`CONTEST_KEY_INVALID` (400); `RESEARCH_PROFILE_UNKNOWN`, `GAME_NOT_IN_PROFILE` (404); `RESEARCH_PROFILE_VERIFYING`,
`RESEARCH_PROFILE_STALE`, `RESEARCH_PROFILE_FILE_MISSING`, `RESEARCH_PROFILE_IDENTITY_MISMATCH`,
`RESEARCH_PROFILE_VERIFICATION_FAILED` and the reader's own `REFERENCE_*` refusal codes (503); `RESEARCH_INTERNAL_ERROR`
(500).

## Browser

`/research` (packaged `product/static/research.html`, `research.js`, `research.css`) loads the profiles, shows the
identity, labels and limitations, and offers season, team, game, model, partition, slice and baseline selectors with
paging over every grain, a game detail with both-team contributing and excluded prior games, estimates and scores, and
the exposed 2023 comparison. Loading, verifying, empty, unavailable, unconfigured and error/retry states are explicit.
Every value is a server record inserted as text; no estimate or aggregate is computed in the browser.

## Validation

`tests/test_research_profile_boundary.py` (core runtime) and `tests/research_product_cases.py` (wired into the hosted
product profile `tests.test_w22_product_serving`; real tiny worlds built and verified by the accepted builders and
reader; the genuine accepted reference when the private lake is mounted). Installed-wheel HTTP and headless-browser
qualification are recorded in the Cycle 57 worker evidence.
