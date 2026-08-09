param(
    [switch]$SkipInstall
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3.12 scripts/bootstrap.py $(if ($SkipInstall) { "--skip-install" })
} else {
    & python scripts/bootstrap.py $(if ($SkipInstall) { "--skip-install" })
}
