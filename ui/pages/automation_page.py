import json
from utils import config as cfg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QComboBox, QLineEdit, QFileDialog,
    QSizePolicy, QStackedWidget, QSpinBox, QTimeEdit, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTime, QTimer, QDateTime
from PyQt5.QtGui import QFont, QPainter, QColor
import subprocess, os, webbrowser

YHEI = 'Microsoft YaHei'

TRIGGERS = [
    ('\u542f\u52a8\u65f6',                   'startup'),
    ('\u62bd\u7b7e\u540e',                   'after_pick'),
    ('\u6b63\u8ba1\u65f6\u5f00\u59cb\u540e', 'after_stopwatch'),
    ('\u5012\u8ba1\u65f6\u7ed3\u675f\u540e', 'after_countdown'),
    ('\u5012\u8ba1\u65f6\u5269\u4f59 N \u79d2','countdown_remain'),
    ('\u65f6\u95f4\u4e3a\u6307\u5b9a\u65f6\u523b','at_time'),
    ('\u65f6\u95f4\u4e3a\u6574\u70b9\u65f6',  'at_hour'),
    ('\u6bcf\u9694 N \u5206\u949f',          'every_n_min'),
    ('\u7a97\u53e3\u663e\u793a\u65f6',        'on_show'),
    ('\u7a97\u53e3\u9690\u85cf\u65f6',        'on_hide'),
]

ACTIONS = [
    ('\u7b49\u5f85 N \u79d2',                 'wait'),
    ('\u6267\u884c CMD \u547d\u4ee4',         'cmd'),
    ('\u8fd0\u884c\u53ef\u6267\u884c\u7a0b\u5e8f','run'),
    ('\u663e\u793a\u5f39\u7a97\u63d0\u793a',  'notify'),
    ('\u5207\u6362\u4e3b\u9898',              'toggle_theme'),
    ('\u62bd\u53d6\u4e00\u540d\u5b66\u751f',  'pick_one'),
    ('\u6253\u5f00\u7f51\u5740',              'open_url'),
    ('\u590d\u5236\u6587\u5b57\u5230\u526a\u8d34\u677f','copy_text'),
]

SC   = 'QComboBox{background:rgba(255,253,245,0.90);color:#3a3220;border:1px solid rgba(200,190,155,0.65);border-radius:6px;padding:2px 8px;font-size:12px;}QComboBox::drop-down{border:none;}'
SE   = 'QLineEdit{background:rgba(255,253,245,0.90);color:#3a3220;border:1px solid rgba(200,190,155,0.65);border-radius:6px;padding:2px 6px;font-size:12px;}'
SSP  = 'QSpinBox{background:rgba(255,253,245,0.90);color:#3a3220;border:1px solid rgba(200,190,155,0.65);border-radius:6px;padding:2px 6px;font-size:12px;}'
STE  = 'QTimeEdit{background:rgba(255,253,245,0.90);color:#3a3220;border:1px solid rgba(200,190,155,0.65);border-radius:6px;padding:2px 6px;font-size:12px;}'
SDEL = 'QPushButton{background:rgba(220,180,160,0.45);color:#8a4030;border:none;border-radius:5px;font-size:12px;}QPushButton:hover{background:rgba(220,150,130,0.70);}'
SAT  = 'QPushButton{background:rgba(200,190,155,0.40);color:#5a5030;border:1px solid rgba(200,190,155,0.60);border-radius:7px;font-size:12px;}QPushButton:hover{background:rgba(200,190,155,0.68);}'
SAA  = 'QPushButton{background:rgba(138,122,80,0.45);color:#fff8e8;border:1px solid rgba(138,122,80,0.65);border-radius:7px;font-size:12px;}QPushButton:hover{background:rgba(138,122,80,0.70);}'
SFB  = 'QPushButton{background:rgba(200,190,155,0.45);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:6px;font-size:11px;padding:0 8px;}QPushButton:hover{background:rgba(200,190,155,0.72);}'


