# Football data and feature domains

The research scope is broader than scores and rankings. Breadth only helps when evidence is available, temporally appropriate, and useful in evaluation.

This is a capability guide, not a live coverage dashboard. A domain can have code and historical captures while remaining inadmissible for a particular pregame model. Current fitted outputs remain experimental.

| Domain | Research use | Evidence and admission boundary |
|---|---|---|
| Schedules and final scores | National population, targets, strength priors | Acquisition and normalization paths exist; final status and participant orientation must be established. |
| Team strength and schedule difficulty | National baseline expectation | Historical baselines exist; stale history and current-season state must be distinguished. |
| Team/player box scores, drives, play-by-play | Efficiency, explosiveness, turnovers, scoring opportunities | Capture and parsing paths exist with uneven coverage. Same-game postgame evidence cannot become that game's pregame input. |
| Rankings | Poll context and exposure | Current snapshots and historical publication authority differ. Missing poll evidence, unranked FBS, and inapplicable FCS polls are distinct states. |
| Conference and subdivision | Comparable populations and current membership | Season-specific authority is required; historical membership is not automatically current membership. |
| Venue, home field, neutral site | Location and playing context | Home/away orientation does not establish venue identity, coordinates, surface, or roof. |
| Weather | Wind, precipitation, temperature, and forecast uncertainty | Forecast-vintage acquisition paths exist. Observed game weather is not a pregame forecast; inferred coordinates do not establish venue authority. |
| Roster membership and returning production | Experience, continuity, turnover, and position-group depth | Research ingestion paths do not establish complete national current coverage. Membership and participation do not prove availability. |
| Injury and availability reports | Pregame uncertainty and personnel changes | Verified, timestamped public evidence is required. No complete admitted national availability layer is claimed. |
| Recruiting and transfers | Talent expectations and roster change | Research scope; no complete admitted national talent layer is claimed. Evaluation coverage, effective dates, and provider rights must be established. |
| Coaching and schemes | Continuity, staff changes, tenure, and regime comparisons | Research scope; no complete admitted national coaching layer is claimed. Associations alone do not establish a coach's causal effect. |
| Travel, time zones, rest | Fatigue and scheduling hypotheses | Derived research features require authoritative venues, schedule times, and a stated travel assumption. Distance is not evidence of actual team travel arrangements. |
| Market prices | Separate external benchmark | Capture paths exist. Preserve bookmaker, event, timestamp, orientation, and valid paired prices; never conceal market data in an independent forecast. |
| In-game state | Retrospective late-game and collapse analysis | Score, clock, possession, and field position are not pregame inputs. A live product needs separate admission and evaluation. |

## Minimum field-level evidence

For each value record its source, canonical entity, event/season scope, actual capture time, defensible known-at boundary, transformation, and admission disposition. If source publication time is unknown, say so. Capturing a page today does not prove what it said years ago.

## Coverage states

- **Available for this cutoff:** identity, temporal authority, and the candidate's input contract pass.
- **Candidate only:** evidence exists, but admission or suitability is unresolved.
- **Missing:** the required evidence was not obtained; do not invent a neutral value.
- **Not applicable:** the domain does not apply to this participant or contest.
- **Conflicted/quarantined:** contradictory evidence prevents use.

Learned missingness handling is a modeling choice, not permission to label missing evidence available. More domains do not guarantee better predictions; each addition needs chronological evaluation.

See [data and reuse](DATA_AND_REUSE.md) for source rights and [methodology](RESEARCH_METHOD.md) for the national-to-A&M comparison.
