# Versioned Cycle 27 Friday T-90M failover. Uses the packaged policy module.
# START is not completion. Does not git-commit. Does not kill A&M sleepers.
$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Ops27 = "C:\BatteredAggieSyndrome.data\ops\cycle27"
$Log = Join-Path $Ops27 "CYCLE27_FRIDAY_T90M_FAILOVER.log"
$env:PYTHONPATH = "$Repo\src;$Repo"

function Log([string]$Msg) {
  $line = "[{0:o}] {1}" -f [DateTime]::UtcNow, $Msg
  Add-Content -Path $Log -Value $line
  Write-Output $line
}

$wake = [DateTime]::Parse("2026-09-04T20:15:00Z", $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
$cutoff = [DateTime]::Parse("2026-09-04T21:00:00Z", $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
$windowOpen = [DateTime]::Parse("2026-09-04T20:00:00Z", $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
$sec = [Math]::Max(0, [int](($wake - [DateTime]::UtcNow).TotalSeconds))
Log "FRIDAY_T90M_FAILOVER_SLEEP seconds=$sec"
if ($sec -gt 0) { Start-Sleep -Seconds $sec }

$attempts = 0
while ([DateTime]::UtcNow -lt $cutoff) {
  $primaryAlive = $false
  Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | ForEach-Object {
    if ($_.CommandLine -and $_.CommandLine -match 'run_friday_t90m_capture.ps1') { $script:primaryAlive = $true }
  }
  $receipt = Get-ChildItem (Join-Path $Ops27 "receipts\FRI_T90M_20260904T2100Z\*.json") -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
  $verified = $false
  $completedAt = $null
  if ($receipt) {
    $txt = Get-Content $receipt.FullName -Raw
    if ($txt -match '"receipt_verified"\s*:\s*true') { $verified = $true }
    if ($txt -match '"completed_at_utc"\s*:\s*"([^"]+)"') { $completedAt = $Matches[1] }
  }
  $progressLogs = Get-ChildItem (Join-Path $Ops27 "CYCLE27_FRIDAY_T90M_SCHEDULER_*.log") -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $lastProgress = $null
  if ($progressLogs) { $lastProgress = $progressLogs.LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ") }

  $decision = python -B -c @"
import json, os, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.environ['PYTHONPATH'].split(';')[0])
from aggie_analytics.operations.checkpoint_failover_policy import decide
def parse(value):
    if not value or value == 'None':
        return None
    return datetime.fromisoformat(value.replace('Z','+00:00'))
now = datetime.now(timezone.utc)
d = decide(
    now=now,
    wake=parse('$($wake.ToString('yyyy-MM-ddTHH:mm:ssZ'))'),
    cutoff=parse('$($cutoff.ToString('yyyy-MM-ddTHH:mm:ssZ'))'),
    capture_window_open=parse('$($windowOpen.ToString('yyyy-MM-ddTHH:mm:ssZ'))'),
    primary_alive=$($primaryAlive.ToString().ToLower()),
    last_progress=parse('$lastProgress'),
    completion_receipt_verified=$($verified.ToString().ToLower()),
    completed_at=parse('$completedAt'),
    attempts=$attempts,
    max_attempts=3,
    required_attempt_budget=timedelta(minutes=5),
    progress_timeout=timedelta(minutes=6),
)
print(json.dumps({'action': d.action, 'reason': d.reason}))
"@
  if ($LASTEXITCODE -ne 0) { throw "failover policy failed exit=$LASTEXITCODE" }
  Log "DECISION $decision"
  $obj = $decision | ConvertFrom-Json
  if ($obj.action -eq "COMPLETE") { Log "VERIFIED_COMPLETE"; exit 0 }
  if ($obj.action -in @("MISSED_CUTOFF_NO_BACKFILL","RETRY_BUDGET_EXHAUSTED","INSUFFICIENT_TIME_FOR_RETRY")) { Log "STOP $($obj.action)"; exit 2 }
  if ($obj.action -eq "START_RETRY_AFTER_EXCLUSIVE_LEASE") {
    $attempts++
    Log "START_RETRY attempt=$attempts"
    & powershell -NoProfile -File (Join-Path $PSScriptRoot "run_friday_t90m_capture.ps1") -TargetUtc ([DateTime]::UtcNow.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"))
    if ($LASTEXITCODE -ne 0) { Log "RETRY_EXIT=$LASTEXITCODE" }
  }
  elseif ($obj.action -eq "STALLED_PRIMARY") {
    Log "STALLED_PRIMARY_NO_DUPLICATE"
  }
  Start-Sleep -Seconds 30
}
Log "LOOP_END_WITHOUT_VERIFIED_RECEIPT"
exit 2