class TriggerRow(QFrame):
    removed = pyqtSignal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('QFrame{background:rgba(248,244,232,0.70);border-radius:9px;border:1px solid rgba(210,200,165,0.45);}')
        lay = QHBoxLayout(self); lay.setContentsMargins(10,6,8,6); lay.setSpacing(6)
        lbl = QLabel('\u5f53'); lbl.setStyleSheet('color:#6b6040;font-size:12px;font-weight:700;border:none;background:transparent;'); lay.addWidget(lbl)
        self._combo = QComboBox()
        for label,_ in TRIGGERS: self._combo.addItem(label)
        self._combo.setStyleSheet(SC); self._combo.currentIndexChanged.connect(self._on_change); self._combo.currentIndexChanged.connect(self._on_data_changed); lay.addWidget(self._combo,1)
        self._spin = QSpinBox(); self._spin.setRange(1,600); self._spin.setValue(5)
        self._spin.setFixedWidth(72); self._spin.setStyleSheet(SSP); self._spin.hide(); lay.addWidget(self._spin)
        self._time_edit = QTimeEdit(); self._time_edit.setDisplayFormat('HH:mm')
        self._time_edit.setFixedWidth(72); self._time_edit.setStyleSheet(STE); self._time_edit.hide(); lay.addWidget(self._time_edit)
        d = QPushButton('\u2715'); d.setFixedSize(22,22); d.setCursor(Qt.PointingHandCursor)
        d.setStyleSheet(SDEL); d.clicked.connect(lambda: self.removed.emit(self)); lay.addWidget(d)
        self._save_cb = None
        self._spin.valueChanged.connect(self._on_data_changed)
        self._time_edit.timeChanged.connect(self._on_data_changed)
        self._on_change(0)
    def _on_data_changed(self, *_):
        if self._save_cb: self._save_cb()
    def _on_change(self, idx):
        _,key = TRIGGERS[idx]
        self._time_edit.setVisible(key=='at_time')
        self._spin.setVisible(key in ('every_n_min','countdown_remain'))
        self._spin.setSuffix(' \u5206' if key=='every_n_min' else ' \u79d2')
    def get_data(self):
        idx=self._combo.currentIndex(); label,key=TRIGGERS[idx]
        return {'type':key,'label':label,'time':self._time_edit.time().toString('HH:mm'),'n':self._spin.value()}


class ActionRow(QFrame):
    removed = pyqtSignal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('QFrame{background:rgba(245,240,228,0.70);border-radius:9px;border:1px solid rgba(200,190,155,0.40);}')
        lay = QHBoxLayout(self); lay.setContentsMargins(10,6,8,6); lay.setSpacing(6)
        self._combo = QComboBox()
        for label,_ in ACTIONS: self._combo.addItem(label)
        self._combo.setStyleSheet(SC); self._combo.currentIndexChanged.connect(self._on_change); self._combo.currentIndexChanged.connect(self._on_data_changed); lay.addWidget(self._combo,1)
        self._spin = QSpinBox(); self._spin.setRange(1,3600); self._spin.setValue(5)
        self._spin.setSuffix(' \u79d2'); self._spin.setFixedWidth(80); self._spin.setStyleSheet(SSP); lay.addWidget(self._spin)
        self._cmd = QLineEdit(); self._cmd.setPlaceholderText('\u8f93\u5165\u547d\u4ee4/\u5185\u5bb9...')
        self._cmd.setStyleSheet(SE); self._cmd.hide(); lay.addWidget(self._cmd,2)
        self._fb = QPushButton('\u9009\u62e9\u6587\u4ef6...'); self._fb.setCursor(Qt.PointingHandCursor)
        self._fb.setFixedHeight(24); self._fb.setStyleSheet(SFB); self._fb.clicked.connect(self._pick)
        self._fb.hide(); lay.addWidget(self._fb)
        self._fl = QLabel('\u672a\u9009\u62e9'); self._fl.setStyleSheet('font-size:11px;color:#8a8060;border:none;background:transparent;')
        self._fl.hide(); lay.addWidget(self._fl,1)
        d = QPushButton('\u2715'); d.setFixedSize(22,22); d.setCursor(Qt.PointingHandCursor)
        d.setStyleSheet(SDEL); d.clicked.connect(lambda: self.removed.emit(self)); lay.addWidget(d)
        self._save_cb = None
        self._spin.valueChanged.connect(self._on_data_changed)
        self._cmd.textChanged.connect(self._on_data_changed)
        self._on_change(0)
    def _on_change(self, idx):
        _,key = ACTIONS[idx]
        self._spin.setVisible(key=='wait')
        self._cmd.setVisible(key in ('cmd','notify','open_url','copy_text'))
        self._fb.setVisible(key=='run'); self._fl.setVisible(key=='run')
        tips = {'notify':'\u63d0\u793a\u5185\u5bb9...','open_url':'https://...','copy_text':'\u8981\u590d\u5236\u7684\u6587\u5b57...'}
        self._cmd.setPlaceholderText(tips.get(key,'\u8f93\u5165\u547d\u4ee4...'))
    def _on_data_changed(self, *_):
        if self._save_cb: self._save_cb()
    def _pick(self):
        p,_=QFileDialog.getOpenFileName(self,'\u9009\u62e9\u6587\u4ef6','','\u53ef\u6267\u884c\u6587\u4ef6 (*.exe *.bat *.sh *.py);;\u6240\u6709\u6587\u4ef6 (*)')
        if p: self._fl.setText(p); self._on_data_changed()
    def get_data(self):
        idx=self._combo.currentIndex(); _,key=ACTIONS[idx]
        return {'type':key,'wait':self._spin.value(),'cmd':self._cmd.text(),'file':self._fl.text()}


