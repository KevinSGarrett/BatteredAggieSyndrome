# OpenAI assistive plane architecture

The optional adapter is deliberately one-way:

```text
versioned task + strict schema + cited excerpt
  -> governed controller
  -> deterministic/cache first; Nano bulk route
  -> 4o Mini or Luna only for task-specific failures
  -> Terra complex ambiguity; Sol hard/high-risk residue
  -> Responses or Batch API
  -> content-addressed external response
  -> strict schema/evidence/provenance validators
  -> candidate | review | quarantine | rejected
  -> existing deterministic domain workflow
```

No production forecast module imports `aggie_analytics.openai_assist`. The package is an offline research/data-engineering adapter. Its outputs have no route to canonical or protected state except through existing deterministic acceptance workflows. The controller enforces the verified `651bbf...aa523` plan, staged cumulative releases, $15/$10 Terra/Sol base caps, $25/$17 absolute Terra/Sol maxima after measured reserve release, and the overall $100 hard stop.

See `governance/OPENAI_ASSISTIVE_PLANE.md`, `configs/openai_assist_policy.json`, and `schemas/openai/assistive_candidate.schema.json` for the controlling contracts.
