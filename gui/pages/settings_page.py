# -*- coding: utf-8 -*-
"""
系统设置与模板管理页面 (SettingsPage)
极简高颜值 Windows 11 Fluent 风格:
1. 模板管理 (当前生效模板展示、内置/自定义状态、导出空白模板、选择自定义模板校验、恢复内置)
2. 导出偏好 (默认输出目录、转换后自动打开目录开关)
3. 网络与接口配置 (高德分享公开接口开关)
4. 界面主题切换 (浅色/深色) 与软件版本说明
"""

import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QComboBox,
    QScrollArea,
    QFrame,
)

from gui.icons import get_icon
from core.template_manager import (
    ConfigManager,
    TemplateManager,
    EXPECTED_HEADERS,
)


class SettingsPage(QWidget):
    """系统设置与模板管理主面板"""

    theme_changed_signal = Signal(str)  # 主题变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 页面标题
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_lbl = QLabel("应用设置与模板管理")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        sub_lbl = QLabel("管理内置导入模板、自定义规范及运行偏好")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_layout.addWidget(title_lbl)
        title_layout.addWidget(sub_lbl)
        main_layout.addLayout(title_layout)

        # 滚动区域以防较小分辨率内容截断
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)

        # 1. 核心模块: 模板管理卡片
        template_card = QFrame()
        template_card.setProperty("class", "fluent-card")
        tpl_layout = QVBoxLayout(template_card)
        tpl_layout.setContentsMargins(14, 12, 14, 12)
        tpl_layout.setSpacing(10)

        tpl_title = QLabel("地图导入模板管理")
        tpl_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        tpl_layout.addWidget(tpl_title)

        tpl_desc = QLabel("本软件已将官方标准导入模板内置于程序中，日常使用完全无需手动选择。")
        tpl_desc.setStyleSheet("font-size: 12px; color: #64748B;")
        tpl_layout.addWidget(tpl_desc)

        # 状态呈现
        status_box = QHBoxLayout()
        status_box.setSpacing(12)

        status_left = QVBoxLayout()
        status_left.setSpacing(3)
        self.current_tpl_label = QLabel("当前模板：内置官方模板 (default.xlsx)")
        self.current_tpl_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.tpl_status_label = QLabel("模板状态：已就绪（严格符合 标记位置 9 列表头规范）")
        self.tpl_status_label.setStyleSheet("font-size: 12px; color: #16A34A;")
        status_left.addWidget(self.current_tpl_label)
        status_left.addWidget(self.tpl_status_label)
        status_box.addLayout(status_left, 1)

        self.tpl_badge = QLabel(" 内置官方 ")
        self.tpl_badge.setProperty("class", "badge-success")
        status_box.addWidget(self.tpl_badge, 0)

        tpl_layout.addLayout(status_box)

        # 操作按钮条
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_export_blank = QPushButton("导出一份空白模板")
        self.btn_export_blank.setIcon(get_icon("download", "#374151", 14))
        self.btn_export_blank.setProperty("class", "btn-secondary")
        self.btn_export_blank.setCursor(Qt.PointingHandCursor)
        self.btn_export_blank.clicked.connect(self._export_blank_template)
        action_bar.addWidget(self.btn_export_blank)

        self.btn_choose_custom = QPushButton("选择自定义模板")
        self.btn_choose_custom.setIcon(get_icon("file-excel", "#374151", 14))
        self.btn_choose_custom.setProperty("class", "btn-secondary")
        self.btn_choose_custom.setCursor(Qt.PointingHandCursor)
        self.btn_choose_custom.clicked.connect(self._choose_custom_template)
        action_bar.addWidget(self.btn_choose_custom)

        self.btn_reset_builtin = QPushButton("恢复内置默认模板")
        self.btn_reset_builtin.setIcon(get_icon("refresh", "#374151", 14))
        self.btn_reset_builtin.setProperty("class", "btn-secondary")
        self.btn_reset_builtin.setCursor(Qt.PointingHandCursor)
        self.btn_reset_builtin.clicked.connect(self._reset_builtin_template)
        action_bar.addWidget(self.btn_reset_builtin)

        self.btn_view_spec = QPushButton("查看模板规范")
        self.btn_view_spec.setIcon(get_icon("list", "#374151", 14))
        self.btn_view_spec.setProperty("class", "btn-secondary")
        self.btn_view_spec.setCursor(Qt.PointingHandCursor)
        self.btn_view_spec.clicked.connect(self._show_spec_dialog)
        action_bar.addWidget(self.btn_view_spec)

        action_bar.addStretch()
        tpl_layout.addLayout(action_bar)

        scroll_layout.addWidget(template_card)

        # 2. 导出与常规偏好卡片
        export_card = QFrame()
        export_card.setProperty("class", "fluent-card")
        exp_layout = QVBoxLayout(export_card)
        exp_layout.setContentsMargins(14, 12, 14, 12)
        exp_layout.setSpacing(10)

        exp_title = QLabel("导出偏好设置")
        exp_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        exp_layout.addWidget(exp_title)

        # 自动打开输出目录
        self.chk_auto_open = QCheckBox("转换成功后自动在资源管理器中打开导出文件夹")
        self.chk_auto_open.setChecked(True)
        self.chk_auto_open.toggled.connect(self._on_auto_open_toggled)
        exp_layout.addWidget(self.chk_auto_open)

        # 默认输出路径设定
        dir_box = QHBoxLayout()
        dir_lbl = QLabel("默认导出目录:")
        dir_lbl.setStyleSheet("color: #64748B; font-weight: 500;")
        self.lbl_default_dir = QLabel("./导出结果")
        self.lbl_default_dir.setProperty("class", "path-box")

        btn_change_def_dir = QPushButton("更改")
        btn_change_def_dir.setProperty("class", "btn-secondary")
        btn_change_def_dir.setCursor(Qt.PointingHandCursor)
        btn_change_def_dir.clicked.connect(self._change_default_dir)

        dir_box.addWidget(dir_lbl)
        dir_box.addWidget(self.lbl_default_dir, 1)
        dir_box.addWidget(btn_change_def_dir)
        exp_layout.addLayout(dir_box)

        scroll_layout.addWidget(export_card)

        # 3. 坐标解析与网络设置卡片
        network_card = QFrame()
        network_card.setProperty("class", "fluent-card")
        net_layout = QVBoxLayout(network_card)
        net_layout.setContentsMargins(14, 12, 14, 12)
        net_layout.setSpacing(8)

        net_title = QLabel("解析引擎与网络设置")
        net_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        net_layout.addWidget(net_title)

        self.chk_share_api = QCheckBox("启用高德动态分享页同源解析接口 (GET m5.amap.com)")
        self.chk_share_api.setChecked(True)
        self.chk_share_api.setToolTip("对缺少明文坐标的分享链接调用高德公开接口恢复终点；断网时会自动跳过。")
        self.chk_share_api.toggled.connect(self._on_share_api_toggled)
        net_layout.addWidget(self.chk_share_api)

        coord_tip = QLabel(
            "提示：系统提取坐标将严格按 GCJ-02 火星坐标系写入模板；百度 BD09MC 墨卡托平面坐标将自动转换为 GCJ-02。"
        )
        coord_tip.setStyleSheet("font-size: 11px; color: #64748B;")
        coord_tip.setWordWrap(True)
        net_layout.addWidget(coord_tip)

        scroll_layout.addWidget(network_card)

        # 4. 外观与主题
        theme_card = QFrame()
        theme_card.setProperty("class", "fluent-card")
        thm_layout = QHBoxLayout(theme_card)
        thm_layout.setContentsMargins(14, 12, 14, 12)
        thm_layout.setSpacing(12)

        thm_lbl = QLabel("界面主题模式:")
        thm_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["浅色主题 (Light - 默认)", "深色主题 (Dark)"])
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        thm_layout.addWidget(thm_lbl)
        thm_layout.addWidget(self.combo_theme)
        thm_layout.addStretch()

        scroll_layout.addWidget(theme_card)

        # 5. 关于与版本说明
        about_card = QFrame()
        about_card.setProperty("class", "fluent-card")
        abt_layout = QVBoxLayout(about_card)
        abt_layout.setContentsMargins(14, 12, 14, 12)
        abt_layout.setSpacing(4)

        v_lbl = QLabel("地图位置转换器 V2.0 Fluent Edition (Windows 64-bit)")
        v_lbl.setStyleSheet("font-weight: 600;")
        t_lbl = QLabel("技术栈: Python + PySide6 (Qt) + openpyxl + xlrd + Requests | 内置 GCJ-02 模板规范")
        t_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
        abt_layout.addWidget(v_lbl)
        abt_layout.addWidget(t_lbl)
        scroll_layout.addWidget(about_card)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

    def load_settings(self):
        cfg = ConfigManager.load()
        # 模板状态
        is_builtin = TemplateManager.is_using_builtin()
        active_path = TemplateManager.get_active_template_path()

        if is_builtin:
            self.current_tpl_label.setText("当前模板：内置官方模板 (resources/templates/default.xlsx)")
            self.tpl_badge.setText(" 内置官方 ")
            self.tpl_badge.setProperty("class", "badge-success")
            self.btn_reset_builtin.setEnabled(False)
        else:
            self.current_tpl_label.setText(f"当前模板：自定义模板 ({os.path.basename(active_path)})")
            self.current_tpl_label.setToolTip(active_path)
            self.tpl_badge.setText(" 自定义模板 ")
            self.tpl_badge.setProperty("class", "badge-ready")
            self.btn_reset_builtin.setEnabled(True)

        # 重新应用样式以使 badge property 生效
        self.tpl_badge.style().unpolish(self.tpl_badge)
        self.tpl_badge.style().polish(self.tpl_badge)

        # 导出偏好
        self.chk_auto_open.setChecked(cfg.get("auto_open_output", True))
        def_dir = cfg.get("default_output_dir") or os.path.abspath("./导出结果")
        self.lbl_default_dir.setText(def_dir)

        # 网络开关
        self.chk_share_api.setChecked(cfg.get("enable_share_api", True))

        # 主题
        cur_theme = cfg.get("theme", "light")
        self.combo_theme.setCurrentIndex(1 if cur_theme == "dark" else 0)

    def _export_blank_template(self):
        target_path, _ = QFileDialog.getSaveFileName(
            self, "导出一份空白导入模板", "地图导入标准模板.xlsx", "Excel 文件 (*.xlsx)"
        )
        if target_path:
            ok, msg = TemplateManager.export_blank_template(target_path)
            if ok:
                QMessageBox.information(self, "导出成功", f"空白模板已导出至:\n{target_path}")
            else:
                QMessageBox.critical(self, "导出失败", msg)

    def _choose_custom_template(self):
        chosen_file, _ = QFileDialog.getOpenFileNames(
            self, "选择自定义地图导入模板", "", "Excel 模板文件 (*.xlsx)"
        )
        target = chosen_file[0] if chosen_file else ""
        if target:
            ok, msg = TemplateManager.set_custom_template(target)
            if ok:
                QMessageBox.information(self, "设置成功", "自定义模板已通过合规校验并成功应用！")
                self.load_settings()
            else:
                QMessageBox.warning(self, "模板校验失败", f"该文件不符合地图导入规范:\n{msg}")

    def _reset_builtin_template(self):
        TemplateManager.reset_to_builtin()
        QMessageBox.information(self, "已恢复", "已成功恢复为内置官方模板！")
        self.load_settings()

    def _show_spec_dialog(self):
        spec_text = (
            "【地图导入主数据表 9 列固定规范】\n\n"
            "工作表名称: 标记位置\n\n"
            + "\n".join(f"列 {chr(65+i)}:  {col}" for i, col in enumerate(EXPECTED_HEADERS))
            + "\n\n要求:\n"
            "1. 不得修改表头文字、星号及列顺序。\n"
            "2. 经纬度填入数值型 GCJ-02。\n"
            "3. 填写经纬度后地址必须留空，杜绝将网址填入地址列。\n"
            "4. 必须附带「导入说明」与「颜色说明」工作表及其图片。"
        )
        QMessageBox.information(self, "模板字段规范", spec_text)

    def _on_auto_open_toggled(self, checked: bool):
        cfg = ConfigManager.load()
        cfg["auto_open_output"] = checked
        ConfigManager.save(cfg)

    def _change_default_dir(self):
        cur = self.lbl_default_dir.text()
        chosen = QFileDialog.getExistingDirectory(self, "选择默认输出目录", cur)
        if chosen:
            chosen_abs = os.path.abspath(chosen)
            self.lbl_default_dir.setText(chosen_abs)
            cfg = ConfigManager.load()
            cfg["default_output_dir"] = chosen_abs
            ConfigManager.save(cfg)

    def _on_share_api_toggled(self, checked: bool):
        cfg = ConfigManager.load()
        cfg["enable_share_api"] = checked
        ConfigManager.save(cfg)

    def _on_theme_changed(self, idx: int):
        theme = "dark" if idx == 1 else "light"
        cfg = ConfigManager.load()
        cfg["theme"] = theme
        ConfigManager.save(cfg)
        self.theme_changed_signal.emit(theme)
