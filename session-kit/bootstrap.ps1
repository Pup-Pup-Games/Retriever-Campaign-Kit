# Thin wrapper so you can run the bootstrapper from PowerShell.
# Usage:
#   .\session-kit\bootstrap.ps1 --target ..\my-campaign --group winterfell --title "Winterfell Falls"
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $here "bootstrap.py") @args
