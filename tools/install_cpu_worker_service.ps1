[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [string]$InstallRoot = 'C:\BatteredAggieWorker',
    [string]$ExpectedHostName = 'comfy-v4-cpu-01',
    [string]$WorkerTailscaleIPv4 = '100.77.151.3',
    [string]$ControllerTailscaleIPv4 = '100.79.129.63',
    [int]$Port = 8765,
    [switch]$Replace
)

$ErrorActionPreference = 'Stop'
$taskName = 'AggieAnalyticsPrivateCpuWorker'
$firewallName = 'Aggie Analytics private CPU worker'
$actualHostName = [System.Net.Dns]::GetHostName()
if ($actualHostName -ne $ExpectedHostName) { throw "CPU_WORKER_HOST_IDENTITY_MISMATCH:$actualHostName" }
if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $WorkerTailscaleIPv4 -ErrorAction SilentlyContinue)) {
    throw 'CPU_WORKER_TAILSCALE_IP_MISSING'
}
$python = (Get-Command python -ErrorAction Stop).Source
if ((Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) -and -not $Replace) {
    throw 'CPU_WORKER_TASK_EXISTS_USE_REPLACE'
}
if ((Get-NetFirewallRule -DisplayName $firewallName -ErrorAction SilentlyContinue) -and -not $Replace) {
    throw 'CPU_WORKER_FIREWALL_RULE_EXISTS_USE_REPLACE'
}
$sourceService = Join-Path $SourceRoot 'tools\cpu_worker_service.py'
$sourcePackage = Join-Path $SourceRoot 'src\aggie_analytics'
if (-not (Test-Path -LiteralPath $sourceService -PathType Leaf) -or -not (Test-Path -LiteralPath $sourcePackage -PathType Container)) {
    throw 'CPU_WORKER_SOURCE_BUNDLE_INCOMPLETE'
}

if ($PSCmdlet.ShouldProcess($InstallRoot, 'Install private deterministic CPU worker')) {
    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $InstallRoot 'src') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $InstallRoot 'tools') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $InstallRoot 'data') -Force | Out-Null
    Copy-Item -LiteralPath $sourceService -Destination (Join-Path $InstallRoot 'tools\cpu_worker_service.py') -Force
    Copy-Item -LiteralPath $sourcePackage -Destination (Join-Path $InstallRoot 'src') -Recurse -Force
    Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    Get-NetFirewallRule -DisplayName $firewallName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName $firewallName -Direction Inbound -Action Allow -Protocol TCP -LocalAddress $WorkerTailscaleIPv4 -LocalPort $Port -RemoteAddress $ControllerTailscaleIPv4 -Profile Any | Out-Null
    $arguments = "-B `"$InstallRoot\tools\cpu_worker_service.py`" --bind $WorkerTailscaleIPv4 --port $Port --controller-ip $ControllerTailscaleIPv4 --storage-root `"$InstallRoot\data`""
    $action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $InstallRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
}

[pscustomobject]@{
    HostName = $actualHostName
    InstallRoot = $InstallRoot
    BindAddress = $WorkerTailscaleIPv4
    AllowedRemoteAddress = $ControllerTailscaleIPv4
    Port = $Port
    PublicExposure = $false
    ArbitraryShellOrPathExecution = $false
    ScheduledTask = $taskName
    FirewallRule = $firewallName
}
