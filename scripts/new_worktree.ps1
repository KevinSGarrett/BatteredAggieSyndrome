param(
    [Parameter(Mandatory=$true)][string]$TaskSlug,
    [string]$BaseBranch = "main"
)
$ErrorActionPreference = "Stop"
if ($TaskSlug -notmatch '^BAT-[0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*$') {
    throw "TaskSlug must be BAT-123-short-kebab-description."
}
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$actualRoot = (git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or ([IO.Path]::GetFullPath($actualRoot)).TrimEnd('\') -ine $repoRoot.TrimEnd('\')) {
    throw "Canonical Git repository identity check failed."
}
$branch = "codex/$TaskSlug"
git show-ref --verify --quiet "refs/heads/$branch"
if ($LASTEXITCODE -eq 0) { throw "Local branch already exists: $branch" }
$configuredRoot = [Environment]::GetEnvironmentVariable("AGGIE_ANALYTICS_DATA_ROOT")
if ([string]::IsNullOrWhiteSpace($configuredRoot)) {
    $commonGitDir = (git rev-parse --path-format=absolute --git-common-dir 2>$null)
    $canonicalRoot = if ($LASTEXITCODE -eq 0) { Split-Path -Parent $commonGitDir } else { $repoRoot }
    $envFiles = @((Join-Path $repoRoot ".env"), (Join-Path $canonicalRoot ".env")) | Select-Object -Unique
    foreach ($envFile in $envFiles) {
        if (Test-Path -LiteralPath $envFile) {
            $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^AGGIE_ANALYTICS_DATA_ROOT=' } | Select-Object -First 1
            if ($line) { $configuredRoot = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'"); break }
        }
    }
}
if ([string]::IsNullOrWhiteSpace($configuredRoot) -or -not [IO.Path]::IsPathFullyQualified($configuredRoot)) {
    throw "AGGIE_ANALYTICS_DATA_ROOT must be configured as an absolute external path."
}
$dataRoot = [IO.Path]::GetFullPath($configuredRoot).TrimEnd('\')
$repoWithSeparator = $repoRoot.TrimEnd('\') + '\'
$dataWithSeparator = $dataRoot + '\'
if ($dataRoot -ieq $repoRoot -or $dataWithSeparator.StartsWith($repoWithSeparator, [StringComparison]::OrdinalIgnoreCase) -or $repoWithSeparator.StartsWith($dataWithSeparator, [StringComparison]::OrdinalIgnoreCase)) {
    throw "AGGIE_ANALYTICS_DATA_ROOT must be disjoint from the repository."
}
$worktreeRoot = Join-Path $dataRoot "worktrees"
New-Item -ItemType Directory -Force -Path $worktreeRoot | Out-Null
$target = Join-Path $worktreeRoot $TaskSlug
if (Test-Path -LiteralPath $target) { throw "Worktree target already exists: $target" }
git worktree add -b $branch $target $BaseBranch
if ($LASTEXITCODE -ne 0) { throw "git worktree add failed." }
Write-Host "Created $branch at $target"
