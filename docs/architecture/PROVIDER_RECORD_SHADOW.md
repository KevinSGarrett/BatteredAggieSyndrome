# Provider-record UNTRUSTED_SHADOW snapshot (BAT-725)

Cycle #53 — Attempt #1. Governing plan: TP53-A01 revision 2026-10-12.1 sections 1–6. Contract:
`configs/provider_record_shadow_20261017_contract.json` (`BAT-725-PROVIDER-RECORD-SHADOW-20261017-V1`).
Reader: `aggie_analytics.retrospective_baseline.shadow`. Builder: `tools/build_provider_record_shadow.py`.

## What it is and is not

One private, create-only, content-addressed snapshot freezes the accepted fixed provider-record calculations of the
accepted BAT-724 preview for the exact 25-event provider cohort (provider-reported 2026-10-17 starts, 50 participant
records, 100 oriented predictions = 25 events x 2 fixed models x 2 sides). It is served only through the existing
`bas-retrospective-baseline-query` console and `python -m aggie_analytics.retrospective_baseline.query`, explicitly
selected with `--prospective-shadow <snapshot.json>`, at the grains `shadow-prediction` and `shadow-summary`.

It is an actual recorded pre-event shadow prediction with trust explicitly limited. Every payload record and every
served row carries `UNTRUSTED_SHADOW`, `PROVIDER_CLAIM_INPUTS`, `PIT_NOT_ADMITTED`, `NOT_CALIBRATED`,
`PREDICTIVE_SKILL_NOT_ESTABLISHED` and national coverage `UNKNOWN`. It is not a trusted operational forecast, calibrated
prediction, betting recommendation, historical PIT recovery, protected experiment or skill result. Nothing is fitted,
selected, tuned or recalibrated; no outcome is acquired or scored and no prediction value is published. Historical
milestone F1 stays unmet.

The preview keeps its role: each frozen record names the SHA-256 of the exact preview record it freezes and carries
`source_preview_label = PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST` beside `designation = UNTRUSTED_SHADOW`; the payload
names the preview identity, file hash and contract as `SOURCE_PROVENANCE_PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST`.

## Two immutable stages and the timestamp anchor

1. **Payload** (`canonical/provider_record_shadow_20261017/payload/sha256/<payload sha256>/payload.json`): every event,
   participant record and prediction of the verified preview (which the accepted reader re-derives from the bundled
   accepted capsule and its retained raw response), with participant, role, input and model identities, exact reduced
   fractions and 12-place decimals, explicit abstentions (never a zero record), labels, a per-model summary and counts.
   No clock, anchor or timing value enters it. Supported complements and paired orientations sum to exactly 1 and every
   smoothed strength equals `strength_q` of that side's own frozen W/L/T.
2. **Anchor**: the granted material comment `C53-A01-M2` on BAT-725, whose body is rendered deterministically from the
   payload (`shadow.anchor_body`): the payload SHA-256 and size, contract, source, model and cohort identities and counts,
   the trust labels and the timing basis — hashes and metadata only. It is posted once by the platform operation
   (duplicate check first, never reposted) and read back by its id; the exact raw readback is the anchor receipt. The
   receipt must be unedited (`created == updated`): an edited body cannot use its old creation time.
3. **Snapshot** (`canonical/provider_record_shadow_20261017/sha256/<snapshot identity>/`): `snapshot.json`, the exact
   payload bytes, `anchor/jira_comment.json` (the raw receipt), the contract and a byte copy of the preview directory
   (itself holding the capsule directory). The identity is the SHA-256 of the identity document (snapshot file hash plus
   every bundle member hash), so it covers the full payload, the exact receipt, the bindings and the labels.

The anchor proves only that the payload bytes existed no later than the comment's service-created time. Per event the
basis is `PRE_PROVIDER_REPORTED_START` (decision `ANCHORED_PRE_PROVIDER_REPORTED_START`) exactly when observation end <=
anchor created < provider-reported start and the event was pre-game at observation; otherwise the key is retained as
`INELIGIBLE_NOT_PRE_PROVIDER_REPORTED_START` with every reason. It is never called an official kickoff.

Rebuilding with the same payload and receipt is byte-identical (`ALREADY_PRESENT_IDENTICAL`); processing order and read
chunk size never change a byte; an interrupted build leaves only a staging directory; a second different payload or
snapshot in the same root is refused unless a deliberate corrected successor names its frozen predecessor. Only run
manifests record the build clock.

## Verification before any row

The reader verifies the committed contract, the bundled preview through the accepted preview reader (pinned identity and
contract), the exact bundle membership, the re-derived payload (canonical-byte comparison; integer, float, boolean and
string identities differ; the first differing family names `SHADOW_PAYLOAD_<FAMILY>_MISMATCH`), the anchor receipt
(issue, decimal-string comment id, service time grammar, unedited, marker, body equal to the rendered body of this
payload), the re-derived snapshot document (`SHADOW_SNAPSHOT_<FAMILY>_MISMATCH`), the identity, and finally the actual
anchor and snapshot pinned by the packaged final gate (`shadow.ANCHOR_PROFILE`, equal to
`artifacts/data_lake/provider_record_shadow_20261017_gate.json`). A self-consistent forged receipt or rehashed snapshot
therefore never becomes profile authority (`SHADOW_ANCHOR_NOT_PINNED_PROFILE`, `SHADOW_NOT_PINNED_SNAPSHOT`); without a
packaged profile the consumer refuses (`SHADOW_PROFILE_NOT_PINNED`). Fixture receipts and profiles are test-only.

## Query

- `--cutoff` is required: before the anchor's service-created time `SHADOW_UNAVAILABLE_BEFORE_ANCHOR`; at or after it the
  same immutable snapshot is served (also after a provider-reported start; nothing is refreshed, recomputed or written and
  the current clock is never read). Equivalent offsets agree; naive, date-only, malformed and out-of-UTC-range values
  refuse cleanly (`CUTOFF_OUT_OF_RANGE` in this mode only; the shared historical and preview parsers are unchanged).
- Filters are conjunctive: `--season` (2026; other seasons `NOT_YET_AUDITED`), `--event espn:event:<id>`,
  `--team espn:team:<id>`, `--model`, `--orientation home|away` (predictions only). Unknown or disjoint valid selections
  serve `rows=[]`, `total=0`, `returned=0`, `next_offset=null` at both grains. Paging is exact.
- `shadow-summary` counts each game once (two orientations are not two games) with the selected participants,
  predictions, supported/abstained games and the anchored/ineligible games of the timing decisions.
- `--require-pit` is always refused; the mode is never combined with `--database`, `--history-database`, `--manifest` or
  `--prospective-preview` (`SHADOW_MODE_CONFLICT`). Locations follow the accepted literal-location rules (local relative,
  long and extended-length paths and junctions; network and device paths refused before access; a missing file is never
  created).
- Without `--prospective-shadow` every existing invocation, answer and refusal is unchanged; only `--help` of the original
  parser gains one paragraph naming this mode.
