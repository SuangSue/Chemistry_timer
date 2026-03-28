import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QGraphicsDropShadowEffect, QApplication, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPoint,
    QRect, QParallelAnimationGroup, pyqtSignal,
    QTimer
)
from PyQt5.QtWidgets import QLabel as _QLabel
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QLinearGradient, QPainterPath, QPen
)

import utils.styles as styles_mod
from ui.pages.timer_page import TimerPage
from ui.pages.random_pick_page import RandomPickPage
from ui.pages.tools_page import ToolsPage
from ui.pages.settings_page import SettingsPage
from ui.pages.automation_page import AutomationPage
from ui.pages.clock_page import ClockPage

import ctypes
import ctypes.wintypes

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MINMAXINFO(ctypes.Structure):
    _fields_ = [
        ("ptReserved",     POINT),
        ("ptMaxSize",      POINT),
        ("ptMaxPosition",  POINT),
        ("ptMinTrackSize", POINT),
        ("ptMaxTrackSize", POINT),
    ]

WIN_W  = 620
WIN_H  = 479
MARGIN = 14


class SlidingStack(QStackedWidget):
    def __init__(self, duration=250, parent=None):
        super().__init__(parent)
        self._animating = False
        self._duration  = duration

    def set_duration(self, ms):
        self._duration = ms

    def slide_to(self, index):
        if self._animating or index == self.currentIndex():
            self.setCurrentIndex(index); return
        cur = self.currentWidget()
        nxt = self.widget(index)
        if not cur or not nxt:
            self.setCurrentIndex(index); return
        direction = 1 if index > self.currentIndex() else -1
        w, h = self.width(), self.height()
        self._sliding = True
        # move+resize 代替 setGeometry，避免触发子页面尺寸警告
        nxt.move(direction * w, 0)
        nxt.resize(w, h)
        nxt.show(); nxt.raise_()
        self._animating = True
        out = QPropertyAnimation(cur, b'pos')
        out.setDuration(self._duration)
        out.setStartValue(QPoint(0, 0))
        out.setEndValue(QPoint(-direction * w, 0))
        out.setEasingCurve(QEasingCurve.OutQuart)
        inp = QPropertyAnimation(nxt, b'pos')
        inp.setDuration(self._duration)
        inp.setStartValue(QPoint(direction * w, 0))
        inp.setEndValue(QPoint(0, 0))
        inp.setEasingCurve(QEasingCurve.OutQuart)
        self._grp = QParallelAnimationGroup()
        self._grp.addAnimation(out)
        self._grp.addAnimation(inp)
        self._grp.finished.connect(lambda: self._done(index, cur))
        self._grp.start()

    def _done(self, index, old):
        self.setCurrentIndex(index); old.hide(); old.move(0, 0)
        self._animating = False; self._sliding = False


