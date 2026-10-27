# 🗿 Uninstaller Tool

<div align="center">
  <img alt="banner" src="https://i.postimg.cc/VL6RQQ1p/image.png">
  
  <p><strong>Powerful and user-friendly application for managing and uninstalling programs on Windows</strong></p>
  
  <p>
    <a href="#english">🇺🇸 English</a> • 
    <a href="#russian">🇷🇺 Русский</a>
  </p>
</div>

Download program (Скачать программу): https://github.com/lordofsunshine/uninstaller-tool/releases/download/v1.0.0/UninstallerTool-Setup-1.0.0.exe

---

## 🇺🇸 English

### What's New? 🆕

**Version 1.0.0**

- The program now starts up many times faster.

### Features

- [x] **List all installed programs** - See everything installed on your system
- [x] **Search and filter programs** - Find programs quickly
- [x] **Uninstall selected programs** - Remove multiple programs at once
- [x] **Silent uninstall option** - Uninstall without user interaction
- [x] **Detect and remove leftover files** - Clean up after uninstalling
- [x] **View detailed program information** - See program details and sizes
- [x] **Disk space analysis** - See which programs use the most space
- [x] **File preview** - See what files will be removed
- [x] **Modern and responsive GUI** - Works on any screen size

### Requirements

- Windows 10 / 11
- Python 3.9 - 3.12 (PySide6 6.7 requires >=3.9,<3.13)
- Administrator privileges (only for uninstalling programs)

**Tested with:** Python 3.9 and 3.12 on Windows 10 and Windows 11. CI runs lint and tests on Python 3.12 (Windows).

### Quick Start

1. **Download and setup:**
   ```bash
   git clone https://github.com/lordofsunshine/uninstaller-tool.git
   cd uninstaller-tool
   ```

2. **Install dependencies:**
   ```bash
   Run setup.bat
   ```

3. **Run the application:**
   ```bash
   .\run.bat
   ```

### Usage

1. **Select programs** you want to uninstall
2. **Choose uninstall mode** (Silent or Interactive)
3. **Click "Uninstall Selected"** to start the process
4. **Review leftover files** and clean them up if needed

### Compiling to Executable

To build the application folder and the single-file installer, install [Inno Setup 6](https://jrsoftware.org/isdl.php), then run:

```bash
pip install "PySide6>=6.7,<7" "psutil>=5.9,<8" "pyinstaller>=6"
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The ready-to-ship installer is written to `dist\UninstallerTool-Setup-<version>.exe`. Use `-SkipInstaller` to build only the application folder.

---

## 🇷🇺 Русский

### Что нового? 🆕

**Версия 1.0.0**

- Программа стала запускаться в разы быстрее.

### Возможности

- [x] **Список всех установленных программ** - Видите все программы в системе
- [x] **Поиск и фильтрация программ** - Быстро найдите нужные программы
- [x] **Удаление выбранных программ** - Удаляйте несколько программ сразу
- [x] **Тихий режим удаления** - Удаление без взаимодействия с пользователем
- [x] **Обнаружение и удаление остаточных файлов** - Очистка после удаления
- [x] **Просмотр детальной информации о программах** - Размеры и детали программ
- [x] **Анализ использования диска** - Какие программы занимают больше всего места
- [x] **Предварительный просмотр файлов** - Какие файлы будут удалены
- [x] **Современный адаптивный интерфейс** - Работает на любом размере экрана

### Требования

- Windows 10 / 11
- Python 3.9 - 3.12 (PySide6 6.7 требует >=3.9,<3.13)
- Права администратора (только для удаления программ)

**Протестировано на:** Python 3.9 и 3.12, Windows 10 и Windows 11. CI запускает линтер и тесты на Python 3.12 (Windows).

### Быстрый старт

1. **Скачайте и настройте:**
   ```bash
   git clone https://github.com/lordofsunshine/uninstaller-tool.git
   cd uninstaller-tool
   ```

2. **Установите зависимости:**
   ```bash
   Запустите setup.bat
   ```

3. **Запустите приложение:**
   ```bash
   .\run.bat
   ```

### Использование

1. **Выберите программы** для удаления
2. **Выберите режим удаления** (Тихий или Обычный)
3. **Нажмите "Uninstall Selected"** для начала процесса
4. **Проверьте остаточные файлы** и очистите их при необходимости

### Создание исполняемого файла

Для сборки папки приложения и установщика в одном файле установите [Inno Setup 6](https://jrsoftware.org/isdl.php) и выполните:

```bash
pip install "PySide6>=6.7,<7" "psutil>=5.9,<8" "pyinstaller>=6"
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Готовый установщик появится в `dist\UninstallerTool-Setup-<version>.exe`. Флаг `-SkipInstaller` собирает только папку приложения.

---

## License

This project is licensed under the *MIT License* - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p><em>Made with 🌞 for Windows users</em></p>
</div>
