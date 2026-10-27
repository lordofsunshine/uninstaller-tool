# -*- mode: python ; coding: utf-8 -*-

EXCLUDES = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtConcurrent",
    "PySide6.QtDataVisualization",
    "PySide6.QtDBus",
    "PySide6.QtDesigner",
    "PySide6.QtGraphs",
    "PySide6.QtHelp",
    "PySide6.QtHttpServer",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtXml",
]

DROP_PARTS = (
    "PySide6\\Qt6Network.dll",
    "PySide6\\Qt6Pdf.dll",
    "PySide6\\Qt6Qml.dll",
    "PySide6\\Qt6QmlModels.dll",
    "PySide6\\Qt6QmlWorkerScript.dll",
    "PySide6\\Qt6QmlMeta.dll",
    "PySide6\\Qt6Quick.dll",
    "PySide6\\Qt6QuickControls2.dll",
    "PySide6\\Qt6QuickTemplates2.dll",
    "PySide6\\Qt6QuickWidgets.dll",
    "PySide6\\Qt6OpenGL.dll",
    "PySide6\\Qt6VirtualKeyboard.dll",
    "PySide6\\QtNetwork.pyd",
    "PySide6\\opengl32sw.dll",
    "PySide6\\plugins\\generic\\",
    "PySide6\\plugins\\imageformats\\qpdf.dll",
    "PySide6\\plugins\\platforminputcontexts\\",
    "PySide6\\plugins\\platforms\\qdirect2d.dll",
    "PySide6\\plugins\\platforms\\qminimal.dll",
    "PySide6\\plugins\\platforms\\qoffscreen.dll",
    "PySide6\\plugins\\tls\\",
)


def keep_binary(entry):
    name = entry[0].replace("/", "\\")
    return not any(part in name for part in DROP_PARTS)


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\app_icon.ico', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=1,
)
a.binaries = [item for item in a.binaries if keep_binary(item)]
a.datas = [
    item
    for item in a.datas
    if "PySide6\\translations\\" not in item[0].replace("/", "\\")
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UninstallerTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['assets\\app_icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='UninstallerTool',
)