class TextNavBtn(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._set_active(False)

    def setActive(self, on):
        self.setChecked(on)
        self._set_active(on)

    def _set_active(self, on):
        self.setStyleSheet(
            styles_mod.NAV_BUTTON_ACTIVE if on else styles_mod.NAV_BUTTON_NORMAL
        )


class IconBtn(QPushButton):
    def __init__(self, icon_text, tooltip='', checkable=False, parent=None):
        super().__init__(icon_text, parent)
        self.setToolTip(tooltip)
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(28, 28)
        self._refresh(False)

    def setActive(self, on, night=False):
        self.setChecked(on)
        self._refresh(on, night)

    def _refresh(self, on, night=False):
        base = ('QPushButton{border-radius:7px;font-size:14px;'
                'font-family:"Segoe UI Emoji","Apple Color Emoji","Microsoft YaHei";border:none;}')
        if on:
            if night:
                self.setStyleSheet(base +
                    'QPushButton{background:rgba(90,82,130,0.60);color:#e0d8f8;}'
                    'QPushButton:hover{background:rgba(110,100,160,0.80);}')
            else:
                self.setStyleSheet(base +
                    'QPushButton{background:rgba(200,188,150,0.55);color:#3a3220;}'
                    'QPushButton:hover{background:rgba(210,198,160,0.80);}')
        else:
            if night:
                self.setStyleSheet(base +
                    'QPushButton{background:transparent;color:#9090b8;}'
                    'QPushButton:hover{background:rgba(80,75,110,0.35);color:#e0d8f8;}')
            else:
                self.setStyleSheet(base +
                    'QPushButton{background:transparent;color:#8a8060;}'
                    'QPushButton:hover{background:rgba(210,200,165,0.30);color:#3a3220;}')


class _BorderFlash(QWidget):
    """沿主窗口外框：从右上角向左+向下绕半圈到左下角，两线汇合消失（独立顶层窗口）"""
    def __init__(self, parent):
        # 独立顶层透明窗口，不受父窗口层叠影响
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._parent_win = parent
        self._prog = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(12)  # ~83fps，更快
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self):
        self._prog = 0.0
        # 跟随父窗口位置和大小
        geo = self._parent_win.geometry()
        self.setGeometry(geo)
        self.show(); self.raise_(); self._timer.start()

    def _tick(self):
        self._prog = min(1.0, self._prog + 1.0/28)  # ~336ms完成
        if self._prog >= 1.0:
            self._timer.stop()
            QTimer.singleShot(80, self.hide)
        self.update()

    def paintEvent(self, event):
        if self._prog <= 0: return
        from PyQt5.QtGui import QPainterPath as _Path
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m = MARGIN
        prog = self._prog
        top   = float(w - 2*m)
        left  = float(h - 2*m)
        right = float(h - 2*m)
        bot   = float(w - 2*m)
        path_a = top + left
        path_b = right + bot
        da = prog * path_a
        db = prog * path_b
        alpha = 255 if prog < 0.72 else int(255 * (1-(prog-0.72)/0.28))
        pen = QPen(QColor(218, 178, 50, alpha), 2.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        # ── 线A：右上角 → 顶边向左 → 左边向下（折线路径）──
        pa = _Path()
        pa.moveTo(w-m, m)
        if da <= top:
            pa.lineTo(w-m-da, m)
        else:
            pa.lineTo(m, m)
            pa.lineTo(m, m + min(da-top, left))
        p.drawPath(pa)
        # ── 线B：右上角 → 右边向下 → 底边向左（折线路径）──
        pb = _Path()
        pb.moveTo(w-m, m)
        if db <= right:
            pb.lineTo(w-m, m+db)
        else:
            pb.lineTo(w-m, h-m)
            pb.lineTo(w-m - min(db-right, bot), h-m)
        p.drawPath(pb)


class MainWindow(QWidget):
    hide_requested     = pyqtSignal()
    always_top_changed = pyqtSignal(bool)
    theme_changed      = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._night = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        target_w = WIN_W + MARGIN * 2
        target_h = WIN_H + MARGIN * 2
        self.resize(target_w, target_h)
        self.setMinimumSize(target_w, target_h)
        self.setMaximumSize(target_w, target_h)
        self._build_ui()
        self._setup_shadow()
        self._setup_anims()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        root.setSpacing(0)
        self._card = QWidget(self)
        self._card.setObjectName('Card')
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        nav = QWidget()
        nav.setObjectName('NavBar')
        nav.setFixedHeight(42)
        nav.setStyleSheet(styles_mod.NAV_BAR_STYLE)
        nav_lay = QHBoxLayout(nav)
        nav_lay.setContentsMargins(8, 5, 8, 5)
        nav_lay.setSpacing(2)

        pages = [('\u8ba1\u65f6\u5668', TimerPage), ('\u968f\u673a\u62bd\u7b7e', RandomPickPage),
                 ('TIME_PLACEHOLDER', ClockPage), ('\u5b9e\u7528\u5de5\u5177', ToolsPage)]
        self._nav_btns = []
        self._stack = SlidingStack()
        self._stack.setStyleSheet(styles_mod.PAGE_STYLE)
        self._clock_nav_lbl = None
        for i, (name, Cls) in enumerate(pages):
            if name == 'TIME_PLACEHOLDER':
                # 时钟导航按钮，与其他按钮完全一致使用 TextNavBtn
                btn = TextNavBtn('时钟')
                btn.clicked.connect(lambda _, idx=i: self._switch(idx))
                nav_lay.addWidget(btn)
                self._nav_btns.append(btn)
                self._clock_nav_lbl = btn
                pg = Cls()
                pg.setObjectName('PageWidget')
                self._stack.addWidget(pg)
            else:
                btn = TextNavBtn(name)
                btn.clicked.connect(lambda _, idx=i: self._switch(idx))
                nav_lay.addWidget(btn)
                self._nav_btns.append(btn)
                pg = Cls()
                pg.setObjectName('PageWidget')
                self._stack.addWidget(pg)

        self._settings_page = SettingsPage()
        self._settings_page.setObjectName('PageWidget')
        self._stack.addWidget(self._settings_page)
        self._automation_page = AutomationPage()
        self._automation_page.setObjectName('PageWidget')
        self._stack.addWidget(self._automation_page)

        nav_lay.addStretch()
        self._pin_btn = IconBtn('\U0001f4cc', '\u59cb\u7ec8\u7f6e\u9876', checkable=True)
        self._pin_btn.setActive(True)
        self._pin_btn.clicked.connect(self._on_pin)
        self._cfg_btn = IconBtn('\u2699', '\u8bbe\u7f6e')
        self._cfg_btn.clicked.connect(lambda: self._switch(4))
        self._x_btn = IconBtn('\u2715', '\u9690\u85cf')
        self._x_btn.clicked.connect(self.hide_requested)
        for b in (self._pin_btn, self._cfg_btn, self._x_btn):
            nav_lay.addWidget(b)

        card_lay.addWidget(nav)
        card_lay.addWidget(self._stack)

        # theme_btn removed
        root.addWidget(self._card)
        self._switch(0)
        self.setAcceptDrops(True)
        # 外框金色线条动画层（独立顶层窗口）
        self._border_flash = _BorderFlash(self)
        # 连接实用工具页的自动化信号
        tools_pg = self._stack.widget(3)
        if hasattr(tools_pg, 'open_automation'):
            tools_pg.open_automation.connect(lambda: self._switch(5))

    def nativeEvent(self, eventType, message):
        """拦截 WM_GETMINMAXINFO，覆盖系统强加的最小高度"""
        import ctypes
        import ctypes.wintypes
        WM_GETMINMAXINFO = 0x0024
        try:
            if eventType == b'windows_generic_MSG':
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_GETMINMAXINFO:
                    info = ctypes.cast(
                        ctypes.c_void_p(msg.lParam),
                        ctypes.POINTER(MINMAXINFO)
                    ).contents
                    info.ptMinTrackSize.x = WIN_W + MARGIN * 2
                    info.ptMinTrackSize.y = WIN_H + MARGIN * 2
                    info.ptMaxTrackSize.x = WIN_W + MARGIN * 2
                    info.ptMaxTrackSize.y = WIN_H + MARGIN * 2
                    return True, 0
        except Exception:
            pass
        return super().nativeEvent(eventType, message)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def _apply_theme_btn_style(self):
        if self._night:
            self._theme_btn.setText('\u2600\ufe0f')
            self._theme_btn.setStyleSheet(
                'QPushButton{background:rgba(90,82,130,0.55);color:#e8e0ff;'
                'border:1px solid rgba(110,100,160,0.55);border-radius:8px;font-size:15px;}'
                'QPushButton:hover{background:rgba(110,100,150,0.78);}')
        else:
            self._theme_btn.setText('\U0001f319')
            self._theme_btn.setStyleSheet(
                'QPushButton{background:rgba(210,200,165,0.40);color:#5a5030;'
                'border:1px solid rgba(200,190,150,0.50);border-radius:8px;font-size:15px;}'
                'QPushButton:hover{background:rgba(210,200,165,0.72);}')

    def _toggle_theme(self):
        self._night = not self._night
        styles_mod.set_theme(self._night)
        nav = self._card.findChild(QWidget, 'NavBar')
        if nav:
            nav.setStyleSheet(styles_mod.NAV_BAR_STYLE)
        for btn in self._nav_btns:
            if hasattr(btn, '_set_active'):
                btn._set_active(btn.isChecked())
        # 更新 icon 按钮夜间色
        for b in (self._pin_btn, self._cfg_btn, self._x_btn):
            b._refresh(b.isChecked(), self._night)
        self._stack.setStyleSheet(styles_mod.PAGE_STYLE)
        for i in range(self._stack.count()):
            pg = self._stack.widget(i)
            if hasattr(pg, 'apply_night'):
                pg.apply_night(self._night)
        # 同步设置页主题按钮状态
        if hasattr(self._settings_page, '_night'):
            self._settings_page._night = self._night
        # 时钟按钮现为 TextNavBtn，已由上方循环统一处理
        self.update()
        self.theme_changed.emit(self._night)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        for i in range(self._stack.count()):
            pg = self._stack.widget(i)
            if hasattr(pg, '_do_import'):
                for url in e.mimeData().urls():
                    pg._do_import(url.toLocalFile())
                break

    def _on_pin(self):
        on = self._pin_btn.isChecked()
        self._pin_btn.setActive(on)
        self.always_top_changed.emit(on)

    def _setup_shadow(self):
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(28)
        sh.setOffset(0, 5)
        sh.setColor(QColor(60, 50, 20, 50))
        self._card.setGraphicsEffect(sh)

    def _setup_anims(self):
        self._fade_in = QPropertyAnimation(self, b'windowOpacity')
        self._fade_in.setDuration(240)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._geo_anim = QPropertyAnimation(self, b'geometry')
        self._geo_anim.setDuration(280)
        self._geo_anim.setEasingCurve(QEasingCurve.OutBack)
        # 实时更新导航栏时钟
        self._clock_nav_timer = QTimer(self)
        self._clock_nav_timer.setInterval(1000)
        self._clock_nav_timer.timeout.connect(self._update_clock_nav)
        self._clock_nav_timer.start()
        self._update_clock_nav()

    def show_near_ball(self, ball_geo, prefer_left=True):
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        bx, by, bw, bh = ball_geo.x(), ball_geo.y(), ball_geo.width(), ball_geo.height()
        y = by + bh//2 - h//2
        y = max(screen.top() + 8, min(y, screen.bottom() - h - 8))
        x_left  = bx - w - 8
        x_right = bx + bw + 8
        if prefer_left and x_left >= screen.left() + 8:
            x = x_left
        elif x_right + w <= screen.right() - 8:
            x = x_right
        else:
            x = max(screen.left() + 8, screen.right() - w - 8)
        final_geo = QRect(x, y, w, h)
        # 从浮球中心小矩形展开到目标位置
        start_geo = QRect(bx + bw//2 - 20, by + bh//2 - 20, 40, 40)
        self.setGeometry(start_geo)
        self.setWindowOpacity(0.0)
        self.show()
        self._geo_anim.stop()
        self._geo_anim.setStartValue(start_geo)
        self._geo_anim.setEndValue(final_geo)
        self._geo_anim.start()
        self._fade_in.start()

    def hide_with_anim(self, callback=None):
        anim = QPropertyAnimation(self, b'windowOpacity')
        anim.setDuration(170)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        if callback:
            anim.finished.connect(callback)
        anim.finished.connect(self.hide)
        self._hide_anim = anim
        anim.start()

    def follow_ball(self, ball_geo, prefer_left=True):
        """浮球拖动时主窗口跟随，用 move() 保持固定尺寸，带平滑动画"""
        if not self.isVisible():
            return
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        bx, by, bw, bh = ball_geo.x(), ball_geo.y(), ball_geo.width(), ball_geo.height()
        y = by + bh//2 - h//2
        y = max(screen.top() + 8, min(y, screen.bottom() - h - 8))
        x_left  = bx - w - 8
        x_right = bx + bw + 8
        if prefer_left and x_left >= screen.left() + 8:
            x = x_left
        elif x_right + w <= screen.right() - 8:
            x = x_right
        else:
            x = max(screen.left() + 8, screen.right() - w - 8)
        # 用 pos 动画平滑跟随，不改变窗口尺寸
        # 拖动时直接 move，不用动画，避免卡顿
        if not hasattr(self, '_move_anim'):
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QPoint
            self._move_anim = QPropertyAnimation(self, b'pos')
            self._move_anim.setDuration(80)
            self._move_anim.setEasingCurve(QEasingCurve.OutCubic)
        anim = self._move_anim
        if anim.state() == anim.Running:
            anim.stop()
        anim.setStartValue(self.pos())
        from PyQt5.QtCore import QPoint
        anim.setEndValue(QPoint(x, y))
        anim.start()

    def _update_clock_nav(self):
        pass  # 时钟标签显示静态文字，不更新实时时间

    def _switch(self, index):
        for i, btn in enumerate(self._nav_btns):
            if hasattr(btn, 'setActive'):
                btn.setActive(i == index)
        self._cfg_btn.setActive(index == 4)
        self._stack.slide_to(index)

    def set_anim_speed(self, ms):
        self._stack.set_duration(ms)

    def trigger_border_flash(self):
        if hasattr(self, '_border_flash'):
            self._border_flash.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rx, ry = MARGIN, MARGIN
        rw, rh = self.width()-MARGIN*2, self.height()-MARGIN*2
        path = QPainterPath()
        path.addRoundedRect(rx, ry, rw, rh, 16, 16)
        t = styles_mod._theme
        c0 = QColor(*t['card_top'])
        c1 = QColor(*t['card_mid'])
        c2 = QColor(*t['card_bot'])
        grad = QLinearGradient(rx, ry, rx, ry + rh)
        grad.setColorAt(0.0, c0)
        grad.setColorAt(0.5, c1)
        grad.setColorAt(1.0, c2)
        p.fillPath(path, QBrush(grad))
        bc = QColor(*t['border'])
        p.setPen(QPen(bc, 1.2))
        p.drawPath(path)