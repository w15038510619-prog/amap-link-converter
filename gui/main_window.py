# -*- coding: utf-8 -*-
"""
主应用窗口模块 (MainWindow)
极简现代 Windows 11 Fluent 顶栏架构:
1. 彻底移除笨重左侧栏，采用 50px 极简顶栏导航 (转换为 100% 宽幅工作区)
2. 顶栏集成: 品牌标识、分段药丸导航 (转换工作区 / 历史记录 / 设置与模板)、一键明暗主题切换
3. 核心区域完全让位于数据预览与转换流程，在 1200×760 与 960×620 下完美适配
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QButtonGroup,
)

from gui.icons import get_icon
from gui.styles import get_stylesheet
from gui.pages.convert_page import ConvertPage
from gui.pages.history_page import HistoryPage
from gui.pages.settings_page import SettingsPage
from core.template_manager import ConfigManager


class MainWindow(QMainWindow):
    """主程序窗口类"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("地图位置转换器 V2.0 - 高德/百度链接转地图导入规范")
        self.resize(1200, 760)
        self.setMinimumSize(960, 620)

        self._current_theme = "light"
        self._init_ui()
        self._apply_initial_theme()

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ================= 1. 顶部紧凑 Fluent 导航栏 (高 50px) =================
        header_bar = QWidget()
        header_bar.setObjectName("topHeader")
        header_bar.setFixedHeight(50)

        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(18, 0, 18, 0)
        header_layout.setSpacing(16)

        # 品牌标识区域
        brand_box = QHBoxLayout()
        brand_box.setSpacing(8)

        brand_icon_lbl = QLabel()
        brand_icon_lbl.setPixmap(get_icon("convert", "#0067C0", 20).pixmap(20, 20))
        brand_box.addWidget(brand_icon_lbl)

        self.app_title_lbl = QLabel("地图位置转换器")
        self.app_title_lbl.setObjectName("appLogoTitle")
        brand_box.addWidget(self.app_title_lbl)

        self.app_sub_tag = QLabel("V2.0")
        self.app_sub_tag.setObjectName("appSubTag")
        brand_box.addWidget(self.app_sub_tag)

        header_layout.addLayout(brand_box)
        header_layout.addSpacing(20)

        # 头部导航分段按钮组
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_box = QHBoxLayout()
        nav_box.setSpacing(6)

        self.btn_nav_convert = QPushButton(" 转换工作区")
        self.btn_nav_convert.setIcon(get_icon("convert", "#0067C0", 15))
        self.btn_nav_convert.setProperty("class", "header-nav-btn")
        self.btn_nav_convert.setCheckable(True)
        self.btn_nav_convert.setChecked(True)
        self.btn_nav_convert.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(self.btn_nav_convert, 0)
        nav_box.addWidget(self.btn_nav_convert)

        self.btn_nav_history = QPushButton(" 历史记录")
        self.btn_nav_history.setIcon(get_icon("history", "#64748B", 15))
        self.btn_nav_history.setProperty("class", "header-nav-btn")
        self.btn_nav_history.setCheckable(True)
        self.btn_nav_history.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(self.btn_nav_history, 1)
        nav_box.addWidget(self.btn_nav_history)

        self.btn_nav_settings = QPushButton(" 设置与模板")
        self.btn_nav_settings.setIcon(get_icon("settings", "#64748B", 15))
        self.btn_nav_settings.setProperty("class", "header-nav-btn")
        self.btn_nav_settings.setCheckable(True)
        self.btn_nav_settings.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(self.btn_nav_settings, 2)
        nav_box.addWidget(self.btn_nav_settings)

        header_layout.addLayout(nav_box)
        header_layout.addStretch()

        # 右侧: 一键主题切换按钮
        self.btn_theme_toggle = QPushButton("深色模式")
        self.btn_theme_toggle.setIcon(get_icon("theme", "#64748B", 15))
        self.btn_theme_toggle.setProperty("class", "btn-secondary")
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.setToolTip("快速切换明亮 / 深色界面风格")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.btn_theme_toggle)

        root_layout.addWidget(header_bar)

        # ================= 2. 主页面内容堆叠栈 (QStackedWidget) =================
        self.stack = QStackedWidget()

        self.convert_page = ConvertPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.convert_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.settings_page)

        root_layout.addWidget(self.stack, 1)

        # 信号绑定
        self.btn_nav_convert.clicked.connect(lambda: self._switch_page(0))
        self.btn_nav_history.clicked.connect(lambda: self._switch_page(1))
        self.btn_nav_settings.clicked.connect(lambda: self._switch_page(2))
        self.settings_page.theme_changed_signal.connect(self._on_settings_theme_changed)

    def _switch_page(self, page_index: int):
        self.stack.setCurrentIndex(page_index)
        if page_index == 1:
            self.history_page.load_history()
        elif page_index == 2:
            self.settings_page.load_settings()

    def _apply_initial_theme(self):
        cfg = ConfigManager.load()
        theme = cfg.get("theme", "light")
        self._set_theme(theme)

    def _toggle_theme(self):
        new_theme = "dark" if self._current_theme == "light" else "light"
        cfg = ConfigManager.load()
        cfg["theme"] = new_theme
        ConfigManager.save(cfg)
        self._set_theme(new_theme)
        self.settings_page.load_settings()

    def _on_settings_theme_changed(self, theme: str):
        self._set_theme(theme)

    def _set_theme(self, theme: str):
        self._current_theme = theme
        self.setStyleSheet(get_stylesheet(theme))
        if theme == "dark":
            self.btn_theme_toggle.setText("浅色模式")
            self.btn_theme_toggle.setIcon(get_icon("theme", "#F4F4F5", 15))
        else:
            self.btn_theme_toggle.setText("深色模式")
            self.btn_theme_toggle.setIcon(get_icon("theme", "#4B5563", 15))

    def closeEvent(self, event):
        """窗口关闭安全释放后台线程，杜绝 QThread 销毁异常"""
        self.convert_page.cleanup_on_close()
        super().closeEvent(event)
