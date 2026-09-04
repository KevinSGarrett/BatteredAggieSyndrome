# Pregame research report — T-24H evidence

**Label:** `T-24H_EVIDENCE_CAPTURED_NOT_FORECAST_FROZEN`. T-24H evidence is captured for contest 6607349. This is EVIDENCE_CAPTURED, not FORECAST_FROZEN. The table below is the preserved C26 EARLY_WEEK1 successor, not a new T-24H freeze.
**As of (UTC):** 2026-09-04T22:22:07Z
**Contest:** NCAA `6607349` — Texas A&M (home) vs Missouri State (away).
**Kickoff bound:** 2026-09-05T23:00:00Z (from frozen payload).
**Hold:** ACTIVE. Merge unauthorized. Scientific Done unauthorized.
**Trust:** `UNTRUSTED_SHADOW`. The 50% control is a control, never a recommendation.

## BAS candidates (frozen C26 successor of C24 EARLY_WEEK1)

| Candidate | P(home) | P(away) | Margin home | Interval home | Interval level emitted | Trust | Role |
| --- | --- | --- | --- | --- | --- | --- | --- |
| national_base_rate | 0.5 | 0.5 | null | null | None | UNTRUSTED_SHADOW | control (never recommended) |
| national_elo | 0.68188773 | 0.31811227 | null | null | None | UNTRUSTED_SHADOW | shadow candidate |
| national_logistic_l2 | 0.9181732306 | 0.0818267694 | null | null | None | UNTRUSTED_SHADOW | shadow candidate |
| national_margin_ridge | 0.8951316669 | 0.1048683331 | 22.2506043541 | [-0.4836117392, 44.9848204474] | 0.95 | UNTRUSTED_SHADOW | shadow candidate |
| prior_only | 0.8055401846 | 0.1944598154 | null | null | None | UNTRUSTED_SHADOW | shadow candidate |

Ridge probability, margin, and interval are from the same declared Normal residual. Emitted `nominal_interval_level=0.95` does not match declared mass 0.8 (confirmed implementation defect; predecessor rows not rewritten).

## Market reference

**Market:** `ABSENT` (`INSUFFICIENT_MARKET_COVERAGE`). Captured quote count: 0. Consensus median home margin: null. User quotations and browser observations are not receipts. A captured quote count is not a valid two-sided same-book spread+total pair.

## Market-line implied score reference

**Withheld:** `INCOMPATIBLE_SCORE_REFERENCE` (MISSING_BOOK_IDENTITY). Not an independent BAS predicted score. Values were not clamped.

## Other named models

**Other models:** `ABSENT`. No independently sourced, timestamped, identity-matched external-model capture is attached. Equal percentages do not make a numberFire quote into ESPN FPI.

## Coaching context (CONTEXT_ONLY / NOT_CONSUMED_BY_MODEL)

- National domain `coaching_staff`: `SOURCE_ABSENT`.
- Structured acquisition-registry coach entry: `False`.
- Texas A&M staff fetch: `BLOCKED HTTP 404 https://12thman.com/sports/football/coaches final=https://12thman.com/sports/football/coaches sha256=0727fc51fd376c4688e9321eb6627a9254a6d28b2ec0f2182e3ed07eb8cedcc8 retrieved_at=2026-09-04T22:22:08Z identity=PAGE_IDENTITY_PLAUSIBLE error=HTTP Error 404: Not Found; BLOCKED HTTP 404 https://12thman.com/sports/football/staff final=https://12thman.com/sports/football/staff sha256=41421da0617ad504ca75822af5c1913effc0f5f2e5a58873a9da25c321b80a76 retrieved_at=2026-09-04T22:22:08Z identity=PAGE_IDENTITY_PLAUSIBLE error=HTTP Error 404: Not Found; BLOCKED HTTP 200 https://12thman.com/coaches.aspx?path=football final=https://12thman.com/sports/womens-golf/roster/season/2016-17/staff/trelle-mccombs sha256=bb00e5a0f93d66df41b170ad0e9b498dde053065de8d35e4546f5e57962e1f72 retrieved_at=2026-09-04T22:22:08Z identity=WRONG_RESOURCE_REDIRECT error=WRONG_RESOURCE_REDIRECT`.
- Missouri State staff fetch: `BLOCKED HTTP None https://missouristatebears.com/sports/football/coaches final=https://missouristatebears.com/sports/football/coaches sha256=None retrieved_at=2026-09-04T22:22:09Z identity=PAGE_IDENTITY_PLAUSIBLE error=URLError: <urlopen error [Errno 11002] getaddrinfo failed>`.
- HC/OC/DC titles, when observed on an official page, remain titles. Play-caller roles are `UNKNOWN` unless contemporaneous non-title evidence exists.
- Coaching does not affect any displayed BAS number.

