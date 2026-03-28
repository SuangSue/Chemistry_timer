# installer.py - 课堂点名计时器 自定义安装/卸载程序
import sys, os, shutil, time, winreg, ctypes, random
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QCheckBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QPainterPath, QPixmap

APP_NAME      = '课堂点名计时器'
APP_VERSION   = '6.0'
APP_EXE       = 'ClassTimer.exe'
UNINSTALL_EXE = 'Uninstall.exe'
PUBLISHER     = 'ClassroomTimer'
DEFAULT_DIR   = str(Path(os.environ.get('ProgramFiles', 'C:\\Program Files')) / APP_NAME)
REG_KEY       = f'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}'
PAYLOAD       = [APP_EXE, 'pictures', 'sounds']

def res_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent

def get_install_dir_from_reg():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_KEY) as k:
            val, _ = winreg.QueryValueEx(k, 'InstallLocation')
            return val
    except Exception:
        return None


class InstallWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    def __init__(self, dst, desktop, startup):
        super().__init__()
        self.dst = Path(dst); self.desktop = desktop; self.startup = startup
    def run(self):
        try:
            src = res_dir(); self.dst.mkdir(parents=True, exist_ok=True)
            tasks = []
            for item in PAYLOAD:
                sp = src / item
                if sp.is_dir():
                    for f in sp.rglob('*'):
                        if f.is_file(): tasks.append((f, self.dst / item / f.relative_to(sp)))
                elif sp.is_file(): tasks.append((sp, self.dst / item))
            total = max(len(tasks), 1)
            for i, (sf, df) in enumerate(tasks):
                df.parent.mkdir(parents=True, exist_ok=True)
                self.progress.emit(int(i / total * 60), f'复制：{sf.name}')
                shutil.copy2(sf, df); time.sleep(0.015)
            self.progress.emit(65, '写入卸载程序...')
            self_exe = Path(sys.executable) if getattr(sys, 'frozen', False) else None
            if self_exe and self_exe.exists():
                shutil.copy2(self_exe, self.dst / UNINSTALL_EXE)
            self.progress.emit(72, '创建快捷方式...')
            exe = str(self.dst / APP_EXE)
            uninstall_exe = str(self.dst / UNINSTALL_EXE)
            if self.desktop:
                self._lnk(exe, str(Path(os.environ.get('USERPROFILE','')) / 'Desktop' / f'{APP_NAME}.lnk'))
            sm = Path(os.environ.get('APPDATA','')) / 'Microsoft/Windows/Start Menu/Programs'
            sm_dir = sm / APP_NAME
            sm_dir.mkdir(parents=True, exist_ok=True)
            self._lnk(exe, str(sm_dir / f'{APP_NAME}.lnk'))
            self._lnk(uninstall_exe, str(sm_dir / f'卸载 {APP_NAME}.lnk'), args='--uninstall')
            if self.startup:
                self._reg_startup(exe)
            self.progress.emit(88, '写入注册表...')
            self._reg(exe, uninstall_exe)
            self.progress.emit(100, '安装完成！'); time.sleep(0.3)
            self.finished.emit(True, '')
        except Exception as e: self.finished.emit(False, str(e))
    def _lnk(self, target, link, args=''):
        """创建快捷方式，优先用 PowerShell，回退到 VBS"""
        import subprocess
        link = str(link); target = str(target)
        wdir = str(Path(target).parent)
        # 方法1：PowerShell（无需额外依赖，最可靠）
        try:
            args_line = f'$s.Arguments = "{args}"; ' if args else ''
            ps = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{link}"); '
                f'$s.TargetPath = "{target}"; '
                f'$s.WorkingDirectory = "{wdir}"; '
                f'$s.IconLocation = "{target},0"; '
                f'{args_line}'
                f'$s.Save()'
            )
            ret = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', ps],
                capture_output=True, timeout=20
            )
            if ret.returncode == 0 and Path(link).exists():
                return True
        except Exception:
            pass
        # 方法2：win32com
        try:
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(link)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = wdir
            shortcut.IconLocation = f'{target},0'
            if args: shortcut.Arguments = args
            shortcut.save()
            return True
        except Exception:
            pass
        # 方法3：VBS 脚本
        try:
            args_line = f'\r\nl.Arguments="{args}"' if args else ''
            vbs = (
                f'Set s=CreateObject("WScript.Shell")\r\n'
                f'Set l=s.CreateShortcut("{link}")\r\n'
                f'l.TargetPath="{target}"\r\n'
                f'l.WorkingDirectory="{wdir}"\r\n'
                f'l.IconLocation="{target},0"{args_line}\r\n'
                f'l.Save\r\n'
            )
            tmp = Path(os.environ.get('TEMP', 'C:\\Temp')) / '_inst_lnk.vbs'
            tmp.write_text(vbs, encoding='utf-8')
            ret = subprocess.run(
                ['cscript', '//nologo', str(tmp)],
                capture_output=True, timeout=15
            )
            tmp.unlink(missing_ok=True)
            return Path(link).exists()
        except Exception:
            return False

    def _reg(self, exe, uninstall_exe):
        try:
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, REG_KEY) as k:
                for kv in [
                    ('DisplayName',          APP_NAME),
                    ('DisplayVersion',        APP_VERSION),
                    ('Publisher',             PUBLISHER),
                    ('InstallLocation',       str(self.dst)),
                    ('UninstallString',       f'"{uninstall_exe}" --uninstall'),
                    ('QuietUninstallString',  f'"{uninstall_exe}" --uninstall --quiet'),
                    ('DisplayIcon',           exe),
                ]:
                    winreg.SetValueEx(k, kv[0], 0, winreg.REG_SZ, kv[1])
                winreg.SetValueEx(k, 'NoModify',      0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(k, 'EstimatedSize', 0, winreg.REG_DWORD, 80000)
        except Exception as e: print(f'reg: {e}')

    def _reg_startup(self, exe):
        """将程序加入注册表开机自启动（HKCU Run）"""
        try:
            run_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        except Exception as e: print(f'reg_startup: {e}')


class UninstallWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    def __init__(self, install_dir, remove_data):
        super().__init__()
        self.install_dir = Path(install_dir)
        self.remove_data = remove_data
    def run(self):
        try:
            self.progress.emit(5,  '正在停止程序...')
            self._kill_process(APP_EXE); time.sleep(0.5)
            self.progress.emit(20, '删除快捷方式...')
            self._remove_shortcuts()
            self.progress.emit(40, '清理注册表...')
            self._remove_reg()
            self.progress.emit(55, '删除程序文件...')
            self._remove_files()
            self.progress.emit(100,'卸载完成！'); time.sleep(0.4)
            self.finished.emit(True, '')
        except Exception as e:
            self.finished.emit(False, str(e))
    def _kill_process(self, name):
        try:
            import subprocess
            subprocess.run(['taskkill','/F','/IM',name], creationflags=0x08000000, timeout=5)
        except Exception: pass
    def _remove_shortcuts(self):
        sm = Path(os.environ.get('APPDATA','')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
        for p in [
            Path(os.environ.get('USERPROFILE','')) / 'Desktop' / f'{APP_NAME}.lnk',
            sm / f'{APP_NAME}.lnk',
        ]:
            try:
                if p.exists(): p.unlink()
            except Exception: pass
        sm_dir = sm / APP_NAME
        if sm_dir.exists(): shutil.rmtree(sm_dir, ignore_errors=True)
        # 清理注册表开机自启动项
        try:
            run_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0,
                                winreg.KEY_SET_VALUE) as k:
                try: winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError: pass
        except Exception: pass
    def _remove_reg(self):
        try: winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, REG_KEY)
        except Exception: pass
    def _remove_files(self):
        d = self.install_dir
        if not d.exists(): return
        keep = {'rosters','config','data','userdata'} if not self.remove_data else set()
        # 先删除除卸载程序自身以外的所有文件
        for item in list(d.iterdir()):
            if item.name == UNINSTALL_EXE: continue
            if item.name.lower() in keep: continue
            try:
                if item.is_dir(): shutil.rmtree(item, ignore_errors=True)
                else: item.unlink(missing_ok=True)
            except Exception: pass
        # 如果勾选了清除用户数据，删除 %APPDATA%\ClassroomTimer
        if self.remove_data:
            appdata_dir = Path(os.environ.get('APPDATA', '')) / 'ClassroomTimer'
            if appdata_dir.exists():
                try: shutil.rmtree(appdata_dir, ignore_errors=True)
                except Exception: pass
        # 延迟用 PowerShell 删除自身和安装目录（等待进程完全退出）
        import subprocess
        uninstall_exe = str(d / UNINSTALL_EXE).replace("'", "''")
        d_str = str(d).replace("'", "''")
        ps_cmd = (
            f"Start-Sleep -Seconds 4; "
            f"Remove-Item -LiteralPath '{uninstall_exe}' -Force -ErrorAction SilentlyContinue; "
            f"Start-Sleep -Seconds 1; "
            f"Remove-Item -LiteralPath '{d_str}' -Recurse -Force -ErrorAction SilentlyContinue"
        )
        subprocess.Popen(
            ['powershell', '-NoProfile', '-NonInteractive',
             '-WindowStyle', 'Hidden', '-Command', ps_cmd],
            creationflags=0x00000008  # DETACHED_PROCESS
        )


