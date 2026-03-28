from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSlider, QCheckBox, QLineEdit,
    QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

SLIDER_DAY = (
    'QSlider::groove:horizontal{height:6px;border-radius:3px;background:rgba(200,190,155,0.40);}'
    'QSlider::handle:horizontal{width:16px;height:16px;margin:-5px 0;border-radius:8px;'
    'background:#8a7a50;border:2px solid rgba(255,255,250,0.90);}'
    'QSlider::sub-page:horizontal{background:rgba(138,122,80,0.65);border-radius:3px;}'
)
SLIDER_NIGHT = (
    'QSlider::groove:horizontal{height:6px;border-radius:3px;background:rgba(80,75,110,0.40);}'
    'QSlider::handle:horizontal{width:16px;height:16px;margin:-5px 0;border-radius:8px;'
    'background:#9080c0;border:2px solid rgba(220,215,255,0.90);}'
    'QSlider::sub-page:horizontal{background:rgba(120,108,180,0.65);border-radius:3px;}'
)
SLIDER_STYLE = SLIDER_DAY


class HotkeyButton(QPushButton):
    """点击后进入录键状态，按下任意键完成录制"""
    hotkey_recorded = __import__('PyQt5.QtCore', fromlist=['pyqtSignal']).pyqtSignal(str)

    def __init__(self, text='Tab', parent=None):
        super().__init__(text, parent)
        self._recording = False
        self._key_str = text
        self.setCursor(__import__('PyQt5.QtCore', fromlist=['Qt']).Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self.clicked.connect(self._start_recording)

    def _start_recording(self):
        self._recording = True
        self.setText('请按键...')
        self.setStyleSheet(self.styleSheet() + 'border:2px solid #c08030;')
        self.grabKeyboard()

    def event(self, e):
        from PyQt5.QtCore import QEvent
        if self._recording and e.type() == QEvent.KeyPress:
            self._handle_key(e)
            return True
        return super().event(e)

    def keyPressEvent(self, event):
        if self._recording: self._handle_key(event)
        else: super().keyPressEvent(event)

    def _handle_key(self, event):
        from PyQt5.QtCore import Qt
        key = event.key(); mod = event.modifiers()
        key_map = {
            Qt.Key_Tab:'Tab', Qt.Key_Space:'Space', Qt.Key_Return:'Return',
            Qt.Key_CapsLock:'CapsLock',
            Qt.Key_Control:'Ctrl', Qt.Key_Alt:'Alt',
            Qt.Key_Shift:'Shift', Qt.Key_Meta:'Win',
            Qt.Key_F1:'F1',Qt.Key_F2:'F2',Qt.Key_F3:'F3',Qt.Key_F4:'F4',
            Qt.Key_F5:'F5',Qt.Key_F6:'F6',Qt.Key_F7:'F7',Qt.Key_F8:'F8',
            Qt.Key_F9:'F9',Qt.Key_F10:'F10',Qt.Key_F11:'F11',Qt.Key_F12:'F12',
            Qt.Key_Home:'Home',Qt.Key_End:'End',Qt.Key_Insert:'Insert',
            Qt.Key_Delete:'Delete',Qt.Key_Escape:'Escape',
            Qt.Key_PageUp:'PageUp',Qt.Key_PageDown:'PageDown',
            Qt.Key_Left:'Left',Qt.Key_Right:'Right',Qt.Key_Up:'Up',Qt.Key_Down:'Down',
            Qt.Key_QuoteLeft:'`',Qt.Key_Minus:'-',Qt.Key_Equal:'=',
            Qt.Key_BracketLeft:'[',Qt.Key_BracketRight:']',Qt.Key_Backslash:'\\',
            Qt.Key_Semicolon:';',Qt.Key_Apostrophe:"'",
            Qt.Key_Comma:',',Qt.Key_Period:'.',Qt.Key_Slash:'/',
        }
        k = key_map.get(key, '')
        if not k:
            if Qt.Key_A <= key <= Qt.Key_Z: k = chr(key)
            elif Qt.Key_0 <= key <= Qt.Key_9: k = chr(key)
        if k in ('Ctrl','Alt','Shift','Win'):
            self._key_str = k
        elif k:
            parts = []
            if mod & Qt.ControlModifier and k != 'Ctrl': parts.append('Ctrl')
            if mod & Qt.AltModifier and k != 'Alt': parts.append('Alt')
            if mod & Qt.ShiftModifier and k != 'Shift': parts.append('Shift')
            parts.append(k)
            self._key_str = '+'.join(parts)
        else:
            return
        self.releaseKeyboard(); self._recording = False
        self.setText(self._key_str); self._restore_style()
        self.hotkey_recorded.emit(self._key_str)

    def _restore_style(self): pass
    def get_key(self): return self._key_str
    def set_key(self, k): self._key_str=k; self.setText(k)

CB_DAY = (
    'QCheckBox::indicator{width:20px;height:20px;border-radius:5px;'
    'border:1.5px solid rgba(138,122,80,0.60);background:rgba(255,255,250,0.70);}'
    'QCheckBox::indicator:checked{background:rgba(138,122,80,0.85);'
    'border:1.5px solid rgba(138,122,80,0.80);}'
)
CB_NIGHT = (
    'QCheckBox::indicator{width:20px;height:20px;border-radius:5px;'
    'border:1.5px solid rgba(120,108,180,0.60);background:rgba(50,45,75,0.70);}'
    'QCheckBox::indicator:checked{background:rgba(110,98,170,0.85);'
    'border:1.5px solid rgba(130,118,190,0.80);}'
)


class SettingsPage(QWidget):
    opacity_changed      = pyqtSignal(float)
    theme_toggle         = pyqtSignal()
    anim_speed_changed   = pyqtSignal(int)
    silent_start_changed = pyqtSignal(bool)
    pick_speed_changed   = pyqtSignal(int)
    hotkey_changed       = pyqtSignal(str)
    fast_mode_changed    = pyqtSignal(bool)
    async_pick_changed     = pyqtSignal(bool)
    async_duration_changed = pyqtSignal(float)  # 异步窗口显示秒数

    def __init__(self, parent=None):
        super().__init__(parent)
        self._night = False; self._anim_combo = None
        self._frames=[]; self._lbl_sec=[]; self._lbl_row=[]; self._lbl_val=[]
        self._sliders=[]; self._checks=[]; self._plain_btns=[]; self._line_edits=[]
        self._hotkey_btns=[]
        self._build_ui()

    def _section(self, title):
        f = QFrame()
        f.setStyleSheet('QFrame{background:rgba(255,255,250,0.52);border-radius:14px;border:1px solid rgba(210,200,165,0.40);}')
        self._frames.append(f)
        lay = QVBoxLayout(f); lay.setContentsMargins(16,12,16,12); lay.setSpacing(10)
        lbl = QLabel(title)
        lbl.setStyleSheet('font-size:13px;font-weight:700;color:#5a5030;border:none;background:transparent;')
        self._lbl_sec.append(lbl); lay.addWidget(lbl)
        return f, lay

    def _row_lbl(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet('font-size:12px;color:#3a3220;border:none;background:transparent;')
        self._lbl_row.append(lbl); return lbl

    def _val_lbl(self, text, width=34):
        lbl = QLabel(text); lbl.setFixedWidth(width)
        lbl.setStyleSheet('font-size:12px;color:#7a7050;border:none;background:transparent;')
        self._lbl_val.append(lbl); return lbl

    def _reset_btn(self):
        btn = QPushButton('\u6062\u590d\u9ed8\u8ba4'); btn.setCursor(Qt.PointingHandCursor); btn.setFixedHeight(24)
        btn.setStyleSheet('QPushButton{background:rgba(200,190,155,0.35);color:#5a5030;border:1px solid rgba(200,190,155,0.55);border-radius:6px;font-size:11px;padding:0 8px;}QPushButton:hover{background:rgba(200,190,155,0.65);}')
        self._plain_btns.append(btn); return btn

    def _checkbox(self):
        cb = QCheckBox(); cb.setStyleSheet(CB_DAY); self._checks.append(cb); return cb

    def _slider(self, lo, hi, val, width=120):
        sl = QSlider(Qt.Horizontal); sl.setRange(lo,hi); sl.setValue(val); sl.setFixedWidth(width)
        sl.setStyleSheet(SLIDER_DAY); self._sliders.append(sl); return sl

    def _line_edit(self, text, width=80):
        le = QLineEdit(text); le.setFixedSize(width,26)
        le.setStyleSheet('QLineEdit{background:rgba(255,253,245,0.90);color:#2c2510;border:1px solid rgba(200,190,155,0.65);border-radius:6px;font-size:12px;padding:0 6px;}')
        self._line_edits.append(le); return le

    def _hotkey_btn(self, text='Tab', width=90):
        btn = HotkeyButton(text)
        btn.setFixedWidth(width)
        btn.setStyleSheet('QPushButton{background:rgba(255,253,245,0.90);color:#2c2510;border:1px solid rgba(200,190,155,0.65);border-radius:6px;font-size:12px;padding:0 6px;font-family:"Microsoft YaHei";}QPushButton:hover{background:rgba(248,240,220,0.95);}')
        self._hotkey_btns.append(btn); return btn

    def _build_ui(self):
        # 外层：QScrollArea 包裹内容
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:6px;background:transparent;border-radius:3px;}"
            "QScrollBar::handle:vertical{background:rgba(180,168,130,0.55);border-radius:3px;min-height:30px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        outer_vbox = QVBoxLayout(self)
        outer_vbox.setContentsMargins(0,0,0,0)
        outer_vbox.addWidget(scroll)
        scroll.setWidget(container)
        outer = QHBoxLayout(container); outer.setContentsMargins(16,14,16,14); outer.setSpacing(12)
        lc = QVBoxLayout(); lc.setSpacing(12)

        # 外观
        af, al = self._section('\u5916\u89c2\u8bbe\u7f6e')
        tr = QHBoxLayout(); tr.addWidget(self._row_lbl('\u65e5/\u591c\u95f4\u6a21\u5f0f')); tr.addStretch()
        self._theme_btn = QPushButton('\U0001f319 \u591c\u95f4'); self._theme_btn.setCursor(Qt.PointingHandCursor); self._theme_btn.setFixedHeight(28)
        self._theme_btn.setStyleSheet('QPushButton{background:rgba(80,72,110,0.55);color:#d8d0f8;border:1px solid rgba(100,90,150,0.60);border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(100,90,140,0.75);}')
        self._theme_btn.clicked.connect(self._on_theme_toggle); tr.addWidget(self._theme_btn); al.addLayout(tr)
        or_ = QHBoxLayout(); or_.addWidget(self._row_lbl('\u900f\u660e\u5ea6')); or_.addStretch()
        self._opac_slider = self._slider(40,100,95); self._opac_val = self._val_lbl('95%',34)
        rb1 = self._reset_btn(); rb1.clicked.connect(lambda: self._opac_slider.setValue(95))
        self._opac_slider.valueChanged.connect(self._on_opacity)
        or_.addWidget(self._opac_slider); or_.addWidget(self._opac_val); or_.addWidget(rb1); al.addLayout(or_)
        lc.addWidget(af)

        # 行为
        bf, bl = self._section('\u884c\u4e3a\u8bbe\u7f6e')
        ar = QHBoxLayout(); ar.addWidget(self._row_lbl('\u52a8\u753b\u901f\u5ea6')); ar.addStretch()
        self._anim_slider = self._slider(0,600,250); self._anim_val = self._val_lbl('250ms',42)
        rb2 = self._reset_btn(); rb2.clicked.connect(lambda: self._anim_slider.setValue(250))
        self._anim_slider.valueChanged.connect(self._on_anim_speed)
        ar.addWidget(self._anim_slider); ar.addWidget(self._anim_val); ar.addWidget(rb2); bl.addLayout(ar)
        pr = QHBoxLayout(); pr.addWidget(self._row_lbl('\u62bd\u53d6\u901f\u5ea6')); pr.addStretch()
        self._pick_slider = self._slider(0,100,0); self._pick_val = self._val_lbl('\u7acb\u5373',42)
        rb3 = self._reset_btn(); rb3.clicked.connect(lambda: self._pick_slider.setValue(0))
        self._pick_slider.valueChanged.connect(self._on_pick_speed)
        pr.addWidget(self._pick_slider); pr.addWidget(self._pick_val); pr.addWidget(rb3); bl.addLayout(pr)
        sr = QHBoxLayout(); sr.addWidget(self._row_lbl('\u9759\u9ed8\u542f\u52a8')); sr.addStretch()
        self._silent_cb = self._checkbox()
        self._silent_cb.toggled.connect(self.silent_start_changed)
        self._silent_cb.toggled.connect(lambda v: __import__('utils.config',fromlist=['set']).set('silent_start',v))
        sr.addWidget(self._silent_cb); bl.addLayout(sr)
        fmr = QHBoxLayout(); fmr.addWidget(self._row_lbl('\u5feb\u901f\u6a21\u5f0f (\u963b\u65ad\u6240\u6709\u52a8\u753b)')); fmr.addStretch()
        self._fast_cb = self._checkbox()
        self._fast_cb.toggled.connect(self.fast_mode_changed)
        self._fast_cb.toggled.connect(lambda v: __import__('utils.config',fromlist=['set']).set('fast_mode',v))
        fmr.addWidget(self._fast_cb); bl.addLayout(fmr)
        lc.addWidget(bf)

        # 抽签
        pf, pl = self._section('\u62bd\u7b7e\u8bbe\u7f6e')
        # 异步抽签开关
        aqr = QHBoxLayout(); aqr.addWidget(self._row_lbl('\u5f02\u6b65\u62bd\u7b7e')); aqr.addStretch()
        self._async_pick_cb = self._checkbox(); self._async_pick_cb.setChecked(True)
        self._async_pick_cb.toggled.connect(self.async_pick_changed)
        self._async_pick_cb.toggled.connect(lambda v: __import__('utils.config',fromlist=['set']).set('async_pick',v))
        aqr.addWidget(self._async_pick_cb); pl.addLayout(aqr)
        # 快捷键录键按钮
        hkr = QHBoxLayout(); hkr.addWidget(self._row_lbl('\u62bd\u7b7e\u5feb\u6377\u952e')); hkr.addStretch()
        self._hotkey_btn_w = self._hotkey_btn('Tab', 90)
        self._hotkey_btn_w.hotkey_recorded.connect(self._on_hotkey_changed)
        hk_reset = QPushButton('恢复默认'); hk_reset.setCursor(Qt.PointingHandCursor); hk_reset.setFixedHeight(28)
        hk_reset.setStyleSheet('QPushButton{background:rgba(200,190,155,0.35);color:#5a5030;border:1px solid rgba(200,190,155,0.55);border-radius:6px;font-size:11px;padding:0 8px;}QPushButton:hover{background:rgba(200,190,155,0.65);}')
        hk_reset.clicked.connect(lambda: (self._hotkey_btn_w.set_key('Tab'), self._on_hotkey_changed('Tab')))
        self._plain_btns.append(hk_reset)
        hkr.addWidget(self._hotkey_btn_w); hkr.addWidget(hk_reset); pl.addLayout(hkr)
        # 异步窗口显示时间
        dr = QHBoxLayout(); dr.addWidget(self._row_lbl('异步窗口显示时间')); dr.addStretch()
        self._dur_slider = self._slider(50, 500, 175)
        self._dur_val = self._val_lbl('1.75s', 40)
        rb_dur = self._reset_btn(); rb_dur.clicked.connect(lambda: self._dur_slider.setValue(175))
        self._dur_slider.valueChanged.connect(self._on_dur_changed)
        dr.addWidget(self._dur_slider); dr.addWidget(self._dur_val); dr.addWidget(rb_dur)
        pl.addLayout(dr)
        lc.addWidget(pf)
        lc.addStretch(); outer.addLayout(lc,3)

        rc = QVBoxLayout(); rc.setSpacing(12)
        ab_f, ab_l = self._section('\u5173\u4e8e')
        ab_l.addWidget(self._row_lbl('\u8bfe\u5802\u70b9\u540d\u8ba1\u65f6\u5668'))
        ab_l.addWidget(self._row_lbl('V6.0')); ab_l.addSpacing(8)
        ab_l.addWidget(self._row_lbl('\u7279\u522b\u9e23\u8c22'))
        ab_l.addWidget(self._row_lbl('Claude\u7b49\u7f16\u7a0b\u6307\u5bfc'))
        ab_l.addWidget(self._row_lbl('\u5236\u4f5c\u4e0e\u6539\u9032'))
        ab_l.addWidget(self._row_lbl('ShuangSue \u00a9 2026'))
        ab_l.addWidget(self._row_lbl('\u6d4b\u8bd5\u73ed\u7ea7\uff1a\u9ad8\u4e8c\u5341\u4e00\u73ed'))
        ab_l.addWidget(self._row_lbl('2024-2026'))
        rc.addWidget(ab_f); rc.addStretch(); outer.addLayout(rc,2)
        self._load_settings()


    def _load_settings(self):
        from utils import config as cfg
        self._opac_slider.blockSignals(True); self._opac_slider.setValue(int(cfg.get('opacity',95))); self._opac_slider.blockSignals(False)
        self._opac_val.setText(f"{int(cfg.get('opacity',95))}%")
        self._anim_slider.blockSignals(True); self._anim_slider.setValue(int(cfg.get('anim_speed',250))); self._anim_slider.blockSignals(False)
        self._anim_val.setText(f"{int(cfg.get('anim_speed',250))}ms")
        pv=int(cfg.get('pick_speed',0)); self._pick_slider.blockSignals(True); self._pick_slider.setValue(pv); self._pick_slider.blockSignals(False)
        self._pick_val.setText('立即' if pv==0 else str(pv))
        self._silent_cb.blockSignals(True); self._silent_cb.setChecked(bool(cfg.get('silent_start',False))); self._silent_cb.blockSignals(False)
        self._fast_cb.blockSignals(True); self._fast_cb.setChecked(bool(cfg.get('fast_mode',False))); self._fast_cb.blockSignals(False)
        self._async_pick_cb.blockSignals(True); self._async_pick_cb.setChecked(bool(cfg.get('async_pick',True))); self._async_pick_cb.blockSignals(False)
        dv=int(cfg.get('async_duration',1.75)*100); self._dur_slider.blockSignals(True); self._dur_slider.setValue(dv); self._dur_slider.blockSignals(False)
        self._dur_val.setText(f"{dv/100:.2f}s")
        self._hotkey_btn_w.set_key(cfg.get('hotkey','Tab'))

    def _on_theme_toggle(self):
        self._night = not self._night
        if self._night:
            self._theme_btn.setText('\u2600\ufe0f \u65e5\u95f4')
            self._theme_btn.setStyleSheet('QPushButton{background:rgba(210,190,100,0.55);color:#3a3000;border:1px solid rgba(210,190,80,0.70);border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(220,200,110,0.75);}')
        else:
            self._theme_btn.setText('\U0001f319 \u591c\u95f4')
            self._theme_btn.setStyleSheet('QPushButton{background:rgba(80,72,110,0.55);color:#d8d0f8;border:1px solid rgba(100,90,150,0.60);border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(100,90,140,0.75);}')
        self.theme_toggle.emit()
        from utils import config as cfg; cfg.set('night_mode', self._night)

    def _on_opacity(self, v):
        self._opac_val.setText(f'{v}%'); self.opacity_changed.emit(v/100.0)
        from utils import config as cfg; cfg.set('opacity', v)
    def _on_anim_speed(self, v):
        self._anim_val.setText(f'{v}ms'); self.anim_speed_changed.emit(v)
        from utils import config as cfg; cfg.set('anim_speed', v)
    def _on_pick_speed(self, v):
        self._pick_val.setText('\u7acb\u5373' if v==0 else str(v))
        self.pick_speed_changed.emit(v)
        from utils import config as cfg; cfg.set('pick_speed', v)
    def _on_dur_changed(self, v):
        secs = v / 100.0
        self._dur_val.setText(f'{secs:.2f}s')
        self.async_duration_changed.emit(secs)
        from utils import config as cfg; cfg.set('async_duration', secs)

    def get_async_duration(self):
        return getattr(self, '_dur_slider', None) and self._dur_slider.value() / 100.0 or 1.75

    def _on_hotkey_changed(self, key=None):
        if key is None: key = self._hotkey_btn_w.get_key()
        self.hotkey_changed.emit(key or 'Tab')
        from utils import config as cfg; cfg.set('hotkey', key or 'Tab')
    def is_silent_start(self): return self._silent_cb.isChecked()
    def get_pick_speed(self): return self._pick_slider.value()
    def get_hotkey(self): return self._hotkey_btn_w.get_key() if hasattr(self,'_hotkey_btn_w') else 'Tab'
    def is_fast_mode(self): return self._fast_cb.isChecked()

    def apply_night(self, night):
        self._night = night; n = night
        frame_st = ('QFrame{background:rgba(38,34,52,0.60);border-radius:14px;border:1px solid rgba(80,75,110,0.50);}' if n else
                    'QFrame{background:rgba(255,255,250,0.52);border-radius:14px;border:1px solid rgba(210,200,165,0.40);}')
        lbl_sec = ('font-size:13px;font-weight:700;color:#c0b8e8;border:none;background:transparent;' if n else
                   'font-size:13px;font-weight:700;color:#5a5030;border:none;background:transparent;')
        lbl_row = ('font-size:12px;color:#a0a8d8;border:none;background:transparent;' if n else
                   'font-size:12px;color:#3a3220;border:none;background:transparent;')
        lbl_val = ('font-size:12px;color:#9090b8;border:none;background:transparent;' if n else
                   'font-size:12px;color:#7a7050;border:none;background:transparent;')
        btn_st  = ('QPushButton{background:rgba(70,62,110,0.55);color:#e0d8f8;border:1px solid rgba(100,90,150,0.65);border-radius:6px;font-size:11px;padding:0 8px;}QPushButton:hover{background:rgba(90,80,140,0.75);}' if n else
                   'QPushButton{background:rgba(200,190,155,0.35);color:#5a5030;border:1px solid rgba(200,190,155,0.55);border-radius:6px;font-size:11px;padding:0 8px;}QPushButton:hover{background:rgba(200,190,155,0.65);}')
        le_st   = ('QLineEdit{background:rgba(38,34,60,0.90);color:#e0d8f8;border:1px solid rgba(100,90,150,0.65);border-radius:6px;font-size:12px;padding:0 6px;}' if n else
                   'QLineEdit{background:rgba(255,253,245,0.90);color:#2c2510;border:1px solid rgba(200,190,155,0.65);border-radius:6px;font-size:12px;padding:0 6px;}')
        for w in self._frames:      w.setStyleSheet(frame_st)
        for w in self._lbl_sec:     w.setStyleSheet(lbl_sec)
        for w in self._lbl_row:     w.setStyleSheet(lbl_row)
        for w in self._lbl_val:     w.setStyleSheet(lbl_val)
        for w in self._sliders:     w.setStyleSheet(SLIDER_NIGHT if n else SLIDER_DAY)
        for w in self._checks:      w.setStyleSheet(CB_NIGHT if n else CB_DAY)
        for w in self._plain_btns:  w.setStyleSheet(btn_st)
        for w in self._line_edits:  w.setStyleSheet(le_st)
        hk_st = ('QPushButton{background:rgba(38,34,60,0.90);color:#e0d8f8;border:1px solid rgba(100,90,150,0.65);border-radius:6px;font-size:12px;padding:0 6px;}' if n else
                 'QPushButton{background:rgba(255,253,245,0.90);color:#2c2510;border:1px solid rgba(200,190,155,0.65);border-radius:6px;font-size:12px;padding:0 6px;}')
        for w in self._hotkey_btns: w.setStyleSheet(hk_st)
