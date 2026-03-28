# ui/pages/roster_view_page.py - Part 1
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QDialog, QLineEdit, QSizePolicy, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPainterPath, QPen


def _pinyin_initial(ch):
    if not ch: return '#'
    if ch.isalpha() and ord(ch) < 128: return ch.upper()
    try:
        from pypinyin import lazy_pinyin, Style
        r = lazy_pinyin(ch, style=Style.FIRST_LETTER)
        if r and r[0] and r[0][0].isalpha(): return r[0][0].upper()
    except Exception: pass
    return '#'

def _sort_key(name):
    if not name: return (1,'','')
    k = _pinyin_initial(name[0])
    return (0,k,name) if k.isalpha() else (1,k,name)


class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280,180); self._ok=False
        lay=QVBoxLayout(self); lay.setContentsMargins(20,18,20,18); lay.setSpacing(10)
        t=QLabel('\u8bf7\u8f93\u5165\u5bc6\u7801'); t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet('font-size:13px;font-weight:700;color:#3a3220;background:transparent;border:none;')
        lay.addWidget(t)
        self._edit=QLineEdit(); self._edit.setEchoMode(QLineEdit.Password)
        self._edit.setFixedHeight(36); self._edit.setAlignment(Qt.AlignCenter)
        self._edit.setStyleSheet('QLineEdit{background:rgba(255,253,245,0.95);color:#2c2510;border:1px solid rgba(200,190,155,0.70);border-radius:8px;font-size:14px;padding:0 8px;}')
        self._edit.returnPressed.connect(self._check); lay.addWidget(self._edit)
        self._hint=QLabel(''); self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet('font-size:11px;color:#c05030;background:transparent;border:none;')
        lay.addWidget(self._hint)
        row=QHBoxLayout(); row.setSpacing(10)
        ok=QPushButton('\u786e\u5b9a'); ok.setCursor(Qt.PointingHandCursor); ok.setFixedHeight(30)
        ok.setStyleSheet('QPushButton{background:rgba(138,122,80,0.82);color:#fff8e8;border:none;border-radius:7px;font-size:12px;font-weight:700;}QPushButton:hover{background:rgba(158,142,95,0.95);}')
        cn=QPushButton('\u53d6\u6d88'); cn.setCursor(Qt.PointingHandCursor); cn.setFixedHeight(30)
        cn.setStyleSheet('QPushButton{background:rgba(200,190,155,0.40);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:7px;font-size:12px;}QPushButton:hover{background:rgba(200,190,155,0.70);}')
        ok.clicked.connect(self._check); cn.clicked.connect(self.reject)
        row.addWidget(cn,1); row.addWidget(ok,1); lay.addLayout(row)
    def _check(self):
        from utils import config as cfg
        if self._edit.text()==cfg.get('roster_password','123123'): self._ok=True; self.accept()
        else: self._hint.setText('\u5bc6\u7801\u9519\u8bef'); self._edit.clear(); self._edit.setFocus()
    def verified(self): return self._ok
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path=QPainterPath(); path.addRoundedRect(0,0,self.width(),self.height(),14,14)
        p.fillPath(path,QBrush(QColor(255,253,245,248)))
        p.setPen(QPen(QColor(210,200,165,180),1.2)); p.drawPath(path)


