[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [string]$InstallRoot = 'C:\BatteredAggieWorkerV2',
    [string]$ExpectedHostName = 'comfy-v4-cpu-01',
    [string]$ExpectedTailscaleDNSName = 'comfy-v4-cpu-01.tail9b05ab.ts.net',
    [string]$ExpectedTailscaleNodeId = 'nUxabVWSHb11CNTRL',
    [Parameter(Mandatory = $true)][string]$ExpectedUserLogin,
    [Parameter(Mandatory = $true)][string]$SigningKeyInputPath,
    [int]$Port = 8765,
    [switch]$Replace
)

$ErrorActionPreference = 'Stop'
$taskName = 'AggieAnalyticsPrivateCpuWorkerV2'
$actualHostName = [System.Net.Dns]::GetHostName()
if ($actualHostName -ne $ExpectedHostName) { throw "CPU_WORKER_HOST_IDENTITY_MISMATCH:$actualHostName" }
$tailscaleStatus = (& tailscale status --json | ConvertFrom-Json)
$selfDns = [string]$tailscaleStatus.Self.DNSName
if ($selfDns.TrimEnd('.') -ne $ExpectedTailscaleDNSName) { throw "CPU_WORKER_TAILSCALE_IDENTITY_MISMATCH:$selfDns" }
if ([string]$tailscaleStatus.Self.ID -ne $ExpectedTailscaleNodeId) { throw 'CPU_WORKER_TAILSCALE_NODE_ID_MISMATCH' }
if (-not $tailscaleStatus.Self.Online) { throw 'CPU_WORKER_TAILSCALE_OFFLINE' }
if (-not (Test-Path -LiteralPath $SigningKeyInputPath -PathType Leaf)) { throw 'CPU_WORKER_SIGNING_KEY_INPUT_MISSING' }
$inputKey = [IO.File]::ReadAllBytes($SigningKeyInputPath)
if ($inputKey.Length -ne 32) { [Array]::Clear($inputKey, 0, $inputKey.Length); throw 'CPU_WORKER_SIGNING_KEY_INPUT_INVALID' }
$null = & tailscale serve --help
if ($LASTEXITCODE -ne 0) { throw 'CPU_WORKER_TAILSCALE_SERVE_UNAVAILABLE' }

