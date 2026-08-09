# Local Research Resource Scheduling and Concurrency

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Target hardware

The project continues to target Ryzen 7 HX-class CPU, 32 GB RAM, RTX 5060-class GPU and NVMe storage for core Phases 1–4. Wave 18 therefore treats local bounded execution as the baseline, not a Kubernetes/distributed cluster.

## Slots

The scheduler models CPU threads, RAM, GPU slots, VRAM and disk/artifact pressure. A task may request zero GPU. Experiments that exceed local resources remain blocked or can be explicitly approved for optional remote execution later.

## Concurrency

Default concurrency is conservative. CPU-heavy feature materialization, GPU-heavy training, and disk-heavy scans should not all be maximized simultaneously. The scheduler admits only work that fits remaining resource slots.

## Paid compute

Paid compute is off unless the user explicitly authorizes it. No HPO study can silently convert a local experiment into cloud spend.

## Observability

Each execution records requested versus observed resource usage where available. W19–W23 can use those measurements to refine budgets. W18 does not invent runtime/VRAM numbers before real workloads exist.
