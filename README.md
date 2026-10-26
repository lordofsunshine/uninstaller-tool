# 🗿 Uninstaller Tool

<div align="center">
  <img alt="banner" src="https://i.postimg.cc/VL6RQQ1p/image.png">
  
  <p><strong>Powerful and user-friendly application for managing and uninstalling programs on Windows</strong></p>
  
  <p>
    <a href="#english">🇺🇸 English</a> • 
    <a href="#russian">🇷🇺 Русский</a>
  </p>
</div>

Download program (Скачать программу): https://github.com/lordofsunshine/uninstaller-tool/releases/download/v1.0.0/UninstallerTool.exe

---

## 🇺🇸 English

### What's New? 🆕

**Version 1.0.0**

🚀 **Faster and more stable**
- The program list appears immediately: regular desktop applications are shown first, while Microsoft Store apps load in the background and are cached, so startup no longer takes as long.
- Long lists no longer slow the app down: scrolling and searching stay smooth even with hundreds of installed applications.
- Name-based search updates without delay and no longer freezes while you type.

🛡 **Safer operation**
- Windows system folders are better protected: the app will never touch the Windows or System32 folders, or drive roots.
- Registry entries are removed only after a backup is created as a `.reg` file, which can be restored if needed.
- Junctions and symbolic links are detected correctly and are not followed when searching or calculating folder sizes.

🧽 **Cleaner removal**
- Leftover-file scanning runs in the background with progress updates and always finishes cleanly, even if an error occurs; the buttons become active again afterward.
- Leftover searches have a time limit and will not leave the app unresponsive.
- Folder sizes are calculated in the background and cached, making disk-space analysis faster on subsequent runs.

🖥 **Sharper visuals**
- Icons and graphics are sharper on high-resolution displays with 150-200% scaling.
- Application icons are correctly extracted from `.exe` and `.dll` resources and cached.

⚙ **Convenience and accessibility**
- Settings persist between runs, including window size and position, silent-uninstall mode, and sorting.
- Administrator privileges are no longer required just to view the program list; they are requested only when uninstalling.
- Keyboard navigation and accessibility support, including screen readers, have been improved.

🔧 **Fixes**
- Uninstall errors no longer leave the app stuck: failures at each step are logged, and buttons and statuses are always reset to a normal state.
- Uninstaller exit codes are handled correctly. MSI codes `3010` and `1641` are treated as successful results that require a restart.
- `.bat` and `.cmd` scripts now run correctly.
- Running instances of the app are detected correctly, including secondary instances.
- PowerShell is located through the system path, including when running with elevated privileges.
- Removing an already-running uninstaller and running operations at the same time no longer cause conflicts.
- Invalid paths such as `C:\` are handled correctly when checking application folders.
- The window cannot be closed mid-operation: it stays open until uninstalling or cleanup has finished.
- Checkboxes are disabled during uninstalling so the selection cannot be changed accidentally.
- Error messages now show the path to the log file immediately.

🧱 **For developers**
- The code is split into modules for the core functionality (security, leftover scanning, and uninstalling), data models, controllers, UI, and workers.
- Typed models (`Program`, `Leftovers`, `RemovalResult`, and `UninstallResult`) replace dictionaries, and type annotations have been added.
- The app version has a single source of truth in `app/version.py`; `version_info.txt` is generated automatically and checked in CI.
- Dead and duplicate code has been removed, and registry-search logic now uses a single indexed snapshot.

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

To create a standalone executable:

```bash
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

---

## 🇷🇺 Русский

### Что нового? 🆕

**Версия 1.0.0**

🚀 **Стало быстрее и стабильнее**
- Список программ открывается сразу: сначала показываются обычные приложения, а приложения Microsoft Store подгружаются в фоне и кэшируются, поэтому запуск больше не занимает столько времени.
- Длинные списки больше не замедляют программу: прокрутка и поиск работают плавно даже при сотнях установленных приложений.
- Поиск по названию обновляется без задержек и не подвисает во время ввода.

🛡 **Безопаснее**
- Системные папки Windows защищены надёжнее: программа не затрагивает папки Windows и System32, а также корни дисков.
- Записи реестра удаляются только после создания резервной копии в формате `.reg`, которую можно восстановить при необходимости.
- Папки-ссылки (junction и symbolic link) распознаются корректно, и программа не переходит по ним при поиске или подсчёте размеров папок.

🧽 **Чище после удаления**
- Поиск остаточных файлов выполняется в фоне с отображением прогресса и всегда корректно завершается, даже при ошибке; после этого кнопки снова становятся активными.
- Для поиска остатков установлен лимит времени, поэтому он не подвешивает программу.
- Размеры папок рассчитываются в фоне и кэшируются, благодаря чему анализ диска быстрее открывается при повторных запусках.

🖥 **Чётче изображение**
- Иконки и графика стали чётче на экранах с высоким разрешением и масштабированием 150-200%.
- Иконки приложений корректно извлекаются из ресурсов файлов `.exe` и `.dll`, а затем кэшируются.

⚙ **Удобство и доступность**
- Настройки сохраняются между запусками: размер и положение окна, режим тихого удаления и сортировка.
- Права администратора больше не нужны для просмотра списка программ: они запрашиваются только при удалении.
- Улучшены клавиатурная навигация и поддержка средств доступности, включая экранные дикторы.

🔧 **Исправления**
- Ошибки при удалении больше не оставляют программу в зависшем состоянии: сбой каждого шага записывается в лог, а кнопки и статусы возвращаются в нормальное состояние.
- Корректно обрабатываются коды завершения деинсталляторов. Коды MSI `3010` и `1641` считаются успешным завершением с необходимостью перезагрузки.
- Скрипты `.bat` и `.cmd` теперь запускаются корректно.
- Запущенные копии программы определяются правильно, включая дополнительные экземпляры.
- PowerShell ищется через системный путь, в том числе при запуске с повышенными правами.
- Удаление уже работающего деинсталлятора и одновременное выполнение операций больше не конфликтуют.
- Некорректные пути, например `C:\`, правильно обрабатываются при проверке папок программы.
- Окно нельзя закрыть во время выполнения операции: оно остаётся открытым, пока удаление или очистка не завершатся.
- Во время удаления флажки блокируются, чтобы выбор программ нельзя было случайно изменить.
- В сообщении об ошибке сразу указывается путь к лог-файлу.

🧱 **Для разработчиков**
- Код разделён на модули: ядро (безопасность, поиск остатков и удаление), модели данных, контроллеры, интерфейс и рабочие потоки.
- Вместо словарей используются типизированные модели (`Program`, `Leftovers`, `RemovalResult`, `UninstallResult`); добавлены аннотации типов.
- Версия приложения задаётся в одном месте (`app/version.py`); файл `version_info.txt` генерируется автоматически, а версия проверяется в CI.
- Удалён неиспользуемый и дублирующийся код, а логика поиска по реестру объединена в один индексированный снимок.

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
