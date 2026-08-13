[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [string]$RuntimeRoot = 'C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3',
    [string]$ControllerTaskName = 'BAS-UnifiedAssistiveController',
    [string]$WatchdogTaskName = 'BAS-UnifiedAssistiveWatchdog',
    [string]$PythonExecutable = '',
    [switch]$Replace
)

$ErrorActionPreference = 'Stop'
$requestedWhatIf = [bool]$WhatIfPreference
# PowerShell propagates -WhatIf to read-only cmdlets such as Get-FileHash and
# Get-ScheduledTask. Suppress that propagation during preflight; mutations
# remain exclusively behind ShouldProcess below.
$WhatIfPreference = $false
$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$manifestPath = Join-Path $release 'RELEASE_MANIFEST.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'RELEASE_MANIFEST_MISSING' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ((Split-Path -Leaf $release) -ne $manifest.build_commit) { throw 'RELEASE_DIRECTORY_COMMIT_MISMATCH' }
foreach ($property in $manifest.files.PSObject.Properties) {
    $candidate = Join-Path $release ($property.Name.Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { throw "RELEASE_FILE_MISSING:$($property.Name)" }
    $observed = (Get-FileHash -Algorithm SHA256 -LiteralPath $candidate).Hash.ToLowerInvariant()
    if ($observed -ne $property.Value.sha256) { throw "RELEASE_FILE_HASH_MISMATCH:$($property.Name)" }
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $PythonExecutable = (Get-Command python -ErrorAction Stop).Source
}
$python = (Resolve-Path -LiteralPath $PythonExecutable).Path
$version = & $python -c 'import sys; print(sys.version_info.major, sys.version_info.minor)'
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^3 (11|12|13)$') { throw 'PYTHON_VERSION_NOT_SUPPORTED' }

$controllerScript = Join-Path $release 'tools\run_unified_assistive_controller.py'
$watchdogScript = Join-Path $release 'tools\run_unified_assistive_watchdog.py'
$backupRoot = Join-Path $RuntimeRoot ('backups\task-definitions\' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))
$existingTasks = @{}
foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
    $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($existing -and -not $Replace) { throw "SCHEDULED_TASK_EXISTS:$name" }
    $existingTasks[$name] = $existing
}

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
if ($identity.IsSystem) { throw 'CONTROLLER_SERVICE_SYSTEM_IDENTITY_FORBIDDEN' }
$principal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Limited
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
$controllerArguments = '"' + $controllerScript + '" serve --runtime-root "' + $RuntimeRoot + '" --build-commit ' + $manifest.build_commit
$watchdogArguments = '"' + $watchdogScript + '" serve --runtime-root "' + $RuntimeRoot + '" --build-commit ' + $manifest.build_commit
$controllerAction = New-ScheduledTaskAction -Execute $python -Argument $controllerArguments -WorkingDirectory $release
$watchdogAction = New-ScheduledTaskAction -Execute $python -Argument $watchdogArguments -WorkingDirectory $release
$replacementRecovery = $null
$replacementRecoveryDisposition = 'NOT_APPLICABLE'
if ($Replace -and $existingTasks[$ControllerTaskName]) {
    $existingControllerAction = $existingTasks[$ControllerTaskName].Actions | Select-Object -First 1
    if (-not $existingControllerAction) { throw 'CONTROLLER_RECOVERY_ACTION_MISSING' }
    $existingArguments = [string]$existingControllerAction.Arguments
    if ($existingArguments -notmatch '^"([^"\r\n]*\\run_unified_assistive_controller\.py)"\s+serve(?:\s|$)') { throw 'CONTROLLER_RECOVERY_ACTION_IDENTITY_MISMATCH' }
    $existingControllerScriptPath = [System.IO.Path]::GetFullPath($Matches[1])
    $existingWorkingDirectory = [System.IO.Path]::GetFullPath([string]$existingControllerAction.WorkingDirectory)
    $expectedExistingControllerScriptPath = [System.IO.Path]::GetFullPath((Join-Path $existingWorkingDirectory 'tools\run_unified_assistive_controller.py'))
    if ($existingControllerScriptPath -ne $expectedExistingControllerScriptPath) { throw 'CONTROLLER_RECOVERY_ACTION_PATH_MISMATCH' }
    if ([System.IO.Path]::GetFullPath([string]$existingControllerAction.Execute) -ne $python) { throw 'CONTROLLER_RECOVERY_ACTION_EXECUTABLE_MISMATCH' }
    if ($existingArguments -notmatch '--build-commit\s+([0-9a-f]{40})') { throw 'CONTROLLER_RECOVERY_ACTION_BUILD_MISSING' }
    $actionBuildCommit = $Matches[1]
    if ((Split-Path -Leaf $existingWorkingDirectory) -ne $actionBuildCommit) { throw 'CONTROLLER_RECOVERY_ACTION_DIRECTORY_BUILD_MISMATCH' }
    $statusJson = & $python $controllerScript status --runtime-root "$RuntimeRoot"
    if ($LASTEXITCODE -ne 0) { throw 'CONTROLLER_RECOVERY_STATUS_FAILED' }
    $status = $statusJson | ConvertFrom-Json
    if (-not $status.leader) { throw 'CONTROLLER_RECOVERY_LEASE_MISSING' }
    $leaderOwnerId = [string]$status.leader.owner_id
    $leaderBuildCommit = [string]$status.leader.build_commit
    if ($leaderBuildCommit -ne $actionBuildCommit) { throw 'CONTROLLER_RECOVERY_BUILD_BINDING_MISMATCH' }
    if ($leaderOwnerId -notmatch '^[^:]+:([1-9][0-9]*):[0-9a-fA-F]{32}$') { throw 'CONTROLLER_RECOVERY_OWNER_FORMAT_INVALID' }
    [int]$ownerPid = $Matches[1]
    $existingTaskState = [string]$existingTasks[$ControllerTaskName].State
    $ownerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $ownerPid" -ErrorAction SilentlyContinue
    $ownerCommandLine = $null
    if ($ownerProcess) {
        $ownerCommandLine = [string]$ownerProcess.CommandLine
        if ([string]::IsNullOrWhiteSpace($ownerCommandLine)) { throw 'CONTROLLER_RECOVERY_OWNER_COMMANDLINE_MISSING' }
        if ($ownerCommandLine -notmatch 'run_unified_assistive_controller\.py') { throw 'CONTROLLER_RECOVERY_OWNER_COMMAND_IDENTITY_MISMATCH' }
        if ($ownerCommandLine -notmatch ('--build-commit\s+' + [regex]::Escape($leaderBuildCommit))) { throw 'CONTROLLER_RECOVERY_OWNER_BUILD_MISMATCH' }
    } elseif ($existingTaskState -eq 'Running') {
        throw 'CONTROLLER_RECOVERY_OWNER_PROCESS_MISSING_WHILE_TASK_RUNNING'
    }
    $replacementRecoveryEvidence = [ordered]@{
        task_name = $ControllerTaskName
        action_execute = [string]$existingControllerAction.Execute
        action_arguments = $existingArguments
        action_working_directory = $existingWorkingDirectory
        action_controller_script = $existingControllerScriptPath
        owner_id = $leaderOwnerId
        owner_pid = $ownerPid
        owner_commandline = $ownerCommandLine
        owner_process_present = [bool]$ownerProcess
        task_state = $existingTaskState
        build_commit = $leaderBuildCommit
        action_build_commit = $actionBuildCommit
        observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    }
    $replacementRecoveryEvidenceJson = $replacementRecoveryEvidence | ConvertTo-Json -Depth 16 -Compress
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($replacementRecoveryEvidenceJson)
        $hashBytes = $sha256.ComputeHash($bytes)
        $replacementRecoveryEvidenceSha256 = ([System.BitConverter]::ToString($hashBytes)).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
    $replacementRecovery = [ordered]@{
        owner_id = $leaderOwnerId
        owner_pid = $ownerPid
        build_commit = $leaderBuildCommit
        evidence_sha256 = $replacementRecoveryEvidenceSha256
        evidence_json = $replacementRecoveryEvidenceJson
    }
}

$WhatIfPreference = $requestedWhatIf
$installController = $PSCmdlet.ShouldProcess($ControllerTaskName, 'Register limited controller scheduled task')
$installWatchdog = $PSCmdlet.ShouldProcess($WatchdogTaskName, 'Register independent limited watchdog scheduled task')
if ($installController -or $installWatchdog) {
    $WhatIfPreference = $false
    $null = New-Item -ItemType Directory -Path $backupRoot -Force
    foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
        if ($existingTasks[$name]) {
            Export-ScheduledTask -TaskName $name | Set-Content -LiteralPath (Join-Path $backupRoot "$name.xml") -Encoding UTF8
            Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
            $deadline = (Get-Date).AddSeconds(30)
            while ((Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue).State -eq 'Running') {
                if ((Get-Date) -ge $deadline) { throw "SCHEDULED_TASK_STOP_TIMEOUT:$name" }
                Start-Sleep -Milliseconds 250
            }
        }
    }
    if ($replacementRecovery) {
        $controllerState = Get-ScheduledTask -TaskName $ControllerTaskName -ErrorAction SilentlyContinue
        if ($controllerState -and $controllerState.State -eq 'Running') { throw "SCHEDULED_TASK_STOP_TIMEOUT:$ControllerTaskName" }
        if (Get-Process -Id $replacementRecovery.owner_pid -ErrorAction SilentlyContinue) { throw 'CONTROLLER_RECOVERY_OWNER_PROCESS_STILL_LIVE' }
        $postStopStatusJson = & $python $controllerScript status --runtime-root "$RuntimeRoot"
        if ($LASTEXITCODE -ne 0) { throw 'CONTROLLER_RECOVERY_POST_STOP_STATUS_FAILED' }
        $postStopStatus = $postStopStatusJson | ConvertFrom-Json
        if (-not $postStopStatus.leader) {
            $replacementRecoveryDisposition = 'CLEAN_SHUTDOWN_RELEASED_LEASE'
        } else {
            if (
                [string]$postStopStatus.leader.owner_id -ne $replacementRecovery.owner_id -or
                [string]$postStopStatus.leader.build_commit -ne $replacementRecovery.build_commit
            ) { throw 'CONTROLLER_RECOVERY_POST_STOP_LEASE_MISMATCH' }
            $evidenceDirectory = Join-Path $RuntimeRoot ('service-state\recovery-evidence\sha256\' + $replacementRecovery.evidence_sha256)
            $evidencePath = Join-Path $evidenceDirectory 'report.json'
            $null = New-Item -ItemType Directory -Path $evidenceDirectory -Force
            if (Test-Path -LiteralPath $evidencePath -PathType Leaf) {
                $existingEvidenceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $evidencePath).Hash.ToLowerInvariant()
                if ($existingEvidenceHash -ne $replacementRecovery.evidence_sha256) { throw 'CONTROLLER_RECOVERY_EVIDENCE_COLLISION' }
            } else {
                $temporaryEvidencePath = Join-Path $evidenceDirectory ('.report-' + [guid]::NewGuid().ToString('N') + '.tmp')
                [System.IO.File]::WriteAllText(
                    $temporaryEvidencePath,
                    [string]$replacementRecovery.evidence_json,
                    [System.Text.UTF8Encoding]::new($false)
                )
                $writtenEvidenceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $temporaryEvidencePath).Hash.ToLowerInvariant()
                if ($writtenEvidenceHash -ne $replacementRecovery.evidence_sha256) {
                    Remove-Item -LiteralPath $temporaryEvidencePath -Force
                    throw 'CONTROLLER_RECOVERY_EVIDENCE_HASH_MISMATCH'
                }
                Move-Item -LiteralPath $temporaryEvidencePath -Destination $evidencePath
            }
            $recoverResult = & $python $controllerScript recover-orphaned-lease `
                --runtime-root "$RuntimeRoot" `
                --expected-owner-id "$($replacementRecovery.owner_id)" `
                --expected-build-commit "$($replacementRecovery.build_commit)" `
                --expected-owner-pid "$($replacementRecovery.owner_pid)" `
                --recovery-evidence-sha256 "$($replacementRecovery.evidence_sha256)"
            if ($LASTEXITCODE -ne 0) { throw 'CONTROLLER_RECOVERY_RELEASE_FAILED' }
            $replacementRecoveryDisposition = 'EXACT_ORPHAN_LEASE_RELEASED'
        }
    }
}
if ($installController) {
    Register-ScheduledTask -TaskName $ControllerTaskName -Action $controllerAction -Trigger $trigger -Settings $settings -Principal $principal -Description "Aggie Analytics unified assistive controller $($manifest.build_commit)" -Force | Out-Null
}
if ($installWatchdog) {
    Register-ScheduledTask -TaskName $WatchdogTaskName -Action $watchdogAction -Trigger $trigger -Settings $settings -Principal $principal -Description "Aggie Analytics independent read-only watchdog $($manifest.build_commit)" -Force | Out-Null
}

if ($installController -and $installWatchdog) {
    Start-ScheduledTask -TaskName $ControllerTaskName
    Start-ScheduledTask -TaskName $WatchdogTaskName
}
[pscustomobject]@{
    result = if ($requestedWhatIf) { 'WHATIF_PASS' } else { 'PASS' }
    release = $release
    build_commit = $manifest.build_commit
    principal = $identity.Name
    run_level = 'Limited'
    logon_type = 'Interactive'
    controller_task = $ControllerTaskName
    watchdog_task = $WatchdogTaskName
    replacement_recovery = $replacementRecoveryDisposition
    cold_boot_without_user_logon = 'NOT_YET_PROVEN'
    operational_completion = 'INCOMPLETE'
} | ConvertTo-Json -Compress