$runtimeSourceRoot = Join-Path $SourceRoot 'runtime'
$runtimeManifestPath = Join-Path $SourceRoot 'runtime_manifest.csv'
if (-not (Test-Path -LiteralPath $runtimeSourceRoot -PathType Container)) { throw 'CPU_WORKER_RUNTIME_SOURCE_MISSING' }
if (-not (Test-Path -LiteralPath $runtimeManifestPath -PathType Leaf)) { throw 'CPU_WORKER_RUNTIME_MANIFEST_MISSING' }
$runtimeSourceRootResolved = [IO.Path]::GetFullPath($runtimeSourceRoot).TrimEnd('\')
$runtimeEntries = @(Import-Csv -LiteralPath $runtimeManifestPath)
if ($runtimeEntries.Count -eq 0) { throw 'CPU_WORKER_RUNTIME_MANIFEST_EMPTY' }
$runtimePaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($entry in $runtimeEntries) {
    $relativePath = [string]$entry.relative_path
    if ([string]::IsNullOrWhiteSpace($relativePath) -or [IO.Path]::IsPathRooted($relativePath)) {
        throw 'CPU_WORKER_RUNTIME_MANIFEST_PATH_INVALID'
    }
    $sourcePath = [IO.Path]::GetFullPath((Join-Path $runtimeSourceRootResolved $relativePath))
    if (-not $sourcePath.StartsWith($runtimeSourceRootResolved + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'CPU_WORKER_RUNTIME_MANIFEST_PATH_ESCAPE'
    }
    if (-not $runtimePaths.Add($relativePath)) { throw "CPU_WORKER_RUNTIME_MANIFEST_DUPLICATE:$relativePath" }
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "CPU_WORKER_RUNTIME_FILE_MISSING:$relativePath" }
    $sourceItem = Get-Item -LiteralPath $sourcePath
    if ([int64]$entry.bytes -ne $sourceItem.Length) { throw "CPU_WORKER_RUNTIME_BYTES_MISMATCH:$relativePath" }
    $sourceSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
    if ($sourceSha -ne ([string]$entry.sha256).ToLowerInvariant()) { throw "CPU_WORKER_RUNTIME_HASH_MISMATCH:$relativePath" }
}
$actualRuntimeFiles = @(Get-ChildItem -LiteralPath $runtimeSourceRootResolved -Recurse -File)
if ($actualRuntimeFiles.Count -ne $runtimeEntries.Count) { throw 'CPU_WORKER_RUNTIME_MANIFEST_COVERAGE_MISMATCH' }
foreach ($actualRuntimeFile in $actualRuntimeFiles) {
    $actualRelativePath = $actualRuntimeFile.FullName.Substring($runtimeSourceRootResolved.Length).TrimStart('\')
    if (-not $runtimePaths.Contains($actualRelativePath)) { throw "CPU_WORKER_RUNTIME_UNMANIFESTED_FILE:$actualRelativePath" }
}
$runtimePythonSource = Join-Path $runtimeSourceRootResolved 'python.exe'
if (-not (Test-Path -LiteralPath $runtimePythonSource -PathType Leaf)) { throw 'CPU_WORKER_RUNTIME_PYTHON_MISSING' }
$runtimeProbe = (& $runtimePythonSource -I -c "import json,platform,sys;print(json.dumps({'version':platform.python_version(),'bits':64 if sys.maxsize>2**32 else 32}))" | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw 'CPU_WORKER_RUNTIME_PROBE_FAILED' }
if ([string]$runtimeProbe.version -ne '3.11.9') { throw "CPU_WORKER_RUNTIME_VERSION_MISMATCH:$($runtimeProbe.version)" }
if ([int]$runtimeProbe.bits -ne 64) { throw "CPU_WORKER_RUNTIME_ARCHITECTURE_MISMATCH:$($runtimeProbe.bits)" }

$files = @(
    @{ Source = 'tools\cpu_worker_service.py'; Destination = 'tools\cpu_worker_service.py' },
    @{ Source = 'tools\cpu_worker_minimal_init.py'; Destination = 'src\aggie_analytics\assistive_plane\__init__.py' },
    @{ Source = 'src\aggie_analytics\__init__.py'; Destination = 'src\aggie_analytics\__init__.py' },
    @{ Source = 'src\aggie_analytics\assistive_plane\contracts.py'; Destination = 'src\aggie_analytics\assistive_plane\contracts.py' },
    @{ Source = 'src\aggie_analytics\assistive_plane\cpu_worker_backend.py'; Destination = 'src\aggie_analytics\assistive_plane\cpu_worker_backend.py' }
)
foreach ($file in $files) {
    if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot $file.Source) -PathType Leaf)) {
        throw "CPU_WORKER_MINIMAL_BUNDLE_SOURCE_MISSING:$($file.Source)"
    }
}
if ((Test-Path -LiteralPath $InstallRoot) -and -not $Replace) { throw 'CPU_WORKER_V2_INSTALL_ROOT_EXISTS_USE_REPLACE' }
if ((Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) -and -not $Replace) {
    throw 'CPU_WORKER_V2_TASK_EXISTS_USE_REPLACE'
}

