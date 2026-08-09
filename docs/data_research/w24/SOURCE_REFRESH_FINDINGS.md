# Wave 24 Source-Landscape Refresh

## Scope

This is the targeted second-pass refresh required by Wave 24. It compares current source status with the frozen Wave 06 baseline; it does **not** claim exhaustive coverage of every football dataset on the internet.

## Material findings

1. **CollegeFootballData remains a viable primary aggregator.** Current 2026 API/export/download workflows remain active. No evidence found in this pass requires replacing the CFBD lane. Endpoint/schema/version evidence must still be snapshotted rather than assumed timeless.
2. **SportsDataverse provenance is now more explicit.** `cfbfastR-cfb-data` describes itself as analysis-ready rectangularization of enriched `final` JSON produced by sibling `cfbfastR-cfb-raw`. The raw sibling is therefore added as `SRC-061` for upstream provenance/replay diagnostics. The two siblings must never be treated as independent corroborating sources.
3. **Open-Meteo remains useful but access policy is more precise than the earlier shorthand.** The free API is non-commercial; commercial use requires a customer plan, and historical/ensemble customer APIs require Professional or higher. Acquisition configuration must preserve which access lane was used.
4. **Open-Meteo Ensemble Mean is a useful new uncertainty candidate, not a mandatory historical feature.** It exposes ensemble mean/spread and has extended storage mostly from March 2026. That depth is insufficient for the broad historical foundation but may improve forward/current weather uncertainty experiments.
5. **Official availability reporting remains active** for the SEC, ACC, Big 12 and CFP lanes checked. The architecture should continue storing report versions/effective timestamps rather than overwriting state.
6. **NCAA 2026 rule updates validate the effective-dated regulatory environment design.** Targeting carryover semantics changed for 2026, which can affect player availability. This requires data population/versioning, not architectural replacement.

## No-source-disappearance result

This targeted pass found **no material disappearance of a currently preferred core source class** among the checked CFBD, SportsDataverse, Open-Meteo, SEC/ACC/Big12/CFP availability, and NCAA rules surfaces. That statement is deliberately limited to the source classes reviewed here.

## Remaining high-value gaps

Wave 06 gaps remain materially unresolved for nationwide historical injury/depth-chart reconstruction, complete officiating assignments, proprietary route/coverage/tracking/charting, and symmetric private-school football-resource data. W24 found no defensible new universal free source that eliminates those gaps.

## Adoption policy

Discovery still follows:

`SOURCE → CONTRACT → PIT SAFETY → CANONICALIZATION → FEATURE CANDIDATE → EXPERIMENT → WALK-FORWARD/ABLATION → PROMOTE OR REJECT`

Neither `SRC-061` nor `SRC-062` is automatically a production feature source merely because it is now documented.
