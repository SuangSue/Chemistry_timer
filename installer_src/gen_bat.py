import os

lines = [
    '@echo off',
    'chcp 936 >nul',
    'echo === Build Installer ===',
    'echo.',
    'echo [1/3] Building main app...',
    'pyinstaller rollcall.spec',
    'if errorlevel 1 ( echo FAILED & pause & exit /b 1 )',
    'echo Done.',
    'echo.',
    'echo [2/3] Building installer...',
    'pyinstaller --onefile --windowed'
    ' --icon=installer_src\\icon.ico'
    ' --name=ClassTimerSetup'
    ' "--add-data=dist\\ClassTimer.exe;."'
    ' "--add-data=pictures;pictures"'
    ' "--add-data=sounds;sounds"'
    ' "--add-data=installer_src\\icon.ico;."'
    ' installer_src\\installer.py',
    'if errorlevel 1 ( echo FAILED & pause & exit /b 1 )',
    'echo Done.',
    'echo.',
    'echo [3/3] Preparing release...',
    'if not exist release mkdir release',
    'copy /y dist\\ClassTimerSetup.exe release\\ClassTimerSetup.exe',
    'echo.',
    'echo Done! Output: release\\ClassTimerSetup.exe',
    'start explorer release',
    'pause',
]

out = '\r\n'.join(lines) + '\r\n'
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build_installer.bat')
with open(dst, 'wb') as f:
    f.write(out.encode('ascii'))
print('OK:', os.path.abspath(dst))
