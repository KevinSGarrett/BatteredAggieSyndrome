# Mutable Domain Snapshot Policies

## Availability
Preserve policy ID, policy effective dates, game/conference scope, report sequence/version, publication/first-known/retrieval time and each player status observation. Later reports supersede earlier reports only for cutoffs after the later report became knowable. **No report or non-covered game means UNKNOWN, not healthy.**

## Weather
Pregame reconstruction uses an issued forecast run known by the cutoff, with provider/model/version, model initialization, model availability/first-known, target valid time, lead and retrieval lineage. Observed/reanalysis weather is postgame truth and may not replace what a Monday/Wednesday/Friday forecast actually knew.

## Market
Store provider + market + side observations with source-reported/retrieved/first-known times. `opening/current/closing` is descriptive when defensible; it is not an eligibility shortcut. Pure-football forecasts exclude market inputs entirely.

## Roster/staff/depth
Use effective-dated episodes plus knowledge timestamps. A current bio or current roster page is not proof of what was knowable on an earlier game week.

## Regulatory environment
Store both publication/knowability and effective intervals. Rule/eligibility/roster/transfer changes apply according to target-game validity, not merely season number.

## Resources
Reporting period and public release date are distinct. A report about an older fiscal period can still leak if it became public after the historical prediction cutoff.

## Historical outputs
PBP/box-score/final results for the target game are forbidden pregame. Prior games may contribute only after completion and source availability, with chronological training replay maintained.
