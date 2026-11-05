# 地图位置转换器 V2.0 (Windows 11 Fluent 商业桌面版)

一款专为 Windows 10/11 设计的现代化、专业级地图位置链接批量转换桌面软件。将 Excel 表格中的点位名称和高德/百度地图位置链接，批量提取为符合高德地图导入规范的 **GCJ-02 火星坐标系经纬度**，并按标准模板无缝导出。

---

## 一、V2.0 桌面端重构亮点

1. **Windows 11 Fluent Design 原生视觉**：
   - 采用 PySide6（Qt for Python）构建，严格遵循微软 Fluent Design 设计语言规范。
   - 现代侧边导航栏、内容卡片、自适应圆角（8~10px）、细致边框、低饱和度背景与统一的线性图标系统。
   - 支持**浅色主题（默认）**与**深色主题（Dark Mode）**一键平滑切换。
   - 完美适配 125%、150% Windows 高 DPI 缩放，排版清晰不模糊。

2. **官方模板全内置（零手动选择负担）**：
   - 将官方标准导入模板（`导入模板 (9).xlsx`）作为静态资源直接嵌入应用程序（`resources/templates/default.xlsx`）。
   - 用户打开软件后直接拖入源表即可开始转换，**彻底告别每次手动寻找和选择模板的繁琐操作**。
   - 内置「模板管理」模块：支持查看模板结构、一键导出一份空白模板、载入自定义模板（带严格合规校验）及一键恢复内置默认模板。

3. **直观流畅的文件与数据交互流程**：
   - **拖拽文件导入区**：支持批量拖入多个 `.xlsx` 或 `.xls`，自动去重，展示文件大小与状态。
   - **点位数据即时预览表**：选中文件即可秒级预览其解析点位明细，包含序号、点位名称、链接、解析方式、经纬度、状态与异常原因。
   - **交互搜索与筛选**：支持关键词实时检索，支持按“全部 / 仅成功 / 仅待处理”分类过滤。
   - **非阻塞后台多线程**：耗时转换在独立 QThread 中运行，界面实时反馈进度条与 KPI 统计指标卡片，绝无假死。
   - **快捷后续操作**：转换完成后提供「打开导出目录」、「查看待处理明细」及任务历史追溯。

4. **100% 继承并巩固底层核心算法与守恒性**：
   - 完整保留高德 `__r=`、`r=`、`daddr=`、`to[lnglat]`、乱序 `schema`、动态分享页公开接口与百度 `en=`（BD09MC 逆投影多项式）解析能力。
   - 严格保证记录数守恒：`识别业务记录数 = 成功导入数 + 待处理数`。
   - 导出时彻底清除模板旧示例数据，保留 `导入说明` 与 `颜色说明` 工作表及 4 张说明图片。

---

## 二、界面视觉效果 (Screenshots)

| 页面状态 | 效果说明 | 截图文件预览 |
| :--- | :--- | :--- |
| **初始就绪主界面** | 现代卡片布局、拖拽区、指标卡片与数据表 | `screenshots/01_main_window_empty.png` |
| **文件导入与预览** | 拖入真实 Excel 后的即时数据预览与字段呈现 | `screenshots/02_files_imported_and_preview.png` |
| **转换完成状态** | 进度 100%、KPI 指标统计与快速打开目录按钮 | `screenshots/03_conversion_completed.png` |
| **历史记录页** | 任务执行流水台账，支持一键打开结果目录 | `screenshots/04_history_page.png` |
| **设置与模板管理** | 内置官方模板状态、空白模板导出与偏好设置 | `screenshots/05_settings_page.png` |
| **深色模式 (Dark)** | Windows 11 深色夜间模式 | `screenshots/06_dark_theme.png` |

---

## 三、快速开始

### 模式 1：运行独立免安装单文件 EXE（最推荐）
在 Windows 10/11 电脑上，无需安装 Python 环境，直接运行：
```text
dist\地图位置转换器.exe
```
- 双击直接唤起现代化窗口界面，不弹额外黑窗口。
- 内置模板已随 EXE 打包，直接拖入 Excel 文件点击「开始批量转换」即可。

### 模式 2：Python 源码运行 GUI
安装依赖：
```bash
python -m pip install -r requirements.txt
```
启动桌面端软件：
```bash
python main.py
```

