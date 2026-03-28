# installer_src/installer.spec - 安装器打包配置
# 使用方法: pyinstaller installer.spec
block_cipher = None

from PyInstaller.utils.hooks import collect_data_files
pyqt5_datas = collect_data_files('PyQt5', includes=[
    'Qt/plugins/platforms/*',
    'Qt/plugins/imageformats/*',
    'Qt/plugins/styles/*'
])

a = Analysis(
    ['installer.py'],
    pathex=['.'],
    binaries=[],
    datas=pyqt5_datas + [
        ('../dist/课堂点名计时器.exe', '.'),
        ('../pictures', 'pictures'),
        ('../sounds', 'sounds'),
    ],
    hiddenimports=[
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'winreg', 'ctypes', 'ctypes.wintypes',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib','numpy','pandas','tkinter'],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='课堂点名计时器_安装程序',
    debug=False, strip=False,
    upx=True,
    upx_exclude=['qwindows.dll','Qt5Core.dll','Qt5Gui.dll','Qt5Widgets.dll'],
    console=False,
    icon='../pictures/icon.ico',
    uac_admin=True,  # 安装程序需要管理员权限
)
