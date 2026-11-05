# -*- coding: utf-8 -*-
"""
数据预览表格组件
支持只读安全预览、关键字搜索、状态筛选 (全部/成功/待处理) 以及完整字段悬浮提示
"""

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from map_link_converter import Record


class PreviewTableWidget(QWidget):
    """只读且支持检索的数据预览表"""

    COLUMNS = [
        ("序号", 50),
        ("点位名称", 140),
        ("原始位置/链接", 240),
        ("解析方式", 120),
        ("经度 (GCJ-02)", 110),
        ("纬度 (GCJ-02)", 110),
        ("状态", 80),
        ("备注 / 异常原因", 180),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_records: List[Record] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 顶部工具栏: 搜索与状态筛选
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 快速搜索点位名称、链接或异常原因...")
        self.search_input.textChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.search_input, 1)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部状态", "仅成功记录", "仅待处理项"])
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.status_combo, 0)

        self.count_lbl = QLabel("共 0 条记录")
        self.count_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
        filter_bar.addWidget(self.count_lbl, 0)

        layout.addLayout(filter_bar)

        # 核心表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([col[0] for col in self.COLUMNS])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setStretchLastSection(True)

        for idx, (_, width) in enumerate(self.COLUMNS):
            self.table.setColumnWidth(idx, width)

        # 让名称和链接列自适应伸展
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)

        layout.addWidget(self.table)

    def set_records(self, records: List[Record]):
        """加载点位数据列表"""
        self._all_records = list(records)
        self._apply_filter()

    def clear_records(self):
        self._all_records = []
        self.table.setRowCount(0)
        self.count_lbl.setText("共 0 条记录")

    def _apply_filter(self):
        query = self.search_input.text().strip().lower()
        filter_type = self.status_combo.currentIndex()  # 0:全部, 1:成功, 2:待处理

        filtered: List[Record] = []
        for r in self._all_records:
            # 状态匹配
            if filter_type == 1 and r.status != "SUCCESS":
                continue
            if filter_type == 2 and r.status != "PENDING":
                continue

            # 关键词匹配
            if query:
                match_name = query in r.name.lower()
                match_loc = query in (r.raw_location or "").lower()
                match_err = query in (r.error_reason or "").lower()
                match_method = query in (r.method or "").lower()
                if not (match_name or match_loc or match_err or match_method):
                    continue

            filtered.append(r)

        self._populate_table(filtered)

    def _populate_table(self, records: List[Record]):
        self.table.setRowCount(len(records))
        self.count_lbl.setText(f"显示 {len(records)} / {len(self._all_records)} 条记录")

        for row_idx, r in enumerate(records):
            # 0: 序号
            item_idx = QTableWidgetItem(str(row_idx + 1))
            item_idx.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, item_idx)

            # 1: 点位名称 (设置 Tooltip 显示长全称)
            item_name = QTableWidgetItem(r.name)
            item_name.setToolTip(f"原始行号: {r.row_idx}\n点位全称: {r.name}")
            self.table.setItem(row_idx, 1, item_name)

            # 2: 原始位置/链接 (设置 Tooltip 显示完整网址)
            item_loc = QTableWidgetItem(r.raw_location or "")
            item_loc.setToolTip(r.raw_location or "(无位置内容)")
            self.table.setItem(row_idx, 2, item_loc)

            # 3: 解析方式
            item_method = QTableWidgetItem(r.method or "-")
            item_method.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 3, item_method)

            # 4: 经度
            lon_str = f"{r.lon:.6f}" if r.lon is not None else "-"
            item_lon = QTableWidgetItem(lon_str)
            item_lon.setTextAlignment(Qt.AlignCenter)
            if r.lon is not None:
                item_lon.setToolTip(f"完整经度: {r.lon}")
            self.table.setItem(row_idx, 4, item_lon)

            # 5: 纬度
            lat_str = f"{r.lat:.6f}" if r.lat is not None else "-"
            item_lat = QTableWidgetItem(lat_str)
            item_lat.setTextAlignment(Qt.AlignCenter)
            if r.lat is not None:
                item_lat.setToolTip(f"完整纬度: {r.lat}")
            self.table.setItem(row_idx, 5, item_lat)

            # 6: 状态 Badge
            badge_text = "成功" if r.status == "SUCCESS" else "待处理"
            item_status = QTableWidgetItem(badge_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            if r.status == "SUCCESS":
                item_status.setForeground(Qt.darkGreen)
            else:
                item_status.setForeground(Qt.darkRed)
            self.table.setItem(row_idx, 6, item_status)

            # 7: 备注 / 异常原因
            item_err = QTableWidgetItem(r.error_reason or r.intermediate_info or "-")
            item_err.setToolTip(r.error_reason or r.intermediate_info or "")
            if r.error_reason:
                item_err.setForeground(Qt.red)
            self.table.setItem(row_idx, 7, item_err)
