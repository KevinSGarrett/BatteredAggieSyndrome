param(
    [Parameter(Mandatory=$true)][string]$Hydration,
    [Parameter(Mandatory=$true)][string]$Cumulative,
    [Parameter(Mandatory=$true)][string]$ExpectedNextWave,
    [string]$ExtractTo
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$argsList = @("tools/verify_prior_wave.py", "--hydration", $Hydration, "--cumulative", $Cumulative, "--expected-next-wave", $ExpectedNextWave)
if ($ExtractTo) { $argsList += @("--extract-to", $ExtractTo) }
python @argsList
