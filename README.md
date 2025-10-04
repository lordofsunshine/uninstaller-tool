# 🗿 Uninstaller Tool

<div align="center">
  <img alt="banner" src="https://cdn.glitch.global/4ae4fbec-cbe7-491c-b8b9-57879c9f0e5d/0aa05300-1d0f-48f5-b4bc-daceafa0209f.image.png?v=1738338009508">
  
  <p><strong>Powerful and user-friendly application for managing and uninstalling programs on Windows</strong></p>
  
  <p>
    <a href="#english">🇺🇸 English</a> • 
    <a href="#russian">🇷🇺 Русский</a>
  </p>
</div>

---

## 🇺🇸 English

### What's New? 🆕

**Latest Updates:**
- ✅ **Adaptive window sizing** - Works perfectly on small screens
- ✅ **Smart file detection** - More accurate leftover file detection
- ✅ **Administrator rights check** - Automatic restart with admin privileges
- ✅ **Better error handling** - No more crashes, detailed error messages
- ✅ **Improved uninstall process** - Supports all types of uninstallers (MSI, EXE, GUID)
- ✅ **Real-time status updates** - Always know what's happening
- ✅ **Fixed size calculations** - Correct program sizes, no more fake 2TB displays
- ✅ **Enhanced UI** - Responsive buttons that adapt to screen size

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
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

---

## 🇷🇺 Русский

### Что нового? 🆕

**Последние обновления:**
- ✅ **Адаптивные размеры окна** - Отлично работает на маленьких экранах
- ✅ **Умное определение файлов** - Более точное обнаружение остаточных файлов
- ✅ **Проверка прав администратора** - Автоматический перезапуск с правами админа
- ✅ **Улучшенная обработка ошибок** - Никаких крашей, детальные сообщения об ошибках
- ✅ **Улучшенный процесс удаления** - Поддержка всех типов деинсталляторов (MSI, EXE, GUID)
- ✅ **Обновления статуса в реальном времени** - Всегда знайте, что происходит
- ✅ **Исправлены расчеты размеров** - Правильные размеры программ, никаких фальшивых 2ТБ
- ✅ **Улучшенный интерфейс** - Адаптивные кнопки под размер экрана

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
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

---

## License

This project is licensed under the *MIT License* - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p><em>Made with ❤️ for Windows users</em></p>
</div>