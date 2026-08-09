param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = "Stop"
python tools/backup_state.py --source $Source --output $Output
