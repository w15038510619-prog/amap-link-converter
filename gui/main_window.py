# -*- coding: utf-8 -*-
"""
主应用窗口模块 (MainWindow)
基于 Windows 11 Fluent Design 架构:
- 左侧导航栏 (导航到: 转换任务、历史记录、设置与模板管理)
- 右侧 QStackedWidget 内容堆叠区
- 统一的高 DPI、主题自适应与响应式布局
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont
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

        self._init_ui()
        self._apply_initial_theme()

    def _init_ui(self):
        # 根容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. 左侧 Fluent 风格导航栏 (宽 220px)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(8)

        # 品牌头部
        brand_box = QHBoxLayout()
        brand_box.setSpacing(8)
        brand_icon = QLabel("🗺️")
        brand_icon.setStyleSheet("font-size: 26px;")

        brand_text_col = QVBoxLayout()
        brand_text_col.setSpacing(1)
        self.nav_title = QLabel("地图位置转换器")
        self.nav_title.setObjectName("navTitle")
        self.nav_sub = QLabel("V2.0 商业重构版")
        self.nav_sub.setObjectName("navSubtitle")
        brand_text_col.addWidget(self.nav_title)
        brand_text_col.addWidget(self.nav_sub)

        brand_box.addWidget(brand_icon)
        brand_box.addLayout(brand_text_col, 1)
        sidebar_layout.addLayout(brand_box)
        sidebar_layout.addSpacing(18)

        # 导航按钮组
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_convert = QPushButton("🧭  转换任务")
        self.btn_nav_convert.setProperty("class", "nav-btn")
        self.btn_nav_convert.setCheckable(True)
        self.btn_nav_convert.setChecked(True)
        self.btn_nav_convert.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(self.btn_nav_convert, 0)
        sidebar_layout.addWidget(self.btn_nav_convert)

        self.btn_nav_history = QPushButton("🕒  历史记录")
        self.btn_nav_history.setProperty("class", "nav-btn")
        self.btn_nav_history.setCheckable(True)
        self.btn_nav_history.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(self.btn_nav_history, 1)
        sidebar_layout.addWidget(self.btn_nav_history)

        sidebar_layout.addStretch()

        # 底部设置按钮
        self.btn_nav_settings = QPushButton("⚙️  系统与模板设置")
        self.btn_nav_settings.setProperty("class", "nav-btn")
        self.btn_nav_settings.setCheckable(True)
        self.btn_nav_settings.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(self.btn_nav_settings, 2)
        sidebar_layout.addWidget(self.btn_nav_settings)

        root_layout.addWidget(sidebar)

        # 2. 右侧页面堆叠栈 (QStackedWidget)
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
        self.settings_page.theme_changed_signal.connect(self._on_theme_changed)

    def _switch_page(self, page_index: int):
        self.stack.setCurrentIndex(page_index)
        if page_index == 1:
            self.history_page.load_history()
        elif page_index == 2:
            self.settings_page.load_settings()

    def _apply_initial_theme(self):
        cfg = ConfigManager.load()
        theme = cfg.get("theme", "light")
        self.setStyleSheet(get_stylesheet(theme))

    def _on_theme_changed(self, theme: str):
        self.setStyleSheet(get_stylesheet(theme))