class EditRosterDialog(QDialog):
    def __init__(self,names,parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(320,400); self._result=None
        lay=QVBoxLayout(self); lay.setContentsMargins(18,16,18,16); lay.setSpacing(10)
        t=QLabel('\u4fee\u6539\u540d\u5355  (\u6bcf\u884c\u4e00\u4e2a\u59d3\u540d)'); t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet('font-size:13px;font-weight:700;color:#3a3220;background:transparent;border:none;')
        lay.addWidget(t)
        self._edit=QTextEdit(); self._edit.setPlainText('\n'.join(names))
        self._edit.setStyleSheet('QTextEdit{background:rgba(255,253,245,0.95);color:#2c2510;border:1px solid rgba(200,190,155,0.70);border-radius:8px;font-size:13px;padding:6px;}')
        lay.addWidget(self._edit,1)
        row=QHBoxLayout(); row.setSpacing(10)
        ok=QPushButton('\u4fdd\u5b58'); ok.setCursor(Qt.PointingHandCursor); ok.setFixedHeight(32)
        ok.setStyleSheet('QPushButton{background:rgba(138,122,80,0.82);color:#fff8e8;border:none;border-radius:8px;font-size:13px;font-weight:700;}QPushButton:hover{background:rgba(158,142,95,0.95);}')
        cn=QPushButton('\u53d6\u6d88'); cn.setCursor(Qt.PointingHandCursor); cn.setFixedHeight(32)
        cn.setStyleSheet('QPushButton{background:rgba(200,190,155,0.40);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:8px;font-size:13px;}QPushButton:hover{background:rgba(200,190,155,0.70);}')
        ok.clicked.connect(self._save); cn.clicked.connect(self.reject)
        row.addWidget(cn,1); row.addWidget(ok,1); lay.addLayout(row)
    def _save(self):
        self._result=[l.strip() for l in self._edit.toPlainText().splitlines() if l.strip()]; self.accept()
    def get_names(self): return self._result
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path=QPainterPath(); path.addRoundedRect(0,0,self.width(),self.height(),16,16)
        p.fillPath(path,QBrush(QColor(255,253,245,245)))
        p.setPen(QPen(QColor(210,200,165,180),1.2)); p.drawPath(path)


class RosterViewPage(QWidget):
    edit_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._names=[]; self._night=False; self._group_widgets={}
        self._build_ui()

    def _build_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        self._top=QWidget(); self._top.setFixedHeight(44)
        self._top.setObjectName("rv_top")
        self._top.setStyleSheet("#rv_top{background:rgba(255,255,250,0.70);border-bottom:1px solid rgba(210,200,165,0.45);}")
        tl=QHBoxLayout(self._top); tl.setContentsMargins(12,0,12,0)
        self._back_btn=QPushButton("← 返回")
        self._back_btn.setCursor(Qt.PointingHandCursor); self._back_btn.setFixedHeight(28)
        self._back_btn.setStyleSheet("QPushButton{background:transparent;color:#8a7a50;border:none;font-size:12px;font-weight:600;}QPushButton:hover{color:#3a3220;}")
        self._back_btn.clicked.connect(self.back_requested)
        tl.addWidget(self._back_btn); tl.addStretch()
        self._count_lbl=QLabel("共 0 人")
        self._count_lbl.setStyleSheet("font-size:13px;font-weight:700;color:#5a5030;background:transparent;border:none;")
        tl.addWidget(self._count_lbl); root.addWidget(self._top)
        body=QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        self._scroll=QScrollArea(); self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._content=QWidget(); self._content.setStyleSheet("background:transparent;")
        self._list_layout=QVBoxLayout(self._content)
        self._list_layout.setContentsMargins(16,12,8,12); self._list_layout.setSpacing(8)
        self._scroll.setWidget(self._content); body.addWidget(self._scroll,1)
        self._idx_widget=QWidget(); self._idx_widget.setFixedWidth(32)
        self._idx_widget.setStyleSheet("background:transparent;")
        self._idx_layout=QVBoxLayout(self._idx_widget)
        self._idx_layout.setContentsMargins(2,8,2,8); self._idx_layout.setSpacing(1)
        body.addWidget(self._idx_widget); root.addLayout(body,1)
        self._bot=QWidget(); self._bot.setFixedHeight(48)
        self._bot.setObjectName("rv_bot")
        self._bot.setStyleSheet("#rv_bot{background:rgba(255,255,250,0.70);border-top:1px solid rgba(210,200,165,0.45);}")
        bl=QHBoxLayout(self._bot); bl.setContentsMargins(16,0,16,0); bl.addStretch()
        self._edit_btn=QPushButton("✏ 修改名单")
        self._edit_btn.setCursor(Qt.PointingHandCursor); self._edit_btn.setFixedHeight(32)
        self._edit_btn.setStyleSheet("QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:none;border-radius:8px;font-size:12px;font-weight:600;padding:0 18px;}QPushButton:hover{background:rgba(158,142,95,0.80);}")
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        bl.addWidget(self._edit_btn); root.addWidget(self._bot)

    def _on_edit_clicked(self):
        dlg=PasswordDialog(self)
        if dlg.exec_()==QDialog.Accepted and dlg.verified(): self.edit_requested.emit()

    def load_names(self,names):
        self._names=list(names); self._refresh()

    def _refresh(self):
        while self._list_layout.count():
            item=self._list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        while self._idx_layout.count():
            item=self._idx_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._group_widgets={}
        self._count_lbl.setText(f"共 {len(self._names)} 人")
        if not self._names:
            lbl=QLabel("暂无名单"); lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color:rgba(150,140,100,150);font-size:13px;background:transparent;border:none;")
            self._list_layout.addWidget(lbl); return
        sorted_names=sorted(self._names,key=_sort_key)
        groups={}
        for name in sorted_names:
            letter=_pinyin_initial(name[0]) if name else "#"
            if not letter.isalpha(): letter="#"
            groups.setdefault(letter,[]).append(name)
        n=self._night
        name_st=("font-size:12px;color:#e0d8f8;background:rgba(50,46,72,0.70);border-radius:6px;border:1px solid rgba(80,75,110,0.45);" if n else
                 "font-size:12px;color:#3a3220;background:rgba(245,242,232,0.70);border-radius:6px;border:1px solid rgba(210,200,165,0.45);")
        letter_st=("font-size:12px;font-weight:700;color:#a090d0;background:transparent;border:none;padding-left:4px;" if n else
                   "font-size:12px;font-weight:700;color:#8a7a50;background:transparent;border:none;padding-left:4px;")
        idx_st=("QPushButton{background:transparent;color:#a090d0;border:none;font-size:13px;font-weight:700;}QPushButton:hover{color:#e0d8f8;}" if n else
                "QPushButton{background:transparent;color:#8a7a50;border:none;font-size:13px;font-weight:700;}QPushButton:hover{color:#3a3220;}")
        letter_order=sorted(groups.keys(),key=lambda x:(0,x) if x!="#" else (1,""))
        for letter in letter_order:
            grp_w=QWidget(); grp_w.setStyleSheet("background:transparent;")
            gl=QVBoxLayout(grp_w); gl.setContentsMargins(0,0,0,0); gl.setSpacing(4)
            lbl_l=QLabel(letter); lbl_l.setFixedHeight(24); lbl_l.setStyleSheet(letter_st)
            gl.addWidget(lbl_l)
            col=0; row_w=None
            for name in groups[letter]:
                if col%4==0:
                    row_w=QWidget(); row_w.setStyleSheet("background:transparent;")
                    rl=QHBoxLayout(row_w); rl.setContentsMargins(0,0,0,0); rl.setSpacing(6)
                    gl.addWidget(row_w)
                nlbl=QLabel(name); nlbl.setFixedHeight(30); nlbl.setAlignment(Qt.AlignCenter)
                nlbl.setStyleSheet(name_st); row_w.layout().addWidget(nlbl,1); col+=1
            rem=col%4
            if rem and row_w:
                for _ in range(4-rem):
                    sp=QWidget(); sp.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
                    sp.setFixedHeight(30); sp.setStyleSheet("background:transparent;")
                    row_w.layout().addWidget(sp,1)
            self._list_layout.addWidget(grp_w); self._group_widgets[letter]=grp_w
        self._list_layout.addStretch()
        for letter in letter_order:
            btn=QPushButton(letter); btn.setFixedSize(26,20)
            btn.setCursor(Qt.PointingHandCursor); btn.setStyleSheet(idx_st)
            btn.clicked.connect(lambda _,l=letter:self._scroll_to(l))
            self._idx_layout.addWidget(btn)
        self._idx_layout.addStretch()

    def _scroll_to(self,letter):
        w=self._group_widgets.get(letter)
        if w: self._scroll.ensureWidgetVisible(w,0,20)

    def apply_night(self,night):
        self._night=night; n=night
        self._top.setStyleSheet("#rv_top{background:rgba(38,34,52,0.70);border-bottom:1px solid rgba(80,75,110,0.45);}" if n else
                                "#rv_top{background:rgba(255,255,250,0.70);border-bottom:1px solid rgba(210,200,165,0.45);}")
        self._bot.setStyleSheet("#rv_bot{background:rgba(38,34,52,0.70);border-top:1px solid rgba(80,75,110,0.45);}" if n else
                                "#rv_bot{background:rgba(255,255,250,0.70);border-top:1px solid rgba(210,200,165,0.45);}")
        cnt_fg="#c0b8e8" if n else "#5a5030"
        self._count_lbl.setStyleSheet(f"font-size:13px;font-weight:700;color:{cnt_fg};background:transparent;border:none;")
        self._back_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{"#a090d0" if n else "#8a7a50"};border:none;font-size:12px;font-weight:600;}}QPushButton:hover{{color:{"#e0d8f8" if n else "#3a3220"};}}") 
        self._edit_btn.setStyleSheet("QPushButton{background:rgba(70,62,110,0.55);color:#e0d8f8;border:none;border-radius:8px;font-size:12px;font-weight:600;padding:0 18px;}QPushButton:hover{background:rgba(90,80,140,0.78);}" if n else
                                     "QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:none;border-radius:8px;font-size:12px;font-weight:600;padding:0 18px;}QPushButton:hover{background:rgba(158,142,95,0.80);}")
        self._refresh()
