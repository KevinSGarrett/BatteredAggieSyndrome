# OpenRouter Assistive Plane Architecture

The provider-neutral dispatcher owns task admission, request identity, strict-schema validation, redaction, budget reservation, external manifests, disposition, and final deterministic validation. Exactly one backend owns OpenRouter HTTP behavior and credential loading. The existing direct OpenAI controller remains unchanged and separately governed.

```text
bounded task packet
  -> provider-neutral dispatcher
  -> authority + secret + schema + budget gates
  -> one selected backend
  -> strict candidate response
  -> deterministic evidence/path/test validation
  -> candidate | review | quarantine | rejected
```

The production OpenRouter policy has a separate USD 25 hard limit and a lower USD 5 released pilot stage. Both are enforced locally before dispatch, and later releases require empirical evidence. Fake-client tests exercise budget, schema, and provider boundaries independently. Public catalog capture is a separate non-billable read-only operation.

Operational data is content-addressed outside Git. Repository code contains only policy, schemas, adapter/controller code, tests, and documentation. Batch Beta is disabled pending its separate gate.
