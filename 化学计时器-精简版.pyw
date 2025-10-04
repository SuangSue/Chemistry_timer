import tkinter as tk
from tkinter import Scrollbar, ttk
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
from datetime import datetime, timedelta
from typing import Optional, Any, Tuple
import functools
import requests
import webbrowser

try:
    import tkinterdnd2
except ImportError:
    pass

class UpdateChecker:
    VERSION = "V5.TG-特供版"
    UPDATE_URL = "https://api.github.com/repos/SuangSue/Chemistry_timer/releases/latest"
    
    @classmethod
    def check_update(cls) -> Tuple[bool, str, str]:
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Chemistry-Timer-App'
            }
            
            config = Config()
            github_token = config.get("github_token")
            
            if github_token:
                headers['Authorization'] = f'Bearer {github_token}'
                os.environ['GITHUB_TOKEN'] = github_token
            
            response = requests.get(cls.UPDATE_URL, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            latest_version = data['tag_name']
            download_url = data['assets'][0]['browser_download_url']
            
            Logger.info(f"当前版本: {cls.VERSION}, 最新版本: {latest_version}")
            
            has_update = cls._compare_versions(latest_version, cls.VERSION)
            return has_update, latest_version, download_url
            
        except Exception as e:
            Logger.error(f"检查更新失败: {e}")
            return False, cls.VERSION, ""
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> bool:
        def normalize(v):
            v = v.upper().lstrip('V')
            parts = [int(x) for x in v.split('.')]
            while len(parts) < 2:
                parts.append(0)
            return parts
            
        try:
            v1_parts = normalize(v1)
            v2_parts = normalize(v2)
            return v1_parts > v2_parts
        except Exception as e:
            Logger.error(f"版本号比较失败: {e}")
            return False

class Logger:
    def __init__(self):
        log_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'chemistry_timer_{datetime.now().strftime("%Y%m%d")}.log')
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        logger.handlers.clear()
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.propagate = False
    
    @staticmethod
    def info(msg: str) -> None:
        logging.info(msg)
        
    @staticmethod
    def error(msg: str) -> None:
        logging.error(msg)
        
    @staticmethod
    def debug(msg: str) -> None:
        logging.debug(msg)

class StateManager:
    def __init__(self):
        self.states = {}
        
    def set_state(self, key: str, value: Any) -> None:
        self.states[key] = value
        Logger.debug(f"状态更新: {key} = {value}")
        
    def get_state(self, key: str, default: Any = None) -> Any:
        return self.states.get(key, default)

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
        
    def start_measure(self, name: str) -> None:
        self.metrics[name] = time.time()
        
    def end_measure(self, name: str) -> Optional[float]:
        if name in self.metrics:
            duration = time.time() - self.metrics[name]
            del self.metrics[name]
            return duration
        return None

