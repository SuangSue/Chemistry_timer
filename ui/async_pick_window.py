# ui/async_pick_window.py
import math
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPainterPath, QPen, QFont, QLinearGradient


class RippleOverlay(QWidget):
    """独立全屏涟漪覆盖层，显示在异步窗口下层"""
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._cx = 0; self._cy = 0
        self._radius = 0.0; self._alpha = 0
        self._timer = QTimer(self); self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self, cx, cy):
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        self._cx = cx; self._cy = cy
        self._radius = 0.0; self._alpha = 220
        self.show(); self.update(); self._timer.start()

    def _tick(self):
        self._radius += 400 / (0.6 * 1000 / 16)
        self._alpha = max(0, int(220 * (1 - self._radius / 400)))
        if self._radius >= 400:
            self._timer.stop(); self.hide()
            self._radius = 0.0; self._alpha = 0
        self.update()

    def paintEvent(self, event):
        if self._alpha <= 0: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = int(self._radius)
        color = QColor(255, 255, 255, self._alpha)
        p.setPen(QPen(color, 2.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(self._cx - r, self._cy - r, r * 2, r * 2)


_ripple_overlay = None
def _get_ripple_overlay():
    global _ripple_overlay
    if _ripple_overlay is None:
        _ripple_overlay = RippleOverlay()
    return _ripple_overlay


class AsyncPickWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._night = False
        self._fast_mode = False
        self._opacity = 0.95
        self._line_progress = 0.0
        self._tail_progress = 0.0
        self._hide_timer = QTimer(self); self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_hide)
        self._line_timer = QTimer(self); self._line_timer.setInterval(16)
        self._line_timer.timeout.connect(self._line_tick)
        self.setFixedSize(320, 160)
        self._build_ui()
        self._setup_anims()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(0)
        # 名字垂直居中于整个窗口
        lay.addStretch(2)
        self._result_lbl = QLabel('\u2014')
        self._result_lbl.setAlignment(Qt.AlignCenter)
        self._result_lbl.setFont(QFont('Microsoft YaHei', 30, QFont.Bold))
        self._result_lbl.setStyleSheet('color:#2c2510;background:transparent;border:none;')
        self._result_lbl.setWordWrap(True)
        lay.addWidget(self._result_lbl)
        lay.addStretch(2)
        self._sub_lbl = QLabel('\u5316\u5b66\u8ba1\u65f6\u5668V6.0  |  \u5171 0 \u4eba')
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet('font-size:10px;color:rgba(160,150,120,160);background:transparent;border:none;')
        self._sub_lbl.setFixedHeight(20)
        lay.addWidget(self._sub_lbl)
        lay.addSpacing(10)

    def _setup_anims(self):
        self._op_anim = QPropertyAnimation(self, b'windowOpacity')
        self._op_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pos_anim = QPropertyAnimation(self, b'pos')
        self._pos_anim.setEasingCurve(QEasingCurve.OutBack)

    def set_opacity(self, opacity):
        """同步主窗口透明度"""
        self._opacity = max(0.3, opacity)

    def set_night(self, night):
        self._night = night; self.update()
        fg = '#e0d8f8' if night else '#2c2510'
        sub = 'rgba(160,150,200,140)' if night else 'rgba(160,150,120,160)'
        self._result_lbl.setStyleSheet(f'color:{fg};background:transparent;border:none;')
        self._sub_lbl.setStyleSheet(f'font-size:10px;color:{sub};background:transparent;border:none;')

    def set_fast_mode(self, v): self._fast_mode = v

    def set_display_duration(self, secs):
        """设置窗口显示时长（秒），默认1.75"""
        self._display_ms = max(500, int(secs * 1000))

    def _get_display_ms(self):
        return getattr(self, '_display_ms', 1750)

    def set_roster_info(self, roster_name, count):
        sub = 'rgba(160,150,200,140)' if self._night else 'rgba(160,150,120,160)'
        self._sub_lbl.setText(f'\u5316\u5b66\u8ba1\u65f6\u5668V6.0  |  \u5171 {count} \u4eba')
        self._sub_lbl.setStyleSheet(f'font-size:10px;color:{sub};background:transparent;border:none;')

    def show_result(self, names):
        self._result_lbl.setText('  '.join(names) if names else '\u2014')
        screen = QApplication.primaryScreen().availableGeometry()
        cx = screen.center().x() - self.width() // 2
        cy = screen.center().y() - self.height() // 2
        final_pos = QPoint(cx, cy); start_pos = QPoint(cx, cy - 40)
        self.move(start_pos)
        if self._fast_mode:
            self.setWindowOpacity(self._opacity); self.move(final_pos); self.show()
            self._hide_timer.start(self._get_display_ms()); return
        self.setWindowOpacity(0.0); self.show(); self.raise_()
        self._op_anim.stop(); self._op_anim.setDuration(350)
        self._op_anim.setStartValue(0.0); self._op_anim.setEndValue(self._opacity); self._op_anim.start()
        self._pos_anim.stop(); self._pos_anim.setDuration(420)
        self._pos_anim.setStartValue(start_pos); self._pos_anim.setEndValue(final_pos); self._pos_anim.start()
        self._line_progress = 0.0; self._tail_progress = 0.0; self._line_timer.start()
        # 启动独立涟漪覆盖层，圆心在窗口中央
        try:
            overlay = _get_ripple_overlay()
            win_cx = final_pos.x() + self.width() // 2
            win_cy = final_pos.y() + self.height() // 2
            overlay.start(win_cx, win_cy)
            self.raise_()  # 确保异步窗口在涟漪上层
        except Exception as e:
            print('ripple err:', e)
        self._hide_timer.start(self._get_display_ms() + 450)

    def _line_tick(self):
        # 头部 0~1 用 0.75s 走完整路径，尾部从 0.3 开始追赶，总时长 2s
        dt = 16.0
        self._line_progress = min(1.0, self._line_progress + dt / 750)
        self._tail_progress = min(1.0, self._tail_progress + dt / 1400)
        self.update()
        if self._line_progress >= 1.0 and self._tail_progress >= 1.0:
            self._line_timer.stop()

    def _start_hide(self):
        self._line_timer.stop()
        if self._fast_mode: self.hide(); return
        self._op_anim.stop(); self._op_anim.setDuration(260)
        self._op_anim.setStartValue(self.windowOpacity()); self._op_anim.setEndValue(0.0)
        self._op_anim.finished.connect(self._on_hide_done)
        self._pos_anim.stop(); self._pos_anim.setDuration(260)
        self._pos_anim.setStartValue(self.pos())
        self._pos_anim.setEndValue(QPoint(self.x(), self.y() - 28))
        self._pos_anim.setEasingCurve(QEasingCurve.InCubic); self._pos_anim.start()
        self._op_anim.start()

    def _on_hide_done(self):
        try: self._op_anim.finished.disconnect(self._on_hide_done)
        except Exception: pass
        self.hide(); self._pos_anim.setEasingCurve(QEasingCurve.OutBack)

    def is_busy(self):
        "`Returns True if window is showing (block new picks)"
        return self.isVisible()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        n = self._night
        path = QPainterPath(); path.addRoundedRect(3, 3, W - 6, H - 6, 18, 18)
        if n:
            grad = QLinearGradient(0, 0, 0, H)
            grad.setColorAt(0.0, QColor(45, 40, 68, 242))
            grad.setColorAt(1.0, QColor(30, 26, 50, 242))
        else:
            grad = QLinearGradient(0, 0, 0, H)
            grad.setColorAt(0.0, QColor(255, 253, 245, 246))
            grad.setColorAt(1.0, QColor(246, 242, 226, 246))
        p.fillPath(path, QBrush(grad))
        p.setPen(QPen(QColor(110, 100, 160, 160) if n else QColor(208, 198, 162, 190), 1.4))
        p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 50 if n else 110), 0.8))
        p.drawLine(22, 4, W - 22, 4)
        if self._line_progress > 0:
            self._draw_lines(p, W, H, n, self._line_progress, self._tail_progress)

    def _draw_lines(self, p, W, H, night, head_prog, tail_prog):
        import math
        m = 3; r = 18
        # 颜色：头部蓝色，尾部白色/浅色
        head_col = QColor(80, 160, 255, 240)   # 蓝
        tail_col = QColor(240, 240, 255, 200)  # 接近白

        def arc_pts(cx, cy, rad, a0, a1, segs=20):
            return [(cx + rad * math.cos(math.radians(a0 + (a1-a0)*i/segs)),
                     cy + rad * math.sin(math.radians(a0 + (a1-a0)*i/segs)))
                    for i in range(segs+1)]

        # 线1: 上边中点->右->右上弧->下->右下弧->下边向左延伸
        def line1_path():
            pts = [(W/2, m)]
            pts += arc_pts(W-m-r, m+r, r, -90, 0)[1:]
            pts += [(W-m, m+r+(H-2*m-2*r)*k/16) for k in range(1,17)]
            pts += arc_pts(W-m-r, H-m-r, r, 0, 90)[1:]
            pts += [(W-m-r-(W-2*m-2*r+120)*k/20, H-m) for k in range(1,21)]
            return pts

        # 线2: 下边中点->左->左下弧->上->左上弧->上边向右延伸
        def line2_path():
            pts = [(W/2, H-m)]
            pts += arc_pts(m+r, H-m-r, r, 90, 180)[1:]
            pts += [(m, H-m-r-(H-2*m-2*r)*k/16) for k in range(1,17)]
            pts += arc_pts(m+r, m+r, r, 180, 270)[1:]
            pts += [(m+r+(W-2*m-2*r+120)*k/20, m) for k in range(1,21)]
            return pts

        def plen(pts):
            s=0.0
            for i in range(1,len(pts)):
                dx=pts[i][0]-pts[i-1][0]; dy=pts[i][1]-pts[i-1][1]
                s+=math.sqrt(dx*dx+dy*dy)
            return s

        def clip(pts, frac):
            if frac<=0: return pts[:1]
            total=plen(pts); dist=frac*total
            res=[pts[0]]; acc=0.0
            for i in range(1,len(pts)):
                dx=pts[i][0]-pts[i-1][0]; dy=pts[i][1]-pts[i-1][1]
                s=math.sqrt(dx*dx+dy*dy)
                if acc+s>=dist:
                    f=(dist-acc)/s if s>0 else 0
                    res.append((pts[i-1][0]+dx*f,pts[i-1][1]+dy*f)); break
                acc+=s; res.append(pts[i])
            return res

        full1=line1_path(); full2=line2_path()
        # 头部走前80%，尾部以同比例的延迟追赶
        main_frac=0.80
        h_frac = head_prog * main_frac + max(0, head_prog-1.0)*(1-main_frac)
        h_frac = min(1.0, head_prog)  # 简化：头部直接用 head_prog
        t_frac = min(1.0, tail_prog)

        h1=clip(full1, h_frac); t1=clip(full1, t_frac)
        h2=clip(full2, h_frac); t2=clip(full2, t_frac)

        def draw_between(head_pts, tail_pts):
            # 只画从尾端到头端的线段
            nh=len(head_pts); nt=len(tail_pts)
            # 取头部完整点集，从尾部截断点开始画
            seg=head_pts[max(0,nt-1):]
            if len(seg)<2 and len(head_pts)>=2: seg=head_pts[-2:]
            n_=len(seg)
            for i in range(n_-1):
                t=i/max(n_-2,1)
                rc=int(head_col.red()*(1-t)+tail_col.red()*t)
                gc=int(head_col.green()*(1-t)+tail_col.green()*t)
                bc=int(head_col.blue()*(1-t)+tail_col.blue()*t)
                ac=int(head_col.alpha()*(1-t)+tail_col.alpha()*t)
                pen=QPen(QColor(rc,gc,bc,ac),5.5); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
                p.drawLine(int(seg[i][0]),int(seg[i][1]),int(seg[i+1][0]),int(seg[i+1][1]))

        draw_between(h1,t1); draw_between(h2,t2)