### 模式 3：静默命令行批处理（CLI）
适合服务器、CI/CD 或脚本自动化调度，传入 `-i` 参数即自动以静默方式运行，不弹界面：
```bash
python main.py -i "新建 XLSX 工作表.xlsx" -o "./导出结果"
```
或使用 EXE 命令行调用：
```bash
dist\地图位置转换器.exe -i "新建 XLSX 工作表.xlsx" -o "./导出结果"
```

#### 命令行参数说明：
- `-i, --input`：待处理的 Excel 源文件路径（支持空格分隔多个文件）。
- `-t, --template`：（可选）指定自定义模板路径；若留空则自动提取内置官方模板。
- `-o, --output-dir`：（可选）输出目录，默认为 `./导出结果`。
- `--offline`：（可选）离线模式，禁止访问网络请求高德分享接口。

---

## 四、自动化测试套件

项目配套了 30 项全覆盖自动化测试（涵盖底层算法、接口 Mock、Excel 表头与图片保留、GUI 页面逻辑与截图视觉验收）：

```bash
python -m pytest -v
```

全部测试用例覆盖：
1. `test_coord_transform.py`：BD09MC 回归样例 (13145007, 2792306) -> BD-09 -> GCJ-02 精度验证、坐标合法性与异常边界测试。
2. `test_coord_extractor.py`：高德各类参数（`__r`、`r=`、`daddr=`、`to[lnglat]`、乱序 schema）、百度 `en=`、冲突检测、非合法链接拦截。
3. `test_amap_api.py`：高德分享接口模拟响应测试（成功、超时、失效、缺字段）及真实请求验证。
4. `test_excel_io.py`：`.xlsx` 与 `.xls` 读写、无表头数据行、真实超链接与 `=HYPERLINK()` 静态公式解析、坏链接隔离。
5. `test_template_manager.py`：内置模板定位完整性核验、空白模板导出、自定义模板合规校验与恢复默认设置。
6. `test_gui_visual.py`：GUI 完整生命周期交互与 6 张界面视觉截图自动化验收。
7. `test_end_to_end.py`：使用附带真实业务表端到端全流程转换并严格核验 9 列表头与导出格式。

---

## 五、EXE 重新打包说明

如对代码进行修改后需重新生成单文件免安装桌面版 EXE，请执行：

```bash
python -m PyInstaller --noconfirm --onefile --windowed --name "地图位置转换器" --add-data "resources;resources" main.py
```
打包成功后，产物位于 `dist/地图位置转换器.exe`。

---

## 六、项目架构目录

```text
高德链接转换/
│
├── main.py                     # 程序入口 (自动判定 GUI 还是 CLI 批处理)
├── map_link_converter.py        # 转换引擎底层驱动
├── coord_extractor.py          # 各类地图 URL 解析器
├── coord_transform.py          # 坐标逆投影与转换算法 (BD09MC / BD-09 / GCJ-02)
├── amap_api.py                 # 隔离的高德分享公开接口模块
├── requirements.txt            # 项目依赖清单
├── README.md                   # 详细使用手册与技术文档
│
├── core/                       # 核心业务与持久层
│   ├── template_manager.py     # 内置模板加载、校验、导出与自定义配置
│   ├── history_manager.py      # 转换任务历史记录持久化
│   └── worker.py               # QThread 异步工作线程
│
├── gui/                        # PySide6 现代桌面端呈现层
│   ├── styles.py               # Fluent Design 浅色/深色主题 QSS 系统
│   ├── main_window.py          # 现代化主窗口与侧边导航
│   ├── components/             # 复用组件库 (Card, DropArea, DataTable, MetricCard)
│   └── pages/                  # 主业务页面 (ConvertPage, HistoryPage, SettingsPage)
│
├── resources/                  # 内置静态资源
│   └── templates/
│       └── default.xlsx        # 内置官方标准导入规范模板
│
├── screenshots/                # 视觉验收截图
│   ├── 01_main_window_empty.png
│   ├── 02_files_imported_and_preview.png
│   ├── 03_conversion_completed.png
│   ├── 04_history_page.png
│   ├── 05_settings_page.png
│   └── 06_dark_theme.png
│
├── tests/                      # 30 项全覆盖测试套件
└── dist/
    └── 地图位置转换器.exe        # 独立免安装 Windows 桌面端可执行程序
```
