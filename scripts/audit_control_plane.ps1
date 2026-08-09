param(
    [string]$RepoRoot = ".",
    [string]$Output = "artifacts/control-plane-audit.json"
)

$ErrorActionPreference = "Stop"
python -B tools/audit_control_plane.py --repo-root $RepoRoot --output $Output
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
