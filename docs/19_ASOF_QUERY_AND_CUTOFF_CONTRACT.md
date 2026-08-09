# As-Of Query, Forecast Cutoff and Replay Contract

## Immutable cutoff record
Every replay/forecast has an immutable cutoff record containing at least: cutoff ID, purpose, target game (when applicable), prediction timestamp, target-event time, forecast lane, temporal-policy version, data-snapshot ID and creation lineage.

## Selection algorithm
For each candidate observation:
1. apply hard domain prohibitions;
2. establish the defensible knowledge time (`first_known_at`, otherwise conservative retrieval fallback);
3. require knowledge time `<= prediction_timestamp`;
4. require target event/state time to be within the observation's valid interval where relevant;
5. reconstruct revision/supersession state **as it was knowable at the cutoff**;
6. apply source/domain precedence and deterministic tie-breaking;
7. return immutable observation IDs and lineage, not only values.

## Training replay
There are two cutoffs that must not be conflated:
- the **feature cutoff for each historical example** (pregame for that game);
- the **model-training cutoff** determining which completed historical games/labels were available to the training run.

A training run at time T cannot train on a future game's outcome merely because a backfilled table now contains it.

## Future-effective knowledge
A rule announced in June and effective in September may be used in an August forecast for an October target game if the exact rule was public by the forecast cutoff and the October target lies in the rule's valid interval. This is why knowledge time and validity time are separate.
