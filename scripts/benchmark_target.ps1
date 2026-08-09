$ErrorActionPreference = "Stop"
python tools/run_local_benchmark.py --profile representative --output artifacts/benchmarks/w23-target.json
Write-Host "Review target_match/authoritative_for_thr_011_012 before freezing THR-011/THR-012."
