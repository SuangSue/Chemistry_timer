import tkinter as tk
from tkinter import ttk
import time
from PIL import Image, ImageTk, ImageDraw
import win32gui
import win32con
import pystray
import threading
import winsound
import random
import os
import sys
import win32event
import win32api
import winerror
import json
from tkinter import messagebox
import keyboard
import logging
from datetime import datetime
from typing import Optional, Any, Tuple
import functools
import requests
import webbrowser

# 将 UpdateChecker 类移到这里，在所有其他类之前
class UpdateChecker:
    """更新检查类"""
    
    VERSION = "5.0"  # 当前版本号
    UPDATE_URL = "https://api.github.com/repos/SuangSue/Chemistry_timer/releases/latest"
    
    @classmethod
    def check_update(cls) -> Tuple[bool, str, str]:
        """检查更新"""
        try:
            # 添加请求头，避免API限制
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Chemistry-Timer-App'
            }
            
            response = requests.get(cls.UPDATE_URL, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            latest_version = data['tag_name'].lstrip('v')
            download_url = data['assets'][0]['browser_download_url']
            
            has_update = cls._compare_versions(latest_version, cls.VERSION)
            return has_update, latest_version, download_url
            
        except Exception as e:
            Logger.error(f"检查更新失败: {e}")
            return False, cls.VERSION, ""
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> bool:
        """比较版本号
        
        Args:
            v1: 版本号1
            v2: 版本号2
            
        Returns:
            bool: 如果v1 > v2返回True
        """
        def normalize(v):
            return [int(x) for x in v.split('.')]
            
        return normalize(v1) > normalize(v2)

class Logger:
    """日志管理类"""
    
    def __init__(self):
        # 创建日志目录
        log_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志文件名
        log_file = os.path.join(log_dir, f'chemistry_timer_{datetime.now().strftime("%Y%m%d")}.log')
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    @staticmethod
    def info(msg: str) -> None:
        """记录信息日志"""
        logging.info(msg)
        
    @staticmethod
    def error(msg: str) -> None:
        """记录错误日志"""
        logging.error(msg)
        
    @staticmethod
    def debug(msg: str) -> None:
        """记录调试日志"""
        logging.debug(msg)

class StateManager:
    """状态管理器"""
    
    def __init__(self):
        self.states = {}
        
    def set_state(self, key: str, value: Any) -> None:
        """设置状态"""
        self.states[key] = value
        Logger.debug(f"状态更新: {key} = {value}")
        
    def get_state(self, key: str, default: Any = None) -> Any:
        """获取状态"""
        return self.states.get(key, default)

class PerformanceMonitor:
    """性能监控类"""
    
    def __init__(self):
        self.metrics = {}
        
    def start_measure(self, name: str) -> None:
        """开始测量操作耗时"""
        self.metrics[name] = time.time()
        
    def end_measure(self, name: str) -> Optional[float]:
        """结束测量并返回耗时"""
        if name in self.metrics:
            duration = time.time() - self.metrics[name]
            del self.metrics[name]
            return duration
        return None

class Config:
    def __init__(self):
        # 使用用户目录
        self.config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
        # 确保目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        # 配置文件路径
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        self.default_config = {
            "opacity": 0.8,
            "sound_enabled": True,
            "theme": "默认蓝",
            "draw_speed": 8.0,  # 修改默认值为 8.0
            "hotkey": "enter",
            "always_allow_quick_draw": False,
            "async_draw": False,
            "async_draw_animation": False,
            "hide_delay": 2.0,  # 添加新的设置项，默认2秒
            "always_auto_hide": True  # 添加的设置项
        }
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = self.default_config
            self.save_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.config = self.default_config

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def get(self, key):
        return self.config.get(key, self.default_config.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

class SingleInstance:
    def __init__(self):
        self.mutexname = "ChemistryTimer_{D0E858DF-985E-4907-B7FB-8D732C3FC3B9}"
        self.mutex = win32event.CreateMutex(None, False, self.mutexname)
        self.lasterror = win32api.GetLastError()
    
    def already_running(self):
        return (self.lasterror == winerror.ERROR_ALREADY_EXISTS)

    def activate_running_instance(self):
        """激活已运行实例"""
        try:
            # 查找所有顶层窗口
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if "化学计时器" in window_text:
                        windows.append(hwnd)
                return True

            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            # 如果找到窗口，激活它
            if windows:
                hwnd = windows[0]
                # 如果窗口被最小化，恢复它
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                # 将窗口置于前台
                win32gui.SetForegroundWindow(hwnd)
                return True
            
            # 如果有找到可见窗口，尝试查找系统托盘
            def find_tray_window(hwnd, windows):
                if "化学计时器" in win32gui.GetWindowText(hwnd):
                    windows.append(hwnd)
                return True
                
            tray_windows = []
            win32gui.EnumWindows(find_tray_window, tray_windows)
            
            if tray_windows:
                # 发送自定义消息给已存在的实例
                win32gui.SendMessage(tray_windows[0], win32con.WM_USER + 20, 0, 0)
                return True
                
        except Exception as e:
            print(f"激活窗口败: {e}")
        return False

class ScrollableSpinbox(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.spinbox = ttk.Spinbox(self, from_=0, to=59, wrap=True, width=2, font=("Arial", 24), justify=tk.CENTER)
        self.spinbox.pack(expand=True, fill=tk.BOTH)

        self.spinbox.bind("<Button-1>", self.on_click)
        self.spinbox.bind("<B1-Motion>", self.on_drag)
        self.spinbox.bind("<ButtonRelease-1>", self.on_release)

        self.y = 0
        self.dragging = False

    def on_click(self, event):
        self.y = event.y
        self.dragging = True

    def on_drag(self, event):
        if self.dragging:
            delta = self.y - event.y
            if abs(delta) > 10:
                value = int(self.spinbox.get())
                new_value = (value + (1 if delta > 0 else -1)) % 60
                self.spinbox.set(f"{new_value:02d}")
                self.y = event.y

    def on_release(self, event):
        self.dragging = False

    def get(self):
        return self.spinbox.get()

    def set(self, value):
        self.spinbox.set(value)

class FloatingBall(tk.Toplevel):
    def __init__(self, master, size=50):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-transparentcolor', 'white')
        self.wm_attributes("-toolwindow", True)
        self.geometry(f"{size}x{size}+200+200")
        self.configure(bg='white')
        
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            
            image_path = os.path.join(base_path, "化学计时器.png")
            self.image = Image.open(image_path)
            self.image = self.image.resize((size, size), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(self.image)

            self.canvas = tk.Canvas(self, width=size, height=size, bg='white', highlightthickness=0)
            self.canvas.pack()
            self.canvas.create_image(size//2, size//2, image=self.photo)
        except Exception as e:
            print(f"加载图片失败: {e}")
            self.canvas = tk.Canvas(self, width=size, height=size, bg='lightblue', highlightthickness=0)
            self.canvas.pack()
            self.canvas.create_text(size//2, size//2, text="CT", font=("Arial", 16))
        
        # 修改拖动相关变量
        self.drag_data = {
            "x": 0, 
            "y": 0, 
            "start_x": 0,
            "start_y": 0,
            "clicked": False
        }
        
        # 只在 canvas 上绑定事件，而不是在窗口上
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

    def on_press(self, event):
        """鼠标按下时记录起始位置"""
        # 转换为相对于窗口的坐标
        self.drag_data["x"] = event.x_root - self.winfo_x()
        self.drag_data["y"] = event.y_root - self.winfo_y()
        self.drag_data["start_x"] = event.x_root
        self.drag_data["start_y"] = event.y_root
        self.drag_data["clicked"] = True
        return "break"  # 阻止事件继续传播

    def on_release(self, event):
        """鼠标释放时处理点击事件"""
        if not self.drag_data["clicked"]:
            return "break"
            
        # 计算移动距离
        dx = abs(event.x_root - self.drag_data["start_x"])
        dy = abs(event.y_root - self.drag_data["start_y"])
        
        # 如果移动距离小于阈值（5像素），认为是点击而不是拖动
        if dx < 5 and dy < 5 and hasattr(self.master, 'toggle_visibility'):
            self.master.toggle_visibility()
            
        # 重置点击状态
        self.drag_data["clicked"] = False
        return "break"  # 阻止事件继续传播

    def on_drag(self, event):
        """处拖事件"""
        # 如果已经开始拖动，取消点击状态
        self.drag_data["clicked"] = False
        
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        
        # 保不超出屏幕
        x = max(0, min(x, self.screen_width - self.winfo_width()))
        y = max(0, min(y, self.screen_height - self.winfo_height()))
        
        # 计算移动距离
        dx = abs(event.x_root - self.drag_data["start_x"])
        dy = abs(event.y_root - self.drag_data["start_y"])
        
        # 只有当移动距离超过阈值时才进行拖动
        if dx > 5 or dy > 5:
            self.geometry(f"+{x}+{y}")
            
            # 更新主窗口位
            if self.master and hasattr(self.master, 'move_main_window'):
                if x + self.winfo_width() > self.screen_width * 0.8:
                    self.master.move_main_window(x - self.master.master.winfo_width(), y)
                else:
                    self.master.move_main_window(x + self.winfo_width(), y)
        
        return "break"  # 阻止事件继续传播

class ChemistryTimer:
    def __init__(self, master):
        # 保存主窗口引用
        self.master = master
        
        # 在其他初始化之前添加系统托盘相关的属性
        self.icon = None
        self.tray_created = False
        
        # 添加异步抽签相关的属性
        self.async_drawing = False  # 添加这一行
        
        # 初始化基础组件
        self.logger = Logger()
        self.resource_manager = ResourceManager()
        self.performance_monitor = PerformanceMonitor()
        self.state_manager = StateManager()
        
        # 记录启动
        Logger.info("化学计时器启动")
        self.performance_monitor.start_measure("initialization")
        
        # 初始化配置
        self.config = Config()
        Logger.info(f"加载配置: {self.config.config}")
        
        # 初始化主题
        self.init_themes()
        
        # 初始化主窗口属性
        master.title("化学计时器")
        master.overrideredirect(True)
        master.attributes('-alpha', self.config.get("opacity"))
        master.attributes('-topmost', True)
        master.wm_attributes("-toolwindow", True)
        master.geometry("600x450+230+200")
        
        # 获取屏幕尺寸
        self.screen_width = master.winfo_screenwidth()
        self.screen_height = master.winfo_screenheight()
        
        # 初始化其他属性
        self.visible = True
        self.time_running1 = False
        self.time_running2 = False
        self.time_count1 = 0
        self.time_count2 = 0
        self.current_mode = "forward"
        self.last_selected_file = None
        
        # 创建主框架和UI组件
        self.create_main_frame()
        self.create_top_navbar()
        self.create_left_navbar()
        self.create_main_content()
        
        # 创建浮球
        self.floating_ball = FloatingBall(master, size=50)
        self.floating_ball.master = self
        self.floating_ball.lift()
        
        # 绑定事件
        self.bind_events()
        
        # 创建水印
        self.create_watermark()
        
        # 初始化系统托盘
        self.create_system_tray()
        
        # 记录初始化完成
        duration = self.performance_monitor.end_measure("initialization")
        Logger.info(f"初始化完成，耗时: {duration:.3f}秒")
        
        # 延迟检查更新
        self.master.after(3000, self.check_for_updates)

    def create_main_frame(self):
        """创建主框架"""
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def bind_events(self):
        """绑定事件"""
        # 绑定窗口移动事件
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<ButtonRelease-1>", self.stop_move)
        self.master.bind("<B1-Motion>", self.do_move)
        
        # 绑定焦点事件
        self.master.bind("<FocusIn>", self.prevent_focus)
        
        # 绑定关闭事件
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 注册全局热键
        try:
            keyboard.on_press_key(self.config.get("hotkey"), self.handle_global_hotkey)
        except Exception as e:
            Logger.error(f"注册全局热键失败: {e}")

    def prevent_focus(self, event):
        """防止窗口获取焦点"""
        if event.widget == self.master:
            self.master.focus_force()
            # 立即将焦点还给之前的窗口
            self.master.after(1, lambda: self.master.wm_attributes("-topmost", False))
            self.master.after(2, lambda: self.master.wm_attributes("-topmost", True))
        return "break"

    def init_themes(self):
        """初始化主题"""
        self.themes = {
            "默认蓝": {
                'nav': '#87CEEB',  # 天蓝色
                'bg': '#F0F0F0',   # 浅灰色
                'text': 'black',
                'left_nav': '#D3D3D3'  # 左侧导航栏颜色
            },
            "深邃黑": {
                'nav': '#2C2C2C',      # 深灰色
                'bg': '#1E1E1E',       # 更深的灰色
                'text': '#FFFFFF',     # 白色文字
                'left_nav': '#383838'  # 深色导航栏
            },
            "清新绿": {
                'nav': '#90EE90',  # 浅绿色
                'bg': '#F0FFF0',   # 蜜瓜色
                'text': 'black',
                'left_nav': '#C1FFC1'
            },
            "暖阳橙": {
                'nav': '#FFA500',  # 橙色
                'bg': '#FFF5E6',   # 浅橙色
                'text': 'black',
                'left_nav': '#FFE4B5'
            },
            "梦幻紫": {
                'nav': '#DDA0DD',  # 梅红色
                'bg': '#F5E6F5',   # 浅紫色
                'text': 'black',
                'left_nav': '#E6E6FA'
            },
            "海洋蓝": {
                'nav': '#4169E1',  # 皇家蓝
                'bg': '#F0F8FF',   # 爱丽丝蓝
                'text': 'black',
                'left_nav': '#B0C4DE'
            },
            "樱花粉": {
                'nav': '#FFB6C1',  # 浅粉色
                'bg': '#FFF0F5',   # 紫红
                'text': 'black',
                'left_nav': '#FFC0CB'
            },
            "高级灰": {
                'nav': '#808080',  # 灰色
                'bg': '#F5F5F5',   # 白烟色
                'text': 'black',
                'left_nav': '#A9A9A9'
            }
        }
        
        # 在其他初始化代码前添加闪烁相关的变量
        self.flash_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
        self.draw_flash_colors = ['#4169E1', '#1E90FF', '#00BFFF']
        self.flash_count = 0
        self.max_flashes = 45
        self.max_draw_flashes = 15
        self.audio_play_count = 0
        self.max_audio_plays = 5
        
        # 获取当前主题
        current_theme = self.config.get("theme")
        theme = self.themes[current_theme]
        
        # 修改样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 使用保存的配置样式
        self.style.configure('TFrame', background=theme['bg'])
        self.style.configure('TopNav.TFrame', background=theme['nav'])
        self.style.configure('LeftNav.TFrame', background=theme['left_nav'])
        self.style.configure('TopNav.TButton', background=theme['nav'], foreground=theme['text'])
        self.style.configure('LeftNav.TButton', background=theme['left_nav'], foreground=theme['text'])
        self.style.configure('TButton', background=theme['bg'], foreground=theme['text'])
        self.style.configure('Green.TButton', background='green', foreground='white')
        self.style.configure('Red.TButton', background='red', foreground='white')
        self.style.configure('TLabel', background=theme['bg'], foreground=theme['text'])
        self.style.configure('TCheckbutton', background=theme['bg'], foreground=theme['text'])
        self.style.configure('TCombobox', foreground=theme['text'])
        self.style.configure('TCombobox.field', background=theme['bg'], foreground=theme['text'])
        
        # 配置主窗口背景色
        self.master.configure(bg=theme['bg'])  # 使用 self.master 而不是 master
        
        # 添加异步窗口的样式
        self.style.configure('Theme.TFrame', background=theme['bg'])
        self.style.configure('Theme.TLabel', 
                            background=theme['bg'],
                            foreground=theme['text'],
                            font=("Arial", 36))
        
        # 为闪烁效果创建新的样式
        for color in self.flash_colors + self.draw_flash_colors:
            self.style.configure(f'Flash{color}.TFrame', background=color)

    def create_top_navbar(self):
        navbar = ttk.Frame(self.main_frame, style='TopNav.TFrame', height=50)
        navbar.pack(side=tk.TOP, fill=tk.X)
        navbar.pack_propagate(False)

        # 创建左侧按钮框架，用于平分空间的按钮
        left_buttons_frame = ttk.Frame(navbar, style='TopNav.TFrame')
        left_buttons_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 添加平分空间的按钮
        main_buttons = [
            ("计时器", self.show_forward_timer),
            ("计算", self.show_calculator),
            ("元素周期表", self.show_periodic_table),
            ("随机抽签", self.show_random_draw),
            ("化学常数", self.show_chemical_constants)
        ]

        for text, command in main_buttons:
            ttk.Button(left_buttons_frame, text=text, command=command, style='TopNav.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 创建右侧控制按钮框架
        control_frame = ttk.Frame(navbar, style='TopNav.TFrame')
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 添加置顶按钮（修改这里）
        self.topmost_button = ttk.Button(
            control_frame, 
            text="📌", 
            command=self.toggle_topmost, 
            style='Active.TopNav.TButton',  # 默认使用活样式
            width=2
        )
        self.topmost_button.pack(side=tk.LEFT, padx=(0, 2))

        # 设置和最小化按钮
        ttk.Button(control_frame, text="⚙", command=self.show_settings, style='TopNav.TButton', width=2).pack(side=tk.LEFT, padx=(0, 2))
        self.hide_button = ttk.Button(control_frame, text="−", command=self.toggle_visibility, style='Hide.TButton', width=2)
        self.hide_button.pack(side=tk.LEFT, padx=(0, 2))

    def toggle_topmost(self):
        """切换窗口置顶状态"""
        current_state = self.master.attributes('-topmost')
        new_state = not current_state
        self.master.attributes('-topmost', new_state)
        
        # 更新按钮样式以显示当前状态
        if new_state:
            self.topmost_button.configure(style='Active.TopNav.TButton')  # 使用激活样式
        else:
            self.topmost_button.configure(style='TopNav.TButton')  # 恢复默认样式

    def create_left_navbar(self):
        self.left_navbar = ttk.Frame(self.main_frame, width=50, style='LeftNav.TFrame')
        self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)

        self.timer_buttons = ttk.Frame(self.left_navbar, style='TimerNav.TFrame')
        self.timer_buttons.pack(fill=tk.BOTH, expand=True)

        # 修改按钮样式，增大字体大小
        self.style.configure('TimerNav.TButton', 
                            font=('Arial', 16),  # 将字体从14增大到16
                            padding=5,
                            width=5)

        # 创建计时按钮
        self.forward_timer_button = ttk.Button(self.timer_buttons, 
                                             text="正\n计\n时", 
                                             command=self.show_forward_timer, 
                                             style='TimerNav.TButton')
        self.forward_timer_button.pack(fill=tk.BOTH, expand=True)

        # 创建倒计时按钮
        self.countdown_timer_button = ttk.Button(self.timer_buttons, 
                                                   text="倒\n计\n时", 
                                                   command=self.show_countdown_timer, 
                                                   style='TimerNav.TButton')
        self.countdown_timer_button.pack(fill=tk.BOTH, expand=True)

        # 使用after来确保窗口更新
        self.master.after(10, self.adjust_button_heights)

    def adjust_button_heights(self):
        # 获取左侧导栏的高度
        nav_height = self.left_navbar.winfo_height()

        # 设置每个按高度为航栏高的一半
        button_height = nav_height // 2

        # 调整按钮的高度
        self.forward_timer_button.configure(style='TimerNav.TButton')
        self.countdown_timer_button.configure(style='TimerNav.TButton')

        # 创建更新样
        self.style.configure('TimerNav.TButton', padding=(5, button_height//2))

    def create_main_content(self):
        self.main_content = ttk.Frame(self.main_frame)
        self.main_content.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=10, pady=10)

        # 创建所有框架
        self.forward_timer_frame = self.create_forward_timer_frame()
        self.countdown_timer_frame = self.create_countdown_timer_frame()
        self.calculator_frame = self.create_calculator_frame()
        self.periodic_table_frame = self.create_periodic_table_frame()
        self.chemical_constants_frame = self.create_chemical_constants_frame()
        self.settings_frame = self.create_settings_frame()
        
        # 初始隐藏所有框架
        if self.forward_timer_frame:
            self.forward_timer_frame.pack_forget()
        if self.countdown_timer_frame:
            self.countdown_timer_frame.pack_forget()
        if self.calculator_frame:
            self.calculator_frame.pack_forget()
        if self.periodic_table_frame:
            self.periodic_table_frame.pack_forget()
        if self.chemical_constants_frame:
            self.chemical_constants_frame.pack_forget()
        if self.settings_frame:
            self.settings_frame.pack_forget()

        self.show_forward_timer()

    def create_forward_timer_frame(self):
        frame = ttk.Frame(self.main_content)
        
        # 创一个框架来容两个计时器
        timers_frame = ttk.Frame(frame)
        timers_frame.pack(expand=True, fill=tk.BOTH)

        # 一组计时
        timer1_frame = ttk.Frame(timers_frame)
        timer1_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH, pady=(0, 10))  # 加入底部间距
        
        self.time_label1 = ttk.Label(timer1_frame, text="00:00.000", font=("Arial", 64))  # 增字体
        self.time_label1.pack(expand=True)

        button_frame1 = ttk.Frame(timer1_frame)
        button_frame1.pack(pady=(0, 10))  # 加底部间距

        self.start_stop_button1 = ttk.Button(button_frame1, text="开始", command=lambda: self.toggle_timer(1), width=10, style='Green.TButton')
        self.start_stop_button1.pack(side=tk.LEFT, padx=5)

        self.reset_button1 = ttk.Button(button_frame1, text="重置", command=lambda: self.reset_timer(1), width=10)
        self.reset_button1.pack(side=tk.LEFT, padx=5)

        # 添加分隔线
        separator = ttk.Separator(timers_frame, orient='horizontal')
        separator.pack(fill='x', pady=10)
        
        # 第二组计时
        timer2_frame = ttk.Frame(timers_frame)
        timer2_frame.pack(side=tk.BOTTOM, expand=True, fill=tk.BOTH, pady=(10, 0))  # 增加顶间距
        
        self.time_label2 = ttk.Label(timer2_frame, text="00:00.000", font=("Arial", 64))
        self.time_label2.pack(expand=True)

        button_frame2 = ttk.Frame(timer2_frame)
        button_frame2.pack(pady=(10, 0))  # 增加顶部间距

        self.start_stop_button2 = ttk.Button(button_frame2, text="开始", command=lambda: self.toggle_timer(2), width=10, style='Green.TButton')
        self.start_stop_button2.pack(side=tk.LEFT, padx=5)

        self.reset_button2 = ttk.Button(button_frame2, text="重置", command=lambda: self.reset_timer(2), width=10)
        self.reset_button2.pack(side=tk.LEFT, padx=5)

        return frame

    def create_countdown_timer_frame(self):
        frame = ttk.Frame(self.main_content)

        # 创建滚动选器
        selector_frame = ttk.Frame(frame)
        selector_frame.pack(pady=(20, 10))  # 增加顶部间距

        self.minute_spinner = ScrollableSpinbox(selector_frame)
        self.minute_spinner.pack(side=tk.LEFT, padx=2)

        ttk.Label(selector_frame, text=":", font=("Arial", 36)).pack(side=tk.LEFT)

        self.second_spinner = ScrollableSpinbox(selector_frame)
        self.second_spinner.pack(side=tk.LEFT, padx=2)

        # 创建倒计时标签
        self.countdown_label = ttk.Label(frame, text="00:00", font=("Arial", 88))  # 增大字体
        self.countdown_label.pack(pady=20)

        # 创建控制按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        self.start_stop_countdown_button = ttk.Button(button_frame, text="开始", command=self.toggle_countdown, width=10, style='Green.TButton')
        self.start_stop_countdown_button.pack(side=tk.LEFT, padx=5)

        self.reset_countdown_button = ttk.Button(button_frame, text="重置", command=self.reset_countdown, width=10)
        self.reset_countdown_button.pack(side=tk.LEFT, padx=5)

        # 设按和累加关
        preset_frame = ttk.Frame(frame)
        preset_frame.pack(pady=20)

        # 添加累加开关
        self.accumulate_var = tk.BooleanVar()
        accumulate_switch = ttk.Checkbutton(preset_frame, text="累加", variable=self.accumulate_var, style='TCheckbutton')
        accumulate_switch.pack(side=tk.LEFT, padx=(0, 20))  # 增右间距

        presets = [("10秒", 10), ("30秒", 30), ("1分钟", 60), ("2分钟", 120)]
        for text, seconds in presets:
            ttk.Button(preset_frame, text=text, command=lambda s=seconds: self.set_preset(s), width=8).pack(side=tk.LEFT, padx=5)

        return frame

    def create_calculator_frame(self):
        frame = ttk.Frame(self.main_content)

        # 创建计算器示
        self.calc_display = ttk.Entry(frame, font=("Arial", 32), justify=tk.RIGHT)
        self.calc_display.pack(pady=10, padx=10, fill=tk.X)

        # 创建按钮框
        button_frame = ttk.Frame(frame)
        button_frame.pack(expand=True, fill=tk.BOTH)

        # 定义按钮及其样式
        buttons = [
            ('7', 'CalcNum'), ('8', 'CalcNum'), ('9', 'CalcNum'), ('/', 'CalcOp'), ('C', 'CalcClear'), ('sin', 'CalcFunc'),
            ('4', 'CalcNum'), ('5', 'CalcNum'), ('6', 'CalcNum'), ('*', 'CalcOp'), ('(', 'CalcOp'), ('cos', 'CalcFunc'),
            ('1', 'CalcNum'), ('2', 'CalcNum'), ('3', 'CalcNum'), ('-', 'CalcOp'), (')', 'CalcOp'), ('tan', 'CalcFunc'),
            ('0', 'CalcNum'), ('.', 'CalcNum'), ('=', 'CalcOp'), ('+', 'CalcOp'), ('^', 'CalcOp'), ('sqrt', 'CalcFunc'),
            ('π', 'CalcFunc'), ('e', 'CalcFunc'), ('log', 'CalcFunc'), ('ln', 'CalcFunc'), ('abs', 'CalcFunc'), ('mod', 'CalcOp')
        ]

        for i, (button, style) in enumerate(buttons):
            cmd = lambda x=button: self.click_button(x)
            btn = ttk.Button(button_frame, text=button, command=cmd, style=f'{style}.TButton')
            btn.grid(row=i//6, column=i%6, sticky='nsew', padx=1, pady=1)

        for i in range(5):
            button_frame.grid_rowconfigure(i, weight=1)
        for i in range(6):
            button_frame.grid_columnconfigure(i, weight=1)

        return frame

    def click_button(self, key):
        if key == '=':
            try:
                result = self.evaluate_expression(self.calc_display.get())
                self.calc_display.delete(0, tk.END)
                self.calc_display.insert(tk.END, str(result))
            except:
                self.calc_display.delete(0, tk.END)
                self.calc_display.insert(tk.END, "Error")
        elif key == 'C':
            self.calc_display.delete(0, tk.END)
        elif key in ['sin', 'cos', 'tan', 'sqrt', 'log', 'ln', 'abs']:
            self.calc_display.insert(tk.END, key + '(')
        elif key == 'π':
            self.calc_display.insert(tk.END, 'pi')
        elif key == 'e':
            self.calc_display.insert(tk.END, 'e')
        elif key == 'mod':
            self.calc_display.insert(tk.END, '%')
        else:
            self.calc_display.insert(tk.END, key)

    def evaluate_expression(self, expression):
        import math
        # 替换特殊符
        expression = expression.replace('^', '**').replace('π', 'math.pi').replace('e', 'math.e')
        # 添加 math. 前缀数学函数
        for func in ['sin', 'cos', 'tan', 'sqrt', 'log', 'ln', 'abs']:
            expression = expression.replace(func, f'math.{func}')
        expression = expression.replace('ln', 'log')
        return eval(expression)

    def show_calculator(self):
        self.clear_main_content()
        
        # 确保左侧导航栏可见
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
            
            # 隐藏其他航元
            self.timer_buttons.pack_forget()
            if hasattr(self, 'record_frame'):
                self.record_frame.pack_forget()
    
        # 显示计算器架
        self.calculator_frame.pack(expand=True, fill=tk.BOTH)

    def create_periodic_table_frame(self):
        # 创建在main_content中而不是master中
        frame = ttk.Frame(self.main_content)
        self.periodic_table_label = ttk.Label(frame)
        self.periodic_table_label.pack(expand=True, fill=tk.BOTH)
        return frame

    def show_periodic_table(self):
        self.clear_main_content()
        
        # 隐藏左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack_forget()
        
        # 隐藏所有子列表
        self.timer_buttons.pack_forget()
        self.record_frame.pack_forget() if hasattr(self, 'record_frame') else None
        
        # pack而不是place来显示周期表框架，设fill=tk.BOTH和expand=True
        self.periodic_table_frame.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
        self.load_periodic_table()
        
        # 提升显示先级
        self.periodic_table_frame.lift()
        self.periodic_table_label.lift()

    def load_periodic_table(self):
        try:
            # 保存原始图片以供调整大小使用
            self.original_image = Image.open("元素周期表.png")
            # 初次加载时调整图大小
            self.resize_periodic_table()
            # 确保素周期表始终显示在最上层
            self.periodic_table_label.lift()
        except FileNotFoundError:
            self.periodic_table_label.config(text="未找到元素周期表图片")
        except Exception as e:
            self.periodic_table_label.config(text=f"加载图片时发生错误: {e}")

    def show_forward_timer(self):
        self.clear_main_content()
        self.forward_timer_frame.pack(expand=True, fill=tk.BOTH)
        self.timer_buttons.pack(fill=tk.BOTH, expand=True)  # 显示计时子导航栏

    def show_countdown_timer(self):
        self.clear_main_content()
        self.countdown_timer_frame.pack(expand=True, fill=tk.BOTH)
        self.timer_buttons.pack(fill=tk.BOTH, expand=True)  # 显示计时器子导航栏

    def toggle_timer(self, timer_id):
        if timer_id == 1:
            if self.time_running1:
                self.stop_timer(1)
                self.start_stop_button1.config(text="开始", style='Green.TButton')
            else:
                self.start_timer(1)
                self.start_stop_button1.config(text="停止", style='Red.TButton')
        elif timer_id == 2:
            if self.time_running2:
                self.stop_timer(2)
                self.start_stop_button2.config(text="开始", style='Green.TButton')
            else:
                self.start_timer(2)
                self.start_stop_button2.config(text="停止", style='Red.TButton')

    def start_timer(self, timer_id):
        if timer_id == 1:
            self.start_time1 = time.time() - self.time_count1
            self.time_running1 = True
            self.update_timer(1)
        elif timer_id == 2:
            self.start_time2 = time.time() - self.time_count2
            self.time_running2 = True
            self.update_timer(2)

    def update_timer(self, timer_id):
        if timer_id == 1 and self.time_running1:
            self.time_count1 = time.time() - self.start_time1
            minutes = int(self.time_count1 // 60)
            seconds = int(self.time_count1 % 60)
            # 修改这里,将毫秒算改为正确方式
            milliseconds = int((self.time_count1 * 1000) % 1000)
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.time_label1.config(text=time_str)
            self.master.after(50, lambda: self.update_timer(1))
        elif timer_id == 2 and self.time_running2:
            self.time_count2 = time.time() - self.start_time2
            minutes = int(self.time_count2 // 60)
            seconds = int(self.time_count2 % 60)
            # 同样修改这里的毫秒计算
            milliseconds = int((self.time_count2 * 1000) % 1000)
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.time_label2.config(text=time_str)
            self.master.after(50, lambda: self.update_timer(2))

    def stop_timer(self, timer_id):
        if timer_id == 1:
            self.time_running1 = False
        elif timer_id == 2:
            self.time_running2 = False

    def reset_timer(self, timer_id):
        if timer_id == 1:
            self.stop_timer(1)
            self.time_count1 = 0
            self.time_label1.config(text="00:00.000")
            self.start_stop_button1.config(text="开始", style='Green.TButton')
        elif timer_id == 2:
            self.stop_timer(2)
            self.time_count2 = 0
            self.time_label2.config(text="00:00.000")
            self.start_stop_button2.config(text="开始", style='Green.TButton')

    def toggle_countdown(self):
        if hasattr(self, 'countdown_running') and self.countdown_running:
            self.stop_countdown()
            self.start_stop_countdown_button.config(text="开始", style='Green.TButton')
        else:
            self.start_countdown()
            self.start_stop_countdown_button.config(text="停止", style='Red.TButton')

    def start_countdown(self):
        try:
            minutes = int(self.minute_spinner.get() or 0)
            seconds = int(self.second_spinner.get() or 0)
            self.countdown_time = minutes * 60 + seconds
            if self.countdown_time > 0:
                self.countdown_running = True
                self.update_countdown()
            else:
                self.countdown_label.config(text="请设置时间")
        except ValueError:
            self.countdown_label.config(text="无效输入")

    def stop_countdown(self):
        self.countdown_running = False
        if hasattr(self, 'countdown_after_id'):
            self.master.after_cancel(self.countdown_after_id)

    def reset_countdown(self):
        self.stop_countdown()
        self.minute_spinner.set("00")
        self.second_spinner.set("00")
        self.countdown_label.config(text="00:00")
        self.start_stop_countdown_button.config(text="开始", style='Green.TButton')

    def update_countdown(self):
        if self.countdown_running and self.countdown_time > 0:
            minutes, seconds = divmod(self.countdown_time, 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            self.countdown_label.config(text=time_str)
            self.countdown_time -= 1
            self.countdown_after_id = self.master.after(1000, self.update_countdown)
        elif self.countdown_running and self.countdown_time <= 0:
            self.countdown_label.config(text="时间到！")
            self.countdown_running = False
            self.start_stop_countdown_button.config(text="开始", style='Green.TButton')
            
            # 重置音频播放计数
            self.audio_play_count = 0
            # 开播放声音
            self.play_countdown_alarm()
            
            self.start_flashing()
            
            # 创建倒计时标签
            self.hide_countdown = ttk.Label(
                self.countdown_timer_frame, 
                text=f"{self.config.get('hide_delay'):.1f}", 
                font=("Arial", 24, "bold"),
                foreground='#FF4500'
            )
            self.hide_countdown.place(relx=1.0, rely=0, x=-20, y=20, anchor="ne")
            
            # 如果设置了始终自动藏，则开始倒计并在结束时隐藏窗口
            if self.config.get("always_auto_hide"):
                self.start_hide_countdown()

    def play_countdown_alarm(self):
        """倒计时结束时播放声"""
        try:
            if self.config.get("sound_enabled") and self.audio_play_count < 5:  # 限播放5次
                winsound.PlaySound("time.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.audio_play_count += 1
                # 1.5秒后再次播放
                self.master.after(1100, self.play_countdown_alarm)
        except Exception as e:
            print(f"无法播放声音文件: {e}")

    def start_flashing(self):
        self.flash_count = 0
        self.flash_window()

    def flash_window(self):
        if self.flash_count < self.max_flashes:
            color = self.flash_colors[self.flash_count % len(self.flash_colors)]
            self.master.configure(background=color)
            for widget in self.master.winfo_children():
                if isinstance(widget, ttk.Frame):
                    widget.configure(style=f'Flash{color}.TFrame')
            self.flash_count += 1
            self.master.after(100, self.stop_flashing)  # 少闪烁间隔到100毫秒
        else:
            self.reset_window_color()

    def stop_flashing(self):
        self.reset_window_color()
        self.master.after(100, self.flash_window)  # 减少闪烁隔100毫秒

    def reset_window_color(self):
        self.master.configure(background='#F0F0F0')
        for widget in self.master.winfo_children():
            if isinstance(widget, ttk.Frame):
                widget.configure(style='TFrame')

    def set_preset(self, seconds):
        current_minutes = int(self.minute_spinner.get() or 0)
        current_seconds = int(self.second_spinner.get() or 0)
        current_total_seconds = current_minutes * 60 + current_seconds

        if self.accumulate_var.get():
            # 果累加开关打开，则累加时间
            new_total_seconds = current_total_seconds + seconds
        else:
            # 如果累开关关闭，则直接设置为预设时间
            new_total_seconds = seconds

        new_minutes, new_seconds = divmod(new_total_seconds, 60)
        self.minute_spinner.set(f"{new_minutes:02d}")
        self.second_spinner.set(f"{new_seconds:02d}")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.master.winfo_x() + deltax
            y = self.master.winfo_y() + deltay
            
            # 确保主口不会移出屏
            x = max(0, min(x, self.screen_width - self.master.winfo_width()))
            y = max(0, min(y, self.screen_height - self.master.winfo_height()))
            
            self.master.geometry(f"+{x}+{y}")
            
            # 据窗口更新位置
            if x < self.screen_width * 0.2:  # 当主口位于屏幕左侧20%域时
                self.floating_ball.geometry(f"+{x+self.master.winfo_width()}+{y}")
            else:
                self.floating_ball.geometry(f"+{x-self.floating_ball.winfo_width()}+{y}")
            
            # 印位置
            self.update_watermark_position()

    def toggle_visibility(self):
        if self.visible:
            self.master.withdraw()
            self.visible = False
        else:
            self.master.deiconify()
            self.visible = True
        
        # 确保浮球始终可见
        self.floating_ball.lift()
        
        # 更新隐藏按钮的文本
        self.update_hide_button_text()

    def move_main_window(self, x, y):
        # 确保主窗口会移出幕
        x = max(0, min(x, self.screen_width - self.master.winfo_width()))
        y = max(0, min(y, self.screen_height - self.master.winfo_height()))
        
        self.master.geometry(f"+{x}+{y}")
        
        # 新水印位置
        self.update_watermark_position()

    # 添加新方法来更新隐藏按钮的文本
    def update_hide_button_text(self):
        self.hide_button.config(text="□" if not self.visible else "−")  # 用方框符号表示"显示"

    # 添加以下方法到 ChemistryTimer 类：
    def update_current_time(self):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.current_time_label:
            self.current_time_label.config(text=current_time)
        self.master.after(1000, self.update_current_time)

    def on_closing(self):
        if not self.tray_created:  # 只有在系统托盘未创建时才创建
            self.master.withdraw()  # 隐藏主窗口
            self.floating_ball.withdraw()  # 隐藏浮球
            self.create_system_tray()
        else:
            # 如果系统托盘已存在，只隐藏窗口
            self.master.withdraw()
            self.floating_ball.withdraw()

    def create_system_tray(self):
        """创建系统托盘图标"""
        if self.tray_created:
            return
        
        try:
            # 获取图标路径
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            
            # 尝试加载图标
            icon_path = None
            for icon_file in ["icon.ico", "icon.png", "化学计时器.png"]:
                temp_path = os.path.join(base_path, icon_file)
                if os.path.exists(temp_path):
                    icon_path = temp_path
                    break
            
            if icon_path is None:
                raise FileNotFoundError("未找到任何可用的图标文件")
            
            # 加载并处理图标
            image = Image.open(icon_path)
            if not icon_path.endswith('.ico'):
                image = image.resize((32, 32), Image.LANCZOS)
            
            # 停止现有的图标（如果存在）
            if self.icon:
                try:
                    self.icon.stop()
                except:
                    pass
                self.icon = None
            
            # 创建新的托盘图标
            self.icon = pystray.Icon(
                name="化学计时器",
                icon=image,
                title="化学计时器",
                menu=pystray.Menu(
                    pystray.MenuItem(
                        "显示/隐藏",
                        lambda: self.master.after(0, self.toggle_window),
                        default=True
                    ),
                    pystray.MenuItem(
                        "退出",
                        lambda: self.master.after(0, self.quit_window)
                    )
                )
            )
            
            # 使用守护线程运行图标
            threading.Thread(
                target=self.icon.run,
                daemon=True,
                name="SystemTrayThread"
            ).start()
            
            self.tray_created = True
            
        except Exception as e:
            self.tray_created = False
            Logger.error(f"创建统托盘图标失败: {e}")
            messagebox.showerror("错误", f"创建系统托盘图标失败:\n{str(e)}")

    def toggle_window(self):
        """切换窗口显示状态"""
        if self.master.state() == 'withdrawn':
            self.master.deiconify()
            self.floating_ball.deiconify()
            self.visible = True
        else:
            self.master.withdraw()
            self.floating_ball.withdraw()
            self.visible = False
        self.update_hide_button_text()

    def quit_window(self):
        """退出程序"""
        try:
            # 注销热键
            keyboard.unhook_all()
            
            # 停止系统托盘图标
            if self.icon:
                try:
                    self.icon.stop()
                except:
                    pass
                self.icon = None
                self.tray_created = False
            
            # 退出程序
            self.master.quit()
            
        except Exception as e:
            Logger.error(f"退出程序时发生错误: {e}")
            self.master.quit()

    def create_watermark(self):
        watermark_text = "钱高化学组×27届高一三班"
        self.watermark = tk.Label(self.master, 
                                   text=watermark_text,
                                   fg='#A0A0A0',  # 灰色文
                                   font=('Arial', 10),
                                   bg=self.themes[self.config.get("theme")]['bg'])  # 背景色与主窗口一致
        self.watermark.pack(side=tk.BOTTOM, anchor=tk.SE, padx=10, pady=10)

    def update_watermark_position(self):
        # 确保水印终在右下角
        self.master.update_idletasks()
        watermark = self.master.children['!label']
        watermark.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

    def hide_main_window(self):
        """隐藏主窗口"""
        try:
            # 确保倒计时标签销毁
            if hasattr(self, 'hide_countdown'):
                self.hide_countdown.destroy()
                delattr(self, 'hide_countdown')
            
            # 隐藏主窗口
            if self.visible:
                self.master.withdraw()
                self.visible = False
                self.update_hide_button_text()
            
        except Exception as e:
            print(f"销毁倒计时标签出错: {e}")

    # 添加新方法理"随机抽签"按钮点击事件
    def show_random_draw(self):
        self.clear_main_content()
        self.timer_buttons.pack_forget()
        
        # 创建主抽签区域
        self.random_draw_frame = ttk.Frame(self.main_content)
        self.random_draw_frame.pack(expand=True, fill=tk.BOTH)
        
        # 获取有txt件
        txt_files = self.get_txt_files()
        
        if not txt_files:
            # 创建提示框架
            hint_frame = ttk.Frame(self.random_draw_frame)
            hint_frame.pack(expand=True)
            
            # 提示标签
            ttk.Label(hint_frame, 
                     text="未找到名单文件!\n请在程序目录下创建'.txt'文件,\n每行输入个学生姓名,\n并添加文件后重新启动程序!", 
                     font=("Arial", 14),
                     justify=tk.CENTER).pack(pady=20)
              
            # 打开目录按钮
            ttk.Button(hint_frame, 
                      text="打开程序目录", 
                      command=self.open_program_directory).pack(pady=10)
            return

        # 创重置按钮（如果还没有创建）
        if not hasattr(self, 'reset_records_button'):
            self.reset_records_button = ttk.Button(self.left_navbar, 
                                                 text="重置抽取记录", 
                                                 command=self.reset_records,
                                                 width=12)
        # 显示重置按钮
        self.reset_records_button.pack(side=tk.TOP, pady=5)

        # 创建文件选择框架
        select_frame = ttk.Frame(self.random_draw_frame)
        select_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(select_frame, text="选择名单：", font=('Arial', 12)).pack(side=tk.LEFT)
        
        # 使用次选择的文件，如果没有则使用第一个
        initial_file = self.last_selected_file if self.last_selected_file in txt_files else txt_files[0]
        
        # 创建下拉选择框
        self.file_var = tk.StringVar(value=initial_file)
        file_combo = ttk.Combobox(select_frame, 
                                 textvariable=self.file_var,
                                 values=txt_files,
                                 state='readonly',
                                 width=30)
        file_combo.pack(side=tk.LEFT, padx=5)
        
        # 修文选择的响应
        def on_file_changed(event):
            selected_file = self.file_var.get()
            # 保存选择的文件
            self.last_selected_file = selected_file
            
            if not hasattr(self, 'file_records'):
                self.file_records = {}
            
            # 如果是新文初始化其记录
            if selected_file not in self.file_records:
                self.file_records[selected_file] = {}
                # 读取文件并初始化记录
                try:
                    program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
                    file_path = os.path.join(program_dir, selected_file)
                    with open(file_path, "r", encoding="utf-8") as file:
                        self.students = file.read().strip().split("\n")
                        for student in self.students:
                            self.file_records[selected_file][student] = 0
                except Exception as e:
                    print(f"初始化记录失败: {e}")
            
            # 更新当前录引用
            self.student_records = self.file_records[selected_file]
            # 立即更新显示
            self.update_record_display()
            # 重置显示文本
            if hasattr(self, 'draw_display'):
                self.draw_display.config(text="等待抽签...")
        
        file_combo.bind('<<ComboboxSelected>>', on_file_changed)
        
        # 初化显示当前择的文件记录
        on_file_changed(None)  # 手动触发次新
        
        # 创建抽签界面
        self.create_draw_interface()

    def get_txt_files(self):
        """获取程序目录下的所有txt文件"""
        program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        txt_files = [f for f in os.listdir(program_dir) if f.endswith('.txt')]
        return txt_files

    def start_draw(self, count, force=False, auto_hide=False):
        # 添加 auto_hide 参数传递给 update_draw
        # 检查是否正抽取，除是强制抽取
        if (hasattr(self, 'is_drawing') and self.is_drawing) and not force:
            return
        
        try:
            # 设置抽取状态
            self.is_drawing = True
            # 禁用抽取按钮
            if hasattr(self, 'draw_one_button'):
                self.draw_one_button.configure(state='disabled')
            if hasattr(self, 'draw_two_button'):
                self.draw_two_button.configure(state='disabled')
            
            # 选择的文件
            selected_file = self.file_var.get()
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            file_path = os.path.join(program_dir, selected_file)
            
            # 为每个文件创建独立的记录字典
            if not hasattr(self, 'file_records'):
                self.file_records = {}
            
            # 果是新文件，初始化其记录
            if selected_file not in self.file_records:
                self.file_records[selected_file] = {}
            
            # 使用当前文件的记录
            self.student_records = self.file_records[selected_file]
            
            with open(file_path, "r", encoding="utf-8") as file:
                self.students = file.read().strip().split("\n")
                # 初始化未记录学生
                for student in self.students:
                    if student not in self.student_records:
                        self.student_records[student] = 0
                
                if len(self.students) < count:
                    self.draw_display.config(text="名单中学生数量不足")
                else:
                    self.progress['maximum'] = 100
                    self.progress['value'] = 0
                    self.draw_display.config(text="抽取中...")
                    # 传递 auto_hide 参数
                    self.update_draw(count, auto_hide=auto_hide)
        except FileNotFoundError:
            self.draw_display.config(text="未找到所选名单文件")
        except Exception as e:
            self.draw_display.config(text=f"发生错误: {e}")
            # 发生错误时也要置状态
            self.is_drawing = False
            if hasattr(self, 'draw_one_button'):
                self.draw_one_button.configure(state='normal')
            if hasattr(self, 'draw_two_button'):
                self.draw_two_button.configure(state='normal')

    def update_draw(self, count, step=0, auto_hide=False):
        if step < 100:
            # 根据权重随机显示名字
            weights = self.calculate_weights()
            random_name = random.choices(self.students, weights=weights, k=1)[0]
            
            self.draw_display.config(text=random_name)
            self.progress['value'] = step
            
            # 使用配置的速
            speed = self.config.get("draw_speed")
            self.master.after(50, lambda: self.update_draw(count, step + speed, auto_hide))
        else:
            # 最终抽取结果处理
            weights = self.calculate_weights()
            if count == 1:
                selected_students = [random.choices(self.students, weights=weights, k=1)[0]]  # 修改这里，使用列表包装
            else:
                # 抽取不同的学生
                selected_students = []
                remaining_students = self.students.copy()
                remaining_weights = weights.copy()
                
                for _ in range(count):
                    if not remaining_students:  # 如果没有余学生可选
                        break
                    
                    # 抽取一名学生
                    selected_idx = random.choices(range(len(remaining_students)), 
                                       weights=remaining_weights, k=1)[0]
                    selected_student = remaining_students.pop(selected_idx)
                    remaining_weights.pop(selected_idx)  # 同时移除对应的权重
                    selected_students.append(selected_student)
            
            # 更新记录和显示
            for student in selected_students:
                self.student_records[student] = self.student_records.get(student, 0) + 1
            
            # 新显示（修改这里，使用空格分隔）
            self.draw_display.config(text=" ".join(selected_students))
            self.progress['value'] = 100
            
            # 更新记录
            selected_file = self.file_var.get()
            self.file_records[selected_file] = self.student_records
            
            # 更新记显示
            if hasattr(self, 'record_text'):
                self.record_text.config(state='normal')
                self.update_record_display()
                self.record_text.config(state='disabled')
                
                # 强制刷新界面
                self.record_text.update()
                self.master.update_idletasks()
            
            # 重置状态并启用按钮
            self.is_drawing = False
            if hasattr(self, 'draw_one_button'):
                self.draw_one_button.configure(state='normal')
            if hasattr(self, 'draw_two_button'):
                self.draw_two_button.configure(state='normal')
            
            # 添闪效果（使用门的抽签闪烁方法）
            self.flash_count = 0
            self.flash_draw_window()
            
            # 如果声音已启用，播放系统提示音
            if self.config.get("sound_enabled"):
                try:
                    # 使用异步方式播放系统提示音
                    winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except Exception as e:
                    print(f"无法播放系统提示音: {e}")
            
            # 如果是通过快捷键触的抽签，2秒后自隐藏窗口
            if auto_hide:
                # 创建倒计时标签
                self.hide_countdown = ttk.Label(
                    self.random_draw_frame, 
                    text="2.0", 
                    font=("Arial", 24, "bold"),
                    foreground='#FF4500'
                )
                self.hide_countdown.place(relx=1.0, rely=0, x=-20, y=20, anchor="ne")
                
                # 开始倒计时并在结束时隐藏窗口
                self.start_hide_countdown(2000)

    def start_hide_countdown(self, duration=None):
        """开始倒计时并在结束时隐藏窗口"""
        if duration is None:
            # 使用配的隐藏时间
            duration = self.config.get("hide_delay") * 1000
            
        start_time = time.time()
        
        def update():
            current_time = time.time()
            elapsed = int((current_time - start_time) * 1000)
            remaining = max(0, duration - elapsed)
            
            if remaining > 0:
                # 更新显示文本（保留一位小数）
                if hasattr(self, 'hide_countdown'):
                    self.hide_countdown.config(text=f"{remaining/1000:.1f}")
                    # 继续更新
                    self.master.after(16, update)
            else:
                # 时间到，藏窗口
                self.hide_main_window()
        
        # 开始更新循环
        update()

    def calculate_weights(self):
        """计算每个学生抽取权重"""
        # 获取最小和最大抽取次数
        min_count = min(self.student_records.values())
        max_count = max(self.student_records.values())
        
        weights = []
        for student in self.students:
            count = self.student_records.get(student, 0)
            if count > min_count:
                # 如果该学生的抽取次数高于最小值，给予极低的权重
                weight = 0.01
            else:
                # 如果学生的抽取次数等于最值，给予正常权重
                weight = 1.0
            weights.append(weight)
        
        # 如果所有重都是0.01（即所有人抽取次数相同）置为相等权重
        if all(w == 0.01 for w in weights):
            weights = [1.0] * len(weights)
        
        return weights

    def update_record_display(self):
        if hasattr(self, 'record_text'):
            self.record_text.config(state='normal')  # 启用编辑
            self.record_text.delete(1.0, tk.END)
            # 按被抽取次数排序
            sorted_records = sorted(self.student_records.items(), key=lambda x: (-x[1], x[0]))
            
            # 显示每个学生的抽取次数
            for student, count in sorted_records:
                # 使用不同的颜色标记不同的抽取数
                if count == 0:
                    color = '#FFFFFF'  # 灰色，表示未被抽取
                elif count == 1:
                    color = '#FFD700'  # 金色，表示抽取1次
                elif count == 2:
                    color = '#FFD700'  # 金色，表示抽取2次
                else:
                    color = '#FF4500'  # 红橙色，表示抽取3次及以上
                
                # 插入生字和抽取次数，并设置颜色
                self.record_text.insert(tk.END, f"{student}: {count}\n")
                # 获取插入文本的位置
                last_line_start = self.record_text.get("end-2c linestart", "end-1c")
                # 为这一行设置标签
                self.record_text.tag_add(f"color_{count}", 
                                       f"end-{len(last_line_start)+1}c linestart",
                                       "end-1c")
                self.record_text.tag_config(f"color_{count}", foreground=color)
            
            # 禁用文本编
            self.record_text.config(state='disabled')
            
            # 强制刷新界面
            self.record_text.update()
            self.master.update_idletasks()

    def clear_main_content(self):
        # 隐藏所有导航元素
        if hasattr(self, 'record_frame'):
            self.record_frame.pack_forget()
        if hasattr(self, 'reset_records_button'):
            self.reset_records_button.pack_forget()
        
        # 隐藏所有其他框架
        if hasattr(self, 'periodic_table_frame'):
            self.periodic_table_frame.pack_forget()
        if hasattr(self, 'chemical_constants_frame'):
            self.chemical_constants_frame.pack_forget()
        
        # 恢复主框架和左侧航栏示
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        
        # 隐藏其他框架
        if hasattr(self, 'forward_timer_frame'):
            self.forward_timer_frame.pack_forget()
        if hasattr(self, 'countdown_timer_frame'):
            self.countdown_timer_frame.pack_forget()
        if hasattr(self, 'calculator_frame'):
            self.calculator_frame.pack_forget()
        if hasattr(self, 'random_draw_frame'):
            self.random_draw_frame.pack_forget()
        if hasattr(self, 'settings_frame') and self.settings_frame:
            self.settings_frame.pack_forget()

    # 添加新方法
    def minimize_to_tray(self):
        self.master.withdraw()  # 隐藏主窗口
        self.floating_ball.withdraw()  # 隐藏浮球
        self.create_system_tray()  # 创建系统托盘图标

    def get_resource_path(self, relative_path):
        """获取资源文件的绝对路径"""
        try:
            # PyInstaller创建时件夹,路径存储_MEIPASS中
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def show_all_windows(self):
        """显示所有窗口"""
        self.master.deiconify()  # 显示主窗口
        self.floating_ball.deiconify()  # 显示浮球
        self.visible = True
        self.update_hide_button_text()

    def create_settings_frame(self):
        frame = ttk.Frame(self.main_content)
        
        # 建左右分栏局
        left_frame = ttk.Frame(frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)
        
        # 创建一个画布和滚动条
        canvas = tk.Canvas(left_frame, bg=self.themes[self.config.get("theme")]['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置画布
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 添加"设置"标题
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill=tk.X, padx=20, pady=(20, 30))
        ttk.Label(title_frame, text="设置", font=('Arial', 20, 'bold')).pack(anchor=tk.CENTER)
        
        # 1. 窗口透明度设置
        opacity_frame = ttk.Frame(scrollable_frame)
        opacity_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(opacity_frame, text="窗口透明度：", font=('Arial', 12)).pack(side=tk.LEFT)
        
        opacity_control_frame = ttk.Frame(opacity_frame)
        opacity_control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        opacity_scale = ttk.Scale(opacity_control_frame, from_=0.5, to=1.0, orient=tk.HORIZONTAL)
        opacity_scale.set(self.config.get("opacity"))
        opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def reset_opacity():
            opacity_scale.set(0.8)
            self.master.attributes('-alpha', 0.8)
            self.config.set("opacity", 0.8)
        
        ttk.Button(opacity_control_frame, text="恢复默认", command=reset_opacity, width=8).pack(side=tk.LEFT, padx=(10, 0))
        
        def update_opacity(event):
            value = opacity_scale.get()
            self.master.attributes('-alpha', value)
            self.config.set("opacity", value)
        opacity_scale.bind("<ButtonRelease-1>", update_opacity)
        
        # 2. 抽速度设置
        speed_frame = ttk.Frame(scrollable_frame)
        speed_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(speed_frame, text="抽取速度：", font=('Arial', 12)).pack(side=tk.LEFT)
        
        speed_control_frame = ttk.Frame(speed_frame)
        speed_control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        speed_scale = ttk.Scale(speed_control_frame, from_=5.0, to=20.0, orient=tk.HORIZONTAL)
        speed_scale.set(self.config.get("draw_speed"))
        speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def reset_speed():
            speed_scale.set(8.0)
            self.config.set("draw_speed", 8.0)
        
        ttk.Button(speed_control_frame, text="恢复默认", command=reset_speed, width=8).pack(side=tk.LEFT, padx=(10, 0))
        
        def update_speed(event):
            value = speed_scale.get()
            self.config.set("draw_speed", value)
        speed_scale.bind("<ButtonRelease-1>", update_speed)
        
        # 3. 快捷键设置
        hotkey_frame = ttk.Frame(scrollable_frame)
        hotkey_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(hotkey_frame, text="快速抽取快捷键:", font=('Arial', 12)).pack(side=tk.LEFT)
        
        current_hotkey = self.config.get("hotkey")
        self.hotkey_label = ttk.Label(hotkey_frame, text=f"{current_hotkey}", font=('Arial', 12))
        self.hotkey_label.pack(side=tk.LEFT, padx=10)
        
        self.hotkey_button = ttk.Button(hotkey_frame, text="点击设置", command=self.start_hotkey_listen, width=8)
        self.hotkey_button.pack(side=tk.LEFT)
        
        ttk.Button(hotkey_frame, text="恢复默认", command=lambda: self.reset_hotkey("enter"), width=8).pack(side=tk.LEFT, padx=(10, 0))
        
        # 4. 始终允许快速抽设置
        always_draw_frame = ttk.Frame(scrollable_frame)
        always_draw_frame.pack(fill=tk.X, padx=20, pady=10)
        self.always_draw_enabled = tk.BooleanVar(value=self.config.get("always_allow_quick_draw"))
        always_draw_check = ttk.Checkbutton(
            always_draw_frame, 
            text="始终允许快速抽取(不隐藏窗口时也能抽取)",
            variable=self.always_draw_enabled,
            command=lambda: self.config.set("always_allow_quick_draw", self.always_draw_enabled.get()),
            style='TCheckbutton'
        )
        always_draw_check.pack(side=tk.LEFT)
        
        # 5. 用异步抽签设
        async_draw_frame = ttk.Frame(scrollable_frame)
        async_draw_frame.pack(fill=tk.X, padx=20, pady=10)
        self.async_draw_enabled = tk.BooleanVar(value=self.config.get("async_draw"))
        async_draw_check = ttk.Checkbutton(
            async_draw_frame, 
            text="使用异步抽签(使用更快的抽签)", 
            variable=self.async_draw_enabled,
            command=lambda: self.config.set("async_draw", self.async_draw_enabled.get()),
            style='TCheckbutton'
        )
        async_draw_check.pack(side=tk.LEFT)
        
        # 6. 异步抽签动画置
        async_animation_frame = ttk.Frame(scrollable_frame)
        async_animation_frame.pack(fill=tk.X, padx=20, pady=10)
        self.async_animation_enabled = tk.BooleanVar(value=self.config.get("async_draw_animation"))
        async_animation_check = ttk.Checkbutton(
            async_animation_frame, 
            text="异步抽签显示抽取动画", 
            variable=self.async_animation_enabled,
            command=lambda: self.config.set("async_draw_animation", self.async_animation_enabled.get()),
            style='TCheckbutton'
        )
        async_animation_check.pack(side=tk.LEFT)
        
        # 7. 自动隐藏时间设置
        hide_delay_frame = ttk.Frame(scrollable_frame)
        hide_delay_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(hide_delay_frame, text="自动隐藏时间：", font=('Arial', 12)).pack(side=tk.LEFT)
        
        hide_delay_control_frame = ttk.Frame(hide_delay_frame)
        hide_delay_control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        hide_delay_scale = ttk.Scale(hide_delay_control_frame, from_=0.5, to=5.0, orient=tk.HORIZONTAL)
        hide_delay_scale.set(self.config.get("hide_delay"))
        hide_delay_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.hide_delay_label = ttk.Label(hide_delay_control_frame, text=f"{self.config.get('hide_delay'):.1f}秒", width=6)
        self.hide_delay_label.pack(side=tk.LEFT, padx=5)
        
        def reset_hide_delay():
            hide_delay_scale.set(2.0)
            self.hide_delay_label.config(text="2.0秒")
            self.config.set("hide_delay", 2.0)
        
        ttk.Button(hide_delay_control_frame, text="恢复默认", command=reset_hide_delay, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        def update_hide_delay(event):
            raw_value = hide_delay_scale.get()
            value = round(raw_value * 2) / 2
            hide_delay_scale.set(value)
            self.hide_delay_label.config(text=f"{value:.1f}秒")
            self.config.set("hide_delay", value)
            self.enable_window_move()
        
        hide_delay_scale.bind("<ButtonPress-1>", self.disable_window_move)
        hide_delay_scale.bind("<ButtonRelease-1>", update_hide_delay)
        hide_delay_scale.bind("<Motion>", lambda e: self.hide_delay_label.config(text=f"{round(hide_delay_scale.get() * 2) / 2:.1f}秒"))
        
        # 8. 快速抽取始终自动隐藏设置
        always_auto_hide_frame = ttk.Frame(scrollable_frame)
        always_auto_hide_frame.pack(fill=tk.X, padx=20, pady=10)
        self.always_auto_hide_enabled = tk.BooleanVar(value=self.config.get("always_auto_hide"))
        always_auto_hide_check = ttk.Checkbutton(
            always_auto_hide_frame, 
            text="快速抽取始终自动隐藏(无论是否异步抽取)", 
            variable=self.always_auto_hide_enabled,
            command=lambda: self.config.set("always_auto_hide", self.always_auto_hide_enabled.get()),
            style='TCheckbutton'
        )
        always_auto_hide_check.pack(side=tk.LEFT)
        
        # 9. 倒计时声音设置
        sound_frame = ttk.Frame(scrollable_frame)
        sound_frame.pack(fill=tk.X, padx=20, pady=10)
        self.sound_enabled = tk.BooleanVar(value=self.config.get("sound_enabled"))
        sound_check = ttk.Checkbutton(
            sound_frame, 
            text="启用倒计时/抽取结束声音", 
            variable=self.sound_enabled,
            command=lambda: self.config.set("sound_enabled", self.sound_enabled.get()),
            style='TCheckbutton'
        )
        sound_check.pack(side=tk.LEFT)
        
        # 10. 主题切换
        theme_frame = ttk.Frame(scrollable_frame)
        theme_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(theme_frame, text="主选择：", font=('Arial', 12)).pack(side=tk.LEFT)
        theme_var = tk.StringVar(value=self.config.get("theme"))
        theme_combo = ttk.Combobox(
            theme_frame, 
            textvariable=theme_var,
            values=list(self.themes.keys()),
            state='readonly'
        )
        theme_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def update_theme(event):
            selected_theme = theme_var.get()
            self.config.set("theme", selected_theme)
            theme = self.themes[selected_theme]
            
            # 更新基础样式
            self.style.configure('TopNav.TFrame', background=theme['nav'])
            self.style.configure('LeftNav.TFrame', background=theme['left_nav'])
            self.style.configure('TFrame', background=theme['bg'])
            self.style.configure('TopNav.TButton', background=theme['nav'], foreground=theme['text'])
            self.style.configure('LeftNav.TButton', background=theme['left_nav'], foreground=theme['text'])
            
            # 更新计时器导航栏样式
            self.style.configure('TimerNav.TFrame', background=theme['left_nav'])
            self.style.configure('TimerNav.TButton', 
                                background=theme['left_nav'], 
                                foreground=theme['text'],
                                font=('Arial', 16),  # 保持字体大为16
                                padding=5,
                                width=5)
            
            # 更新标签样式
            self.style.configure('TLabel', background=theme['bg'], foreground=theme['text'])
            
            # 更新按钮样式
            self.style.configure('TButton', background=theme['bg'], foreground=theme['text'])
            
            # 更新复选框样式
            self.style.configure('TCheckbutton', background=theme['bg'], foreground=theme['text'])
            
            # 更新下拉样式
            self.style.configure('TCombobox', background=theme['bg'], foreground=theme['text'])
            self.style.configure('TCombobox.field', background=theme['bg'], foreground=theme['text'])
            
            # 更新滚动条样式
            self.style.configure('TScrollbar', background=theme['bg'], troughcolor=theme['bg'])
            
            # 更新分隔线样式
            self.style.configure('TSeparator', background=theme['text'])
            
            # 更新设置页面中的所有标签文字颜色
            for widget in scrollable_frame.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Label):
                            child.configure(style='TLabel')
                        elif isinstance(child, ttk.Checkbutton):
                            child.configure(style='TCheckbutton')
            
            # 新主窗口背景
            self.master.configure(bg=theme['bg'])
            
            # 更新水印背景色和文颜色
            if hasattr(self, 'watermark'):
                self.watermark.configure(bg=theme['bg'], fg=theme['text'])
            
            # 更新计时器标签样式
            if hasattr(self, 'time_label1'):
                self.time_label1.configure(background=theme['bg'], foreground=theme['text'])
            if hasattr(self, 'time_label2'):
                self.time_label2.configure(background=theme['bg'], foreground=theme['text'])
            if hasattr(self, 'countdown_label'):
                self.countdown_label.configure(background=theme['bg'], foreground=theme['text'])
            
            # 更新异步窗口的样式
            self.style.configure('Theme.TLabel',
                                background=theme['bg'],
                                foreground=theme['text'],
                                font=("Arial", 36))
            
            # 如果异步窗口存在，更新其样式
            if hasattr(self, 'async_window'):
                self.async_window.configure(bg=theme['bg'])
                self.async_window.flash_frame.configure(style='Theme.TFrame')
                self.async_window.content_frame.configure(style='Theme.TFrame')
                self.async_window.result_label.configure(style='Theme.TLabel')
                self.async_window.countdown_label.configure(
                    style='Theme.TLabel',
                    foreground='#FF4500'
                )
                
                # 重新配置样式
                self.style.configure('Theme.TFrame', background=theme['bg'])
                self.style.configure('Theme.TLabel',
                                    background=theme['bg'],
                                    foreground=theme['text'],
                                    font=("Arial", 36))
                
                # 更新闪烁效果的样式
                for color in self.draw_flash_colors:
                    self.style.configure(f'Flash{color}.TFrame', background=color)
        
        theme_combo.bind('<<ComboboxSelected>>', update_theme)
        
        # 添加分隔线和程序目录按钮
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, padx=20, pady=20)
        directory_frame = ttk.Frame(scrollable_frame)
        directory_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(
            directory_frame,
            text="打开程序根目录",
            command=lambda: os.startfile(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)))
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            directory_frame,
            text="（用于添加名单）",
            font=('Arial', 10),
            foreground='#808080'
        ).pack(side=tk.LEFT, padx=10)
        
        # 添加分隔线和卸载按钮
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, padx=20, pady=20)
        uninstall_frame = ttk.Frame(scrollable_frame)
        uninstall_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(
            uninstall_frame,
            text="卸载程序",
            command=self.uninstall_program,
            style='Red.TButton'  # 使用红色按钮样式
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            uninstall_frame,
            text="（将删除所有配置）",
            font=('Arial', 10),
            foreground='#FF4D4D'  # 使用红色警告文字
        ).pack(side=tk.LEFT, padx=10)
        
        # 配置滚动区域
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_reqwidth())
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # 布局 - 使用pack_propagate(False)保frame保持其大小
        frame.pack_propagate(False)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 修改滚动条事件绑定
        def on_scroll_press(event):
            self.disable_window_move()
            scrollbar._drag_start = event.y
            scrollbar._scroll_start = canvas.yview()[0]
        
        def on_scroll_release(event):
            self.enable_window_move()
            if hasattr(scrollbar, '_drag_start'):
                del scrollbar._drag_start
            if hasattr(scrollbar, '_scroll_start'):
                del scrollbar._scroll_start
        
        def on_scroll_motion(event):
            if hasattr(scrollbar, '_drag_start'):
                delta = (event.y - scrollbar._drag_start) / canvas.winfo_height()
                new_pos = max(0, min(1, scrollbar._scroll_start + delta))
                canvas.yview_moveto(new_pos)
        
        scrollbar.bind("<Button-1>", on_scroll_press)
        scrollbar.bind("<B1-Motion>", on_scroll_motion)
        scrollbar.bind("<ButtonRelease-1>", on_scroll_release)
        
        # 修改透明度滑块的绑定
        opacity_scale.bind("<Button-1>", self.disable_window_move)
        opacity_scale.bind("<ButtonRelease-1>", lambda e: self.enable_window_move(e, update_opacity))
        
        # 修改速度滑块的绑定
        speed_scale.bind("<Button-1>", self.disable_window_move)
        speed_scale.bind("<ButtonRelease-1>", lambda e: self.enable_window_move(e, update_speed))
        
        # 修改滚动条的绑定
        scrollbar.bind("<Button-1>", self.disable_window_move)
        scrollbar.bind("<ButtonRelease-1>", self.enable_window_move)
        
        # 右侧信息面板
        credits_frame = ttk.Frame(right_frame)
        credits_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标题框架
        title_container = ttk.Frame(credits_frame)
        title_container.pack(pady=(20, 10))
        
        # 添加程序图标
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            
            image_path = os.path.join(base_path, "化学计时器.png")
            image = Image.open(image_path)
            image = image.resize((48, 48), Image.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            icon_label = ttk.Label(title_container, image=photo)
            icon_label.image = photo
            icon_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # 在图标右侧添加程序名称和版本
            name_version_frame = ttk.Frame(title_container)
            name_version_frame.pack(side=tk.LEFT)
            
            ttk.Label(name_version_frame, 
                     text="计时器", 
                     font=('Arial', 20, 'bold')).pack(anchor=tk.W)
            
            ttk.Label(name_version_frame, 
                     text="版本 V 5.0", 
                     font=('Arial', 10)).pack(anchor=tk.W)
        
        except Exception as e:
            print(f"加载图标失败: {e}")
            # 可以添加一默认的文本标作为备用
            ttk.Label(title_container, 
                     text="化学计时器", 
                     font=('Arial', 20, 'bold')).pack(side=tk.LEFT)
        
        # 添加分隔线
        ttk.Separator(credits_frame, orient='horizontal').pack(fill=tk.X, padx=20, pady=15)
        
        # 添加鸣谢信息
        credits_text = """特别鸣谢
Claude-3.5-sonnet

制作与改进
霜筱、三班全体
1915491976@qq.com

ShuangSue © 2024
钱高化学组×高一三班
保留所有权利"""

        for line in credits_text.split('\n'):
            if line.strip():
                if line in ["特别鸣谢", "制作与改进", "ShuangSue © 2024"]:
                    ttk.Label(credits_frame, 
                             text=line,
                             font=('Arial', 12, 'bold')).pack(pady=(10, 3))
                else:
                    ttk.Label(credits_frame, 
                             text=line,
                             font=('Arial', 10)).pack(pady=1)
        
        # 添加检查更新按钮
        update_frame = ttk.Frame(scrollable_frame)
        update_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(
            update_frame,
            text="检查更新",
            command=self.check_for_updates
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            update_frame,
            text=f"当前版本：v{UpdateChecker.VERSION}",
            font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=10)
        
        return frame

    def uninstall_program(self):
        """卸载程序"""
        if messagebox.askyesno("卸载确认", 
                              "确定要卸载化学计时器吗？\n这将删除所配置文件，但不删除您创建的名单文件"):
            try:
                # 删除配置文件夹
                config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
                if os.path.exists(config_dir):
                    import shutil
                    shutil.rmtree(config_dir)
                
                # 提示用户卸载成功
                messagebox.showinfo("卸载成功", 
                                  "化学计时器已卸载。\n您可以接着删除程序文件夹完成最后的清理。")
                
                # 退出程序
                self.quit_window()
                
            except Exception as e:
                messagebox.showerror("卸载失败", f"卸载过程中发生错误：\n{str(e)}")

    def disable_window_move(self, event=None):
        """禁用窗口移动"""
        self.master.unbind("<ButtonPress-1>")
        self.master.unbind("<B1-Motion>")
        self.master.unbind("<ButtonRelease-1>")

    def enable_window_move(self, event=None, callback=None):
        """恢复窗口移动"""
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<B1-Motion>", self.do_move)
        self.master.bind("<ButtonRelease-1>", self.stop_move)
        
        # 如果有回调函数执它
        if callback:
            callback(event)

    def create_draw_interface(self):
        """创抽签界面的主要部分"""
        # 获取前主题颜色
        current_theme = self.themes[self.config.get("theme")]
        
        # 创建记录表框架
        self.record_frame = ttk.Frame(self.left_navbar, style='Record.TFrame')
        self.record_frame.pack(fill=tk.BOTH, expand=True)

        # 添加标题
        ttk.Label(self.record_frame, text="抽取记录", 
                  font=("Arial", 16), style='Record.TLabel').pack(pady=(10, 10))

        # 创建一个框架容纳文本框和滚动条
        text_frame = ttk.Frame(self.record_frame, style='Record.TFrame')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建滚动条
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建记录列表，并与滚动条关联
        self.record_text = tk.Text(text_frame, 
                                  width=12, 
                                  height=20,
                                  font=("Arial", 12), 
                                  relief='flat',
                                  yscrollcommand=scrollbar.set,
                                  bg=current_theme['left_nav'],
                                  fg=current_theme['text'],
                                  insertbackground=current_theme['text'])
        
        self.record_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 配置滚动
        scrollbar.config(command=self.record_text.yview)

        # 修改滚动条事件绑定
        def on_scroll_press(event):
            self.disable_window_move()
        
        def on_scroll_release(event):
            self.enable_window_move()
        
        def on_mousewheel(event):
            self.record_text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        scrollbar.bind("<Button-1>", on_scroll_press)
        scrollbar.bind("<ButtonRelease-1>", on_scroll_release)
        self.record_text.bind("<MouseWheel>", on_mousewheel)  # 添加鼠标滚轮支持

        # 显示
        self.draw_display = ttk.Label(self.random_draw_frame, text="等待抽签...", 
                                     font=("Arial", 48), anchor=tk.CENTER)
        self.draw_display.pack(expand=True, pady=20)

        # 进度条
        self.progress = ttk.Progressbar(self.random_draw_frame, orient='horizontal', 
                                        mode='determinate', length=300)
        self.progress.pack(pady=10)

        # 按钮框架
        button_frame = ttk.Frame(self.random_draw_frame)
        button_frame.pack(pady=20)

        # 取按钮
        self.draw_one_button = ttk.Button(button_frame, text="抽取一名学生", 
                                         command=lambda: self.start_draw(1), 
                                         style='TButton')
        self.draw_one_button.pack(side=tk.LEFT, padx=10)
        
        self.draw_two_button = ttk.Button(button_frame, text="抽取两名学生", 
                                         command=lambda: self.start_draw(2), 
                                         style='TButton')
        self.draw_two_button.pack(side=tk.LEFT, padx=10)

        # 显示现有记录
        self.update_record_display()

        # 修改动条事件绑定
        scrollbar.bind("<Button-1>", self.disable_window_move)
        scrollbar.bind("<ButtonRelease-1>", self.enable_window_move)
        
        # 确保有框架使用正确的背景色
        for widget in [self.record_frame, text_frame]:
            widget.configure(style='Record.TFrame')

        # 为文本框和其父框架都添加鼠标滚轮支持
        self.record_text.bind("<MouseWheel>", on_mousewheel)
        text_frame.bind("<MouseWheel>", on_mousewheel)

    def reset_records(self):
        """重置选中名单的抽取记录"""
        selected_file = self.file_var.get()
        if hasattr(self, 'file_records'):
            # 清空当前文件的记录
            self.file_records[selected_file] = {}
            # 更新当前记录引用
            self.student_records = self.file_records[selected_file]
            # 重新初始化所有学生的记录为0
            try:
                program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
                file_path = os.path.join(program_dir, selected_file)
                with open(file_path, "r", encoding="utf-8") as file:
                    self.students = file.read().strip().split("\n")
                    for student in self.students:
                        self.student_records[student] = 0
                # 立即更新显示
                self.update_record_display()
                # 置显示文本
                if hasattr(self, 'draw_display'):
                    self.draw_display.config(text="等待抽签...")
            except Exception as e:
                print(f"重置记录失败: {e}")

    def resize_periodic_table(self, event=None):
        """调整元素周期表大小"""
        if hasattr(self, 'original_image'):
            try:
                # 使用窗口的大小
                window_width = self.master.winfo_width()
                window_height = self.master.winfo_height() - 50  # 减顶部导航栏的高度
                
                # 如果窗口太小，跳过调整
                if window_width <= 1 or window_height <= 1:
                    return
                    
                # 计算图片的宽高
                img_ratio = self.original_image.width / self.original_image.height
                window_ratio = window_width / window_height
                
                # 根据窗口比例确定缩放小
                if window_ratio > img_ratio:
                    new_height = window_height
                    new_width = int(new_height * img_ratio)
                else:
                    new_width = window_width
                    new_height = int(new_width / img_ratio)
                
                # 调整图片大小
                resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized_image)
                
                # 更
                self.periodic_table_label.config(image=photo)
                self.periodic_table_label.image = photo  # 保持引用防止垃圾回收
                
            except Exception as e:
                print(f"调整图片大小时发生错误: {e}")

    def create_chemical_constants_frame(self):
        """创建化学常数页面"""
        frame = ttk.Frame(self.main_content)
        
        # 建标题
        title_label = ttk.Label(frame, text="常用化学常数", font=("Arial", 24, "bold"))
        title_label.pack(pady=20)
        
        # 创建常数列表框架
        constants_frame = ttk.Frame(frame)
        constants_frame.pack(expand=True, fill=tk.BOTH, padx=20)
        
        # 义常用化学常数（统一保留两位小数）
        constants = [
            ("阿伏伽德罗常数 (NA)", "6.02 × 10²³ mol⁻¹"),
            ("气体常数 (R)", "8.31 J/(mol·K)"),
            ("标准大气压 (P)", "1.01 × 10⁵ Pa"),
            ("标准摩尔体积 (Vm)", "22.41 L/mol"),
            ("法拉第常数 (F)", "9.65 × 10⁴ C/mol"),
            ("普朗克常数 (h)", "6.63 × 10⁻³⁴ J·s"),
            ("光速 (c)", "3.00 × 10⁸ m/s"),
            ("玻尔兹曼数 (k)", "1.38 × 10⁻²³ J/K"),
            ("元电荷 (e)", "1.60 × 10⁻¹⁹ C"),
            ("空介电常数 (ε₀)", "8.85 × 10⁻¹² F/m")
        ]
        
        # 创建常数标签
        for i, (name, value) in enumerate(constants):
            # 创建一个框架来容纳每个常数
            constant_frame = ttk.Frame(constants_frame)
            constant_frame.pack(fill=tk.X, pady=5)
            
            # 常数名称
            name_label = ttk.Label(constant_frame, text=name, font=("Arial", 12))
            name_label.pack(side=tk.LEFT, padx=10)
            
            # 常数值
            value_label = ttk.Label(constant_frame, text=value, font=("Arial", 12))
            value_label.pack(side=tk.RIGHT, padx=10)
        
        return frame

    def show_chemical_constants(self):
        """显示化学常数页面"""
        self.clear_main_content()
        
        # 隐藏左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack_forget()
        
        # 隐藏所有子列表
        self.timer_buttons.pack_forget()
        self.record_frame.pack_forget() if hasattr(self, 'record_frame') else None
        
        # 显示化学常数框架
        if hasattr(self, 'chemical_constants_frame'):
            self.chemical_constants_frame.pack(expand=True, fill=tk.BOTH)

    def show_settings(self):
        """显示设置页面"""
        self.clear_main_content()
        
        # 隐藏左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack_forget()
        
        # 隐藏所有子列表
        self.timer_buttons.pack_forget()
        self.record_frame.pack_forget() if hasattr(self, 'record_frame') else None
        
        # 显示设置框架
        if hasattr(self, 'settings_frame'):
            self.settings_frame.pack(expand=True, fill=tk.BOTH)

    def handle_global_hotkey(self, event):
        """处理全局热键事件"""
        try:
            # 检查是否正在异步抽签
            if hasattr(self, 'async_drawing') and self.async_drawing and self.config.get("async_draw"):
                return
                
            # 检查是否允许快速抽取
            if not self.visible and not self.config.get("always_allow_quick_draw"):
                # 检查是否使用异步抽签
                if self.config.get("async_draw"):
                    # 直接进行抽签，不显示窗口
                    self.quick_async_draw()
                else:
                    # 显示界面后抽签
                    self.master.deiconify()
                    self.visible = True
                    self.update_hide_button_text()
                    self.show_random_draw()
                    # 使用 always_auto_hide 设置
                    self.master.after(100, lambda: self.start_draw(1, auto_hide=True))
                
            elif self.config.get("always_allow_quick_draw"):
                # 如果启用了始终允许快速抽取
                if self.config.get("async_draw"):
                    # 直接进行抽签，不显示主窗口
                    self.quick_async_draw()
                else:
                    # 显示界面后抽签
                    if not self.visible:
                        self.master.deiconify()
                        self.visible = True
                        self.update_hide_button_text()
                    self.show_random_draw()
                    # 使用 always_auto_hide 设置
                    self.master.after(100, lambda: self.start_draw(1, auto_hide=True))
        except Exception as e:
            Logger.error(f"处理全局热键时发生错误: {e}")

    def flash_draw_window(self):
        """门用抽签结果的闪烁效果"""
        if self.flash_count < self.max_draw_flashes:
            color = self.draw_flash_colors[self.flash_count % len(self.draw_flash_colors)]
            self.master.configure(background=color)
            for widget in self.master.winfo_children():
                if isinstance(widget, ttk.Frame):
                    widget.configure(style=f'Flash{color}.TFrame')
            self.flash_count += 1
            self.master.after(100, self.stop_draw_flashing)
        else:
            self.reset_window_color()

    def stop_draw_flashing(self):
        """停止签闪烁"""
        self.reset_window_color()
        self.master.after(100, self.flash_draw_window)

    def reset_hotkey(self, default_key):
        self.config.set("hotkey", default_key)
        self.hotkey_label.config(text=f":{default_key}")
        self.hotkey_button.config(text="点击设置")

    def start_hotkey_listen(self):
        """开始监听键盘输入"""
        self.hotkey_button.configure(text="请按键...", state='disabled')
        self.hotkey_label.configure(text="在等待按...")
        
        # 创建键盘监听器
        keyboard.hook(self.on_key_press)

    def on_key_press(self, event):
        """理键盘按键"""
        try:
            # 获取按键名称
            key_name = event.name
            
            # 停止监听
            keyboard.unhook(self.on_key_press)
            
            # 更新配置
            self.update_hotkey(key_name)
            
            # 恢复按钮状态
            self.hotkey_button.configure(text="点设置", state='normal')
            
        except Exception as e:
            print(f"设置快捷键时发生错误: {e}")
            self.reset_hotkey(self.config.get("hotkey"))

    def update_hotkey(self, new_hotkey):
        """更新快捷键设置"""
        try:
            # 先注销旧的快捷键
            keyboard.unhook_all()
            
            # 更新配置
            self.config.set("hotkey", new_hotkey)
            
            # 更新显示
            self.hotkey_label.configure(text=f":{new_hotkey}")
            
            # 注册新的快捷键
            keyboard.on_press_key(new_hotkey, self.handle_global_hotkey)
            
        except Exception as e:
            print(f"更新快捷键失败: {e}")
            messagebox.showerror("错误", "设置快捷键失败，已恢复默认设置")
            self.reset_hotkey("enter")

    def reset_hotkey(self, default_key):
        """重置快捷键为默认值"""
        self.update_hotkey(default_key)
        self.hotkey_button.configure(text="点击设置", state='normal')

    def quick_async_draw(self):
        """异步快速抽签"""
        if self.async_drawing:
            return
            
        try:
            self.async_drawing = True
            
            current_theme = self.themes[self.config.get("theme")]
            if not hasattr(self, 'async_window'):
                self.async_window = AsyncDrawWindow(self.master, current_theme)
            else:
                self.async_window.deiconify()
            
            # 根据设置决定是否显示动画
            if self.config.get("async_draw_animation"):
                self.start_async_animation()
            else:
                # 直接执行抽签
                self.perform_async_draw()
            
        except Exception as e:
            print(f"异步抽签失败: {e}")
            if hasattr(self, 'async_window'):
                self.async_window.result_label.config(text="抽签失败")
            self.async_drawing = False

    def start_async_animation(self):
        """开始异步抽签动画"""
        try:
            # 获取学生列表和抽签结果
            selected_file = self.file_var.get() if hasattr(self, 'file_var') else self.get_first_txt_file()
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            file_path = os.path.join(program_dir, selected_file)
            
            with open(file_path, "r", encoding="utf-8") as file:
                students = file.read().strip().split("\n")
                selected_student = self.get_draw_result(students)
            
            # 开始动画
            def update_animation(step=0):
                if step < 100:  # 使用进度条相同的进度
                    # 随机显示一个名字
                    random_student = random.choice(students)
                    self.async_window.result_label.config(text=random_student)
                    # 使用配置的速
                    speed = self.config.get("draw_speed")
                    self.master.after(50, lambda: update_animation(step + speed))
                else:
                    # 动画结束，显示真实结果
                    self.async_window.result_label.config(text=selected_student)
                    # 播放声音和闪烁效果
                    if self.config.get("sound_enabled"):
                        try:
                            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                        except Exception as e:
                            print(f"无法播放系统提示音: {e}")
                    
                    self.flash_count = 0
                    self.flash_async_window()
                    # 开始倒计时
                    self.start_async_countdown()
            
            # 启动动画循环
            update_animation()
            
        except Exception as e:
            print(f"异步抽签画失败: {e}")
            if hasattr(self, 'async_window'):
                self.async_window.result_label.config(text="抽签失败")

    def get_draw_result(self, students=None):
        """获取抽签结果"""
        try:
            # 如果没传入学生表，则读取文件
            if students is None:
                selected_file = self.file_var.get() if hasattr(self, 'file_var') else self.get_first_txt_file()
                program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
                file_path = os.path.join(program_dir, selected_file)
                
                with open(file_path, "r", encoding="utf-8") as file:
                    students = file.read().strip().split("\n")
            
            # 初始化记录字典（如果需要）
            selected_file = self.file_var.get() if hasattr(self, 'file_var') else self.get_first_txt_file()
            if not hasattr(self, 'file_records'):
                self.file_records = {}
            if selected_file not in self.file_records:
                self.file_records[selected_file] = {}
            
            # 确保有学生都在记录中并初始化为0
            for student in students:
                if student not in self.file_records[selected_file]:
                    self.file_records[selected_file][student] = 0
            
            # 使用权重进行抽取
            if len(self.file_records[selected_file]) > 0:
                min_count = min(self.file_records[selected_file].values())
                weights = []
                for student in students:
                    count = self.file_records[selected_file].get(student, 0)
                    if count > min_count:
                        weight = 0.01
                    else:
                        weight = 1.0
                    weights.append(weight)
            else:
                weights = [1.0] * len(students)
            
            # 如果所有权重都是0.01，重置为相等权重
            if all(w == 0.01 for w in weights):
                weights = [1.0] * len(weights)
            
            # 抽取学生
            selected_student = random.choices(students, weights=weights, k=1)[0]
            
            # 更新记录
            self.file_records[selected_file][selected_student] = self.file_records[selected_file].get(selected_student, 0) + 1
            
            return selected_student
                
        except Exception as e:
            print(f"获取抽签结果失败: {e}")
            return "抽签失败"

    def flash_async_window(self):
        """闪烁异步抽签窗口"""
        if hasattr(self, 'async_window'):
            if self.flash_count < self.max_draw_flashes:
                color = self.draw_flash_colors[self.flash_count % len(self.draw_flash_colors)]
                # 只改变闪烁框架的背景色
                self.async_window.flash_frame.configure(style=f'Flash{color}.TFrame')
                self.flash_count += 1
                self.master.after(100, self.stop_async_flashing)
            else:
                self.reset_async_window_color()

    def reset_async_window_color(self):
        """重置异步窗口颜色"""
        if hasattr(self, 'async_window'):
            # 重置闪烁框架的颜色
            self.async_window.flash_frame.configure(style='Flash.TFrame')

    def stop_async_flashing(self):
        """停止异步窗口闪烁"""
        if hasattr(self, 'async_window'):
            self.reset_async_window_color()
            self.master.after(100, self.flash_async_window)

    def start_async_countdown(self, duration=None):
        """异步窗口的倒计时"""
        if hasattr(self, 'async_window'):
            if duration is None:
                # 使用配置的隐藏时间
                duration = self.config.get("hide_delay") * 1000
                
            start_time = time.time()
            
            def update():
                current_time = time.time()
                elapsed = int((current_time - start_time) * 1000)
                remaining = max(0, duration - elapsed)
                
                if remaining > 0:
                    # 确保倒计时标签在最上层
                    self.async_window.countdown_label.lift()
                    self.async_window.countdown_label.config(text=f"{remaining/1000:.1f}")
                    self.master.after(16, update)
                else:
                    self.async_window.withdraw()
                    # 在窗口隐后重置抽签状态
                    self.async_drawing = False
            
            # 确保倒计时标签初始显示
            self.async_window.countdown_label.config(text=f"{duration/1000:.1f}")
            self.async_window.countdown_label.lift()
            update()

    def start_hide_countdown(self, duration=None):
        """开始倒计时并在结束时隐藏窗口"""
        if duration is None:
            # 使用配置的隐藏时间
            duration = self.config.get("hide_delay") * 1000
            
        start_time = time.time()
        
        def update():
            current_time = time.time()
            elapsed = int((current_time - start_time) * 1000)
            remaining = max(0, duration - elapsed)
            
            if remaining > 0:
                # 更新显示文本（保留一位小数）
                if hasattr(self, 'hide_countdown'):
                    self.hide_countdown.config(text=f"{remaining/1000:.1f}")
                    # 继续更新
                    self.master.after(16, update)
            else:
                # 时间到，隐藏窗口
                self.hide_main_window()
        
        # 开始更新循环
        update()

    def hide_async_result(self):
        """隐藏异步抽签结果"""
        if hasattr(self, 'async_window'):
            self.async_window.withdraw()
        self.hide_main_window()

    def get_first_txt_file(self):
        """获取第一个txt文件"""
        program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        txt_files = [f for f in os.listdir(program_dir) if f.endswith('.txt')]
        return txt_files[0] if txt_files else None

    def perform_async_draw(self):
        """执行实际的异步抽签"""
        try:
            # 使用选择的文件
            selected_file = self.file_var.get() if hasattr(self, 'file_var') else self.get_first_txt_file()
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            file_path = os.path.join(program_dir, selected_file)
            
            # 读取并抽取学生
            with open(file_path, "r", encoding="utf-8") as file:
                students = file.read().strip().split("\n")
                selected_student = self.get_draw_result(students)
                
                # 更新显示
                self.async_window.result_label.config(text=selected_student)
                
                # 播放声音和闪烁效果
                if self.config.get("sound_enabled"):
                    try:
                        winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except Exception as e:
                        print(f"无法播放系统提示音: {e}")
                
                self.flash_count = 0
                self.flash_async_window()
                
                # 开始倒计时并在结束时隐藏窗口
                self.start_async_countdown()
                
        except Exception as e:
            print(f"异步抽签失败: {e}")
            if hasattr(self, 'async_window'):
                self.async_window.result_label.config(text="抽签失败")

    def check_for_updates(self):
        """检查更新"""
        try:
            has_update, latest_version, download_url = UpdateChecker.check_update()
            if has_update:
                # 显示更新提示对话框
                if messagebox.askyesno(
                    "发现新版本",
                    f"发现新版本 v{latest_version}\n是否立即更新？",
                    icon='info'
                ):
                    # 打开下载��接
                    webbrowser.open(download_url)
        except Exception as e:
            Logger.error(f"检查更新失败: {e}")

class ThemeManager:
    """主题管理类"""
    
    def __init__(self, app: 'ChemistryTimer') -> None:
        self.app = app
        self.current_theme = app.config.get("theme")
        
    def apply_theme(self, theme_name: str) -> None:
        """应用主题"""
        if theme_name not in self.app.themes:
            Logger.error(f"主题 {theme_name} 不存在")
            return
            
        theme = self.app.themes[theme_name]
        self._update_styles(theme)
        self._update_colors(theme)
        self.current_theme = theme_name
        self.app.config.set("theme", theme_name)

def create_icon_file():
    """自动将 PNG 换为 ICO 文件"""
    try:
        from PIL import Image
        import os
        
        # 获取程序目录
        program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        png_path = os.path.join(program_dir, "icon.png")
        ico_path = os.path.join(program_dir, "icon.ico")
        
        # 如果 ICO 文件已存在，直接返回路径
        if os.path.exists(ico_path):
            return ico_path
            
        # 转换图片
        img = Image.open(png_path)
        # 确保图片是正方形
        size = max(img.size)
        new_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        new_img.paste(img, ((size - img.size[0]) // 2, (size - img.size[1]) // 2))
        # 保存为 ICO 文件
        new_img.save(ico_path, format='ICO', sizes=[(size, size)])
        return ico_path
    except Exception as e:
        print(f"创建图标文件失败: {e}")
        return None

class SplashScreen(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        
        # 获取幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 设置窗口大小
        width = 400
        height = 280
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # 设置窗口样式
        self.configure(bg='white')
        
        # 创建主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # 创建内容框架
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(expand=True, fill=tk.BOTH)
        
        try:
            # 加载和显示图标
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            
            image_path = os.path.join(base_path, "化学计时器.png")
            image = Image.open(image_path)
            image = image.resize((80, 80), Image.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            icon_label = ttk.Label(content_frame, image=photo)
            icon_label.image = photo
            icon_label.pack(pady=(30, 15))
        except Exception:
            pass
        
        # 添加标题
        title_frame = ttk.Frame(content_frame)
        title_frame.pack(fill=tk.X)
        
        ttk.Label(title_frame, 
                 text="化学计时器", 
                 font=('Microsoft YaHei UI', 32, 'bold')).pack()
        
        ttk.Label(title_frame,
                 text="Version 5.0",
                 font=('Arial', 12)).pack(pady=(5, 15))  # 减少底部间距
        
        # 创建度显示框架
        progress_frame = ttk.Frame(content_frame)
        progress_frame.pack(fill=tk.X, padx=40)
        
        # 添加加载提示和百分比
        self.loading_text = ttk.Label(progress_frame, 
                                    text="正在启动...", 
                                    font=('Microsoft YaHei UI', 10))
        self.loading_text.pack(side=tk.LEFT)
        
        self.percent_label = ttk.Label(progress_frame,
                                     text="0%",
                                     font=('Arial', 10))
        self.percent_label.pack(side=tk.RIGHT)
        
        # 添加进度条
        style = ttk.Style()
        style.configure('Splash.Horizontal.TProgressbar',
                       troughcolor='#F0F0F0',
                       background='#4A90E2',
                       thickness=6)
        
        self.progress = ttk.Progressbar(content_frame, 
                                      mode='determinate',
                                      length=320,
                                      style='Splash.Horizontal.TProgressbar')
        self.progress.pack(pady=(5, 30))  # 增加底部间距，为版权信息留出空间
        
        # 创建底部框架
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=15)
        
        # 添加版权信息
        ttk.Label(bottom_frame,
                 text="钱高化学组×27届高一三班",
                 font=('Arial', 9),
                 foreground='#808080').pack()
        
        # 初始进度
        self.progress['value'] = 0
        self.progress['maximum'] = 100
        
        # 定义加载步骤
        self.loading_steps = [
            "正在启动...",
            "正在加载配置...",
            "正在初始化界面...",
            "准就绪..."
        ]
        self.current_step = 0
        self.update_progress()
        
        # 强制更新显示
        self.update()

    def update_progress(self):
        """更新进度条和加载文本"""
        if self.progress['value'] < 100:
            # 计算当前步骤
            step_index = min(int(self.progress['value'] / 25), len(self.loading_steps) - 1)
            if step_index != self.current_step:
                self.current_step = step_index
                self.loading_text.config(text=self.loading_steps[step_index])
            
            # 更新进度条和百分比
            self.progress['value'] += 2
            self.percent_label.config(text=f"{int(self.progress['value'])}%")
            
            # 设置下次更新
            self.after(20, self.update_progress)  # 加快更新速度

    def destroy(self):
        """销毁启动窗口"""
        super().destroy()

# 在 ChemistryTimer 类之前添加
class AsyncDrawWindow(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        
        # 设置窗口不在任务栏显示
        self.wm_attributes("-toolwindow", True)
        
        # 修改获取透明度的方式，并降低透明度
        if hasattr(master, 'timer') and hasattr(master.timer, 'config'):
            main_opacity = master.timer.config.get("opacity")
            self.attributes('-alpha', max(0.3, main_opacity - 0.2))
        
        # 使用主窗口的主题
        self.configure(bg=theme['bg'])
        
        # 设置窗口大小和位置
        width = 300
        height = 200
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建外层框架（用于闪烁效果）
        self.flash_frame = ttk.Frame(self, style='Theme.TFrame')
        self.flash_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 创建内容框架（使用主题背景色
        self.content_frame = ttk.Frame(self.flash_frame, style='Theme.TFrame')
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # 创建结果标签（使用主题颜色）
        self.result_label = ttk.Label(
            self.content_frame,
            text="",
            font=("Arial", 36),
            anchor=tk.CENTER,
            justify=tk.CENTER,
            style='Theme.TLabel'
        )
        self.result_label.pack(expand=True)
        
        # 创建倒计时标签
        self.countdown_label = ttk.Label(
            self.content_frame,
            text="",
            font=("Arial", 24, "bold"),
            foreground='#FF4500',
            style='Theme.TLabel'
        )
        self.countdown_label.place(relx=1.0, rely=0, x=-20, y=20, anchor="ne")
        
        # 绑定拖动事件
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<ButtonRelease-1>", self.stop_move)
        self.bind("<B1-Motion>", self.do_move)
        
        self.x = None
        self.y = None
    
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
    
    def stop_move(self, event):
        self.x = None
        self.y = None
    
    def do_move(self, event):
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.winfo_x() + deltax
            y = self.winfo_y() + deltay
            self.geometry(f"+{x}+{y}")

class ResourceManager:
    """资源管理类"""
    
    def __init__(self):
        self.base_path = self._get_base_path()
        self.cache = {}
        
    def _get_base_path(self):
        """获取资源基础路径"""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.abspath(".")
    
    def get_image(self, name: str) -> Optional[ImageTk.PhotoImage]:
        """获取图片资源"""
        if name in self.cache:
            return self.cache[name]
            
        try:
            path = os.path.join(self.base_path, name)
            image = Image.open(path)
            photo = ImageTk.PhotoImage(image)
            self.cache[name] = photo
            return photo
        except Exception as e:
            Logger.error(f"加载图片 {name} 失败: {str(e)}")
            return None
            
    def get_icon(self) -> Optional[str]:
        """获取图标文件路径"""
        for icon_file in ["icon.ico", "icon.png", "化学计时.png"]:
            path = os.path.join(self.base_path, icon_file)
            if os.path.exists(path):
                return path
        return None

def handle_exception(func):
    """异常处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"执行 {func.__name__} 时发生错误: {str(e)}"
            Logger.error(error_msg)
            messagebox.showerror("错误", f"操作失败:\n{str(e)}")
            return None
    return wrapper

# 修改主程序入口
if __name__ == "__main__":
    # 创建主窗口但先不显示
    root = tk.Tk()
    root.withdraw()
    
    # 显示启动窗口
    splash = SplashScreen(root)
    
    try:
        # 初始化主程序
        timer = ChemistryTimer(root)
        
        # 设置窗口关闭处理
        root.protocol("WM_DELETE_WINDOW", timer.on_closing)
        
        # 销毁启动窗口
        splash.destroy()
        
        # 开始主循环
        root.mainloop()
        
    except Exception as e:
        # 如果发生错误确保启动窗口被销毁
        if splash:
            splash.destroy()
        # 显示错误消息
        messagebox.showerror("启动错误", f"程序启动时发生错误：\n{str(e)}")
        sys.exit(1)


