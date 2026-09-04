# Versioned Cycle 27 Friday earliest T-90M national raw capture caller.
# Wake 20:15Z, cutoff 21:00Z for contest 6594366. Does NOT git-commit.
# Live sleeper copies under ops/cycle27 remain the armed owners; this file is
# the reviewed source for caller tests.
param(
  [string]$TargetUtc = "2026-09-04T20:15:00Z",
  [string]$CutoffUtc = "2026-09-04T21:00:00Z"
)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Ops26 = "C:\BatteredAggieSyndrome.data\ops\cycle26"
$Ops27 = "C:\BatteredAggieSyndrome.data\ops\cycle27"
$Log = Join-Path $Ops27 ("CYCLE27_FRIDAY_T90M_SCHEDULER_{0:yyyyMMddTHHmmss}Z.log" -f (Get-Date).ToUniversalTime())
$RunId = "c27-fri-t90m-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$env:PYTHONPATH = "$Repo\src;$Repo"

function Log([string]$Msg) {
  $line = "[{0:o}] {1}" -f [DateTime]::UtcNow, $Msg
  Add-Content -Path $Log -Value $line
  Write-Output $line
}

try {
  $target = [DateTime]::Parse($TargetUtc, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
  $cutoff = [DateTime]::Parse($CutoffUtc, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
  $sec = [Math]::Max(0, [int]($target - [DateTime]::UtcNow).TotalSeconds)
  Log "CYCLE27_FRIDAY_T90M_SCHEDULER_START run_id=$RunId target=$TargetUtc sleep_seconds=$sec cutoff=$CutoffUtc no_git_commit=1"
  if ($sec -gt 0) { Start-Sleep -Seconds $sec }

  if ([DateTime]::UtcNow -ge $cutoff) {
    Log "MISSED_CUTOFF_NO_BACKFILL now=$([DateTime]::UtcNow.ToString('o'))"
    exit 2
  }

  $acquire = python -B -c @"
import json, os, sys
sys.path.insert(0, os.environ['PYTHONPATH'].split(';')[0])
from aggie_analytics.operations.checkpoint_lease import acquire
print(json.dumps(acquire(checkpoint='FRI_T90M_20260904T2100Z', owner='CYCLE27_FRIDAY_T90M', run_id='$RunId', ttl_seconds=3600, heartbeat_seconds=60, pid=$PID)))
"@
  if ($LASTEXITCODE -ne 0) { throw "lease acquire failed exit=$LASTEXITCODE" }
  Log "LEASE $acquire"
  $leaseObj = $acquire | ConvertFrom-Json
  if (-not $leaseObj.ok) { throw "lease not acquired: $acquire" }

  Log "START capture Phase=T90M run_id=$RunId"
  & powershell -NoProfile -File (Join-Path $Ops26 "run_week1_checkpoint_capture.ps1") -Phase T90M 2>&1 | ForEach-Object { Log $_ }
  if ($LASTEXITCODE -ne 0) { throw "capture runner failed exit=$LASTEXITCODE" }

  python -B (Join-Path $Ops27 "bind_cycle27_checkpoint_receipt.py") --checkpoint FRI_T90M_20260904T2100Z --phase T90M --run-id $RunId --log $Log --cutoff $CutoffUtc --cohort-contest 6594366 2>&1 | ForEach-Object { Log $_ }
  if ($LASTEXITCODE -ne 0) { throw "receipt bind failed exit=$LASTEXITCODE" }

  python -B -c @"
import json, os, sys
sys.path.insert(0, os.environ['PYTHONPATH'].split(';')[0])
from aggie_analytics.operations.checkpoint_lease import release
print(json.dumps(release(checkpoint='FRI_T90M_20260904T2100Z', run_id='$RunId', pid=$PID)))
"@ | ForEach-Object { Log $_ }
  if ($LASTEXITCODE -ne 0) { throw "lease release failed exit=$LASTEXITCODE" }

  Log "CYCLE27_FRIDAY_T90M_SCHEDULER_COMPLETE no_git_commit=1"
}
catch {
  Log "FATAL $($_.Exception.Message)"
  throw
}
