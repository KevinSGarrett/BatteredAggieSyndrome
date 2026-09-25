# Cycle #30 CFIP / C01 reviewable patch (adoption pending)

**Authority:** This file is a complete reviewable RFC for CFIP-18/19/20/22/24/27.
It does **not** modify `C:\CFB\repos\CFBProgramSpecifications` or
`C:\CFB\repos\CFBIntelligenceContracts`. Adoption remains pending those owners.
C01/Film consumption stays blocked until release/BOM/license/provenance/temporal/compatibility pass.

Observed C01 disagreement, not patched in place:

- Manifest objects / fixtures: 36 / 7
- Catalog objects / fixtures: 105 / 8

## BAS_INTEGRATION documents to update when authorized

- `50_BAS_INTEGRATION/01_CONTEXT_PUBLISHING.md` — GameContextV2 fields (designation, site_class, venue, per-team travel, weather, time, unknowns, consumed_columns).
- Staff / matchup / PIT / end-to-end / acceptance plans — StaffSnapshotV2 and CoachStateV2; PIT estimand is bounded 2013–2023 FBS–FBS binary win with in-window priors; ties excluded from the binary estimand; ordinary home exposure masked on verified neutrals.
- Negative fixtures: empty science PASS; neighborhood `Final`; equal-length coach arrays; `DISPLAY:` IDs; literal `attempted:true`; GameContextV1 squeeze of unknown/neutral.

## Built-package tests (proposed)

1. Full-packet round trip of GameContextV2 and StaffSnapshotV2.
2. Missing release/BOM rejection (must fail closed).
3. V1 consumer rejects V2-required packets rather than dropping fields.
4. Synthetic All-22 compatibility is labeled synthetic; runtime does not default to `C:\All-22`.

## BAS technical-plan updates already applied on this isolated branch

- `docs/30_ENVIRONMENT_RESOURCE_CONTEXT_ARCHITECTURE.md`
- `docs/33_OPPONENT_STYLE_SCHEDULE_OFFICIATING.md`
- `docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md`
- `docs/36_AVAILABILITY_EVIDENCE_AND_OFFICIAL_REPORTS.md`
- `docs/contracts/proposed/GameContextV2.md`
- `docs/contracts/proposed/StaffSnapshotV2.md`
- `docs/contracts/proposed/CoachStateV2.md`
