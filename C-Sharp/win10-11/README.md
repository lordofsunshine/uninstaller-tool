<div align="center">

# Uninstaller Tool — Windows 10 / 11

[English](#english) · [Русский](#русский)

</div>

---

<a id="english"></a>

## English

### Compatibility

| Parameter | Value |
|:----------|:------|
| OS | Windows 10, Windows 11 |
| Architecture | x64 |
| .NET Framework | 4.8+ |
| Target framework | `net48` |
| Setup compiler | Inno Setup 6 |

### Build

```powershell
powershell -ExecutionPolicy Bypass -File .\win10-11\build.ps1
```

The script builds the application, runs tests, compiles the installer into
`win10-11/dist`, and prints the SHA-256 hash.

**Skip tests:**

```powershell
powershell -ExecutionPolicy Bypass -File .\win10-11\build.ps1 -SkipTests
```

### Requirements

- .NET SDK;
- Inno Setup 6.

### Notes

- The installer checks for .NET Framework 4.8 (`Release >= 528040`).
- Only x64 architecture is supported.
- All features are available, including Microsoft Store support.

---

<a id="русский"></a>

<details>
<summary><strong>Русская версия</strong></summary>

## Русский

### Совместимость

| Параметр | Значение |
|:---------|:---------|
| ОС | Windows 10, Windows 11 |
| Архитектура | x64 |
| .NET Framework | 4.8+ |
| Target framework | `net48` |
| Компилятор установщика | Inno Setup 6 |

### Сборка

```powershell
powershell -ExecutionPolicy Bypass -File .\win10-11\build.ps1
```

Скрипт собирает приложение, запускает тесты, компилирует установщик в
`win10-11/dist` и печатает SHA-256.

**Пропустить тесты:**

```powershell
powershell -ExecutionPolicy Bypass -File .\win10-11\build.ps1 -SkipTests
```

### Требования

- .NET SDK;
- Inno Setup 6.

### Особенности

- Установщик проверяет .NET Framework 4.8 (`Release >= 528040`).
- Разрешена только x64-архитектура.
- Доступны все функции, включая Microsoft Store.

</details>