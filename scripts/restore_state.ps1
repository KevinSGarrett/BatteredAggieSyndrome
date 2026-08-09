param([Parameter(Mandatory=$true)][string]$Backup,[Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = "Stop"
python tools/restore_state.py --backup $Backup --destination $Destination