## Other unused/missing domains

- `coaching`: **BLOCKED** — No HC/OC/DC/play-caller columns in active Week1 designs. coaches_poll_rank is a poll, not staff. Official staff packets, if any, remain CONTEXT_ONLY / NOT_CONSUMED_BY_MODEL.
- `recruiting_talent`: **ABSENT** — national_pit_domain_admission coaching-adjacent recruiting_talent SOURCE_ABSENT.
- `roster_availability`: **ABSENT** — Spine ROSTER_MEMBERSHIP and PREGAME_AVAILABILITY SOURCE_EVIDENCE_ABSENT for 182 cells.
- `weather`: **CANDIDATE_ONLY** — week1_feature_construction.weather_admitted_as_model_input is false; weather vintage capture is not a consumed feature.
- `travel_rest`: **ABSENT** — No travel/rest feature columns in ALL_ADMITTED_FEATURES.
- `market`: **ABSENT** — Market references attach separately and do not enter the fitted design. Captured focus-contest quotes: 0.
- `strength_context`: **ACTUALLY_CONSUMED** — Prior game counts, site, FBS, conference (when in training levels), AP rank when present, and learned missingness indicators.
- `coaches_poll_rank`: **ACTUALLY_CONSUMED** — Consumed as Coaches Poll ranking with missingness indicator; not staff.
- `learned_missingness`: **ACTUALLY_CONSUMED** — Missing prior rates/margins/ranks/venue fields are explicit indicators, not imputed means without an indicator.

## Disagreement diagnosis

**Classes:** CONFIRMED_IMPLEMENTATION_DEFECT, INPUT_LIMITATION, MODEL_SPECIFICATION_LIMITATION, UNEXPLAINED_DISAGREEMENT.

C26 ridge emits P(home)=0.8951316669 and expected home margin +22.2506043541 from a Normal residual on ALL_ADMITTED_FEATURES. The largest arithmetic contributions are learned missingness, home indicator, intercept, and prior game-count z-scores. Coaching is not consumed. Captured market quotes for this contest: 0.

Linear contributions are model arithmetic, not causal explanations. An 18-point market gap is not a verified residual unless a captured same-event quote exists; captured quotes are not automatically a compatible spread+total pair. Exploratory matchup slices stay `EXPLORATORY`.

## Independent predicted score

`independent_predicted_score = None`

**Blocker:** NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE; active suite emits probability and ridge margin only; JointScoreDistribution/IndependentPoissonScoreRuntime are interfaces/experiments, not frozen Week1 outputs; preliminary Poisson and offense/defense Elo used 2024/2025 which are historically exposed and not blind; deprecated experiments are not enabled.

No actual-score column. Week 1 outcomes are not training data.

## What a reader may and may not infer

- May read the shadow probabilities and supported ridge margin as issued, with trust `UNTRUSTED_SHADOW`.
- May not treat the control as a pick.
- May not treat this report as T-24H or T-90M.
- May not treat coaching titles as model inputs or play-caller proof.
- May not treat a line-implied score, if later eligible, as a BAS final-score prediction.
- May not conclude calibration, BAS, or persistent underperformance from one game.
