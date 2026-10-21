# Installs the official Lean toolchain manager (elan) for the current Windows user.
# Lean/Lake toolchain selection then follows mathlib4/lean-toolchain.
$ErrorActionPreference = 'Stop'
$elanBin = Join-Path $env:USERPROFILE '.elan\bin'
if (Test-Path (Join-Path $elanBin 'lake.exe')) {
    Write-Host 'Lean launcher already installed.'
    exit 0
}
Write-Host 'Installing Lean 4 through its official elan installer...'
$installer = Join-Path $env:TEMP ('aljabr-elan-install-' + [guid]::NewGuid().ToString('N') + '.ps1')
try {
    Invoke-WebRequest -Uri 'https://elan.lean-lang.org/elan-init.ps1' -UseBasicParsing -OutFile $installer
    # Call the downloaded script within this PowerShell process: a native
    # bool is preserved (powershell.exe -File passes command-line strings).
    $result = & $installer -NoPrompt $true -DefaultToolchain "leanprover/lean4:stable"
    if ($result -is [int] -and $result -ne 0) { throw "elan installer returned code $result" }
    if (-not (Test-Path (Join-Path $elanBin 'lake.exe'))) { throw 'Installer completed but lake.exe is missing.' }
    Write-Host 'Lean/elan installation successful.'
} finally {
    Remove-Item $installer -ErrorAction SilentlyContinue
}
