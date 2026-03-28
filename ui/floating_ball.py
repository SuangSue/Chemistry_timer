import os
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QPixmap, QBrush, QColor, QPen, QRadialGradient, QPainterPath


class FloatingBall(QWidget):
    clicked = pyqtSignal(QPoint)
    moved   = pyqtSignal(object)
    BALL_SIZE  = 56
    SNAP_DELAY = 30000  # 30秒无操作后贴边
    HIDE_DELAY = 3000   # 贴边后3秒没入
    EDGE_THRESHOLD = 30  # 距边缘30px以内视为贴边区域

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None; self._press_pos = None
        self._is_dragging = False; self._drag_threshold = 6
        self._hover = False; self._pressed = False
        self._faded = False; self._snapped = False; self._main_visible = False
        # 状态：'free'(自由) / 'snapping'(贴边计时中) / 'snapped'(已贴边) / 'hidden'(已没入)
        self._state = 'free'
        self._setup_window(); self._load_icon(); self._setup_anim()
        # 贴边计时器（30秒）
        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.setInterval(self.SNAP_DELAY)
        self._snap_timer.timeout.connect(self._auto_snap)
        # 没入计时器（3秒，仅在贴边后启动）
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(self.HIDE_DELAY)
        self._hide_timer.timeout.connect(self._do_hide)

    def _setup_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self.BALL_SIZE + 16, self.BALL_SIZE + 16)
        self.setMouseTracking(True)

    def _load_icon(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, 'pictures', 'icon.png')
        self._icon = None
        if os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                sz = self.BALL_SIZE - 10
                self._icon = pix.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _setup_anim(self):
        self._pos_anim = QPropertyAnimation(self, b'pos')
        self._pos_anim.setDuration(300); self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._op_anim = QPropertyAnimation(self, b'windowOpacity')
        self._op_anim.setDuration(500); self._op_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _screen_rect(self):
        return QApplication.primaryScreen().availableGeometry()

    def _clamp_pos(self, x, y):
        sr = self._screen_rect(); w, h = self.width(), self.height()
        return max(sr.left(), min(x, sr.right()-w)), max(sr.top(), min(y, sr.bottom()-h))

    def _get_edge_distance(self):
        """返回 (距左边, 距右边)"""
        sr = self._screen_rect(); geo = self.geometry()
        dl = geo.left() - sr.left()
        dr = sr.right() - geo.right()
        return dl, dr

    def _is_in_snap_zone(self):
        """检查是否在贴边区域内（距边缘 <= EDGE_THRESHOLD）"""
        dl, dr = self._get_edge_distance()
        return min(dl, dr) <= self.EDGE_THRESHOLD

    def _is_far_from_edge(self):
        """检查是否远离边缘（距边缘 > EDGE_THRESHOLD）"""
        dl, dr = self._get_edge_distance()
        return min(dl, dr) > self.EDGE_THRESHOLD

    def set_main_visible(self, visible):
        self._main_visible = visible
        if visible and self._state == 'hidden': 
            self._unfade()

    def _auto_snap(self):
        """30秒无操作后自动贴边"""
        if self._main_visible or self._state != 'snapping': return
        self._do_snap()

    def _do_snap(self):
        """执行贴边：吸附到边缘，启动没入计时"""
        sr = self._screen_rect(); geo = self.geometry(); bw = geo.width()
        dl, dr = self._get_edge_distance()
        half = bw // 2
        # 计算贴边位置（完全贴边）
        if dl <= dr:
            tx_normal = sr.left() - half + 20
            self._tx_faded = sr.left() - half
        else:
            tx_normal = sr.right() - half - 20
            self._tx_faded = sr.right() - half
        ty = max(sr.top(), min(geo.y(), sr.bottom() - geo.height()))
        # 动画移动到贴边位置
        self._pos_anim.stop()
        self._pos_anim.setStartValue(geo.topLeft())
        self._pos_anim.setEndValue(QPoint(tx_normal, ty))
        self._pos_anim.start()
        self._state = 'snapped'
        self._snap_timer.stop()
        self._hide_timer.start()  # 启动3秒没入计时

    def _do_hide(self):
        """没入：靠近屏幕的那一半没入屏幕边缘，半透明"""
        if self._main_visible or self._state != 'snapped': return
        self._state = 'hidden'
        self._faded = True
        self._op_anim.stop()
        self._op_anim.setStartValue(self.windowOpacity())
        self._op_anim.setEndValue(0.45)
        self._op_anim.start()
        # 没入边缘一半：靠近屏幕的那一半没入
        if hasattr(self, "_tx_faded"):
            self._pos_anim.stop()
            self._pos_anim.setStartValue(self.pos())
            # _tx_faded 是完全贴边位置，没入时移动到该位置
            self._pos_anim.setEndValue(QPoint(self._tx_faded, self.y()))
            self._pos_anim.start()

    def _unfade(self):
        """从没入状态恢复到贴边状态"""
        if self._state != 'hidden': return
        self._state = 'snapped'
        self._faded = False; self._hide_timer.stop()
        self._op_anim.stop()
        self._op_anim.setStartValue(self.windowOpacity())
        self._op_anim.setEndValue(1.0); self._op_anim.start()
        # 恢复到贴边位置
        if hasattr(self, "_tx_faded"):
            from PyQt5.QtCore import QPoint as _P
            tx_normal = self._tx_faded + (20 if self.x() <= self._tx_faded + 2 else -20)
            self._pos_anim.stop()
            self._pos_anim.setStartValue(self.pos())
            self._pos_anim.setEndValue(_P(tx_normal, self.y()))
            self._pos_anim.start()

    def snap_to_edge(self):
        """公共接口：立即贴边（由外部调用）"""
        self._do_snap()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        pad = 8; r = self.BALL_SIZE//2
        cx = self.width()//2; cy = self.height()//2
        for i in range(4,0,-1):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(80,65,30,18-i*3))
            p.drawEllipse(int(cx-r+i*1.5-i),int(cy-r+i*1.5+i),self.BALL_SIZE+i*2,self.BALL_SIZE+i*2)
        path = QPainterPath()
        path.addEllipse(pad, pad, self.BALL_SIZE, self.BALL_SIZE)
        base_a = 210 if self._pressed else (238 if self._hover else 224)
        grad = QRadialGradient(cx-r*0.2, cy-r*0.28, r*1.05)
        grad.setColorAt(0.0, QColor(255,254,250,base_a))
        grad.setColorAt(0.6, QColor(250,246,235,base_a-12))
        grad.setColorAt(1.0, QColor(240,234,218,base_a-26))
        p.setClipPath(path); p.fillPath(path, QBrush(grad))
        hl = QRadialGradient(cx-r*0.25, cy-r*0.4, r*0.48)
        hl.setColorAt(0.0, QColor(255,255,255,120))
        hl.setColorAt(1.0, QColor(255,255,255,0))
        p.fillPath(path, QBrush(hl)); p.setClipping(False)
        pen_c = QColor(175,163,128,210) if self._hover else QColor(198,188,158,170)
        p.setPen(QPen(pen_c,1.2))
        p.drawEllipse(pad+1,pad+1,self.BALL_SIZE-2,self.BALL_SIZE-2)
        if self._icon:
            iw,ih = self._icon.width(),self._icon.height()
            p.drawPixmap(cx-iw//2, cy-ih//2, self._icon)
        else:
            p.setPen(QColor(80,70,40))
            f = p.font(); f.setPixelSize(20); f.setBold(True); p.setFont(f)
            p.drawText(pad,pad,self.BALL_SIZE,self.BALL_SIZE,Qt.AlignCenter,"点")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos  = event.globalPos()
            self._drag_pos   = event.globalPos() - self.frameGeometry().topLeft()
            self._is_dragging = False
            self._pressed = True
            # 点击时恢复透明度（如果已没入）
            if self._state == 'hidden': self._unfade()
            # 点击时停止所有计时
            self._snap_timer.stop(); self._hide_timer.stop()
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos is not None:
            if (event.globalPos()-self._press_pos).manhattanLength() > self._drag_threshold:
                self._is_dragging = True
            if self._is_dragging:
                raw = event.globalPos() - self._drag_pos
                x, y = self._clamp_pos(raw.x(), raw.y())
                self.move(x, y)
                self.moved.emit(self.geometry())
                # 拖动时停止所有计时
                self._snap_timer.stop(); self._hide_timer.stop()
                # 拖动后检查位置
                if self._is_in_snap_zone():
                    # 仍在贴边区域，保持贴边状态
                    self._state = 'snapped'
                else:
                    # 移出贴边区域，进入自由状态并启动贴边计时
                    self._state = 'free'
                    self._snap_timer.start()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = False; self.update()
            if not self._is_dragging:
                center = self.geometry().center()
                QTimer.singleShot(80, lambda: self.clicked.emit(center))
            self._drag_pos = None; self._is_dragging = False
            # 释放时根据状态处理
            if self._state == 'snapped':
                # 已贴边，启动没入计时
                self._hide_timer.start()
            elif self._state == 'free':
                # 自由状态，启动贴边计时
                self._snap_timer.start()

    def enterEvent(self, event):
        """鼠标悬停：停止计时，如果已没入则恢复"""
        self._hover = True
        self._snap_timer.stop(); self._hide_timer.stop()
        if self._state == 'hidden': 
            self._unfade()  # 恢复到贴边状态
            # 没入状态下悬停，向屏幕内侧移动
            dl, dr = self._get_edge_distance()
            offset = -8 if dr < dl else 8
            geo = self.geometry()
            self._pos_anim.stop()
            self._pos_anim.setStartValue(geo.topLeft())
            self._pos_anim.setEndValue(QPoint(geo.x() + offset, geo.y()))
            self._pos_anim.setDuration(150)
            self._pos_anim.start()
        self.update()

    def leaveEvent(self, event):
        """鼠标离开：根据状态启动相应计时"""
        self._hover = False
        if self._state == 'snapped':
            # 已贴边，启动没入计时
            self._hide_timer.start()
        elif self._state == 'free':
            # 自由状态，启动贴边计时
            self._snap_timer.start()
        self.update()

    def move_to_default(self, screen_rect):
        x = max(screen_rect.left(), 20)
        y = screen_rect.height() - self.height() - 80
        self.move(x, y)
        self._state = 'free'
        self._snap_timer.start()  # 启动30秒贴边计时
