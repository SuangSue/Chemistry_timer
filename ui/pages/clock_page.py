from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush


class ClockPage(QWidget):
    """实时时钟页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fullscreen_win = None
        self._night = False
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._update_time)
        self._timer.start()
        self._update_time()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(14)
        layout.addStretch()

        self._time_lbl = QLabel('00:00:00')
        self._time_lbl.setAlignment(Qt.AlignCenter)
        self._time_lbl.setFont(QFont('Microsoft YaHei', 64, QFont.Bold))
        self._time_lbl.setStyleSheet(
            'color:#2c2510; background:rgba(255,255,250,0.60);'
            'border-radius:16px; border:1px solid rgba(210,200,165,0.55); padding:16px 0;'
        )
        layout.addWidget(self._time_lbl)

        self._date_lbl = QLabel('')
        self._date_lbl.setAlignment(Qt.AlignCenter)
        self._date_lbl.setStyleSheet(
            'color:#6b6040; font-size:16px;'
            'font-family:"Microsoft YaHei"; background:transparent;'
        )
        layout.addWidget(self._date_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._fs_btn = QPushButton('\u5168\u5c4f\u663e\u793a')
        self._fs_btn.setCursor(Qt.PointingHandCursor)
        self._fs_btn.setFixedSize(110, 34)
        self._fs_btn.setStyleSheet(
            'QPushButton{background:rgba(200,188,150,0.55);color:#2c2510;'
            'border:1px solid rgba(200,188,150,0.70);border-radius:8px;'
            'font-size:13px;font-weight:600;font-family:"Microsoft YaHei";}'
            'QPushButton:hover{background:rgba(210,198,160,0.80);}'
        )
        self._fs_btn.clicked.connect(self._toggle_fullscreen)
        btn_row.addWidget(self._fs_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

    def apply_night(self, night):
        self._night = night
        if night:
            self._time_lbl.setStyleSheet(
                'color:#e0d8f8; background:rgba(40,36,60,0.65);'
                'border-radius:16px; border:1px solid rgba(90,80,130,0.55); padding:16px 0;'
            )
            self._date_lbl.setStyleSheet(
                'color:#b0a8d8; font-size:16px;'
                'font-family:"Microsoft YaHei"; background:transparent;'
            )
            self._fs_btn.setStyleSheet(
                'QPushButton{background:rgba(70,62,110,0.55);color:#e0d8f8;'
                'border:1px solid rgba(100,90,150,0.65);border-radius:8px;'
                'font-size:13px;font-weight:600;font-family:"Microsoft YaHei";}'
                'QPushButton:hover{background:rgba(90,80,140,0.78);}'
            )
        else:
            self._time_lbl.setStyleSheet(
                'color:#2c2510; background:rgba(255,255,250,0.60);'
                'border-radius:16px; border:1px solid rgba(210,200,165,0.55); padding:16px 0;'
            )
            self._date_lbl.setStyleSheet(
                'color:#6b6040; font-size:16px;'
                'font-family:"Microsoft YaHei"; background:transparent;'
            )
            self._fs_btn.setStyleSheet(
                'QPushButton{background:rgba(200,188,150,0.55);color:#2c2510;'
                'border:1px solid rgba(200,188,150,0.70);border-radius:8px;'
                'font-size:13px;font-weight:600;font-family:"Microsoft YaHei";}'
                'QPushButton:hover{background:rgba(210,198,160,0.80);}'
            )

    def _update_time(self):
        now = QDateTime.currentDateTime()
        self._time_lbl.setText(now.toString('HH:mm:ss'))
        self._date_lbl.setText(now.toString('yyyy\u5e74MM\u6708dd\u65e5  dddd'))
        if self._fullscreen_win and self._fullscreen_win.isVisible():
            self._fullscreen_win.update_time(now)

    def _toggle_fullscreen(self):
        if self._fullscreen_win and self._fullscreen_win.isVisible():
            self._fullscreen_win.close_with_anim()
        else:
            self._fullscreen_win = FullscreenClock()
            self._fullscreen_win.closed.connect(lambda: self._fs_btn.setText('\u5168\u5c4f\u663e\u793a'))
            self._fullscreen_win.show()
            self._fs_btn.setText('\u9000\u51fa\u5168\u5c4f')


class FullscreenClock(QWidget):
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 右上角退出按钮（固定位置）
        self._exit_btn = QPushButton('\u2715  \u9000\u51fa\u5168\u5c4f', self)
        self._exit_btn.setCursor(Qt.PointingHandCursor)
        self._exit_btn.setFixedSize(130, 38)
        self._exit_btn.setStyleSheet(
            'QPushButton{background:rgba(200,188,150,0.55);color:#2c2510;'
            'border:1px solid rgba(200,188,150,0.70);border-radius:10px;'
            'font-size:14px;font-weight:600;font-family:"Microsoft YaHei";}'
            'QPushButton:hover{background:rgba(210,198,160,0.85);}'
        )
        self._exit_btn.clicked.connect(self.close_with_anim)
        self._exit_btn.move(screen.width() - 150, 16)
        self._exit_btn.raise_()

        # 中心内容
        center = QVBoxLayout()
        center.setAlignment(Qt.AlignCenter)
        center.setSpacing(16)

        self._time_lbl = QLabel('00:00:00')
        self._time_lbl.setAlignment(Qt.AlignCenter)
        self._time_lbl.setFont(QFont('Microsoft YaHei', 120, QFont.Bold))
        self._time_lbl.setStyleSheet('color:rgba(44,37,16,230);background:transparent;')
        center.addWidget(self._time_lbl)

        self._date_lbl = QLabel('')
        self._date_lbl.setAlignment(Qt.AlignCenter)
        self._date_lbl.setStyleSheet(
            'color:rgba(100,90,55,200);font-size:28px;'
            'font-family:"Microsoft YaHei";background:transparent;'
        )
        center.addWidget(self._date_lbl)

        layout.addStretch()
        layout.addLayout(center)
        layout.addStretch()

        self.setWindowOpacity(0)
        self._in_anim = QPropertyAnimation(self, b'windowOpacity')
        self._in_anim.setDuration(400)
        self._in_anim.setStartValue(0.0)
        self._in_anim.setEndValue(1.0)
        self._in_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._in_anim.start()

    def update_time(self, dt):
        self._time_lbl.setText(dt.toString('HH:mm:ss'))
        self._date_lbl.setText(dt.toString('yyyy\u5e74MM\u6708dd\u65e5  dddd'))

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(255,253,245,245))
        grad.setColorAt(1.0, QColor(248,244,228,240))
        p.fillRect(self.rect(), QBrush(grad))

    def close_with_anim(self):
        anim = QPropertyAnimation(self, b'windowOpacity')
        anim.setDuration(280)
        anim.setStartValue(1.0); anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.close)
        anim.finished.connect(self.closed)
        self._out_anim = anim
        anim.start()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Space):
            self.close_with_anim()
