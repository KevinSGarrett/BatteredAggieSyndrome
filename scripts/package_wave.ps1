param(
    [Parameter(Mandatory=$true)][string]$Wave,
    [Parameter(Mandatory=$true)][string]$OutputDir,
    [string]$PreviousCumulative
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$argsList = @("tools/package_wave.py", "--repo-root", ".", "--wave", $Wave, "--output-dir", $OutputDir)
if ($PreviousCumulative) { $argsList += @("--previous-cumulative", $PreviousCumulative) }
python @argsList
