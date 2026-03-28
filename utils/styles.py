# ── 日间主题（默认）──────────────────────────────────
DAY = {
    'card_top':    (255, 255, 253, 218),
    'card_mid':    (253, 251, 244, 208),
    'card_bot':    (248, 244, 232, 200),
    'border':      (215, 205, 168, 170),
    'nav_bg':      'rgba(255,255,252,0.72)',
    'nav_border':  'rgba(220,210,175,0.55)',
    'nav_btn_fg':  '#6b6550',
    'nav_btn_hover_bg': 'rgba(220,210,175,0.30)',
    'nav_btn_hover_fg': '#3a3220',
    'nav_act_bg':  'rgba(230,220,190,0.45)',
    'nav_act_fg':  '#2c2510',
    'nav_act_border': 'rgba(200,188,150,0.60)',
    'page_label':  '#2c2510',
    'page_btn_bg': 'rgba(200,188,150,0.55)',
    'page_btn_fg': '#2c2510',
    'page_btn_border': 'rgba(200,188,150,0.70)',
    'page_btn_hover': 'rgba(210,198,160,0.80)',
    'input_bg':    'rgba(255,255,250,0.78)',
    'input_border':'rgba(210,200,165,0.60)',
    'input_focus_border': 'rgba(180,165,110,0.85)',
    'input_focus_bg': 'rgba(255,255,252,0.92)',
    'scroll_track':'rgba(230,225,205,0.25)',
    'scroll_handle':'rgba(190,178,140,0.60)',
}

# ── 夜间主题 ──────────────────────────────────────────
NIGHT = {
    'card_top':    (38,  36,  48,  228),
    'card_mid':    (32,  30,  42,  222),
    'card_bot':    (26,  24,  36,  218),
    'border':      (80,  75, 110, 160),
    'nav_bg':      'rgba(40,38,52,0.88)',
    'nav_border':  'rgba(80,75,110,0.55)',
    'nav_btn_fg':  '#c8c0e0',
    'nav_btn_hover_bg': 'rgba(80,75,110,0.35)',
    'nav_btn_hover_fg': '#e8e0ff',
    'nav_act_bg':  'rgba(90,82,130,0.55)',
    'nav_act_fg':  '#f0ecff',
    'nav_act_border': 'rgba(120,110,170,0.65)',
    'page_label':  '#e0d8f8',
    'page_btn_bg': 'rgba(80,72,120,0.60)',
    'page_btn_fg': '#e8e0ff',
    'page_btn_border': 'rgba(100,90,150,0.70)',
    'page_btn_hover': 'rgba(100,92,145,0.80)',
    'input_bg':    'rgba(48,44,66,0.80)',
    'input_border':'rgba(90,82,130,0.60)',
    'input_focus_border': 'rgba(130,118,190,0.88)',
    'input_focus_bg': 'rgba(55,50,75,0.92)',
    'scroll_track':'rgba(60,56,80,0.30)',
    'scroll_handle':'rgba(100,90,145,0.65)',
}

_theme = DAY

def set_theme(night: bool):
    global _theme
    _theme = NIGHT if night else DAY
    _rebuild()

def _rebuild():
    global NAV_BAR_STYLE, NAV_BUTTON_NORMAL, NAV_BUTTON_ACTIVE, PAGE_STYLE
    t = _theme
    NAV_BAR_STYLE = f"""
        QWidget#NavBar {{
            background: {t['nav_bg']};
            border-bottom: 1px solid {t['nav_border']};
            border-top-left-radius: 18px;
            border-top-right-radius: 18px;
        }}
    """
    NAV_BUTTON_NORMAL = f"""
        QPushButton {{
            background: transparent;
            color: {t['nav_btn_fg']};
            border: none;
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 13px;
            font-weight: 500;
            font-family: 'Microsoft YaHei', sans-serif;
        }}
        QPushButton:hover {{
            background: {t['nav_btn_hover_bg']};
            color: {t['nav_btn_hover_fg']};
        }}
    """
    NAV_BUTTON_ACTIVE = f"""
        QPushButton {{
            background: {t['nav_act_bg']};
            color: {t['nav_act_fg']};
            border: 1px solid {t['nav_act_border']};
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 13px;
            font-weight: 700;
            font-family: 'Microsoft YaHei', sans-serif;
        }}
    """
    PAGE_STYLE = f"""
        QWidget#PageWidget {{ background: transparent; }}
        QLabel {{ color: {t['page_label']}; font-family: 'Microsoft YaHei', sans-serif; }}
        QPushButton {{
            background: {t['page_btn_bg']};
            color: {t['page_btn_fg']};
            border: 1px solid {t['page_btn_border']};
            border-radius: 8px;
            padding: 6px 22px;
            font-size: 13px;
            font-weight: 600;
            font-family: 'Microsoft YaHei', sans-serif;
        }}
        QPushButton:hover {{ background: {t['page_btn_hover']}; }}
        QLineEdit, QTextEdit {{
            background: {t['input_bg']};
            border: 1px solid {t['input_border']};
            border-radius: 7px;
            padding: 5px 9px;
            color: {t['page_label']};
            font-family: 'Microsoft YaHei', sans-serif;
            font-size: 13px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 1.5px solid {t['input_focus_border']};
            background: {t['input_focus_bg']};
        }}
        QScrollBar:vertical {{
            background: {t['scroll_track']};
            width: 6px; border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['scroll_handle']};
            border-radius: 3px; min-height: 24px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """

# 初始化
_rebuild()
