# -*- coding: utf-8 -*-
"""
KPI 统计指标卡片组件
用于在转换中及转换完成后直观呈现指标数据
"""

from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
)


class MetricCard(QFrame):
    """单项统计指标卡片"""

    def __init__(
        self,
        title: str,
        value: str = "0",
        icon: str = "📊",
        accent_color: str = "#0066CC",
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("class", "fluent-card")
        self.setMinimumWidth(130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # 头部: 图标 + 标题
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 16px; color: {accent_color};")
        top_layout.addWidget(icon_lbl)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #64748B;")
        top_layout.addWidget(self.title_lbl)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        # 数值大字
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {accent_color};")
        layout.addWidget(self.value_lbl)

    def set_value(self, val: Any):
        self.value_lbl.setText(str(val))
