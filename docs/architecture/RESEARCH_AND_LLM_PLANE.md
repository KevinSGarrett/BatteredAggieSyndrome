# Research and LLM Plane

## Research plane

Research operates on versioned, immutable inputs and writes:
- experiment configuration;
- candidate features/models;
- evaluation requests;
- error analyses;
- hypotheses;
- architecture proposals.

Research cannot directly write:
- ground truth;
- protected test windows;
- leakage policy;
- promotion thresholds;
- champion designation;
- historical results.

## LLM policy

LLMs are optional assistive tools, not a required dependency of the core prediction path.

Appropriate candidate uses:
- source/document interpretation;
- extracting structured candidates from unstructured injury/coaching/news evidence;
- schema/column interpretation;
- experiment/hypothesis generation;
- postmortem summarization.

Any LLM-derived factual extraction must retain source evidence, extraction version and confidence and pass deterministic validation or review before becoming canonical state.

Inappropriate core dependency:
- asking an LLM at forecast time to invent/guess structured football facts;
- allowing an LLM to alter PIT eligibility;
- allowing an LLM to decide its own promotion threshold;
- requiring an external LLM API for normal deterministic forecast refreshes.

## Isolation rule

Production components may consume approved artifacts that originated from a governed research process, but production runtime code must not import/call the research agent as a required dependency.
