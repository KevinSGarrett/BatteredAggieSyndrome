# W23 Target-Hardware Benchmark Procedure

`AC-038`, `THR-011` and `THR-012` require evidence from the actual target class: Windows, Ryzen 7 HX-class CPU, 32 GB RAM, RTX 5060-class GPU, NVMe.

Run on that machine:

```powershell
python tools/run_local_benchmark.py --profile representative --output artifacts/benchmarks/w23-target.json
```

The harness records host identity, wall-clock timings and Python allocation peaks for deterministic representative starter workloads. A result is marked authoritative for THR-011/012 only when the declared target profile matches and the representative profile is used. The W23 build environment is not the target machine, so its smoke result cannot freeze RAM/runtime budgets.

Do not convert smoke numbers into target budgets. After a target run, review the evidence and freeze governed thresholds explicitly rather than having the benchmark mutate governance automatically.
