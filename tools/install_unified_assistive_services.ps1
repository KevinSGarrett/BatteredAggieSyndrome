[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [string]$RuntimeRoot = 'C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3',
    [string]$ControllerTaskName = 'BAS-UnifiedAssistiveController',
    [string]$WatchdogTaskName = 'BAS-UnifiedAssistiveWatchdog',
    [string]$PythonExecutable = '',
    [ValidateSet('LocalService', 'InteractiveUser')][string]$PrincipalMode = 'LocalService',
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
$expectedReleaseFiles = @('RELEASE_MANIFEST.json') + @(
    $manifest.files.PSObject.Properties | ForEach-Object { [string]$_.Name }
)
$releasePrefix = $release.TrimEnd('\') + '\'
$actualReleaseFiles = @(
    Get-ChildItem -LiteralPath $release -Recurse -File | ForEach-Object {
        $_.FullName.Substring($releasePrefix.Length).Replace('\', '/')
    }
)
$releaseFileDifference = @(Compare-Object -ReferenceObject $expectedReleaseFiles -DifferenceObject $actualReleaseFiles)
if ($releaseFileDifference.Count -ne 0) { throw 'RELEASE_FILE_SET_MISMATCH' }

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $PythonExecutable = (Get-Command python -ErrorAction Stop).Source
}
$python = (Resolve-Path -LiteralPath $PythonExecutable).Path
$version = & $python -c 'import sys; print(sys.version_info.major, sys.version_info.minor)'
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^3 (11|12|13)$') { throw 'PYTHON_VERSION_NOT_SUPPORTED' }

$controllerScript = Join-Path $release 'tools\run_unified_assistive_controller.py'
$watchdogScript = Join-Path $release 'tools\run_unified_assistive_watchdog.py'
$releaseLauncher = Join-Path $release 'tools\launch_unified_assistive_service.py'
$releaseActivator = Join-Path $release 'tools\activate_unified_assistive_release.py'
$stableLauncherRoot = Join-Path $RuntimeRoot 'launcher'
$stableLauncher = Join-Path $stableLauncherRoot 'launch_unified_assistive_service.py'
$backupRoot = Join-Path $RuntimeRoot ('backups\task-definitions\' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))
$existingTasks = @{}
foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
    $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($existing -and -not $Replace) { throw "SCHEDULED_TASK_EXISTS:$name" }
    $existingTasks[$name] = $existing
}

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
if ($identity.IsSystem) { throw 'CONTROLLER_SERVICE_SYSTEM_IDENTITY_FORBIDDEN' }
if ($PrincipalMode -eq 'LocalService') {
    $principalName = 'NT AUTHORITY\LOCAL SERVICE'
    $principal = New-ScheduledTaskPrincipal -UserId $principalName -LogonType ServiceAccount -RunLevel Limited
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $logonType = 'ServiceAccount'
    $triggerType = 'BootTrigger'
} else {
    $principalName = $identity.Name
    $principal = New-ScheduledTaskPrincipal -UserId $principalName -LogonType Interactive -RunLevel Limited
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $principalName
    $logonType = 'Interactive'
    $triggerType = 'LogonTrigger'
}
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$controllerArguments = '-B "' + $stableLauncher + '" --role controller --runtime-root "' + $RuntimeRoot + '"'
$watchdogArguments = '-B "' + $stableLauncher + '" --role watchdog --runtime-root "' + $RuntimeRoot + '"'
$controllerAction = New-ScheduledTaskAction -Execute $python -Argument $controllerArguments -WorkingDirectory $stableLauncherRoot
$watchdogAction = New-ScheduledTaskAction -Execute $python -Argument $watchdogArguments -WorkingDirectory $stableLauncherRoot
$replacementRecovery = $null
$replacementRecoveryDisposition = 'NOT_APPLICABLE'
$installedLauncherHash = $null
$activation = $null
if ($Replace -and $existingTasks[$ControllerTaskName]) {
    $existingControllerAction = $existingTasks[$ControllerTaskName].Actions | Select-Object -First 1
    if (-not $existingControllerAction) { throw 'CONTROLLER_RECOVERY_ACTION_MISSING' }
    $existingArguments = [string]$existingControllerAction.Arguments
    $existingWorkingDirectory = [System.IO.Path]::GetFullPath([string]$existingControllerAction.WorkingDirectory)
    if ([System.IO.Path]::GetFullPath([string]$existingControllerAction.Execute) -ne $python) { throw 'CONTROLLER_RECOVERY_ACTION_EXECUTABLE_MISMATCH' }
    if ($existingArguments -match '^(?:-B\s+)?"([^"\r\n]*\\run_unified_assistive_controller\.py)"\s+serve(?:\s|$)') {
        $existingControllerScriptPath = [System.IO.Path]::GetFullPath($Matches[1])
        $expectedExistingControllerScriptPath = [System.IO.Path]::GetFullPath((Join-Path $existingWorkingDirectory 'tools\run_unified_assistive_controller.py'))
        if ($existingControllerScriptPath -ne $expectedExistingControllerScriptPath) { throw 'CONTROLLER_RECOVERY_ACTION_PATH_MISMATCH' }
        if ($existingArguments -notmatch '--build-commit\s+([0-9a-f]{40})') { throw 'CONTROLLER_RECOVERY_ACTION_BUILD_MISSING' }
        $actionBuildCommit = $Matches[1]
        if ((Split-Path -Leaf $existingWorkingDirectory) -ne $actionBuildCommit) { throw 'CONTROLLER_RECOVERY_ACTION_DIRECTORY_BUILD_MISMATCH' }
    } elseif ($existingArguments -match '^(?:-B\s+)?"([^"\r\n]*\\launch_unified_assistive_service\.py)"\s+--role\s+controller(?:\s|$)') {
        $existingLauncherPath = [System.IO.Path]::GetFullPath($Matches[1])
        if ($existingLauncherPath -ne [System.IO.Path]::GetFullPath($stableLauncher)) { throw 'CONTROLLER_RECOVERY_ACTION_PATH_MISMATCH' }
        $pointerPath = Join-Path $RuntimeRoot 'deployment\current-release.json'
        if (-not (Test-Path -LiteralPath $pointerPath -PathType Leaf)) { throw 'CONTROLLER_RECOVERY_POINTER_MISSING' }
        $pointer = Get-Content -LiteralPath $pointerPath -Raw | ConvertFrom-Json
        $actionBuildCommit = [string]$pointer.build_commit
        if ($actionBuildCommit -notmatch '^[0-9a-f]{40}$') { throw 'CONTROLLER_RECOVERY_ACTION_BUILD_MISSING' }
        $existingControllerScriptPath = Join-Path $RuntimeRoot ('releases\' + $actionBuildCommit + '\tools\run_unified_assistive_controller.py')
    } else {
        throw 'CONTROLLER_RECOVERY_ACTION_IDENTITY_MISMATCH'
    }
    $statusJson = & $python -B $controllerScript status --runtime-root "$RuntimeRoot"
    if ($LASTEXITCODE -ne 0) { throw 'CONTROLLER_RECOVERY_STATUS_FAILED' }
    $status = $statusJson | ConvertFrom-Json
    $existingTaskState = [string]$existingTasks[$ControllerTaskName].State
    if (-not $status.leader) {
        if ($existingTaskState -eq 'Running') { throw 'CONTROLLER_RECOVERY_LEASE_MISSING_WHILE_TASK_RUNNING' }
        $replacementRecoveryDisposition = 'CLEAN_SHUTDOWN_NO_LEASE'
    } else {
        $leaderOwnerId = [string]$status.leader.owner_id
        $leaderBuildCommit = [string]$status.leader.build_commit
        if ($leaderBuildCommit -ne $actionBuildCommit) { throw 'CONTROLLER_RECOVERY_BUILD_BINDING_MISMATCH' }
        if ($leaderOwnerId -notmatch '^[^:]+:([1-9][0-9]*):[0-9a-fA-F]{32}$') { throw 'CONTROLLER_RECOVERY_OWNER_FORMAT_INVALID' }
        [int]$ownerPid = $Matches[1]
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
}

$WhatIfPreference = $requestedWhatIf
$installController = $PSCmdlet.ShouldProcess($ControllerTaskName, 'Register limited controller scheduled task')
$installWatchdog = $PSCmdlet.ShouldProcess($WatchdogTaskName, 'Register independent limited watchdog scheduled task')
if (($installController -or $installWatchdog) -and $PrincipalMode -eq 'LocalService') {
    $windowsPrincipal = [System.Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $windowsPrincipal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'CONTROLLER_LOCAL_SERVICE_ELEVATION_REQUIRED_BEFORE_MUTATION'
    }
}
if ($installController -or $installWatchdog) {
    $WhatIfPreference = $false
    $null = New-Item -ItemType Directory -Path $backupRoot -Force
    if ($PrincipalMode -eq 'LocalService') {
        $assistiveRoot = Split-Path -Parent $RuntimeRoot
        $dataRoot = Split-Path -Parent $assistiveRoot
        $inventoryRoot = Join-Path $assistiveRoot 'inventory'
        $cpuWorkerRoot = Join-Path $assistiveRoot 'cpu_worker'
        $providerWorkRoot = Join-Path $assistiveRoot 'provider_work'
        $openrouterRoot = Join-Path $assistiveRoot 'openrouter'
        $cursorRoot = Join-Path $assistiveRoot 'cursor'
        $localQwenRoot = Join-Path $assistiveRoot 'local_qwen'
        $openaiRoot = Join-Path $dataRoot 'openai'
        $authoritativeEnvPath = 'C:\BatteredAggieSyndrome\.env'
        $signingKeyPath = Join-Path $cpuWorkerRoot 'controller\secrets\worker-v2.bin'
        $readContainers = @(
            (Split-Path -Parent $python),
            (Join-Path $RuntimeRoot 'releases'),
            $stableLauncherRoot,
            (Join-Path $RuntimeRoot 'deployment'),
            (Join-Path $dataRoot 'manifests'),
            $providerWorkRoot,
            $openrouterRoot,
            $cursorRoot,
            $localQwenRoot,
            $cpuWorkerRoot
        )
        $writeContainers = @(
            (Join-Path $RuntimeRoot 'state'),
            (Join-Path $RuntimeRoot 'runtime'),
            (Join-Path $RuntimeRoot 'evidence'),
            (Join-Path $RuntimeRoot 'watchdog'),
            (Join-Path $RuntimeRoot 'packets'),
            (Join-Path $inventoryRoot 'current'),
            (Join-Path $inventoryRoot 'runtime'),
            (Join-Path $cpuWorkerRoot 'results'),
            $openaiRoot
        )
        foreach ($path in $readContainers + $writeContainers) {
            if (-not (Test-Path -LiteralPath $path -PathType Container)) {
                $null = New-Item -ItemType Directory -Path $path -Force
            }
        }
        if (-not (Test-Path -LiteralPath $signingKeyPath -PathType Leaf)) {
            throw 'CONTROLLER_LOCAL_SERVICE_SIGNING_KEY_MISSING'
        }
        if (-not (Test-Path -LiteralPath $authoritativeEnvPath -PathType Leaf)) {
            throw 'CONTROLLER_LOCAL_SERVICE_AUTHORITATIVE_ENV_MISSING'
        }
        foreach ($path in $readContainers) {
            & icacls.exe $path /grant '*S-1-5-19:(OI)(CI)RX' | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "CONTROLLER_LOCAL_SERVICE_READ_ACL_FAILED:$path" }
        }
        foreach ($path in $writeContainers) {
            & icacls.exe $path /grant '*S-1-5-19:(OI)(CI)M' | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "CONTROLLER_LOCAL_SERVICE_WRITE_ACL_FAILED:$path" }
        }
        & icacls.exe $signingKeyPath /grant '*S-1-5-19:R' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'CONTROLLER_LOCAL_SERVICE_KEY_ACL_FAILED' }
        & icacls.exe $authoritativeEnvPath /grant '*S-1-5-19:R' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'CONTROLLER_LOCAL_SERVICE_ENV_ACL_FAILED' }
    }
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
        $postStopStatusJson = & $python -B $controllerScript status --runtime-root "$RuntimeRoot"
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
            $recoverResult = & $python -B $controllerScript recover-orphaned-lease `
                --runtime-root "$RuntimeRoot" `
                --expected-owner-id "$($replacementRecovery.owner_id)" `
                --expected-build-commit "$($replacementRecovery.build_commit)" `
                --expected-owner-pid "$($replacementRecovery.owner_pid)" `
                --recovery-evidence-sha256 "$($replacementRecovery.evidence_sha256)"
            if ($LASTEXITCODE -ne 0) { throw 'CONTROLLER_RECOVERY_RELEASE_FAILED' }
            $replacementRecoveryDisposition = 'EXACT_ORPHAN_LEASE_RELEASED'
        }
    }
    $null = New-Item -ItemType Directory -Path $stableLauncherRoot -Force
    Copy-Item -LiteralPath $releaseLauncher -Destination $stableLauncher -Force
    $installedLauncherHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $stableLauncher).Hash.ToLowerInvariant()
    $expectedLauncherHash = [string]$manifest.files.'tools/launch_unified_assistive_service.py'.sha256
    if ($installedLauncherHash -ne $expectedLauncherHash) { throw 'STABLE_LAUNCHER_INSTALL_HASH_MISMATCH' }
    & icacls.exe $stableLauncher /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' '*S-1-5-19:RX' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'STABLE_LAUNCHER_ACL_FAILED' }
    $activationJson = & $python -B $releaseActivator --runtime-root "$RuntimeRoot" --release-root "$release"
    if ($LASTEXITCODE -ne 0) { throw 'RELEASE_ACTIVATION_FAILED' }
    $activation = $activationJson | ConvertFrom-Json
}
if ($installController) {
    Register-ScheduledTask -TaskName $ControllerTaskName -Action $controllerAction -Trigger $trigger -Settings $settings -Principal $principal -Description 'Aggie Analytics unified assistive controller stable launcher' -Force | Out-Null
}
if ($installWatchdog) {
    Register-ScheduledTask -TaskName $WatchdogTaskName -Action $watchdogAction -Trigger $trigger -Settings $settings -Principal $principal -Description 'Aggie Analytics independent read-only watchdog stable launcher' -Force | Out-Null
}

if ($installController -and $installWatchdog) {
    Start-ScheduledTask -TaskName $ControllerTaskName
    Start-ScheduledTask -TaskName $WatchdogTaskName
}
[pscustomobject]@{
    result = if ($requestedWhatIf) { 'WHATIF_PASS' } else { 'PASS' }
    release = $release
    build_commit = $manifest.build_commit
    principal = $principalName
    run_level = 'Limited'
    logon_type = $logonType
    trigger_type = $triggerType
    allow_start_if_on_batteries = $true
    stop_if_going_on_batteries = $false
    controller_task = $ControllerTaskName
    watchdog_task = $WatchdogTaskName
    replacement_recovery = $replacementRecoveryDisposition
    stable_launcher = $stableLauncher
    stable_launcher_sha256 = $installedLauncherHash
    release_pointer_sha256 = $activation.pointer_sha256
    future_release_switch_elevation_required = $false
    cold_boot_without_user_logon = if ($PrincipalMode -eq 'LocalService') { 'STARTUP_CAPABLE_CONFIGURATION_BOOT_OBSERVATION_PENDING' } else { 'NOT_YET_PROVEN' }
    operational_completion = 'INCOMPLETE'
} | ConvertTo-Json -Compress
