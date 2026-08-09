param(
    [Parameter(Mandatory=$true)][string]$TaskSlug,
    [string]$BaseBranch = "main"
)
$ErrorActionPreference = "Stop"
if ($TaskSlug -notmatch '^[a-z0-9][a-z0-9-]+$') {
    throw "TaskSlug must use lowercase letters, digits and hyphens only."
}
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$branch = "codex/$TaskSlug"
$parent = Split-Path -Parent (Get-Location)
$worktreeRoot = Join-Path $parent "Aggie_Analytics_Engine-worktrees"
New-Item -ItemType Directory -Force -Path $worktreeRoot | Out-Null
$target = Join-Path $worktreeRoot $TaskSlug
if (Test-Path $target) { throw "Worktree target already exists: $target" }
git worktree add -b $branch $target $BaseBranch
Write-Host "Created $branch at $target"
