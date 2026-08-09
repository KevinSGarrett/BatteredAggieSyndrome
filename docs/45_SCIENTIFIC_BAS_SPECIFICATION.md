# Scientific BAS Specification — Wave 15

## Headline definition
BAS is **not** `P(Texas A&M loses)`.

For a Texas A&M game orientation:

`performance_residual = actual_A&M_margin - expected_A&M_margin`

and positive shortfall is:

`underperformance_shortfall = expected_A&M_margin - actual_A&M_margin = -performance_residual`.

The headline event is `BAS >= 7 <=> performance_residual <= -7`, with nested severity events at **3, 7, 14 and 21 points**. These thresholds are part of the label definition and are not tuned to maximize an observed A&M effect.

## Expected-margin requirement
Historical expected margin must be strictly pregame, out-of-sample and generated under a chronological model-training cutoff. The target canonical game and all mirrored representations are excluded. The primary scientific anchor is BAS-independent and cannot use a BAS label/target or an A&M-underperformance target.

W15 freezes these properties but **does not select the expectation model family**. W16 defines eligible model architecture; W17 owns protected empirical evaluation.

## Label immutability
Every label links to expectation model/version, fold/strategy, prediction cutoff, training cutoff, data snapshot and label-definition version. A changed anchor/version creates a new label version; historical labels are not overwritten.

## Scientific posture
The project must be able to conclude that no stable A&M-specific excess underperformance exists. Product naming or fan narrative cannot force an effect.
