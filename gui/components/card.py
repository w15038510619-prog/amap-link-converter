# -*- coding: utf-8 -*-
"""
Fluent Design 卡片控件
包含头部标题、说明文字、操作插槽与内容区域
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class CardWidget(QFrame):
    """WinUI 3 风格的内容卡片组件"""

    def __init__(
        self,
        title: str = "",
        description: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("class", "fluent-card")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 18, 20, 18)
        self.main_layout.setSpacing(14)

        # 头部布局 (标题 + 右侧操作区)
        if title or description:
            self.header_layout = QHBoxLayout()
            self.header_layout.setSpacing(10)

            title_col = QVBoxLayout()
            title_col.setSpacing(3)

            if title:
                self.title_lbl = QLabel(title)
                self.title_lbl.setProperty("class", "card-title")
                title_col.addWidget(self.title_lbl)

            if description:
                self.desc_lbl = QLabel(description)
                self.desc_lbl.setProperty("class", "card-desc")
                self.desc_lbl.setWordWrap(True)
                title_col.addWidget(self.desc_lbl)

            self.header_layout.addLayout(title_col, 1)

            # 右侧操作插槽
            self.action_layout = QHBoxLayout()
            self.action_layout.setSpacing(8)
            self.header_layout.addLayout(self.action_layout, 0)

            self.main_layout.addLayout(self.header_layout)

        # 实际内容挂载区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget)

    def add_action_widget(self, widget: QWidget):
        """向卡片右上角添加操作控件"""
        if hasattr(self, "action_layout"):
            self.action_layout.addWidget(widget)

    def set_content_layout(self, layout):
        """设置内部容器布局"""
        # 清除现有布局
        QWidget().setLayout(self.content_widget.layout())
        self.content_widget.setLayout(layout)