class Config:
    def __init__(self):
        self.config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        self.default_config = {
            "opacity": 0.8,
            "sound_enabled": True,
            "theme": "默认蓝",
            "draw_speed": 8.0,
            "hotkey": "enter",
            "always_allow_quick_draw": False,
            "async_draw": False,
            "async_draw_animation": False,
            "hide_delay": 2.0,
            "always_auto_hide": True,
            "countdown_auto_hide": False,
            "show_watermark": True,
            "quick_init": False,
            "github_token": "",
            "save_draw_records": True,
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

    def get(self, key, default=None):
        return self.config.get(key, self.default_config.get(key) if default is None else default)

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
        try:
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if "化学计时器" in window_text:
                        windows.append(hwnd)
                return True

            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            if windows:
                hwnd = windows[0]
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True
            
            def find_tray_window(hwnd, windows):
                if "化学计时" in win32gui.GetWindowText(hwnd):
                    windows.append(hwnd)
                return True
                
            tray_windows = []
            win32gui.EnumWindows(find_tray_window, tray_windows)
            
            if tray_windows:
                win32gui.SendMessage(tray_windows[0], win32con.WM_USER + 20, 0, 0)
                return True
                
        except Exception as e:
            print(f"激活窗口失败: {e}")
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
        
        self.drag_data = {
            "x": 0, 
            "y": 0, 
            "start_x": 0,
            "start_y": 0,
            "clicked": False
        }
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

    def on_press(self, event):
        self.drag_data["x"] = event.x_root - self.winfo_x()
        self.drag_data["y"] = event.y_root - self.winfo_y()
        self.drag_data["start_x"] = event.x_root
        self.drag_data["start_y"] = event.y_root
        self.drag_data["clicked"] = True
        return "break"

    def on_release(self, event):
        if not self.drag_data["clicked"]:
            return "break"
            
        dx = abs(event.x_root - self.drag_data["start_x"])
        dy = abs(event.y_root - self.drag_data["start_y"])
        
        if dx < 5 and dy < 5 and hasattr(self.master, 'toggle_visibility'):
            self.master.toggle_visibility()
            
        self.drag_data["clicked"] = False
        return "break"

    def on_drag(self, event):
        self.drag_data["clicked"] = False
        
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        
        x = max(0, min(x, self.screen_width - self.winfo_width()))
        y = max(0, min(y, self.screen_height - self.winfo_height()))
        
        dx = abs(event.x_root - self.drag_data["start_x"])
        dy = abs(event.y_root - self.drag_data["start_y"])
        
        if dx > 5 or dy > 5:
            self.geometry(f"+{x}+{y}")
            
            if self.master and hasattr(self.master, 'move_main_window'):
                if x + self.winfo_width() > self.screen_width * 0.8:
                    self.master.move_main_window(x - self.master.master.winfo_width(), y)
                else:
                    self.master.move_main_window(x + self.winfo_width(), y)
        
        return "break"

class ChemistryTimer:
    def __init__(self, master):
        self.master = master
        
        self.icon = None
        self.tray_created = False
        
        self.async_drawing = False
        
        self.logger = Logger()
        self.resource_manager = ResourceManager()
        self.performance_monitor = PerformanceMonitor()
        self.state_manager = StateManager()
        
        Logger.info("化学计时器启")
        self.performance_monitor.start_measure("initialization")
        
        self.config = Config()
        Logger.info(f"加载配置: {self.config.config}")
        
        self.load_draw_records()
        Logger.info("尝试加载抽取记录")
        
        self.init_themes()
        
        self.copy_txt_files_to_config()
        
        master.title("化学计时器")
        master.overrideredirect(True)
        master.attributes('-alpha', self.config.get("opacity"))
        master.attributes('-topmost', True)
        master.wm_attributes("-toolwindow", True)
        master.geometry("600x450+230+200")
        
        self.screen_width = master.winfo_screenwidth()
        self.screen_height = master.winfo_screenheight()
        
        self.visible = True
        self.time_running1 = False
        self.time_running2 = False
        self.time_count1 = 0
        self.time_count2 = 0
        self.current_mode = "forward"
        self.last_selected_file = None
        
        self.create_main_frame()
        self.create_top_navbar()
        self.create_left_navbar()
        self.create_main_content()
        
        self.floating_ball = FloatingBall(master, size=50)
        self.floating_ball.master = self
        self.floating_ball.withdraw()
        
        self.bind_events()
        
        self.create_watermark()
        
        self.create_system_tray()
        
        duration = self.performance_monitor.end_measure("initialization")
        Logger.info(f"初始化完成，耗时: {duration:.3f}秒")
        
        self.check_updates_and_show_ball()
        
        try:
            import tkinterdnd2
            if not isinstance(self.master, tkinterdnd2.TkinterDnD.Tk):
                new_master = tkinterdnd2.TkinterDnD.Tk()
                new_master.withdraw()
                new_master.geometry(self.master.geometry())
                new_master.title(self.master.title())
                new_master.attributes('-alpha', self.master.attributes('-alpha'))
                new_master.attributes('-topmost', True)
                new_master.overrideredirect(True)
                new_master.wm_attributes("-toolwindow", True)
                self.master.destroy()
                self.master = new_master
            self.setup_drag_drop()
        except ImportError:
            Logger.error("tkinterdnd2 模块未安装，拖拽功能将不可用")
        except Exception as e:
            Logger.error(f"初始化拖拽功能失败: {e}")

        self.students_list = [
            "蔡克瑞", "张浩楠", "黄诗缘", "魏朵朵", "叶克勤", "董伟业", "林骁", "潘涛",
            "戴熙诺", "陈德宏", "林家琪", "杨媛媛", "黄通洋", "林孝杭", "王文耀", "吴浩南",
            "吴登豪", "陈语嫣", "陈杰", "陈如萌", "罗奥", "章子轩", "林雨婷", "顾诗棋",
            "王紫涵", "陈雨杭", "李紫歆", "冯灏", "周梓璇", "王豪", "杨子萱", "杨若琪",
            "王辰睿", "苏其烨", "唐文俐", "林依婷", "徐莹莹", "许欢", "方钦钦", "林国友",
            "戴恩钒", "吴连耀", "蒋贤通", "金理灿", "林继泉", "章连杰", "陈宥彬"
        ]
        
        self.student_records = {student: 0 for student in self.students_list}

    def copy_txt_files_to_config(self):
        try:
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            namelist_dir = os.path.join(config_dir, 'namelists')
            os.makedirs(namelist_dir, exist_ok=True)
            
            program_txt_files = [f for f in os.listdir(program_dir) if f.endswith('.txt')]
            config_txt_files = [f for f in os.listdir(namelist_dir) if f.endswith('.txt')]
            
            new_files = [f for f in program_txt_files if f not in config_txt_files]
            
            if new_files:
                for file_name in new_files:
                    src_path = os.path.join(program_dir, file_name)
                    dst_path = os.path.join(namelist_dir, file_name)
                    import shutil
                    shutil.copy2(src_path, dst_path)
                
                Logger.info(f"已复制 {len(new_files)} 个新的名单文件到配置目录")
            else:
                Logger.info("没有新的名单文件需要复制")
            
        except Exception as e:
            Logger.error(f"复制名单文失败: {e}")
    
    def get_txt_files(self):
        try:
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            namelist_dir = os.path.join(config_dir, 'namelists')
            os.makedirs(namelist_dir, exist_ok=True)
            txt_files = [f for f in os.listdir(namelist_dir) if f.endswith('.txt')]
            return txt_files
        except Exception as e:
            Logger.error(f"获取名单文件列表失败: {e}")
            return []
    
    def get_namelist_path(self, filename: str) -> str:
        config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
        namelist_dir = os.path.join(config_dir, 'namelists')
        return os.path.join(namelist_dir, filename)

    def create_main_frame(self):
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def bind_events(self):
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<ButtonRelease-1>", self.stop_move)
        self.master.bind("<B1-Motion>", self.do_move)
        
        self.master.bind("<FocusIn>", self.prevent_focus)
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        try:
            keyboard.on_press_key(self.config.get("hotkey"), self.handle_global_hotkey)
        except Exception as e:
            Logger.error(f"注册全局热键失败: {e}")

    def prevent_focus(self, event):
        if event.widget == self.master:
            self.master.focus_force()
            self.master.after(1, lambda: self.master.wm_attributes("-topmost", False))
            self.master.after(2, lambda: self.master.wm_attributes("-topmost", True))
        return "break"

    def init_themes(self):
        self.themes = {
            "默认蓝": {
                'nav': '#87CEEB',
                'bg': '#F0F0F0',
                'text': 'black',
                'left_nav': '#D3D3D3'
            },
            "深邃黑": {
                'nav': '#2C2C2C',
                'bg': '#1E1E1E',
                'text': '#FFFFFF',
                'left_nav': '#383838'
            },
            "清新绿": {
                'nav': '#90EE90',
                'bg': '#F0FFF0',
                'text': 'black',
                'left_nav': '#C1FFC1'
            },
            "暖阳橙": {
                'nav': '#FFA500',
                'bg': '#FFF5E6',
                'text': 'black',
                'left_nav': '#FFE4B5'
            },
            "梦幻紫": {
                'nav': '#DDA0DD',
                'bg': '#F5E6F5',
                'text': 'black',
                'left_nav': '#E6E6FA'
            },
            "海洋蓝": {
                'nav': '#4169E1',
                'bg': '#F0F8FF',
                'text': 'black',
                'left_nav': '#B0C4DE'
            },
            "樱花粉": {
                'nav': '#FFB6C1',
                'bg': '#FFF0F5',
                'text': 'black',
                'left_nav': '#FFC0CB'
            },
            "高级灰": {
                'nav': '#808080',
                'bg': '#F5F5F5',
                'text': 'black',
                'left_nav': '#A9A9A9'
            }
        }
        
        self.flash_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
        self.draw_flash_colors = ['#4169E1', '#1E90FF', '#00BFFF']
        self.flash_count = 0
        self.max_flashes = 45
        self.max_draw_flashes = 10
        self.audio_play_count = 0
        self.max_audio_plays = 5
        
        current_theme = self.config.get("theme")
        theme = self.themes[current_theme]
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
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
        
        self.master.configure(bg=theme['bg'])
        
        self.style.configure('Theme.TFrame', background=theme['bg'])
        self.style.configure('Theme.TLabel', 
                            background=theme['bg'],
                            foreground=theme['text'],
                            font=("Arial", 36))
        
        for color in self.flash_colors + self.draw_flash_colors:
            self.style.configure(f'Flash{color}.TFrame', background=color)
        
        self.style.configure('CalcNum.TButton', 
                            font=('Arial', 14),
                            padding=10,
                            width=6)
        self.style.configure('CalcOp.TButton',
                            font=('Arial', 14),
                            padding=10,
                            width=6,
                            background='#E8E8E8')
        self.style.configure('CalcFunc.TButton',
                            font=('Arial', 14),
                            padding=10,
                            width=6,
                            background='#D0D0D0')
        self.style.configure('CalcClear.TButton',
                            font=('Arial', 14),
                            padding=10,
                            width=6,
                            background='#FFB6C1')

        self.style.configure('Settings.TButton',
                            background='#4A90E2',
                            foreground='white',
                            font=('Arial', 12))
        
        self.style.configure('Theme.TFrame', background=theme['bg'])
        self.style.configure('Theme.TLabel', 
                            background=theme['bg'],
                            foreground=theme['text'],
                            font=("Arial", 36))
        
        if hasattr(self, 'async_window'):
            self.async_window.configure(bg=theme['bg'])
            self.async_window.flash_frame.configure(style='Theme.TFrame')
            self.async_window.content_frame.configure(style='Theme.TFrame')
            self.async_window.result_label.configure(style='Theme.TLabel')
            self.async_window.countdown_label.configure(
                style='Theme.TLabel',
                foreground='#FF4500'
            )

    def create_top_navbar(self):
        navbar = ttk.Frame(self.main_frame, style='TopNav.TFrame', height=50)
        navbar.pack(side=tk.TOP, fill=tk.X)
        navbar.pack_propagate(False)

        left_buttons_frame = ttk.Frame(navbar, style='TopNav.TFrame')
        left_buttons_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main_buttons = [
            ("计时器", self.show_forward_timer),
            ("随机抽签", self.show_random_draw),
        ]

        for text, command in main_buttons:
            ttk.Button(left_buttons_frame, text=text, command=command, style='TopNav.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X)

        control_frame = ttk.Frame(navbar, style='TopNav.TFrame')
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.style.configure('Active.TopNav.TButton', 
                            background='#DC143C',
                            foreground='white')

        self.topmost_button = ttk.Button(
            control_frame, 
            text="📌", 
            command=self.toggle_topmost, 
            style='Active.TopNav.TButton',
            width=2
        )
        self.topmost_button.pack(side=tk.LEFT, padx=(0, 2))

        ttk.Button(control_frame, 
                   text="⚙", 
                   command=self.show_settings, 
                   style='Settings.TButton',
                   width=2).pack(side=tk.LEFT, padx=(0, 2))
        self.hide_button = ttk.Button(control_frame, text="−", command=self.toggle_visibility, style='Hide.TButton', width=2)
        self.hide_button.pack(side=tk.LEFT, padx=(0, 2))

        self.update_label = ttk.Label(
            control_frame,
            text="发现新版本",
            foreground='#FF4500',
            cursor="hand2"
        )
        self.update_label.pack(side=tk.LEFT, padx=(0, 2))
        self.update_label.pack_forget()
        self.update_label.bind("<Button-1>", lambda e: self.show_update_dialog())

    def toggle_topmost(self):
        current_state = self.master.attributes('-topmost')
        new_state = not current_state
        self.master.attributes('-topmost', new_state)
        
        if new_state:
            self.topmost_button.configure(style='Active.TopNav.TButton')
        else:
            self.topmost_button.configure(style='TopNav.TButton')

    def create_left_navbar(self):
        self.left_navbar = ttk.Frame(self.main_frame, width=50, style='LeftNav.TFrame')
        self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)

        self.timer_buttons = ttk.Frame(self.left_navbar, style='TimerNav.TFrame')
        self.timer_buttons.pack(fill=tk.BOTH, expand=True)

        self.style.configure('TimerNav.TButton', 
                            font=('Arial', 16),
                            padding=5,
                            width=5)

        self.forward_timer_button = ttk.Button(self.timer_buttons, 
                                             text="正\n计\n时", 
                                             command=self.show_forward_timer, 
                                             style='TimerNav.TButton')
        self.forward_timer_button.pack(fill=tk.BOTH, expand=True)

        self.countdown_timer_button = ttk.Button(self.timer_buttons, 
                                                   text="倒\n计\n时", 
                                                   command=self.show_countdown_timer, 
                                                   style='TimerNav.TButton')
        self.countdown_timer_button.pack(fill=tk.BOTH, expand=True)

        self.master.after(10, self.adjust_button_heights)

    def adjust_button_heights(self):
        nav_height = self.left_navbar.winfo_height()

        button_height = nav_height // 2

        self.forward_timer_button.configure(style='TimerNav.TButton')
        self.countdown_timer_button.configure(style='TimerNav.TButton')

        self.style.configure('TimerNav.TButton', padding=(5, button_height//2))

    def create_main_content(self):
        self.main_content = ttk.Frame(self.main_frame)
        self.main_content.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.forward_timer_frame = self.create_forward_timer_frame()
        self.countdown_timer_frame = self.create_countdown_timer_frame()
        self.settings_frame = self.create_settings_frame()
        
        if self.forward_timer_frame:
            self.forward_timer_frame.pack_forget()
        if self.countdown_timer_frame:
            self.countdown_timer_frame.pack_forget()
        if self.settings_frame:
            self.settings_frame.pack_forget()

        self.show_forward_timer()

    def create_forward_timer_frame(self):
        frame = ttk.Frame(self.main_content)
        
        timers_frame = ttk.Frame(frame)
        timers_frame.pack(expand=True, fill=tk.BOTH)

        timer1_frame = ttk.Frame(timers_frame)
        timer1_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH, pady=(0, 10))
        
        self.time_label1 = ttk.Label(timer1_frame, text="00:00.000", font=("Arial", 64))
        self.time_label1.pack(expand=True)

        button_frame1 = ttk.Frame(timer1_frame)
        button_frame1.pack(pady=(0, 10))

        self.start_stop_button1 = ttk.Button(button_frame1, text="开始", command=lambda: self.toggle_timer(1), width=10, style='Green.TButton')
        self.start_stop_button1.pack(side=tk.LEFT, padx=5)

        self.reset_button1 = ttk.Button(button_frame1, text="重置", command=lambda: self.reset_timer(1), width=10)
        self.reset_button1.pack(side=tk.LEFT, padx=5)

        separator = ttk.Separator(timers_frame, orient='horizontal')
        separator.pack(fill='x', pady=10)
        
        timer2_frame = ttk.Frame(timers_frame)
        timer2_frame.pack(side=tk.BOTTOM, expand=True, fill=tk.BOTH, pady=(10, 0))
        
        self.time_label2 = ttk.Label(timer2_frame, text="00:00.000", font=("Arial", 64))
        self.time_label2.pack(expand=True)

        button_frame2 = ttk.Frame(timer2_frame)
        button_frame2.pack(pady=(10, 0))

        self.start_stop_button2 = ttk.Button(button_frame2, text="开始", command=lambda: self.toggle_timer(2), width=10, style='Green.TButton')
        self.start_stop_button2.pack(side=tk.LEFT, padx=5)

        self.reset_button2 = ttk.Button(button_frame2, text="重置", command=lambda: self.reset_timer(2), width=10)
        self.reset_button2.pack(side=tk.LEFT, padx=5)

        return frame

    def create_countdown_timer_frame(self):
        frame = ttk.Frame(self.main_content)

        selector_frame = ttk.Frame(frame)
        selector_frame.pack(pady=(20, 10))

        self.minute_spinner = ScrollableSpinbox(selector_frame)
        self.minute_spinner.pack(side=tk.LEFT, padx=2)

        ttk.Label(selector_frame, text=":", font=("Arial", 36)).pack(side=tk.LEFT)

        self.second_spinner = ScrollableSpinbox(selector_frame)
        self.second_spinner.pack(side=tk.LEFT, padx=2)

        self.countdown_label = ttk.Label(frame, text="00:00", font=("Arial", 88))
        self.countdown_label.pack(pady=20)

        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)

        self.start_stop_countdown_button = ttk.Button(button_frame, text="开始", command=self.toggle_countdown, width=10, style='Green.TButton')
        self.start_stop_countdown_button.pack(side=tk.LEFT, padx=5)

        self.reset_countdown_button = ttk.Button(button_frame, text="重置", command=self.reset_countdown, width=10)
        self.reset_countdown_button.pack(side=tk.LEFT, padx=5)

        preset_frame = ttk.Frame(frame)
        preset_frame.pack(pady=20)

        self.accumulate_var = tk.BooleanVar()
        accumulate_switch = ttk.Checkbutton(preset_frame, text="累加", variable=self.accumulate_var, style='TCheckbutton')
        accumulate_switch.pack(side=tk.LEFT, padx=(0, 20))

        presets = [("10秒", 10), ("30秒", 30), ("1分钟", 60), ("2分钟", 120)]
        for text, seconds in presets:
            ttk.Button(preset_frame, text=text, command=lambda s=seconds: self.set_preset(s), width=8).pack(side=tk.LEFT, padx=5)

        return frame

    def create_calculator_frame(self):
        frame = ttk.Frame(self.main_content)

        self.calc_display = ttk.Entry(frame, font=("Arial", 32), justify=tk.RIGHT)
        self.calc_display.pack(pady=10, padx=10, fill=tk.X)

        button_frame = ttk.Frame(frame)
        button_frame.pack(expand=True, fill=tk.BOTH)

        self.style.configure('CalcNum.TButton', 
                            font=('Arial', 16),
                            padding=10,
                            width=6,
                            background='#FFFFFF',
                            foreground='#000000')
                        
        self.style.configure('CalcOp.TButton',
                            font=('Arial', 16),
                            padding=10,
                            width=6,
                            background='#F0F0F0',
                            foreground='#000000')
                            
        self.style.configure('CalcFunc.TButton',
                            font=('Arial', 16),
                            padding=10,
                            width=6,
                            background='#E0E0E0',
                            foreground='#000000')
                            
        self.style.configure('CalcClear.TButton',
                            font=('Arial', 16),
                            padding=10,
                            width=6,
                            background='#FFB6C1',
                            foreground='#000000')

        buttons = [
            [('C', 'calc_clear', 'CalcClear.TButton'), ('±', 'calc_negate', 'CalcFunc.TButton'), ('%', 'calc_percent', 'CalcFunc.TButton'), ('÷', 'calc_divide', 'CalcOp.TButton')],
            [('7', 'calc_7', 'CalcNum.TButton'), ('8', 'calc_8', 'CalcNum.TButton'), ('9', 'calc_9', 'CalcNum.TButton'), ('×', 'calc_multiply', 'CalcOp.TButton')],
            [('4', 'calc_4', 'CalcNum.TButton'), ('5', 'calc_5', 'CalcNum.TButton'), ('6', 'calc_6', 'CalcNum.TButton'), ('−', 'calc_subtract', 'CalcOp.TButton')],
            [('1', 'calc_1', 'CalcNum.TButton'), ('2', 'calc_2', 'CalcNum.TButton'), ('3', 'calc_3', 'CalcNum.TButton'), ('+', 'calc_add', 'CalcOp.TButton')],
            [('0', 'calc_0', 'CalcNum.TButton'), ('.', 'calc_decimal', 'CalcNum.TButton'), ('=', 'calc_equals', 'CalcOp.TButton')]
        ]

        for row in buttons:
            row_frame = ttk.Frame(button_frame)
            row_frame.pack(expand=True, fill=tk.BOTH)
            for text, command, style in row:
                if text == '0':
                    ttk.Button(row_frame, text=text, command=getattr(self, command), style=style).pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=1, pady=1)
                else:
                    ttk.Button(row_frame, text=text, command=getattr(self, command), style=style).pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=1, pady=1)

        return frame

    def create_settings_frame(self):
        frame = ttk.Frame(self.main_content)

        scroll_frame = ttk.Frame(frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(scroll_frame, bg=self.style.lookup('TFrame', 'background'))
        scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.create_settings_content(self.scrollable_frame)

        return frame

    def create_settings_content(self, parent):
        settings = [
            ("透明度", "opacity", "scale", (0.1, 1.0, 0.1)),
            ("提示音", "sound_enabled", "check"),
            ("主题", "theme", "combo", list(self.themes.keys())),
            ("抽签速度", "draw_speed", "scale", (1.0, 20.0, 0.5)),
            ("全局热键", "hotkey", "entry"),
            ("总是允许快速抽签", "always_allow_quick_draw", "check"),
            ("异步抽签", "async_draw", "check"),
            ("异步抽签动画", "async_draw_animation", "check"),
            ("自动隐藏延迟", "hide_delay", "scale", (0.5, 10.0, 0.5)),
            ("总是自动隐藏", "always_auto_hide", "check"),
            ("倒计时自动隐藏", "countdown_auto_hide", "check"),
            ("显示水印", "show_watermark", "check"),
            ("快速初始化", "quick_init", "check"),
            ("GitHub Token", "github_token", "entry"),
            ("保存抽签记录", "save_draw_records", "check"),
        ]

        for i, (label, key, widget_type, *args) in enumerate(settings):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)

            if widget_type == "scale":
                min_val, max_val, step = args[0]
                current_val = tk.DoubleVar(value=self.config.get(key))
                scale = ttk.Scale(row, from_=min_val, to=max_val, orient=tk.HORIZONTAL, 
                                variable=current_val, command=lambda val, k=key: self.on_scale_change(k, float(val)))
                scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
                value_label = ttk.Label(row, text=str(current_val.get()), width=5)
                value_label.pack(side=tk.RIGHT, padx=(5, 0))
                current_val.trace_add("write", lambda *args, v=current_val, l=value_label: l.config(text=f"{v.get():.1f}"))

            elif widget_type == "check":
                var = tk.BooleanVar(value=self.config.get(key))
                check = ttk.Checkbutton(row, variable=var, command=lambda v=var, k=key: self.config.set(k, v.get()))
                check.pack(side=tk.LEFT)

            elif widget_type == "combo":
                var = tk.StringVar(value=self.config.get(key))
                combo = ttk.Combobox(row, textvariable=var, values=args[0], state="readonly")
                combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
                var.trace_add("write", lambda *args, v=var, k=key: self.on_combo_change(k, v.get()))

            elif widget_type == "entry":
                var = tk.StringVar(value=self.config.get(key))
                entry = ttk.Entry(row, textvariable=var, show="*" if "token" in key else None)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                var.trace_add("write", lambda *args, v=var, k=key: self.config.set(k, v.get()))

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=20)

        ttk.Button(button_frame, text="重置设置", command=self.reset_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="检查更新", command=self.check_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="打开日志目录", command=self.open_log_dir).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关于", command=self.show_about).pack(side=tk.RIGHT, padx=5)

    def on_scale_change(self, key, value):
        self.config.set(key, value)
        if key == "opacity":
            self.master.attributes('-alpha', value)

    def on_combo_change(self, key, value):
        self.config.set(key, value)
        if key == "theme":
            self.init_themes()
            self.refresh_ui()

    def refresh_ui(self):
        for widget in [self.main_frame, self.left_navbar, self.main_content]:
            if hasattr(widget, 'configure'):
                widget.configure(style='TFrame')

    def reset_settings(self):
        self.config.config = self.config.default_config.copy()
        self.config.save_config()
        self.init_themes()
        self.refresh_ui()
        self.show_settings()

    def check_update(self):
        has_update, latest_version, download_url = UpdateChecker.check_update()
        if has_update:
            self.show_update_dialog(latest_version, download_url)
        else:
            messagebox.showinfo("检查更新", "当前已是最新版本！")

    def open_log_dir(self):
        log_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        os.startfile(log_dir)

    def show_about(self):
        about_text = f"""
化学计时器 {UpdateChecker.VERSION}

作者: SuangSue
邮箱: suangsue@outlook.com

功能特点:
• 正计时/倒计时
• 随机抽签
• 科学计算器
• 自定义主题
• 全局热键
• 系统托盘
• 悬浮球

感谢使用！
        """
        messagebox.showinfo("关于", about_text.strip())

    def show_forward_timer(self):
        self.hide_all_frames()
        if self.forward_timer_frame:
            self.forward_timer_frame.pack(expand=True, fill=tk.BOTH)
        self.current_mode = "forward"

    def show_countdown_timer(self):
        self.hide_all_frames()
        if self.countdown_timer_frame:
            self.countdown_timer_frame.pack(expand=True, fill=tk.BOTH)
        self.current_mode = "countdown"

    def show_random_draw(self):
        self.hide_all_frames()
        if not hasattr(self, 'random_draw_frame'):
            self.random_draw_frame = self.create_random_draw_frame()
        self.random_draw_frame.pack(expand=True, fill=tk.BOTH)
        self.current_mode = "random_draw"

    def show_calculator(self):
        self.hide_all_frames()
        if not hasattr(self, 'calculator_frame'):
            self.calculator_frame = self.create_calculator_frame()
        self.calculator_frame.pack(expand=True, fill=tk.BOTH)
        self.current_mode = "calculator"

    def show_settings(self):
        self.hide_all_frames()
        if self.settings_frame:
            self.settings_frame.pack(expand=True, fill=tk.BOTH)
        self.current_mode = "settings"

    def hide_all_frames(self):
        frames = [
            self.forward_timer_frame,
            self.countdown_timer_frame,
            self.settings_frame
        ]
        
        if hasattr(self, 'random_draw_frame'):
            frames.append(self.random_draw_frame)
        if hasattr(self, 'calculator_frame'):
            frames.append(self.calculator_frame)
            
        for frame in frames:
            if frame:
                frame.pack_forget()

    def toggle_timer(self, timer_num):
        if timer_num == 1:
            if not self.time_running1:
                self.time_running1 = True
                self.start_stop_button1.configure(text="停止", style='Red.TButton')
                self.update_timer1()
            else:
                self.time_running1 = False
                self.start_stop_button1.configure(text="开始", style='Green.TButton')
        else:
            if not self.time_running2:
                self.time_running2 = True
                self.start_stop_button2.configure(text="停止", style='Red.TButton')
                self.update_timer2()
            else:
                self.time_running2 = False
                self.start_stop_button2.configure(text="开始", style='Green.TButton')

    def update_timer1(self):
        if self.time_running1:
            self.time_count1 += 1
            minutes = self.time_count1 // 6000
            seconds = (self.time_count1 // 100) % 60
            milliseconds = self.time_count1 % 100
            self.time_label1.config(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")
            self.master.after(10, self.update_timer1)

    def update_timer2(self):
        if self.time_running2:
            self.time_count2 += 1
            minutes = self.time_count2 // 6000
            seconds = (self.time_count2 // 100) % 60
            milliseconds = self.time_count2 % 100
            self.time_label2.config(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")
            self.master.after(10, self.update_timer2)

    def reset_timer(self, timer_num):
        if timer_num == 1:
            self.time_running1 = False
            self.time_count1 = 0
            self.time_label1.config(text="00:00.000")
            self.start_stop_button1.configure(text="开始", style='Green.TButton')
        else:
            self.time_running2 = False
            self.time_count2 = 0
            self.time_label2.config(text="00:00.000")
            self.start_stop_button2.configure(text="开始", style='Green.TButton")

    def toggle_countdown(self):
        if not self.countdown_running:
            try:
                minutes = int(self.minute_spinner.get())
                seconds = int(self.second_spinner.get())
                self.countdown_total = minutes * 60 + seconds
                if self.countdown_total <= 0:
                    return
                
                self.countdown_running = True
                self.start_stop_countdown_button.configure(text="停止", style='Red.TButton')
                self.update_countdown()
            except ValueError:
                pass
        else:
            self.countdown_running = False
            self.start_stop_countdown_button.configure(text="开始", style='Green.TButton')

    def update_countdown(self):
        if self.countdown_running and self.countdown_total > 0:
            minutes = self.countdown_total // 60
            seconds = self.countdown_total % 60
            self.countdown_label.config(text=f"{minutes:02d}:{seconds:02d}")
            self.countdown_total -= 1
            self.master.after(1000, self.update_countdown)
        elif self.countdown_total <= 0:
            self.countdown_finished()

    def countdown_finished(self):
        self.countdown_running = False
        self.start_stop_countdown_button.configure(text="开始", style='Green.TButton')
        self.countdown_label.config(text="00:00")
        
        if self.config.get("sound_enabled"):
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        
        if self.config.get("countdown_auto_hide"):
            self.master.after(int(self.config.get("hide_delay") * 1000), self.toggle_visibility)

    def reset_countdown(self):
        self.countdown_running = False
        self.countdown_total = 0
        self.countdown_label.config(text="00:00")
        self.start_stop_countdown_button.configure(text="开始", style='Green.TButton')
        self.minute_spinner.set("00")
        self.second_spinner.set("00")

    def set_preset(self, seconds):
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        self.minute_spinner.set(f"{minutes:02d}")
        self.second_spinner.set(f"{remaining_seconds:02d}")

    def create_random_draw_frame(self):
        frame = ttk.Frame(self.main_content)

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_var = tk.StringVar()
        txt_files = self.get_txt_files()
        if txt_files:
            self.file_var.set(txt_files[0])
            self.last_selected_file = txt_files[0]
        else:
            self.file_var.set("无名单文件")
            
        file_combo = ttk.Combobox(top_frame, textvariable=self.file_var, values=txt_files, state="readonly")
        file_combo.pack(side=tk.LEFT, padx=(0, 10))
        file_combo.bind('<<ComboboxSelected>>', self.on_file_selected)

        self.reload_button = ttk.Button(top_frame, text="↻", command=self.reload_files, width=3)
        self.reload_button.pack(side=tk.LEFT, padx=(0, 10))

        self.quick_draw_var = tk.BooleanVar(value=self.config.get("always_allow_quick_draw"))
        quick_draw_check = ttk.Checkbutton(top_frame, text="快速抽签", variable=self.quick_draw_var)
        quick_draw_check.pack(side=tk.LEFT)

        self.draw_result_label = ttk.Label(frame, text="准备抽签", font=("Arial", 48))
        self.draw_result_label.pack(expand=True, fill=tk.BOTH)

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.draw_button = ttk.Button(button_frame, text="开始抽签", command=self.start_draw, width=15, style='Green.TButton')
        self.draw_button.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_draw, width=15, style='Red.TButton')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.stop_button.configure(state='disabled')

        ttk.Button(button_frame, text="查看记录", command=self.show_draw_records, width=15).pack(side=tk.LEFT, padx=5)

        self.draw_running = False
        self.draw_names = []
        self.current_draw_index = 0

        return frame

    def on_file_selected(self, event=None):
        selected_file = self.file_var.get()
        if selected_file != self.last_selected_file:
            self.last_selected_file = selected_file
            self.load_names_from_file()

    def reload_files(self):
        txt_files = self.get_txt_files()
        self.file_var.set("")
        file_combo = self.file_var._root.children['!combobox']
        file_combo['values'] = txt_files
        if txt_files:
            self.file_var.set(txt_files[0])
            self.last_selected_file = txt_files[0]
            self.load_names_from_file()

    def load_names_from_file(self):
        try:
            filename = self.file_var.get()
            if filename and filename != "无名单文件":
                filepath = self.get_namelist_path(filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.draw_names = [line.strip() for line in f if line.strip()]
                Logger.info(f"加载名单文件: {filename}, 共 {len(self.draw_names)} 个名字")
            else:
                self.draw_names = []
        except Exception as e:
            Logger.error(f"加载名单文件失败: {e}")
            self.draw_names = []

    def start_draw(self):
        if not self.draw_names:
            messagebox.showwarning("警告", "请先选择有效的名单文件！")
            return

        if self.config.get("async_draw"):
            self.start_async_draw()
        else:
            self.start_normal_draw()

    def start_normal_draw(self):
        self.draw_running = True
        self.draw_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.current_draw_index = 0
        
        if self.quick_draw_var.get():
            self.quick_draw()
        else:
            self.normal_draw()

    def normal_draw(self):
        if self.draw_running:
            name = random.choice(self.draw_names)
            self.draw_result_label.config(text=name)
            
            speed = self.config.get("draw_speed")
            delay = max(1, int(1000 / speed))
            
            self.master.after(delay, self.normal_draw)

    def quick_draw(self):
        if self.draw_running:
            name = random.choice(self.draw_names)
            self.draw_result_label.config(text=name)
            
            self.current_draw_index += 1
            speed = self.config.get("draw_speed")
            
            if self.current_draw_index < 20:
                delay = max(1, int(1000 / speed))
                self.master.after(delay, self.quick_draw)
            else:
                self.finalize_draw(name)

    def start_async_draw(self):
        if not hasattr(self, 'async_window') or not self.async_window.winfo_exists():
            self.async_window = AsyncDrawWindow(self.master, self)
        
        self.async_window.start_draw(self.draw_names)

    def stop_draw(self):
        self.draw_running = False
        self.draw_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        
        if not self.quick_draw_var.get() and self.draw_result_label['text'] != "准备抽签":
            final_name = self.draw_result_label['text']
            self.finalize_draw(final_name)

    def finalize_draw(self, name):
        self.draw_result_label.config(text=name)
        self.draw_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        self.draw_running = False
        
        if self.config.get("sound_enabled"):
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        
        self.record_draw_result(name)
        
        if self.config.get("always_auto_hide"):
            self.master.after(int(self.config.get("hide_delay") * 1000), self.toggle_visibility)

    def record_draw_result(self, name):
        if not self.config.get("save_draw_records"):
            return
            
        try:
            record_file = os.path.join(self.config.config_dir, "draw_records.txt")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(record_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {name}\n")
                
            Logger.info(f"记录抽签结果: {name}")
        except Exception as e:
            Logger.error(f"记录抽签结果失败: {e}")

    def load_draw_records(self):
        try:
            record_file = os.path.join(self.config.config_dir, "draw_records.txt")
            if os.path.exists(record_file):
                with open(record_file, 'r', encoding='utf-8') as f:
                    self.draw_records = [line.strip() for line in f if line.strip()]
            else:
                self.draw_records = []
        except Exception as e:
            Logger.error(f"加载抽签记录失败: {e}")
            self.draw_records = []

    def show_draw_records(self):
        records_window = tk.Toplevel(self.master)
        records_window.title("抽签记录")
        records_window.geometry("400x500")
        records_window.attributes('-topmost', True)
        
        text_frame = ttk.Frame(records_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(text_frame, yscrollcommand=scrollbar.set, font=("Arial", 12))
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        if self.draw_records:
            for record in reversed(self.draw_records[-100:]):
                text_widget.insert(tk.END, record + '\n')
        else:
            text_widget.insert(tk.END, "暂无抽签记录")
        
        text_widget.config(state=tk.DISABLED)
        
        button_frame = ttk.Frame(records_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="清空记录", command=lambda: self.clear_draw_records(text_widget)).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="关闭", command=records_window.destroy).pack(side=tk.RIGHT)

    def clear_draw_records(self, text_widget):
        try:
            record_file = os.path.join(self.config.config_dir, "draw_records.txt")
            if os.path.exists(record_file):
                os.remove(record_file)
            self.draw_records = []
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "暂无抽签记录")
            text_widget.config(state=tk.DISABLED)
            Logger.info("抽签记录已清空")
        except Exception as e:
            Logger.error(f"清空抽签记录失败: {e}")

    def calc_clear(self):
        self.calc_display.delete(0, tk.END)

    def calc_negate(self):
        current = self.calc_display.get()
        if current and current[0] == '-':
            self.calc_display.delete(0)
        elif current:
            self.calc_display.insert(0, '-')

    def calc_percent(self):
        try:
            current = float(self.calc_display.get())
            result = current / 100
            self.calc_display.delete(0, tk.END)
            self.calc_display.insert(0, str(result))
        except:
            pass

    def calc_divide(self):
        self.calc_operation('÷')

    def calc_multiply(self):
        self.calc_operation('×')

    def calc_subtract(self):
        self.calc_operation('−')

    def calc_add(self):
        self.calc_operation('+')

    def calc_operation(self, op):
        self.calc_prev = self.calc_display.get()
        self.calc_op = op
        self.calc_display.delete(0, tk.END)

    def calc_equals(self):
        try:
            current = self.calc_display.get()
            if hasattr(self, 'calc_prev') and hasattr(self, 'calc_op'):
                prev = float(self.calc_prev)
                curr = float(current)
                
                if self.calc_op == '+':
                    result = prev + curr
                elif self.calc_op == '−':
                    result = prev - curr
                elif self.calc_op == '×':
                    result = prev * curr
                elif self.calc_op == '÷':
                    result = prev / curr if curr != 0 else "错误"
                else:
                    result = curr
                
                self.calc_display.delete(0, tk.END)
                self.calc_display.insert(0, str(result))
        except:
            self.calc_display.delete(0, tk.END)
            self.calc_display.insert(0, "错误")

    def calc_decimal(self):
        current = self.calc_display.get()
        if '.' not in current:
            self.calc_display.insert(tk.END, '.')

    def calc_number(self, num):
        current = self.calc_display.get()
        if current == "0" or current == "错误":
            self.calc_display.delete(0, tk.END)
        self.calc_display.insert(tk.END, str(num))

    def calc_0(self): self.calc_number(0)
    def calc_1(self): self.calc_number(1)
    def calc_2(self): self.calc_number(2)
    def calc_3(self): self.calc_number(3)
    def calc_4(self): self.calc_number(4)
    def calc_5(self): self.calc_number(5)
    def calc_6(self): self.calc_number(6)
    def calc_7(self): self.calc_number(7)
    def calc_8(self): self.calc_number(8)
    def calc_9(self): self.calc_number(9)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        if hasattr(self, 'x') and hasattr(self, 'y'):
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.master.winfo_x() + deltax
            y = self.master.winfo_y() + deltay
            self.master.geometry(f"+{x}+{y}")

    def toggle_visibility(self):
        if self.visible:
            self.master.withdraw()
            self.floating_ball.deiconify()
            self.visible = False
        else:
            self.master.deiconify()
            self.floating_ball.withdraw()
            self.visible = True

    def move_main_window(self, x, y):
        if self.visible:
            self.master.geometry(f"+{x}+{y}")

    def create_watermark(self):
        if not self.config.get("show_watermark"):
            return
            
        watermark = tk.Label(self.master, text="化学计时器", 
                           font=("Arial", 8), fg="gray", bg=self.style.lookup('TFrame', 'background'))
        watermark.place(relx=1.0, rely=1.0, anchor='se', x=-2, y=-2)

    def create_system_tray(self):
        try:
            def create_image():
                image = Image.new('RGB', (64, 64), color='white')
                dc = ImageDraw.Draw(image)
                dc.rectangle([0, 0, 63, 63], fill='lightblue')
                dc.text((32, 32), "CT", fill='black', anchor='mm')
                return image

            image = create_image()
            
            menu = pystray.Menu(
                pystray.MenuItem("显示/隐藏", self.toggle_visibility, default=True),
                pystray.MenuItem("退出", self.quit_app)
            )
            
            self.icon = pystray.Icon("chemistry_timer", image, "化学计时器", menu)
            
            def run_icon():
                try:
                    self.icon.run()
                except Exception as e:
                    print(f"系统托盘错误: {e}")
            
            tray_thread = threading.Thread(target=run_icon, daemon=True)
            tray_thread.start()
            self.tray_created = True
            
        except Exception as e:
            print(f"创建系统托盘失败: {e}")

    def quit_app(self):
        if self.icon:
            self.icon.stop()
        self.master.quit()
        self.master.destroy()

    def on_closing(self):
        self.toggle_visibility()

    def handle_global_hotkey(self, event):
        if event.event_type == keyboard.KEY_DOWN:
            self.toggle_visibility()

    def check_updates_and_show_ball(self):
        def check():
            has_update, latest_version, download_url = UpdateChecker.check_update()
            if has_update:
                self.master.after(0, lambda: self.show_update_notification(latest_version, download_url))
        
        threading.Thread(target=check, daemon=True).start()

    def show_update_notification(self, latest_version, download_url):
        self.update_label.pack(side=tk.LEFT, padx=(0, 2))
        self.floating_ball.deiconify()

    def show_update_dialog(self, latest_version=None, download_url=None):
        if not latest_version:
            has_update, latest_version, download_url = UpdateChecker.check_update()
            if not has_update:
                messagebox.showinfo("检查更新", "当前已是最新版本！")
                return
        
        result = messagebox.askyesno(
            "发现新版本", 
            f"发现新版本 {latest_version}！\n是否立即下载更新？",
            detail=f"当前版本: {UpdateChecker.VERSION}"
        )
        
        if result and download_url:
            webbrowser.open(download_url)

    def setup_drag_drop(self):
        try:
            import tkinterdnd2
            self.master.drop_target_register(tkinterdnd2.DND_FILES)
            self.master.dnd_bind('<<Drop>>', self.on_file_drop)
        except Exception as e:
            Logger.error(f"设置拖拽功能失败: {e}")

    def on_file_drop(self, event):
        try:
            files = event.data
            if files:
                file_path = files.strip('{}')
                if file_path.lower().endswith('.txt'):
                    self.process_dropped_file(file_path)
        except Exception as e:
            Logger.error(f"处理拖拽文件失败: {e}")

    def process_dropped_file(self, file_path):
        try:
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            namelist_dir = os.path.join(config_dir, 'namelists')
            os.makedirs(namelist_dir, exist_ok=True)
            
            filename = os.path.basename(file_path)
            dst_path = os.path.join(namelist_dir, filename)
            
            import shutil
            shutil.copy2(file_path, dst_path)
            
            self.reload_files()
            self.file_var.set(filename)
            self.load_names_from_file()
            
            Logger.info(f"已添加名单文件: {filename}")
            messagebox.showinfo("成功", f"已成功添加名单文件: {filename}")
            
        except Exception as e:
            Logger.error(f"处理拖拽文件失败: {e}")
            messagebox.showerror("错误", f"添加名单文件失败: {e}")

class AsyncDrawWindow(tk.Toplevel):
    def __init__(self, master, main_app):
        super().__init__(master)
        self.main_app = main_app
        self.draw_running = False
        self.configure(bg=main_app.style.lookup('TFrame', 'background'))
        
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.95)
        self.geometry("400x300+500+300")
        
        self.flash_frame = ttk.Frame(self, width=400, height=300)
        self.flash_frame.pack(fill=tk.BOTH, expand=True)
        
        self.content_frame = ttk.Frame(self)
        self.content_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        self.result_label = ttk.Label(self.content_frame, text="", font=("Arial", 48))
        self.result_label.pack()
        
        self.countdown_label = ttk.Label(self.content_frame, text="", font=("Arial", 24))
        self.countdown_label.pack()
        
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)
        
        self.flash_count = 0
        self.max_flashes = 45
        
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
        
    def do_move(self, event):
        if hasattr(self, 'x') and hasattr(self, 'y'):
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.winfo_x() + deltax
            y = self.winfo_y() + deltay
            self.geometry(f"+{x}+{y}")
    
    def start_draw(self, names):
        self.names = names
        self.draw_running = True
        self.flash_count = 0
        self.deiconify()
        
        if self.main_app.config.get("async_draw_animation"):
            self.animate_draw()
        else:
            self.simple_draw()
    
    def simple_draw(self):
        if self.draw_running and self.flash_count < 20:
            name = random.choice(self.names)
            self.result_label.config(text=name)
            self.flash_count += 1
            speed = self.main_app.config.get("draw_speed")
            delay = max(1, int(1000 / speed))
            self.after(delay, self.simple_draw)
        else:
            self.finalize_draw()
    
    def animate_draw(self):
        if self.draw_running and self.flash_count < self.max_flashes:
            name = random.choice(self.names)
            self.result_label.config(text=name)
            
            if self.flash_count < self.max_flashes - 10:
                color = random.choice(self.main_app.draw_flash_colors)
                self.flash_frame.configure(style=f'Flash{color}.TFrame')
            else:
                progress = self.flash_count - (self.max_flashes - 10)
                countdown = 10 - progress
                self.countdown_label.config(text=str(countdown))
            
            self.flash_count += 1
            
            if self.flash_count < self.max_flashes - 20:
                speed = self.main_app.config.get("draw_speed") * 0.8
            elif self.flash_count < self.max_flashes - 10:
                speed = self.main_app.config.get("draw_speed") * 0.6
            else:
                speed = self.main_app.config.get("draw_speed") * 0.4
                
            delay = max(1, int(1000 / speed))
            self.after(delay, self.animate_draw)
        else:
            self.finalize_draw()
    
    def finalize_draw(self):
        final_name = random.choice(self.names)
        self.result_label.config(text=final_name)
        self.countdown_label.config(text="")
        self.flash_frame.configure(style='Theme.TFrame')
        
        if self.main_app.config.get("sound_enabled"):
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        
        self.main_app.record_draw_result(final_name)
        
        if self.main_app.config.get("always_auto_hide"):
            self.after(int(self.main_app.config.get("hide_delay") * 1000), self.withdraw)

class ResourceManager:
    def __init__(self):
        self.resources = {}
        
    def load_image(self, path):
        if path in self.resources:
            return self.resources[path]
            
        try:
            image = Image.open(path)
            self.resources[path] = image
            return image
        except Exception as e:
            Logger.error(f"加载图片失败: {path}, 错误: {e}")
            return None
            
    def cleanup(self):
        self.resources.clear()

def main():
    single_instance = SingleInstance()
    if single_instance.already_running():
        if single_instance.activate_running_instance():
            print("程序已在运行中，已激活现有窗口")
            sys.exit(0)
        else:
            print("程序已在运行中，但无法激活窗口")
            sys.exit(1)
    
    root = tk.Tk()
    
    try:
        import tkinterdnd2
        root = tkinterdnd2.TkinterDnD.Tk()
    except ImportError:
        pass
    
    app = ChemistryTimer(root)
    
    def on_closing():
        if hasattr(app, 'icon') and app.icon:
            app.icon.stop()
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_closing()
    except Exception as e:
        Logger.error(f"程序运行错误: {e}")
        on_closing()

if __name__ == "__main__":
    try:
        # 尝试使用 TkinterDnD.Tk
        import tkinterdnd2
        root = tkinterdnd2.TkinterDnD.Tk()
    except ImportError:
        # 如果没有 tkinterdnd2，使用普通的 Tk
        root = tk.Tk()
    except Exception as e:
        # 其他错误时也使用普通的 Tk
        Logger.error(f"初始化 TkinterDnD 失败: {e}")
        root = tk.Tk()

    root.withdraw()
    
    # 显示启动窗口
    splash = SplashScreen(root)
    splash.update()

    try:
        # 初始化主程序
        timer = ChemistryTimer(root)
        
        # 设置窗口关闭处理
        root.protocol("WM_DELETE_WINDOW", timer.on_closing)
        
        # 根据快速初始化设置决定等待时间
        if splash.quick_init:
            wait_time = 50
        else:
            # 确保进度条完全读满
            while splash.progress['value'] < 100:
                splash.update()
                time.sleep(0.01)
            wait_time = 500

        def show_main_window():
            splash.destroy()
            # 显示浮球
            timer.floating_ball.deiconify()
            timer.floating_ball.lift()
            
        root.after(wait_time, show_main_window)
        
        # 开始循环
        root.mainloop()
        
    except Exception as e:
        # 如果发生错误确保启动窗口被销毁
        if splash:
            splash.destroy()
        # 显示错误消息
        messagebox.showerror("启动错误", f"程序启动时发生错误：\n{str(e)}")
        sys.exit(1)


