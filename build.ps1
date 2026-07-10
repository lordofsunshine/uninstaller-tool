$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = $PSScriptRoot
$requiredFiles = @(
    "main.py",
    "version_info.txt",
    "assets\app_icon.ico"
)

foreach ($file in $requiredFiles) {
    $path = Join-Path $root $file
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required build file not found: $path"
    }
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH."
}

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed. Run: python -m pip install pyinstaller"
}

Push-Location $root
try {
    python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --uac-admin `
        --name UninstallerTool `
        --icon "assets\app_icon.ico" `
        --add-data "assets\app_icon.ico;assets" `
        --version-file "version_info.txt" `
        "main.py"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    $exe = Join-Path $root "dist\UninstallerTool.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Build completed without the expected executable: $exe"
    }

    $item = Get-Item -LiteralPath $exe
    $hash = Get-FileHash -LiteralPath $exe -Algorithm SHA256
    Write-Host ""
    Write-Host "Build completed: $($item.FullName)"
    Write-Host "Size: $([math]::Round($item.Length / 1MB, 2)) MiB"
    Write-Host "SHA-256: $($hash.Hash)"
}
finally {
    Pop-Location
}