class AutomationDetailPage(QWidget):
    run_requested = pyqtSignal(object)  # 发送 {'triggers':[], 'actions':[]}

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self._trigger_rows=[]; self._action_rows=[]; self._save_cb=None; self._build_ui()
    def _build_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(16,12,16,12); root.setSpacing(8)
        tl=QLabel('\u5f53\u2026\u65f6'); tl.setStyleSheet('font-size:13px;font-weight:700;color:#5a5030;border:none;background:transparent;'); root.addWidget(tl)
        self._ts=QScrollArea(); self._ts.setWidgetResizable(True); self._ts.setFrameShape(QFrame.NoFrame)
        self._ts.setMaximumHeight(160); self._ts.setStyleSheet('QScrollArea{background:transparent;border:none;}')
        self._tc=QWidget(); self._tl=QVBoxLayout(self._tc)
        self._tl.setContentsMargins(0,0,0,0); self._tl.setSpacing(6); self._tl.addStretch()
        self._ts.setWidget(self._tc); root.addWidget(self._ts)
        at=QPushButton('+ \u65b0\u5efa\u89e6\u53d1\u5668'); at.setCursor(Qt.PointingHandCursor); at.setFixedHeight(28)
        at.setStyleSheet(SAT); at.clicked.connect(self._add_trig); root.addWidget(at)
        sep=QFrame(); sep.setFixedHeight(1); sep.setStyleSheet('background:rgba(210,200,165,0.50);border:none;'); root.addWidget(sep)
        al=QLabel('\u6267\u884c\u4ee5\u4e0b\u64cd\u4f5c'); al.setStyleSheet('font-size:13px;font-weight:700;color:#5a5030;border:none;background:transparent;'); root.addWidget(al)
        self._as2=QScrollArea(); self._as2.setWidgetResizable(True); self._as2.setFrameShape(QFrame.NoFrame)
        self._as2.setStyleSheet('QScrollArea{background:transparent;border:none;}')
        self._ac=QWidget(); self._al_lay=QVBoxLayout(self._ac)
        self._al_lay.setContentsMargins(0,0,0,0); self._al_lay.setSpacing(6); self._al_lay.addStretch()
        self._as2.setWidget(self._ac); root.addWidget(self._as2,1)
        aa=QPushButton('+ \u65b0\u5efa\u6267\u884c\u5668'); aa.setCursor(Qt.PointingHandCursor); aa.setFixedHeight(28)
        aa.setStyleSheet(SAA); aa.clicked.connect(self._add_act); root.addWidget(aa)
        bot = QHBoxLayout(); bot.setSpacing(8)
        self._run_btn = QPushButton('\u25b6 \u7acb\u5373\u6267\u884c'); self._run_btn.setCursor(Qt.PointingHandCursor)
        self._run_btn.setFixedHeight(30); self._run_btn.setStyleSheet(SAA)
        self._run_btn.clicked.connect(self._run_now)
        self._status_lbl = QLabel('')
        self._status_lbl.setStyleSheet('font-size:11px;color:#6a8a4a;background:transparent;border:none;')
        bot.addWidget(self._run_btn); bot.addWidget(self._status_lbl, 1)
        root.addLayout(bot)
    def _add_trig(self):
        r=TriggerRow(); r.removed.connect(self._rm_trig)
        self._trigger_rows.append(r); self._tl.insertWidget(self._tl.count()-1,r)
        if self._save_cb: self._save_cb()
    def _rm_trig(self,r):
        self._trigger_rows.remove(r); self._tl.removeWidget(r); r.deleteLater()
        if self._save_cb: self._save_cb()
    def _add_act(self):
        r=ActionRow(); r.removed.connect(self._rm_act)
        self._action_rows.append(r); self._al_lay.insertWidget(self._al_lay.count()-1,r)
        if self._save_cb: self._save_cb()
    def _rm_act(self,r):
        self._action_rows.remove(r); self._al_lay.removeWidget(r); r.deleteLater()
        if self._save_cb: self._save_cb()

    def get_config(self):
        return {
            'triggers': [r.get_data() for r in self._trigger_rows],
            'actions':  [r.get_data() for r in self._action_rows],
        }

    def _run_now(self):
        cfg = self.get_config()
        AutomationRunner.execute_actions(cfg['actions'], status_cb=self._set_status)

    def _set_status(self, msg):
        self._status_lbl.setText(msg)