$parent = Split-Path -Parent $InstallRoot
$staging = Join-Path $parent ('.aggie-worker-v2-staging-' + [guid]::NewGuid().ToString('N'))
$recovery = $null
if ($PSCmdlet.ShouldProcess($InstallRoot, 'Install corrected least-privilege private CPU worker')) {
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    foreach ($directory in @('tools', 'src\aggie_analytics\assistive_plane', 'data', 'runtime', 'secrets')) {
        New-Item -ItemType Directory -Path (Join-Path $staging $directory) -Force | Out-Null
    }
    $manifest = @()
    foreach ($file in $files) {
        $source = Join-Path $SourceRoot $file.Source
        $destination = Join-Path $staging $file.Destination
        Copy-Item -LiteralPath $source -Destination $destination -Force
        $manifest += [ordered]@{
            kind = 'worker_code'
            relative_path = $file.Destination
            source_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
            installed_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
        }
    }
    foreach ($entry in $runtimeEntries) {
        $source = Join-Path $runtimeSourceRootResolved $entry.relative_path
        $relativeDestination = Join-Path 'runtime' $entry.relative_path
        $destination = Join-Path $staging $relativeDestination
        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
        $manifest += [ordered]@{
            kind = 'embedded_python_runtime'
            relative_path = $relativeDestination
            source_sha256 = ([string]$entry.sha256).ToLowerInvariant()
            installed_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
        }
    }
    $manifestPath = Join-Path $staging 'worker_bundle_manifest.json'
    $manifestPayload = [ordered]@{
        schema_version = 3
        worker_dns_name = $selfDns.TrimEnd('.')
        worker_node_id = [string]$tailscaleStatus.Self.ID
        windows_hostname = $actualHostName
        created_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        python_runtime = [ordered]@{
            distribution = 'CPython embeddable package'
            version = [string]$runtimeProbe.version
            architecture_bits = [int]$runtimeProbe.bits
            executable_relative_path = 'runtime\python.exe'
            source_archive_sha256 = '009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b'
            source_signature_verified = $true
        }
        files = $manifest
    }
    [IO.File]::WriteAllText($manifestPath, ($manifestPayload | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    $keyPath = Join-Path $staging 'secrets\worker-hmac.key'
    [IO.File]::WriteAllBytes($keyPath, $inputKey)
    [Array]::Clear($inputKey, 0, $inputKey.Length)

    if (Test-Path -LiteralPath $InstallRoot) {
        $existingManifest = Join-Path $InstallRoot 'worker_bundle_manifest.json'
        if (-not (Test-Path -LiteralPath $existingManifest -PathType Leaf)) { throw 'CPU_WORKER_EXISTING_ROOT_NOT_VERIFIED_V2' }
        $recovery = "$InstallRoot.recovery.$((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))"
        Move-Item -LiteralPath $InstallRoot -Destination $recovery
    }
    Move-Item -LiteralPath $staging -Destination $InstallRoot
    $installedManifest = Get-Content -LiteralPath (Join-Path $InstallRoot 'worker_bundle_manifest.json') -Raw | ConvertFrom-Json
    foreach ($file in $installedManifest.files) {
        $installedFile = Join-Path $InstallRoot $file.relative_path
        if (-not (Test-Path -LiteralPath $installedFile -PathType Leaf)) { throw "CPU_WORKER_POST_TRANSFER_FILE_MISSING:$($file.relative_path)" }
        $postTransferSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $installedFile).Hash.ToLowerInvariant()
        if ($postTransferSha -ne $file.installed_sha256) { throw "CPU_WORKER_POST_TRANSFER_HASH_MISMATCH:$($file.relative_path)" }
    }
    Remove-Item -LiteralPath $SigningKeyInputPath -Force

    & icacls $InstallRoot /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' 'LOCAL SERVICE:(OI)(CI)RX' | Out-Null
    & icacls (Join-Path $InstallRoot 'data') /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' 'LOCAL SERVICE:(OI)(CI)M' | Out-Null
    & icacls (Join-Path $InstallRoot 'runtime') /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' 'LOCAL SERVICE:(OI)(CI)RX' | Out-Null
    & icacls (Join-Path $InstallRoot 'secrets') /inheritance:r /grant:r 'SYSTEM:(OI)(CI)F' 'Administrators:(OI)(CI)F' 'LOCAL SERVICE:(OI)(CI)R' | Out-Null
    Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    $arguments = "-B `"$InstallRoot\tools\cpu_worker_service.py`" --bind 127.0.0.1 --port $Port --storage-root `"$InstallRoot\data`" --signing-key-file `"$InstallRoot\secrets\worker-hmac.key`" --expected-user-login `"$ExpectedUserLogin`""
    $runtimePythonInstalled = Join-Path $InstallRoot 'runtime\python.exe'
    $action = New-ScheduledTaskAction -Execute $runtimePythonInstalled -Argument $arguments -WorkingDirectory $InstallRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
    $principal = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\LOCAL SERVICE' -LogonType ServiceAccount -RunLevel Limited
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
    & tailscale funnel reset | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'CPU_WORKER_TAILSCALE_FUNNEL_RESET_FAILED' }
    & tailscale serve --bg --yes --https=443 "http://127.0.0.1:$Port" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'CPU_WORKER_TAILSCALE_SERVE_CONFIGURATION_FAILED' }
}

[pscustomobject]@{
    HostName = $actualHostName
    TailscaleDNSName = $selfDns.TrimEnd('.')
    TailscaleNodeId = [string]$tailscaleStatus.Self.ID
    InstallRoot = $InstallRoot
    RecoveryRoot = $recovery
    BindAddress = '127.0.0.1'
    PrivateEndpoint = "https://$($selfDns.TrimEnd('.'))"
    Transport = 'TAILSCALE_SERVE_PRIVATE_HTTPS'
    Funnel = $false
    ServiceIdentity = 'NT AUTHORITY\LOCAL SERVICE'
    RunLevel = 'Limited'
    PythonRuntimeVersion = [string]$runtimeProbe.version
    PythonRuntimeArchitectureBits = [int]$runtimeProbe.bits
    PythonExecutable = (Join-Path $InstallRoot 'runtime\python.exe')
    PythonExecutableSha256 = if (Test-Path -LiteralPath (Join-Path $InstallRoot 'runtime\python.exe')) { (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $InstallRoot 'runtime\python.exe')).Hash } else { $null }
    BundleManifestSha256 = if (Test-Path -LiteralPath (Join-Path $InstallRoot 'worker_bundle_manifest.json')) { (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $InstallRoot 'worker_bundle_manifest.json')).Hash } else { $null }
    SigningKeyRecorded = $false
    ArbitraryShellOrPathExecution = $false
    ScheduledTask = $taskName
}
