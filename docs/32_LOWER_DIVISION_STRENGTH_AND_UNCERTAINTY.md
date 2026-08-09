# Lower-Division Strength and Uncertainty — Wave 11

## Bounded hierarchy
The project does not recursively build a full advanced model of every football program.

| Level | Intended depth |
|---|---|
| FBS | full national foundation |
| FCS | strong secondary strength model |
| D-II | coarse ratings/results |
| D-III | coarse prior |
| NAIA | team prior where feasible, otherwise class prior |
| JUCO | class/origin prior |
| Other | boundary prior |

## Continuous strength
Every opponent ultimately needs:
- a continuous strength estimate;
- a strength uncertainty estimate.

Division labels alone are insufficient.

## FCS
FCS-vs-FCS games establish internal relative strength. FCS-vs-FBS games help learn cross-division translation. No fixed `FCS = -N points` penalty is allowed.

## Lower divisions
D-II/D-III/NAIA/JUCO support progressively coarser priors. Sparse evidence increases uncertainty rather than forcing arbitrary directional corrections.

## Workload is separate
A weak opponent can still create physical workload. Opponent-quality translation must not replace actual snaps/drives/travel/workload evidence.

## Empirical implementation
Actual cross-division functions and uncertainty calibration require materialized historical data and chronological testing later.
