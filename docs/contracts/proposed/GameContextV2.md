# GameContextV2 — proposed BAS context packet

**Status:** PROPOSED. Adoption pending C01 / CFIP-20. Not consumed at runtime.
**Compatibility:** GameContextV1 remains `additionalProperties: false` with `home`, `away`, `season` only. Unknown and neutral fields must not be dropped to squeeze through V1.

## Grain

Canonical contest × schedule/venue version × cutoff.

## Required fields

| Field | Type | Units / notes |
|---|---|---|
| `canonical_game_id` | string | Stable contest identity |
| `source_order` | [string, string] | Source-published participant order |
| `canonical_home_id` | string | After permutation |
| `canonical_away_id` | string | After permutation |
| `designated_home_id` | string or `UNKNOWN` | Official designation, not display order |
| `designated_source` | string or null | Source that asserted designation |
| `site_class` | `NEUTRAL` \| `NON_NEUTRAL` \| `UNKNOWN` \| `CONFLICT` | Missing annotation is `UNKNOWN` |
| `venue_id` | string or null | Physical venue |
| `venue_name` | string or null | Display only |
| `venue_latitude` | number or null | WGS84 degrees |
| `venue_longitude` | number or null | WGS84 degrees |
| `ordinary_home_exposure_designated_home` | 0 \| 1 \| null | Null when site unknown/conflict |
| `ordinary_home_exposure_designated_away` | 0 \| 1 \| null | Always 0 when site is verified |
| `travel_home_km` | number or null | Origin → venue; null if coordinates missing |
| `travel_away_km` | number or null | Same |
| `travel_method` | `haversine+vincenty` or null | Independent methods; disagreement >25 km fails |
| `weather` | object or `UNKNOWN` | Distinct from travel; issued-forecast vintage |
| `kickoff_utc` | string or null | Aware UTC; midnight is not date-only |
| `date_precision` | `INSTANT` \| `DATE_ONLY` \| `UNKNOWN` | Declared, never inferred from 00:00Z |
| `unknowns` | string[] | Explicit missingness |
| `consumed_columns` | string[] | Proof of what a model actually used |
| `rights` | string | Source rights class |
| `known_at_utc` | string or null | Per-row |

## Migration

- V1 packets remain readable. V2 fields are additive.
- Consumers that require V2 must reject V1 rather than default site class to non-neutral.
- Frozen forecast rows are not rewritten when later venue/site knowledge arrives.

## Fixtures

- Positive: verified ordinary home; verified Lambeau-class neutral with travel; international/relocation; shared venue.
- Negative: missing annotation treated as home; proximity treated as HFA; silent drop of unknown; V1 additionalProperties squeeze.

## Built-package compatibility

C01 consumption stays blocked until release/BOM/license/provenance/temporal/compatibility pass. Synthetic compatibility fixtures are labeled `SYNTHETIC_FIXTURE`. Runtime must not default to `C:\All-22`.
