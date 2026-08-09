# Wave 06 Data Research Findings

Research date: 2026-08-08

## Material new or materially upgraded findings

1. **Player availability is much more structured than the original reconnaissance implied for recent seasons.** Official public football availability-report systems now cover the SEC (2024+), Big Ten (2023+), MAC (2024+), and ACC, Big 12, American, Sun Belt and Conference USA (2025+), plus CFP games beginning 2025-26. This creates a high-confidence recent availability lane, especially for Texas A&M SEC games, while leaving nonconference and earlier history incomplete.
2. **Historical weather can use issued forecasts rather than observed-weather proxies.** NOAA HRRR archives preserve model runs from 2014, other NOAA archives extend useful model coverage, and Open-Meteo now exposes Previous Runs / Single Runs with explicit initialization/lead semantics.
3. **Timestamped historical market data is obtainable but high-quality PIT history is often paid.** The Odds API documents historical snapshots from June 2020 (5-minute intervals from September 2022); SportsDataIO exposes opening, movement and closing timestamps. The pure-football lane therefore remains essential and market enrichment stays optional.
4. **Lower-division strength can be better grounded without recursively modeling every program at FBS resolution.** NCAA official statistics cover FCS/DII/DIII; NAIA uses PrestoStats and added a 2026 data feed to NAIA.org; NJCAA publishes team/player statistics and rankings with substantial history.
5. **Rule era must expand beyond on-field rules.** House-settlement roster-limit changes effective in 2025 and the Division I age-based eligibility model adopted in 2026 materially change roster/experience semantics. Transfer/eligibility policy should be modeled as an effective-dated regulatory environment.
6. **Commercial advanced charting exists but does not justify a core dependency.** SIS, Stats Perform/Opta, Teamworks, SportsDataIO and Sportradar provide various deeper/live/licensed capabilities. They remain optional/research-only unless protected experiments show marginal value worth cost/rights/maintenance burden.
7. **Open national depth-chart, complete historical injury, pregame officiating-assignment and route/coverage/tracking data remain important gaps.** W06 did not find a legitimate scalable free source that closes these completely.
8. **Private-school resource asymmetry can be reduced, not eliminated.** IRS Form 990 bulk filings add institutional/foundation context for some private nonprofits, but must never be mislabeled as football-specific spending.

## What should definitely be collected
- SportsDataverse + CFBD national foundation with version/upstream provenance.
- NCAA official stats/membership/rules as validation, lower-division and regulatory evidence.
- Texas A&M official rosters, schedules, game notes/media guides and SEC availability reports.
- Official conference availability reports where covered.
- NOAA/Open-Meteo issued forecast-run evidence plus separate observed-weather evidence.
- EADA/Knight/IPEDS resource data.
- NCAA/NAIA/NJCAA official lower-division statistics sufficient for strength/translation priors.
- Dated official polls/rankings/award lists where tested as candidate features.

## Conditional/optional
- Timestamped commercial odds.
- Commercial injuries/live feeds.
- SIS/Opta/Teamworks advanced charting/tracking.
- IRS 990 private-resource proxies.

## Should not be made mandatory now
- PFF.
- Any restricted NCAA member system.
- Any source requiring access-control bypass.
- A full commercial tracking stack.
- A separate microservice architecture for each source.

## Remaining unavoidable gaps
- pre-official-report historical injury/availability completeness;
- national historical depth charts and snap-aligned role certainty;
- stable national pregame officiating assignments;
- open national route/coverage/formation/tracking;
- older timestamped betting line history;
- perfect private-school football financial comparability.
