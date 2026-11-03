param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = $PSScriptRoot
$framework = "net461"
$version = "1.0.0"
$project = Join-Path $root "src\UninstallerTool\UninstallerTool.csproj"
$tests = Join-Path $root "tests\UninstallerTool.Tests\UninstallerTool.Tests.csproj"
$iss = Join-Path $root "installer\UninstallerTool.iss"
$appDir = Join-Path $root "dist\app"
$installerName = "UninstallerTool-Setup-$version-Windows7-8-8.1.exe"

function Resolve-Dotnet {
    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "dotnet\dotnet.exe"),
        (Join-Path $env:ProgramFiles "dotnet\dotnet.exe")
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }

    $command = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }

    throw "The .NET SDK was not found."
}

function Resolve-Iscc {
    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "InnoSetup\ISCC.exe"),
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe"
    )) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }

    throw "Inno Setup 6 was not found."
}

$dotnet = Resolve-Dotnet
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:DOTNET_NOLOGO = "1"

& $dotnet build $project -c Release -f $framework -v minimal
if ($LASTEXITCODE -ne 0) {
    throw "Application build failed."
}

if (-not $SkipTests) {
    & $dotnet build $tests -c Release -f $framework -v minimal
    if ($LASTEXITCODE -ne 0) {
        throw "Test build failed."
    }

    $testExe = Join-Path $root "tests\UninstallerTool.Tests\bin\Release\$framework\UninstallerTool.Tests.exe"
    & $testExe
    if ($LASTEXITCODE -ne 0) {
        throw "Functional tests failed."
    }
}

if (Test-Path -LiteralPath $appDir) {
    Remove-Item -LiteralPath $appDir -Recurse -Force
}

New-Item -ItemType Directory -Path $appDir -Force | Out-Null
Copy-Item -Path (Join-Path $root "src\UninstallerTool\bin\Release\$framework\*") -Destination $appDir -Recurse -Force

if (-not (Test-Path -LiteralPath (Join-Path $appDir "UninstallerTool.exe") -PathType Leaf)) {
    throw "Missing executable after build."
}

$iscc = Resolve-Iscc
& $iscc "/DAppVersion=$version" $iss | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "The installer build failed."
}

$installer = Join-Path $root "dist\$installerName"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
    throw "The installer was not produced: $installer"
}

$item = Get-Item -LiteralPath $installer
$hash = Get-FileHash -LiteralPath $installer -Algorithm SHA256
Write-Host ""
Write-Host "Installer: $($item.FullName)"
Write-Host "Size: $([math]::Round($item.Length / 1MB, 2)) MB"
Write-Host "SHA-256: $($hash.Hash)"
