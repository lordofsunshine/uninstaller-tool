<div align="center">

# Uninstaller Tool — Windows XP / Vista

[English](#english) · [Русский](#russian)

</div>

---

<a id="english"></a>

## English

### Compatibility

| Parameter | Value |
|:----------|:------|
| OS | Windows XP SP3, Windows Vista SP1+ |
| Architecture | x86 and x64 |
| .NET Framework | 4.0 + KB2468871 |
| Target framework | `net40` |
| Setup compiler | Inno Setup 5.6.1 (Unicode) |

### Build

```powershell
powershell -ExecutionPolicy Bypass -File .\winxp-vista\build.ps1
```

The script builds the application, runs tests, compiles the installer into `winxp-vista/dist`, and prints the SHA-256 hash.

**Skip tests:**

```powershell
powershell -ExecutionPolicy Bypass -File .\winxp-vista\build.ps1 -SkipTests
```

### Build Requirements

- .NET SDK;
- Inno Setup 5.6.1 — the last version supporting Windows XP.

  Download: [Inno Setup — Older Versions](https://jrsoftware.org/isdl-old.php).

The script searches for `ISCC.exe` in the standard Inno Setup 5 directories, as well as in:

- `..\tools\InnoSetup561`
- `..\compat\tools\InnoSetup561`

### Target Machine Requirements

1. **Windows XP SP3** or **Windows Vista SP1+**.
2. **.NET Framework 4.0 Full**.
3. **KB2468871** — a .NET Framework 4 update required for Portable Class Library support. It is needed for `Microsoft.Bcl.Async` and is usually delivered through Windows Update.

### .NET 4.0 Compatibility Adaptations

- `IReadOnlyList<T>` → `IList<T>`.
- `Task.Run` → `Task.Factory.StartNew`.
- `Task.Delay` → `TaskEx.Delay`.
- `Array.Empty<string>()` → `new string[0]`.
- `DateTimeOffset.ToUnixTimeSeconds()` → a local helper.
- `ValueTuple` → regular classes.
- `System.Progress<T>` → a custom compatible class.
- XAML virtualization → `VirtualizingStackPanel.*`.

### Limitations

- Microsoft Store applications are not available on Windows XP/Vista.
- WPF usually works without hardware acceleration.
- Windows Vista RTM without SP1 is rejected by the installer.
- Windows XP x64 is identified as version 5.2 and is supported.

---

<a id="russian"></a>

<details>
<summary><strong>Русская версия</strong></summary>

## Русский

### Совместимость

| Параметр | Значение |
|:---------|:---------|
| ОС | Windows XP SP3, Windows Vista SP1+ |
| Архитектура | x86 и x64 |
| .NET Framework | 4.0 + KB2468871 |
| Target framework | `net40` |
| Компилятор установщика | Inno Setup 5.6.1 (Unicode) |

### Сборка

```powershell
powershell -ExecutionPolicy Bypass -File .\winxp-vista\build.ps1
```

Скрипт собирает приложение, запускает тесты, компилирует установщик в `winxp-vista/dist` и печатает SHA-256.

**Пропустить тесты:**

```powershell
powershell -ExecutionPolicy Bypass -File .\winxp-vista\build.ps1 -SkipTests
```

### Требования к сборке

- .NET SDK;
- Inno Setup 5.6.1 — последняя версия, поддерживающая Windows XP.

  Скачать: [Inno Setup — старые версии](https://jrsoftware.org/isdl-old.php).

Скрипт ищет `ISCC.exe` в стандартных путях Inno Setup 5, а также в:

- `..\tools\InnoSetup561`
- `..\compat\tools\InnoSetup561`

### Требования к целевой машине

1. **Windows XP SP3** или **Windows Vista SP1+**.
2. **.NET Framework 4.0 Full**.
3. **KB2468871** — обновление .NET Framework 4 для поддержки Portable Class Library. Нужно для `Microsoft.Bcl.Async`; обычно приходит через Windows Update.

### Что адаптировано под .NET 4.0 в моём софте

- `IReadOnlyList<T>` → `IList<T>`.
- `Task.Run` → `Task.Factory.StartNew`.
- `Task.Delay` → `TaskEx.Delay`.
- `Array.Empty<string>()` → `new string[0]`.
- `DateTimeOffset.ToUnixTimeSeconds()` → локальный помощник.
- `ValueTuple` → обычные классы.
- `System.Progress<T>` → собственный совместимый класс.
- Виртуализация XAML → `VirtualizingStackPanel.*`.

### Ограничения

- Microsoft Store приложений на XP/Vista нет.
- WPF обычно работает без аппаратного ускорения.
- Vista RTM без SP1 отклоняется установщиком.
- Windows XP x64 определяется как 5.2 и поддерживается.

</details>