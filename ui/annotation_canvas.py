# ui/annotation_canvas.py - 全屏透明批注画布 + 白板（含底部工具栏）
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush


COLOR_MAP = {
    'red':   QColor(220, 50, 50, 220),
    'blue':  QColor(50, 100, 220, 220),
    'black': QColor(30, 30, 30, 220),
}


class AnnotationCanvas(QWidget):
    """全屏透明批注画布，置顶，不挡工具栏"""
    closed = pyqtSignal()
    ball_raise_needed = pyqtSignal()  # 绘制后需要置顶浮球

    def __init__(self, exclude_geo=None, parent=None):
        super().__init__(None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._exclude_geo = exclude_geo
        self._strokes = []
        self._cur_stroke = []
        self._color = QColor(30, 30, 30, 220)
        self._width = 4
        self._mode = 'draw'
        self._drawing = False
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.x(), screen.y())
        self.resize(screen.width(), screen.height())

    def set_mode(self, mode):
        self._mode = mode
        if mode == 'select':
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.setCursor(Qt.CrossCursor if mode == 'draw' else Qt.CrossCursor)
        self.update()

    def set_color(self, color_key):
        self._color = COLOR_MAP.get(color_key, QColor(30, 30, 30, 220))

    def clear_strokes(self):
        self._strokes.clear()
        self._cur_stroke.clear()
        self.update()

    def set_exclude_geo(self, geo):
        self._exclude_geo = geo

    def mousePressEvent(self, e):
        if self._mode == 'select': return
        if e.button() == Qt.LeftButton:
            if self._in_exclude(e.pos()): return
            self._drawing = True
            self._cur_stroke = [QPoint(e.pos())]
            self.update()

    def mouseMoveEvent(self, e):
        if not self._drawing: return
        if self._in_exclude(e.pos()): return
        if self._mode == 'eraser':
            self._erase_near(e.pos())
        else:
            self._cur_stroke.append(QPoint(e.pos()))
        self.update()

    def mouseReleaseEvent(self, e):
        if not self._drawing: return
        self._drawing = False
        if self._mode == 'draw' and len(self._cur_stroke) > 1:
            self._strokes.append((list(self._cur_stroke), QColor(self._color), self._width))
        self._cur_stroke.clear()
        self.update()
        self.ball_raise_needed.emit()  # 绘制后置顶浮球

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for pts, color, width in self._strokes:
            pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            for i in range(1, len(pts)):
                p.drawLine(pts[i-1], pts[i])
        if self._cur_stroke and self._mode == 'draw':
            pen = QPen(self._color, self._width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            for i in range(1, len(self._cur_stroke)):
                p.drawLine(self._cur_stroke[i-1], self._cur_stroke[i])

    def _in_exclude(self, pos):
        if self._exclude_geo is None: return False
        gpos = self.mapToGlobal(pos)
        return self._exclude_geo.contains(gpos)

    def _erase_near(self, pos, radius=24):
        gpos = self.mapToGlobal(pos)
        self._strokes = [
            stroke for stroke in self._strokes
            if not any(
                (self.mapToGlobal(pt).x()-gpos.x())**2 +
                (self.mapToGlobal(pt).y()-gpos.y())**2 < radius**2
                for pt in stroke[0]
            )
        ]


class WhiteboardToolbar(QWidget):
    """白板底部横向工具栏，与浮球工具栏功能一致"""
    btn_clicked = pyqtSignal(str)
    color_changed = pyqtSignal(str)

    BTNS = [
        ('whiteboard', '\u25a1', '\u9690\u85cf\u767d\u677f'),
        ('pick',       '\u2684', '\u968f\u673a\u62bd\u7b7e'),
        ('select',     '\u2d54', '\u9009\u62e9'),
        ('annotate',   '\u270d', '\u6279\u6ce8'),
        ('eraser',     '\u25cb', '\u6a61\u76ae'),
        ('clear',      '\u2716', '\u6e05\u7a7a'),
    ]
    COLORS = [('red','\u7ea2'),('blue','\u84dd'),('black','\u9ed1')]

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._selected = 'annotate'
        self._night = False
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(6)
        self._capsule = QWidget(self)
        cap_lay = QHBoxLayout(self._capsule)
        cap_lay.setContentsMargins(8, 6, 8, 6)
        cap_lay.setSpacing(6)
        self._btns = {}
        for bid, icon, tip in self.BTNS:
            btn = QPushButton(icon, self._capsule)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(36, 36)
            btn.setCheckable(True)
            if bid == self._selected:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, b=bid: self._on_btn(b))
            cap_lay.addWidget(btn)
            self._btns[bid] = btn
        lay.addWidget(self._capsule)
        self.adjustSize()
        self._update_style()

    def _on_btn(self, bid):
        if bid in ('annotate', 'select', 'eraser'):
            self._selected = bid
            self._update_checked()
        self.btn_clicked.emit(bid)

    def _update_checked(self):
        for bid, btn in self._btns.items():
            btn.setChecked(bid == self._selected)
        self._update_style()

    def set_selected(self, bid):
        self._selected = bid
        self._update_checked()

    def _update_style(self):
        cap_bg = 'rgba(40,38,55,0.93)' if self._night else 'rgba(255,253,245,0.96)'
        cap_bd = 'rgba(90,82,130,0.72)' if self._night else 'rgba(210,198,158,0.80)'
        btn_bg = 'rgba(60,55,85,0.82)' if self._night else 'rgba(245,240,225,0.90)'
        btn_fg = '#d8d0f8' if self._night else '#3a3220'
        btn_hov = 'rgba(90,82,130,0.82)' if self._night else 'rgba(218,205,165,0.94)'
        btn_chk = 'rgba(120,108,180,0.90)' if self._night else 'rgba(138,122,80,0.85)'
        btn_chk_fg = '#ffffff' if self._night else '#fff8e8'
        self._capsule.setStyleSheet(
            f'QWidget{{background:{cap_bg};border:1.5px solid {cap_bd};border-radius:24px;}}'
        )
        for btn in self._btns.values():
            btn.setStyleSheet(
                f'QPushButton{{background:{btn_bg};color:{btn_fg};border:none;border-radius:17px;font-size:16px;}}'
                f'QPushButton:hover{{background:{btn_hov};}}'
                f'QPushButton:checked{{background:{btn_chk};color:{btn_chk_fg};}}'
            )

    def show_at_bottom(self):
        """在屏幕底部居中显示工具栏"""
        screen = QApplication.primaryScreen().geometry()
        # 固定尺寸：6个按钮*36px + 间距 + 边距
        btn_count = len(self.BTNS)
        w = btn_count * 36 + (btn_count - 1) * 6 + 16 + 24  # cap内边距+外边距
        h = 60
        cap_w = btn_count * 36 + (btn_count - 1) * 6 + 16
        self.setFixedSize(w, h)
        self._capsule.setFixedSize(cap_w, 48)
        x = screen.center().x() - w // 2
        y = screen.bottom() - h - 20
        self.move(x, y)
        self.show()
        self.raise_()
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(80, self.raise_)
        QTimer.singleShot(300, self.raise_)

    def apply_night(self, night):
        self._night = night
        self._update_style()


