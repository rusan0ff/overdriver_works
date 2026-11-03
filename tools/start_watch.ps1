# start_watch.ps1 - start watcher in background so it survives my sleep.
# ASCII only (PowerShell 5.1 reads BOM-less .ps1 as ANSI).
# Usage: powershell -ExecutionPolicy Bypass -File tools\start_watch.ps1 -Minutes 60

param(
    [int]$Minutes = 60,
    [int]$Interval = 60
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = "C:\Python314\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$iters = [int](($Minutes * 60) / $Interval)
$out = Join-Path $PSScriptRoot "watch_stdout.log"

$args = @("tools\watcher.py", "--interval", "$Interval", "--iterations", "$iters", "--net")
$p = Start-Process -FilePath $py -ArgumentList $args -WorkingDirectory $root `
     -RedirectStandardOutput $out -RedirectStandardError (Join-Path $PSScriptRoot "watch_stderr.log") `
     -WindowStyle Hidden -PassThru

"started pid=$($p.Id) iters=$iters interval=$Interval output=$out"
