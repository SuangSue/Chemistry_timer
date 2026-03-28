from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QSizePolicy, QApplication
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint,
    QParallelAnimationGroup, pyqtSignal
)
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush


class RippleOverlay(QWidget):
    """倒计时结束辐射波纹"""
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._cx = screen.center().x()
        self._cy = screen.center().y()
        self._radius = 0.0
        self._max_r = ((screen.width()**2 + screen.height()**2)**0.5) * 0.55 + 200
        self._alpha = 200
        self._color = QColor(220, 80, 60)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self, cx, cy, color=None):
        self._cx = cx; self._cy = cy
        if color: self._color = QColor(color)
        self._radius = 0.0; self._alpha = 200
        self.show(); self.raise_(); self._timer.start()

    def _tick(self):
        self._radius += self._max_r / 28
        self._alpha = max(0, int(200 * (1 - self._radius / self._max_r)))
        if self._radius >= self._max_r:
            self._timer.stop(); self.hide()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QColor(self._color); c.setAlpha(self._alpha)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c))
        r = int(self._radius)
        p.drawEllipse(self._cx - r, self._cy - r, r*2, r*2)


_ripple_instance = None
def get_ripple():
    global _ripple_instance
    if _ripple_instance is None:
        _ripple_instance = RippleOverlay()
    return _ripple_instance


