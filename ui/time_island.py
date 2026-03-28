# ui/time_island.py - 时间岛：右上角置顶实时时钟
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush
import datetime


class TimeIslandWidget(QWidget):
    """置顶右上角实时时钟，鼠标悬停时隐藏并穿透点击"""
    clicked = pyqtSignal()  # 点击时通知主窗口打开详情

    def __init__(self, parent=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._night = False
        self._show_bg = False         # 是否显示背景框（默认关闭）
        self._text_color = None       # None = 自动反色
        self._dragging = False
        self._drag_pos = None
        self._press_pos = None
        self._hover_hidden = False    # 鼠标悬停时穿透隐藏
        self._move_mode = False       # 移动模式
        self.setMouseTracking(True)
        self.setFixedSize(110, 44)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.update)
        self._timer.start()
        self._op_anim = QPropertyAnimation(self, b'windowOpacity')
        self._op_anim.setDuration(200)
        self._op_anim.setEasingCurve(QEasingCurve.OutCubic)
        # 默认位置：右上角
        self._move_to_default()

    def _move_to_default(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 12, screen.top() + 12)

    # ── 公共接口 ──
    def set_show_bg(self, v):
        self._show_bg = v; self.update()

    def set_text_color(self, color):
        """color: QColor or None(自动反色)"""
        self._text_color = color; self.update()

    def set_move_mode(self, v):
        """移动模式：可拖动，鼠标悬停不隐藏"""
        self._move_mode = v
        if not v and self._hover_hidden:
            self._show_normal()

    def apply_night(self, night):
        self._night = night; self.update()

    # ── 绘制 ──
    def paintEvent(self, e):
        now = datetime.datetime.now()
        time_str = now.strftime('%H:%M')
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        # 背景
        if self._show_bg:
            if self._night:
                bg = QColor(30, 26, 50, 210)
                bd = QColor(90, 82, 130, 160)
            else:
                bg = QColor(255, 253, 245, 210)
                bd = QColor(208, 198, 162, 180)
            p.setBrush(QBrush(bg))
            p.setPen(QPen(bd, 1.2))
            p.drawRoundedRect(2, 2, W-4, H-4, 10, 10)
        # 文字颜色
        if self._text_color:
            fg = self._text_color
        elif self._show_bg:
            fg = QColor(220, 215, 255) if self._night else QColor(44, 37, 16)
        else:
            # 无背景：白色描边确保任何背景下都可见
            fg = QColor(255, 255, 255)
        font = QFont('Microsoft YaHei', 18, QFont.Bold)
        p.setFont(font)
        if not self._show_bg and not self._text_color:
            # 无背景时加黑色描边提升可读性
            p.setPen(QPen(QColor(0, 0, 0, 180), 3))
            p.drawText(1, 1, W, H, Qt.AlignCenter, time_str)
        p.setPen(fg)
        p.drawText(0, 0, W, H, Qt.AlignCenter, time_str)

    # ── 鼠标事件 ──
    def enterEvent(self, e):
        if self._move_mode: return
        if self._hover_hidden: return
        self._hover_hidden = True
        # 淡出动画
        self._op_anim.stop()
        self._op_anim.setStartValue(self.windowOpacity())
        self._op_anim.setEndValue(0.0)
        self._op_anim.setDuration(150)
        self._op_anim.finished.connect(self._on_fade_out_done)
        self._op_anim.start()

    def _on_fade_out_done(self):
        try: self._op_anim.finished.disconnect(self._on_fade_out_done)
        except: pass
        if not self._hover_hidden: return
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # 启动轮询检测鼠标是否离开
        if not hasattr(self, '_hover_check_timer'):
            self._hover_check_timer = QTimer(self)
            self._hover_check_timer.setInterval(100)
            self._hover_check_timer.timeout.connect(self._check_hover)
        self._hover_check_timer.start()

    def leaveEvent(self, e):
        pass  # 由 _check_hover 处理，避免穿透后 leaveEvent 闪烁

    def _check_hover(self):
        """轮询检测鼠标是否还在时间岛范围内"""
        from PyQt5.QtGui import QCursor
        cursor_pos = QCursor.pos()
        geo = self.frameGeometry()
        if not geo.contains(cursor_pos):
            self._hover_check_timer.stop()
            self._show_normal()

    def _show_normal(self):
        self._hover_hidden = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._op_anim.stop()
        self._op_anim.setStartValue(self.windowOpacity())
        self._op_anim.setEndValue(1.0)
        self._op_anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_pos = e.globalPos()
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            self._dragging = False

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and self._drag_pos and self._move_mode:
            if (e.globalPos() - self._press_pos).manhattanLength() > 4:
                self._dragging = True
            if self._dragging:
                self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if not self._dragging:
                self.clicked.emit()
            self._dragging = False
            self._drag_pos = None


