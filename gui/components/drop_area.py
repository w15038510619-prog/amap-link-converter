# -*- coding: utf-8 -*-
"""
文件拖拽上传区域控件
支持直接拖拽单个/多个 .xlsx, .xls 文件，或点击唤起原生文件对话框
"""

import os
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QCursor
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QFileDialog,
)


class FileDropWidget(QFrame):
    """Fluent 风格的拖拽导入卡片"""

    files_selected = Signal(list)  # 选中的文件路径列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(140)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        # 图标展示
        self.icon_lbl = QLabel("📁")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 38px; color: #0066CC;")
        layout.addWidget(self.icon_lbl)

        # 主提示文案
        self.primary_lbl = QLabel("拖拽 Excel 文件到此处，或点击浏览添加")
        self.primary_lbl.setAlignment(Qt.AlignCenter)
        self.primary_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E293B;")
        layout.addWidget(self.primary_lbl)

        # 辅助格式说明
        self.sub_lbl = QLabel("支持 .xlsx 和旧版 .xls 格式，允许多文件批量导入")
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        self.sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(self.sub_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "选择待转换的 Excel 文件 (支持多选)",
                "",
                "Excel 文件 (*.xlsx *.xls);;所有文件 (*.*)",
            )
            if files:
                self.files_selected.emit(files)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # 过滤是否包含支持的文件类型
            urls = event.mimeData().urls()
            valid = any(
                url.toLocalFile().lower().endswith((".xlsx", ".xls"))
                for url in urls
            )
            if valid:
                event.acceptProposedAction()
                self.setStyleSheet("#dropArea { border-color: #0066CC; background-color: #F0F9FF; }")
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        valid_files: List[str] = []
        for url in urls:
            local_path = url.toLocalFile()
            if os.path.isfile(local_path) and local_path.lower().endswith((".xlsx", ".xls")):
                valid_files.append(os.path.abspath(local_path))

        if valid_files:
            event.acceptProposedAction()
            self.files_selected.emit(valid_files)
        else:
            event.ignore()
