# 🗿 Uninstaller Tool

<div align="center">
  <img alt="banner" src="https://i.ibb.co/27FVZd93/image.png">
  
  <p><strong>Powerful and user-friendly application for managing and uninstalling programs on Windows</strong></p>
  
  <p>
    <a href="#english">🇺🇸 English</a> • 
    <a href="#russian">🇷🇺 Русский</a>
  </p>
</div>

Download program (Скачать программу): https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.0.0.4/UninstallerTool.exe

---

## 🇺🇸 English

### What's New? 🆕

**Latest Updates:**
- 🎨 **Fresh new look** - The app got a complete visual makeover: clean program cards, rounded corners, and a modern light theme
- 🌙 **Dark theme** - If Windows uses dark mode, the app now switches to dark too. Change your Windows theme and the app follows instantly
- 📋 **Details panel** - Click any program to see its publisher, version, size, and install location in a side panel, with the program's icon shown right next to its name - no more digging through menus
- 📊 **Selection summary** - The bottom bar always shows how many programs you've picked and how much disk space you'll free
- 🛑 **Running program detection** - If a program is still running, the app will notice and offer to close it before uninstalling - no more failed uninstalls
- ⏱️ **Live uninstall progress** - See elapsed time while a program is being removed, plus a thin progress line at the top of the window
- 🐛 **Crash fix** - Fixed an app crash that could happen right after uninstalling, while searching for leftover files
- ⚙️ **Under the hood** - Switched to a faster, more modern interface toolkit and cleaned up the project structure

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

- Windows operating system
- Python 3.8 or higher
- Administrator privileges (for uninstalling programs)

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

To create a standalone executable:

```bash
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

---

## 🇷🇺 Русский

### Что нового? 🆕

**Последние обновления:**
- 🎨 **Свежий дизайн** - Программа полностью преобразилась: аккуратные карточки программ, скруглённые углы и крутая светлая тема
- 🌙 **Тёмная тема** - Если в Windows включена тёмная тема, программа тоже станет тёмной. Поменяете тему Windows - программа переключится сразу
- 📋 **Панель сведений** - Кликните по программе, и справа появятся её издатель, версия, размер и дата установки, а рядом с названием - иконка программы. Больше не нужно искать в меню
- 📊 **Сводка выбора** - Внизу всегда видно, сколько программ выбрано и сколько места на диске освободится
- 🛑 **Обнаружение запущенных программ** - Если программа ещё работает, приложение это заметит и предложит её закрыть перед удалением - никаких неудачных удалений
- ⏱️ **Прогресс в реальном времени** - Во время удаления видно, сколько времени прошло, а вверху окна тонкая полоска прогресса
- 🐛 **Исправлен вылет** - Больше программа не вылетает сразу после удаления, когда идёт поиск остаточных файлов
- ⚙️ **Под капотом** - Переход на более быстрый и современный интерфейс, проект приведён в порядок

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

- Операционная система Windows
- Python 3.8 или выше
- Права администратора (для удаления программ)

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

Для создания автономного исполняемого файла:

```bash
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

---

## License

This project is licensed under the *MIT License* - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p><em>Made with 🌞 for Windows users</em></p>
</div>