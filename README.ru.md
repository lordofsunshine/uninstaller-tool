<div align="center">

# 🤳 Uninstaller Tool

<img alt="Баннер Uninstaller Tool" src="https://i.postimg.cc/VL6RQQ1p/image.png">

**Приложение для удаления Windows программ с поиском остатков. Ничего лишнего, лёгкая по размерам.**

[English version](README.md)

</div>

> [!CAUTION]
> **Внимание!** Программа, написанная на Python, больше не поддерживается. Я оставил ее на GitHub, но теперь поддерживается только версия на C#. Вы скачиваете приложение, написанное на C#.

## Скачать программу

Моя программа поддерживает операционные системы, начиная с Windows XP до Windows 11. Главное, следуйте требованиям ниже, чтобы программа у вас запустилась.

<details>
<summary><strong>🔶 Windows 10 / Windows 11</strong></summary>

[Скачать на Windows 10 / Windows 11](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.1.0.0.0/UninstallerTool-Setup-1.0.0-Windows10-11-x64.exe)

### Требования

- **Архитектура:** ТОЛЬКО x64
- **.NET Framework:** 4.8+
- **Target framework:** `net48`
- **Компилятор setup:** Inno Setup 6

❕ - Доступны все функции, включая Microsoft Store. В остальных ОС, более устаревших (но не в наших сердцах), некоторые функции могут быть недоступны (они просто урезаны)

</details>

<details>
<summary><strong>🔶 Windows 7 / Windows 8 / Windows 8.1</strong></summary>

[Скачать на Windows 7 / Windows 8 / Windows 8.1](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.1.0.0.0/UninstallerTool-Setup-1.0.0-Windows7-8-8.1.exe)

### Требования

- **Архитектура:** x86 и x64 (AnyCPU)
- **.NET Framework:** 4.6.1+
- **Target framework:** `net461`
- **Компилятор setup:** Inno Setup 6

❕ -  .NET Framework 4.6.1 - последняя версия, которая поддерживает Windows 8 RTM.
❕ -  Microsoft Store: в Windows 8/8.1 зависит от Appx-модуля PowerShell, в Windows 7 недоступен.

</details>

<details>
<summary><strong>🔶 Windows XP SP3, Windows Vista SP1+</strong></summary>

[Скачать на Windows XP / Windows Vista](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.1.0.0.0/UninstallerTool-Setup-1.0.0-WindowsXP-Vista.exe)

- **Архитектура:** x86 и x64
- **.NET Framework:** 4.0 + KB2468871
- **Target framework:** `net40`
- **Компилятор setup:** Inno Setup 5.6.1

### Требования к целевой машине

1. **Windows XP SP3** или **Windows Vista SP1+**.
2. **.NET Framework 4.0 Full**.
3. **KB2468871** - обновление .NET Framework 4 для поддержки Portable Class Library.

❕ - Microsoft Store приложений на XP/Vista нет.
❕ - WPF обычно работает без аппаратного ускорения.
❕ - Vista RTM без SP1 отклоняется установщиком.
❕ - Windows XP x64 определяется как 5.2 и поддерживается.

</details>

## Возможности

- [x] **Список всех установленных программ** - Вы видите все программы в системе;
- [x] **Поиск и фильтрация программ** - Можете быстро найти нужные программы [Как это выглядит](https://i.postimg.cc/8z5SHpSh/image.png);
- [x] **Удаление выбранных программ** - Удаляйте несколько программ сразу;
- [x] **Тихий режим удаления** - Программа сама удалит программы, без вашего вмешательства в управление;
- [x] **Обнаружение и удаление остаточных файлов** - Очистка файлов после удаления;
- [x] **Просмотр детальной информации о программах** - Размеры и детали программ (Издатель, дата установки программы, версия, местоположение, команда для удаления программы) [Как это выглядит](https://i.postimg.cc/zXdm3sg7/image.png);
- [x] **Анализ использования диска** - Какие программы занимают больше всего места на вашем диске [Как это выглядит](https://i.postimg.cc/2jwMXsTX/image.png);
- [x] **Предварительный просмотр файлов** - Какие файлы будут удалены [Как это выглядит](https://i.postimg.cc/V6FGpt94/image.png);
- [x] **Адаптивный интерфейс** - Программа работает на любом размере экрана.
