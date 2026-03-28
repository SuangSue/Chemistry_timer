# ui/pick_flash_overlay.py - 抽签完毕浅蓝色线条动画
import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen


class PickFlashOverlay(QWidget):
    """抽签完毕浅蓝色边框线条动画，覆盖在主窗口上"""
    def __init__(self, parent_ref):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._parent_ref = parent_ref
        self._progress = 0.0
        self._fast_mode = False
        self._timer = QTimer(self)
        self._timer.setInterval(8)  # ~120fps 高帧率
        self._timer.timeout.connect(self._tick)
        self.hide()

    def set_fast_mode(self, v): self._fast_mode = v

    def start(self):
        if self._fast_mode: return
        self._progress = 0.0
        try:
            w = self._parent_ref
            while w.parent() and not w.isWindow(): w = w.parent()
            self.setGeometry(w.geometry())
        except Exception: pass
        self.show(); self.raise_(); self._timer.start()

    def _tick(self):
        self._progress = min(1.0, self._progress + 1.0 / 30)  # ~240ms完成
        self.update()
        if self._progress >= 1.0:
            self._timer.stop()
            QTimer.singleShot(120, self.hide)

    def paintEvent(self, event):
        if self._progress <= 0: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        m = 14; r = 16
        prog = self._progress
        DELAY = 0.45
        tail = max(0.0, (prog - DELAY) / (1.0 - DELAY)) if prog > DELAY else 0.0
        tl = float(W - 2*m - 2*r); ll = float(H - 2*m - 2*r)
        rl = float(H - 2*m - 2*r); bl = float(W - 2*m - 2*r)
        aq = math.pi / 2 * r
        pA = aq + tl + aq + ll
        pB = rl + aq + bl
        NA = 24

        def arc(cx, cy, rad, a0, a1):
            return [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * k / NA)),
                     cy + rad * math.sin(math.radians(a0 + (a1 - a0) * k / NA)))
                    for k in range(NA + 1)]

        def fullA():
            pts = arc(W-m-r, m+r, r, 0, -90)
            pts += [(W-m-r - tl*k/NA, m) for k in range(1, NA+1)]
            pts += arc(m+r, m+r, r, -90, -180)[1:]
            pts += [(m, m+r + ll*k/NA) for k in range(1, NA+1)]
            return pts

        def fullB():
            pts = [(W-m, m+r + rl*k/NA) for k in range(NA+1)]
            pts += arc(W-m-r, H-m-r, r, 0, 90)[1:]
            pts += [(W-m-r - bl*k/NA, H-m) for k in range(1, NA+1)]
            return pts

        def clip(pts, frac, plen):
            if frac <= 0: return [pts[0]]
            dist = frac * plen; res = [pts[0]]; acc = 0.0
            for i in range(1, len(pts)):
                dx = pts[i][0] - pts[i-1][0]; dy = pts[i][1] - pts[i-1][1]
                s = (dx*dx + dy*dy) ** 0.5
                if acc + s >= dist:
                    f = (dist - acc) / s if s > 0 else 0
                    res.append((pts[i-1][0] + dx*f, pts[i-1][1] + dy*f)); break
                acc += s; res.append(pts[i])
            return res

        def draw(hp, tp):
            nt = len(tp)
            seg = hp[max(0, nt-1):]
            if len(seg) < 2: seg = hp[-2:]
            n = len(seg)
            for i in range(n - 1):
                t = i / max(n - 2, 1)
                # 浅蓝色渐变
                if t < 0.18:
                    rc, gc, bc = 100, 180, 255; ac = int(255 * t / 0.18)
                elif t < 0.38:
                    f = (t - 0.18) / 0.20
                    rc = int(100 + (180 - 100) * f); gc = int(180 + (220 - 180) * f); bc = 255; ac = 255
                elif t < 0.78:
                    rc, gc, bc = 140, 210, 255; ac = 255
                else:
                    f = (t - 0.78) / 0.22
                    rc = int(140 + (200 - 140) * f); gc = int(210 + (230 - 210) * f); bc = 255; ac = 255
                # 增加线条粗度：从 4.2 增加到 7.0
                pen = QPen(QColor(rc, gc, bc, ac), 7.0)
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.drawLine(int(seg[i][0]), int(seg[i][1]), int(seg[i+1][0]), int(seg[i+1][1]))

        fa = fullA(); fb = fullB()
        ha = clip(fa, prog, pA); ta = clip(fa, tail, pA)
        hb = clip(fb, prog, pB); tb = clip(fb, tail, pB)
        draw(ha, ta); draw(hb, tb)
