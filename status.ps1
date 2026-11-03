# status.ps1 - quick orientation at tick start. ASCII-only output (PS 5.1 encoding safe).
# Only reads inside my own directory. Usage: powershell -NoProfile -File status.ps1

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path   # repo root, no hardcoded path

Write-Output "=== TIME ==="
Get-Date -Format "yyyy-MM-dd HH:mm:ss dddd"

Write-Output ""
Write-Output "=== MY FILES ==="
Get-ChildItem $root -Force | Sort-Object Name |
    Select-Object @{n='Bytes';e={$_.Length}},
                  @{n='Changed';e={$_.LastWriteTime.ToString('HH:mm')}},
                  Name |
    Format-Table -AutoSize | Out-String -Width 200 | Write-Output

Write-Output "=== SUMMARY ==="
$files = @(Get-ChildItem $root -Force -File)
$total = ($files | Measure-Object -Property Length -Sum).Sum
Write-Output ("files: " + $files.Count + ", total bytes: " + $total)
