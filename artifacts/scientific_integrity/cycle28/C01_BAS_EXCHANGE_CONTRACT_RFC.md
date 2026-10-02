# C01 BAS exchange-contract RFC (Cycle #28)

Status: `RFC_DRAFTED_NOT_ACCEPTED`

Owning control plane: CFIP / C01 (`CFIP-19`). BAS consumer: `BAT-704`.

This RFC is not accepted. Cycle #28 must not consume it as a released contract identity.

## Predecessor disposition

Current C01 snapshots `StaffSnapshotV1`, `CoachStateSnapshotV1`, and `PlayerStateSnapshotV1` are incomplete for BAS. Free-form role strings, a list of coach IDs, and film-inferred availability cannot satisfy the BAS staff or official-availability interface.

Observed Contracts HEAD at Cycle #28 closeout inspection is dirty and does not equal the Foundation-bound C01 head. Snapshot classification: `DRIFTED_NOT_CONSUMABLE`.

## Required contracts

### BASContextExportV1

- Game-grain official context export owned by BAS.
- Canonical contest and ordered participants.
- PIT known-at / cutoff identities.
- Rights, provenance, and quarantine flags.
- No All-22 local path.

### FilmFeaturePackageV1

- Versioned film-derived package from F01–F11.
- Explicit event time, known-at, ruleset, release BOM identity.
- Uncertainty / OOD / missingness enumerations.
- Never auto-admitted into a BAS model.

### BASFilmImportReceiptV1

- Atomic import receipt for a supplied package or fixture root.
- Request identity, package hash, adapter version, rights class.

### BASFilmAdmissionDecisionV1

- `QUARANTINE_CANDIDATE` default.
- Admission requires synthetic conformance, quarantined real-payload replay, chronological evaluation, and explicit BAS admission.
- Rejection classes: incompatible version, unknown schema, future-known data, identity conflict, rights restriction, missing field, invalid uncertainty, OOD, uncommissioned/drifted snapshot.

### StaffRoleEpisodeV1

Separate role types:

- head coach
- offensive coordinator
- defensive coordinator
- special teams coordinator
- co-coordinator
- interim/acting
- offense play caller
- defense play caller
- official title versus inferred functional responsibility

Do not infer play caller from coordinator title. Name-only identity is candidate-only.

### Official availability evidence

Distinct from roster membership and film-inferred participation. Conference-game policies do not establish nonconference coverage. Absence is never healthy.

## Release, compatibility, migration, deprecation

- Immutable `GRIDIRON_CORTEX_RELEASE_BOM`.
- Compatibility matrix keyed by released C01 and BAS adapter versions.
- Breaking changes in grain, identity, time, units, missingness, uncertainty, rights, or enums invalidate affected BAS claims even if an upstream label understates them.
- Dirty worktrees, local branches, and unreleased packages are not runtime authority.

## Allowed Cycle #28 claim

`GRIDIRON_CORTEX_CONSUMER_BOUNDARY_SCAFFOLDED_WITH_SYNTHETIC_FIXTURES`

Forbidden: `GRIDIRON_CORTEX_INTEGRATED`, `FILM_FEATURES_ADMITTED`, `LANE_RUNTIME_OPERATIONAL`.