class WhiteboardCanvas(QWidget):
    """置顶深绿色白板画布，支持在上面批注"""
    toolbar_btn = pyqtSignal(str)  # 转发底部工具栏的按钮事件
    ball_raise_needed = pyqtSignal()  # 绘制后需要置顶浮球

    def __init__(self, parent=None):
        super().__init__(None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._bg_color = QColor(22, 65, 38, 252)
        self._strokes = []
        self._cur_stroke = []
        self._color = QColor(255, 255, 255, 230)
        self._width = 4
        self._drawing = False
        self._mode = 'draw'  # 'draw'|'eraser'|'select'
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.x(), screen.y())
        self.resize(screen.width(), screen.height())
        # 底部工具栏
        self._toolbar = WhiteboardToolbar()
        self._toolbar.btn_clicked.connect(self._on_toolbar_btn)
        self._toolbar.color_changed.connect(self.set_pen_color)

    def _on_toolbar_btn(self, bid):
        if bid == 'annotate':
            self._mode = 'draw'
            self.setCursor(Qt.CrossCursor)
        elif bid == 'select':
            self._mode = 'select'
            self.setCursor(Qt.ArrowCursor)
        elif bid == 'eraser':
            self._mode = 'eraser'
            self.setCursor(Qt.CrossCursor)
        elif bid == 'clear':
            self.clear_strokes()
            self._mode = 'select'
            self._toolbar.set_selected('select')
        else:
            # whiteboard/pick 转发给外部
            self.toolbar_btn.emit(bid)

    def set_pen_color(self, color_key):
        cmap = {
            'red':   QColor(255, 80, 80, 230),
            'blue':  QColor(100, 180, 255, 230),
            'black': QColor(20, 20, 20, 230),
            'white': QColor(255, 255, 255, 230),
        }
        self._color = cmap.get(color_key, QColor(255, 255, 255, 230))

    def clear_strokes(self):
        self._strokes.clear()
        self._cur_stroke.clear()
        self.update()

    def show(self):
        super().show()
        self._toolbar.show_at_bottom()
        self.raise_()
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, self._toolbar.raise_)
        QTimer.singleShot(200, self._toolbar.raise_)
        # 启动工具栏持续置顶定时器
        if not hasattr(self, '_toolbar_keep_top_timer'):
            self._toolbar_keep_top_timer = QTimer(self)
            self._toolbar_keep_top_timer.setInterval(300)
            self._toolbar_keep_top_timer.timeout.connect(self._keep_toolbar_top)
        self._toolbar_keep_top_timer.start()

    def _keep_toolbar_top(self):
        """持续将工具栏置顶"""
        if self._toolbar.isVisible():
            self._toolbar.raise_()

    def hide(self):
        if hasattr(self, '_toolbar_keep_top_timer'):
            self._toolbar_keep_top_timer.stop()
        self._toolbar.hide()
        super().hide()

    def mousePressEvent(self, e):
        # 检查是否点在工具栏区域
        if self._toolbar.isVisible():
            tb_geo = self._toolbar.geometry()
            gpos = self.mapToGlobal(e.pos())
            if tb_geo.contains(gpos):
                return
        if e.button() == Qt.LeftButton and self._mode != 'select':
            self._drawing = True
            self._cur_stroke = [QPoint(e.pos())]
            self.update()

    def mouseMoveEvent(self, e):
        if not self._drawing: return
        if self._mode == 'eraser':
            self._erase_near(e.pos())
        elif self._mode == 'draw':
            self._cur_stroke.append(QPoint(e.pos()))
        self.update()

    def mouseReleaseEvent(self, e):
        if not self._drawing: return
        self._drawing = False
        if self._mode == 'draw' and len(self._cur_stroke) > 1:
            self._strokes.append((list(self._cur_stroke), QColor(self._color), self._width))
        self._cur_stroke.clear()
        self.update()
        self.ball_raise_needed.emit()  # 绘制后置顶浮球

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QBrush(self._bg_color))
        for pts, color, width in self._strokes:
            pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            for i in range(1, len(pts)):
                p.drawLine(pts[i-1], pts[i])
        if self._cur_stroke:
            pen = QPen(self._color, self._width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            for i in range(1, len(self._cur_stroke)):
                p.drawLine(self._cur_stroke[i-1], self._cur_stroke[i])

    def _erase_near(self, pos, radius=24):
        self._strokes = [
            stroke for stroke in self._strokes
            if not any(
                (pt.x()-pos.x())**2 + (pt.y()-pos.y())**2 < radius**2
                for pt in stroke[0]
            )
        ]
        self.update()
