from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ToolsPage(QWidget):
    open_automation      = pyqtSignal()
    time_island_detail    = pyqtSignal()  # 打开时间岛详情
    island_toggle_changed  = pyqtSignal(bool)  # 时间岛启用/禁用
    annotation_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        from utils import config as cfg
        self._annotation_enabled = cfg.get('annotation_enabled', True)
        self._auto_enabled = cfg.get('auto_enabled', True)
        self._island_enabled = cfg.get('island_enabled', False)
        self._night = False
        # 持有引用（不用 findChildren）
        self._frames      = []
        self._title_lbls  = []
        self._desc_lbls   = []
        self._hint_lbls   = []
        self._icon_lbls   = []
        self._plain_btns  = []
        self._accent_btns = []
        self._build_ui()

    def _mk_frame(self):
        f = QFrame()
        f.setStyleSheet('QFrame{background:rgba(255,255,250,0.55);border-radius:14px;border:1px solid rgba(210,200,165,0.45);}')
        self._frames.append(f)
        return f

    def _mk_title(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont('Microsoft YaHei', 13, QFont.Bold))
        lbl.setStyleSheet('color:#3a3220;background:transparent;border:none;')
        self._title_lbls.append(lbl)
        return lbl

    def _mk_desc(self, text):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet('font-size:12px;color:#6b6040;background:transparent;border:none;')
        self._desc_lbls.append(lbl)
        return lbl

    def _mk_hint(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet('font-size:11px;color:#9a9278;background:transparent;border:none;')
        self._hint_lbls.append(lbl)
        return lbl

    def _mk_icon(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet('font-size:20px;background:transparent;border:none;')
        self._icon_lbls.append(lbl)
        return lbl

    def _mk_plain_btn(self, text):
        btn = QPushButton(text); btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(32); btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet('QPushButton{background:rgba(200,190,155,0.45);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:8px;font-size:12px;font-weight:600;font-family:"Microsoft YaHei";}QPushButton:hover{background:rgba(200,190,155,0.72);}')
        self._plain_btns.append(btn)
        return btn

    def _mk_accent_btn(self, text):
        btn = QPushButton(text); btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(32); btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet('QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:1px solid rgba(138,122,80,0.70);border-radius:8px;font-size:12px;font-weight:600;font-family:"Microsoft YaHei";}QPushButton:hover{background:rgba(138,122,80,0.80);}')
        self._accent_btns.append(btn)
        return btn

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20,16,20,16); root.setSpacing(12)

        # ── 全局批注 ──
        anno_frame = self._mk_frame()
        al = QVBoxLayout(anno_frame); al.setContentsMargins(16,14,16,14); al.setSpacing(10)
        tr = QHBoxLayout()
        tr.addWidget(self._mk_icon('\u270d\ufe0f'))
        tr.addWidget(self._mk_title('\u5168\u5c40\u6279\u6ce8'))
        tr.addStretch()
        self._anno_status = QLabel('\u5df2\u542f\u7528')
        self._anno_status.setFixedHeight(22)
        self._anno_status.setStyleSheet('color:#4a8a4a;background:rgba(180,230,180,0.45);border:1px solid rgba(150,210,150,0.60);border-radius:6px;font-size:11px;font-weight:700;padding:0 8px;')
        tr.addWidget(self._anno_status)
        al.addLayout(tr)
        al.addWidget(self._mk_desc('\u5728\u5c4f\u5e55\u4efb\u610f\u4f4d\u7f6e\u7528\u9f20\u6807\u8fdb\u884c\u6279\u6ce8\u3001\u753b\u7ebf\uff0c\u4e0d\u5f71\u54cd\u5176\u4ed6\u5e94\u7528\u3002'))
        br = QHBoxLayout(); br.setSpacing(8)
        self._toggle_btn = self._mk_plain_btn('\u66ab\u505c\u6279\u6ce8')
        self._toggle_btn.clicked.connect(self._toggle_annotation)
        self._clear_btn = self._mk_plain_btn('\u6e05\u9664\u6279\u6ce8')
        self._clear_btn.clicked.connect(self._clear_annotation)
        br.addWidget(self._toggle_btn,1); br.addWidget(self._clear_btn,1)
        al.addLayout(br)

        root.addWidget(anno_frame)

        # ── 自动\u5316 ──
        auto_frame = self._mk_frame()
        aal = QVBoxLayout(auto_frame); aal.setContentsMargins(16,14,16,14); aal.setSpacing(10)
        atr = QHBoxLayout()
        atr.addWidget(self._mk_icon('\u26a1'))
        atr.addWidget(self._mk_title('\u81ea\u52a8\u5316'))
        atr.addStretch()
        self._auto_status = QLabel('\u5df2\u542f\u7528')
        self._auto_status.setFixedHeight(22)
        self._auto_status.setStyleSheet('color:#4a8a4a;background:rgba(180,230,180,0.45);border:1px solid rgba(150,210,150,0.60);border-radius:6px;font-size:11px;font-weight:700;padding:0 8px;')
        atr.addWidget(self._auto_status)
        aal.addLayout(atr)
        aal.addWidget(self._mk_desc('\u6839\u636e\u89e6\u53d1\u6761\u4ef6\u81ea\u52a8\u6267\u884c\u4efb\u52a1\uff0c\u5982\u5012\u8ba1\u65f6\u7ed3\u675f\u540e\u8fd0\u884c\u547d\u4ee4\u3002'))
        abr = QHBoxLayout(); abr.setSpacing(8)
        self._auto_toggle_btn = self._mk_plain_btn('\u66ab\u505c\u81ea\u52a8\u5316')
        self._auto_toggle_btn.clicked.connect(self._toggle_auto)
        detail_btn = self._mk_accent_btn('\u67e5\u770b\u8be6\u60c5')
        detail_btn.clicked.connect(self.open_automation)
        abr.addWidget(self._auto_toggle_btn,1); abr.addWidget(detail_btn,1)
        aal.addLayout(abr)
        root.addWidget(auto_frame)

        # ── 时间岛 ──
        island_frame = self._mk_frame()
        il = QVBoxLayout(island_frame); il.setContentsMargins(16,14,16,14); il.setSpacing(10)
        itr = QHBoxLayout()
        itr.addWidget(self._mk_icon('🏝'))
        itr.addWidget(self._mk_title('时间岛工具'))
        itr.addStretch()
        self._island_status = QLabel('未启用')
        self._island_status.setFixedHeight(22)
        self._island_status.setStyleSheet('color:#8a6a4a;background:rgba(230,210,180,0.45);border:1px solid rgba(210,190,155,0.60);border-radius:6px;font-size:11px;font-weight:700;padding:0 8px;')
        itr.addWidget(self._island_status)
        il.addLayout(itr)
        il.addWidget(self._mk_desc('在右上角置顶显示实时时间（时:分），不影响其他操作。'))
        ibr = QHBoxLayout(); ibr.setSpacing(8)
        self._island_toggle_btn = self._mk_plain_btn('启用时间岛')
        self._island_toggle_btn.clicked.connect(self._toggle_island)
        island_detail_btn = self._mk_accent_btn('查看详情')
        island_detail_btn.clicked.connect(self.time_island_detail)
        ibr.addWidget(self._island_toggle_btn, 1); ibr.addWidget(island_detail_btn, 1)
        il.addLayout(ibr)
        root.addWidget(island_frame)
        root.addStretch()
        self._sync_ui_state()

    def _toggle_island(self):
        self._island_enabled = not self._island_enabled
        self._island_toggle_btn.setText('\u7981\u7528\u65f6\u95f4\u5c9b' if self._island_enabled else '\u542f\u7528\u65f6\u95f4\u5c9b')
        self._island_status.setText('\u5df2\u542f\u7528' if self._island_enabled else '\u672a\u542f\u7528')
        self._apply_status_style(self._island_status, self._island_enabled)
        self.island_toggle_changed.emit(self._island_enabled)
        from utils import config as cfg; cfg.set('island_enabled', self._island_enabled)

    def _sync_ui_state(self):
        """启动时同步UI"""
        self._toggle_btn.setText('暂停批注' if self._annotation_enabled else '启用批注')
        self._anno_status.setText('已启用' if self._annotation_enabled else '未启用')
        self._apply_status_style(self._anno_status, self._annotation_enabled)
        self._auto_toggle_btn.setText('暂停自动化' if self._auto_enabled else '启用自动化')
        self._auto_status.setText('已启用' if self._auto_enabled else '未启用')
        self._apply_status_style(self._auto_status, self._auto_enabled)
        self._island_toggle_btn.setText('禁用时间岛' if self._island_enabled else '启用时间岛')
        self._island_status.setText('已启用' if self._island_enabled else '未启用')
        self._apply_status_style(self._island_status, self._island_enabled)

    def is_island_enabled(self):
        return self._island_enabled

    def _toggle_annotation(self):
        self._annotation_enabled = not self._annotation_enabled
        self._toggle_btn.setText('\u66ab\u505c\u6279\u6ce8' if self._annotation_enabled else '\u542f\u7528\u6279\u6ce8')
        self._anno_status.setText('\u5df2\u542f\u7528' if self._annotation_enabled else '\u5df2\u66ab\u505c')
        self._apply_status_style(self._anno_status, self._annotation_enabled)
        self.annotation_changed.emit(self._annotation_enabled)
        from utils import config as cfg; cfg.set('annotation_enabled', self._annotation_enabled)

    def _clear_annotation(self): pass

    def _toggle_auto(self):
        self._auto_enabled = not self._auto_enabled
        self._auto_toggle_btn.setText('\u66ab\u505c\u81ea\u52a8\u5316' if self._auto_enabled else '\u542f\u7528\u81ea\u52a8\u5316')
        self._auto_status.setText('\u5df2\u542f\u7528' if self._auto_enabled else '\u5df2\u66ab\u505c')
        self._apply_status_style(self._auto_status, self._auto_enabled)
        from utils import config as cfg; cfg.set('auto_enabled', self._auto_enabled)

    def _apply_status_style(self, lbl, enabled):
        if self._night:
            on  = 'color:#80d880;background:rgba(40,80,40,0.50);border:1px solid rgba(60,140,60,0.60);border-radius:6px;font-size:11px;font-weight:700;padding:0 8px;'
            off = 'color:#c0a870;background:rgba(60,50,30,0.50);border:1px solid rgba(110,90,50,0.60);border-radius:6px;font-size:11px;font-weight:700;padding:0 8px;'
        else:
            on  = 'color:#4a8a4a;background:rgba(180,230,180,0.45);border:1px solid rgba(150,210,150,0.60);border-radius:6px;font-size:11px;font-weight:700;padding:0 8px;'
            off = 'color:#8a6a4a;background:rgba(230,210,180,0.45);border:1px solid rgba(210,190,155,0.60);border-radius:6px;font-size:11px;font-weight:700;padding:0 8px;'
        lbl.setStyleSheet(on if enabled else off)

    def apply_night(self, night):
        self._night = night; n = night
        frame_st = ('QFrame{background:rgba(38,34,52,0.60);border-radius:14px;border:1px solid rgba(80,75,110,0.50);}' if n else
                    'QFrame{background:rgba(255,255,250,0.55);border-radius:14px;border:1px solid rgba(210,200,165,0.45);}')
        title_fg = '#e0d8f8' if n else '#3a3220'
        desc_fg  = '#b0a8c8' if n else '#6b6040'
        hint_fg  = '#7878a8' if n else '#9a9278'
        plain_st = ('QPushButton{background:rgba(70,62,110,0.55);color:#e0d8f8;border:1px solid rgba(100,90,150,0.65);border-radius:8px;font-size:12px;font-weight:600;font-family:"Microsoft YaHei";}QPushButton:hover{background:rgba(90,80,140,0.78);}' if n else
                    'QPushButton{background:rgba(200,190,155,0.45);color:#3a3220;border:1px solid rgba(200,190,155,0.60);border-radius:8px;font-size:12px;font-weight:600;font-family:"Microsoft YaHei";}QPushButton:hover{background:rgba(200,190,155,0.72);}')
        accent_st = ('QPushButton{background:rgba(90,80,140,0.70);color:#e0d8f8;border:1px solid rgba(110,100,160,0.80);border-radius:8px;font-size:12px;font-weight:600;font-family:"Microsoft YaHei";}QPushButton:hover{background:rgba(110,100,160,0.90);}' if n else
                     'QPushButton{background:rgba(138,122,80,0.55);color:#fff8e8;border:1px solid rgba(138,122,80,0.70);border-radius:8px;font-size:12px;font-weight:600;font-family:"Microsoft YaHei";}QPushButton:hover{background:rgba(138,122,80,0.80);}')
        for w in self._frames:      w.setStyleSheet(frame_st)
        for w in self._title_lbls:  w.setStyleSheet(f'color:{title_fg};background:transparent;border:none;')
        for w in self._desc_lbls:   w.setStyleSheet(f'font-size:12px;color:{desc_fg};background:transparent;border:none;')
        for w in self._hint_lbls:   w.setStyleSheet(f'font-size:11px;color:{hint_fg};background:transparent;border:none;')
        for w in self._icon_lbls:   w.setStyleSheet('font-size:20px;background:transparent;border:none;')
        for w in self._plain_btns:  w.setStyleSheet(plain_st)
        for w in self._accent_btns: w.setStyleSheet(accent_st)
        self._apply_status_style(self._anno_status, self._annotation_enabled)
        self._apply_status_style(self._auto_status, self._auto_enabled)
        from utils import config as cfg; cfg.set('auto_enabled', self._auto_enabled)
        if hasattr(self, '_island_status'):
            self._apply_status_style(self._island_status, self._island_enabled)
