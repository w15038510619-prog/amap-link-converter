# -*- coding: utf-8 -*-
"""
紧凑轻量型文件拖拽与选择组件
使用矢量 SVG 图标，紧凑高度 (~75px)，大幅节省垂直工作区面积
"""

import os
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFileDialog,
)

from gui.icons import get_pixmap


class FileDropWidget(QFrame):
    """紧凑型拖拽/点击选择文件区域"""

    files_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(72)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        # 矢量 SVG 图标
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(get_pixmap("file-plus", "#0067C0", 22))
        layout.addWidget(self.icon_lbl)

        # 文字提示 (单行水平排版)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignVCenter)

        self.title_lbl = QLabel("点击或拖拽添加文件")
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
        text_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("支持 .xlsx 与 .xls 表格")
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        text_layout.addWidget(self.sub_lbl)

        layout.addLayout(text_layout)

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
            urls = event.mimeData().urls()
            valid = any(
                url.toLocalFile().lower().endswith((".xlsx", ".xls"))
                for url in urls
            )
            if valid:
                event.acceptProposedAction()
                self.setStyleSheet("#dropArea { border-color: #0067C0; background-color: #EFF6FF; }")
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
