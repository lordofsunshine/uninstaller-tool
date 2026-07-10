# 🗿 Uninstaller Tool

<div align="center">
  <img alt="banner" src="https://i.ibb.co/TMNN3sZZ/image.png">
  
  <p><strong>Powerful and user-friendly application for managing and uninstalling programs on Windows</strong></p>
  
  <p>
    <a href="#english">🇺🇸 English</a> • 
    <a href="#russian">🇷🇺 Русский</a>
  </p>
</div>

Download program: https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.0.0.3/UninstallerTool.exe

---

## 🇺🇸 English

### What's New? 🆕

**Latest Updates:**
- ✅ **Safer uninstall commands** - Commands are parsed and started without an unsafe command shell
- ✅ **Reliable MSI and silent removal** - Correct `/I` to `/X` conversion, quiet commands, fallbacks, and restart exit codes
- ✅ **Locked-file cleanup** - Protected files are retried and can be removed safely after the next Windows restart
- ✅ **Safer leftover detection** - System folders, drive roots, links, and unrelated directories are protected
- ✅ **Accurate program data** - Registry duplicates, versions, install locations, dates, and size units are handled correctly
- ✅ **Responsive interface** - Registry loading, file scanning, uninstalling, and cleanup run outside the UI thread
- ✅ **Clearer results** - Cleanup reports removed locations, registry entries, deferred items, and actionable errors separately

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
- ✅ **Безопасный запуск деинсталляторов** - Команды разбираются и запускаются без небезопасной командной оболочки
- ✅ **Надёжное MSI- и тихое удаление** - Исправлены `/I` → `/X`, тихие команды, резервный запуск и коды перезагрузки
- ✅ **Очистка занятых файлов** - Защищённые файлы удаляются повторно или безопасно ставятся на удаление после перезапуска Windows
- ✅ **Безопасный поиск остатков** - Системные папки, корни дисков, ссылки и посторонние каталоги защищены от удаления
- ✅ **Точные данные программ** - Корректно обрабатываются дубликаты реестра, версии, пути, даты и единицы размера
- ✅ **Отзывчивый интерфейс** - Чтение реестра, поиск файлов, удаление и очистка выполняются вне UI-потока
- ✅ **Понятный результат очистки** - Отдельно показаны удалённые пути, записи реестра, отложенные объекты и ошибки

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
  <p><em>Made with ❤️ for Windows users</em></p>
</div>