param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = $PSScriptRoot
$requiredFiles = @(
    "main.py",
    "version_info.txt",
    "UninstallerTool.spec",
    "assets\app_icon.ico",
    "installer\UninstallerTool.iss"
)

foreach ($file in $requiredFiles) {
    $path = Join-Path $root $file
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required build file not found: $path"
    }
}

$python = "python"
foreach ($candidate in @("$root\.venv\Scripts\python.exe", "$root\venv\Scripts\python.exe")) {
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $python = $candidate
        break
    }
}

& $python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed. Run: $python -m pip install pyinstaller"
}

Push-Location $root
try {
    $appVersion = (& $python -c "from app.version import APP_VERSION; print(APP_VERSION)").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($appVersion)) {
        throw "Could not read APP_VERSION from app\version.py."
    }

    $versionInfo = Get-Content -LiteralPath (Join-Path $root "version_info.txt") -Raw
    if ($versionInfo -notmatch [regex]::Escape("u'ProductVersion', u'$appVersion'")) {
        throw "version_info.txt does not match APP_VERSION $appVersion. Update it before building."
    }

    & $python -m PyInstaller --noconfirm --clean "UninstallerTool.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    $exe = Join-Path $root "dist\UninstallerTool\UninstallerTool.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Build completed without the expected executable: $exe"
    }

    $folder = Get-ChildItem -LiteralPath (Join-Path $root "dist\UninstallerTool") -Recurse -File |
        Measure-Object -Property Length -Sum
    $item = Get-Item -LiteralPath $exe
    $hash = Get-FileHash -LiteralPath $exe -Algorithm SHA256
    Write-Host ""
    Write-Host "Build completed: $($item.FullName)"
    Write-Host "Folder size: $([math]::Round($folder.Sum / 1MB, 2)) MiB in $($folder.Count) files"
    Write-Host "Launcher size: $([math]::Round($item.Length / 1MB, 2)) MiB"
    Write-Host "Launcher SHA-256: $($hash.Hash)"

    if ($SkipInstaller) {
        return
    }

    $iscc = $null
    foreach ($candidate in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $iscc = $candidate
            break
        }
    }

    if ($null -eq $iscc) {
        throw "Inno Setup 6 was not found. Install it or run build.ps1 with -SkipInstaller."
    }

    & $iscc "/DAppVersion=$appVersion" (Join-Path $root "installer\UninstallerTool.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }

    $installer = Join-Path $root "dist\UninstallerTool-Setup-$appVersion.exe"
    if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
        throw "Installer was not produced: $installer"
    }

    $setupItem = Get-Item -LiteralPath $installer
    $setupHash = Get-FileHash -LiteralPath $installer -Algorithm SHA256
    Write-Host ""
    Write-Host "Installer: $($setupItem.FullName)"
    Write-Host "Size: $([math]::Round($setupItem.Length / 1MB, 2)) MiB"
    Write-Host "SHA-256: $($setupHash.Hash)"
}
finally {
    Pop-Location
}
