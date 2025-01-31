# 🗿 Uninstaller Tool

A powerful and user-friendly application for managing and uninstalling programs on Windows. *This is my first program, I hope for your support.*

<img alt="banner" src="https://cdn.glitch.global/4ae4fbec-cbe7-491c-b8b9-57879c9f0e5d/0aa05300-1d0f-48f5-b4bc-daceafa0209f.image.png?v=1738338009508">

> [!NOTE]
> The link to download the program: [click](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.0.0.2/UninstallerTool.exe)

## Features

- [x] List all installed programs
- [x] Search and filter programs
- [x] Uninstall selected programs
- [x] Silent uninstall option
- [x] Detect and remove leftover files and registry entries
- [x] View detailed program information
- [x] Refresh program list
- [x] Modern and responsive GUI

## Requirements

- Windows operating system
- Python 3.6 or higher
- Required Python libraries (PyQt6, psutil)

To install all required libraries, run:
```bash
pip install PyQt6 psutil
```

## Installation

1. Clone this repository:
  ```bash
   git clone https://github.com/lordofsunshine/uninstaller-tool.git
   ```

2. Navigate to the project directory:
   ```bash
   cd uninstaller-tool
   ```

3. Install the required dependencies:
   ```bash
   Run setup.bat
   ```

## Usage

Run the application:

```bash
python main.py
```

## 🔑 Compiling to Executable

To create a standalone executable file, follow these steps:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Compile the application:
   ```bash
   pyinstaller --onefile --windowed --icon=icon.ico main.py
   ```

   This will create a single executable file in the `dist` folder.

3. (Optional) To include the icon, make sure you have an `icon.ico` file in the same directory as the script.

## License

This project is licensed under the *MIT License* - see the [LICENSE](LICENSE) file for details.

