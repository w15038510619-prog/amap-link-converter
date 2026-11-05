# -*- coding: utf-8 -*-
"""
历史记录页面 (HistoryPage)
极简高颜值 Windows 11 Fluent 风格:
展示过往批量转换记录，支持快速定位导出成果与清空历史
"""

import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QFrame,
)

from gui.icons import get_icon
from core.history_manager import HistoryManager


class HistoryPage(QWidget):
    """历史任务记录与检索管理页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_history()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 顶部标题与操作栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_lbl = QLabel("转换历史记录")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel("记录近期转换任务的输出成果与详细统计，便于快速追溯与定位成果")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")

        title_layout.addWidget(title_lbl)
        title_layout.addWidget(sub_lbl)
        top_bar.addLayout(title_layout, 1)

        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setIcon(get_icon("refresh", "#374151", 14))
        self.btn_refresh.setProperty("class", "btn-secondary")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.load_history)
        top_bar.addWidget(self.btn_refresh)

        self.btn_clear = QPushButton("清空历史")
        self.btn_clear.setIcon(get_icon("trash", "#94A3B8", 14))
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_history)
        top_bar.addWidget(self.btn_clear)

        main_layout.addLayout(top_bar)

        # 历史记录列表卡片
        history_card = QFrame()
        history_card.setProperty("class", "fluent-card")
        card_layout = QVBoxLayout(history_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "执行时间", "文件数", "识别点位", "成功导出", "待处理", "执行状态", "操作"
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)

        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 75)
        self.table.setColumnWidth(2, 85)
        self.table.setColumnWidth(3, 85)
        self.table.setColumnWidth(4, 85)
        self.table.setColumnWidth(5, 100)

        card_layout.addWidget(self.table)
        main_layout.addWidget(history_card, 1)

    def load_history(self):
        items = HistoryManager.load()
        self.table.setRowCount(len(items))

        for row_idx, item in enumerate(items):
            # 时间
            t_item = QTableWidgetItem(item.get("start_time", "-"))
            t_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, t_item)

            # 文件数
            f_item = QTableWidgetItem(str(item.get("total_files", 0)))
            f_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, f_item)

            # 识别点位
            r_item = QTableWidgetItem(str(item.get("total_records", 0)))
            r_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 2, r_item)

            # 成功导入
            s_item = QTableWidgetItem(str(item.get("total_success", 0)))
            s_item.setTextAlignment(Qt.AlignCenter)
            s_item.setForeground(Qt.darkGreen)
            self.table.setItem(row_idx, 3, s_item)

            # 待处理
            pend_cnt = item.get("total_pending", 0)
            p_item = QTableWidgetItem(str(pend_cnt))
            p_item.setTextAlignment(Qt.AlignCenter)
            if pend_cnt > 0:
                p_item.setForeground(Qt.darkYellow)
            self.table.setItem(row_idx, 4, p_item)

            # 状态
            st = item.get("status", "SUCCESS")
            if st == "SUCCESS":
                st_text = "全部成功"
                color = Qt.darkGreen
            elif st == "PARTIAL":
                st_text = "部分待处理"
                color = Qt.darkYellow
            elif st == "FAILED":
                st_text = "转换失败"
                color = Qt.darkRed
            else:
                st_text = "已取消"
                color = Qt.gray

            st_item = QTableWidgetItem(st_text)
            st_item.setTextAlignment(Qt.AlignCenter)
            st_item.setForeground(color)
            self.table.setItem(row_idx, 5, st_item)

            # 操作按钮 (打开输出目录)
            out_dir = item.get("output_dir", "")
            btn_open = QPushButton("打开导出目录")
            btn_open.setIcon(get_icon("folder-open", "#374151", 13))
            btn_open.setProperty("class", "btn-secondary")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setStyleSheet("padding: 3px 10px; font-size: 12px;")
            btn_open.clicked.connect(lambda _, d=out_dir: self._open_dir(d))
            self.table.setCellWidget(row_idx, 6, btn_open)

    def _open_dir(self, directory: str):
        if directory and os.path.isdir(directory):
            QDesktopServices.openUrl(QUrl.fromLocalFile(directory))
        else:
            QMessageBox.warning(self, "提示", f"该目录已不存在: {directory}")

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定清空所有过往任务历史记录吗？", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            HistoryManager.clear()
            self.load_history()
