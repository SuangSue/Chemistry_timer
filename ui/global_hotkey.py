# ui/global_hotkey.py - Windows 全局热键管理器
import sys
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes
    from PyQt5.QtCore import QAbstractNativeEventFilter, QCoreApplication

    MOD_NONE  = 0x0000
    MOD_ALT   = 0x0001
    MOD_CTRL  = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN   = 0x0008
    WM_HOTKEY = 0x0312

    _VK_MAP = {
        'tab':    0x09, 'space':  0x20, 'return': 0x0D, 'enter': 0x0D,
        'capslock': 0x14,
        'f1':0x70,'f2':0x71,'f3':0x72,'f4':0x73,'f5':0x74,'f6':0x75,
        'f7':0x76,'f8':0x77,'f9':0x78,'f10':0x79,'f11':0x7A,'f12':0x7B,
        'home':0x24,'end':0x23,'pageup':0x21,'pagedown':0x22,
        'insert':0x2D,'delete':0x2E,'backspace':0x08,'escape':0x1B,
        'left':0x25,'up':0x26,'right':0x27,'down':0x28,
        '`':0xC0,'-':0xBD,'=':0xBB,'[':0xDB,']':0xDD,'\\':0xDC,
        ';':0xBA,"'":0xDE,',':0xBC,'.':0xBE,'/':0xBF,
        '0':0x30,'1':0x31,'2':0x32,'3':0x33,'4':0x34,
        '5':0x35,'6':0x36,'7':0x37,'8':0x38,'9':0x39,
    }

    def _parse_hotkey(key_str):
        """解析 'Tab' / 'Ctrl+F1' / 'A' / 'Shift' 等为 (mod, vk)"""
        parts = [p.strip() for p in key_str.split('+')]
        mod = MOD_NONE
        vk  = 0
        for p in parts:
            pl = p.lower()
            if pl == 'ctrl':  mod |= MOD_CTRL
            elif pl == 'alt': mod |= MOD_ALT
            elif pl == 'shift': mod |= MOD_SHIFT
            elif pl == 'win': mod |= MOD_WIN
            elif pl in _VK_MAP: vk = _VK_MAP[pl]
            elif len(p) == 1: vk = ord(p.upper())
        # 单独修饰键作为热键时，vk 取对应虚拟键码
        if vk == 0 and mod == MOD_NONE:
            single = key_str.strip().lower()
            solo_map = {'shift':0x10,'ctrl':0x11,'alt':0x12,'win':0x5B}
            if single in solo_map:
                vk = solo_map[single]
                mod = MOD_NONE
        return mod, vk

    class _NativeFilter(QAbstractNativeEventFilter):
        def __init__(self, callback):
            super().__init__()
            self._callback = callback
        def nativeEventFilter(self, event_type, message):
            if event_type == b'windows_generic_MSG':
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    self._callback(int(msg.wParam))
            return False, 0

    class GlobalHotkey(QObject):
        triggered = pyqtSignal()

        def __init__(self, hotkey_id=1, parent=None):
            super().__init__(parent)
            self._id = hotkey_id
            self._registered = False
            self._mod = MOD_NONE
            self._vk  = 0
            self._enabled = True
            self._filter = _NativeFilter(self._on_hotkey)
            QCoreApplication.instance().installNativeEventFilter(self._filter)

        def set_hotkey(self, key_str):
            self._unregister()
            self._mod, self._vk = _parse_hotkey(key_str)
            if self._vk and self._enabled:
                self._register()

        def set_enabled(self, enabled):
            self._enabled = enabled
            if enabled:
                if self._vk and not self._registered: self._register()
            else:
                self._unregister()

        def _register(self):
            ok = ctypes.windll.user32.RegisterHotKey(None, self._id, self._mod, self._vk)
            self._registered = bool(ok)
            if not ok:
                print(f'RegisterHotKey failed for id={self._id} mod={self._mod} vk={self._vk}')

        def _unregister(self):
            if self._registered:
                ctypes.windll.user32.UnregisterHotKey(None, self._id)
                self._registered = False

        def _on_hotkey(self, hid):
            if hid == self._id and self._enabled:
                self.triggered.emit()

        def __del__(self):
            try: self._unregister()
            except Exception: pass

else:
    # 非 Windows 平台 fallback
    from PyQt5.QtCore import QObject, pyqtSignal

    class GlobalHotkey(QObject):
        triggered = pyqtSignal()
        def __init__(self, hotkey_id=1, parent=None): super().__init__(parent)
        def set_hotkey(self, key_str): pass
        def set_enabled(self, enabled): pass
