# Environment, Resources and Game Context — W13

## Weather
Pregame weather uses an issued forecast/model run that could have been known at the forecast cutoff. Observed or reanalysis weather is retrospective/evaluation evidence and cannot replace a historical forecast.

## Venue and travel
Candidate context includes venue identity, surface/elevation/roof when valid, travel distance, opponent differential, recent travel, road streak, rest, IANA timezone change and body-clock context. Timezone calculations must be date/DST aware.

Scheduled kickoff and actual kickoff remain separate. Actual kickoff is generally retrospective unless it was knowable at the relevant forecast cutoff.

## Resources
Four lanes are preserved:
- R0: no-resource control;
- R1: universal source-compatible resources;
- R2: public-school enriched resource evidence;
- R3: latent-capacity research.

Missing private-school detail is not zero. A latent capacity proxy is not a dollar-spending estimate. EADA and MFRS/Knight concepts require semantic crosswalks rather than silent field merging.

## Home field
Home-field strength is a learned residual relative to neutral-equivalent expectation with shrinkage, not raw home winning percentage. Kyle Field receives no manual 12th-Man bonus.

## Game stakes
Rivalry, senior day, homecoming, postseason/eligibility and look-ahead context must be factual, point-in-time evidence. W13 creates no narrative motivation bonus.

## Cycle #30 site, designation, venue and travel (normative addition)

These facts are separate and must not be collapsed:

1. **Source order** — the participant order as published by a source.
2. **Canonical orientation** — home/away identities used for joins after permutation.
3. **Official designation** — which side is the designated home, with source identity.
4. **Site class** — `NEUTRAL`, `NON_NEUTRAL`, `UNKNOWN`, or `CONFLICT`. Missing annotation is `UNKNOWN`, never ordinary home.
5. **Physical venue** — venue identity and coordinates when present. Missing coordinates are explicit gaps, not defaults.
6. **Per-team travel** — origin → actual venue, kilometres, independent haversine and Vincenty methods. A participant being physically closer is not a learned home bonus.
7. **Ordinary home exposure** — `1` only for designated home on verified non-neutral sites; `0` for verified neutrals in every fitted path; `null` when site class is unknown/conflict.

Feature definitions are versioned (`cycle30-ordinary-home-exposure-v1`). Frozen predecessor rows are not rewritten. Travel may be available in context without being consumed by a model. Weather and timezone remain distinct domains (DOM-023 / DOM-026) and are not implied by travel. Adoption of GameContextV2 by C01 remains pending the contract owner.
