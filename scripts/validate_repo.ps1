$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
python tools/validate_repository.py --repo-root . --strict
python -m unittest discover -s tests -v
