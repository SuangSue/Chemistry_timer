import sys
import os

if sys.platform == 'win32':
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt, QPoint, QTimer, QObject, QEvent
from PyQt5.QtGui import QFont, QIcon

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from utils import logger as log
from ui.splash_screen import SplashScreen
from ui.floating_ball import FloatingBall
from ui.main_window import MainWindow
from ui.annotation_toolbar import AnnotationToolbar
from ui.pages.automation_page import AutomationRunner, AutomationScheduler
from ui.annotation_canvas import WhiteboardCanvas
from ui.time_island import TimeIslandWidget, TimeIslandDetailPanel
from ui.async_pick_window import AsyncPickWindow
from ui.pick_flash_overlay import PickFlashOverlay
from ui.global_hotkey import GlobalHotkey

IDLE_TIMEOUT_MS = 30_000


class IdleFilter(QObject):
    def __init__(self, idle_timer, parent=None):
        super().__init__(parent)
        self._idle_timer = idle_timer

    def eventFilter(self, obj, event):
        if event.type() in (
            QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
            QEvent.KeyPress, QEvent.TouchBegin,
        ):
            self._idle_timer.start()
        return False


class App:
    def __init__(self):
        log.setup()
        log.info('App starting')
        self._app = QApplication(sys.argv)
        self._app.setApplicationName('\u8bfe\u5802\u70b9\u540d\u8ba1\u65f6\u5668')
        self._app.setQuitOnLastWindowClosed(False)
        self._app.setFont(QFont('Microsoft YaHei', 10))

        self._main_win = MainWindow()
        self._ball     = FloatingBall()
        self._anno_bar = AnnotationToolbar()
        self._anno_bar.btn_clicked.connect(self._on_anno_btn)
        self._anno_bar.color_changed.connect(self._on_anno_color)
        self._anno_canvas = None  # 批注画布
        self._whiteboard = None   # 白板画布
        self._time_island = None  # 时间岛
        self._island_panel = None  # 时间岛详情面板
        self._async_win = AsyncPickWindow()
        self._pick_flash = PickFlashOverlay(self._main_win)
        self._fast_mode = False
        self._async_pick_enabled = True

        # 全局热键（Windows RegisterHotKey，任意场景均响应）
        self._global_hotkey = GlobalHotkey(hotkey_id=9001)
        self._global_hotkey.set_hotkey('Tab')
        self._global_hotkey.triggered.connect(self._on_async_pick)

        self._setup_tray()

        sp = self._main_win._settings_page
        if not sp.is_silent_start():
            self._splash = SplashScreen()
            self._splash.finished.connect(self._on_splash_done)
            self._splash.show()
        else:
            self._splash = None
            self._on_splash_done()

        self._ball.clicked.connect(self._on_ball_click)
        self._ball.moved.connect(self._on_ball_moved)
        self._main_win.hide_requested.connect(self._hide_main)
        self._main_win.always_top_changed.connect(self._on_always_top)
        self._main_win.theme_changed.connect(self._on_theme_changed)

        sp.opacity_changed.connect(lambda v: self._main_win.setWindowOpacity(v))
        sp.opacity_changed.connect(lambda v: self._async_win.set_opacity(v))
        sp.theme_toggle.connect(self._main_win._toggle_theme)
        sp.anim_speed_changed.connect(self._main_win.set_anim_speed)
        sp.fast_mode_changed.connect(self._on_fast_mode)
        sp.hotkey_changed.connect(self._on_hotkey_changed)
        sp.pick_speed_changed.connect(self._on_pick_speed_changed)
        if hasattr(sp, 'async_pick_changed'):
            sp.async_pick_changed.connect(self._on_async_pick_enabled)
        if hasattr(sp, 'async_duration_changed'):
            sp.async_duration_changed.connect(self._async_win.set_display_duration)

        # 初始化热键
        self._global_hotkey.set_hotkey(sp.get_hotkey())

        # 连接抽签页完成信号
        self._connect_pick_page()

        self._idle_timer = QTimer()
        self._idle_timer.setInterval(IDLE_TIMEOUT_MS)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._on_idle)
        self._idle_filter = IdleFilter(self._idle_timer)
        self._app.installEventFilter(self._idle_filter)
        self._idle_timer.start()

    def _connect_pick_page(self):
        """连接随机抽签页面的完成信号以触发浅蓝色线条动画"""
        try:
            for i in range(self._main_win._stack.count()):
                pg = self._main_win._stack.widget(i)
                if hasattr(pg, '_finish_pick') and hasattr(pg, '_weighted_sample'):
                    # monkey-patch _finish_pick
                    orig = pg._finish_pick
                    def _patched(names, _pg=pg, _orig=orig):
                        _orig(names)
                        self._pick_flash.start()
                        self._play_sound('ran.mp3')
                        if hasattr(self, '_auto_scheduler'):
                            self._auto_scheduler.notify_event('after_pick')
                    pg._finish_pick = _patched
                    break
        except Exception as e:
            print('connect_pick_page err:', e)

    def _on_theme_changed(self, night):
        if self._time_island: self._time_island.apply_night(night)
        if self._island_panel: self._island_panel.apply_night(night)
        self._anno_bar.apply_night(night)
        self._async_win.set_night(night)

    def _on_fast_mode(self, on):
        self._fast_mode = on
        self._pick_flash.set_fast_mode(on)
        self._async_win.set_fast_mode(on)
        if on:
            # 快速模式：保存当前动画速度，将动画速度设为0
            from utils import config as cfg
            self._saved_anim_speed = cfg.get('anim_speed', 250)
            self._main_win.set_anim_speed(0)
        else:
            # 恢复之前的动画速度
            from utils import config as cfg
            speed = getattr(self, '_saved_anim_speed', cfg.get('anim_speed', 250))
            self._main_win.set_anim_speed(speed)
        # 通知计时器页快速模式
        try:
            timer_pg = self._main_win._stack.widget(0)
            if hasattr(timer_pg, 'set_fast_mode'): timer_pg.set_fast_mode(on)
        except Exception: pass

    def _on_hotkey_changed(self, key):
        self._global_hotkey.set_hotkey(key)

    def _on_async_pick_enabled(self, enabled):
        self._async_pick_enabled = enabled
        self._global_hotkey.set_enabled(enabled)

    def _play_sound(self, filename):
        try:
            import os, threading, subprocess, sys
            base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, 'sounds', filename)
            if not os.path.exists(path): return
            py_exe = sys.executable
            def _play():
                try:
                    code = (
                        'import pygame; pygame.mixer.init(); '
                        f'snd=pygame.mixer.Sound(r"{path}"); '
                        'import time; snd.play(); time.sleep(snd.get_length()+0.3)'
                    )
                    subprocess.run([py_exe, '-c', code],
                        timeout=30, creationflags=0x08000000)
                except Exception as e2:
                    print('sound err:', e2)
            threading.Thread(target=_play, daemon=True).start()
        except Exception as e:
            print('sound err:', e)

    def _on_pick_speed_changed(self, v):
        """抽取速度：v=0最快(内徯roll_max=1,interval=16ms), v=100最慢(roll_max=40,interval=120ms)"""
        try:
            for i2 in range(self._main_win._stack.count()):
                pg = self._main_win._stack.widget(i2)
                if hasattr(pg, '_roll_timer') and hasattr(pg, '_roll_max'):
                    # v=0: interval=16ms, roll_max=18; v=100: interval=120ms, roll_max=40
                    interval = int(16 + v * 1.04)  # 16~120ms
                    pg._roll_timer.setInterval(interval)
                    pg._roll_max_base = int(18 + v * 0.22)  # 18~40
                    break
        except Exception as e:
            print('pick_speed err:', e)
        from utils import config as cfg; cfg.set('pick_speed', v)
    def _on_async_pick(self):
        """热键触发：异步抽签，保存权重到记录"""
        # 上一个窗口未隐藏时不触发新抽签
        if self._async_win.is_busy():
            return
        try:
            names = []
            for i in range(self._main_win._stack.count()):
                pg = self._main_win._stack.widget(i)
                if hasattr(pg, '_weighted_sample') and hasattr(pg, '_names'):
                    if pg._names:
                        names = pg._weighted_sample(1)
                        if names:
                            pg._update_weights(names)
                            # 打印权重到控制台供检查
                            print(f'[抽签] 抽出: {names}')
                            weights_sorted = sorted(pg._weights.items(), key=lambda x: -x[1])
                            print(f'[权重] top10: {weights_sorted[:10]}')
                            log.info(f'async_pick: {names} | top5_weights: {weights_sorted[:5]}')
                        self._async_win.set_roster_info(
                            getattr(pg, '_current_roster', ''),
                            len(pg._names)
                        )
                    break
            self._async_win.show_result(names if names else ['无名单'])
            self._play_sound('ran.mp3')
        except Exception as e:
            self._async_win.show_result(['错误'])
            print('async_pick err:', e)

    def _on_anno_btn(self, bid):
        """批注工具栏按钮点击处理"""
        if bid == 'annotate':
            # 切换为批注模式，创建透明画布
            self._ensure_canvas()
            self._anno_canvas.set_mode('draw')
            if not self._anno_canvas.isVisible():
                self._anno_canvas.show()
            self._anno_canvas.raise_()
            # 确保工具栏在画布上方
            self._anno_bar.raise_()
            # 绘制后定期将浮球置顶
            self._schedule_ball_raise()
            # 隐藏白板（如果开着）
            if self._whiteboard and self._whiteboard.isVisible():
                self._whiteboard.hide()
        elif bid == 'select':
            # 选择：画布鼠标穿透
            if self._anno_canvas and self._anno_canvas.isVisible():
                self._anno_canvas.set_mode('select')
        elif bid == 'eraser':
            self._ensure_canvas()
            self._anno_canvas.set_mode('eraser')
            if not self._anno_canvas.isVisible():
                self._anno_canvas.show()
            self._anno_canvas.raise_()
            self._schedule_ball_raise()
        elif bid == 'clear':
            # 清空当前画布笔迹，自动切换为选择
            if self._anno_canvas:
                self._anno_canvas.clear_strokes()
            if self._whiteboard and self._whiteboard.isVisible():
                self._whiteboard.clear_strokes()
            self._anno_bar._selected = 'select'
            self._anno_bar._update_checked()
            if self._anno_canvas:
                self._anno_canvas.set_mode('select')
        elif bid == 'whiteboard':
            # 白板：切换开/关
            if self._whiteboard and self._whiteboard.isVisible():
                # 再次点击：隐藏白板，切换为选择
                self._whiteboard.hide()
                self._anno_bar._selected = 'select'
                self._anno_bar._update_checked()
            else:
                # 打开白板，自动切换为批注
                self._ensure_whiteboard()
                self._whiteboard.show()
                self._whiteboard.raise_()
                # 白板上的工具栏也同步选中批注
                self._whiteboard._toolbar.set_selected('annotate')
                self._anno_bar._selected = 'annotate'
                self._anno_bar._update_checked()
                # 隐藏透明画布（白板本身可以绘画）
                if self._anno_canvas and self._anno_canvas.isVisible():
                    self._anno_canvas.hide()
            # 确保浮球和工具栏置顶
            self._ball.raise_()
            self._anno_bar.raise_()
        elif bid == 'pick':
            self._on_async_pick()
            self._hide_main()
            self._anno_bar.hide_anim()

    def _on_anno_color(self, color_key):
        """批注颜色变更"""
        if self._anno_canvas:
            self._anno_canvas.set_color(color_key)
        if self._whiteboard:
            self._whiteboard.set_pen_color(color_key)

    def _ensure_whiteboard(self):
        """懒创建白板"""
        if self._whiteboard is None:
            from ui.annotation_canvas import WhiteboardCanvas
            self._whiteboard = WhiteboardCanvas()
            # 白板底部工具栏按钮转发到主逻辑
            self._whiteboard.toolbar_btn.connect(self._on_anno_btn)
            # 绘制后置顶浮球
            self._whiteboard.ball_raise_needed.connect(self._schedule_ball_raise)
        self._whiteboard.set_pen_color(self._anno_bar.get_color())

    def _ensure_canvas(self):
        """懒创建全屏批注画布"""
        if self._anno_canvas is None:
            from ui.annotation_canvas import AnnotationCanvas
            tb_geo = self._anno_bar.geometry() if self._anno_bar.isVisible() else None
            self._anno_canvas = AnnotationCanvas(exclude_geo=tb_geo)
            self._anno_canvas.set_color(self._anno_bar.get_color())
            self._anno_canvas.ball_raise_needed.connect(self._schedule_ball_raise)
        else:
            # 更新工具栏排除区域
            if self._anno_bar.isVisible():
                self._anno_canvas.set_exclude_geo(self._anno_bar.geometry())

    def _is_annotation_enabled(self):
        try:
            tools_page = self._main_win._stack.widget(3)
            return getattr(tools_page, '_annotation_enabled', False)
        except Exception: return False

    def _on_idle(self):
        timer_page = self._main_win._stack.widget(0)
        if hasattr(timer_page, 'is_counting') and timer_page.is_counting():
            self._idle_timer.start(); return
        if self._anno_bar.is_shown(): self._anno_bar.hide_anim()
        self._ball.snap_to_edge()
        if self._main_win.isVisible(): self._hide_main()

    def _setup_tray(self):
        base = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base, 'pictures', 'icon.png')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self._tray = QSystemTrayIcon(icon, self._app)
        self._tray.setToolTip('\u8bfe\u5802\u70b9\u540d\u8ba1\u65f6\u5668')
        menu = QMenu()
        show_act = QAction('\u663e\u793a\u4e3b\u7a97\u53e3', menu)
        show_act.triggered.connect(self._show_from_tray)
        menu.addAction(show_act)
        toggle_ball = QAction('\u663e\u793a/\u9690\u85cf\u6d6e\u7403', menu)
        toggle_ball.triggered.connect(self._toggle_ball)
        menu.addAction(toggle_ball)
        menu.addSeparator()
        quit_act = QAction('\u9000\u51fa', menu)
        quit_act.triggered.connect(self._app.quit)
        menu.addAction(quit_act)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick: self._show_from_tray()

    def _show_from_tray(self):
        if not self._main_win.isVisible():
            self._main_win.show_near_ball(self._ball.geometry(), self._ball_prefers_left())
            self._ball.set_main_visible(True)

    def _toggle_ball(self):
        if self._ball.isVisible(): self._ball.hide()
        else: self._ball.show()

    def _on_splash_done(self):
        # 启动自动化调度器
        auto_pg = self._main_win._automation_page
        self._auto_scheduler = AutomationScheduler(auto_pg)
        self._auto_scheduler.start()
        # 加载已保存的自动化
        try:
            auto_pg.load_automations()
            log.info(f'Loaded {len(auto_pg._auto_items)} automations')
        except Exception as _e:
            log.error(f'load_automations: {_e}')
        # 注入抽签回调给 AutomationRunner
        def _pick_one_cb():
            for i in range(self._main_win._stack.count()):
                pg = self._main_win._stack.widget(i)
                if hasattr(pg, '_weighted_sample') and hasattr(pg, '_names') and pg._names:
                    names = pg._weighted_sample(1)
                    if names: pg._update_weights(names)
                    return names[0] if names else ''
            return ''
        AutomationRunner._pick_cb = _pick_one_cb

        # 应用已保存的设置
        screen = self._app.primaryScreen().availableGeometry()
        self._ball.move_to_default(screen)
        self._ball.show()
        from PyQt5.QtCore import QTimer as _QT
        _QT.singleShot(100, self._apply_saved_settings)
        try:
            tools_pg = self._main_win._stack.widget(3)
            if hasattr(tools_pg, 'annotation_changed'):
                tools_pg.annotation_changed.connect(self._on_annotation_changed)
            if hasattr(tools_pg, 'time_island_detail'):
                tools_pg.time_island_detail.connect(self._show_island_panel)
            if hasattr(tools_pg, 'island_toggle_changed'):
                tools_pg.island_toggle_changed.connect(self._on_island_toggle)
        except Exception: pass
        self._connect_pick_page()


    def _on_island_toggle(self):
        """时间岛启用/禁用 & 显示详情面板"""
        try:
            tools_pg = self._main_win._stack.widget(3)
            enabled = getattr(tools_pg, '_island_enabled', False)
            if enabled:
                if self._time_island is None:
                    self._time_island = TimeIslandWidget()
                    self._time_island.apply_night(self._main_win._night)
                self._time_island.show()
                self._time_island.raise_()
            else:
                if self._time_island:
                    self._time_island.hide()
                if self._island_panel and self._island_panel.isVisible():
                    self._island_panel.hide()
        except Exception as e:
            print(f'[island_toggle] {e}')

    def _hide_island_panel(self):
        """关闭时间岛详情面板，淡出动画"""
        if self._island_panel is None: return
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        _eff = QGraphicsOpacityEffect(self._island_panel)
        _eff.setOpacity(1.0)
        self._island_panel.setGraphicsEffect(_eff)
        _anim = QPropertyAnimation(_eff, b'opacity')
        _anim.setDuration(180)
        _anim.setStartValue(1.0)
        _anim.setEndValue(0.0)
        _anim.setEasingCurve(QEasingCurve.InCubic)
        _anim.finished.connect(self._island_panel.hide)
        _anim.finished.connect(lambda: self._island_panel.setGraphicsEffect(None))
        _anim.start()
        self._island_panel._hide_anim = _anim

    def _show_island_panel(self):
        """在主窗口内显示时间岛详情面板"""
        try:
            if self._time_island is None:
                self._time_island = TimeIslandWidget()
                self._time_island.apply_night(self._main_win._night)
            if self._island_panel is None:
                self._island_panel = TimeIslandDetailPanel(self._time_island, self._main_win)
                self._island_panel.closed.connect(self._hide_island_panel)
                self._island_panel.apply_night(self._main_win._night)
            mw = self._main_win
            pw, ph = mw.width(), mw.height()
            pw2, ph2 = 320, 230
            self._island_panel.setFixedSize(pw2, ph2)
            self._island_panel.move((pw - pw2) // 2, (ph - ph2) // 2)
            self._island_panel.show()
            self._island_panel.raise_()
            # 使用 QGraphicsOpacityEffect 实现淡入动画
            from PyQt5.QtWidgets import QGraphicsOpacityEffect
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
            _eff = QGraphicsOpacityEffect(self._island_panel)
            _eff.setOpacity(0.0)
            self._island_panel.setGraphicsEffect(_eff)
            _anim = QPropertyAnimation(_eff, b'opacity')
            _anim.setDuration(220)
            _anim.setStartValue(0.0)
            _anim.setEndValue(1.0)
            _anim.setEasingCurve(QEasingCurve.OutCubic)
            _anim.finished.connect(lambda: self._island_panel.setGraphicsEffect(None))
            _anim.start()
            self._island_panel._fade_anim = _anim
        except Exception as e:
            print(f'[island_panel] {e}')

    def _schedule_ball_raise(self):
        """绘制后短暂延迟将浮球置顶"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._ball.raise_() if self._ball.isVisible() else None)
        QTimer.singleShot(500, lambda: self._ball.raise_() if self._ball.isVisible() else None)

    def _apply_saved_settings(self):
        """启动时应用所有保存的设置"""
        from utils import config as cfg
        # 透明度（已通过 QTimer.singleShot 延迟调用，确保窗口已 show）
        opac = cfg.get('opacity', 95) / 100.0
        self._main_win.setWindowOpacity(opac)
        self._async_win.set_opacity(opac)
        self._main_win.set_anim_speed(cfg.get('anim_speed', 250))
        self._fast_mode = cfg.get('fast_mode', False)
        self._global_hotkey.set_hotkey(cfg.get('hotkey', 'Tab'))
        self._async_pick_enabled = cfg.get('async_pick', True)
        dur = cfg.get('async_duration', 1.75)
        if hasattr(self._async_win, 'set_display_duration'): self._async_win.set_display_duration(dur)
        # 抽取速度：无条件应用，0=立即也需要设置 interval=16ms
        self._on_pick_speed_changed(cfg.get('pick_speed', 0))
        night = cfg.get('night_mode', False)
        if night != self._main_win._night: self._main_win._toggle_theme()
        island_enabled = cfg.get('island_enabled', False)
        if island_enabled:
            if self._time_island is None:
                from ui.time_island import TimeIslandWidget
                self._time_island = TimeIslandWidget()
                self._time_island.apply_night(self._main_win._night)
            self._time_island.show()
            self._time_island.raise_()
    def _on_annotation_changed(self, enabled):
        if enabled:
            mw_geo = self._main_win.geometry() if self._main_win.isVisible() else None
            self._anno_bar.show_near(self._ball.geometry(), mw_geo)
            self._anno_bar.raise_()
        else:
            if self._anno_bar.is_shown(): self._anno_bar.hide_anim()
            if self._anno_canvas and self._anno_canvas.isVisible():
                self._anno_canvas.hide()

    def _ball_prefers_left(self):
        screen = self._app.primaryScreen().availableGeometry()
        return self._ball.geometry().center().x() > screen.width() // 2

    def _on_ball_click(self, center: QPoint):
        if self._main_win.isVisible():
            self._hide_main()
            if self._anno_bar.is_shown(): self._anno_bar.hide_anim()
            self._ball.set_main_visible(False)
        else:
            self._main_win.show_near_ball(self._ball.geometry(), self._ball_prefers_left())
            self._ball.set_main_visible(True)
            if self._is_annotation_enabled():
                mw_geo = self._main_win.geometry()
                self._anno_bar.show_near(self._ball.geometry(), mw_geo)
                self._anno_bar.raise_()

    def _on_ball_moved(self, ball_geo):
        self._main_win.follow_ball(ball_geo, self._ball_prefers_left())
        if self._anno_bar.is_shown():
            mw_geo = self._main_win.geometry() if self._main_win.isVisible() else None
            self._anno_bar.show_near(ball_geo, mw_geo)

    def _hide_main(self):
        self._main_win.hide_with_anim()
        self._ball.set_main_visible(False)
        if self._anno_bar.is_shown(): self._anno_bar.hide_anim()

    def _on_always_top(self, on: bool):
        flags = self._main_win.windowFlags()
        if on: flags |= Qt.WindowStaysOnTopHint
        else:  flags &= ~Qt.WindowStaysOnTopHint
        visible = self._main_win.isVisible()
        self._main_win.setWindowFlags(flags)
        if visible: self._main_win.show()

    def run(self):
        return self._app.exec_()


def _check_single_instance():
    """检测是否已有程序实例运行"""
    import socket
    import sys
    
    # 使用本地 socket 作为锁文件
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 尝试绑定到本地端口 9999（选择一个不常用的端口）
        sock.bind(('127.0.0.1', 9999))
        sock.listen(1)
        return True, sock  # 成功绑定，这是第一个实例
    except OSError:
        # 端口已被占用，说明已有实例运行
        sock.close()
        return False, None


if __name__ == '__main__':
    # 检测单实例
    is_first, lock_sock = _check_single_instance()
    if not is_first:
        print('程序已在运行，停止启动')
        sys.exit(1)
    
    try:
        app = App()
        sys.exit(app.run())
    finally:
        if lock_sock:
            lock_sock.close()