class TimeIslandDetailPanel(QFrame):
    """在主窗口内显示的时间岛详情设置面板"""
    closed = pyqtSignal()

    def __init__(self, island_widget, parent=None):
        super().__init__(parent)
        self._island = island_widget
        self._night = False
        self._move_mode = False
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet('QFrame{background:rgba(255,255,250,0.96);border-radius:14px;border:1px solid rgba(210,200,165,0.50);}')
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        # 标题行
        title_row = QHBoxLayout()
        title = QLabel('时间岛设置')
        title.setStyleSheet('font-size:13px;font-weight:700;color:#3a3220;background:transparent;border:none;')
        close_btn = QPushButton('✕')
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet('QPushButton{background:rgba(200,180,140,0.40);color:#5a4a30;border:none;border-radius:5px;font-size:11px;}QPushButton:hover{background:rgba(200,140,100,0.60);}')
        close_btn.clicked.connect(self.closed)
        title_row.addWidget(title); title_row.addStretch(); title_row.addWidget(close_btn)
        lay.addLayout(title_row)
        # 背景框开关
        bg_row = QHBoxLayout()
        bg_lbl = QLabel('显示背景框')
        bg_lbl.setStyleSheet('font-size:12px;color:#3a3220;background:transparent;border:none;')
        self._bg_btn = QPushButton('已关闭')
        self._bg_btn.setCheckable(True); self._bg_btn.setChecked(False)
        self._bg_btn.setCursor(Qt.PointingHandCursor)
        self._bg_btn.setFixedHeight(28)
        self._bg_btn.clicked.connect(self._on_bg_toggle)
        self._update_toggle_style(self._bg_btn, False)
        bg_row.addWidget(bg_lbl); bg_row.addStretch(); bg_row.addWidget(self._bg_btn)
        lay.addLayout(bg_row)
        # 颜色选择
        col_row = QHBoxLayout()
        col_lbl = QLabel('文字颜色')
        col_lbl.setStyleSheet('font-size:12px;color:#3a3220;background:transparent;border:none;')
        self._color_btns = []
        colors = [('自动', None), ('白色', QColor(255,255,255)), ('黑色', QColor(0,0,0)),
                  ('金色', QColor(210,170,60)), ('蓝色', QColor(80,140,255))]
        col_row.addWidget(col_lbl); col_row.addStretch()
        for label, color in colors:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.setStyleSheet('QPushButton{background:rgba(200,190,155,0.40);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:6px;font-size:11px;padding:0 6px;}QPushButton:hover{background:rgba(200,190,155,0.70);}')
            btn.clicked.connect(lambda _, c=color: self._island.set_text_color(c))
            col_row.addWidget(btn)
            self._color_btns.append(btn)
        lay.addLayout(col_row)
        # 位置调整
        pos_row = QHBoxLayout()
        pos_lbl = QLabel('位置')
        pos_lbl.setStyleSheet('font-size:12px;color:#3a3220;background:transparent;border:none;')
        self._move_btn = QPushButton('调整位置')
        self._move_btn.setCursor(Qt.PointingHandCursor)
        self._move_btn.setFixedHeight(28)
        self._move_btn.setStyleSheet('QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:none;border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(138,122,80,0.80);}')
        self._move_btn.clicked.connect(self._toggle_move_mode)
        reset_pos_btn = QPushButton('重置位置')
        reset_pos_btn.setCursor(Qt.PointingHandCursor)
        reset_pos_btn.setFixedHeight(28)
        reset_pos_btn.setStyleSheet('QPushButton{background:rgba(200,190,155,0.40);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(200,190,155,0.70);}')
        reset_pos_btn.clicked.connect(self._island._move_to_default)
        pos_row.addWidget(pos_lbl); pos_row.addStretch()
        pos_row.addWidget(reset_pos_btn); pos_row.addWidget(self._move_btn)
        lay.addLayout(pos_row)

    def _on_bg_toggle(self):
        checked = self._bg_btn.isChecked()
        self._island.set_show_bg(checked)
        self._bg_btn.setText('已开启' if checked else '已关闭')
        self._update_toggle_style(self._bg_btn, checked)

    def _toggle_move_mode(self):
        self._move_mode = not self._move_mode
        self._island.set_move_mode(self._move_mode)
        self._move_btn.setText('完成移动' if self._move_mode else '调整位置')
        st_on  = 'QPushButton{background:rgba(80,160,80,0.70);color:#ffffff;border:none;border-radius:7px;font-size:12px;padding:0 10px;}'
        st_off = 'QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:none;border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(138,122,80,0.80);}'
        self._move_btn.setStyleSheet(st_on if self._move_mode else st_off)

    def _update_toggle_style(self, btn, on):
        if on:
            btn.setStyleSheet('QPushButton{background:rgba(80,160,80,0.60);color:#ffffff;border:none;border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(80,160,80,0.80);}')
        else:
            btn.setStyleSheet('QPushButton{background:rgba(180,100,80,0.55);color:#ffffff;border:none;border-radius:7px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(180,100,80,0.80);}')

    def apply_night(self, night):
        self._night = night
        if night:
            self.setStyleSheet('QFrame{background:rgba(38,34,52,0.96);border-radius:14px;border:1px solid rgba(80,75,110,0.55);}')
            fg = 'color:#e0d8f8;'
        else:
            self.setStyleSheet('QFrame{background:rgba(255,255,250,0.96);border-radius:14px;border:1px solid rgba(210,200,165,0.50);}')
            fg = 'color:#3a3220;'
        for lbl in self.findChildren(QLabel):
            lbl.setStyleSheet(f'font-size:12px;{fg}background:transparent;border:none;')
