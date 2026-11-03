<div align="center">

# 🤳 Uninstaller Tool

<img alt="Uninstaller Tool banner" src="https://i.postimg.cc/VL6RQQ1p/image.png">

**A Windows uninstaller with leftover scanning. Nothing unnecessary, just a lightweight program.**

[Русская версия](README.ru.md)

</div>

> [!CAUTION]
> **Attention!** The program, written in Python, is no longer supported. I left it on GitHub, but from now on only the C# version is supported. You are downloading an application written in C#.

## Download

The program supports operating systems from Windows XP through Windows 11. Make sure you meet the requirements below so that the program can run on your system.

<details>
<summary><strong>🔶 Windows 10 / Windows 11</strong></summary>

[Download for Windows 10 / Windows 11](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.1.0.0.0/UninstallerTool-Setup-1.0.0-Windows10-11-x64.exe)

### Requirements

- **Architecture:** x64 ONLY
- **.NET Framework:** 4.8+
- **Target framework:** `net48`
- **Setup compiler:** Inno Setup 6

❕ - All features are available, including Microsoft Store. On other, older operating systems (though not in our hearts), some features may be unavailable (they are simply limited).

</details>

<details>
<summary><strong>🔶 Windows 7 / Windows 8 / Windows 8.1</strong></summary>

[Download for Windows 7 / Windows 8 / Windows 8.1](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.1.0.0.0/UninstallerTool-Setup-1.0.0-Windows7-8-8.1.exe)

### Requirements

- **Architecture:** x86 and x64 (AnyCPU)
- **.NET Framework:** 4.6.1+
- **Target framework:** `net461`
- **Setup compiler:** Inno Setup 6

❕ - .NET Framework 4.6.1 is the last version that supports Windows 8 RTM.<br>
❕ - Microsoft Store: on Windows 8/8.1, availability depends on the PowerShell Appx module; it is unavailable on Windows 7.

</details>

<details>
<summary><strong>🔶 Windows XP SP3 / Windows Vista SP1+</strong></summary>

[Download for Windows XP / Windows Vista](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.1.0.0.0/UninstallerTool-Setup-1.0.0-WindowsXP-Vista.exe)

- **Architecture:** x86 and x64
- **.NET Framework:** 4.0 + KB2468871
- **Target framework:** `net40`
- **Setup compiler:** Inno Setup 5.6.1

### Target machine requirements

1. **Windows XP SP3** or **Windows Vista SP1+**.
2. **.NET Framework 4.0 Full**.
3. **KB2468871** - .NET Framework 4 update that adds support for Portable Class Library.

❕ - Microsoft Store apps are not available on XP/Vista.<br>
❕ - WPF usually works without hardware acceleration.<br>
❕ - Vista RTM without SP1 is rejected by the installer.<br>
❕ - Windows XP x64 is detected as version 5.2 and is supported.

</details>

## Features

- [x] **List of all installed programs** - View all programs installed on your system.
- [x] **Program search and filtering** - Quickly find the programs you need. [See what it looks like](https://i.postimg.cc/8z5SHpSh/image.png)
- [x] **Uninstall selected programs** - Uninstall several programs at once.
- [x] **Silent uninstallation mode** - The program uninstalls programs automatically, without requiring your intervention.
- [x] **Detect and remove leftover files** - Clean up files left behind after uninstallation.
- [x] **Detailed program information** - View program sizes and details (publisher, installation date, version, location, and uninstall command). [See what it looks like](https://i.postimg.cc/zXdm3sg7/image.png)
- [x] **Disk usage analysis** - See which programs take up the most space on your drive. [See what it looks like](https://i.postimg.cc/2jwMXsTX/image.png)
- [x] **File preview** - See which files will be deleted. [See what it looks like](https://i.postimg.cc/V6FGpt94/image.png)
- [x] **Responsive interface** - The program works at any screen size.
