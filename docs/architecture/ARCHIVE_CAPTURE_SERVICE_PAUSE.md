# Archive capture: service-aware pause and explicit resume (BAT-716)

Prospective capture policy for `tools/build_national_archived_publication.py` (Cycle #44 — Attempt #1,
TP44-A01 revision 2026-10-07.1). Configuration: `configs/national_archived_publication_capture_policy.json`.
It changes when the existing capture stage dispatches requests. It never adds request authority, a host, a
credential, a proxy, a scheduler, a background monitor or a retry loop, and it changes no contract, acquired byte,
materialization, consumer or default invocation.

## Selection and default

* Default (no `--capture-policy`): the frozen per-key retry behaviour of every contract. A key's transient failure
  (HTTP 429/5xx or a network error) is retried once within the run after `Retry-After` (capped by the contract);
  then the next key is attempted. Accepted Cycle #41/#43 contracts, journals, acquisitions and identities stay
  reproducible byte for byte.
* Service-aware mode: `--capture-policy <policy.json>` with `--stage capture` or `--stage all` (the materialize stage
  refuses the option with `ARGUMENT_INVALID`). `--acknowledge-unknown-intent <seq>` is valid only with it.

## One logical acquisition: the binding

The policy names each acquisition it may run as an exact binding: `contract_id`, `contract_sha256` (bytes of the
`--contract` file), `acquisition_policy_id` (the contract's existing acquisition policy id), `ordered_keys` (the exact
key order the capture loop visits), `total_requests` (the contract's ceiling) and `output_root`. Before any write
the CLI checks, in this order, and refuses with zero requests:

| Check | Refusal |
| --- | --- |
| policy schema, `authorizes_requests: false`, every rule equals an implemented rule, positive integer fallback, unique roots | `CAPTURE_POLICY_INVALID` |
| a binding names the normalized `--output-root` (a fresh or different directory is not new authority) | `CAPTURE_ROOT_NOT_BOUND` |
| binding contract id and bytes | `CAPTURE_CONTRACT_MISMATCH` |
| binding acquisition policy id | `CAPTURE_ACQUISITION_POLICY_MISMATCH` |
| binding keys contain a duplicate | `CAPTURE_KEYSET_DUPLICATE` |
| binding keys differ from the contract's ordered keys (missing, extra or reordered) | `CAPTURE_KEYSET_MISMATCH` |
| binding total differs from the contract ceiling | `CAPTURE_LIMIT_MISMATCH` |

A finalized acquisition document for the policy id returns `ALREADY_FINALIZED` with zero requests and zero writes,
whichever mode finalized it. The committed configuration binds only the BAT-715 expansion cohort acquisition (70
keys), which Cycle #43 finalized; it can spend nothing. A future retry needs a newly issued contract acquisition and
a manager-qualified binding.

## Owner, journal and request authority

* Owner: an exclusive operating-system lock on `acquisition/journal/<policy id>/OWNER.lock` is held for the whole
  invocation. A second caller refuses `CAPTURE_OWNER_ACTIVE` with zero requests; a crashed owner's lock is released
  by the operating system. `OWNER_START`/`OWNER_END` journal lines make an owner that stopped without release
  visible (`previous_owner_unreleased`, `stopped_owner` in the result).
* Journal `acquisition/journal/<policy id>/journal.jsonl`, schema `BAS-NATIONAL-ARCHIVED-PUBLICATION-JOURNAL-2`.
  The header binds the policy id, cohort or tranche sha256, contract id and sha256, the rules identity (sha256 of
  the canonical `rules` object), the binding identity (sha256 of the canonical normative binding fields), the
  ordered-keys sha256 and the total ceiling. Every later line carries `prev`, the sha256 of the previous line's exact
  bytes. A legacy (`JOURNAL-1`) journal for the same policy id refuses `CAPTURE_MODE_CONFLICT`; a different header
  refuses `CAPTURE_POLICY_CHANGED`; a broken chain refuses `CAPTURE_JOURNAL_PREFIX_CHANGED`; a torn last line refuses
  `JOURNAL_TORN`. The legacy mode likewise refuses a service journal (`REFUSED_STALE_JOURNAL`).
* Request authority anchor `acquisition/journal/<policy id>/AUTHORITY.json`: the number of INTENT lines and the
  sha256 of the last INTENT line, replaced atomically after every INTENT and before dispatch. It must equal the
  journal's INTENT count (or trail it by one after a crash before the update) with the matching line hash. A missing
  anchor beside recorded intents, an anchor ahead of the journal (a truncated journal), an anchor behind by more
  than one, a journal missing beside an anchor, or raw bodies that no acquisition, journal or control explains in a
  root whose journal is new, refuse `CAPTURE_COUNTER_RESET`. A mismatched line hash refuses
  `CAPTURE_JOURNAL_PREFIX_CHANGED`. Every recorded body is re-verified (`RAW_MISSING`, `RAW_ALTERED`).

Every attempted request counts against the per-key and total limits: failures, HTTP 429, redirect hops and any
INTENT whose result is unknown. The contract's per-key plan and limits are unchanged.

## One request

1. `INTENT` line (fsync), then the anchor update, then the single dispatch through the existing transport.
2. The response body goes create-only into the raw store; the `RESULT` line keeps the request record shape of the
   default mode (its `retry_after_seconds` is computed against the response receipt clock).
3. If the status is a service-pause status (HTTP 429, at metadata, replay or a redirect hop), a `PAUSE` line is
   written before anything else and the invocation stops: no further dispatch, no retry, no next key. The paused
   key stays pending; nothing is turned into "no capture", completion or coverage.

Crash boundaries: after an INTENT without a RESULT the next invocation returns `RECONCILIATION_REQUIRED` (exit 5)
with zero requests, naming the sequence, key, URL, start time and whether the anchor had advanced (per the write
order the request was not dispatched when it had not). Only `--acknowledge-unknown-intent <seq>` records an
`ACKNOWLEDGED` line; the request stays counted as `INTERRUPTED_UNKNOWN` and the per-key plan decides any retry.
After a 429 RESULT without its PAUSE line the next invocation derives the same pause from the recorded RESULT
and writes it (`recovered: true`) before any decision.

## Retry-After and eligibility

The response receipt clock is the request's recorded `ended_utc`. All `Retry-After` header values are kept raw and
trimmed of spaces and tabs. Rules, in order:

| Case | Rule | Eligible instant |
| --- | --- | --- |
| no value | `FALLBACK_MISSING` | receipt + fallback (900 s) |
| more than one distinct value | `FALLBACK_CONFLICTING` | receipt + fallback |
| digits only | `DELTA_SECONDS` | receipt + that many seconds, never capped (beyond year 9999: `9999-12-31T23:59:59.999999Z`) |
| `-` then digits | `FALLBACK_NEGATIVE` | receipt + fallback |
| IMF-fixdate, RFC 850 (two-digit year per RFC 9110) or asctime date in GMT, not earlier than the receipt | `HTTP_DATE` | that instant |
| such a date earlier than the receipt | `FALLBACK_PAST_DATE` | receipt + fallback |
| anything else | `FALLBACK_MALFORMED` | receipt + fallback |

The weekday name of a date is not used. The effective eligible instant is the latest over every recorded pause.
An invocation proceeds only when its UTC clock is at or after that instant and not earlier than the latest instant
already recorded in the journal; otherwise it returns `DEFERRED` (exit 4, reason `SERVICE_PAUSE_NOT_ELIGIBLE` or
`CLOCK_BEHIND_JOURNAL`) with zero requests and nothing written. A clock moved backwards can only lengthen a pause.
There is no cooldown sleep, poller or self-dispatch: resuming is a new explicit invocation, under the same ceiling,
journal and source grant. On resume a `RESUME` line is written; the contract's per-key plan retries the paused
request (the pause has honoured `Retry-After`, so the in-run cap does not apply to it) and a second 429 pauses again.
The minimum spacing between request starts also applies across invocations.

## Results and exit codes

| State | Exit | Meaning |
| --- | --- | --- |
| `FINALIZED`, `ALREADY_FINALIZED` | 0 | every key done; a repeated invocation sends zero requests |
| `PAUSED_SERVICE_429` | 4 | this invocation stopped at a 429; resume after `eligible_utc` |
| `DEFERRED` | 4 | not eligible yet (or clock behind the journal); zero requests |
| `RECONCILIATION_REQUIRED` | 5 | an INTENT without a RESULT needs explicit acknowledgement |
| refused | 2 | a binding, identity, counter, owner or argument refusal |

Every non-refused result reports `requests_used`, `requests_limit`, `requests_remaining`, `new_requests`, the
effective `eligible_utc`, every recorded pause and an exact key partition: `completed` (key -> outcome; outcomes are
the default mode's, for example `CAPTURED`, `NO_ARCHIVE_CAPTURE_REPORTED`, `METADATA_REQUEST_FAILED` after a 404),
`attempted_failed_pending` (attempted, not done, last request failed) and `pending_unattempted`. Finalization writes
the same acquisition document as the default mode, so materialization, validators and installed consumers are
unchanged.

## Limits

The lock, chain and anchor protect one acquisition root against restarts, concurrent callers, mode switches and
naive resets; they are not tamper-proof against a writer who rewrites the journal, anchor and raw store together
or deletes the whole acquisition. Offline tests use fixture policies and fake transports in owned roots; they are
not acquisition evidence. Live archive recovery is not claimed.
