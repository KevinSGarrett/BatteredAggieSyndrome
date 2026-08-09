# W23 — Local Production Operations

Wave 23 hardens the W19-W22 functional system without modifying forecast science.

## Implemented
- cross-platform core CI plus separately locked optional product-adapter CI;
- dependency pin/provenance policy, CodeQL and PR dependency review configuration;
- runtime environment manifests;
- append-only structured JSONL operational events and a dependency-free metric registry;
- credential/sensitive-key redaction before serialization;
- content-manifested backup/restore with path and hash verification;
- retention classes protecting governance, published forecasts and champion history;
- target-hardware benchmark harness and Windows operator wrapper.

## Deliberately not added
Docker, Kubernetes, Redis, PostgreSQL, an external log stack or an external metrics service are not required by the current single-host workload. These remain evidence-triggered options.

## Blocked evidence
The benchmark harness was smoke-tested in the build environment, but that environment does not match the target hardware. Therefore THR-011/THR-012 remain TBD and the W23 local-production gate is not cleared. This is a release blocker, not an implementation failure.
