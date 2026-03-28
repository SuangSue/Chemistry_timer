import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QDialog, QSpinBox,
    QFileDialog, QComboBox, QStackedWidget
)
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup

class SlidingStack(QStackedWidget):
    def __init__(self, duration=200, parent=None):
        super().__init__(parent); self._animating=False; self._duration=duration
    def slide_to(self, index):
        if self._animating or index==self.currentIndex(): self.setCurrentIndex(index); return
        cur=self.currentWidget(); nxt=self.widget(index)
        if not cur or not nxt: self.setCurrentIndex(index); return
        direction=1 if index>self.currentIndex() else -1
        w,h=self.width(),self.height()
        nxt.move(direction*w,0); nxt.resize(w,h); nxt.show(); nxt.raise_()
        self._animating=True
        out=QPropertyAnimation(cur,b'pos'); out.setDuration(self._duration)
        out.setStartValue(QPoint(0,0)); out.setEndValue(QPoint(-direction*w,0)); out.setEasingCurve(QEasingCurve.OutQuart)
        inp=QPropertyAnimation(nxt,b'pos'); inp.setDuration(self._duration)
        inp.setStartValue(QPoint(direction*w,0)); inp.setEndValue(QPoint(0,0)); inp.setEasingCurve(QEasingCurve.OutQuart)
        self._grp=QParallelAnimationGroup(); self._grp.addAnimation(out); self._grp.addAnimation(inp)
        self._grp.finished.connect(lambda: self._done(index,cur)); self._grp.start()
    def _done(self, index, old):
        self.setCurrentIndex(index); old.hide(); old.move(0,0); self._animating=False
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QBrush, QPainterPath, QPen
from utils import config as cfg
from utils.roster_importer import import_file
from ui.pages.roster_view_page import RosterViewPage, EditRosterDialog


