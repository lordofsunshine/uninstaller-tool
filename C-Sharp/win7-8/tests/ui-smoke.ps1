param(
    [string]$ExePath = "",
    [string]$ScreenshotPath = ""
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WindowRect
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr window, out RECT rect);
}
"@

$automation = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$checks = 0
$failures = 0

function Check {
    param([bool]$Condition, [string]$Name)
    $script:checks++
    if ($Condition) {
        Write-Host "ok    $Name"
    }
    else {
        $script:failures++
        Write-Host "FAIL  $Name"
    }
}

function Get-Window {
    param([int]$TargetProcessId, [int]$TimeoutSeconds = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $condition = New-Object System.Windows.Automation.PropertyCondition($automation::ProcessIdProperty, $TargetProcessId)
        $windows = $automation::RootElement.FindAll($scope::Children, $condition)
        foreach ($window in $windows) {
            return $window
        }

        Start-Sleep -Milliseconds 250
    }

    return $null
}

function Find-ByAutomationId {
    param($Root, [string]$Id)
    $condition = New-Object System.Windows.Automation.PropertyCondition($automation::AutomationIdProperty, $Id)
    return $Root.FindFirst($scope::Descendants, $condition)
}

function Find-ByName {
    param($Root, [string]$Name)
    $condition = New-Object System.Windows.Automation.PropertyCondition($automation::NameProperty, $Name)
    return $Root.FindFirst($scope::Descendants, $condition)
}

function Get-ListItems {
    param($List)
    $condition = New-Object System.Windows.Automation.PropertyCondition($automation::ControlTypeProperty, [System.Windows.Automation.ControlType]::ListItem)
    return $List.FindAll($scope::Children, $condition)
}

function Get-AllText {
    param($Root)
    $condition = New-Object System.Windows.Automation.PropertyCondition($automation::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)
    $items = $Root.FindAll($scope::Descendants, $condition)
    $texts = @()
    foreach ($item in $items) {
        $texts += $item.Current.Name
    }

    return $texts
}

function Set-TextValue {
    param($Element, [string]$Value)
    $pattern = $Element.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
    $pattern.SetValue($Value)
}

function Wait-Until {
    param([scriptblock]$Condition, [int]$TimeoutSeconds = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) {
            return $true
        }

        Start-Sleep -Milliseconds 250
    }

    return $false
}

function Close-Window {
    param($Window)
    try {
        $pattern = $Window.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern)
        $pattern.Close()
    }
    catch {
    }
}

if ([string]::IsNullOrWhiteSpace($ExePath)) {
    $ExePath = Join-Path (Split-Path -Parent $PSScriptRoot) "dist\app\UninstallerTool.exe"
}

if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) {
    throw "Executable not found: $ExePath"
}

$process = Start-Process -FilePath $ExePath -PassThru
$window = $null
$list = $null

try {
    $window = Get-Window -TargetProcessId $process.Id -TimeoutSeconds 40
    Check ($null -ne $window) "main window appears"
    if ($null -eq $window) {
        return
    }

    Check ($window.Current.Name -eq "Uninstaller Tool") "window title"

    Check (Wait-Until -Condition { $script:list = Find-ByAutomationId -Root $window -Id "ProgramList"; $null -ne $script:list } -TimeoutSeconds 20) "program list exists"

    Check (Wait-Until -Condition { (Get-ListItems -List $script:list).Count -gt 0 } -TimeoutSeconds 60) "programs are listed"

    $items = Get-ListItems -List $script:list
    Check ($items.Count -gt 0) "list item count above zero"
    Write-Host "      visible rows: $($items.Count)"

    $texts = Get-AllText -Root $window
    Check (($texts | Where-Object { $_ -match "programs found" }).Count -gt 0) "subtitle shows program count"
    Check (($texts | Where-Object { $_ -eq "No programs selected" }).Count -gt 0) "empty selection summary"

    foreach ($name in @("Disk usage", "Refresh", "Uninstall selected", "Silent mode")) {
        Check ($null -ne (Find-ByName -Root $window -Name $name)) "control present: $name"
    }

    $search = Find-ByAutomationId -Root $window -Id "SearchBox"
    Check ($null -ne $search) "search field exists"
    if ($null -ne $search) {
        Set-TextValue -Element $search -Value "zzzz-no-such-program"
        Start-Sleep -Milliseconds 700
        Check ((Get-ListItems -List $script:list).Count -eq 0) "filter hides non matching rows"
        Check ((Get-AllText -Root $window | Where-Object { $_ -match "of .* programs shown" }).Count -gt 0) "subtitle shows filtered count"

        Set-TextValue -Element $search -Value ""
        Start-Sleep -Milliseconds 700
        Check ((Get-ListItems -List $script:list).Count -gt 0) "filter reset restores rows"
    }

    $items = Get-ListItems -List $script:list
    if ($items.Count -gt 0) {
        $first = $items[0]
        $selection = $first.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
        $selection.Select()
        Start-Sleep -Milliseconds 400

        $texts = Get-AllText -Root $window
        Check (($texts | Where-Object { $_ -eq "PUBLISHER" }).Count -gt 0) "details panel shows fields"
        Check (($texts | Where-Object { $_ -eq "No programs selected" }).Count -gt 0) "summary ignores plain selection"

        $checkBoxCondition = New-Object System.Windows.Automation.PropertyCondition($automation::ControlTypeProperty, [System.Windows.Automation.ControlType]::CheckBox)
        $checkBox = $first.FindFirst($scope::Descendants, $checkBoxCondition)
        Check ($null -ne $checkBox) "row checkbox exists"
        if ($null -ne $checkBox) {
            $toggle = $checkBox.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
            $toggle.Toggle()
            Start-Sleep -Milliseconds 400
            $texts = Get-AllText -Root $window
            Check (($texts | Where-Object { $_ -match "selected" -and $_ -notmatch "No programs selected" }).Count -gt 0) "selection summary counts programs"
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($ScreenshotPath)) {
        try {
            $rect = New-Object WindowRect+RECT
            if ([WindowRect]::GetWindowRect([IntPtr]$window.Current.NativeWindowHandle, [ref]$rect)) {
                $width = $rect.Right - $rect.Left
                $height = $rect.Bottom - $rect.Top
                if ($width -gt 0 -and $height -gt 0) {
                    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
                    $directory = Split-Path -Parent $ScreenshotPath
                    if (-not (Test-Path -LiteralPath $directory)) {
                        New-Item -ItemType Directory -Path $directory -Force | Out-Null
                    }

                    $bitmap.Save($ScreenshotPath, [System.Drawing.Imaging.ImageFormat]::Png)
                    $graphics.Dispose()
                    $bitmap.Dispose()
                    Write-Host "      screenshot: $ScreenshotPath"
                }
            }
        }
        catch {
            Write-Host "      screenshot skipped: $($_.Exception.Message)"
        }
    }

    Close-Window -Window $window
    Check (Wait-Until -Condition { $process.HasExited } -TimeoutSeconds 20) "application closes cleanly"
}
finally {
    if (-not $process.HasExited) {
        $process.Kill()
    }
}

Write-Host ""
Write-Host "checks=$checks failures=$failures"
if ($failures -gt 0) {
    exit 1
}
