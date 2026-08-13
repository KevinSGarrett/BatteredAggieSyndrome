[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [string]$RuntimeRoot = 'C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3',
    [string]$ControllerTaskName = 'BAS-UnifiedAssistiveController',
    [string]$WatchdogTaskName = 'BAS-UnifiedAssistiveWatchdog',
    [string]$PythonExecutable = ''
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
    $activationJson = & $python -B $activator --runtime-root $RuntimeRoot --release-root $release
    if ($LASTEXITCODE -ne 0) { throw 'RELEASE_ACTIVATION_FAILED' }
    $activation = $activationJson | ConvertFrom-Json
    try {
        Stop-ScheduledTask -TaskName $ControllerTaskName -ErrorAction Stop
        Stop-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction Stop
        $deadline = (Get-Date).AddSeconds(45)
        foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
            while ((Get-ScheduledTask -TaskName $name -ErrorAction Stop).State -eq 'Running') {
                if ((Get-Date) -ge $deadline) { throw "SCHEDULED_TASK_STOP_TIMEOUT:$name" }
                Start-Sleep -Milliseconds 250
            }
        }
        Start-ScheduledTask -TaskName $ControllerTaskName
        Start-ScheduledTask -TaskName $WatchdogTaskName
    } catch {
        if ($previousPointer) {
            $rollback = Join-Path (Split-Path -Parent $pointerPath) ('.current-release-' + [guid]::NewGuid().ToString('N') + '.tmp')
            [System.IO.File]::WriteAllBytes($rollback, $previousPointer)
            [System.IO.File]::Replace($rollback, $pointerPath, $null)
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
    } | ConvertTo-Json -Compress
}