class NumberDialog(QDialog):
    def __init__(self, current, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(260, 150); self._result = current
        lay = QVBoxLayout(self); lay.setContentsMargins(18, 16, 18, 16); lay.setSpacing(12)
        t = QLabel('修改抽取人数'); t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet('font-size:13px;font-weight:700;color:#3a3220;background:transparent;border:none;')
        lay.addWidget(t)
        self._spin = QSpinBox(); self._spin.setRange(1, 10); self._spin.setValue(min(current, 10))
        self._spin.setAlignment(Qt.AlignCenter); self._spin.setFixedHeight(38)
        self._spin.setStyleSheet('QSpinBox{background:rgba(248,244,232,0.95);color:#2c2510;border:1px solid rgba(200,190,155,0.70);border-radius:9px;font-size:20px;font-weight:700;font-family:"Microsoft YaHei";padding:0 6px;}QSpinBox::up-button,QSpinBox::down-button{width:26px;border-radius:5px;background:rgba(200,190,155,0.40);}')
        lay.addWidget(self._spin)
        row = QHBoxLayout(); row.setSpacing(10)
        ok = QPushButton('确定'); ok.setCursor(Qt.PointingHandCursor); ok.setFixedHeight(32)
        ok.setStyleSheet('QPushButton{background:rgba(138,122,80,0.82);color:#fff8e8;border:none;border-radius:8px;font-size:13px;font-weight:700;}QPushButton:hover{background:rgba(158,142,95,0.95);}')
        cn = QPushButton('取消'); cn.setCursor(Qt.PointingHandCursor); cn.setFixedHeight(32)
        cn.setStyleSheet('QPushButton{background:rgba(200,190,155,0.40);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:8px;font-size:13px;}QPushButton:hover{background:rgba(200,190,155,0.70);}')
        ok.clicked.connect(self._accept); cn.clicked.connect(self.reject)
        row.addWidget(cn, 1); row.addWidget(ok, 1); lay.addLayout(row)

    def _accept(self): self._result = self._spin.value(); self.accept()
    def get_value(self): return self._result

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        p.fillPath(path, QBrush(QColor(255, 253, 245, 245)))
        p.setPen(QPen(QColor(210, 200, 165, 180), 1.2)); p.drawPath(path)


class CustomPickBtn(QPushButton):
    def __init__(self, n=5, parent=None):
        super().__init__(parent); self._n = n
        self.setCursor(Qt.PointingHandCursor); self.setFixedHeight(38)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet('QPushButton{background:rgba(138,122,80,0.38);border:1px solid rgba(138,122,80,0.52);border-radius:9px;}QPushButton:hover{background:rgba(138,122,80,0.60);}')

    def set_n(self, n): self._n = n; self.update()
    def get_n(self): return self._n

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        fn = QFont('Microsoft YaHei', 12, QFont.DemiBold)
        fb = QFont('Microsoft YaHei', 15, QFont.Black)
        p.setFont(fn); fm = p.fontMetrics()
        pre = '抽取\u00a0'; suf = '\u00a0名学生'; ns = str(self._n)
        pw = fm.horizontalAdvance(pre); sw = fm.horizontalAdvance(suf)
        p.setFont(fb); nw = p.fontMetrics().horizontalAdvance(ns)
        total = pw + nw + sw; x = (self.width() - total) // 2; cy = self.height() // 2
        p.setFont(fn); p.setPen(QColor(58, 50, 32))
        p.drawText(x, cy + p.fontMetrics().ascent() // 2, pre); x += pw
        p.setFont(fb); p.setPen(QColor(195, 95, 20))
        p.drawText(x, cy + p.fontMetrics().ascent() // 2, ns); x += nw
        p.setFont(fn); p.setPen(QColor(58, 50, 32))
        p.drawText(x, cy + p.fontMetrics().ascent() // 2, suf)


class RandomPickPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._names = []; self._weights = {}; self._rolling = False
        self._roll_count = 0; self._roll_max = 24
        self._custom_n = cfg.get('custom_pick_n', 5)
        self._current_roster = cfg.get('last_roster', '')
        self._night = False
        self._frames = []; self._plain_btns = []
        self._roll_timer = QTimer(self)
        self._roll_timer.setInterval(55)
        self._roll_timer.timeout.connect(self._roll_tick)
        self._stack = SlidingStack(200, self)
        self._stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._main_page = QWidget()
        self._roster_view = RosterViewPage()
        self._roster_view.back_requested.connect(self._show_main)
        self._roster_view.edit_requested.connect(self._edit_roster)
        self._stack.addWidget(self._main_page)
        self._stack.addWidget(self._roster_view)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(self._stack)
        self._build_ui(); self._load_last_roster()
        self.setAcceptDrops(True)

    def _build_ui(self):
        root = QVBoxLayout(self._main_page)
        root.setContentsMargins(16, 10, 16, 10); root.setSpacing(6)

        # ── 名单选择行 ──
        rb = QHBoxLayout(); rb.setSpacing(6)
        lbl = QLabel('名单：')
        lbl.setStyleSheet('font-size:12px;color:#6b6040;background:transparent;border:none;')
        rb.addWidget(lbl)
        self._roster_combo = QComboBox()
        self._roster_combo.setFixedHeight(30)
        self._roster_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._roster_combo.setStyleSheet('QComboBox{background:rgba(255,253,245,0.88);color:#3a3220;border:1px solid rgba(200,190,155,0.65);border-radius:7px;padding:2px 8px;font-size:12px;}QComboBox::drop-down{border:none;}')
        self._roster_combo.currentTextChanged.connect(self._on_roster_selected)
        self._refresh_roster_combo()
        ib = self._mk_btn('导入名单', 138, 122, 80); ib.clicked.connect(self._import_roster)
        vb = self._mk_btn('查看名单', 80, 110, 138); vb.clicked.connect(self._view_roster)
        self._plain_btns.extend([ib, vb])
        rb.addWidget(self._roster_combo, 1); rb.addWidget(ib); rb.addWidget(vb)
        root.addLayout(rb)

        # ── 状态标签 ──
        self._status_lbl = QLabel('等待抽签')
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        self._status_lbl.setStyleSheet('color:#7a7050;background:transparent;border:none;')
        root.addWidget(self._status_lbl)

        # ── 结果容器（中间偏上，弹性拉伸：上少下多）──
        wf = QFrame()
        wf.setStyleSheet('QFrame{background:rgba(255,255,250,0.55);border-radius:16px;border:1px solid rgba(210,200,165,0.45);}')
        self._frames.append(wf)
        wl = QVBoxLayout(wf); wl.setContentsMargins(14, 14, 14, 14); wl.setSpacing(0)
        ra = QFrame()
        ra.setStyleSheet('QFrame{background:rgba(245,242,230,0.60);border-radius:12px;border:1px solid rgba(200,190,155,0.40);}')
        self._frames.append(ra)
        rl = QVBoxLayout(ra); rl.setContentsMargins(10, 10, 10, 10)
        self._result_lbl = QLabel('—')
        self._result_lbl.setAlignment(Qt.AlignCenter)
        self._result_lbl.setFont(QFont('Microsoft YaHei', 34, QFont.Bold))
        self._result_lbl.setStyleSheet('color:#2c2510;background:transparent;border:none;')
        self._result_lbl.setMinimumHeight(80); self._result_lbl.setWordWrap(True)
        rl.addWidget(self._result_lbl)
        wl.addWidget(ra)

        # 上方弹性小、下方弹性大 -> 结果框偏上
        root.addStretch(1)
        root.addWidget(wf)
        root.addStretch(3)

        # ── 抽取按钮行 ──
        btn_frame = QFrame()
        btn_frame.setStyleSheet('QFrame{background:transparent;border:none;}')
        br_outer = QVBoxLayout(btn_frame); br_outer.setContentsMargins(0, 0, 0, 0); br_outer.setSpacing(6)

        # 第一行：抽取一名 + 抽取两名
        br1 = QHBoxLayout(); br1.setSpacing(6)
        self._btn_one = self._pick_btn('抽取一名学生', True)
        self._btn_two = self._pick_btn('抽取两名学生', False)
        self._btn_one.clicked.connect(lambda: self._start_pick(1))
        self._btn_two.clicked.connect(lambda: self._start_pick(2))
        self._plain_btns.extend([self._btn_one, self._btn_two])
        br1.addWidget(self._btn_one, 1); br1.addWidget(self._btn_two, 1)
        br_outer.addLayout(br1)

        # 第二行：自定义抽取按钮 + 编辑数量按钮（紧凑排列）
        br2 = QHBoxLayout(); br2.setSpacing(4)
        self._btn_custom = CustomPickBtn(self._custom_n)
        self._btn_custom.clicked.connect(lambda: self._start_pick(self._custom_n))
        en = QPushButton('✎ 修改'); en.setCursor(Qt.PointingHandCursor)
        en.setFixedSize(72, 38)
        en.setStyleSheet('QPushButton{background:rgba(180,165,120,0.35);color:#5a5030;border:1px solid rgba(180,165,120,0.50);border-radius:7px;font-size:11px;font-weight:600;}QPushButton:hover{background:rgba(180,165,120,0.65);}')
        en.clicked.connect(self._edit_custom_n)
        self._plain_btns.append(en)
        br2.addWidget(self._btn_custom, 1); br2.addWidget(en)
        br_outer.addLayout(br2)

        # 第三行：重置抽取记录
        br3 = QHBoxLayout(); br3.setSpacing(4)
        self._btn_reset = QPushButton('重置抽取记录')
        self._btn_reset.setCursor(Qt.PointingHandCursor)
        self._btn_reset.setFixedHeight(30)
        self._btn_reset.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_reset.setStyleSheet('QPushButton{background:rgba(180,100,80,0.35);color:#6a3020;border:1px solid rgba(180,100,80,0.50);border-radius:7px;font-size:11px;font-weight:600;}QPushButton:hover{background:rgba(180,100,80,0.60);}')
        self._btn_reset.clicked.connect(self._reset_weights)
        self._plain_btns.append(self._btn_reset)
        br3.addWidget(self._btn_reset)
        br_outer.addLayout(br3)

        root.addWidget(btn_frame)

    @staticmethod
    def _mk_btn(text, r, g, b):
        btn = QPushButton(text); btn.setCursor(Qt.PointingHandCursor); btn.setFixedHeight(30)
        btn.setStyleSheet(f'QPushButton{{background:rgba({r},{g},{b},0.55);color:#fff8e8;border:none;border-radius:7px;font-size:11px;font-weight:600;padding:0 10px;}}QPushButton:hover{{background:rgba({r},{g},{b},0.78);}}')
        return btn

    @staticmethod
    def _pick_btn(text, primary):
        btn = QPushButton(text); btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(38); btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        st = ('QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:none;border-radius:9px;font-size:13px;font-weight:700;}QPushButton:hover{background:rgba(158,142,95,0.80);}' if primary else
              'QPushButton{background:rgba(200,190,155,0.45);color:#3a3220;border:1px solid rgba(200,190,155,0.65);border-radius:9px;font-size:13px;font-weight:600;}QPushButton:hover{background:rgba(210,200,165,0.72);}')
        btn.setStyleSheet(st); return btn

    def _refresh_roster_combo(self):
        self._roster_combo.blockSignals(True); self._roster_combo.clear()
        rosters = cfg.list_rosters()
        if not rosters: self._roster_combo.addItem('(无名单)')
        else:
            for r in rosters: self._roster_combo.addItem(r)
            if self._current_roster in rosters: self._roster_combo.setCurrentText(self._current_roster)
        self._roster_combo.blockSignals(False)

    def _on_roster_selected(self, name):
        if name and name != '(无名单)':
            self._current_roster = name; self._names = cfg.load_roster(name)
            cfg.set('last_roster', name)
            self._pick_counts = cfg.load_pick_weights(name); self._sync_weights()
            self._status_lbl.setText(f'已加载 {len(self._names)} 人')

    def _load_last_roster(self):
        self._scan_root_rosters()
        if self._current_roster:
            rosters = cfg.list_rosters()
            if self._current_roster in rosters:
                self._roster_combo.blockSignals(True)
                self._roster_combo.setCurrentText(self._current_roster)
                self._roster_combo.blockSignals(False)
            names = cfg.load_roster(self._current_roster)
            if names:
                self._names = names
                self._pick_counts = cfg.load_pick_weights(self._current_roster)
                self._sync_weights()
                self._status_lbl.setText(f'已加载 {len(names)} 人')
    def _scan_root_rosters(self):
        import os; from utils.roster_importer import import_file as _if
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for fname in os.listdir(base):
            if fname.lower().endswith(('.txt', '.xlsx', '.xls', '.csv')):
                try: _if(os.path.join(base, fname))
                except Exception: pass
        self._refresh_roster_combo()

    def _sync_weights(self):
        # 同步 _pick_counts（被抽次数）到名单
        if not hasattr(self, '_pick_counts'): self._pick_counts = {}
        self._pick_counts = {k: v for k, v in self._pick_counts.items() if k in self._names}
        for nm in self._names:
            if nm not in self._pick_counts: self._pick_counts[nm] = 0
        self._weights = self._counts_to_weights()

    def _counts_to_weights(self):
        """将被抽次数转换为归一化权重
        公式：weight_i = 1/(count_i+1)^1.5 + base
        base 保证每人都有最低概率，指数1.5让多次被抽者概率显著降低
        """
        import math
        if not self._names: return {}
        counts = getattr(self, '_pick_counts', {})
        raw = {nm: 1.0 / math.pow(counts.get(nm, 0) + 1, 1.5) for nm in self._names}
        total = sum(raw.values())
        # 归一化到[5, 100]区间，保证每人最低概率
        mn = min(raw.values()); mx = max(raw.values())
        if mx == mn:
            return {nm: 100.0 for nm in self._names}
        return {nm: 5.0 + 95.0 * (raw[nm] - mn) / (mx - mn) for nm in self._names}

    def _import_roster(self):
        p, _ = QFileDialog.getOpenFileName(self, '选择名单文件', '',
            '支持的文件 (*.txt *.xlsx *.xls *.csv);;所有文件 (*)')
        if p: self._do_import(p)

    def _do_import(self, p):
        names, roster_name, err = import_file(p)
        if err:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, '导入失败', err); return
        self._names = names; self._current_roster = roster_name
        self._pick_counts = cfg.load_pick_weights(roster_name); self._sync_weights()
        self._refresh_roster_combo(); self._roster_combo.setCurrentText(roster_name)
        self._status_lbl.setText(f'已加载 {len(names)} 人')

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls(): self._do_import(url.toLocalFile()); break

    def _view_roster(self):
        self._roster_view.load_names(self._names)
        self._stack.slide_to(1)

    def _show_main(self): self._stack.slide_to(0)

    def showEvent(self, event):
        super().showEvent(event)
        parent_stack = self.parent()
        if hasattr(parent_stack, '_sliding') and parent_stack._sliding:
            return
        if self._stack.currentIndex() != 0:
            self._stack.setCurrentIndex(0)

    def _edit_roster(self):
        dlg = EditRosterDialog(self._names, self)
        if dlg.exec_() == QDialog.Accepted and dlg.get_names() is not None:
            self._names = dlg.get_names()
            if self._current_roster: cfg.save_roster(self._current_roster, self._names)
            self._sync_weights()
            self._roster_view.load_names(self._names)
            self._status_lbl.setText(f'已加载 {len(self._names)} 人')

    def _edit_custom_n(self):
        dlg = NumberDialog(self._custom_n, self)
        if dlg.exec_() == QDialog.Accepted:
            self._custom_n = min(10, dlg.get_value())  # 最多10人
            self._btn_custom.set_n(self._custom_n)
            cfg.set('custom_pick_n', self._custom_n)
    def _weighted_sample(self, n):
        if not self._names: return []
        # 确保权重是最新的
        if not hasattr(self, '_pick_counts'): self._pick_counts = {}
        self._weights = self._counts_to_weights()
        pool = list(self._names)
        k = min(n, len(pool)); result = []; cur_pool = list(pool)
        for _ in range(k):
            total = sum(self._weights.get(nm, 100.0) for nm in cur_pool)
            if total <= 0: break
            r = __import__("random").uniform(0, total); acc = 0.0
            for nm in cur_pool:
                acc += self._weights.get(nm, 100.0)
                if acc >= r:
                    result.append(nm); cur_pool.remove(nm); break
        return result

    def _update_weights(self, picked):
        """基于被抽次数的权重算法：
        - 记录每人被抽总次数
        - 权重 = 1/(次数+1)^1.5，归一化到[5,100]
        - 被抽越多的人权重越低，随着其他人被抽权重自然相对回升
        - 天然均衡，不会出现权重趋同或永久排除的情况
        """
        if not hasattr(self, '_pick_counts'): self._pick_counts = {}
        for nm in picked:
            self._pick_counts[nm] = self._pick_counts.get(nm, 0) + 1
        self._weights = self._counts_to_weights()
        counts_sorted = sorted(self._pick_counts.items(), key=lambda x: -x[1])
        print(f'[抽取次数] top5: {counts_sorted[:5]} | bot5: {counts_sorted[-5:]}')
        weights_sorted = sorted(self._weights.items(), key=lambda x: -x[1])
        print(f'[权重] top5: {weights_sorted[:5]} | bot5: {weights_sorted[-5:]}')
        if self._current_roster:
            cfg.save_pick_weights(self._current_roster, self._pick_counts)

    def _reset_weights(self):
        """重置所有人被抽次数为0"""
        self._pick_counts = {nm: 0 for nm in self._names}
        self._weights = self._counts_to_weights()
        if self._current_roster:
            cfg.save_pick_weights(self._current_roster, self._pick_counts)
        self._status_lbl.setText('抽取记录已重置')
        print('[权重] 已重置所有人被抽次数为0')

    def _start_pick(self, n):
        if not self._names: self._status_lbl.setText('请先导入名单'); return
        if self._rolling: return
        self._pick_n = min(n, len(self._names))
        self._rolling = True; self._roll_count = 0
        self._roll_max = 18 + self._pick_n * 4
        self._status_lbl.setText('抽签中…'); self._roll_timer.start()

    def _roll_tick(self):
        self._roll_count += 1
        import random as _r
        sample = _r.sample(self._names, min(self._pick_n, len(self._names)))
        self._result_lbl.setText(chr(32).join(sample))
        if self._roll_count >= self._roll_max:
            self._roll_timer.stop(); self._rolling = False
            final = self._weighted_sample(self._pick_n)
            self._result_lbl.setText(chr(32).join(final))
            self._status_lbl.setText(f'抽出：{chr(32).join(final)}')
            self._update_weights(final)
            # 输出到控制台
            print(f'[主窗口抽签] 抽出: {final}')
            weights_sorted = sorted(self._weights.items(), key=lambda x: -x[1])
            print(f'[权重] top10: {weights_sorted[:10]}')
            self._finish_pick(final)

    def _finish_pick(self, names):
        pass

    def apply_night(self, night):
        self._night = night; n = night
        fg_st = ("QFrame{background:rgba(38,34,52,0.60);border-radius:14px;border:1px solid rgba(80,75,110,0.50);}" if n else
                 "QFrame{background:rgba(255,255,250,0.55);border-radius:14px;border:1px solid rgba(210,200,165,0.45.)}")
        btn_st = ("QPushButton{background:rgba(70,62,110,0.55);color:#e0d8f8;border:1px solid rgba(100,90,150,0.65);border-radius:8px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(90,80,140,0.78);}" if n else
                  "QPushButton{background:rgba(200,190,155,0.45);color:#3a3220;border:none;border-radius:8px;font-size:12px;padding:0 10px;}QPushButton:hover{background:rgba(210,200,165,0.72.)}")
        combo_st = ("QComboBox{background:rgba(48,44,66,0.80);color:#e0d8f8;border:1px solid rgba(90,82,130,0.60);border-radius:7px;padding:2px 8px;font-size:12px;}QComboBox::drop-down{border:none;}" if n else
                    "QComboBox{background:rgba(255,253,245,0.88);color:#3a3220;border:1px solid rgba(200,190,155,0.65);border-radius:7px;padding:2px 8px;font-size:12px;}QComboBox::drop-down{border:none;}")
        for w in self._frames: w.setStyleSheet(fg_st)
        for w in self._plain_btns: w.setStyleSheet(btn_st)
        self._roster_combo.setStyleSheet(combo_st)
        lbl_fg = "#e0d8f8" if n else "#2c2510"
        stat_fg = "#b0a8c8" if n else "#7a7050"
        self._result_lbl.setStyleSheet(f"color:{lbl_fg};background:transparent;border:none;")
        self._status_lbl.setStyleSheet(f"color:{stat_fg};background:transparent;border:none;")
        self._roster_view.apply_night(night)