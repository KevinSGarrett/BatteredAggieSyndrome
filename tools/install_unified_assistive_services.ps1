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
$null = New-Item -ItemType Directory -Path $backupRoot -Force
foreach ($name in @($ControllerTaskName, $WatchdogTaskName)) {
    $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($existing -and -not $Replace) { throw "SCHEDULED_TASK_EXISTS:$name" }
    if ($existing) {
        Export-ScheduledTask -TaskName $name | Set-Content -LiteralPath (Join-Path $backupRoot "$name.xml") -Encoding UTF8
        Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        $deadline = (Get-Date).AddSeconds(30)
        while ((Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue).State -eq 'Running') {
            if ((Get-Date) -ge $deadline) { throw "SCHEDULED_TASK_STOP_TIMEOUT:$name" }
            Start-Sleep -Milliseconds 250
        }
    }
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

if ($PSCmdlet.ShouldProcess($ControllerTaskName, 'Register limited controller scheduled task')) {
    Register-ScheduledTask -TaskName $ControllerTaskName -Action $controllerAction -Trigger $trigger -Settings $settings -Principal $principal -Description "Aggie Analytics unified assistive controller $($manifest.build_commit)" -Force | Out-Null
}
if ($PSCmdlet.ShouldProcess($WatchdogTaskName, 'Register independent limited watchdog scheduled task')) {
    Register-ScheduledTask -TaskName $WatchdogTaskName -Action $watchdogAction -Trigger $trigger -Settings $settings -Principal $principal -Description "Aggie Analytics independent read-only watchdog $($manifest.build_commit)" -Force | Out-Null
}

if (-not $WhatIfPreference) {
    Start-ScheduledTask -TaskName $ControllerTaskName
    Start-ScheduledTask -TaskName $WatchdogTaskName
}
[pscustomobject]@{
    result = if ($WhatIfPreference) { 'WHATIF_PASS' } else { 'PASS' }
    release = $release
    build_commit = $manifest.build_commit
    principal = $identity.Name
    run_level = 'Limited'
    logon_type = 'Interactive'
    controller_task = $ControllerTaskName
    watchdog_task = $WatchdogTaskName
    cold_boot_without_user_logon = 'NOT_YET_PROVEN'
    operational_completion = 'INCOMPLETE'
} | ConvertTo-Json -Compress
