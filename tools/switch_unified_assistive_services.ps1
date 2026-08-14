[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [string]$RuntimeRoot = 'C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3',
    [string]$ControllerTaskName = 'BAS-UnifiedAssistiveController',
    [string]$WatchdogTaskName = 'BAS-UnifiedAssistiveWatchdog',
    [string]$PythonExecutable = '',
    [ValidateRange(45, 300)][int]$GracefulStopTimeoutSeconds = 90,
    [ValidateRange(5, 60)][int]$AcknowledgementVisibilityTimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $PythonExecutable = (Get-Command python -ErrorAction Stop).Source
}
$python = (Resolve-Path -LiteralPath $PythonExecutable).Path
$release = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$activator = Join-Path $release 'tools\activate_unified_assistive_release.py'
$launcher = Join-Path $RuntimeRoot 'launcher\launch_unified_assistive_service.py'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw 'STABLE_LAUNCHER_NOT_INSTALLED' }
foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction Stop
    $action = $task.Actions | Select-Object -First 1
    if (-not $action -or [System.IO.Path]::GetFullPath([string]$action.Execute) -ne $python) {
        throw "STABLE_TASK_EXECUTABLE_MISMATCH:$name"
    }
    if ([string]$action.Arguments -notmatch [regex]::Escape($launcher)) {
        throw "STABLE_TASK_LAUNCHER_MISMATCH:$name"
    }
}
if ($PSCmdlet.ShouldProcess($release, 'Activate verified release and restart existing limited tasks')) {
    $pointerPath = Join-Path $RuntimeRoot 'deployment\current-release.json'
    $previousPointer = if (Test-Path -LiteralPath $pointerPath -PathType Leaf) {
        [System.IO.File]::ReadAllBytes($pointerPath)
    } else {
        $null
    }
    $currentPointer = Get-Content -LiteralPath $pointerPath -Raw | ConvertFrom-Json
    $currentBuild = [string]$currentPointer.build_commit
    if ($currentBuild -notmatch '^[0-9a-f]{40}$') { throw 'CURRENT_RELEASE_POINTER_BUILD_INVALID' }
    $controlRoot = Join-Path $RuntimeRoot 'control'
    $acknowledgements = @{}
    foreach ($role in @('controller', 'watchdog')) {
        $request = [ordered]@{
            artifact_type = 'UNIFIED_ASSISTIVE_SERVICE_STOP_REQUEST'
            build_commit = $currentBuild
            request_id = [guid]::NewGuid().ToString('N')
            requested_at = (Get-Date).ToUniversalTime().ToString('o').Replace('+00:00', 'Z')
            role = $role
            schema_version = 1
        }
        $requestJson = ($request | ConvertTo-Json -Compress) + "`n"
        $requestBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($requestJson)
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $requestHash = ([System.BitConverter]::ToString($sha.ComputeHash($requestBytes))).Replace('-', '').ToLowerInvariant()
        } finally {
            $sha.Dispose()
        }
        $requestPath = Join-Path $controlRoot ($role + '-stop.json')
        $temporaryRequest = Join-Path $controlRoot ('.' + $role + '-stop-' + [guid]::NewGuid().ToString('N') + '.tmp')
        $null = New-Item -ItemType Directory -Path $controlRoot -Force
        [System.IO.File]::WriteAllBytes($temporaryRequest, $requestBytes)
        Move-Item -LiteralPath $temporaryRequest -Destination $requestPath -Force
        $acknowledgements[$role] = Join-Path $controlRoot ('acknowledged\' + $role + '\sha256\' + $requestHash + '\request.json')
    }
    try {
        # A controller may be finishing a bounded provider poll when it receives
        # the stop request.  Keep the stop cooperative and non-elevated, but allow
        # one complete bounded poll plus Task Scheduler state propagation before
        # treating it as a failed switch.
        $deadline = (Get-Date).AddSeconds($GracefulStopTimeoutSeconds)
        foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
            while ((Get-ScheduledTask -TaskName $name -ErrorAction Stop).State -eq 'Running') {
                if ((Get-Date) -ge $deadline) { throw "GRACEFUL_SERVICE_STOP_TIMEOUT:$name" }
                Start-Sleep -Milliseconds 250
            }
        }
        $acknowledgementDeadline = (Get-Date).AddSeconds($AcknowledgementVisibilityTimeoutSeconds)
        foreach ($role in @('controller', 'watchdog')) {
            # Task Scheduler can publish the terminal task state a few seconds
            # before the service's atomic acknowledgement rename is visible.
            # The controller still has the original bounded stop deadline. Once
            # both tasks are terminal, allow only this separate bounded
            # filesystem-visibility grace so a successful cooperative stop is
            # not misclassified after the process already exited.
            while (-not (Test-Path -LiteralPath $acknowledgements[$role] -PathType Leaf)) {
                if ((Get-Date) -ge $acknowledgementDeadline) {
                    throw "SERVICE_STOP_ACKNOWLEDGEMENT_MISSING:$role"
                }
                Start-Sleep -Milliseconds 250
            }
        }
        $statusJson = & $python -B (Join-Path $release 'tools\run_unified_assistive_controller.py') status --runtime-root $RuntimeRoot
        if ($LASTEXITCODE -ne 0) { throw 'POST_STOP_CONTROLLER_STATUS_FAILED' }
        if (($statusJson | ConvertFrom-Json).leader) { throw 'POST_STOP_CONTROLLER_LEADER_REMAINS' }
        $activationJson = & $python -B $activator --runtime-root $RuntimeRoot --release-root $release
        if ($LASTEXITCODE -ne 0) { throw 'RELEASE_ACTIVATION_FAILED' }
        $activation = $activationJson | ConvertFrom-Json
        Start-ScheduledTask -TaskName $ControllerTaskName
        Start-ScheduledTask -TaskName $WatchdogTaskName
        $deadline = (Get-Date).AddSeconds(30)
        foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
            while ((Get-ScheduledTask -TaskName $name -ErrorAction Stop).State -ne 'Running') {
                if ((Get-Date) -ge $deadline) { throw "SCHEDULED_TASK_START_TIMEOUT:$name" }
                Start-Sleep -Milliseconds 250
            }
        }
    } catch {
        if ($previousPointer) {
            $rollback = Join-Path (Split-Path -Parent $pointerPath) ('.current-release-' + [guid]::NewGuid().ToString('N') + '.tmp')
            $failedPointerBackup = Join-Path (Split-Path -Parent $pointerPath) ('failed-current-release-' + [guid]::NewGuid().ToString('N') + '.json')
            [System.IO.File]::WriteAllBytes($rollback, $previousPointer)
            [System.IO.File]::Replace($rollback, $pointerPath, $failedPointerBackup)
            $restoredPointer = [System.IO.File]::ReadAllBytes($pointerPath)
            if (
                [System.Convert]::ToBase64String($restoredPointer) -ne
                [System.Convert]::ToBase64String($previousPointer)
            ) {
                throw 'RELEASE_POINTER_ROLLBACK_VERIFICATION_FAILED'
            }
        }
        Start-ScheduledTask -TaskName $ControllerTaskName -ErrorAction SilentlyContinue
        Start-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
        throw
    }
    [pscustomobject]@{
        result = 'PASS'
        build_commit = $activation.build_commit
        pointer_sha256 = $activation.pointer_sha256
        controller_task = $ControllerTaskName
        watchdog_task = $WatchdogTaskName
        elevation_required = $false
        task_registration_performed = $false
        rollback_available = [bool]$previousPointer
        graceful_stop_acknowledged = $true
    } | ConvertTo-Json -Compress
}