# ══════════════════════════════════════════════════════════
# 粒子背景 & 进度条
# ══════════════════════════════════════════════════════════
class _Pt:
    def __init__(self, W, H):
        self.W=W; self.H=H; self._s()
    def _s(self):
        self.x=random.uniform(0,self.W); self.y=random.uniform(self.H*.4,self.H)
        self.r=random.uniform(1.5,3.5); self.vx=random.uniform(-.3,.3); self.vy=random.uniform(-.65,-.18)
        self.a=random.uniform(35,95)
        self.c=random.choice([QColor(218,178,50),QColor(245,210,90),QColor(200,160,55),QColor(255,235,130)])
    def step(self):
        self.x+=self.vx; self.y+=self.vy; self.a-=0.32
        if self.y<-8 or self.a<=0: self._s(); self.y=self.H+4

class ParticleBg(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._pts=[]; self._t=QTimer(self); self._t.setInterval(22); self._t.timeout.connect(self._tick)
    def start(self):
        W,H=max(self.width(),620),max(self.height(),480)
        self._pts=[_Pt(W,H) for _ in range(44)]; self._t.start()
    def _tick(self):
        for p in self._pts: p.step()
        self.update()
    def paintEvent(self, e):
        if not self._pts: return
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for pt in self._pts:
            c=QColor(pt.c); c.setAlpha(max(0,int(pt.a)))
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawEllipse(int(pt.x-pt.r),int(pt.y-pt.r),int(pt.r*2),int(pt.r*2))

class FancyBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self._v=0; self._sh=0.0; self.setFixedHeight(10)
        t=QTimer(self); t.setInterval(18); t.timeout.connect(self._tick); t.start()
    def set_value(self, v): self._v=max(0,min(100,v)); self.update()
    def _tick(self): self._sh=(self._sh+0.020)%1.0; self.update()
    def paintEvent(self, e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W,H=self.width(),self.height(); r=H//2
        p.setPen(Qt.NoPen); p.setBrush(QColor(255,255,255,22)); p.drawRoundedRect(0,0,W,H,r,r)
        fw=int(W*self._v/100)
        if fw>0:
            g=QLinearGradient(0,0,fw,0)
            g.setColorAt(0.0,QColor(180,140,40)); g.setColorAt(0.5,QColor(240,200,75)); g.setColorAt(1.0,QColor(255,225,105))
            p.setBrush(g); p.drawRoundedRect(0,0,fw,H,r,r)
            sx=int((self._sh-0.12)*fw); sw=max(int(fw*0.16),20)
            sg=QLinearGradient(sx,0,sx+sw,0)
            sg.setColorAt(0.0,QColor(255,255,255,0)); sg.setColorAt(0.5,QColor(255,255,255,85)); sg.setColorAt(1.0,QColor(255,255,255,0))
            p.setBrush(sg); p.drawRoundedRect(max(0,sx),0,sw,H,r,r)



class _Pt:
    def __init__(self, W, H):
        self.W=W; self.H=H; self._s()
    def _s(self):
        self.x=random.uniform(0,self.W); self.y=random.uniform(self.H*.4,self.H)
        self.r=random.uniform(1.5,3.5); self.vx=random.uniform(-.3,.3); self.vy=random.uniform(-.65,-.18)
        self.a=random.uniform(35,95)
        self.c=random.choice([QColor(218,178,50),QColor(245,210,90),QColor(200,160,55),QColor(255,235,130)])
    def step(self):
        self.x+=self.vx; self.y+=self.vy; self.a-=0.32
        if self.y<-8 or self.a<=0: self._s(); self.y=self.H+4

class ParticleBg(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._pts=[]; self._t=QTimer(self); self._t.setInterval(22); self._t.timeout.connect(self._tick)
    def start(self):
        W,H=max(self.width(),620),max(self.height(),480)
        self._pts=[_Pt(W,H) for _ in range(44)]; self._t.start()
    def _tick(self):
        for p in self._pts: p.step()
        self.update()
    def paintEvent(self, e):
        if not self._pts: return
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for pt in self._pts:
            c=QColor(pt.c); c.setAlpha(max(0,int(pt.a)))
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawEllipse(int(pt.x-pt.r),int(pt.y-pt.r),int(pt.r*2),int(pt.r*2))

class FancyBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self._v=0; self._sh=0.0; self.setFixedHeight(10)
        t=QTimer(self); t.setInterval(18); t.timeout.connect(self._tick); t.start()
    def set_value(self, v): self._v=max(0,min(100,v)); self.update()
    def _tick(self): self._sh=(self._sh+0.020)%1.0; self.update()
    def paintEvent(self, e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W,H=self.width(),self.height(); r=H//2
        p.setPen(Qt.NoPen); p.setBrush(QColor(255,255,255,22)); p.drawRoundedRect(0,0,W,H,r,r)
        fw=int(W*self._v/100)
        if fw>0:
            g=QLinearGradient(0,0,fw,0)
            g.setColorAt(0.0,QColor(180,140,40)); g.setColorAt(0.5,QColor(240,200,75)); g.setColorAt(1.0,QColor(255,225,105))
            p.setBrush(g); p.drawRoundedRect(0,0,fw,H,r,r)
            sx=int((self._sh-0.12)*fw); sw=max(int(fw*0.16),20)
            sg=QLinearGradient(sx,0,sx+sw,0)
            sg.setColorAt(0.0,QColor(255,255,255,0)); sg.setColorAt(0.5,QColor(255,255,255,85)); sg.setColorAt(1.0,QColor(255,255,255,0))
            p.setBrush(sg); p.drawRoundedRect(max(0,sx),0,sw,H,r,r)


class BaseWindow(QWidget):
    W, H = 620, 480
    def __init__(self, title_text):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.W, self.H)
        from PyQt5.QtGui import QIcon
        _meipass = getattr(sys, "_MEIPASS", None)
        icon_candidates = []
        if _meipass: icon_candidates += [Path(_meipass) / "icon.ico"]
        icon_candidates += [Path(__file__).parent / "icon.ico", res_dir() / "pictures" / "icon.ico", res_dir() / "pictures" / "icon.png"]
        for _ip in icon_candidates:
            if _ip.exists(): self.setWindowIcon(QIcon(str(_ip))); break
        self._drag_pos = None
        self._build(title_text)
        scr = QApplication.primaryScreen().availableGeometry()
        self.move((scr.width()-self.W)//2, (scr.height()-self.H)//2)
        self.setWindowOpacity(0)
        a = QPropertyAnimation(self, b"windowOpacity")
        a.setDuration(480); a.setStartValue(0); a.setEndValue(1)
        a.setEasingCurve(QEasingCurve.OutCubic); a.start(); self._fa = a
        self._bg.start()
    def _build(self, title_text):
        self._bg = ParticleBg(self); self._bg.setGeometry(0,0,self.W,self.H)
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        bar = QWidget(); bar.setFixedHeight(46); bar.setStyleSheet("background:transparent;")
        bl = QHBoxLayout(bar); bl.setContentsMargins(22,0,10,0)
        tlbl = QLabel(title_text)
        tlbl.setStyleSheet("color:rgba(255,245,195,220);font-size:13px;font-weight:700;font-family:'Microsoft YaHei';background:transparent;")
        xb = QPushButton("x"); xb.setFixedSize(30,30); xb.setCursor(Qt.PointingHandCursor)
        xb.setStyleSheet("QPushButton{background:transparent;color:rgba(255,200,180,180);border:none;font-size:14px;border-radius:8px;}QPushButton:hover{background:rgba(220,60,40,200);color:#fff;}")
        xb.clicked.connect(self.close)
        bl.addWidget(tlbl,1); bl.addWidget(xb); root.addWidget(bar)
        body = QWidget(); body.setStyleSheet("background:transparent;")
        self._lay = QVBoxLayout(body); self._lay.setContentsMargins(44,8,44,30); self._lay.setSpacing(0)
        root.addWidget(body,1)
    def _clear(self):
        while self._lay.count():
            it = self._lay.takeAt(0); w = it.widget()
            if w: w.setParent(None); w.hide(); w.deleteLater()
            elif it.layout():
                sub = it.layout()
                while sub.count():
                    si = sub.takeAt(0); sw = si.widget()
                    if sw: sw.setParent(None); sw.hide(); sw.deleteLater()
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self._drag_pos=e.globalPos()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self,e):
        if e.buttons()&Qt.LeftButton and self._drag_pos: self.move(e.globalPos()-self._drag_pos)
    def mouseReleaseEvent(self,e): self._drag_pos=None
    def paintEvent(self, e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W,H=self.W,self.H; path=QPainterPath(); path.addRoundedRect(0,0,W,H,16,16)
        g=QLinearGradient(0,0,0,H)
        g.setColorAt(0.0,QColor(28,24,18,235)); g.setColorAt(0.5,QColor(22,18,12,242)); g.setColorAt(1.0,QColor(18,14,8,248))
        p.fillPath(path,QBrush(g))
        p.setPen(QPen(QColor(200,170,60,120),1.2)); p.drawPath(path)
        tg=QLinearGradient(0,0,W,0)
        tg.setColorAt(0.0,QColor(180,140,40,0)); tg.setColorAt(0.3,QColor(230,190,70,90))
        tg.setColorAt(0.7,QColor(230,190,70,90)); tg.setColorAt(1.0,QColor(180,140,40,0))
        p.setPen(Qt.NoPen); p.setBrush(tg); p.drawRect(0,0,W,2)
    def _gold_btn(self,text,w=160):
        b=QPushButton(text); b.setFixedSize(w,40); b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 rgba(180,140,40,220),stop:0.5 rgba(230,190,70,240),stop:1 rgba(180,140,40,220));color:#1a1408;border:none;border-radius:10px;font-size:13px;font-weight:700;font-family:'Microsoft YaHei';}QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 rgba(210,170,60,255),stop:0.5 rgba(255,215,80,255),stop:1 rgba(210,170,60,255));}QPushButton:pressed{background:rgba(160,120,30,230);}")
        return b
    def _ghost_btn(self,text,w=120):
        b=QPushButton(text); b.setFixedSize(w,40); b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("QPushButton{background:rgba(255,255,255,12);color:rgba(220,205,150,200);border:1px solid rgba(200,170,60,80);border-radius:10px;font-size:13px;font-family:'Microsoft YaHei';}QPushButton:hover{background:rgba(255,255,255,22);color:rgba(240,220,160,255);}")
        return b
    def _red_btn(self,text,w=160):
        b=QPushButton(text); b.setFixedSize(w,40); b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("QPushButton{background:rgba(180,50,40,200);color:#fff0ee;border:none;border-radius:10px;font-size:13px;font-weight:700;font-family:'Microsoft YaHei';}QPushButton:hover{background:rgba(210,60,50,230);}QPushButton:pressed{background:rgba(150,35,30,220);}")
        return b
    def _h1(self,text):
        l=QLabel(text); l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("font-size:24px;font-weight:900;color:rgba(255,245,195,230);font-family:'Microsoft YaHei';background:transparent;letter-spacing:2px;")
        return l
    def _sub(self,text):
        l=QLabel(text); l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("font-size:12px;color:rgba(210,195,135,160);font-family:'Microsoft YaHei';background:transparent;")
        return l
    def _divider(self):
        f=QFrame(); f.setFixedHeight(1); f.setStyleSheet("background:rgba(200,170,60,35);border:none;"); return f
    def _checkbox(self,text,checked):
        cb=QCheckBox(text); cb.setChecked(checked)
        cb.setStyleSheet("QCheckBox{color:rgba(225,210,155,200);font-size:13px;font-family:'Microsoft YaHei';background:transparent;spacing:8px;}QCheckBox::indicator{width:16px;height:16px;border-radius:4px;border:1px solid rgba(200,170,60,100);background:rgba(255,255,255,10);}QCheckBox::indicator:checked{background:rgba(220,180,55,200);border:1px solid rgba(220,180,55,255);}")
        return cb



class InstallerWindow(BaseWindow):
    def __init__(self):
        self._install_dir = DEFAULT_DIR
        super().__init__(f"  {APP_NAME}  安装向导")
        self._show_welcome()

    def _show_welcome(self):
        self._clear(); lay=self._lay
        il=QLabel(); il.setAlignment(Qt.AlignCenter)
        pp=str(res_dir()/"pictures"/"icon.png")
        if os.path.exists(pp):
            pix=QPixmap(pp).scaled(76,76,Qt.KeepAspectRatio,Qt.SmoothTransformation); il.setPixmap(pix)
        lay.addStretch(1); lay.addWidget(il)
        lay.addSpacing(14); lay.addWidget(self._h1(f"欢迎安装  {APP_NAME}"))
        lay.addSpacing(7);  lay.addWidget(self._sub(f"版本 {APP_VERSION}    ·    专为课堂教学设计"))
        lay.addSpacing(26); lay.addWidget(self._divider())
        desc=QLabel("本向导将引导您完成程序安装。\n点击「下一步」继续，点击「x」退出安装。")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size:13px;color:rgba(230,215,160,185);font-family:'Microsoft YaHei';background:transparent;")
        lay.addSpacing(18); lay.addWidget(desc); lay.addStretch(2)
        btn=self._gold_btn("下一步  →"); btn.clicked.connect(self._show_options)
        row=QHBoxLayout(); row.addStretch(); row.addWidget(btn); lay.addLayout(row)

    def _show_options(self):
        self._clear(); lay=self._lay
        lay.addSpacing(10); lay.addWidget(self._h1("安装选项"))
        lay.addSpacing(6);  lay.addWidget(self._sub("配置安装目录与快捷方式"))
        lay.addSpacing(20); lay.addWidget(self._divider()); lay.addSpacing(18)
        dl=QLabel("安装目录"); dl.setStyleSheet("font-size:12px;color:rgba(200,185,130,200);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(dl); lay.addSpacing(6)
        dr=QHBoxLayout(); dr.setSpacing(8)
        self._dir_lbl=QLabel(self._install_dir)
        self._dir_lbl.setStyleSheet("background:rgba(255,255,255,10);color:rgba(240,225,165,220);border:1px solid rgba(200,170,60,60);border-radius:8px;padding:6px 10px;font-size:12px;")
        br=self._ghost_btn("浏览...", 80); br.clicked.connect(self._browse)
        dr.addWidget(self._dir_lbl,1); dr.addWidget(br); lay.addLayout(dr); lay.addSpacing(20)
        ol=QLabel("附加选项"); ol.setStyleSheet("font-size:12px;color:rgba(200,185,130,200);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(ol); lay.addSpacing(8)
        self._cb_desk=self._checkbox("创建桌面快捷方式",True)
        self._cb_startup=self._checkbox("开机自动启动",True)
        lay.addWidget(self._cb_desk); lay.addSpacing(4); lay.addWidget(self._cb_startup)
        lay.addStretch(1); lay.addWidget(self._divider()); lay.addSpacing(14)
        br2=QHBoxLayout(); br2.setSpacing(12)
        bk=self._ghost_btn("← 上一步"); bk.clicked.connect(self._show_welcome)
        nx=self._gold_btn("开始安装  ▶"); nx.clicked.connect(self._start_install)
        br2.addStretch(); br2.addWidget(bk); br2.addWidget(nx); lay.addLayout(br2)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择安装目录", self._install_dir)
        if d:
            from pathlib import Path as _P
            p = _P(d)
            if p.name != APP_NAME:
                p = p / APP_NAME
            self._install_dir = str(p)
            self._dir_lbl.setText(self._install_dir)

    def _start_install(self):
        self._install_dir = self._dir_lbl.text()
        desktop = self._cb_desk.isChecked(); startup = self._cb_startup.isChecked()
        self._clear(); lay = self._lay
        lay.addSpacing(20); lay.addWidget(self._h1("正在安装..."))
        lay.addSpacing(6);  lay.addWidget(self._sub("请稍候，安装程序正在复制文件"))
        lay.addSpacing(32); lay.addWidget(self._divider()); lay.addSpacing(24)
        self._bar = FancyBar(); lay.addWidget(self._bar); lay.addSpacing(14)
        self._status = QLabel("准备中...")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("font-size:12px;color:rgba(200,185,130,180);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(self._status); lay.addStretch(1)
        self._worker = InstallWorker(self._install_dir, desktop, startup)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_prog)
        self._worker.finished.connect(self._on_done)
        self._thread.start()

    def _on_prog(self, v, msg): self._bar.set_value(v); self._status.setText(msg)
    def _on_done(self, ok, err):
        self._thread.quit(); self._thread.wait()
        if ok: self._show_done()
        else:  self._show_error(err)

    def _show_done(self):
        self._clear(); lay = self._lay
        ok_l = QLabel("✓"); ok_l.setAlignment(Qt.AlignCenter)
        ok_l.setStyleSheet("font-size:58px;color:rgba(160,220,90,220);background:transparent;")
        lay.addStretch(1); lay.addWidget(ok_l)
        lay.addSpacing(8); lay.addWidget(self._h1("安装完成！"))
        lay.addSpacing(8)
        sub = QLabel(f"{APP_NAME} 已成功安装。")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size:12px;color:rgba(210,195,135,160);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(sub); lay.addStretch(1); lay.addWidget(self._divider()); lay.addSpacing(14)
        row = QHBoxLayout(); row.setSpacing(12)
        self._cb_run = self._checkbox("立即启动程序", True)
        fin = self._gold_btn("完成", 120); fin.clicked.connect(self._finish)
        row.addWidget(self._cb_run); row.addStretch(); row.addWidget(fin)
        lay.addLayout(row)

    def _show_error(self, err):
        self._clear(); lay = self._lay
        el = QLabel("✕"); el.setAlignment(Qt.AlignCenter)
        el.setStyleSheet("font-size:58px;color:rgba(220,80,60,200);background:transparent;")
        lay.addStretch(1); lay.addWidget(el)
        lay.addSpacing(8); lay.addWidget(self._h1("安装失败"))
        lay.addSpacing(8)
        em = QLabel(err); em.setAlignment(Qt.AlignCenter); em.setWordWrap(True)
        em.setStyleSheet("font-size:11px;color:rgba(220,160,140,200);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(em); lay.addStretch(1)
        lay.addWidget(self._divider()); lay.addSpacing(14)
        row = QHBoxLayout()
        cls = self._gold_btn("关闭", 120); cls.clicked.connect(self.close)
        row.addStretch(); row.addWidget(cls); lay.addLayout(row)

    def _finish(self):
        if hasattr(self, "_cb_run") and self._cb_run.isChecked():
            exe = str(Path(self._install_dir) / APP_EXE)
            if os.path.exists(exe):
                import subprocess
                try:
                    # 用 cmd /c start 启动，脱离安装器进程树，避免权限继承问题
                    subprocess.Popen(
                        ['cmd', '/c', 'start', '', exe],
                        creationflags=0x08000000,  # CREATE_NO_WINDOW
                        close_fds=True
                    )
                except Exception:
                    try:
                        subprocess.Popen([exe], creationflags=0x00000008)
                    except Exception:
                        pass
        self.close()



class UninstallerWindow(BaseWindow):
    def __init__(self, install_dir):
        self._install_dir = install_dir
        super().__init__(f"  {APP_NAME}  卸载向导")
        self._show_confirm()

    def _show_confirm(self):
        self._clear(); lay = self._lay
        el = QLabel("⚠"); el.setAlignment(Qt.AlignCenter)
        el.setStyleSheet("font-size:52px;color:rgba(220,160,50,200);background:transparent;")
        lay.addStretch(1); lay.addWidget(el)
        lay.addSpacing(8); lay.addWidget(self._h1(f"卸载  {APP_NAME}"))
        lay.addSpacing(8)
        sub = QLabel(f"将从以下位置卸载程序：\n{self._install_dir}")
        sub.setAlignment(Qt.AlignCenter); sub.setWordWrap(True)
        sub.setStyleSheet("font-size:12px;color:rgba(210,195,135,160);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(sub)
        lay.addSpacing(20); lay.addWidget(self._divider()); lay.addSpacing(14)
        self._cb_data = self._checkbox("同时删除用户数据（名单、配置等）", False)
        lay.addWidget(self._cb_data)
        lay.addStretch(1); lay.addWidget(self._divider()); lay.addSpacing(14)
        row = QHBoxLayout(); row.setSpacing(12)
        bk = self._ghost_btn("取消", 120); bk.clicked.connect(self.close)
        nx = self._red_btn("开始卸载  ▶", 160); nx.clicked.connect(self._start_uninstall)
        row.addStretch(); row.addWidget(bk); row.addWidget(nx)
        lay.addLayout(row)

    def _start_uninstall(self):
        remove_data = self._cb_data.isChecked()
        self._clear(); lay = self._lay
        lay.addSpacing(20); lay.addWidget(self._h1("正在卸载..."))
        lay.addSpacing(6);  lay.addWidget(self._sub("请稍候，正在清理程序文件"))
        lay.addSpacing(32); lay.addWidget(self._divider()); lay.addSpacing(24)
        self._bar = FancyBar(); lay.addWidget(self._bar); lay.addSpacing(14)
        self._status = QLabel("准备中...")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("font-size:12px;color:rgba(200,185,130,180);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(self._status); lay.addStretch(1)
        self._worker = UninstallWorker(self._install_dir, remove_data)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_prog)
        self._worker.finished.connect(self._on_done)
        self._thread.start()

    def _on_prog(self, v, msg): self._bar.set_value(v); self._status.setText(msg)
    def _on_done(self, ok, err):
        self._thread.quit(); self._thread.wait()
        if ok: self._show_done()
        else:  self._show_error(err)

    def _show_done(self):
        self._clear(); lay = self._lay
        ok_l = QLabel("✓"); ok_l.setAlignment(Qt.AlignCenter)
        ok_l.setStyleSheet("font-size:58px;color:rgba(160,220,90,220);background:transparent;")
        lay.addStretch(1); lay.addWidget(ok_l)
        lay.addSpacing(8); lay.addWidget(self._h1("卸载完成！"))
        lay.addSpacing(8)
        sub = QLabel(f"{APP_NAME} 已成功从您的计算机中卸载。")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size:12px;color:rgba(210,195,135,160);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(sub); lay.addStretch(1)
        lay.addWidget(self._divider()); lay.addSpacing(14)
        row = QHBoxLayout()
        fin = self._gold_btn("关闭", 120)
        fin.clicked.connect(self.close)
        row.addStretch(); row.addWidget(fin)
        lay.addLayout(row)

    def _show_error(self, err):
        self._clear(); lay = self._lay
        el = QLabel("✕"); el.setAlignment(Qt.AlignCenter)
        el.setStyleSheet("font-size:58px;color:rgba(220,80,60,200);background:transparent;")
        lay.addStretch(1); lay.addWidget(el)
        lay.addSpacing(8); lay.addWidget(self._h1("卸载失败"))
        lay.addSpacing(8)
        em = QLabel(err); em.setAlignment(Qt.AlignCenter); em.setWordWrap(True)
        em.setStyleSheet("font-size:11px;color:rgba(220,160,140,200);font-family:'Microsoft YaHei';background:transparent;")
        lay.addWidget(em); lay.addStretch(1)
        lay.addWidget(self._divider()); lay.addSpacing(14)
        row = QHBoxLayout()
        cls = self._gold_btn("关闭", 120); cls.clicked.connect(self.close)
        row.addStretch(); row.addWidget(cls); lay.addLayout(row)


# ══════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setFont(__import__("PyQt5.QtGui", fromlist=["QFont"]).QFont("Microsoft YaHei", 10))

    # 判断是否为卸载模式：
    # 1. 命令行有 --uninstall 参数（从控制面板/注册表触发）
    # 2. 可执行文件名包含 uninstall/uninst（双击 Uninstall.exe 触发）
    _exe_name = Path(sys.executable).stem.lower() if getattr(sys, 'frozen', False) else ''
    _is_uninstall = ('--uninstall' in sys.argv or
                     'uninstall' in _exe_name or
                     'uninst' in _exe_name)

    if _is_uninstall:
        install_dir = get_install_dir_from_reg()
        if not install_dir:
            install_dir = str(Path(sys.executable).parent) if getattr(sys, 'frozen', False) else DEFAULT_DIR
        win = UninstallerWindow(install_dir)
    else:
        win = InstallerWindow()

    win.show()
    sys.exit(app.exec_())