class AutomationSideBtn(QPushButton):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self._name=name; self._enabled=True; self._night=False
        self.setCheckable(True); self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48); self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(p.Antialiasing)
        if self.isChecked():
            bg=QColor(80,72,120,168) if self._night else QColor(200,188,150,168)
            bar=QColor(120,108,180,230) if self._night else QColor(138,122,80,230)
            p.fillRect(self.rect(),bg); p.fillRect(0,0,3,self.height(),bar)
            c=QColor(220,210,255) if self._night else QColor(44,37,16)
        else:
            hov=QColor(70,65,100,60) if self._night else QColor(210,200,165,60)
            if self.underMouse(): p.fillRect(self.rect(),hov)
            c=QColor(160,152,200) if self._night else QColor(80,72,45)
        f=QFont(YHEI,11,QFont.Bold if self.isChecked() else QFont.Normal)
        p.setFont(f); fm=p.fontMetrics(); p.setPen(c)
        p.drawText(12,(self.height()-fm.height())//2+fm.ascent(),self._name)
        dx=self.width()-18; dy=self.height()//2; p.setPen(Qt.NoPen)
        p.setBrush(QColor(80,190,80,200) if self._enabled else QColor(180,170,150,180))
        p.drawEllipse(dx-5,dy-5,10,10)
    def toggle_enabled(self): self._enabled=not self._enabled; self.update()
    def get_name(self): return self._name


class AutomationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._auto_items=[]; self._night=False; self._build_ui()

    def _build_ui(self):
        root=QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        sb=QWidget(); sb.setFixedWidth(140)
        sb.setStyleSheet("QWidget{background:rgba(248,244,232,0.55);border-right:1px solid rgba(210,200,165,0.45);}")
        self._sb=sb
        sl=QVBoxLayout(sb); sl.setContentsMargins(0,0,0,0); sl.setSpacing(0)
        self._sc=QScrollArea(); self._sc.setWidgetResizable(True)
        self._sc.setFrameShape(QFrame.NoFrame)
        self._sc.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._scon=QWidget(); self._sl=QVBoxLayout(self._scon)
        self._sl.setContentsMargins(0,0,0,0); self._sl.setSpacing(0); self._sl.addStretch()
        self._sc.setWidget(self._scon); sl.addWidget(self._sc,1)
        self._add_btn=QPushButton("+ 新建"); self._add_btn.setCursor(Qt.PointingHandCursor); self._add_btn.setFixedHeight(32)
        self._add_btn.setStyleSheet("QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:none;font-size:12px;font-weight:700;}QPushButton:hover{background:rgba(138,122,80,0.80);}")
        self._add_btn.clicked.connect(self._add); sl.addWidget(self._add_btn)
        root.addWidget(sb)
        self._ds=QStackedWidget(); self._ds.setStyleSheet("QWidget{background:transparent;}")
        emp=QLabel("选择或新建一个自动化")
        emp.setAlignment(Qt.AlignCenter)
        emp.setStyleSheet("font-size:13px;color:rgba(150,140,100,140);background:transparent;border:none;")
        self._ds.addWidget(emp); root.addWidget(self._ds,1)

    def _add(self, preset_name=None):
        n=len(self._auto_items)+1; name=preset_name or f"自动化 {n}"
        row_w=QWidget(); row_w.setStyleSheet("QWidget{background:transparent;border:none;}")
        row_lay=QHBoxLayout(row_w); row_lay.setContentsMargins(0,0,4,0); row_lay.setSpacing(0)
        btn=AutomationSideBtn(name); btn._night=self._night
        detail=AutomationDetailPage(name)
        detail.run_requested.connect(lambda cfg: AutomationRunner.execute_actions(cfg['actions']))
        detail._save_cb = self._save_automations
        self._ds.addWidget(detail)
        btn.clicked.connect(lambda _,b=btn,d=detail: self._select(b,d))
        del_btn=QPushButton("✕"); del_btn.setFixedSize(18,18)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton{background:rgba(220,160,140,0.45);color:#8a4030;border:none;border-radius:4px;font-size:10px;}QPushButton:hover{background:rgba(220,120,100,0.70);}")
        del_btn.clicked.connect(lambda _,rw=row_w,b=btn,d=detail: self._delete(rw,b,d))
        row_lay.addWidget(btn,1); row_lay.addWidget(del_btn)
        self._auto_items.append((name,btn,detail,row_w))
        self._sl.insertWidget(self._sl.count()-1,row_w)
        self._select(btn,detail)
        self._save_automations()

    def _delete(self,row_widget,btn,detail):
        self._auto_items=[(n,b,d,rw) for (n,b,d,rw) in self._auto_items if b is not btn]
        self._sl.removeWidget(row_widget); row_widget.deleteLater()
        self._ds.removeWidget(detail); detail.deleteLater()
        if self._auto_items: self._select(self._auto_items[0][1],self._auto_items[0][2])
        else: self._ds.setCurrentIndex(0)
        self._save_automations()

    def _select(self,btn,detail):
        for _,b,d,rw in self._auto_items: b.setChecked(b is btn); b.update()
        self._ds.setCurrentWidget(detail)

    def apply_night(self, night):
        self._night=night
        if night:
            sb_st="QWidget{background:rgba(38,34,52,0.55);border-right:1px solid rgba(80,75,110,0.45);}"
            add_st="QPushButton{background:rgba(80,72,120,0.55);color:#e0d8f8;border:none;font-size:12px;font-weight:700;}QPushButton:hover{background:rgba(100,90,150,0.80);}"
        else:
            sb_st="QWidget{background:rgba(248,244,232,0.55);border-right:1px solid rgba(210,200,165,0.45);}"
            add_st="QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:none;font-size:12px;font-weight:700;}QPushButton:hover{background:rgba(138,122,80,0.80);}"
        self._sb.setStyleSheet(sb_st)
        self._add_btn.setStyleSheet(add_st)
        for _,btn,_,_ in self._auto_items:
            btn._night=night; btn.update()

    def _save_automations(self):
        """保存所有自动化配置到文件"""
        try:
            from pathlib import Path
            auto_dir = cfg.get_config_dir() / 'automation'
            auto_dir.mkdir(parents=True, exist_ok=True)
            existing = {f.stem for f in auto_dir.glob('*.json')}
            current = set()
            for idx2, (name, btn, detail, rw) in enumerate(self._auto_items):
                safe = f'auto_{idx2:03d}'
                current.add(safe)
                data = detail.get_config()
                data['name'] = name
                with open(auto_dir / f'{safe}.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            for old in existing - current:
                p = auto_dir / f'{old}.json'
                if p.exists(): p.unlink()
        except Exception as e:
            print(f'[AutoSave] {e}')

    def load_automations(self):
        """从文件加载自动化配置"""
        try:
            from pathlib import Path
            auto_dir = cfg.get_config_dir() / 'automation'
            if not auto_dir.exists(): return
            for fp in sorted(auto_dir.glob('*.json')):
                try:
                    with open(fp, encoding='utf-8') as fh:
                        data = json.load(fh)
                    name = data.get('name', fp.stem)
                    from PyQt5.QtWidgets import QHBoxLayout as _HL, QPushButton as _PB, QWidget as _W
                    from PyQt5.QtCore import Qt as _Qt
                    row_w = _W(); row_w.setStyleSheet('QWidget{background:transparent;border:none;}')
                    row_lay = _HL(row_w); row_lay.setContentsMargins(0,0,4,0); row_lay.setSpacing(0)
                    btn = AutomationSideBtn(name); btn._night = self._night
                    detail = AutomationDetailPage(name)
                    detail.run_requested.connect(lambda c: AutomationRunner.execute_actions(c['actions']))
                    detail._save_cb = self._save_automations
                    self._ds.addWidget(detail)
                    btn.clicked.connect(lambda _, b=btn, d=detail: self._select(b, d))
                    del_btn = _PB('✕'); del_btn.setFixedSize(18, 18)
                    del_btn.setCursor(_Qt.PointingHandCursor)
                    del_btn.setStyleSheet('QPushButton{background:rgba(220,160,140,0.45);color:#8a4030;border:none;border-radius:4px;font-size:10px;}')
                    del_btn.clicked.connect(lambda _, rw=row_w, b=btn, d=detail: self._delete(rw, b, d))
                    row_lay.addWidget(btn, 1); row_lay.addWidget(del_btn)
                    self._auto_items.append((name, btn, detail, row_w))
                    self._sl.insertWidget(self._sl.count()-1, row_w)
                    # 恢复 triggers
                    trig_keys = [k for _, k in TRIGGERS]
                    for td in data.get('triggers', []):
                        tr = TriggerRow()
                        tr.removed.connect(lambda rr, d=detail: (d._trigger_rows.remove(rr), d._tl.removeWidget(rr), rr.deleteLater()) if rr in d._trigger_rows else None)
                        detail._trigger_rows.append(tr)
                        detail._tl.insertWidget(detail._tl.count()-1, tr)
                        if td.get('type') in trig_keys:
                            tr._combo.setCurrentIndex(trig_keys.index(td['type']))
                        if td.get('n'): tr._spin.setValue(int(td['n']))
                        tr._save_cb = self._save_automations
                        if td.get('time'): tr._time_edit.setTime(__import__('PyQt5.QtCore', fromlist=['QTime']).QTime.fromString(str(td['time']), 'HH:mm'))
                    keys = [k for _, k in ACTIONS]
                    for ad in data.get('actions', []):
                        r = ActionRow()
                        r.removed.connect(lambda rr, d=detail: (d._action_rows.remove(rr), d._al_lay.removeWidget(rr), rr.deleteLater()) if rr in d._action_rows else None)
                        detail._action_rows.append(r)
                        detail._al_lay.insertWidget(detail._al_lay.count()-1, r)
                        if ad.get('type') in keys: r._combo.setCurrentIndex(keys.index(ad['type']))
                        if ad.get('wait'): r._spin.setValue(int(ad['wait']))
                        if ad.get('cmd'): r._cmd.setText(str(ad['cmd']))
                        if ad.get('file'): r._fl.setText(str(ad['file']))
                        r._save_cb = self._save_automations
                except Exception as e2:
                    print(f'[AutoLoad] {fp.name}: {e2}')
            if self._auto_items:
                self._select(self._auto_items[0][1], self._auto_items[0][2])
        except Exception as e:
            print(f'[AutoLoad] {e}')


class AutomationRunner:
    """执行自动化动作列表"""
    _pick_cb = None  # 由外部注入：callable() -> str
    _theme_cb = None  # 由外部注入：callable()

    @classmethod
    def execute_actions(cls, actions, status_cb=None):
        """执行动作列表，每个动作顺序执行（wait 用 QTimer 异步）"""
        cls._exec_seq(actions, 0, status_cb)

    @classmethod
    def _exec_seq(cls, actions, idx, status_cb):
        if idx >= len(actions):
            if status_cb: status_cb('已完成')
            return
        a = actions[idx]
        t = a.get('type', '')
        try:
            if t == 'wait':
                secs = int(a.get('wait', 1))
                if status_cb: status_cb(f'等待 {secs} 秒…')
                QTimer.singleShot(secs * 1000, lambda: cls._exec_seq(actions, idx+1, status_cb))
                return
            elif t == 'cmd':
                cmd = a.get('cmd', '').strip()
                if cmd:
                    subprocess.Popen(cmd, shell=True)
                    if status_cb: status_cb(f'已执行: {cmd[:30]}')
            elif t == 'run':
                fpath = a.get('file', '').strip()
                if fpath and os.path.exists(fpath):
                    subprocess.Popen([fpath], shell=True)
                    if status_cb: status_cb(f'已启动: {os.path.basename(fpath)}')
                else:
                    if status_cb: status_cb('文件不存在')
            elif t == 'notify':
                msg = a.get('cmd', '').strip()
                from PyQt5.QtWidgets import QSystemTrayIcon
                # 通过全局 app 发送托盘通知
                app = QApplication.instance()
                tray = None
                for w in app.topLevelWidgets():
                    if hasattr(w, '_tray'):
                        tray = w._tray; break
                if tray:
                    tray.showMessage('自动化提醒', msg, QSystemTrayIcon.Information, 3000)
                if status_cb: status_cb(f'通知: {msg[:20]}')
            elif t == 'toggle_theme':
                app = QApplication.instance()
                for w in app.topLevelWidgets():
                    if hasattr(w, '_toggle_theme'):
                        w._toggle_theme(); break
                if status_cb: status_cb('已切换主题')
            elif t == 'pick_one':
                if cls._pick_cb:
                    name = cls._pick_cb()
                    if status_cb: status_cb(f'抽取: {name}')
                else:
                    if status_cb: status_cb('未连接抽签功能')
            elif t == 'open_url':
                url = a.get('cmd', '').strip()
                if url:
                    webbrowser.open(url)
                    if status_cb: status_cb(f'已打开: {url[:30]}')
            elif t == 'copy_text':
                text = a.get('cmd', '').strip()
                if text:
                    QApplication.clipboard().setText(text)
                    if status_cb: status_cb(f'已复制: {text[:20]}')
        except Exception as e:
            if status_cb: status_cb(f'错误: {e}')
        cls._exec_seq(actions, idx+1, status_cb)


class AutomationScheduler:
    """定时触发器引擎，由外部创建并启动"""
    def __init__(self, page_ref):
        self._page = page_ref
        self._timer = QTimer()
        self._timer.setInterval(10000)  # 每10秒检查一次
        self._timer.timeout.connect(self._check)
        self._last_hour = -1
        self._last_min = -1
        self._counters = {}  # automation_name -> last_trigger_min

    def start(self): self._timer.start()
    def stop(self): self._timer.stop()

    def notify_event(self, event_type):
        """由外部在特定事件发生时调用，如 after_pick / after_countdown 等"""
        self._fire_triggers(event_type)

    def _check(self):
        now = QDateTime.currentDateTime()
        h = now.time().hour(); m = now.time().minute()
        self._fire_triggers('at_hour', h=h, m=m)
        self._fire_triggers('at_time', h=h, m=m)
        self._fire_triggers('every_n_min', h=h, m=m)
        self._last_hour = h; self._last_min = m

    def _fire_triggers(self, event, **kwargs):
        if not hasattr(self._page, '_auto_items'): return
        for name, btn, detail, _ in self._page._auto_items:
            if not btn._enabled: continue
            cfg = detail.get_config()
            for trig in cfg['triggers']:
                if self._matches(trig, event, **kwargs):
                    AutomationRunner.execute_actions(cfg['actions'])
                    break

    def _matches(self, trig, event, h=0, m=0):
        t = trig.get('type', '')
        if t != event: return False
        if t == 'at_hour': return True
        if t == 'at_time':
            ts = trig.get('time', '00:00').split(':')
            return int(ts[0]) == h and int(ts[1]) == m
        if t == 'every_n_min':
            n = trig.get('n', 5)
            return m % n == 0
        return True