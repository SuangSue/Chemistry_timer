<div align="center">

<img src="pictures/icon.png" width="140" height="140" alt="课堂点名计时器" style="border-radius: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.15);" />

# 🎓 课堂点名计时器

**ClassroomTimer · 专为课堂教学设计的轻量工具集**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-6.0-ff6b6b?style=for-the-badge)]()

[🚀 快速开始](#-快速开始) · [✨ 功能预览](#-功能预览) · [📖 功能介绍](#-功能介绍) · [❓ 常见问题](#-常见问题)

</div>

---

## 📌 简介

课堂点名计时器是一款专为教师打造的 Windows 桌面工具，集 **随机点名**、**课堂计时** 等功能于一体。

程序以一个悬浮小球的形式常驻屏幕角落，不遮挡教学内容，需要时一键唤出。支持拖放名单、全局热键抽签、日间/夜间主题，是课堂教学的得力助手。

以翻页笔为工具的遥控抽签满足教师在任意位置随时随地抽签，小窗口置顶显示，不影响 PPT、其他工具正常使用。

---

## ✨ 功能预览

| 功能 | 说明 |
|------|------|
| 🎱 **悬浮小球** | 常驻屏幕，30秒无操作自动贴边隐藏，悬停恢复 |
| 🎲 **随机点名** | 加权随机算法，越久未被点到概率越高 |
| ⏱ **课堂计时** | 倒计时 / 正计时，音效提醒 |
| 🏝 **时间岛** | 浮动时间显示组件，不影响其他窗口 |
| ⌨️ **全局热键抽签** | 任意场景一键异步抽签，无需切换窗口 |
| 🌙 **双主题** | 日间暖色 / 夜间冷色，一键切换 |
| 📋 **名单管理** | 支持 txt / xlsx / xls / csv / docx / doc 导入 |
| ✏️ **屏幕批注** | *(开发中)* 屏幕透明画布，多色画笔与橡皮擦 |
| 🤖 **自动化调度** | *(开发中)* 定时任务，自动执行指定操作 |

---

## 🚀 快速开始

### 方式一：官网下载（推荐）⭐

前往官网 **[chemistrytimer.top](https://chemistrytimer.top)** 下载最新版安装包，双击运行安装向导即可。

具体使用教程可参阅网站"帮助与反馈"部分。

**系统要求：** Windows 10 / 11，无需安装 Python

### 方式二：GitHub Release

在 Release 处直接下载程序安装包。

### 方式三：源码运行

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/classtimer.git
cd classtimer

# 安装依赖
pip install -r requirements.txt

# 启动程序
python main.py
```

---

## 📖 功能介绍

### 🎱 悬浮小球

程序启动后，屏幕上会出现一个可自由拖动的浮球。

<img src="pictures/p5/low-distraction.png" width="300" alt="悬浮小球演示" />

- **单击** 展开主面板
- **拖动** 调整位置
- **30秒无操作** → 自动滑向屏幕边缘贴边
- **贴边3秒后** → 没入屏幕边缘（半透明），不遮挡内容
- **鼠标悬停** → 自动弹出

### 🎲 随机点名

采用**加权随机算法**，每次被点到的同学权重降低，长期未被点到的同学权重升高，确保点名更加公平均衡。

<img src="pictures/p5/random-pick.png" width="300" alt="随机点名界面" />

- 支持批量导入名单（拖拽文件到窗口即可）
- 支持自定义每次抽取人数
- 历史记录与权重自动保存
- **全局热键**（默认 `Tab`）在任何场景下触发异步抽签

**支持的名单格式：**

| 格式 | 说明 |
|------|------|
| `.txt` | 每行一个姓名 |
| `.xlsx` / `.xls` | Excel 表格，自动识别姓名列 |
| `.csv` | CSV 表格 |
| `.docx` / `.doc` | Word 文档，支持表格和段落 |

### ⌨️ 全局热键抽签

这是本程序最具特色的功能之一。

**无论当前打开什么程序、处于哪个窗口**，只需按下设定的热键，即可立刻触发随机抽签，结果以悬浮窗口的形式显示在屏幕上，不打断当前操作。

<img src="pictures/v6/设置.png" width="300" alt="全局热键设置" />

- 默认热键：`Tab`（可在设置中自定义）
- 支持 `Tab`、`F1`~`F12` 等多种组合
- 抽签结果 2 秒后自动淡出，不遮挡教学内容
- 使用 Windows `RegisterHotKey` API 实现，系统级响应，稳定可靠

#### 🕹️ 遥控抽签：翻页笔方案

> **将翻页笔上的闲置按键设为抽签热键，即可实现随时遥控抽签。**

大多数翻页笔都有一到两个可自定义的闲置按键（通常是「▢键」或「自定义键」）。只需通过翻页笔驱动软件将该按键映射为本程序设定的热键，即可：

1. 手持翻页笔在教室任意位置走动
2. 按下翻页笔上的自定义键
3. 屏幕上立即弹出被抽到的同学姓名

设置方式：在设置中找到"异步抽取快捷键"，点击录键后按下翻页笔上的闲置按键即可。

**无需触碰电脑，站在讲台任意位置均可操作。** 非常适合课堂互动提问场景。

### ⏱ 课堂计时

<img src="pictures/v6/countdown.png" width="300" alt="课堂计时" />

- 倒计时 / 正计时两种模式
- 音效提醒（计时结束）
- 快速模式：关闭所有动画，响应更迅速

### ✏️ 屏幕批注 *(开发中)*

- **批注模式**：在当前屏幕内容上直接绘画，不影响其他程序
- **白板模式**：呼出全屏白板，适合板书讲解
- 支持多种颜色，橡皮擦，一键清空

> ⚠️ 该功能目前仍在开发阶段，尚不稳定，默认为关闭状态。

### ⚙️ 界面设置

| 设置项 | 说明 |
|--------|------|
| 日/夜间模式 | 暖色调 / 冷色调 |
| 透明度 | 40% ~ 100% 可调 |
| 界面缩放 | 小 / 标准 / 大 / 超大 四档 |
| 动画速度 | 0 ~ 600ms 可调 |
| 静默启动 | 跳过启动动画 |
| 全局热键 | 自定义抽签触发键 |
| 开机自启 | 安装时可选 |

---

## 📁 项目结构

```
classtimer/
├── main.py                    # 应用入口
├── requirements.txt           # 依赖清单
├── rollcall.spec              # PyInstaller 打包配置
├── build.bat                  # 一键构建脚本
│
├── ui/                        # UI 层
│   ├── main_window.py         # 主窗口
│   ├── floating_ball.py       # 悬浮小球
│   ├── global_hotkey.py       # 全局热键
│   ├── splash_screen.py       # 启动屏
│   ├── annotation_toolbar.py  # 批注工具栏
│   ├── annotation_canvas.py   # 批注画布 & 白板
│   ├── async_pick_window.py   # 异步抽签窗口
│   ├── time_island.py         # 时间岛组件
│   └── pages/                 # 功能页面
│       ├── timer_page.py      # 计时器
│       ├── random_pick_page.py # 随机点名
│       ├── settings_page.py   # 设置
│       ├── tools_page.py      # 工具
│       └── automation_page.py # 自动化
│
├── utils/                     # 工具层
│   ├── config.py              # 配置管理
│   ├── styles.py              # 主题样式
│   ├── logger.py              # 日志系统
│   └── roster_importer.py     # 名单导入
│
├── pictures/                  # 图标资源
├── sounds/                    # 音频资源
└── installer_src/             # 安装器源码
```

---

## 📖 开发指南

### 依赖环境

```
PyQt5 >= 5.15.0
pygame >= 2.0.0
openpyxl >= 3.1.0
python-docx >= 1.1.0
```

### 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| UI 框架 | PyQt5 | 界面渲染与事件处理 |
| 系统集成 | ctypes | Windows API（热键、窗口管理） |
| 配置管理 | JSON | 用户设置持久化 |
| 音频 | pygame.mixer | 音效播放 |
| 打包 | PyInstaller | 生成独立 .exe |

### 新增功能流程

1. 在 `ui/pages/` 创建新页面类（继承 `QWidget`）
2. 在 `main_window.py` 注册到 `QStackedWidget`
3. 在导航栏添加对应按钮
4. 通过信号槽连接事件
5. 配置项存入 `config.py` 的 `DEFAULTS`
6. 主题样式在 `apply_night()` 中处理

> **注意**：在设置页新增控件时，留意小挡位（`WIN_W < 500`）下右侧栏会移至下方，控件固定宽度建议 ≤ 120px。

---

## ❓ 常见问题

### Tab 热键和其他软件冲突怎么办？

在设置页找到「抽签快捷键」，点击按钮后按下你想要的新热键（支持 F1-F12、字母、方向键、组合键等），自动保存生效。推荐使用 F9 或 CapsLock 等不常用按键。

### 名单文件格式要求是什么？

P5 版本只可读取 .txt 文件。.txt 文件每行写一个姓名，必须以 UTF-8 编码保存（可用记事本另存为时选择 UTF-8）。V6.0 兼容 .txt、.docx、.xlsx/.xls 等多种文件，表格任意列写姓名，从第一行开始。

### V6 和 P5 有什么区别，该下载哪个？

V6.0 基于 PyQt5 全面重构，有流畅动画、时间岛等新功能，属于测试版。P5.0 是经长期验证的稳定版，功能完整、运行可靠，推荐初次使用或对稳定性要求高的场景。

### 如何同时管理多个班级名单？

每次点击「导入名单」选择不同文件，软件会将其作为独立名单添加到下拉列表中，文件名即为名单名称。点击顶部下拉框可随时切换班级，各名单的抽签记录互相独立。

### 抽签弹窗的显示时间太短 / 太长怎么调？

进入设置页，找到「弹窗显示时长」滑块，向左拖动缩短显示时间，向右拖动延长。设置即时生效，下次抽签时生效。

### V6.0 界面显示太小 / 太大怎么调整？

进入设置页，找到「界面缩放」选项，调整到合适比例后重启软件后生效。推荐在 4K 高分屏上设置为 150% 或 200%。

---

## 🤝 贡献

欢迎提交 [Issue](../../issues) 反馈问题，或 [Pull Request](../../pulls) 贡献代码。

提交 Issue 时请附上：
- 操作系统版本
- 程序版本号
- 复现步骤
- 错误截图（如有）

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

<div align="center">

**如果这个项目对你有帮助，欢迎点一个 ⭐ Star！**

制作 & 维护：**ShuangSue** · 测试班级：高二十班 · © 2024–2026

</div>
