param([Parameter(ValueFromRemainingArguments=$true)][string[]]$RunnerArgs)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force logs | Out-Null
$bootstrap = Join-Path (Get-Location) 'logs\bootstrap.log'
try {
    $python = $null
    foreach ($candidate in @('py', 'python', 'python3')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            $prefix = @()
            if ($candidate -eq 'py') { $prefix = @('-3') }
            & $candidate @prefix -c 'import sys; assert sys.version_info >= (3,9)' 2>> $bootstrap
            if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
        }
    }
    if (-not $python) { throw 'Install Python 3.9 or newer, including the Python launcher, then retry.' }
    & $python @prefix -u scripts\run.py @RunnerArgs
    exit $LASTEXITCODE
} catch {
    $message = (Get-Date -Format o) + ' BOOTSTRAP ERROR: ' + $_.ToString()
    Add-Content -LiteralPath $bootstrap -Value $message
    Write-Host $message
    exit 1
}
