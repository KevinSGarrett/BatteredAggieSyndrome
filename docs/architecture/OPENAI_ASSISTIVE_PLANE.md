# OpenAI assistive plane architecture

The optional adapter is deliberately one-way:

```text
versioned task + strict schema + cited excerpt
  -> governed controller
  -> Responses or Batch API
  -> content-addressed external response
  -> strict schema/evidence/provenance validators
  -> candidate | review | quarantine | rejected
  -> existing deterministic domain workflow
```

No production forecast module imports `aggie_analytics.openai_assist`. The package is an offline research/data-engineering adapter. Its outputs have no route to canonical or protected state except through existing deterministic acceptance workflows.

See `governance/OPENAI_ASSISTIVE_PLANE.md`, `configs/openai_assist_policy.json`, and `schemas/openai/assistive_candidate.schema.json` for the controlling contracts.
