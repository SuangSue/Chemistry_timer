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
from datetime import datetime, timedelta
from typing import Optional, Any, Tuple
import functools
import requests
import webbrowser
from tkinter import filedialog  # 添加此行以支持文件选择对话框

try:
    import tkinterdnd2
except ImportError:
    pass

# 将 UpdateChecker 类修改如下
class UpdateChecker:
    """更新检查类"""
    
    VERSION = "V5.2"  # 当前版本号
    UPDATE_URL = "https://api.github.com/repos/SuangSue/Chemistry_timer/releases/latest"
    
    @classmethod
    def check_update(cls) -> Tuple[bool, str, str]:
        """检查更新"""
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Chemistry-Timer-App'
            }
            
            # 从配置文件获取token
            config = Config()
            github_token = config.get("github_token")
            
            if github_token:
                headers['Authorization'] = f'Bearer {github_token}'
                os.environ['GITHUB_TOKEN'] = github_token  # 同步到环境变量
            
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
        """比较版本号
        
        Args:
            v1: 版本号1（最新版本）
            v2: 版本号2（当前版本）
            
        Returns:
            bool: 如果v1 > v2返回True
        """
        def normalize(v):
            # 移除 'V' 并分版本号
            v = v.upper().lstrip('V')
            parts = [int(x) for x in v.split('.')]
            # 确保至少有两个部分
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
    """日志管理类"""
    
    def __init__(self):
        # 创建日志目录
        log_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志文件名
        log_file = os.path.join(log_dir, f'chemistry_timer_{datetime.now().strftime("%Y%m%d")}.log')
        
        # 创建日志格式器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)  # 明确指定输出到 stdout
        console_handler.setFormatter(formatter)
        
        # 获取日志记录器（修复获取日志记录器）
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # 清除所有的处理器
        logger.handlers.clear()
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 防止日志传播到父记录器
        logger.propagate = False
    
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
        """记录调试志"""
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
            "github_token": "",  # 添加这一行
            "punishment_end_time": "",
            "deleted_students": {},  # 添加新字段，用于记录被删除的学生
            "save_draw_records": True,  # 添加新的配置项，默认为开启
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
            print(f"加载配置文件失败: {e}")  # 修复"加载配置件失败"
            self.config = self.default_config

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置文件失败: {e}")  # 修复"保存置文件失败"

    def get(self, key, default=None):  # 修改这里，添加默认参数
        """获取配置值，如果不存在则返回默认值"""
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
        """激活已有实例"""  # 修复"激活已例"
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
            
            # 如果没有找到可见窗口，尝试查找系统托盘
            def find_tray_window(hwnd, windows):
                if "化学计时器" in win32gui.GetWindowText(hwnd):
                    windows.append(hwnd)
                return True
                
            tray_windows = []
            win32gui.EnumWindows(find_tray_window, tray_windows)
            
            if tray_windows:
                # 发送自定义消息给存在的实例
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
        """鼠标按下时记录起始位"""
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
        
        # 如果动距离小于阈值（5像素），认为是点击而不是拖动
        if dx < 5 and dy < 5 and hasattr(self.master, 'toggle_visibility'):
            self.master.toggle_visibility()
            
        # 重置点击状态
        self.drag_data["clicked"] = False
        return "break"  # 阻止事件继续传播

    def on_drag(self, event):
        """处理拖动事件"""  # 修复"处拖事件"
        # 如果已经开始拖动，取消点击状态  # 修复"取消点击态"
        self.drag_data["clicked"] = False
        
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        
        # 保不出屏幕
        x = max(0, min(x, self.screen_width - self.winfo_width()))
        y = max(0, min(y, self.screen_height - self.winfo_height()))
        
        # 计算移动距离
        dx = abs(event.x_root - self.drag_data["start_x"])
        dy = abs(event.y_root - self.drag_data["start_y"])
        
        # 只当移动距离超过阈值时才进行拖动
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
        self.async_drawing = False
        
        # 初始化基础组件
        self.logger = Logger()  # 先化系统
        self.resource_manager = ResourceManager()
        self.performance_monitor = PerformanceMonitor()
        self.state_manager = StateManager()
        
        # 记录启动
        Logger.info("化学计时器启动")
        self.performance_monitor.start_measure("initialization")
        
        # 初始化配置
        self.config = Config()
        Logger.info(f"加载配置: {self.config.config}")
        
        # 加载抽取记录（确保在初始化配置后立即加载）
        self.load_draw_records()
        Logger.info("尝试加载抽取记录")
        
        # 初始化主题
        self.init_themes()
        
        # 在志系统和主题初始化后再执行文件操作
        self.copy_txt_files_to_config()
        self.compare_namelists()
        
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
        
        # 建浮球但先不显示
        self.floating_ball = FloatingBall(master, size=50)
        self.floating_ball.master = self
        self.floating_ball.withdraw()  # 先隐藏浮球
        
        # 绑定事件
        self.bind_events()
        
        # 创建水印
        self.create_watermark()
        
        # 初始化系统托盘
        self.create_system_tray()
        
        # 记录初始化完成
        duration = self.performance_monitor.end_measure("initialization")
        Logger.info(f"初始化完成，耗时: {duration:.3f}秒")
        
        # 检查更新并在完成后示浮球
        self.check_updates_and_show_ball()
        
        # 在其他初始化之后添加
        try:
            # 导入tkinterdnd2模块
            import tkinterdnd2
            # 如果主窗口不是 TkinterDnD.Tk，则重新创建
            if not isinstance(self.master, tkinterdnd2.TkinterDnD.Tk):
                new_master = tkinterdnd2.TkinterDnD.Tk()
                new_master.withdraw()
                # 复制原窗口的属性
                new_master.geometry(self.master.geometry())
                new_master.title(self.master.title())
                new_master.attributes('-alpha', self.master.attributes('-alpha'))
                new_master.attributes('-topmost', True)
                new_master.overrideredirect(True)
                new_master.wm_attributes("-toolwindow", True)
                # 替换主窗口
                self.master.destroy()
                self.master = new_master
            # 设置拖拽能
            self.setup_drag_drop()
        except ImportError:
            Logger.error("tkinterdnd2 模块未安装，拖拽功能将不可用")
        except Exception as e:
            Logger.error(f"初始化拖拽功能失败: {e}")

    def copy_txt_files_to_config(self):
        """复制程序目录下的新的txt文件到配置目录"""
        try:
            # 获取程序目录
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            # 取配置目录
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            # 创建名单文件
            namelist_dir = os.path.join(config_dir, 'namelists')
            os.makedirs(namelist_dir, exist_ok=True)
            
            # 获取程序目录和配置目录中的txt文件列表
            program_txt_files = [f for f in os.listdir(program_dir) if f.endswith('.txt')]
            config_txt_files = [f for f in os.listdir(namelist_dir) if f.endswith('.txt')]
            
            # 找出需要复制的新文件
            new_files = [f for f in program_txt_files if f not in config_txt_files]
            
            # 复制新文件
            if new_files:
                for file_name in new_files:
                    src_path = os.path.join(program_dir, file_name)
                    dst_path = os.path.join(namelist_dir, file_name)
                    import shutil
                    shutil.copy2(src_path, dst_path)
                
                Logger.info(f"已复制 {len(new_files)} 个新的单文件到配置目录")
            else:
                Logger.info("没有新的名单文件需要复制")
            
        except Exception as e:
            Logger.error(f"复制名单文件失败: {e}")
    
    def get_txt_files(self):
        """获取配置目录下的所有txt文"""
        try:
            # 使用配置目录
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            namelist_dir = os.path.join(config_dir, 'namelists')
            # 确保目录存在
            os.makedirs(namelist_dir, exist_ok=True)
            # 获取文列表
            txt_files = [f for f in os.listdir(namelist_dir) if f.endswith('.txt')]
            return txt_files
        except Exception as e:
            Logger.error(f"获取名单文件列表失败: {e}")
            return []
    
    def get_namelist_path(self, filename: str) -> str:
        """获取名单文件的完整路径"""
        config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
        namelist_dir = os.path.join(config_dir, 'namelists')
        return os.path.join(namelist_dir, filename)

    def create_main_frame(self):
        """创建主框架"""
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def bind_events(self):
        """绑定事件"""
        # 绑定窗口移动事
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<ButtonRelease-1>", self.stop_move)
        self.master.bind("<B1-Motion>", self.do_move)
        
        # 绑定焦点事件
        self.master.bind("<FocusIn>", self.prevent_focus)
        
        # 绑关闭事件
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
                'nav': '#90EE90',  # 绿色
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
                'bg': '#F5E6F5',   # 紫色
                'text': 'black',
                'left_nav': '#E6E6FA'
            },
            "海洋蓝": {
                'nav': '#4169E1',  # 皇
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
        
        # 在其他初始化代添加闪烁相关变量
        self.flash_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
        self.draw_flash_colors = ['#4169E1', '#1E90FF', '#00BFFF']
        self.flash_count = 0
        self.max_flashes = 45
        self.max_draw_flashes = 10
        self.audio_play_count = 0
        self.max_audio_plays = 5
        
        # 获取当前主题
        current_theme = self.config.get("theme")
        theme = self.themes[current_theme]
        
        # 修改式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 使用保存的样式
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
        
        # 配置主窗背景色
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
        
        # 添加计算器按钮样式
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
                            background='#FFB6C1')  # 红色

        # 在 init_themes 方法中添加设置按钮样式
        self.style.configure('Settings.TButton',
                            background='#4A90E2',  # 使用蓝色背景
                            foreground='white',    # 白色文字
                            font=('Arial', 12))    # 调整体大小
        
        # 配置异步窗口样式
        self.style.configure('Theme.TFrame', background=theme['bg'])
        self.style.configure('Theme.TLabel', 
                            background=theme['bg'],
                            foreground=theme['text'],
                            font=("Arial", 36))
        
        # 如果异步窗口已存在，更新其样式
        if hasattr(self, 'async_window'):
            self.async_window.configure(bg=theme['bg'])
            self.async_window.flash_frame.configure(style='Theme.TFrame')
            self.async_window.content_frame.configure(style='Theme.TFrame')
            self.async_window.result_label.configure(style='Theme.TLabel')
            self.async_window.countdown_label.configure(
                style='Theme.TLabel',
                foreground='#FF4500'
            )

        # 添加化学资料按钮样式
        self.style.configure('Resource.TButton',
                            font=('Arial', 14),
                            padding=10)

        # 添加工具导航栏样式
        self.style.configure('ToolsNav.TFrame', background=theme['left_nav'])
        self.style.configure('ToolsNav.TButton', 
                            background=theme['left_nav'],
                            foreground=theme['text'],
                            font=('Arial', 12),
                            padding=10)

    def create_top_navbar(self):
        navbar = ttk.Frame(self.main_frame, style='TopNav.TFrame', height=50)
        navbar.pack(side=tk.TOP, fill=tk.X)
        navbar.pack_propagate(False)

        # 创建左侧按钮框架，用于平分空间的按钮
        left_buttons_frame = ttk.Frame(navbar, style='TopNav.TFrame')
        left_buttons_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 修改主导航按钮
        main_buttons = [
            ("计时器", self.show_forward_timer),
            ("计算器", self.show_calculator),
            ("随机抽签", self.show_random_draw),
            ("化学资料", self.show_chemistry_resources),
            ("妙妙工具", self.show_tools_lab)  # 添加妙妙工具按钮
        ]

        for text, command in main_buttons:
            ttk.Button(left_buttons_frame, text=text, command=command, style='TopNav.TButton').pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 创建右侧控制按钮框架
        control_frame = ttk.Frame(navbar, style='TopNav.TFrame')
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 在创建控制按钮框架后，添加新的样式
        self.style.configure('Active.TopNav.TButton', 
                            background='#DC143C',  # 橙色背景
                            foreground='white')    # 白色文字

        # 添加置顶按（修改这里）
        self.topmost_button = ttk.Button(
            control_frame, 
            text="📌", 
            command=self.toggle_topmost, 
            style='Active.TopNav.TButton',  # 默认使用激活样式
            width=2
        )
        self.topmost_button.pack(side=tk.LEFT, padx=(0, 2))

        # 设置和最小化按钮
        ttk.Button(control_frame, 
                   text="⚙", 
                   command=self.show_settings, 
                   style='Settings.TButton',  # 使用新的样式
                   width=2).pack(side=tk.LEFT, padx=(0, 2))
        self.hide_button = ttk.Button(control_frame, text="−", command=self.toggle_visibility, style='Hide.TButton', width=2)
        self.hide_button.pack(side=tk.LEFT, padx=(0, 2))

        # 添加新版本提示标签（始隐藏）
        self.update_label = ttk.Label(
            control_frame,
            text="发现新版本",  # 修正为 "发现新版本"
            foreground='#FF4500',
            cursor="hand2"
        )
        self.update_label.pack(side=tk.LEFT, padx=(0, 2))
        self.update_label.pack_forget()  # 初始隐
        self.update_label.bind("<Button-1>", lambda e: self.show_update_dialog())

    def toggle_topmost(self):
        """切换窗口置顶状态"""
        current_state = self.master.attributes('-topmost')
        new_state = not current_state
        self.master.attributes('-topmost', new_state)
        
        # 更新按钮样式以显示当前态
        if new_state:
            self.topmost_button.configure(style='Active.TopNav.TButton')  # 使用橙色样式
        else:
            self.topmost_button.configure(style='TopNav.TButton')  # 恢复默样式

    def create_left_navbar(self):
        self.left_navbar = ttk.Frame(self.main_frame, width=50, style='LeftNav.TFrame')
        self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)

        self.timer_buttons = ttk.Frame(self.left_navbar, style='TimerNav.TFrame')
        self.timer_buttons.pack(fill=tk.BOTH, expand=True)

        # 修改按钮样式，增大字体大小
        self.style.configure('TimerNav.TButton', 
                            font=('Arial', 16),  # 字体从14增大到16
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
        # 获取左侧导航栏的高度
        nav_height = self.left_navbar.winfo_height()

        # 设置每个按钮高度为导航栏高度的一半
        button_height = nav_height // 2

        # 调整按钮的高度
        self.forward_timer_button.configure(style='TimerNav.TButton')
        self.countdown_timer_button.configure(style='TimerNav.TButton')

        # 建更新样
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
        self.chemistry_resources_frame = self.create_chemistry_resources_frame()
        
        # 初始隐藏所框架
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
        if self.chemistry_resources_frame:
            self.chemistry_resources_frame.pack_forget()

        self.show_forward_timer()

    def create_forward_timer_frame(self):
        frame = ttk.Frame(self.main_content)
        
        # 创个框架来容两个计时器
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

        # 创建滚动选
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

        # 设置按钮和累加开关
        preset_frame = ttk.Frame(frame)
        preset_frame.pack(pady=20)

        # 添加累加开关
        self.accumulate_var = tk.BooleanVar()
        accumulate_switch = ttk.Checkbutton(preset_frame, text="累加", variable=self.accumulate_var, style='TCheckbutton')
        accumulate_switch.pack(side=tk.LEFT, padx=(0, 20))  # 增加右间

        presets = [("10秒", 10), ("30秒", 30), ("1分钟", 60), ("2分钟", 120)]
        for text, seconds in presets:
            ttk.Button(preset_frame, text=text, command=lambda s=seconds: self.set_preset(s), width=8).pack(side=tk.LEFT, padx=5)

        return frame

    def create_calculator_frame(self):
        frame = ttk.Frame(self.main_content)

        # 创建计算器显示
        self.calc_display = ttk.Entry(frame, font=("Arial", 32), justify=tk.RIGHT)
        self.calc_display.pack(pady=10, padx=10, fill=tk.X)

        # 创建钮框架
        button_frame = ttk.Frame(frame)
        button_frame.pack(expand=True, fill=tk.BOTH)

        # 修改按钮样式置
        self.style.configure('CalcNum.TButton', 
                            font=('Arial', 16),  # 加大字号
                            padding=10,
                            width=6,
                            background='#FFFFFF',  # 白色背景
                            foreground='#000000')  # 黑色文字
                        
        self.style.configure('CalcOp.TButton',
                            font=('Arial', 16),  # 加大字号
                            padding=10,
                            width=6,
                            background='#E8E8E8',  # 浅灰色背景
                            foreground='#000000')  # 色文字
                        
        self.style.configure('CalcFunc.TButton',
                            font=('Arial', 16),  # 加大字号
                            padding=10,
                            width=6,
                            background='#D0D0D0',  # 深灰色背景
                            foreground='#000000')  # 黑色文字
                        
        self.style.configure('CalcClear.TButton',
                            font=('Arial', 16),  # 加大字号
                            padding=10,
                            width=6,
                            background='#FFB6C1',  # 浅红色背景
                            foreground='#000000')  # 黑色字

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
        # 替特殊符
        expression = expression.replace('^', '**').replace('π', 'math.pi').replace('e', 'math.e')
        # 添 math. 前缀数学函数
        for func in ['sin', 'cos', 'tan', 'sqrt', 'log', 'ln', 'abs']:
            expression = expression.replace(func, f'math.{func}')
        expression = expression.replace('ln', 'log')
        return eval(expression)

    def show_calculator(self):
        self.clear_main_content()
        
        # 保持左侧导航栏可见
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
            
            # 隐藏其他导航元素
            self.timer_buttons.pack_forget()
            if hasattr(self, 'record_frame'):
                self.record_frame.pack_forget()
    
        # 显示计算器框架
        self.calculator_frame.pack(expand=True, fill=tk.BOTH)

    def create_periodic_table_frame(self):
        # 创建main_content中而不是master
        frame = ttk.Frame(self.main_content)
        self.periodic_table_label = ttk.Label(frame)
        self.periodic_table_label.pack(expand=True, fill=tk.BOTH)
        return frame

    def show_periodic_table(self):
        self.clear_main_content()
        
        # 藏左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack_forget()
        
        # 隐藏所有子列表
        self.timer_buttons.pack_forget()
        self.record_frame.pack_forget() if hasattr(self, 'record_frame') else None
        
        # pack而是place来显示周期框架，设fill=tk.BOTH和expand=True
        self.periodic_table_frame.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
        self.load_periodic_table()
        
        # 提升显示优先级
        self.periodic_table_frame.lift()
        self.periodic_table_label.lift()

    def load_periodic_table(self):
        try:
            # 保存始图片以供调整大小使用
            self.original_image = Image.open("元素周期表.png")
            # 初载时调整图大小
            self.resize_periodic_table()
            # 确保元素周期表始终显示在最上层
            self.periodic_table_label.lift()
        except FileNotFoundError:
            self.periodic_table_label.config(text="未找到元素周期图片")
        except Exception as e:
            self.periodic_table_label.config(text=f"加载图片时发生错误: {e}")

    def show_forward_timer(self):
        self.clear_main_content()
        self.forward_timer_frame.pack(expand=True, fill=tk.BOTH)
        self.timer_buttons.pack(fill=tk.BOTH, expand=True)  # 显示计时导航栏

    def show_countdown_timer(self):
        self.clear_main_content()
        self.countdown_timer_frame.pack(expand=True, fill=tk.BOTH)
        self.timer_buttons.pack(fill=tk.BOTH, expand=True)  # 显计时器子导航栏

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
            milliseconds = int((self.time_count1 * 1000) % 1000)  # 添加缺少的右括号
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.time_label1.config(text=time_str)
            self.master.after(16, lambda: self.update_timer(1))  # 从 50ms 改为 16ms (约60fps)
        elif timer_id == 2 and self.time_running2:
            self.time_count2 = time.time() - self.start_time2
            minutes = int(self.time_count2 // 60)
            seconds = int(self.time_count2 % 60)
            milliseconds = int((self.time_count2 * 1000) % 1000) # 添加缺少的右括号
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.time_label2.config(text=time_str)
            self.master.after(16, lambda: self.update_timer(2))  # 从 50ms 改为 16ms (60fps)

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
            self.countdown_label.config(text="无输入")

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
            # 开始播放声音
            self.play_countdown_alarm()
            
            self.start_flashing()
            
            # 如果启用了自动隐藏，添加倒计时标签并始倒计时
            if self.config.get("countdown_auto_hide"):
                self.hide_countdown = ttk.Label(
                    self.countdown_timer_frame, 
                    text=f"{self.config.get('hide_delay'):.1f}", 
                    font=("Arial", 24, "bold"),
                    foreground='#FF4500'
                )
                self.hide_countdown.place(relx=1.0, rely=0, x=-20, y=20, anchor="ne")
                self.start_hide_countdown()

    def play_countdown_alarm(self):
        """倒计时结束播放声"""
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
        self.master.after(100, self.flash_window)  # 减少闪隔100毫秒

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
            # 如果累加开关打开，则累加时间
            new_total_seconds = current_total_seconds + seconds
        else:
            # 如果累开关关闭，则直设置为预设时间
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
            
            # 确保主不会出屏
            x = max(0, min(x, self.screen_width - self.master.winfo_width()))
            y = max(0, min(y, self.screen_height - self.master.winfo_height()))
            
            self.master.geometry(f"+{x}+{y}")
            
            # 据窗口更置
            if x < self.screen_width * 0.2:  # 口位于屏幕侧20%域时
                self.floating_ball.geometry(f"+{x+self.master.winfo_width()}+{y}")
            else:
                self.floating_ball.geometry(f"+{x-self.floating_ball.winfo_width()}+{y}")
            
            # 更新位置
            self.update_watermark_position()

    def toggle_visibility(self):
        if self.visible:
            self.master.withdraw()
            self.visible = False
        else:
            self.master.deiconify()
            self.visible = True
        
        # 确保浮球始可见
        self.floating_ball.lift()
        
        # 更新隐藏按钮的文本
        self.update_hide_button_text()

    def move_main_window(self, x, y):
        # 确保窗口移出幕
        x = max(0, min(x, self.screen_width - self.master.winfo_width()))
        y = max(0, min(y, self.screen_height - self.master.winfo_height()))
        
        self.master.geometry(f"+{x}+{y}")
        
        # 新水印位置
        self.update_watermark_position()

    # 添加新方法更新隐藏按钮的文本
    def update_hide_button_text(self):
        self.hide_button.config(text="□" if not self.visible else "−")  # 用方框符号示"示"

    # 添加以下方法到 ChemistryTimer 类：
    def update_current_time(self):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.current_time_label:
            self.current_time_label.config(text=current_time)
        self.master.after(1000, self.update_current_time)

    def on_closing(self):
        if not self.tray_created:  # 只有在系统托盘未创建时才创建
            self.master.withdraw()  # 隐藏主窗口
            self.floating_ball.withdraw()  # 隐藏浮
            self.create_system_tray()
        else:
            # 如果系统托盘已存在，只隐藏窗口
            self.master.withdraw()
            self.floating_ball.withdraw()

    def create_system_tray(self):
        """创建系统托盘图标"""  # 修复"创建统托盘图标"
        if self.tray_created:
            return
        
        try:
            # 获取图标路径
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.abspath(".")
            
            # 尝试加载图标  # 修复"尝载图标"
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
            # 创建新的盘图标
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
        
        
        
        

            # 使用守护线程运行图标  # 修复"运行标"
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
        """退出程序"""  # 修复"程序"
        try:
            # 保存抽取记录（确保在退出前保存）
            Logger.info("正在保存抽取记录...")
            self.save_draw_records()
            
            # 注热键
            keyboard.unhook_all()
            
            # 停止系统托盘图标  # 修复"止系统托盘图标"
            if self.icon:
                try:
                    self.icon.stop()
                except:
                    pass
                self.icon = None
                self.tray_created = False
            
            # 出程序
            self.master.quit()
            
        except Exception as e:
            Logger.error(f"退出程序时发生错误: {e}")
            self.master.quit()

    def create_watermark(self):
        """创建水印"""
        if self.config.get("show_watermark"):
            watermark_text = "钱高化学组×27届高一三班"
            self.watermark = tk.Label(self.master, 
                               text=watermark_text,
                               fg='#A0A0A0',  # 灰色文字
                               font=('Arial', 10),
                               bg=self.themes[self.config.get("theme")]['bg'])
            self.watermark.pack(side=tk.BOTTOM, anchor=tk.SE, padx=10, pady=10)

    def update_watermark_position(self):
        """更新水印位置"""
        if hasattr(self, 'watermark') and self.config.get("show_watermark"):
            self.master.update_idletasks()
            self.watermark.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

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
        
        # 取配置目录中的txt文件
        txt_files = self.get_txt_files()
        
        if not txt_files:
            # 创建提示框架
            hint_frame = ttk.Frame(self.random_draw_frame)
            hint_frame.pack(expand=True)
            
            # 提示标签
            ttk.Label(hint_frame, 
                     text="未找到名单文件!\n请在程序目录下创建'.txt'文件,\n每行输入一个学生姓名,\n并添加文件后重新启动程序!", 
                     font=("Arial", 14),
                     justify=tk.CENTER).pack(pady=20)  # 修复"学生名"为"学生姓名"
              
            # 打开目录按钮
            ttk.Button(hint_frame, 
                      text="打开程序目录", 
                      command=lambda: os.startfile(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)))
                      ).pack(pady=10)
            return

        # 创建文件选择框架
        select_frame = ttk.Frame(self.random_draw_frame)
        select_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(select_frame, text="选择名单：", font=('Arial', 12)).pack(side=tk.LEFT)
        
        # 使用配置目录中的文件
        initial_file = self.last_selected_file if self.last_selected_file in txt_files else txt_files[0]
        
        # 创建下拉选择框
        self.file_var = tk.StringVar(value=initial_file)
        file_combo = ttk.Combobox(select_frame, 
                                 textvariable=self.file_var,
                                 values=txt_files,
                                 state='readonly',
                                 width=30)
        file_combo.pack(side=tk.LEFT, padx=5)
        
        # 修改文件选择的响应
        def on_file_changed(event):
            selected_file = self.file_var.get()
            # 保存选择的文件
            self.last_selected_file = selected_file
            
            if not hasattr(self, 'file_records'):
                self.file_records = {}
            
            # 如果是新文件，初始化其记录
            if selected_file not in self.file_records:
                self.file_records[selected_file] = {}
                # 读取文件并初始化记录
                try:
                    file_path = self.get_namelist_path(selected_file)  # 使用配置目录中的文件
                    with open(file_path, "r", encoding="utf-8") as file:
                        self.students = file.read().strip().split("\n")
                        for student in self.students:
                            self.file_records[selected_file][student] = 0
                except Exception as e:
                    Logger.error(f"初始化记录失败: {e}")
            
            # 更新当前记录引用
            self.student_records = self.file_records[selected_file]
            # 立即更新显示
            self.update_record_display()
            # 重置显示文本
            if hasattr(self, 'draw_display'):
                self.draw_display.config(text="等待抽签...")
        
        file_combo.bind('<<ComboboxSelected>>', on_file_changed)
        
        # 初始化显示当前选择的文件记录
        on_file_changed(None)  # 手动触发一次更新
        
        # 创建重置按钮（如还没创建）
        if not hasattr(self, 'reset_records_button'):
            self.reset_records_button = ttk.Button(self.left_navbar, 
                                                 text="重置抽取记录", 
                                                 command=self.reset_records,
                                                 width=12)
        # 显重置按钮
        self.reset_records_button.pack(side=tk.TOP, pady=5)
        
        # 创建抽签面
        self.create_draw_interface()
        
        # 更新处罚状态显示
        self.update_punishment_status()

    def get_txt_files(self):
        """获取配置目录下的所有txt文件"""
        try:
            # 用配置目录
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            namelist_dir = os.path.join(config_dir, 'namelists')
            # 确保目录存在
            os.makedirs(namelist_dir, exist_ok=True)
            # 获取文件列表
            txt_files = [f for f in os.listdir(namelist_dir) if f.endswith('.txt')]
            return txt_files
        except Exception as e:
            Logger.error(f"获取名单文件列表失败: {e}")
            return []
    
    def get_namelist_path(self, filename: str) -> str:
        """获取名单文件的完整路径"""
        config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
        namelist_dir = os.path.join(config_dir, 'namelists')
        return os.path.join(namelist_dir, filename)

    def start_draw(self, count, force=False, auto_hide=False):
        # 加 auto_hide 参数传递给 update_draw
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
            file_path = self.get_namelist_path(selected_file)  # 使用新方法获取路
            
            # 为每文件创建立的记录字典
            if not hasattr(self, 'file_records'):
                self.file_records = {}
            
            # 果是新文件，初始化其记录
            if selected_file not in self.file_records:
                self.file_records[selected_file] = {}
            
            # 使用当前件的记录
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
            # 发生错误时也要置状
            self.is_drawing = False
            if hasattr(self, 'draw_one_button'):
                self.draw_one_button.configure(state='normal')
            if hasattr(self, 'draw_two_button'):
                self.draw_two_button.configure(state='normal')

    def update_draw(self, count, step=0, auto_hide=False):
        if step < 100:
            # 根据权重机制显示名字  # 修复"根据权重机显示名字"
            weights = self.calculate_weights()
            random_name = random.choices(self.students, weights=weights, k=1)[0]
            
            self.draw_display.config(text=random_name)
            self.progress['value'] = step
            
            # 使用配置的速度  # 修复"使用配置的速"
            speed = self.config.get("draw_speed")
            self.master.after(50, lambda: self.update_draw(count, step + speed, auto_hide))
        else:
            # 最终抽取结果处理
            weights = self.calculate_weights()
            if count == 1:
                selected_students = [random.choices(self.students, weights=weights, k=1)[0]]  # 修改这里，使用列表包装
            else:
                # 抽不同的学生
                selected_students = []
                remaining_students = self.students.copy()
                remaining_weights = weights.copy()
                
                for _ in range(count):
                    if not remaining_students:  # 果没有余学生可选  # 修复"果没有余学生可选"
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
            
            # 新显示（修这里，使用空格分）
            self.draw_display.config(text=" ".join(selected_students))
            self.progress['value'] = 100
            
            # 更新记录
            selected_file = self.file_var.get()
            self.file_records[selected_file] = self.student_records
            
            # 立即保存记录到文件（添加这一行）
            self.save_draw_records()
            
            # 更新记录显示
            if hasattr(self, 'record_text'):
                self.record_text.config(state='normal')
                self.update_record_display()
                self.record_text.config(state='disabled')
                
                # 强制刷新界面
                self.record_text.update()
                self.master.update_idletasks()
            
            # 重置状态并用按钮
            self.is_drawing = False
            if hasattr(self, 'draw_one_button'):
                self.draw_one_button.configure(state='normal')
            if hasattr(self, 'draw_two_button'):
                self.draw_two_button.configure(state='normal')
            
            # 添闪效果（使用门的抽签闪方法
            self.flash_count = 0
            self.flash_draw_window()
            
            # 如声音已启用，播放系统提示音
            if self.config.get("sound_enabled"):
                try:
                    # 使用异步方式播放系统提示音
                    winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                except Exception as e:
                    print(f"无法播放系统提示音: {e}")
            
            # 如果是通过快捷键触的抽签，2秒自隐藏窗口
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
                # 时间到，隐藏窗
                self.hide_main_window()
        
        # 开始更新循环
        update()

    def calculate_weights(self):
        """计算每个学生抽取权重"""
        try:
            # 获取当前时间和处罚信息
            current_time = datetime.now()
            punishment_end_time = self.config.get("punishment_end_time")
            deleted_students_record = self.config.get("deleted_students")
            
            # 获取所有被删除的学生列表
            all_deleted_students = []
            if deleted_students_record:
                for filename, students in deleted_students_record.items():
                    all_deleted_students.extend(students)
            
            # 检查是否在处罚时间内
            is_punishing = False
            if punishment_end_time:
                end_time = datetime.strptime(punishment_end_time, "%Y-%m-%d %H:%M:%S")
                is_punishing = current_time < end_time
            
            weights = []
            
            if is_punishing and all_deleted_students:
                # 在处罚期间，分别计算被删除学生和普通学生的最小抽取次
                deleted_counts = [self.student_records.get(s, 0) for s in self.students if s in all_deleted_students]
                normal_counts = [self.student_records.get(s, 0) for s in self.students if s not in all_deleted_students]
                
                min_deleted_count = min(deleted_counts) if deleted_counts else 0
                min_normal_count = min(normal_counts) if normal_counts else 0
                
                for student in self.students:
                    count = self.student_records.get(student, 0)
                    if student in all_deleted_students:
                        # 被删除的学生
                        if count <= min_deleted_count:
                            # 如果是最少抽取次数，给予5.0倍权重（从3.0改为5.0，相当于提升400%）
                            weights.append(5.0)
                        else:
                            # 否则给予较低权重
                            weights.append(0.01)
                    else:
                        # 普通学生
                        if count <= min_normal_count:
                            weights.append(1.0)
                        else:
                            weights.append(0.01)
            else:
                # 不在处罚期间，使用普通权重计算
                min_count = min(self.student_records.values()) if self.student_records else 0
                for student in self.students:
                    count = self.student_records.get(student, 0)
                    weights.append(1.0 if count <= min_count else 0.01)
            
            # 确保至少有一个学生有非零权重
            if all(w <= 0.01 for w in weights):
                # 如果所有权重都很小重置所有权
                weights = [5.0 if student in all_deleted_students else 1.0 for student in self.students]
            
            Logger.info(f"权重计算 - 处罚状态: {is_punishing}, 被删除学生: {all_deleted_students}")
            Logger.info(f"计算的权重: {list(zip(self.students, weights))}")
            
            return weights
                
        except Exception as e:
            Logger.error(f"计算权重失败: {e}")
            return [1.0] * len(self.students)

    def update_record_display(self):
        if hasattr(self, 'record_text'):
            self.record_text.config(state='normal')  # 启用编辑
            self.record_text.delete(1.0, tk.END)
            # 按被抽取次数排序
            sorted_records = sorted(self.student_records.items(), key=lambda x: (-x[1], x[0]))
            
            # 显示每个学生的抽取次数
            for student, count in sorted_records:
                # 使用不同的颜色记不同的抽取数
                if count == 0:
                    color = '#FFFFFF'  # 灰色，表示未被抽取
                elif count == 1:
                    color = '#FFD700'  # 金色，表示抽取1次
                elif count == 2:
                    color = '#FFD700'  # 金色，表示2次
                else:
                    color = '#6A5ACD'  # 红橙色，表示抽取3次及以上
                
                # 插入生字和抽取次数，并设置色
                self.record_text.insert(tk.END, f"{student}: {count}\n")
                # 获取插文本的位置
                last_line_start = self.record_text.get("end-2c linestart", "end-1c")
                # 为这一行设置标签
                self.record_text.tag_add(f"color_{count}", 
                                       f"end-{len(last_line_start)+1}c linestart",
                                       "end-1c")
                self.record_text.tag_config(f"color_{count}", foreground=color)
            
            # 禁用文本编
            self.record_text.config(state='disabled')
            
            # 强制刷界面
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
        
        # 恢复框架和左侧导航栏显示
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
        if hasattr(self, 'chemistry_resources_frame'):
            self.chemistry_resources_frame.pack_forget()
        
        # 清理工具实验室相关框架
        if hasattr(self, 'tools_lab_frame'):
            self.tools_lab_frame.pack_forget()
        if hasattr(self, 'quiet_sound_frame'):
            self.quiet_sound_frame.pack_forget()
        if hasattr(self, 'tools_buttons'):
            self.tools_buttons.pack_forget()
        
        # 清理个人抽取音效框架
        if hasattr(self, 'personal_sound_frame'):
            self.personal_sound_frame.destroy()  # 使用destroy而不是pack_forget
            delattr(self, 'personal_sound_frame')  # 删除引用

    # 添加方法
    def minimize_to_tray(self):
        self.master.withdraw()  # 隐藏主窗口
        self.floating_ball.withdraw()  # 隐藏球
        self.create_system_tray()  # 创建系统托盘图标

    def get_resource_path(self, relative_path):
        """获取资源文件绝对路径"""
        try:
            # PyInstaller创建时件夹,路径存储_MEIPASS中
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def show_all_windows(self):
        """显示所有窗口"""
        self.master.deiconify()  # 示主窗口
        self.floating_ball.deiconify()  # 显示浮球
        self.visible = True
        self.update_hide_button_text()

    def create_settings_frame(self):
        # 创建主框架
        frame = ttk.Frame(self.main_content)
        
        # 创建左分栏局
        left_frame = ttk.Frame(frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)
        
        # 创建一个布局和滚动条
        canvas = tk.Canvas(left_frame, bg=self.themes[self.config.get("theme")]['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # 配置画布
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 添加鼠标滚轮绑定
        def on_mousewheel(event):
            # 在 Windows 上，event.delta 的值 120 的倍数
            delta = int(-1 * (event.delta / 120))
            canvas.yview_scroll(delta, "units")
            return "break"  # 阻止事件继续传播
        
        # 为所有相关组件绑定鼠标滚轮事件
        canvas.bind("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        frame.bind("<MouseWheel>", on_mousewheel)
        left_frame.bind("<MouseWheel>", on_mousewheel)
        
        # 当鼠标进入/离设置页时绑定/解绑全局滚轮事件
        def bind_mousewheel(event=None):
            self.master.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event=None):
            self.master.unbind_all("<MouseWheel>")
        
        # 为整个设置页面绑定鼠标进入/离开事件
        frame.bind("<Enter>", bind_mousewheel)
        frame.bind("<Leave>", unbind_mousewheel)
        
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
        
        speed_scale = ttk.Scale(speed_control_frame, from_=5.2, to=20.0, orient=tk.HORIZONTAL)
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
        ttk.Label(hotkey_frame, text="快速抽取快键:", font=('Arial', 12)).pack(side=tk.LEFT)
        
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
        
        # 5. 用异步抽设
        async_draw_frame = ttk.Frame(scrollable_frame)
        async_draw_frame.pack(fill=tk.X, padx=20, pady=10)
        self.async_draw_enabled = tk.BooleanVar(value=self.config.get("async_draw"))
        async_draw_check = ttk.Checkbutton(
            async_draw_frame, 
            text="使用异步抽签（更快的抽签方式）",  # 改进描述
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
            text="显示异步抽签动画", 
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
        
        hide_delay_scale = ttk.Scale(hide_delay_control_frame, from_=0.5, to=5.2, orient=tk.HORIZONTAL)
        hide_delay_scale.set(self.config.get("hide_delay"))
        hide_delay_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.hide_delay_label = ttk.Label(hide_delay_control_frame, text=f"{self.config.get('hide_delay'):.1f}", width=6)
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
        
        # 10. 倒计自动隐藏设置（移动到这里）
        countdown_auto_hide_frame = ttk.Frame(scrollable_frame)
        countdown_auto_hide_frame.pack(fill=tk.X, padx=20, pady=10)
        self.countdown_auto_hide_enabled = tk.BooleanVar(value=self.config.get("countdown_auto_hide"))
        countdown_auto_hide_check = ttk.Checkbutton(
            countdown_auto_hide_frame, 
            text="倒计时结束后自动隐藏窗口", 
            variable=self.countdown_auto_hide_enabled,
            command=lambda: self.config.set("countdown_auto_hide", self.countdown_auto_hide_enabled.get()),
            style='TCheckbutton'
        )
        countdown_auto_hide_check.pack(side=tk.LEFT)
        
        # 11. 主题切换
        theme_frame = ttk.Frame(scrollable_frame)
        theme_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(theme_frame, text="主题选择：", font=('Arial', 12)).pack(side=tk.LEFT)
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
            
            # 新基础样式
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
            
            # 更标签样式
            self.style.configure('TLabel', background=theme['bg'], foreground=theme['text'])
            
            # 更新按钮样式
            self.style.configure('TButton', background=theme['bg'], foreground=theme['text'])
            
            # 更新复选框样式
            self.style.configure('TCheckbutton', background=theme['bg'], foreground=theme['text'])
            
            # 更下拉样式
            self.style.configure('TCombobox', background=theme['bg'], foreground=theme['text'])
            self.style.configure('TCombobox.field', background=theme['bg'], foreground=theme['text'])
            
            # 更新滚动条样式
            self.style.configure('TScrollbar', background=theme['bg'], troughcolor=theme['bg'])
            
            # 更新分隔样式
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
            
            # 更水印背景色和文色
            if hasattr(self, 'watermark'):
                self.watermark.configure(bg=theme['bg'], fg=theme['text'])
            
            # 更计时器标样式
            if hasattr(self, 'time_label1'):
                self.time_label1.configure(background=theme['bg'], foreground=theme['text'])
            if hasattr(self, 'time_label2'):
                self.time_label2.configure(background=theme['bg'], foreground=theme['text'])
            if hasattr(self, 'countdown_label'):
                self.countdown_label.configure(background=theme['bg'], foreground=theme['text'])
            
            # 更新异步窗的样式
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
                
                # 重配置样式
                self.style.configure('Theme.TFrame', background=theme['bg'])
                self.style.configure('Theme.TLabel',
                                    background=theme['bg'],
                                    foreground=theme['text'],
                                    font=("Arial", 36))
                
                # 更新闪效果的样式
                for color in self.draw_flash_colors:
                    self.style.configure(f'Flash{color}.TFrame', background=color)
            
            # 更新水印景色
            if hasattr(self, 'watermark') and self.config.get("show_watermark"):
                self.watermark.configure(bg=theme['bg'])
        
        theme_combo.bind('<<ComboboxSelected>>', update_theme)
        
        # 添加快速初始化设置
        quick_init_frame = ttk.Frame(scrollable_frame)
        quick_init_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.quick_init_enabled = tk.BooleanVar(value=self.config.get("quick_init"))
        quick_init_check = ttk.Checkbutton(
            quick_init_frame, 
            text="快速初始化", 
            variable=self.quick_init_enabled,
            command=lambda: self.config.set("quick_init", self.quick_init_enabled.get()),
            style='TCheckbutton'
        )
        quick_init_check.pack(side=tk.LEFT)
        
        # 添加提示标签
        ttk.Label(
            quick_init_frame,
            text="（重启生效）",
            font=('Arial', 10),
            foreground='#808080'
        ).pack(side=tk.LEFT, padx=10)
        
        # 添加水印设置
        watermark_frame = ttk.Frame(scrollable_frame)
        watermark_frame.pack(fill=tk.X, padx=20, pady=10)
        self.show_watermark_enabled = tk.BooleanVar(value=self.config.get("show_watermark"))
        watermark_check = ttk.Checkbutton(
            watermark_frame, 
            text="显示常驻水印", 
            variable=self.show_watermark_enabled,
            command=self.toggle_watermark,
            style='TCheckbutton'
        )
        watermark_check.pack(side=tk.LEFT)
        
        # 添加保存抽取记录设置
        save_records_frame = ttk.Frame(scrollable_frame)
        save_records_frame.pack(fill=tk.X, padx=20, pady=10)
        self.save_records_enabled = tk.BooleanVar(value=self.config.get("save_draw_records"))
        save_records_check = ttk.Checkbutton(
            save_records_frame,
            text="保存抽取记录",
            variable=self.save_records_enabled,
            command=lambda: self.config.set("save_draw_records", self.save_records_enabled.get()),
            style='TCheckbutton'
        )
        save_records_check.pack(side=tk.LEFT)
        
        # 添加提示标签
        ttk.Label(
            save_records_frame,
            text="（关闭程序时保存记录）",
            font=('Arial', 10),
            foreground='#808080'
        ).pack(side=tk.LEFT, padx=10)
        
        # 配滚动区域
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
        
        # 修改明度滑块的绑定
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
        
        # 创建标题架
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
            
            # 在图标右侧添程序名称和版本
            name_version_frame = ttk.Frame(title_container)
            name_version_frame.pack(side=tk.LEFT)
            
            ttk.Label(name_version_frame, 
                     text="计时器", 
                     font=('Arial', 20, 'bold')).pack(anchor=tk.W)
            
            ttk.Label(name_version_frame, 
                     text=f"版本 {UpdateChecker.VERSION}", 
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
Claude-3.5-Sonnet

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
        self.update_frame = ttk.Frame(scrollable_frame)  # 修改这里，保存为实例变量
        self.update_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.update_button = ttk.Button(  # 也保存按钮引用
            self.update_frame,
            text="检查更新",
            command=self.check_for_updates
        )
        self.update_button.pack(side=tk.LEFT)
        
        ttk.Label(
            self.update_frame,
            text=f"当前版本：{UpdateChecker.VERSION}",
            font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=10)
        
        # 添加分隔线和序录按钮
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, padx=20, pady=20)
        directory_frame = ttk.Frame(scrollable_frame)
        directory_frame.pack(fill=tk.X, padx=20, pady=10)

        # 打开程序根目录按钮
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

        # 添加打开配置文件夹按钮
        def open_config_dir():
            # 创建密码输入对话框
            dialog = tk.Toplevel(self.master)
            dialog.title("验证")
            dialog.geometry("300x150")
            dialog.transient(self.master)  # 设置为主窗口的临时窗口
            dialog.grab_set()  # 模对话框
            
            # 设置对话框在屏幕中央
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'+{x}+{y}')
            
            # 创建密码输入框架
            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="请输入密码:", font=('Arial', 12)).pack(pady=(0, 10))
            
            # 码输入框
            password_var = tk.StringVar()
            password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=20)
            password_entry.pack(pady=(0, 20))
            
            def verify_password():
                if password_var.get() == "27314":  # 设密码为 27314
                    dialog.destroy()
                    config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
                    os.makedirs(config_dir, exist_ok=True)  # 确保目录存在
                    os.startfile(config_dir)
                else:
                    messagebox.showerror("错误", "密码错误", parent=dialog)  # 修复"密错误"
                    password_entry.select_range(0, tk.END)  # 选中所有文本
                    password_entry.focus()  # 重新获得焦点
            
            # 确认按钮
            ttk.Button(frame, text="确认", command=verify_password, width=10).pack(side=tk.LEFT, padx=5)
            
            # 取消按钮
            ttk.Button(frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
            
            # 绑定回车键
            password_entry.bind('<Return>', lambda e: verify_password())
            
            # 设置初始焦点
            password_entry.focus()

        ttk.Button(
            directory_frame,
            text="打开配置文件夹",
            command=open_config_dir
        ).pack(side=tk.LEFT)

        ttk.Label(
            directory_frame,
            text="（放配置和名单）",
            font=('Arial', 10),
            foreground='#808080'
        ).pack(side=tk.LEFT, padx=10)

        # 添加分隔线和卸载按钮
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
        
        # 创建清除处罚框架
        punishment_frame = ttk.Frame(scrollable_frame)
        punishment_frame.pack(fill=tk.X, padx=20, pady=10)

        # 创建清除处罚按钮
        clear_punishment_btn = ttk.Button(
            punishment_frame,
            text="清除所有处罚",
            command=self.show_clear_punishment_dialog,
            style='Red.TButton'  # 使用红色按钮样式
        )
        clear_punishment_btn.pack(side=tk.LEFT)

        # 添加处罚状态提示
        punishment_status = "处于处罚状态" if self.config.get("punishment_end_time") else "不在处罚状态"
        punishment_status_label = ttk.Label(
            punishment_frame,
            text=f"（{punishment_status}）",
            font=('Arial', 10),
            foreground='#FF4D4D' if self.config.get("punishment_end_time") else '#808080'
        )
        punishment_status_label.pack(side=tk.LEFT, padx=10)
        
        # 添加分隔线
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, padx=20, pady=20)

        # 创建GitHub Token设置框架（只保留这一个）
        github_token_frame = ttk.Frame(scrollable_frame)
        github_token_frame.pack(fill=tk.X, padx=20, pady=10)

        # Token 标签
        ttk.Label(github_token_frame, text="GitHub Token:", font=('Arial', 12)).pack(side=tk.LEFT)

        # Token 输入框
        token_var = tk.StringVar(value=self.config.get("github_token"))
        token_entry = ttk.Entry(github_token_frame, textvariable=token_var, width=40, show='*')
        token_entry.pack(side=tk.LEFT, padx=5)

        # 说明文本
        ttk.Label(
            github_token_frame,
            text="（可选）用于解除API请限制",
            font=('Arial', 9),
            foreground='#808080'
        ).pack(side=tk.LEFT, padx=10)

        # 创建按钮框架（在输入框下方）
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        # 添加右键菜单
        def create_popup_menu():
            menu = tk.Menu(token_entry, tearoff=0)
            menu.add_command(label="粘贴", command=lambda: token_entry.event_generate('<<Paste>>'))
            return menu

        def show_popup_menu(event):
            menu = create_popup_menu()
            menu.tk_popup(event.x_root, event.y_root)

        token_entry.bind("<Button-3>", show_popup_menu)  # 绑定右事件

        # 显示/隐藏按钮
        def toggle_token_visibility():
            current = token_entry['show']
            token_entry['show'] = '' if current == '*' else '*'
            show_token_btn['text'] = '隐藏' if current == '*' else '显示'

        show_token_btn = ttk.Button(button_frame, text='显示', command=toggle_token_visibility, width=6)
        show_token_btn.pack(side=tk.LEFT, padx=2)

        # 保存按钮
        def save_github_token():
            token = token_var.get().strip()
            
            if token:
                # 验证 token 有效性
                try:
                    headers = {
                        'Accept': 'application/vnd.github.v3+json',
                        'User-Agent': 'Chemistry-Timer-App',
                        'Authorization': f'Bearer {token}'
                    }
                    response = requests.get('https://api.github.com/user', headers=headers)
                    response.raise_for_status()
                    
                    # Token 有效保存配置
                    self.config.set("github_token", token)
                    os.environ['GITHUB_TOKEN'] = token
                    messagebox.showinfo("成功", "GitHub Token 验证成功并已保存")
                    
                except requests.exceptions.RequestException as e:
                    if hasattr(e, 'response') and e.response.status_code == 401:
                        messagebox.showerror("错误", "GitHub Token 无效，请检查后重试")
                    else:
                        messagebox.showerror("错误", f"验证 Token 时发生错误：\n{str(e)}")
                        return
            else:
                # 清除 token
                self.config.set("github_token", "")
                if 'GITHUB_TOKEN' in os.environ:
                    del os.environ['GITHUB_TOKEN']
                messagebox.showinfo("提示", "GitHub Token 已清除")

        save_btn = ttk.Button(button_frame, text='保存', command=save_github_token, width=6)
        save_btn.pack(side=tk.LEFT, padx=2)

        # 在法最添加这一行保存 frame 的引用
        self.settings_frame = frame
        
        # 返回创建 frame
        return frame

    def toggle_watermark(self):
        """切换水印显示状态"""  # 修复"切换水显示状态"
        show_watermark = self.show_watermark_enabled.get()
        self.config.set("show_watermark", show_watermark)
        
        if show_watermark:
            # 如果启用水印，创建并显示
            if not hasattr(self, 'watermark'):
                self.create_watermark()
            else:
                self.watermark.pack(side=tk.BOTTOM, anchor=tk.SE, padx=10, pady=10)
        else:
            # 如禁用水印，除显示并删除引
            if hasattr(self, 'watermark'):
                self.watermark.destroy()  # 使用 destroy 而不是 pack_forget
                delattr(self, 'watermark')  # 删除引用

    def uninstall_program(self):
        """卸载程序"""
        if messagebox.askyesno("卸载确认", 
                              "确定要卸载化学计时器吗？\n这将删除所有配置文件，但不删除您创建的名单文件"):
            try:
                # 删除配置文件夹
                config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
                if os.path.exists(config_dir):
                    import shutil
                    shutil.rmtree(config_dir)
                
                # 提用户卸载成
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
        
        # 如果有回调函数则执行它
        if callback:
            callback(event)

    def create_draw_interface(self):
        """创建抽签界面主要部分"""
        # 首先创建处罚提示框架
        self.punishment_frame = ttk.Frame(self.random_draw_frame)
        self.punishment_frame.pack(fill=tk.X, pady=(10, 0))  # 添加在顶部
        
        # 创建处罚提示标签
        self.punishment_label = ttk.Label(
            self.punishment_frame,
            text="",
            font=("Arial", 12, "bold"),
            foreground='#FF4500',  # 使用醒目的红橙色
            justify=tk.CENTER
        )
        self.punishment_label.pack(pady=5)
        
        # 更新处罚状态显示
        self.update_punishment_status()
        
        # 在创建界面之前初始化记录
        selected_file = self.file_var.get()
        
        # 初始化文件记录字典（如果还没有）
        if not hasattr(self, 'file_records'):
            self.file_records = {}
        
        # 初始化当前文件的记录
        if selected_file not in self.file_records:
            self.file_records[selected_file] = {}
        
        # 设置当前学生记录引用
        self.student_records = self.file_records[selected_file]
        
        # 读取并初始化学生记录
        try:
            file_path = self.get_namelist_path(selected_file)
            with open(file_path, "r", encoding="utf-8") as file:
                self.students = file.read().strip().split("\n")
                for student in self.students:
                    if student not in self.student_records:
                        self.student_records[student] = 0
        except Exception as e:
            Logger.error(f"初始化学生记录失败: {e}")
            self.student_records = {}
        
        # 创建记录框架
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
                                  bg=self.themes[self.config.get("theme")]['left_nav'],
                                  fg=self.themes[self.config.get("theme")]['text'],
                                  insertbackground=self.themes[self.config.get("theme")]['text']
        )
        self.record_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 设置滚动
        scrollbar.config(command=self.record_text.yview)

        # 改滚动条事件绑定
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
                                         style='TButton')  # 修复"取一名学生"
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
            # 重新初始化所有学生记录为0
            try:
                file_path = self.get_namelist_path(selected_file)
                with open(file_path, "r", encoding="utf-8") as file:
                    self.students = file.read().strip().split("\n")
                    for student in self.students:
                        self.student_records[student] = 0
                
                # 立即保存更新后的记录到文件（添加这一行）
                self.save_draw_records()
                
                # 立即更新显示
                self.update_record_display()
                # 重置显文本
                if hasattr(self, 'draw_display'):
                    self.draw_display.config(text="等待抽签...")
            except Exception as e:
                Logger.error(f"重置记录失败: {e}")

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
                
                # 根据窗口比例确定缩放大小
                if window_ratio > img_ratio:
                    new_height = window_height
                    new_width = int(new_height * img_ratio)
                else:
                    new_width = window_width
                    new_height = int(new_width / img_ratio)
                
                # 整图片小
                resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized_image)
                
                # 更
                self.periodic_table_label.config(image=photo)
                self.periodic_table_label.image = photo  # 保持引用防止垃圾回收
                
            except Exception as e:
                print(f"调整图片大小时发生错误: {e}")  # 修复"调整图片大小时发生误: {e}"

    def create_chemical_constants_frame(self):
        """创建化学常数页面"""
        frame = ttk.Frame(self.main_content)
        
        # 创建标题
        title_label = ttk.Label(frame, text="常化学常数", font=("Arial", 24, "bold"))  # 修复"常用化学常"
        title_label.pack(pady=20)
        
        # 创建数列表框架
        constants_frame = ttk.Frame(frame)
        constants_frame.pack(expand=True, fill=tk.BOTH, padx=20)
        
        # 定义常用化学常数（统一保留两位小数）
        constants = [
            ("阿伽德罗常数 (NA)", "6.02 × 10²³ mol⁻¹"),
            ("气体常数 (R)", "8.31 J/(mol·K)"),
            ("标准大气压 (P)", "1.01  10⁵ Pa"),
            ("标准尔体积 (Vm)", "22.41 L/mol"),
            ("法拉第常数 (F)", "9.65 × 10⁴ C/mol"),
            ("普朗克常数 (h)", "6.63 × 10⁻³ J·s"),
            ("光速 (c)", "3.00 × 10⁸ m/s"),
            ("玻尔兹曼数 (k)", "1.38 × 10⁻²³ J/K"),
            ("电荷 (e)", "1.60 × 10⁻¹⁹ C"),
            ("空介电常数 (ε₀)", "8.85 × 10⁻¹² F/m")
        ]
        
        # 创建常数标签
        for i, (name, value) in enumerate(constants):
            # 创一个框架来纳每个常数
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
        
        # 隐所有子列表
        self.timer_buttons.pack_forget()
        self.record_frame.pack_forget() if hasattr(self, 'record_frame') else None
        
        # 显示化学常数架
        if hasattr(self, 'chemical_constants_frame'):
            self.chemical_constants_frame.pack(expand=True, fill=tk.BOTH)

    def show_settings(self):
        """显示设置页面"""  # 修复"显示置页面"
        self.clear_main_content()
        
        # 隐藏左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack_forget()
        
        # 隐藏所有子列表
        self.timer_buttons.pack_forget()
        self.record_frame.pack_forget() if hasattr(self, 'record_frame') else None
        
        # 显示设框架
        if hasattr(self, 'settings_frame'):
            self.settings_frame.pack(expand=True, fill=tk.BOTH)

    def handle_global_hotkey(self, event):
        """处理全局热键事件"""
        try:
            # 检查是否正在异步抽签
            if hasattr(self, 'async_drawing') and self.async_drawing and self.config.get("async_draw"):
                return
                
            # 检查是否允快速抽取
            if not self.visible and not self.config.get("always_allow_quick_draw"):
                # 检查是否使用异步抽签
                if self.config.get("async_draw"):
                    # 直接进行抽签，不显示窗
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
        """门用抽签结果的闪烁效果"""  # 修复"门用抽结果的闪烁效果"
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
        """停止抽签闪烁"""
        self.reset_window_color()
        self.master.after(100, self.flash_draw_window)

    def reset_hotkey(self, default_key):
        self.config.set("hotkey", default_key)
        self.hotkey_label.config(text=f":{default_key}")
        self.hotkey_button.config(text="点击设置")

    def start_hotkey_listen(self):
        """开始监听键盘输入"""  # 修复"开始监听键盘"
        self.hotkey_button.configure(text="请按键...", state='disabled')
        self.hotkey_label.configure(text="在等待按键...")
        
        # 创建键盘监听器
        keyboard.hook(self.on_key_press)

    def on_key_press(self, event):
        """处理键盘按键"""
        try:
            # 获取按键名称
            key_name = event.name
            
            # 停止监听
            keyboard.unhook(self.on_key_press)
            
            # 更新配置
            self.update_hotkey(key_name)
            
            # 恢复按钮状态
            self.hotkey_button.configure(text="点击设置", state='normal')
            
        except Exception as e:
            print(f"设置快捷键时发生错误: {e}")
            self.reset_hotkey(self.config.get("hotkey"))

    def update_hotkey(self, new_hotkey):
        """更新快捷键设置"""
        try:
            # 先注销旧的捷键
            keyboard.unhook_all()
            
            # 更新配置
            self.config.set("hotkey", new_hotkey)
            
            # 更新显示
            self.hotkey_label.configure(text=f":{new_hotkey}")
            
            # 注册新的捷键
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
            
            # 根据设决定否显示画
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
            file_path = self.get_namelist_path(selected_file)  # 使用新方法获取路径
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            
            with open(file_path, "r", encoding="utf-8") as file:
                students = file.read().strip().split("\n")
                selected_student = self.get_draw_result(students)
            
            # 开始动画
            def update_animation(step=0):
                if step < 100:  # 使用进度条相同的进度
                    # 随机显示一个名字
                    random_student = random.choice(students)
                    self.async_window.result_label.config(text=random_student)
                    # 使用配置的速度
                    speed = self.config.get("draw_speed")
                    self.master.after(50, lambda: update_animation(step + speed))
                else:
                    # 动画结束显示真实果
                    self.async_window.result_label.config(text=selected_student)
                    # 播放声和闪烁效果
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
            print(f"异步抽签动画失败: {e}")
            if hasattr(self, 'async_window'):
                self.async_window.result_label.config(text="抽签失败")

    def get_draw_result(self, students=None):
        """获取抽签结果"""
        try:
            # 如果没传入学生列表，则读取文件
            if students is None:
                selected_file = self.file_var.get() if hasattr(self, 'file_var') else self.get_first_txt_file()
                file_path = self.get_namelist_path(selected_file)  # 使用新方法获取路径
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    students = file.read().strip().split('\n')
            
            # 初始化记录字典（果需要）
            selected_file = self.file_var.get() if hasattr(self, 'file_var') else self.get_first_txt_file()
            if not hasattr(self, 'file_records'):
                self.file_records = {}
            if selected_file not in self.file_records:
                self.file_records[selected_file] = {}
            
            # 确保所有学生都在记录中并初始化为0
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
            
            # 如果所有重都是0.01，重置为相等权重
            if all(w == 0.01 for w in weights):
                weights = [1.0] * len(weights)
            
            # 抽生
            selected_student = random.choices(students, weights=weights, k=1)[0]
            
            # 更新记录
            self.file_records[selected_file][selected_student] = self.file_records[selected_file].get(selected_student, 0) + 1
            
            return selected_student
                
        except Exception as e:
            Logger.error(f"获取抽签结果失败: {e}")
            return "抽签失败"

    def flash_async_window(self):
        """闪烁异步抽签窗口"""
        if hasattr(self, 'async_window'):
            if self.flash_count < self.max_draw_flashes:
                color = self.draw_flash_colors[self.flash_count % len(self.draw_flash_colors)]
                # 只改变闪烁框的背景色
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
        """停止异步口闪烁"""
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
            # 使用配的隐藏时间
            duration = self.config.get("hide_delay") * 1000
            
        start_time = time.time()
        
        def update():
            current_time = time.time()
            elapsed = int((current_time - start_time) * 1000)
            remaining = max(0, duration - elapsed)
            
            if remaining > 0:
                # 更显示文（保留一位小数）
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
            file_path = self.get_namelist_path(selected_file)  # 使用新方法获取路径
            
            # 读取并抽取学生
            with open(file_path, "r", encoding="utf-8") as file:
                students = file.read().strip().split("\n")
                selected_student = self.get_draw_result(students)
                
                # 更新显示
                self.async_window.result_label.config(text=selected_student)
                
                # 立即保存记录到文件（添加这一行）
                self.save_draw_records()
                
                # 播放声音和烁效果
                if self.config.get("sound_enabled"):
                    try:
                        winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except Exception as e:
                        print(f"无法播放系统提示音: {e}")
                
                self.flash_count = 0
                self.flash_async_window()
                
                # 开始计时并在结束时隐藏窗口
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
                # 显示更提示对话框
                if messagebox.askyesno(
                    "发现版本",
                    f"发现新版本 {latest_version}\n是否立即更新？",
                    icon='info'
                ):
                    # 打开下载链接
                    webbrowser.open(download_url)
            else:
                # 在更钮下方添加提示签
                if hasattr(self, 'update_status_label'):
                    self.update_status_label.destroy()
                
                # 确保 update_frame 存在
                if hasattr(self, 'update_frame'):
                    self.update_status_label = ttk.Label(
                        self.update_frame,
                        text="已是最新版本",
                        font=('Arial', 9),
                        foreground='#808080'
                    )
                    self.update_status_label.pack(side=tk.LEFT, padx=(10, 0))
                    
                    # 3秒后自动移除提示
                    self.master.after(3000, lambda: self.update_status_label.destroy() if hasattr(self, 'update_status_label') else None)
                else:
                    Logger.error("update_frame 不存在")
                
        except Exception as e:
            Logger.error(f"检查更新失败: {e}")

    def check_updates_and_show_ball(self):
        """检查更新但不显示浮球"""
        try:
            # 检查更新
            has_update, latest_version, self.download_url = UpdateChecker.check_update()
            if has_update:
                # 显示新版本提示标签
                self.update_label.pack(side=tk.LEFT, padx=(0, 2))
                self.latest_version = latest_version  # 保存最新版本号
        except Exception as e:
            Logger.error(f"检查更新失败: {e}")

    def show_update_dialog(self):
        """显示更新对话框"""
        if hasattr(self, 'latest_version') and hasattr(self, 'download_url'):
            if messagebox.askyesno(
                "发新版本",
                f"发现新版本 {self.latest_version}\n是否立即更新？",
                icon='info'
            ):
                webbrowser.open(self.download_url)

    # 在 ChemistryTimer 类中添加以下方法
    def setup_drag_drop(self):
        """设置拖拽功"""
        # 注册文件拖拽事件
        self.master.drop_target_register('DND_Files')
        self.master.dnd_bind('<<Drop>>', self.handle_drop)
        
        # 在随机抽签界面也注册拖拽
        if hasattr(self, 'random_draw_frame'):
            self.random_draw_frame.drop_target_register('DND_Files')
            self.random_draw_frame.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        """处理文件拖拽"""
        try:
            # 获取拖拽的文件路径
            files = event.data
            if isinstance(files, str):
                files = [files]
                
            # 过滤出txt文件
            txt_files = [f for f in files if f.lower().endswith('.txt')]
            if not txt_files:
                messagebox.showwarning("无效文件", "请拖拽.txt格式的名单文件")
                return
                
            # 复制文件到程序目录
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            imported_files = []
            
            for file_path in txt_files:
                filename = os.path.basename(file_path)
                target_path = os.path.join(program_dir, filename)
                
                # 如果文件已存在，添加序号
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(target_path):
                    filename = f"{base}_{counter}{ext}"
                    target_path = os.path.join(program_dir, filename)
                    counter += 1
                
                # 复制文件
                import shutil
                shutil.copy2(file_path, target_path)
                imported_files.append(filename)
            
            # 显示导入成功消息
            if imported_files:
                messagebox.showinfo("导入成功", 
                                  f"成功导入以下名单文件:\n{chr(10).join(imported_files)}\n\n请重新打开抽签页面以刷新名单。")
                
                # 如果当前在抽签界面，自动刷新
                if hasattr(self, 'random_draw_frame'):
                    self.show_random_draw()
                    
        except Exception as e:
            Logger.error(f"导入名单文件失败: {e}")
            messagebox.showerror("导入失败", f"导入名单文件时发生错误:\n{str(e)}")  # 修复"导入失败"

    def compare_namelists(self):
        """比对根目录和配目录中的名单文件内容"""
        try:
            # 获取程序目录和配置目录路径
            program_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            namelist_dir = os.path.join(config_dir, 'namelists')
            os.makedirs(namelist_dir, exist_ok=True)  # 确保目录存在
            
            # 获取两个目中的txt文件
            program_txt_files = [f for f in os.listdir(program_dir) if f.endswith('.txt')]
            config_txt_files = [f for f in os.listdir(namelist_dir) if f.endswith('.txt')]
            
            # 在终端输出开始比对提示
            Logger.info("开始比对名单文件...")
            Logger.info(f"找到 {len(program_txt_files)} 个名单文")
            
            missing_students = {}  # 用于存储每个文件中缺少的学生
            all_files_normal = True  # 标记所有文件是否正常
            
            # 比对每个文件的内容
            for filename in program_txt_files:
                Logger.info(f"正在比对: {filename}")
                program_file_path = os.path.join(program_dir, filename)
                config_file_path = os.path.join(namelist_dir, filename)
                
                # 读取程序目录中的名单
                with open(program_file_path, 'r', encoding='utf-8') as f:
                    program_students = set(f.read().strip().split('\n'))
                
                # 读取配置目录中的名单
                if filename in config_txt_files:
                    with open(config_file_path, 'r', encoding='utf-8') as f:
                        config_students = set(f.read().strip().split('\n'))
                    
                    # 检查是否有学生从程序目录名单中删除
                    missing = config_students - program_students
                    if missing:
                        missing_students[filename] = sorted(list(missing))
                        all_files_normal = False
                        # 在终端输出删除的学生
                        Logger.info(f"在 {filename} 中删除了: {', '.join(missing)}")
                        
                        # 保存被删除的学生到配置文件
                        deleted_students = self.config.get("deleted_students") or {}
                        deleted_students[filename] = sorted(list(missing))
                        self.config.set("deleted_students", deleted_students)
                        
                        # 如果检测到文件被篡改，立即用配置文件覆盖
                        with open(config_file_path, 'r', encoding='utf-8') as source:
                            content = source.read()
                        with open(program_file_path, 'w', encoding='utf-8') as target:
                            target.write(content)
                        Logger.info(f"已修复被篡改的文件: {filename}")
                    else:
                        Logger.info(f"{filename} 内容一致")
                else:
                    Logger.info(f"配置目录中不存在文件: {filename}")
                    all_files_normal = False
            
            # 如果有缺少的学生，设置处罚结束时间和权重
            if missing_students:
                # 计算被删除的总人数
                total_deleted = sum(len(students) for students in missing_students.values())
                
                # 计算处罚时间：基础16小时 + 每人8小时
                punishment_hours = 16 + (total_deleted - 1) * 8
                punishment_end_time = datetime.now() + timedelta(hours=punishment_hours)
                self.config.set("punishment_end_time", punishment_end_time.strftime("%Y-%m-%d %H:%M:%S"))
                
                # 计算处罚权重：基础3.0 + 每人1.5
                punishment_weight = 3.0 + (total_deleted - 1) * 1.5
                self.config.set("punishment_weight", punishment_weight)
                
                # 更新警告文本
                warning_text = (f"警告：根据比对，检测到名单文件被非法修改！\n"
                               f"处罚{punishment_hours}小时，期间被随机抽取到的概率升{int(punishment_weight*100-100)}%")

            def show_warning():
                    # 创建警告窗口
                warning_window = tk.Toplevel(self.master)
                warning_window.overrideredirect(True)
                warning_window.attributes('-topmost', True)
                warning_window.wm_attributes("-toolwindow", True)
                
                # 使用当前主题的颜色
                current_theme = self.themes[self.config.get("theme")]
                warning_window.configure(bg=current_theme['bg'])
                
                    # 设置窗口大小和位置
                width = 400
                height = 200
                screen_width = warning_window.winfo_screenwidth()
                screen_height = warning_window.winfo_screenheight()
                x = (screen_width - width) // 2
                y = (screen_height - height) // 2
                warning_window.geometry(f'{width}x{height}+{x}+{y}')
                
                # 配置警告窗口的样式
                style = ttk.Style(warning_window)
                style.configure('Warning.TFrame', background=current_theme['bg'])
                style.configure('Warning.TLabel',
                              background=current_theme['bg'],
                              foreground='#FF4500',
                              font=("Arial", 14, "bold"))
                
                # 创建外层框架
                flash_frame = ttk.Frame(warning_window, style='Warning.TFrame')
                flash_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
                
                # 创建内容框架
                content_frame = ttk.Frame(flash_frame, style='Warning.TFrame')
                content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
                
                # 创建警告标签
                warning_label = ttk.Label(
                    content_frame,
                    text=warning_text,
                    style='Warning.TLabel',
                    justify=tk.CENTER
                )
                warning_label.pack(expand=True)
                
                # 3秒后自动关闭
                warning_window.after(3000, warning_window.destroy)
                
                # 闪烁效果
                def flash_warning(count=0):
                    if count < 6:  # 闪烁3次
                        color = '#FF4500' if count % 2 == 0 else current_theme['bg']
                        style.configure('Warning.TFrame', background=color)
                        warning_window.after(500, lambda: flash_warning(count + 1))
                
                flash_warning()
                
                # 播放警告音
                if self.config.get("sound_enabled"):
                    try:
                        winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except Exception as e:
                        Logger.error(f"播放警告音失败: {e}")
            
            # 录日志
            if all_files_normal:
                Logger.info("名单正常")
            else:
                Logger.info("名单比对完成")
            
            # 如果有缺少的学生，在初始化完成后显示警告窗口
            if missing_students:
                def show_warning():
                    # 创建警告窗口
                    warning_window = tk.Toplevel(self.master)
                    warning_window.overrideredirect(True)
                    warning_window.attributes('-topmost', True)
                    warning_window.wm_attributes("-toolwindow", True)
                    
                    # 设窗口大小和位置
                    width = 600
                    height = 300
                    screen_width = warning_window.winfo_screenwidth()
                    screen_height = warning_window.winfo_screenheight()
                    x = (screen_width - width) // 2
                    y = (screen_height - height) // 2
                    warning_window.geometry(f'{width}x{height}+{x}+{y}')
                    
                    # 使用黑色背景
                    warning_window.configure(bg='#000000')
                    
                    # 创建内容框架
                    content_frame = ttk.Frame(warning_window)
                    content_frame.pack(fill=tk.BOTH, expand=True)
                    
                    # 配置样式
                    style = ttk.Style(warning_window)
                    style.configure('Warning.TFrame', background='#000000')
                    style.configure('Warning.TLabel',
                                   background='#000000',
                                   foreground='#FF0000',  # 红色文字
                                   font=("Arial", 18, "bold"),
                                   justify='center',
                                   anchor='center')
                    style.configure('Student.TLabel',
                                   background='#000000',
                                   foreground='#FFD700',  # 金黄色文字
                                   font=("Arial", 18),
                                   justify='center',
                                   anchor='center')
                    style.configure('Version.TLabel',
                                   background='#000000',
                                   foreground='#4169E1',  # 皇家蓝
                                   font=("Arial", 12),
                                   justify='center',
                                   anchor='center')
                    
                    # 应用样式
                    content_frame.configure(style='Warning.TFrame')
                    
                    # 创建标签容器以确保居中
                    labels_frame = ttk.Frame(content_frame, style='Warning.TFrame')
                    labels_frame.pack(expand=True)
                    
                    # 警告文本
                    warning_label = ttk.Label(
                        labels_frame,
                                text="警告：根据比对��检测到名单��被非法修改",
                                style='Warning.TLabel',
                                justify=tk.CENTER,
                                anchor='center'
                    )
                    warning_label.pack(pady=(20, 20))
                            
                    # 被删除的学生名单
                    deleted_students = []
                    for filename, students in missing_students.items():
                        deleted_students.extend(students)
                    deleted_text = "、".join(deleted_students)
                    
                    students_label = ttk.Label(
                                labels_frame,
                                text=f"被删除的学生：{deleted_text}",
                                style='Student.TLabel',
                                justify=tk.CENTER,
                                anchor='center',
                                wraplength=500
                        )
                    students_label.pack(pady=(0, 20))
                            
                    # 计算处罚结束时间的显示文本
                    end_time_str = punishment_end_time.strftime("%m月%d日 %H:%M")
                            
                    # 修改惩罚文本，添加结束时间
                    punishment_label = ttk.Label(
                        labels_frame,
                        text=f"作为惩罚，在{end_time_str}之前\n被随机抽取到的概率提升{int(punishment_weight*100-100)}%",
                        style='Warning.TLabel',
                        justify=tk.CENTER,
                        anchor='center'
                        )
                    punishment_label.pack(pady=(0, 20))
                    
                    # 添加版本信息
                    version_label = ttk.Label(
                        content_frame,
                                text="化学计时器V5.2 × 羌洛大模型",
                        style='Version.TLabel'
                    )
                    version_label.pack(side=tk.BOTTOM, pady=10)
                            
                    # 添加倒计时标签
                    countdown_label = ttk.Label(
                        content_frame,
                        text="10.0",  # 改为10秒
                        font=("Arial", 24, "bold"),
                        foreground='#FF4500',
                        background='#000000'
                        )
                    countdown_label.place(relx=1.0, rely=0, x=-20, y=20, anchor="ne")
                            
                    # 倒计时更新函数
                    def update_countdown():
                                remaining = float(countdown_label['text'])
                                if remaining > 0:
                                    countdown_label.config(text=f"{remaining-0.1:.1f}")
                                    warning_window.after(100, update_countdown)
                                else:
                                    warning_window.destroy()
                            
                    # 播放警告音（增加次数）
                    def play_warning_sound(count=0):
                        if count < 3 and self.config.get("sound_enabled"):  # 从10次改为3次
                            try:
                                        winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
                                        warning_window.after(1000, lambda: play_warning_sound(count + 1))  # 每秒播放一次
                            except Exception as e:
                                        Logger.error(f"播放警告音失败: {e}")
                            
                            # 启动倒计时和声音
                            update_countdown()
                            play_warning_sound()
                        
                        # 在初始化完成后显示警告窗口
                    self.master.after(2000, show_warning)
            
            # 记录日志
            if all_files_normal:
                Logger.info("名单正常")
            else:
                Logger.info("名单比对完成")
            
            # 如果有缺少的学生，在初始化完成后显示警告窗口
            if missing_students:
                def show_warning():
                    # 创建警窗口
                    warning_window = tk.Toplevel(self.master)
                    warning_window.overrideredirect(True)
                    warning_window.attributes('-topmost', True)
                    warning_window.wm_attributes("-toolwindow", True)
                    
                    # 设置窗口大小和位置
                    width = 600
                    height = 300
                    screen_width = warning_window.winfo_screenwidth()
                    screen_height = warning_window.winfo_screenheight()
                    x = (screen_width - width) // 2
                    y = (screen_height - height) // 2
                    warning_window.geometry(f'{width}x{height}+{x}+{y}')
                    
                    # 使用黑色背景
                    warning_window.configure(bg='#000000')
                    
                    # 创建内容框架
                    content_frame = ttk.Frame(warning_window)
                    content_frame.pack(fill=tk.BOTH, expand=True)
                    
                    # 配样式
                    style = ttk.Style(warning_window)
                    style.configure('Warning.TFrame', background='#000000')
                    style.configure('Warning.TLabel',
                                   background='#000000',
                                   foreground='#FF0000',  # 红色文字
                                   font=("Arial", 18, "bold"),
                                   justify='center',
                                   anchor='center')
                    style.configure('Student.TLabel',
                                   background='#000000',
                                   foreground='#FFD700',  # 金黄色文字
                                   font=("Arial", 18),
                                   justify='center',
                                   anchor='center')
                    style.configure('Version.TLabel',
                                   background='#000000',
                                   foreground='#4169E1',  # 皇家蓝
                                   font=("Arial", 12),
                                   justify='center',
                                   anchor='center')
                    
                    # 应用样式
                    content_frame.configure(style='Warning.TFrame')
                    
                    # 创建标签容器以确保居中
                    labels_frame = ttk.Frame(content_frame, style='Warning.TFrame')
                    labels_frame.pack(expand=True)
                    
                    # 警告文本
                    warning_label = ttk.Label(
                        labels_frame,
                        text="警告：根据比对，检测到名单文件被非法修改！",
                        style='Warning.TLabel',
                        justify=tk.CENTER,
                        anchor='center'
                    )
                    warning_label.pack(pady=(20, 20))
                    
                    # 被删除的学生名单
                    deleted_students = []
                    for filename, students in missing_students.items():
                        deleted_students.extend(students)
                    deleted_text = "、".join(deleted_students)
                    
                    students_label = ttk.Label(
                        labels_frame,
                        text=f"被删除的学生：{deleted_text}",
                        style='Student.TLabel',
                        justify=tk.CENTER,
                        anchor='center',
                        wraplength=500
                    )
                    students_label.pack(pady=(0, 20))
                            
                    # 计算处罚结束时间的显示文本
                    end_time_str = punishment_end_time.strftime("%m月%d日 %H:%M")
                            
                    # 修改惩罚文本，添加结束时间
                    punishment_label = ttk.Label(
                        labels_frame,
                        text=f"作为惩罚，在{end_time_str}之前\n被随机抽取到的概率提升{int(punishment_weight*100-100)}%",
                        style='Warning.TLabel',
                        justify=tk.CENTER,
                        anchor='center'
                        )
                    punishment_label.pack(pady=(0, 20))
                    
                    # 添加版本信息
                    version_label = ttk.Label(
                        content_frame,
                                text="化学计时器V5.2 × 羌洛大模型",
                        style='Version.TLabel'
                    )
                    version_label.pack(side=tk.BOTTOM, pady=10)
                            
                    # 添加倒计时标签
                    countdown_label = ttk.Label(
                        content_frame,
                        text="10.0",  # 改为10秒
                        font=("Arial", 24, "bold"),
                        foreground='#FF4500',
                        background='#000000'
                        )
                    countdown_label.place(relx=1.0, rely=0, x=-20, y=20, anchor="ne")
                            
                    # 倒计时更新函数
                    def update_countdown():
                                remaining = float(countdown_label['text'])
                                if remaining > 0:
                                    countdown_label.config(text=f"{remaining-0.1:.1f}")
                                    warning_window.after(100, update_countdown)
                                else:
                                    warning_window.destroy()
                            
                    # 播放警告音（增加次数）
                    def play_warning_sound(count=0):
                        if count < 3 and self.config.get("sound_enabled"):  # 从10次改为3次
                            try:
                                winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
                                warning_window.after(1000, lambda: play_warning_sound(count + 1))  # 每秒播放一次
                            except Exception as e:
                                Logger.error(f"播放警告音失败: {e}")
                    
                    # 启动倒计时声音
                    update_countdown()
                    play_warning_sound()
                
                # 在始完成后显示警告窗口
                self.master.after(2000, show_warning)
            
        except Exception as e:
            Logger.error(f"名单比对失败: {e}")

    # 添加新方法来更新处罚状态
    def update_punishment_status(self):
        """更新处罚状态显示"""
        try:
            # 获取处罚结束时间和被删除的学生记录
            punishment_end_time = self.config.get("punishment_end_time")
            deleted_students = self.config.get("deleted_students")
            
            Logger.info(f"更新处罚状态 - 处罚时间: {punishment_end_time}")
            Logger.info(f"更新处罚状态 - 被删除学生: {deleted_students}")
            
            # 清除所有现有的标签
            for widget in self.punishment_frame.winfo_children():
                widget.destroy()
            
            if punishment_end_time and deleted_students:
                end_time = datetime.strptime(punishment_end_time, "%Y-%m-%d %H:%M:%S")
                current_time = datetime.now()
                
                if current_time < end_time:
                    # 计算剩余时间
                    remaining = end_time - current_time
                    hours = remaining.seconds // 3600 + remaining.days * 24
                    minutes = (remaining.seconds % 3600) // 60
                    
                    # 获取所有被删除的学生名单
                    all_deleted = []
                    for filename, students in deleted_students.items():
                        all_deleted.extend(students)
                    deleted_text = "、".join(all_deleted)
                    
                    # 计算当前的处罚权重：基础16小时 + 每人8小时
                    total_deleted = len(all_deleted)
                    punishment_hours = 16 + (total_deleted - 1) * 8
                    # 计算处罚权重：础3.0 + 每人1.5
                    punishment_weight = 3.0 + (total_deleted - 1) * 1.5
                    
                    # 创建警告标签
                    warning_label = ttk.Label(
                        self.punishment_frame,
                        text="       ⚠ 检测到名单被修改 ⚠\n"
                             f"处罚时段：还剩 {hours} 小时 {minutes} 分钟",
                        font=("Arial",12, "bold"),
                        foreground='#FF4500'
                    )
                    warning_label.pack(pady=(5, 2))
                    
                    # 创建学生名字标签（使用深蓝色）
                    students_label = ttk.Label(
                        self.punishment_frame,
                        text=f"被处罚学生：{deleted_text}",
                        font=("Arial", 12, "bold"),
                        foreground='#4169E1'
                    )
                    students_label.pack(pady=(0, 2))
                    
                    # 创建处罚信息签
                    info_label = ttk.Label(
                        self.punishment_frame,
                        text=f"这些学生被抽取概率提升{int(punishment_weight*100-100)}%",
                        font=("Arial", 12, "bold"),
                        foreground='#FF4500'
                    )
                    info_label.pack(pady=(0, 5))
                    
                    # 每分钟更新一次显示
                    self.master.after(60000, self.update_punishment_status)
                else:
                    # 处罚结束，清除所有记录
                    self.config.set("punishment_end_time", "")
                    self.config.set("deleted_students", {})
            
        except Exception as e:
            Logger.error(f"更新处罚状态失败: {e}")
            # 清除所有标签
            for widget in self.punishment_frame.winfo_children():
                widget.destroy()

    # 添新方法来处理清除处罚功能
    def show_clear_punishment_dialog(self):
        """显示清除处罚确认对话框"""
        # 创建密码输入对话框
        dialog = tk.Toplevel(self.master)
        dialog.title("证")
        dialog.geometry("300x150")
        dialog.transient(self.master)  # 设置为主窗口的临时窗口
        dialog.grab_set()  # 模态对话框
        
        # 设置对话框在屏幕中央
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        # 创建密码输入框架
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="请输入管理员密码:", font=('Arial', 12)).pack(pady=(0, 10))
        
        # 密码输入框
        password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=20)
        password_entry.pack(pady=(0, 20))
        
        def verify_password():
            if password_var.get() == "27314":  # 使用相同的密码
                dialog.destroy()
                self.clear_all_punishments()
            else:
                messagebox.showerror("错误", "密码错误", parent=dialog)
                password_entry.select_range(0, tk.END)  # 选中有文本
                password_entry.focus()  # 重新获得焦点
        
        # 确认按钮
        ttk.Button(frame, text="确认", command=verify_password, width=10).pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        ttk.Button(frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        password_entry.bind('<Return>', lambda e: verify_password())
        
        # 设置初始焦点
        password_entry.focus()

    def clear_all_punishments(self):
        """清除所有处罚状态和抽取记录"""
        try:
            # 清除处罚相关的配置
            self.config.set("punishment_end_time", "")
            self.config.set("deleted_students", {})
            
            # 重置所有文件的抽取记录
            self.file_records = {}
            
            # 重新初始化当前显示的文件记录
            if hasattr(self, 'file_var'):
                selected_file = self.file_var.get()
                self.file_records[selected_file] = {}
                self.student_records = self.file_records[selected_file]
                
                # 读取并始化学生记录
                try:
                    file_path = self.get_namelist_path(selected_file)
                    with open(file_path, "r", encoding="utf-8") as file:
                        self.students = file.read().strip().split("\n")
                        for student in self.students:
                            self.student_records[student] = 0
                except Exception as e:
                    Logger.error(f"初始化学生记录失败: {e}")
            
            # 更新显示
            if hasattr(self, 'record_text'):
                self.update_record_display()
            
            # 更新处罚状态显示
            if hasattr(self, 'punishment_label'):
                self.update_punishment_status()
            
            # 显示成功消息
            messagebox.showinfo("成功", "已清除所有处罚状态和抽取记录")
            
            Logger.info("已清除所有处罚态和抽取记录")
            
        except Exception as e:
            Logger.error(f"清除处罚状态失败: {e}")
            messagebox.showerror("错误", f"清除处罚状态失败:\n{str(e)}")

    def save_draw_records(self):
        """保存抽取记录"""
        if not self.config.get("save_draw_records"):
            Logger.info("抽取记录保存功能未启用")
            return
        
        try:
            # 获取配置目录
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '学计时器')
            # 确保目录存在
            os.makedirs(config_dir, exist_ok=True)
            records_file = os.path.join(config_dir, "draw_records.json")
            
            # 保存记
            if hasattr(self, 'file_records'):  # 移除 and self.file_records 检查
                with open(records_file, 'w', encoding='utf-8') as f:
                    json.dump(self.file_records, f, ensure_ascii=False, indent=4)
                Logger.info(f"已保存抽取记录到: {records_file}")
                Logger.info(f"保存的记录内容: {self.file_records}")
            else:
                Logger.info("没有可保存的抽取记录")
                # 如果没有记录，创建空记录
                self.file_records = {}
                with open(records_file, 'w', encoding='utf-8') as f:
                    json.dump(self.file_records, f, ensure_ascii=False, indent=4)
                Logger.info("已创建空的抽取记录文件")
        except Exception as e:
            Logger.error(f"保存抽取记录失败: {e}")

    def load_draw_records(self):
        """加载抽取记录"""
        if not self.config.get("save_draw_records"):
            Logger.info("抽取记录加载功能未启用")
            return
        
        try:
            # 获取配置目录
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', '化学计时器')
            # 确保目录存在
            os.makedirs(config_dir, exist_ok=True)
            records_file = os.path.join(config_dir, "draw_records.json")
            
            # 加载记录
            if os.path.exists(records_file):
                with open(records_file, 'r', encoding='utf-8') as f:
                    self.file_records = json.load(f)
                Logger.info(f"已加载抽取记录: {records_file}")
            else:
                Logger.info("未找到抽取录文件，正在创建...")
                self.file_records = {}
                # 立即创建空的记录文件
                with open(records_file, 'w', encoding='utf-8') as f:
                    json.dump(self.file_records, f, ensure_ascii=False, indent=4)
                Logger.info(f"已创建空的抽取记录文件: {records_file}")
        except Exception as e:
            Logger.error(f"加载抽取记录失败: {e}")
            self.file_records = {}
            try:
                # 如果加载失败，尝试创建新的记录文件
                with open(records_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
                Logger.info("已创建新的抽取记录文件")
            except Exception as e:
                Logger.error(f"创建抽取记录文件失败: {e}")

    def create_chemistry_resources_frame(self):
        """创建化学资料页面"""
        frame = ttk.Frame(self.main_content)
        
        # 创建标题
        title_label = ttk.Label(frame, text="化学资料", font=("Arial", 24, "bold"))
        title_label.pack(pady=20)
        
        # 创建按钮框架
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(expand=True, fill=tk.BOTH, padx=20)
        
        # 添加资料按钮
        resources = [
            ("元素周期表", self.show_periodic_table),
            ("化学常数", self.show_chemical_constants),
            ("妙妙工具", self.show_tools_lab)  # 添加妙妙工具按钮
        ]
        
        for text, command in resources:
            btn = ttk.Button(buttons_frame, 
                            text=text, 
                            command=command,
                            style='Resource.TButton',  # 使用新的按钮样式
                            width=20)  # 设置固定宽度
            btn.pack(pady=10)
        
        return frame

    def show_chemistry_resources(self):
        """显示化学资料页面"""
        self.clear_main_content()
        
        # 隐藏左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack_forget()
        
        # 隐藏所有子列表
        self.timer_buttons.pack_forget()
        self.record_frame.pack_forget() if hasattr(self, 'record_frame') else None
        
        # 显示化学资料框架
        if not hasattr(self, 'chemistry_resources_frame'):
            self.chemistry_resources_frame = self.create_chemistry_resources_frame()
        self.chemistry_resources_frame.pack(expand=True, fill=tk.BOTH)

    def create_tools_lab_frame(self):
        """创建妙妙工具实验室面"""
        frame = ttk.Frame(self.main_content)
        
        # 创建标题
        title_label = ttk.Label(frame, text="妙妙工具实验室", font=("Arial", 24, "bold"))
        title_label.pack(pady=20)
        
        # 创建主要内容区域
        content_frame = ttk.Frame(frame)
        content_frame.pack(expand=True, fill=tk.BOTH, padx=20)
        
        # 这里将来放置具体功能的实现
        
        return frame

    def create_tools_navbar(self):
        """创建妙妙工具子导航栏"""
        if not hasattr(self, 'tools_buttons'):
            self.tools_buttons = ttk.Frame(self.left_navbar, style='ToolsNav.TFrame')
        
        # 清除现有的按钮
        for widget in self.tools_buttons.winfo_children():
            widget.destroy()
        
        # 添加工具按钮
        tools = [
            ("个\n人\n抽\n取\n音\n效", self.show_personal_sound_settings),
            ("安\n静\n音\n效", self.show_quiet_sound_settings)
        ]
        
        for text, command in tools:
            btn = ttk.Button(
                self.tools_buttons,
                text=text,
                command=command,
                style='ToolsNav.TButton'
            )
            btn.pack(fill=tk.BOTH, expand=True)

    def create_tools_back_button(self):
        """创建返回按钮"""
        if not hasattr(self, 'tools_back_frame'):
            self.tools_back_frame = ttk.Frame(self.left_navbar, style='ToolsNav.TFrame')
        
        # 清除现有的按钮
        for widget in self.tools_back_frame.winfo_children():
            widget.destroy()
        
        # 创建返回按钮
        back_btn = ttk.Button(
            self.tools_back_frame,
            text="返\n回",
            command=self.show_tools_lab,
            style='ToolsNav.TButton'
        )
        back_btn.pack(fill=tk.BOTH, expand=True)

    def show_tools_lab(self):
        """显示妙妙工具实验室页面"""
        self.clear_main_content()
        
        # 显示左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        
        # 隐藏其他子导航栏
        self.timer_buttons.pack_forget()
        if hasattr(self, 'record_frame'):
            self.record_frame.pack_forget()
        
        # 隐藏返回按钮（如果存在）
        if hasattr(self, 'tools_back_frame'):
            self.tools_back_frame.pack_forget()
        
        # 显示工具子导航栏
        self.create_tools_navbar()
        self.tools_buttons.pack(fill=tk.BOTH, expand=True)
        
        # 显示主框架
        if not hasattr(self, 'tools_lab_frame'):
            self.tools_lab_frame = self.create_tools_lab_frame()
        self.tools_lab_frame.pack(expand=True, fill=tk.BOTH)

    def show_personal_sound_settings(self):
        """显示个人抽取音效设置页面"""
        self.clear_main_content()
        
        # 显示左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        
        # 隐藏工具子导航栏
        if hasattr(self, 'tools_buttons'):
            self.tools_buttons.pack_forget()
        
        # 显示返回按钮
        self.create_tools_back_button()
        self.tools_back_frame.pack(fill=tk.BOTH, expand=True)
        
        # 其余代码保持不变...

    def show_quiet_sound_settings(self):
        """显示安静音效设置页面"""
        self.clear_main_content()
        
        # 显示左侧导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        
        # 隐藏工具子导航栏
        if hasattr(self, 'tools_buttons'):
            self.tools_buttons.pack_forget()
        
        # 显示返回按钮
        self.create_tools_back_button()
        self.tools_back_frame.pack(fill=tk.BOTH, expand=True)
        
        # 其余代码保持不变...

    def show_quiet_sound_settings(self):
        """显示安静音效设置页面"""
        # 初始化 pygame mixer
        try:
            import pygame
            pygame.mixer.init()
        except Exception as e:
            Logger.error(f"初始化音频播放器失败: {e}")
            messagebox.showerror("错误", "初始化音频播放器失败")
            return
            
        self.clear_main_content()
        
        # 显示左侧导航栏和工具子导航栏
        if hasattr(self, 'left_navbar'):
            self.left_navbar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        self.create_tools_navbar()
        self.tools_buttons.pack(fill=tk.BOTH, expand=True)
        
        # 如果已经存在框架，直接显示
        if hasattr(self, 'quiet_sound_frame'):
            self.quiet_sound_frame.pack(expand=True, fill=tk.BOTH)
            return
            
        # 创建主框架
        self.quiet_sound_frame = ttk.Frame(self.main_content)
        self.quiet_sound_frame.pack(expand=True, fill=tk.BOTH)

        # 添加标题
        title_label = ttk.Label(self.quiet_sound_frame, text="安静音效", font=("Arial", 24, "bold"))
        title_label.pack(pady=20)
        
        # 创建按钮框架
        buttons_frame = ttk.Frame(self.quiet_sound_frame)
        buttons_frame.pack(expand=True)
        
        # 调整按钮样式 - 加大按钮
        self.style.configure('Sound.TButton',
                            font=('Arial', 14),     # 加大字号
                            padding=12,             # 加大内边距
                            width=12)               # 加宽按钮
        
        # 定义音效按钮及其对应的音效文件
        sounds = {
            "小嘴巴": "mouth.mp3",
            "钢管落地": "pipe.mp3"
        }
        
        # 获取程序目录
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        # 音效文件夹路径
        sounds_dir = os.path.join(base_path, "sounds")
        
        for sound_name, sound_file in sounds.items():
            sound_path = os.path.join(sounds_dir, sound_file)
            btn = ttk.Button(
                buttons_frame, 
                text=sound_name, 
                command=lambda p=sound_path: self.play_sound(p),
                style='Sound.TButton'
            )
            btn.pack(pady=15)  # 增加按钮间距
        
        # 自定义按钮
        custom_btn = ttk.Button(
            buttons_frame, 
            text="自定义", 
            command=self.custom_sound,
            style='Sound.TButton'
        )
        custom_btn.pack(pady=15)  # 增加按钮间距

    def play_sound(self, sound_path):
        """播放指定的音效"""
        try:
            # 检查文件是否存在
            if not os.path.exists(sound_path):
                Logger.error(f"音效文件不存在: {sound_path}")
                messagebox.showerror("错误", f"音效文件不存在:\n{sound_path}")
                return
                
            # 使用完整路径播放音效
            abs_path = os.path.abspath(sound_path)
            Logger.info(f"尝试播放音效: {abs_path}")
            
            # 使用 pygame 播放音频
            import pygame
            try:
                pygame.mixer.music.load(abs_path)
                pygame.mixer.music.play()
                Logger.info(f"音效播放成功: {abs_path}")
            except Exception as e:
                raise Exception(f"pygame 播放失败: {e}")
            
        except Exception as e:
            Logger.error(f"播放音效失败: {e}")
            messagebox.showerror("错误", f"无法播放音效文件:\n{str(e)}")

    def custom_sound(self):
        """允许用户选择自定义音效文件"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择音效文件",
                filetypes=(("音频文件", "*.mp3;*.wav"), ("所有文件", "*.*"))  # 移除 m4a 格式
            )
            if file_path:
                self.play_sound(file_path)
        except Exception as e:
            Logger.error(f"选择自定义音效失败: {e}")
            messagebox.showerror("错误", f"无法选择音效文件:\n{e}")

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
    """自动将 PNG 转换为 ICO 文件"""
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
        
        # 获取快速初始化设置
        self.quick_init = False
        try:
            config = Config()
            self.quick_init = config.get("quick_init")
        except:
            pass
            
        # 设置更新间和增量
        if self.quick_init:
            self.update_interval = 10  # 快速初始化时使用更短的间隔
            self.increment = 4         # 快速初始化时使用更大的增量
        else:
            self.update_interval = 30  # 正常初始化时使用较长的间隔
            self.increment = 1         # 正常初始化时使用较小的增量
            
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        
        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 设窗口大小
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
            # 载和显示图标
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
                 text="Version 5.2",
                 font=('Arial', 12)).pack(pady=(5, 15))  # 减少部分间距
        
        # 创建进度显示框架
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
        self.progress.pack(pady=(5, 30))  # 增加底部距，为版权信息留出空
        
        # 建底部框架
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
            "正在启动程序...",  # 修复"正在动程序..."
            "正在加载配置文件...",
            "正在初始化界面...",
            "正在检查更新...",  # 修复"正在检查新..."
            "准备就绪..."
        ]
        self.current_step = 0
        
        # 强制更新显示
        self.update()
        
        # 开始更新进度
        self.update_progress()

    def update_progress(self):
        """更新进度条和加载文本"""
        if self.progress['value'] < 100:
            # 计算当前步骤
            step_index = min(int(self.progress['value'] / 20), len(self.loading_steps) - 1)
            if step_index != self.current_step:
                self.current_step = step_index
                self.loading_text.config(text=self.loading_steps[step_index])
            
            # 更新进度条和分比
            if self.progress['value'] >= 95:
                # 在接近完时放慢度
                self.progress['value'] += 0.2  # 减小增量
            else:
                self.progress['value'] += self.increment
            
            self.percent_label.config(text=f"{int(self.progress['value'])}%")
            
            # 设置下一次更新
            if self.progress['value'] >= 95:
                # 接近完成时增加间隔
                self.after(100, self.update_progress)  # 增间隔时间
            else:
                self.after(self.update_interval, self.update_progress)

    def destroy(self):
        """销毁启动窗口"""
        super().destroy()

# 在 ChemistryTimer 之添加
class AsyncDrawWindow(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        
        # 设置窗口不在任务栏显示
        self.wm_attributes("-toolwindow", True)
        
        # 直接使用主口的透明度
        main_opacity = master.attributes('-alpha')
        self.attributes('-alpha', main_opacity)
        
        # 使用当前主题的颜色
        self.configure(bg=theme['bg'])
        
        # 设置窗口大小和位置
        width = 300
        height = 200
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # 创建外层框架（使用主题颜色）
        self.flash_frame = ttk.Frame(self)
        self.flash_frame.configure(style='Theme.TFrame')  # 使用主题样式
        self.flash_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 创建内容框架（使用主题颜色）
        self.content_frame = ttk.Frame(self.flash_frame)
        self.content_frame.configure(style='Theme.TFrame')  # 使用主题样式
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # 创建结果标签（使用主题颜色）
        self.result_label = ttk.Label(
            self.content_frame,
            text="",
            style='Theme.TLabel'  # 使用主题样式
        )
        self.result_label.pack(expand=True)
        
        # 创建倒计时标签（使用主题颜色）
        self.countdown_label = ttk.Label(
            self.content_frame,
            text="",
            font=("Arial", 24, "bold"),
            foreground='#FF4500',
            style='Theme.TLabel'  # 使用主题样式
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
        """获取资基础路径"""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.abspath(".")
    
    def get_image(self, name: str) -> Optional[ImageTk.PhotoImage]:
        """获取图资源"""
        if name in self.cache:
            return self.cache[name]
            
        try:
            path = os.path.join(self.base_path, name)
            image = Image.open(path)
            photo = ImageTk.PhotoImage(image)
            self.cache[name] = photo
            return photo
        except Exception as e:
            Logger.error(f"加载片 {name} 失败: {str(e)}")
            return None
            
    def get_icon(self) -> Optional[str]:
        """获取标文件路径"""
        for icon_file in ["icon.ico", "icon.png", "化学计时器.png"]:
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
            error_msg = f"执行 {func.__name__} 时发生错误: {str(e)}"  # 修复"时发错误"
            Logger.error(error_msg)
            messagebox.showerror("错误", f"操作失败:\n{str(e)}")
            return None
    return wrapper

# 修改主程序入口
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
        
        # 设置窗口关闭处
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
        # 如发生错误确保启动窗口被销毁
        if splash:
            splash.destroy()
        # 显示错误消息
        messagebox.showerror("启动错误", f"程序启动时发生错误：\n{str(e)}")
        sys.exit(1)


