# Final Data-Source Audit — W25

Checked: 2026-08-09 UTC. This is a focused final verification of high-value W24 source conclusions, not a claim of exhaustive internet coverage.

## Confirmed current surfaces

### CollegeFootballData
- Homepage/workflows remain active for 2026: https://collegefootballdata.com/
- REST documentation is live at https://api.collegefootballdata.com/ and currently exposes the active v2-era catalog.
- Final decision: **KEEP PRIMARY AGGREGATOR WITH VERSIONED CONTRACTS**. Never assume endpoint/version stability indefinitely.

### SportsDataverse
- `cfbfastR-cfb-data`: https://github.com/sportsdataverse/cfbfastR-cfb-data
- `cfbfastR-cfb-raw`: https://github.com/sportsdataverse/cfbfastR-cfb-raw
- The analysis-ready repository still documents its derivation from enriched `final` JSON in the raw sibling.
- Final decision: **KEEP DERIVED + UPSTREAM PROVENANCE RELATIONSHIP**; do not count the sibling repositories as independent corroboration.

### Open-Meteo
- Pricing/access: https://open-meteo.com/en/pricing
- Historical weather: https://open-meteo.com/en/docs/historical-weather-api
- Ensemble mean/spread: https://open-meteo.com/en/docs/ensemble-mean-api
- Final decision: **KEEP WITH EXPLICIT ACCESS/RUN PROVENANCE**. Free use remains non-commercial; customer historical/ensemble access requires an eligible higher plan. Ensemble mean/spread history is mostly recent and stays optional research rather than a mandatory long-history feature.

### Official availability reporting
- SEC: https://www.secsports.com/fbreports
- ACC: https://theacc.com/sports/2025/8/28/availability-reporting-football.aspx
- Big 12: https://big12sports.com/sports/2025/8/14/FBreporting.aspx
- Final decision: **KEEP EFFECTIVE-DATED OFFICIAL REPORT SNAPSHOTS**. Report versions must not be overwritten.

### NCAA rule environment
- 2026 FBS targeting trial approval: https://www.ncaa.org/media-center-changes-to-penalty-structure-for-targeting-in-di-football-approved/
- Final decision: **KEEP EFFECTIVE-DATED REGULATORY ENVIRONMENT**. 2026 rule changes validate explicit rule/version state rather than season-only inference.

## Final gap conclusion
No checked source invalidates the W24 source architecture. Material gaps remain in nationwide historical injury/depth evidence, complete officiating history, proprietary charting/tracking, symmetric private-school resource data, and source-specific redistribution rights. These remain known limitations rather than fields to fabricate.