class BorderFlashOverlay(QWidget):
    """从右上角向左、向下各一条金色线段"""
    def __init__(self, parent_ref):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._parent_ref = parent_ref
        self._progress = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self):
        self._progress = 0.0
        # 定位到主窗口（向上找顶级窗口）
        try:
            w = self._parent_ref
            while w.parent() and not w.isWindow(): w = w.parent()
            self.setGeometry(w.geometry())
        except Exception: pass
        self.show(); self.raise_(); self._timer.start()

    def _tick(self):
        self._progress = min(1.0, self._progress + 1.0/22)
        if self._progress >= 1.0:
            self._timer.stop()
            from PyQt5.QtCore import QTimer as _T
            _T.singleShot(120, self.hide)
        self.update()

    def paintEvent(self, event):
        if self._progress <= 0: return
        import math
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        m = 14; r = 16
        prog = self._progress
        DELAY = 0.45
        tail = max(0.0,(prog-DELAY)/(1.0-DELAY)) if prog>DELAY else 0.0
        # 路径直线段长度
        tl=float(W-2*m-2*r); ll=float(H-2*m-2*r)
        rl=float(H-2*m-2*r); bl=float(W-2*m-2*r)
        aq=math.pi/2*r  # 四分之一弧长
        pA=aq+tl+aq+ll; pB=aq+rl+aq+bl
        NA=24  # 弧段插值数
        def arc(cx,cy,rad,a0,a1):
            return [(cx+rad*math.cos(math.radians(a0+(a1-a0)*k/NA)),
                     cy+rad*math.sin(math.radians(a0+(a1-a0)*k/NA)))
                    for k in range(NA+1)]
        # 线A完整路径: 起点(W-m, m+r)
        # 右上弧: 中心(W-m-r, m+r), 0°到-90° => 从(W-m,m+r)到(W-m-r,m)
        def fullA():
            pts = arc(W-m-r, m+r, r, 0, -90)   # (W-m,m+r)到(W-m-r,m)
            # 顶边: (W-m-r,m) 向左到 (m+r,m)
            pts += [(W-m-r - tl*k/NA, m) for k in range(1,NA+1)]
            # 左上弧: 中心(m+r,m+r), -90°到-180° => (m+r,m)到(m,m+r)
            pts += arc(m+r, m+r, r, -90, -180)[1:]
            # 左边: (m,m+r)向下到(m,m+r+ll)
            pts += [(m, m+r+ll*k/NA) for k in range(1,NA+1)]
            return pts
        # 线B完整路径: 起点(W-m, m+r)
        # 右上弧: 中心(W-m-r, m+r), 0°到90° => 从(W-m,m+r)到(W-m-r,m+2r)
        def fullB():
            pts = arc(W-m-r, m+r, r, 0, 90)    # (W-m,m+r)到(W-m-r,m+2r)
            # 右边: (W-m-r,m+2r)? 不对，右边是(W-m, m+r)到(W-m, m+r+rl)
            # 实际上右上弧0->90是 (W-m,m+r)->(W-m-r,m+2r), 但右边应从(W-m,m+r)向下
            # 修正: 右上角不画弧，直接从(W-m,m+r)向下到(W-m,H-m-r)
            pts = [(W-m, m+r+rl*k/NA) for k in range(NA+1)]
            # 右下弧: 中心(W-m-r, H-m-r), 0°到90° => (W-m,H-m-r)到(W-m-r,H-m)
            pts += arc(W-m-r, H-m-r, r, 0, 90)[1:]
            # 底边: (W-m-r,H-m)向左到(m+r,H-m)
            pts += [(W-m-r - bl*k/NA, H-m) for k in range(1,NA+1)]
            return pts
        def clip(pts,frac,plen):
            if frac<=0: return [pts[0]]
            dist=frac*plen; res=[pts[0]]; acc=0.0
            for i in range(1,len(pts)):
                dx=pts[i][0]-pts[i-1][0]; dy=pts[i][1]-pts[i-1][1]
                s=(dx*dx+dy*dy)**0.5
                if acc+s>=dist:
                    f=(dist-acc)/s if s>0 else 0
                    res.append((pts[i-1][0]+dx*f, pts[i-1][1]+dy*f)); break
                acc+=s; res.append(pts[i])
            return res
        def draw(hp,tp):
            nt=len(tp); seg=hp[max(0,nt-1):]
            if len(seg)<2: seg=hp[-2:]
            n=len(seg)
            for i in range(n-1):
                t=i/max(n-2,1)
                if t<0.18: rc,gc,bc=218,178,50; ac=int(255*t/0.18)
                elif t<0.38:
                    f=(t-0.18)/0.20
                    rc=int(218+(255-218)*f); gc=int(178+(255-178)*f); bc=int(50+(255-50)*f); ac=255
                elif t<0.78: rc,gc,bc=218,178,50; ac=255
                else:
                    f=(t-0.78)/0.22
                    rc=int(218+(255-218)*f); gc=int(178+(255-178)*f); bc=int(50+(255-50)*f); ac=255
                pen=QPen(QColor(rc,gc,bc,ac),4.2); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
                p.drawLine(int(seg[i][0]),int(seg[i][1]),int(seg[i+1][0]),int(seg[i+1][1]))
        fa=fullA(); fb=fullB()
        ha=clip(fa,prog,pA); ta=clip(fa,tail,pA)
        hb=clip(fb,prog,pB); tb=clip(fb,tail,pB)
        draw(ha,ta); draw(hb,tb)

