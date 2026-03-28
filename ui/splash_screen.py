import os
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QBrush,
    QPainterPath, QPen, QFont, QPixmap
)


class SplashScreen(QWidget):
    """启动页：浮球图标 + 标题 + 底部线形进度条（贴窗口底部）"""
    finished = pyqtSignal()

    _DURATION = 2400
    _STEP_MS  = 16

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().availableGeometry()
        self._w, self._h = 400, 240
        self.setFixedSize(self._w, self._h)
        self.move(
            (screen.width()  - self._w) // 2,
            (screen.height() - self._h) // 2,
        )
        self._progress = 0.0
        self._load_icon()
        self._build_ui()
        self._start()

    def _load_icon(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, 'pictures', 'icon.png')
        self._icon = None
        if os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                self._icon = pix.scaled(68, 68, Qt.KeepAspectRatio,
                                        Qt.SmoothTransformation)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 48, 0, 20)
        layout.setSpacing(0)

        # 图标区（paintEvent 绘制，QLabel 只占高度）
        self._icon_spacer = QLabel()
        self._icon_spacer.setFixedHeight(80)
        self._icon_spacer.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self._icon_spacer)

        self._title = QLabel('课堂点名计时器')
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setFont(QFont('Microsoft YaHei', 22, QFont.Bold))
        self._title.setStyleSheet('color:rgba(44,37,16,225); background:transparent;')
        layout.addWidget(self._title)

        self._sub = QLabel('化学计时器 V6.0')
        self._sub.setAlignment(Qt.AlignCenter)
        self._sub.setStyleSheet(
            'color:rgba(100,90,60,175); font-size:12px;'
            ' font-family:"Microsoft YaHei"; background:transparent;'
        )
        layout.addWidget(self._sub)
        layout.addStretch()
        # 进度条区域留在 paintEvent，底部 12px 处

    def _start(self):
        self._fade_in = QPropertyAnimation(self, b'windowOpacity')
        self._fade_in.setDuration(480)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.start()

        self._elapsed_ms = 0
        self._prog_timer = QTimer(self)
        self._prog_timer.setInterval(self._STEP_MS)
        self._prog_timer.timeout.connect(self._tick)
        self._prog_timer.start()

    def _tick(self):
        self._elapsed_ms += self._STEP_MS
        t = min(self._elapsed_ms / self._DURATION, 1.0)
        # ease-in-out cubic
        self._progress = 4*t**3 if t < 0.5 else 1 - (-2*t+2)**3/2
        self.update()
        if t >= 1.0:
            self._prog_timer.stop()
            self._fadeout()

    def _fadeout(self):
        anim = QPropertyAnimation(self, b'windowOpacity')
        anim.setDuration(360)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self._on_done)
        self._out_anim = anim
        anim.start()

    def _on_done(self):
        self.hide()
        self.finished.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self._w, self._h

        # 圆角卡片
        path = QPainterPath()
        path.addRoundedRect(14, 14, w - 28, h - 28, 20, 20)
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(255, 255, 253, 238))
        grad.setColorAt(1.0, QColor(248, 244, 230, 218))
        p.fillPath(path, QBrush(grad))
        p.setPen(QPen(QColor(215, 205, 168, 180), 1.2))
        p.drawPath(path)

        # 浮球图标（居中，顶部）
        if self._icon:
            iw, ih = self._icon.width(), self._icon.height()
            ix = (w - iw) // 2
            iy = 44
            # 轻微阴影圆
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(180, 170, 140, 40))
            p.drawEllipse(ix + 4, iy + ih - 6, iw - 8, 14)
            p.drawPixmap(ix, iy, self._icon)

        # 底部进度条（完全贴底，距边框内侧 12px）
        bar_h  = 2
        bar_y  = h - 14 - bar_h       # 距窗口底部 14px
        bar_x  = 30
        bar_w  = w - 60
        p.setPen(Qt.NoPen)
        # 轨道
        p.setBrush(QColor(215, 205, 170, 90))
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 1, 1)
        # 填充
        fill_w = int(bar_w * self._progress)
        if fill_w > 0:
            bg = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            bg.setColorAt(0.0, QColor(170, 150,  80, 210))
            bg.setColorAt(0.6, QColor(205, 185, 105, 235))
            bg.setColorAt(1.0, QColor(235, 215, 130, 255))
            p.setBrush(QBrush(bg))
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 1, 1)
            # 端点光晕
            tip = bar_x + fill_w
            gl = QLinearGradient(tip - 14, 0, tip + 4, 0)
            gl.setColorAt(0.0, QColor(255, 240, 155,   0))
            gl.setColorAt(1.0, QColor(255, 240, 155, 190))
            p.setBrush(QBrush(gl))
            p.drawRoundedRect(tip - 14, bar_y - 2, 18, bar_h + 4, 2, 2)
