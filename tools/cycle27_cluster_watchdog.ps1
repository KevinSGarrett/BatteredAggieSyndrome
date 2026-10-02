# Durable Cycle 27 T-90M and T-24H cluster watchdog. Restarts a dead owner only
# when the cutoff is still open and no verified receipt exists. Does not backfill.
# Also restarts A&M T-90M primary if both C26 owners are dead before cutoff.
$ErrorActionPreference = "Stop"
$Ops26 = "C:\BatteredAggieSyndrome.data\ops\cycle26"
$Ops27 = "C:\BatteredAggieSyndrome.data\ops\cycle27"
$Repo = "C:\BatteredAggieSyndrome.data\worktrees\BAT-690-c27-scr"
$Log = Join-Path $Ops27 "CYCLE27_CLUSTER_WATCHDOG.log"
$T24Arm = Join-Path $Ops27 "CYCLE27_REMAINING_T24_CLUSTER_ARM.json"
$Lease = Join-Path $Repo "artifacts\scientific_integrity\cycle27\CYCLE27_LEASE_AND_RESTART_PLAN.json"
$until = [DateTime]::Parse("2026-09-08T00:00:00Z").ToUniversalTime()
$amT90Cutoff = [DateTime]::Parse("2026-09-05T21:30:00Z").ToUniversalTime()
$amT90Wake = "2026-09-05T20:45:00Z"

function Log([string]$Msg) {
  $line = "[{0:o}] {1}" -f [DateTime]::UtcNow, $Msg
  Add-Content -Path $Log -Value $line
}

function CheckpointName([datetime]$Cutoff) {
  $stamp = $Cutoff.ToUniversalTime().ToString("yyyyMMddTHHmmZ")
  switch ($Cutoff.ToUniversalTime().Day) {
    4 { return "FRI_T90M_$stamp" }
    5 { return "SAT_T90M_$stamp" }
    6 { return "SUN_T90M_$stamp" }
    default { return "MON_T90M_$stamp" }
  }
}

function LiveCommandLines([string]$Pattern) {
  return (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $Pattern } | ForEach-Object { $_.CommandLine }) -join "`n"
}