class StopwatchCard(QWidget):
    action_triggered = pyqtSignal()
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._ms = 0; self._running = False; self._title = title
        self._setup_ui()
        self._qtimer = QTimer(self); self._qtimer.setInterval(30)
        self._qtimer.timeout.connect(self._tick)

    def _setup_ui(self):
        self.setStyleSheet('StopwatchCard{background:transparent;border:none;}')
        lay = QVBoxLayout(self); lay.setContentsMargins(8,4,8,4); lay.setSpacing(6)
        lbl = QLabel(self._title); lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet('font-size:11px;font-weight:700;color:#7a7050;background:transparent;border:none;')
        lay.addWidget(lbl)
        self._display = QLabel('00:00.000'); self._display.setAlignment(Qt.AlignCenter)
        self._display.setFont(QFont('Microsoft YaHei', 50, QFont.Bold))
        self._display.setStyleSheet('color:#2c2510;background:transparent;border:none;')
        lay.addWidget(self._display, 1)
        row = QHBoxLayout(); row.setSpacing(10); row.setContentsMargins(20,0,20,0)
        self._btn_start = self._mk('\u5f00\u59cb', '#8a7a50')
        self._btn_reset = self._mk('\u91cd\u7f6e', '#afa898')
        self._btn_start.clicked.connect(self._toggle)
        self._btn_reset.clicked.connect(self._reset)
        row.addWidget(self._btn_start, 1); row.addWidget(self._btn_reset, 1)
        lay.addLayout(row)

    @staticmethod
    def _mk(text, hx):
        h=hx.lstrip('#'); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16); rgb=f'{r},{g},{b}'
        btn=QPushButton(text); btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(34); btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        btn.setStyleSheet(f'QPushButton{{background:rgba({rgb},0.50);color:#2c2510;border:1px solid rgba({rgb},0.65);border-radius:7px;font-size:14px;font-weight:600;font-family:"Microsoft YaHei";padding:0 18px;}}QPushButton:hover{{background:rgba({rgb},0.78);}}')
        return btn

    def _toggle(self):
        if self._running:
            self._running=False; self._qtimer.stop(); self._btn_start.setText('\u7ee7\u7eed')
        else:
            self._running=True; self._qtimer.start(); self._btn_start.setText('\u6682\u505c')
            self.action_triggered.emit()

    def _reset(self):
        self._running=False; self._qtimer.stop(); self._ms=0
        self._btn_start.setText('\u5f00\u59cb'); self._display.setText('00:00.000')

    def _tick(self):
        self._ms+=30; ms=self._ms
        m=(ms//60000)%100; s=(ms%60000)//1000; msec=ms%1000
        self._display.setText(f'{m:02d}:{s:02d}.{msec:03d}')

    def is_running(self): return self._running
    def apply_night(self, night):
        self._night = night
        fg='#e0d8f8' if night else '#2c2510'
        self._display.setStyleSheet(f'color:{fg};background:transparent;border:none;')
        bs = ('QPushButton{background:rgba(70,62,110,0.55);color:#e0d8f8;border:1px solid rgba(100,90,150,0.65);border-radius:7px;font-size:14px;font-weight:600;padding:0 18px;}'               'QPushButton:hover{background:rgba(90,80,140,0.78);}') if night else               ('QPushButton{background:rgba(138,122,80,0.50);color:#2c2510;border:1px solid rgba(138,122,80,0.65);border-radius:7px;font-size:14px;font-weight:600;padding:0 18px;}'               'QPushButton:hover{background:rgba(158,140,96,0.78);}')
        self._btn_start.setStyleSheet(bs); self._btn_reset.setStyleSheet(bs)


class DualStopwatchPage(QWidget):
    action_triggered = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(8,6,8,6); lay.setSpacing(0)
        self._sw1 = StopwatchCard('\u6b63\u8ba1\u65f6 A'); lay.addWidget(self._sw1, 1)
        self._sw1.action_triggered.connect(self.action_triggered)
        line = QFrame(); line.setFixedHeight(1)
        line.setStyleSheet('background:rgba(200,190,155,0.55);border:none;')
        lay.addWidget(line)
        self._sw2 = StopwatchCard('\u6b63\u8ba1\u65f6 B'); lay.addWidget(self._sw2, 1)
        self._sw2.action_triggered.connect(self.action_triggered)

    def is_running(self): return self._sw1.is_running() or self._sw2.is_running()
    def apply_night(self, night): self._sw1.apply_night(night); self._sw2.apply_night(night)


COUNTDOWN_PRESETS = [
    ('10\u79d2',10),('30\u79d2',30),('5\u5206',300),('10\u5206',600),('60\u5206',3600),
]


class CountdownCard(QFrame):
    action_triggered = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self._total_ms=0; self._remain_ms=0
        self._running=False; self._night=False
        self._preset_btns=[]; self._setup_ui()
        self._qtimer=QTimer(self); self._qtimer.setInterval(100)
        self._qtimer.timeout.connect(self._tick)

    def _setup_ui(self):
        self.setStyleSheet("CountdownCard{background:transparent;border:none;}")
        lay=QVBoxLayout(self); lay.setContentsMargins(10,4,10,4); lay.setSpacing(5)
        lbl=QLabel("倒计时"); lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size:12px;font-weight:700;color:#7a7050;background:transparent;border:none;")
        lay.addWidget(lbl)
        adj=QHBoxLayout(); adj.setSpacing(8); adj.setContentsMargins(8,0,8,0)
        min_col=QVBoxLayout(); min_col.setSpacing(2)
        self._btn_min_up=self._adj_btn("+")
        self._min_lbl=QLabel("00"); self._min_lbl.setAlignment(Qt.AlignCenter)
        self._min_lbl.setFont(QFont("Microsoft YaHei",54,QFont.Bold))
        self._min_lbl.setStyleSheet("color:#2c2510;background:transparent;border:none;")
        self._btn_min_dn=self._adj_btn("-")
        self._btn_min_up.clicked.connect(lambda: self._adj(60,1))
        self._btn_min_dn.clicked.connect(lambda: self._adj(60,-1))
        min_col.addWidget(self._btn_min_up); min_col.addWidget(self._min_lbl,1); min_col.addWidget(self._btn_min_dn)
        colon=QLabel(":"); colon.setAlignment(Qt.AlignCenter)
        colon.setFont(QFont("Microsoft YaHei",44,QFont.Bold))
        colon.setStyleSheet("color:#2c2510;background:transparent;border:none;"); colon.setFixedWidth(22)
        sec_col=QVBoxLayout(); sec_col.setSpacing(2)
        self._btn_sec_up=self._adj_btn("+")
        self._sec_lbl=QLabel("00"); self._sec_lbl.setAlignment(Qt.AlignCenter)
        self._sec_lbl.setFont(QFont("Microsoft YaHei",54,QFont.Bold))
        self._sec_lbl.setStyleSheet("color:#2c2510;background:transparent;border:none;")
        self._btn_sec_dn=self._adj_btn("-")
        self._btn_sec_up.clicked.connect(lambda: self._adj(1,1))
        self._btn_sec_dn.clicked.connect(lambda: self._adj(1,-1))
        sec_col.addWidget(self._btn_sec_up); sec_col.addWidget(self._sec_lbl,1); sec_col.addWidget(self._btn_sec_dn)
        adj.addLayout(min_col,1); adj.addWidget(colon); adj.addLayout(sec_col,1)
        lay.addLayout(adj,1)
        hint=QLabel("点击累加"); hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size:10px;color:#9a9278;background:transparent;border:none;")
        lay.addWidget(hint)
        prow=QHBoxLayout(); prow.setSpacing(5)
        for label,secs in COUNTDOWN_PRESETS:
            btn=QPushButton(label); btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(26); btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            btn.setStyleSheet("QPushButton{background:rgba(210,200,165,0.38);color:#2c2510;border:1px solid rgba(200,190,155,0.50);border-radius:5px;font-size:12px;}QPushButton:hover{background:rgba(210,200,165,0.72);}")
            btn.clicked.connect(lambda _,s=secs: self._add_time(s))
            prow.addWidget(btn); self._preset_btns.append(btn)
        lay.addLayout(prow)
        ctrl=QHBoxLayout(); ctrl.setSpacing(10); ctrl.setContentsMargins(20,0,20,0)
        self._btn_toggle=self._mk("开始","#8a7a50")
        self._btn_reset_btn=self._mk("重置","#afa898")
        self._btn_toggle.clicked.connect(self._toggle)
        self._btn_reset_btn.clicked.connect(self._reset)
        ctrl.addWidget(self._btn_toggle,1); ctrl.addWidget(self._btn_reset_btn,1)
        lay.addLayout(ctrl)

    @staticmethod
    def _adj_btn(text):
        btn=QPushButton(text); btn.setCursor(Qt.PointingHandCursor); btn.setFixedHeight(22)
        btn.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        btn.setStyleSheet("QPushButton{background:rgba(200,190,155,0.35);color:#5a5030;border:1px solid rgba(200,190,155,0.50);border-radius:6px;font-size:13px;font-weight:700;}QPushButton:hover{background:rgba(200,190,155,0.65);}")
        return btn

    @staticmethod
    def _mk(text,hx):
        h=hx.lstrip("#"); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16); rgb=f"{r},{g},{b}"
        btn=QPushButton(text); btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(34); btn.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Fixed)
        btn.setStyleSheet(f"QPushButton{{background:rgba({rgb},0.50);color:#2c2510;border:1px solid rgba({rgb},0.65);border-radius:7px;font-size:14px;font-weight:600;padding:0 18px;}}QPushButton:hover{{background:rgba({rgb},0.78);}}")
        return btn

    def _adj(self,unit,delta):
        if self._running: return
        self._total_ms=max(0,self._total_ms+unit*delta*1000)
        self._remain_ms=self._total_ms; self._refresh_display()

    def _toggle(self):
        if self._running: self._running=False; self._qtimer.stop(); self._btn_toggle.setText("继续")
        else:
            if self._total_ms==0: return
            self._running=True; self._qtimer.start(); self._btn_toggle.setText("暂停")
            self.action_triggered.emit()

    def _add_time(self,secs):
        self._total_ms+=secs*1000
        if not self._running: self._remain_ms=self._total_ms
        self._refresh_display()

    def is_running(self): return self._running

    def apply_night(self,night):
        self._night=night; fg="#e0d8f8" if night else "#2c2510"
        self._min_lbl.setStyleSheet(f"color:{fg};background:transparent;border:none;")
        self._sec_lbl.setStyleSheet(f"color:{fg};background:transparent;border:none;")
        # 冒号标签
        for lbl in self.findChildren(__import__('PyQt5.QtWidgets',fromlist=['QLabel']).QLabel):
            s = lbl.styleSheet()
            if 'color:#2c2510' in s or 'color:#e0d8f8' in s:
                lbl.setStyleSheet(s.replace('color:#2c2510',fg).replace('color:#e0d8f8',fg))
        # 预设按钮
        ps=("QPushButton{background:rgba(80,72,120,0.45);color:#e0d8f8;border:1px solid rgba(100,90,150,0.55);border-radius:5px;font-size:12px;}QPushButton:hover{background:rgba(100,90,145,0.70);}" if night else "QPushButton{background:rgba(210,200,165,0.38);color:#2c2510;border:1px solid rgba(200,190,155,0.50);border-radius:5px;font-size:12px;}QPushButton:hover{background:rgba(210,200,165,0.72);}")
        for btn in self._preset_btns: btn.setStyleSheet(ps)
        # 加减按钮
        adj_st = ("QPushButton{background:rgba(70,62,110,0.45);color:#e0d8f8;border:1px solid rgba(100,90,150,0.55);border-radius:6px;font-size:13px;font-weight:700;}QPushButton:hover{background:rgba(90,80,140,0.70);}" if night else "QPushButton{background:rgba(200,190,155,0.35);color:#5a5030;border:1px solid rgba(200,190,155,0.50);border-radius:6px;font-size:13px;font-weight:700;}QPushButton:hover{background:rgba(200,190,155,0.65);}")
        for btn in (self._btn_min_up,self._btn_min_dn,self._btn_sec_up,self._btn_sec_dn): btn.setStyleSheet(adj_st)
        # 开始/重置按钮
        main_st = ("QPushButton{background:rgba(70,62,110,0.55);color:#e0d8f8;border:1px solid rgba(100,90,150,0.65);border-radius:7px;font-size:14px;font-weight:600;padding:0 18px;}QPushButton:hover{background:rgba(90,80,140,0.78);}" if night else "QPushButton{background:rgba(138,122,80,0.50);color:#2c2510;border:1px solid rgba(138,122,80,0.65);border-radius:7px;font-size:14px;font-weight:600;padding:0 18px;}QPushButton:hover{background:rgba(158,140,96,0.78);}")
        self._btn_toggle.setStyleSheet(main_st); self._btn_reset_btn.setStyleSheet(main_st)

    def _reset(self):
        self._running=False; self._qtimer.stop(); self._total_ms=0; self._remain_ms=0
        self._btn_toggle.setText("开始"); self._min_lbl.setText("00"); self._sec_lbl.setText("00")
        fg="#e0d8f8" if self._night else "#2c2510"
        self._min_lbl.setStyleSheet(f"color:{fg};background:transparent;border:none;")
        self._sec_lbl.setStyleSheet(f"color:{fg};background:transparent;border:none;")

    def _tick(self):
        self._remain_ms-=100
        if self._remain_ms<=0:
            self._remain_ms=0; self._running=False; self._qtimer.stop()
            self._refresh_display(); self._btn_toggle.setText("开始")
            self._min_lbl.setStyleSheet("color:#e05050;background:transparent;border:none;")
            self._sec_lbl.setStyleSheet("color:#e05050;background:transparent;border:none;")
            try:
                rl=get_ripple(); scr=QApplication.primaryScreen().geometry()
                rl.start(scr.center().x(),scr.center().y(),QColor(220,80,60))
                self._play_countdown_sound()
            except Exception: pass
        else:
            if self._remain_ms<=10000:
                self._min_lbl.setStyleSheet("color:#e07010;background:transparent;border:none;")
                self._sec_lbl.setStyleSheet("color:#e07010;background:transparent;border:none;")
            self._refresh_display()

    def _play_countdown_sound(self):
        try:
            import os, threading, subprocess, sys
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base, 'sounds', 'daojishi.mp3')
            if not os.path.exists(path): return
            py_exe = sys.executable
            def _play():
                try:
                    code = (
                        'import pygame; pygame.mixer.init(); '
                        f'snd=pygame.mixer.Sound(r"{path}"); '
                        'import time; snd.play(); time.sleep(snd.get_length()+0.3)'
                    )
                    subprocess.run([py_exe, '-c', code],
                        timeout=30, creationflags=0x08000000)
                except Exception as e2:
                    print('cd sound err:', e2)
            threading.Thread(target=_play, daemon=True).start()
        except Exception as e:
            print('cd sound err:', e)

    def _refresh_display(self):
        ms=self._remain_ms; m=ms//60000; s=(ms%60000)//1000
        self._min_lbl.setText(f"{m:02d}"); self._sec_lbl.setText(f"{s:02d}")


class SlidingStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self._animating=False
    def slide_to(self, index):
        if self._animating or index==self.currentIndex(): self.setCurrentIndex(index); return
        cur=self.currentWidget(); nxt=self.widget(index)
        if not cur or not nxt: self.setCurrentIndex(index); return
        w,h=self.width(),self.height()
        nxt.setGeometry(0,h,w,h); nxt.show(); nxt.raise_(); self._animating=True
        out=QPropertyAnimation(cur,b"pos"); out.setDuration(200)
        out.setStartValue(QPoint(0,0)); out.setEndValue(QPoint(0,-h)); out.setEasingCurve(QEasingCurve.OutQuart)
        inp=QPropertyAnimation(nxt,b"pos"); inp.setDuration(200)
        inp.setStartValue(QPoint(0,h)); inp.setEndValue(QPoint(0,0)); inp.setEasingCurve(QEasingCurve.OutQuart)
        self._grp=QParallelAnimationGroup()
        self._grp.addAnimation(out); self._grp.addAnimation(inp)
        self._grp.finished.connect(lambda: self._done(index,cur)); self._grp.start()
    def _done(self,index,old): self.setCurrentIndex(index); old.hide(); old.move(0,0); self._animating=False


class SideNavBtn(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._text=text; self._night=False; self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
    def set_night(self,night): self._night=night; self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        if self.isChecked():
            bg=QColor(80,72,120,168) if self._night else QColor(200,188,150,178)
            bar=QColor(120,108,180,230) if self._night else QColor(138,122,80,230)
            p.fillRect(self.rect(),bg); p.fillRect(0,0,3,self.height(),bar)
            color=QColor(220,210,255) if self._night else QColor(44,37,16)
        else:
            hov=QColor(70,65,100,76) if self._night else QColor(210,200,165,76)
            if self.underMouse(): p.fillRect(self.rect(),hov)
            color=QColor(160,152,200) if self._night else QColor(100,90,60)
        font=QFont("Microsoft YaHei",11,QFont.Bold if self.isChecked() else QFont.Normal)
        p.setFont(font); fm=p.fontMetrics()
        chars=list(self._text); line_h=fm.height()+2; total_h=len(chars)*line_h
        y0=(self.height()-total_h)//2+fm.ascent()
        for i,ch in enumerate(chars):
            tw=fm.horizontalAdvance(ch); p.setPen(color)
            p.drawText((self.width()-tw)//2,y0+i*line_h,ch)


class TimerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dual=None; self._cd=None; self._flash=None
        self._build_ui()

    def _build_ui(self):
        from PyQt5.QtWidgets import QHBoxLayout,QVBoxLayout,QFrame,QWidget
        root=QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        sidebar=QWidget(); sidebar.setFixedWidth(44); self._sidebar=sidebar
        sidebar.setStyleSheet("QWidget{background:rgba(248,244,232,0.55);border-right:1px solid rgba(210,200,165,0.45);}")
        side_lay=QVBoxLayout(sidebar); side_lay.setContentsMargins(0,0,0,0); side_lay.setSpacing(0)
        self._sub_btns=[]; self._sub_stack=SlidingStack()
        dual=DualStopwatchPage(); cd=CountdownCard()
        self._dual=dual; self._cd=cd
        for i,(label,widget) in enumerate([("正计时",dual),("倒计时",cd)]):
            w=QWidget(); wl=QVBoxLayout(w); wl.setContentsMargins(4,4,4,4); wl.addWidget(widget)
            btn=SideNavBtn(label)
            btn.clicked.connect(lambda _,idx=i: self._switch_sub(idx))
            side_lay.addWidget(btn,1); self._sub_btns.append(btn); self._sub_stack.addWidget(w)
        root.addWidget(sidebar)
        content=QFrame(); content.setStyleSheet("QFrame{background:transparent;border:none;}")
        cl=QVBoxLayout(content); cl.setContentsMargins(0,0,0,0); cl.addWidget(self._sub_stack)
        root.addWidget(content,1)
        self._switch_sub(0)
        # 金色边框闪光覆盖层
        self._flash=BorderFlashOverlay(self)
        dual.action_triggered.connect(self._flash.start)
        cd.action_triggered.connect(self._flash.start)

    def _switch_sub(self,idx):
        self._sub_stack.slide_to(idx)
        for i,btn in enumerate(self._sub_btns): btn.setChecked(i==idx); btn.update()

    def is_counting(self):
        return (self._dual and self._dual.is_running()) or (self._cd and self._cd.is_running())

    def apply_night(self,night):
        if self._dual: self._dual.apply_night(night)
        if self._cd: self._cd.apply_night(night)
        bg="rgba(38,34,52,0.60)" if night else "rgba(248,244,232,0.55)"
        bd="rgba(80,75,110,0.45)" if night else "rgba(210,200,165,0.45)"
        self._sidebar.setStyleSheet(f"QWidget{{background:{bg};border-right:1px solid {bd};}}")
        for btn in self._sub_btns:
            if hasattr(btn,'set_night'): btn.set_night(night)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._flash: self._flash.setGeometry(self.rect())
