param(
    [ValidateSet('core','product')][string]$Profile = 'core',
    [string]$Output = 'artifacts/readiness/bootstrap-check.json'
)
$ErrorActionPreference = 'Stop'
python tools/bootstrap_readiness.py --repo-root . --profile $Profile --output $Output
exit $LASTEXITCODE
