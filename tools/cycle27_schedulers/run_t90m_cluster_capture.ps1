# Cycle 27 parameterized national T-90M cluster capture. Does NOT git-commit.
# Does not kill A&M or the already-armed Friday 21:00Z sleeper (PIDs 40708/41416).
param(
  [Parameter(Mandatory = $true)][string]$Checkpoint,
  [Parameter(Mandatory = $true)][string]$TargetUtc,
  [Parameter(Mandatory = $true)][string]$CutoffUtc,
  [Parameter(Mandatory = $true)][string]$CohortContest,
  [string]$Owner = "CYCLE27_T90M_CLUSTER"
)

$ErrorActionPreference = "Stop"
$Repo = "C:\BatteredAggieSyndrome.data\worktrees\BAT-690-c27-scr"
$Ops26 = "C:\BatteredAggieSyndrome.data\ops\cycle26"
$Ops27 = "C:\BatteredAggieSyndrome.data\ops\cycle27"
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmss")
$Log = Join-Path $Ops27 ("CYCLE27_{0}_SCHEDULER_{1}Z.log" -f $Checkpoint, $stamp)
$RunId = ("c27-{0}-" -f $Checkpoint.ToLower()) + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
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
  Log "CYCLE27_T90M_CLUSTER_START checkpoint=$Checkpoint run_id=$RunId target=$TargetUtc sleep_seconds=$sec cutoff=$CutoffUtc cohort=$CohortContest no_git_commit=1"
  if ($sec -gt 0) { Start-Sleep -Seconds $sec }

  if ([DateTime]::UtcNow -ge $cutoff) {
    Log "MISSED_CUTOFF_NO_BACKFILL now=$([DateTime]::UtcNow.ToString('o'))"
    exit 2
  }

  $acquire = python -B -c @"
import json, os, sys
sys.path.insert(0, os.environ['PYTHONPATH'].split(';')[0])
from aggie_analytics.operations.checkpoint_lease import acquire
print(json.dumps(acquire(checkpoint='$Checkpoint', owner='$Owner', run_id='$RunId', ttl_seconds=3600, heartbeat_seconds=60, pid=$PID)))
"@
  if ($LASTEXITCODE -ne 0) { throw "lease acquire failed exit=$LASTEXITCODE" }
  Log "LEASE $acquire"
  $leaseObj = $acquire | ConvertFrom-Json
  if (-not $leaseObj.ok) { throw "lease not acquired: $acquire" }

  Log "START capture Phase=T90M run_id=$RunId"
  & powershell -NoProfile -File (Join-Path $Ops26 "run_week1_checkpoint_capture.ps1") -Phase T90M 2>&1 | ForEach-Object { Log $_ }
  if ($LASTEXITCODE -ne 0) { throw "capture runner failed exit=$LASTEXITCODE" }

  python -B (Join-Path $Ops27 "bind_cycle27_checkpoint_receipt.py") --checkpoint $Checkpoint --phase T90M --run-id $RunId --log $Log --cutoff $CutoffUtc --cohort-contest $CohortContest 2>&1 | ForEach-Object { Log $_ }
  if ($LASTEXITCODE -ne 0) { throw "receipt bind failed exit=$LASTEXITCODE" }

  python -B -c @"
import json, os, sys
sys.path.insert(0, os.environ['PYTHONPATH'].split(';')[0])
from aggie_analytics.operations.checkpoint_lease import release
print(json.dumps(release(checkpoint='$Checkpoint', run_id='$RunId', pid=$PID)))
"@ | ForEach-Object { Log $_ }
  if ($LASTEXITCODE -ne 0) { throw "lease release failed exit=$LASTEXITCODE" }

  Log "CYCLE27_T90M_CLUSTER_COMPLETE no_git_commit=1"
}
catch {
  Log "FATAL $($_.Exception.Message)"
  throw
}
