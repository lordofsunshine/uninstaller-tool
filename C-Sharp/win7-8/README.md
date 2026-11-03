<div align="center">

# Uninstaller Tool — Windows 7 / 8 / 8.1

[English](#english) · [Русский](#русский)

</div>

---

<a id="english"></a>

## English

### Compatibility

| Parameter | Value |
|:----------|:------|
| OS | Windows 7 SP1, Windows 8, Windows 8.1 |
| Architecture | x86 and x64 (AnyCPU) |
| .NET Framework | 4.6.1+ |
| Target framework | `net461` |
| Setup compiler | Inno Setup 6 |

### Build

```powershell
powershell -ExecutionPolicy Bypass -File .\win7-8\build.ps1
```

The script builds the application, runs tests, compiles the installer into
`win7-8/dist`, and prints the SHA-256 hash.

**Skip tests:**

```powershell
powershell -ExecutionPolicy Bypass -File .\win7-8\build.ps1 -SkipTests
```

### Requirements

- .NET SDK;
- Inno Setup 6.

### Notes

- .NET Framework 4.6.1 is the last version that supports Windows 8 RTM.
- The installer checks `Release >= 394254`.
- `System.ValueTuple.dll` is included.
- The application is built as AnyCPU and works on both 32-bit and 64-bit systems.
- Microsoft Store: on Windows 8/8.1, availability depends on the PowerShell Appx module. It is unavailable on Windows 7.

---

<a id="русский"></a>

<details>
<summary><strong>Русская версия</strong></summary>

## Русский

### Совместимость

| Параметр | Значение |
|:---------|:---------|
| ОС | Windows 7 SP1, Windows 8, Windows 8.1 |
| Архитектура | x86 и x64 (AnyCPU) |
| .NET Framework | 4.6.1+ |
| Target framework | `net461` |
| Компилятор установщика | Inno Setup 6 |

### Сборка

```powershell
powershell -ExecutionPolicy Bypass -File .\win7-8\build.ps1
```

Скрипт собирает приложение, запускает тесты, компилирует установщик в
`win7-8/dist` и выводит SHA-256.

**Пропустить тесты:**

```powershell
powershell -ExecutionPolicy Bypass -File .\win7-8\build.ps1 -SkipTests
```

### Требования

- .NET SDK;
- Inno Setup 6.

### Особенности

- .NET Framework 4.6.1 — последняя версия, которая поддерживает Windows 8 RTM.
- Установщик проверяет `Release >= 394254`.
- В комплект входит `System.ValueTuple.dll`.
- Приложение собирается как AnyCPU и работает как на 32-битных, так и на 64-битных системах.
- Microsoft Store: в Windows 8/8.1 зависит от Appx-модуля PowerShell, в Windows 7 недоступен.

</details>