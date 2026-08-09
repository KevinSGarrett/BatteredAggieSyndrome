# Recruiting, Transfer & Freshman Intelligence — Wave 12

## One player identity
A transfer does not create a new player. W07 canonical identity persists while team membership, position, role and transfer episodes change over time.

## Transfer translation
Raw production is not assumed portable across environments. Fixed rules such as `G5 QB -> SEC = -15%` are prohibited.

Candidate translation training uses historical same-player transfers and position-aware inputs such as:
- source opponent-adjusted production;
- continuous opponent/team strength;
- experience/starts/snaps;
- recruiting prior;
- source supporting cast;
- destination supporting cast;
- source/destination scheme context;
- destination competition distribution;
- expected destination role.

Candidate outputs:
- expected destination player value;
- expected usage;
- translation delta;
- uncertainty.

No translation model or coefficient is selected in W12.

## Freshmen/prospects
Players with zero college production use a separate prospect prior rather than a transfer-production model. Candidate evidence includes recruiting rating/rank, physical profile where legitimately known, historical similar recruits, program development history, position and expected role.

Uncertainty should begin wide and shrink as PIT-safe college evidence accumulates.

## Recruiting/transfer source rights
W12 completes the missing upstream provenance/access-license augmentation and audits the W06 recruiting/transfer source lanes. Public visibility is not treated as permission to repackage data. Raw snapshots must preserve retrieval/provenance/terms context.
