# 🗿 Uninstaller Tool

A powerful and user-friendly application for managing and uninstalling programs on Windows.

<img alt="banner" src="https://cdn.glitch.global/64e004e3-d81d-4b3a-9fb1-c899982de83f/b9b742e9-8926-40c1-89d8-0da9618ae1f0.image.png?v=1735136414857">

> [!NOTE]
> The link to download the program: [click](https://github.com/lordofsunshine/uninstaller-tool/releases/download/v.0.0.1/main.exe)

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
   git clone https://github.com/yourusername/uninstaller-tool.git
   ```

2. Navigate to the project directory:
   ```bash
   cd uninstaller-tool
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:

```bash
python uninstaller_tool.py
```

## 🔑 Compiling to Executable

To create a standalone executable file, follow these steps:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Compile the application:
   ```bash
   pyinstaller --onefile --windowed --icon=icon.ico uninstaller_tool.py
   ```

   This will create a single executable file in the `dist` folder.

3. (Optional) To include the icon, make sure you have an `icon.ico` file in the same directory as the script.

## License

This project is licensed under the *MIT License* - see the [LICENSE](LICENSE) file for details.

