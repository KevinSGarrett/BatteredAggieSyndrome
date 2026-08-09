# Runbook — Source/API Outage, Contract Drift, or Access Failure

## Trigger

Source unavailable, credential rejected, rate-limited, schema changed, terms/rights uncertain, or payload contract fails.

## Diagnose

- source/provider and endpoint/version;
- authentication class (not secret value);
- HTTP/error/status evidence;
- rate-limit/quota state;
- terms/license/redistribution status;
- expected versus actual schema/grain/semantics;
- last known good immutable snapshot;
- affected tasks/pipelines/publications.

## Response

- respect provider backoff/rate limits;
- do not bypass controls/CAPTCHA/paywall;
- preserve last valid snapshot and freshness state;
- fail closed on uncertain semantics/rights;
- quarantine unexpected payloads;
- update source-drift evidence;
- use an approved fallback only if its semantics/rights are accepted;
- switch to independent Ready work when outage is external.

Do not fabricate data or silently substitute a source.

## Exit criteria

Access/contract/rights restored and validated, or exact external blocker/fallback decision is recorded.