Log "WATCHDOG_START until=$($until.ToString('o')) t24=1 am90_restart=1"
while ([DateTime]::UtcNow -lt $until) {
  $liveT90 = LiveCommandLines 'run_t90m_cluster_capture'
  $liveT24 = LiveCommandLines 'run_t24h_cluster_capture'
  $am24 = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_scheduled_am_t24h_capture' }).Count
  $am90 = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_scheduled_am_t90m_capture' }).Count
  $am90Fail = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_am_t90m_failover' }).Count
  Log "heartbeat am24=$am24 am90=$am90 am90_failover=$am90Fail live_t90=$($liveT90.Length) live_t24=$($liveT24.Length)"

  if (Test-Path $Lease) {
    $plan = Get-Content $Lease -Raw | ConvertFrom-Json
    foreach ($cluster in $plan.saturday_t90_clusters_starting_2026_09_05T14_30Z) {
      $cutoff = [DateTime]::Parse($cluster.cutoff_utc).ToUniversalTime()
      $name = CheckpointName $cutoff
      if ($cluster.cutoff_utc -eq "2026-09-05T21:30:00Z") { continue }
      if ([DateTime]::UtcNow -ge $cutoff) { continue }
      $latest = Join-Path $Ops27 ("receipts\{0}\LATEST.json" -f $name)
      if (Test-Path $latest) { continue }
      if ($liveT90 -match [regex]::Escape($name)) { continue }
      $ids = $cluster.national_contest_ids
      if (-not $ids) { $ids = $cluster.contest_ids }
      if (-not $ids) { continue }
      Log "RESTART_DEAD_T90_OWNER checkpoint=$name cutoff=$($cutoff.ToString('o'))"
      Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $Ops27 "run_t90m_cluster_capture.ps1"),
        "-Checkpoint", $name, "-TargetUtc", $cluster.wake_utc, "-CutoffUtc", $cluster.cutoff_utc,
        "-CohortContest", $ids[0]
      ) -WindowStyle Hidden | Out-Null
    }
  }

  if (Test-Path $T24Arm) {
    $arm = Get-Content $T24Arm -Raw | ConvertFrom-Json
    foreach ($cluster in $arm.launched) {
      $cutoff = [DateTime]::Parse($cluster.cutoff_utc).ToUniversalTime()
      $name = [string]$cluster.checkpoint
      if ([DateTime]::UtcNow -ge $cutoff) { continue }
      $latest = Join-Path $Ops27 ("receipts\{0}\LATEST.json" -f $name)
      if (Test-Path $latest) { continue }
      if ($liveT24 -match [regex]::Escape($name)) { continue }
      Log "RESTART_DEAD_T24_OWNER checkpoint=$name cutoff=$($cutoff.ToString('o'))"
      Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $Ops27 "run_t24h_cluster_capture.ps1"),
        "-Checkpoint", $name, "-TargetUtc", $cluster.wake_utc, "-CutoffUtc", $cluster.cutoff_utc,
        "-CohortContest", $cluster.cohort
      ) -WindowStyle Hidden | Out-Null
    }
  }

  $amT90Receipt = Join-Path $Ops27 "receipts\AM_T90M_20260905T2130Z\LATEST.json"
  $amT90C26 = Join-Path $Ops26 "CYCLE26_AM_6607349_T90M_FREEZE_RECEIPT.json"
  $amT90C26Art = Join-Path $Repo "artifacts\scientific_integrity\cycle26\CYCLE26_AM_6607349_T90M_FREEZE_RECEIPT.json"
  if (
    [DateTime]::UtcNow -lt $amT90Cutoff -and
    -not (Test-Path $amT90Receipt) -and
    -not (Test-Path $amT90C26) -and
    -not (Test-Path $amT90C26Art) -and
    $am90 -eq 0 -and
    $am90Fail -eq 0
  ) {
    Log "RESTART_DEAD_AM_T90_OWNER wake=$amT90Wake"
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
      "-NoProfile", "-File", (Join-Path $Ops26 "run_scheduled_am_t90m_capture.ps1"),
      "-TargetUtc", $amT90Wake
    ) -WindowStyle Hidden | Out-Null
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
      "-NoProfile", "-File", (Join-Path $Ops26 "run_am_t90m_failover.ps1")
    ) -WindowStyle Hidden | Out-Null
  }

  if (-not (Test-Path $amT90Receipt)) {
    $c26Ready = (Test-Path $amT90C26) -or (Test-Path $amT90C26Art)
    $amCapture = $false
    $pointer = Join-Path $Ops27 "LAST_CAPTURE_RUN.json"
    if (Test-Path $pointer) {
      $ptr = Get-Content $pointer -Raw | ConvertFrom-Json
      if ($ptr.phase -eq "T90M" -and "$($ptr.log)$($ptr.run_id)" -match "AM_T90M|6607349") { $amCapture = $true }
    }
    if ($c26Ready -or $amCapture) {
      $bindLog = Join-Path $Ops27 "CYCLE27_AM_T90M_BIND.log"
      Log "BIND_C27_AM_T90M"
      $env:PYTHONPATH = "$Repo\src;$Repo"
      python -B (Join-Path $Ops27 "bind_cycle27_checkpoint_receipt.py") --checkpoint AM_T90M_20260905T2130Z --phase T90M --run-id c27-am-t90m-watchdog --log (Join-Path $Ops26 "CYCLE26_CAPTURE_RUN_20260905T204500Z.log") --cutoff 2026-09-05T21:30:00Z --cohort-contest 6607349 *>> $bindLog
      if ($LASTEXITCODE -ne 0) { Log "BIND_C27_AM_T90M_FAILED exit=$LASTEXITCODE" }
    }
  }

  Start-Sleep -Seconds 300
}
Log "WATCHDOG_DONE"
