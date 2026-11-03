# ASCII-only wrapper. Usage: powershell -File git_wrap.ps1 <cmd> [args...]
$ErrorActionPreference = "Stop"
$git = "C:\Program Files\Git\cmd\git.exe"
& $git @args 2>&1
exit $LASTEXITCODE
