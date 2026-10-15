# Shanyi launcher: kill old instance, find Python, start hidden.
# Lives in the repo root; works on any machine with Python 3.11+ installed.
$ErrorActionPreference = "Stop"

# kill previous instance
$old = Get-CimInstance Win32_Process -Filter "Name='python.exe','pythonw.exe'" |
    Where-Object { $_.CommandLine -like '*shanyi*main.py*' }
$old | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Milliseconds 500

# locate Python: prefer pythonw (no console), fall back to python/py launcher
$py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error "Python not found in PATH"; exit 1 }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process -FilePath $py -ArgumentList (Join-Path $root "main.py") `
    -WindowStyle Hidden -WorkingDirectory $root
Write-Output "started"
