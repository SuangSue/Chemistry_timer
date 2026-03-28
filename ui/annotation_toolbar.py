from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMenu, QAction
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen


class AnnotationToolbar(QWidget):
    btn_clicked = pyqtSignal(str)   # bid: whiteboard/pick/select/annotate/eraser/clear
    color_changed = pyqtSignal(str)  # 'red'/'blue'/'black'

    BTN_SIZE  = 36
    BTN_GAP   = 5
    CAPSULE_W = 48
    BALL_GAP  = 10

    # 上方胶囊：白板、随机抽签
    TOP_BTNS = [
        ('whiteboard', '\u25a1', '\u767d\u677f'),
        ('pick',       '\u2684', '\u968f\u673a\u62bd\u7b7e\u4e00\u4eba'),
    ]
    # 下方胶囊：选择、批注、橡皮、清空
    BOT_BTNS = [
        ('select',   '\u2d54', '\u9009\u62e9'),
        ('annotate', '\u270d', '\u6279\u6ce8'),
        ('eraser',   '\u25cb', '\u6a61\u76ae'),
        ('clear',    '\u2716', '\u6e05\u7a7a\u6279\u6ce8'),
    ]

    COLORS = [
        ('red',   '\u7ea2\u8272', QColor(220, 50, 50)),
        ('blue',  '\u84dd\u8272', QColor(50, 100, 220)),
        ('black', '\u9ed1\u8272', QColor(30, 30, 30)),
    ]

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._night = False
        self._shown = False
        self._hiding = False
        self._selected = 'select'
        self._annotate_color = 'black'
        self._op_anim = QPropertyAnimation(self, b'windowOpacity')
        self._op_anim.setDuration(180)
        self._op_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pos_anim = QPropertyAnimation(self, b'pos')
        self._pos_anim.setDuration(60)
        self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._top_h = self._cap_height(len(self.TOP_BTNS))
        self._bot_h = self._cap_height(len(self.BOT_BTNS))
        self._build_ui()
        self.hide()

    def _cap_height(self, n):
        return n * self.BTN_SIZE + (n - 1) * self.BTN_GAP + 20

    def _build_ui(self):
        self._top_capsule = self._make_capsule(self.TOP_BTNS)
        self._bot_capsule = self._make_capsule(self.BOT_BTNS)
        self._top_capsule.setParent(self)
        self._bot_capsule.setParent(self)
        self._btns = {}
        for cap, btns in [(self._top_capsule, self.TOP_BTNS), (self._bot_capsule, self.BOT_BTNS)]:
            for i, (bid, icon, tip) in enumerate(btns):
                btn = cap.findChildren(QPushButton)[i]
                self._btns[bid] = btn
        self._update_style()

    def _make_capsule(self, btns):
        capsule = QWidget()
        capsule.setFixedSize(self.CAPSULE_W, self._cap_height(len(btns)))
        lay = QVBoxLayout(capsule)
        lay.setContentsMargins(6, 10, 6, 10)
        lay.setSpacing(self.BTN_GAP)
        for bid, icon, tip in btns:
            btn = QPushButton(icon, capsule)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(self.BTN_SIZE, self.BTN_SIZE)
            btn.setCheckable(True)
            if bid == 'select':
                btn.setChecked(True)
            btn.clicked.connect(lambda _, b=bid: self._on_btn(b))
            lay.addWidget(btn)
        return capsule

    def _on_btn(self, bid):
        if bid == 'annotate' and self._selected == 'annotate':
            self._show_color_menu()
            return
        self._selected = bid
        self._update_checked()
        self.btn_clicked.emit(bid)

    def _show_color_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            'QMenu{background:rgba(255,253,245,0.98);border:1px solid rgba(200,190,155,0.80);'
            'border-radius:8px;padding:4px;}'
            'QMenu::item{padding:6px 18px;font-size:12px;color:#3a3220;border-radius:5px;}'
            'QMenu::item:selected{background:rgba(200,190,155,0.55);}'
        )
        for key, label, color in self.COLORS:
            act = QAction(f'\u25cf  {label}', menu)
            act.setData(key)
            menu.addAction(act)
        btn_widget = self._btns['annotate']
        pos = btn_widget.mapToGlobal(QPoint(self.CAPSULE_W + 4, 0))
        chosen = menu.exec_(pos)
        if chosen:
            self._annotate_color = chosen.data()
            self.color_changed.emit(self._annotate_color)

    def _update_checked(self):
        for bid, btn in self._btns.items():
            btn.setChecked(bid == self._selected)
        self._update_style()

    def _update_style(self):
        if self._night:
            cap_bg = 'rgba(40,38,55,0.93)'; cap_bd = 'rgba(90,82,130,0.72)'
            btn_bg = 'rgba(60,55,85,0.82)'; btn_fg = '#d8d0f8'
            btn_hov = 'rgba(90,82,130,0.82)'
            btn_chk = 'rgba(120,108,180,0.90)'; btn_chk_fg = '#ffffff'
        else:
            cap_bg = 'rgba(255,253,245,0.96)'; cap_bd = 'rgba(210,198,158,0.80)'
            btn_bg = 'rgba(245,240,225,0.90)'; btn_fg = '#3a3220'
            btn_hov = 'rgba(218,205,165,0.94)'
            btn_chk = 'rgba(138,122,80,0.85)'; btn_chk_fg = '#fff8e8'
        cap_st = f'QWidget{{background:{cap_bg};border:1.5px solid {cap_bd};border-radius:24px;}}'
        btn_st = (
            f'QPushButton{{background:{btn_bg};color:{btn_fg};border:none;'
            f'border-radius:17px;font-size:16px;}}'
            f'QPushButton:hover{{background:{btn_hov};}}'
            f'QPushButton:checked{{background:{btn_chk};color:{btn_chk_fg};}}'
        )
        for cap in (self._top_capsule, self._bot_capsule):
            cap.setStyleSheet(cap_st)
            for btn in cap.findChildren(QPushButton):
                btn.setStyleSheet(btn_st)

    def apply_night(self, night):
        self._night = night
        self._update_style()

    def get_selected(self): return self._selected
    def get_color(self): return self._annotate_color

    def show_near(self, ball_geo, main_win_geo=None):
        """显示或移动工具栏到浮球旁"""
        if self._hiding:
            self._op_anim.stop(); self._pos_anim.stop(); self._hiding = False
            try: self._op_anim.finished.disconnect(self._on_hide_done)
            except Exception: pass

        bx = ball_geo.x(); by = ball_geo.y()
        bw = ball_geo.width(); bh = ball_geo.height()
        ball_cx = bx + bw // 2
        x = ball_cx - self.CAPSULE_W // 2
        top_y = by - self.BALL_GAP - self._top_h
        bot_y = by + bh + self.BALL_GAP
        rel_bot = bot_y - top_y
        total_h = rel_bot + self._bot_h
        target = QPoint(x, top_y)

        self.setFixedSize(self.CAPSULE_W, total_h)
        self._top_capsule.move(0, 0)
        self._bot_capsule.move(0, rel_bot)

        if not self._shown:
            self.move(target)
            self.setWindowOpacity(0.0)
            self.show()
            self._op_anim.stop()
            self._op_anim.setStartValue(0.0)
            self._op_anim.setEndValue(1.0)
            self._op_anim.start()
        else:
            self._pos_anim.stop()
            self._pos_anim.setStartValue(self.pos())
            self._pos_anim.setEndValue(target)
            self._pos_anim.start()
        self._shown = True

    def hide_anim(self):
        if not self._shown: return
        self._shown = False; self._hiding = True
        self._pos_anim.stop(); self._op_anim.stop()
        self._op_anim.setStartValue(self.windowOpacity())
        self._op_anim.setEndValue(0.0)
        self._op_anim.finished.connect(self._on_hide_done)
        self._op_anim.start()

    def _on_hide_done(self):
        self._hiding = False; self.hide()
        try: self._op_anim.finished.disconnect(self._on_hide_done)
        except Exception: pass

    def is_shown(self): return self._shown
