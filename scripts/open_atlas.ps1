$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$url = 'http://127.0.0.1:8765'
try {
    $health = Invoke-RestMethod ($url + '/api/health') -TimeoutSec 2
    if ($health.app -ne 'ALJABR') { throw 'Unexpected service on atlas port' }
} catch {
    New-Item -ItemType Directory -Force logs | Out-Null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $python = (Get-Command py).Source
        $arguments = @('-3')
    } else {
        $python = (Get-Command python -ErrorAction Stop).Source
        $arguments = @()
    }
    $arguments += @(('"' + (Join-Path $PSScriptRoot 'serve.py') + '"'), '--no-browser')
    Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $root 'logs\atlas-server.log') -RedirectStandardError (Join-Path $root 'logs\atlas-server-errors.log')
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod ($url + '/api/health') -TimeoutSec 1
            if ($health.app -eq 'ALJABR') { $ready = $true; break }
        } catch {}
    }
    if (-not $ready) { throw 'Atlas server could not start. See logs\atlas-server-errors.log.' }
}
Start-Process ($url + '/aljabr.html')
