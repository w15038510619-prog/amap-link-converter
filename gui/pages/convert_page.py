# -*- coding: utf-8 -*-
"""
转换任务主页面 (ConvertPage)
整合文件拖拽导入、文件队列管理、数据即时预览、实时进度、KPI 指标与结果导出操作
"""

import os
import subprocess
import sys
from typing import List, Dict, Optional

from PySide6.QtCore import Qt, QUrl, Slot
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
    QFileDialog,
    QProgressBar,
    QSplitter,
    QMessageBox,
    QTextEdit,
    QAbstractItemView,
)

from gui.components.card import CardWidget
from gui.components.drop_area import FileDropWidget
from gui.components.metric_card import MetricCard
from gui.components.data_table import PreviewTableWidget
from core.template_manager import ConfigManager, TemplateManager
from core.worker import ConversionWorker
from map_link_converter import TableReader, Record


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小为易读形式"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


class ConvertPage(QWidget):
    """主转换任务页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_list: List[str] = []
        self.file_records_cache: Dict[str, List[Record]] = {}
        self.worker: Optional[ConversionWorker] = None
        self.last_summary: Optional[dict] = None

        self._init_ui()
        self._load_default_output_dir()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. 顶部操作栏: 标题、模板状态标识与输出路径
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        page_title_layout = QVBoxLayout()
        page_title_layout.setSpacing(2)
        title_lbl = QLabel("批量位置转换")
        title_lbl.setProperty("class", "page-title")
        sub_title_lbl = QLabel("拖拽源表直接转换，已内置官方 GCJ-02 地图导入规范模板")
        sub_title_lbl.setProperty("class", "page-subtitle")
        page_title_layout.addWidget(title_lbl)
        page_title_layout.addWidget(sub_title_lbl)
        top_bar.addLayout(page_title_layout, 1)

        # 模板状态标签
        self.template_badge = QLabel("  内置模板就绪  ")
        self.template_badge.setStyleSheet(
            "background-color: #DCFCE7; color: #15803D; font-size: 12px; font-weight: 600; "
            "padding: 6px 12px; border-radius: 6px;"
        )
        top_bar.addWidget(self.template_badge)

        main_layout.addLayout(top_bar)

        # 2. 中部垂直分割器: 上部文件管理与转换控制，下部数据预览表
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(8)

        # ================= 上部控制容器 =================
        top_container = QWidget()
        top_container_layout = QHBoxLayout(top_container)
        top_container_layout.setContentsMargins(0, 0, 0, 0)
        top_container_layout.setSpacing(16)

        # 左侧: 文件导入与队列卡片
        file_card = CardWidget("待转换文件列表", "支持多文件批量处理，点击文件行可预览点位")
        file_card_layout = QVBoxLayout()
        file_card_layout.setSpacing(10)

        # 拖拽区域
        self.drop_widget = FileDropWidget()
        self.drop_widget.files_selected.connect(self.add_files)
        file_card_layout.addWidget(self.drop_widget)

        # 文件列表表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["文件名", "大小", "状态", "操作"])
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setShowGrid(False)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.horizontalHeader().setStretchLastSection(False)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.setColumnWidth(1, 80)
        self.file_table.setColumnWidth(2, 90)
        self.file_table.setColumnWidth(3, 60)
        self.file_table.cellClicked.connect(self._on_file_selected)

        file_card_layout.addWidget(self.file_table)

        # 文件卡片底部操作按钮
        file_btn_bar = QHBoxLayout()
        self.btn_add_files = QPushButton("＋ 添加文件")
        self.btn_add_files.setProperty("class", "btn-secondary")
        self.btn_add_files.clicked.connect(self._browse_add_files)
        file_btn_bar.addWidget(self.btn_add_files)

        self.btn_clear_files = QPushButton("清空列表")
        self.btn_clear_files.setProperty("class", "btn-secondary")
        self.btn_clear_files.clicked.connect(self.clear_files)
        file_btn_bar.addWidget(self.btn_clear_files)

        file_btn_bar.addStretch()
        file_card_layout.addLayout(file_btn_bar)

        file_card.set_content_layout(file_card_layout)
        top_container_layout.addWidget(file_card, 6)

        # 右侧: 执行控制与状态卡片
        action_card = CardWidget("转换配置与操作", "设置结果输出位置并启动全自动解析流程")
        action_card_layout = QVBoxLayout()
        action_card_layout.setSpacing(14)

        # 输出目录选择
        out_box_layout = QVBoxLayout()
        out_box_layout.setSpacing(6)
        out_lbl = QLabel("导出结果保存目录:")
        out_lbl.setProperty("class", "field-label")
        out_box_layout.addWidget(out_lbl)

        out_select_bar = QHBoxLayout()
        self.out_dir_lbl = QLabel("./导出结果")
        self.out_dir_lbl.setProperty("class", "path-display")
        out_select_bar.addWidget(self.out_dir_lbl, 1)

        self.btn_choose_out = QPushButton("更改目录")
        self.btn_choose_out.setProperty("class", "btn-secondary")
        self.btn_choose_out.clicked.connect(self._choose_output_dir)
        out_select_bar.addWidget(self.btn_choose_out)

        out_box_layout.addLayout(out_select_bar)
        action_card_layout.addLayout(out_box_layout)

        # KPI 指标统计格
        metric_layout = QHBoxLayout()
        metric_layout.setSpacing(8)
        self.metric_files = MetricCard("待处理文件", "0", "📁", "#0066CC")
        self.metric_total = MetricCard("总识别点位", "0", "📍", "#0F172A")
        self.metric_success = MetricCard("成功导入", "0", "✅", "#15803D")
        self.metric_pending = MetricCard("待处理项", "0", "⚠️", "#B45309")
        metric_layout.addWidget(self.metric_files)
        metric_layout.addWidget(self.metric_total)
        metric_layout.addWidget(self.metric_success)
        metric_layout.addWidget(self.metric_pending)
        action_card_layout.addLayout(metric_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        action_card_layout.addWidget(self.progress_bar)

        self.status_tip_lbl = QLabel("准备就绪，请添加待转换文件后点击开始")
        self.status_tip_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        action_card_layout.addWidget(self.status_tip_lbl)

        # 主操作按钮
        self.btn_start = QPushButton("▶ 开始批量转换")
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setMinimumHeight(42)
        self.btn_start.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.btn_start.clicked.connect(self.start_conversion)
        action_card_layout.addWidget(self.btn_start)

        # 完成后的操作按钮组 (默认隐藏)
        self.finish_actions_widget = QWidget()
        finish_layout = QHBoxLayout(self.finish_actions_widget)
        finish_layout.setContentsMargins(0, 0, 0, 0)
        finish_layout.setSpacing(8)

        self.btn_open_out_dir = QPushButton("📂 打开导出目录")
        self.btn_open_out_dir.setProperty("class", "btn-secondary")
        self.btn_open_out_dir.clicked.connect(self.open_output_dir)
        finish_layout.addWidget(self.btn_open_out_dir)

        self.btn_open_pending = QPushButton("📋 查看待处理明细")
        self.btn_open_pending.setProperty("class", "btn-secondary")
        self.btn_open_pending.clicked.connect(self.open_pending_file)
        finish_layout.addWidget(self.btn_open_pending)

        action_card_layout.addWidget(self.finish_actions_widget)
        self.finish_actions_widget.setVisible(False)

        action_card_layout.addStretch()
        action_card.set_content_layout(action_card_layout)
        top_container_layout.addWidget(action_card, 5)

        splitter.addWidget(top_container)

        # ================= 下部数据预览表 =================
        preview_card = CardWidget("点位数据预览", "选中左侧列表文件即可提前核验解析结果，支持关键词搜索与状态筛选")
        preview_card_layout = QVBoxLayout()
        preview_card_layout.setSpacing(8)

        self.preview_table = PreviewTableWidget()
        preview_card_layout.addWidget(self.preview_table)

        preview_card.set_content_layout(preview_card_layout)
        splitter.addWidget(preview_card)

        # 分割器初始比例
        splitter.setSizes([340, 380])
        main_layout.addWidget(splitter, 1)

    def _load_default_output_dir(self):
        cfg = ConfigManager.load()
        saved_dir = cfg.get("default_output_dir")
        if saved_dir and os.path.isdir(saved_dir):
            self.output_dir = saved_dir
        else:
            self.output_dir = os.path.abspath("./导出结果")
        self.out_dir_lbl.setText(self.output_dir)
        self.out_dir_lbl.setToolTip(self.output_dir)

    def _choose_output_dir(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "选择导出结果保存目录", self.output_dir
        )
        if chosen:
            self.output_dir = os.path.abspath(chosen)
            self.out_dir_lbl.setText(self.output_dir)
            self.out_dir_lbl.setToolTip(self.output_dir)
            cfg = ConfigManager.load()
            cfg["default_output_dir"] = self.output_dir
            ConfigManager.save(cfg)

    def _browse_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "添加待转换的 Excel 文件", "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*.*)"
        )
        if files:
            self.add_files(files)

    @Slot(list)
    def add_files(self, paths: List[str]):
        """添加文件到列表，自动过滤重复项"""
        added_count = 0
        for p in paths:
            abs_p = os.path.abspath(p)
            if abs_p not in self.file_list and os.path.isfile(abs_p):
                self.file_list.append(abs_p)
                added_count += 1

        if added_count > 0:
            self._refresh_file_table()
            # 默认选中第一个未预览的文件
            if self.file_table.rowCount() > 0:
                self.file_table.selectRow(0)
                self._load_file_preview(self.file_list[0])

    def clear_files(self):
        self.file_list = []
        self.file_records_cache = {}
        self.file_table.setRowCount(0)
        self.preview_table.clear_records()
        self.metric_files.set_value("0")
        self.metric_total.set_value("0")
        self.metric_success.set_value("0")
        self.metric_pending.set_value("0")
        self.progress_bar.setVisible(False)
        self.finish_actions_widget.setVisible(False)
        self.status_tip_lbl.setText("准备就绪，请添加待转换文件后点击开始")

    def _refresh_file_table(self):
        self.file_table.setRowCount(len(self.file_list))
        self.metric_files.set_value(str(len(self.file_list)))

        for r_idx, fpath in enumerate(self.file_list):
            bname = os.path.basename(fpath)
            try:
                fsize = format_file_size(os.path.getsize(fpath))
            except Exception:
                fsize = "未知"

            # 文件名
            item_name = QTableWidgetItem(bname)
            item_name.setToolTip(fpath)
            self.file_table.setItem(r_idx, 0, item_name)

            # 大小
            item_size = QTableWidgetItem(fsize)
            item_size.setTextAlignment(Qt.AlignCenter)
            self.file_table.setItem(r_idx, 1, item_size)

            # 状态
            item_status = QTableWidgetItem("待转换")
            item_status.setTextAlignment(Qt.AlignCenter)
            item_status.setForeground(Qt.darkGray)
            self.file_table.setItem(r_idx, 2, item_status)

            # 删除操作按钮
            btn_del = QPushButton("✕")
            btn_del.setStyleSheet("border:none; color:#DC2626; font-weight:bold; font-size:14px;")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda _, p=fpath: self._remove_single_file(p))
            self.file_table.setCellWidget(r_idx, 3, btn_del)

    def _remove_single_file(self, target_path: str):
        if target_path in self.file_list:
            self.file_list.remove(target_path)
            self.file_records_cache.pop(target_path, None)
            self._refresh_file_table()
            if self.file_list:
                self.file_table.selectRow(0)
                self._load_file_preview(self.file_list[0])
            else:
                self.preview_table.clear_records()

    def _on_file_selected(self, row: int, col: int):
        if 0 <= row < len(self.file_list):
            fpath = self.file_list[row]
            self._load_file_preview(fpath)

    def _load_file_preview(self, fpath: str):
        """读取文件并呈现在数据预览表中"""
        if fpath in self.file_records_cache:
            records = self.file_records_cache[fpath]
        else:
            try:
                # 离线读取解析预览，避免阻塞
                records = TableReader.read_file(fpath, allow_network=False)
                self.file_records_cache[fpath] = records
            except Exception as e:
                self.preview_table.clear_records()
                self.status_tip_lbl.setText(f"预览文件 [{os.path.basename(fpath)}] 失败: {e}")
                return

        self.preview_table.set_records(records)
        # 更新单表点位统计
        succ = sum(1 for r in records if r.status == "SUCCESS")
        pend = sum(1 for r in records if r.status == "PENDING")
        self.metric_total.set_value(str(len(records)))
        self.metric_success.set_value(str(succ))
        self.metric_pending.set_value(str(pend))

    def start_conversion(self):
        """启动后台多线程转换任务"""
        if not self.file_list:
            QMessageBox.information(self, "提示", "请先添加至少一个待转换的 Excel 文件！")
            return

        cfg = ConfigManager.load()
        allow_network = cfg.get("enable_share_api", True)

        self.btn_start.setEnabled(False)
        self.btn_add_files.setEnabled(False)
        self.btn_clear_files.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.finish_actions_widget.setVisible(False)
        self.status_tip_lbl.setText("正在执行高精坐标转换...")

        self.worker = ConversionWorker(
            source_files=self.file_list,
            output_dir=self.output_dir,
            allow_network=allow_network,
        )

        self.worker.started_signal.connect(self._on_batch_started)
        self.worker.file_started_signal.connect(self._on_file_started)
        self.worker.file_finished_signal.connect(self._on_file_finished)
        self.worker.batch_finished_signal.connect(self._on_batch_finished)
        self.worker.error_signal.connect(self._on_error)

        self.worker.start()

    @Slot(int, int)
    def _on_batch_started(self, total_files: int, _):
        self.progress_bar.setRange(0, total_files)
        self.progress_bar.setValue(0)

    @Slot(int, int, str)
    def _on_file_started(self, current: int, total: int, filename: str):
        self.status_tip_lbl.setText(f"[{current}/{total}] 正在转换: {filename}...")
        for r in range(self.file_table.rowCount()):
            if self.file_table.item(r, 0) and self.file_table.item(r, 0).text() == filename:
                st = self.file_table.item(r, 2)
                st.setText("转换中...")
                st.setForeground(Qt.blue)
                break

    @Slot(dict)
    def _on_file_finished(self, summary: dict):
        fname = summary["filename"]
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        for r in range(self.file_table.rowCount()):
            if self.file_table.item(r, 0) and self.file_table.item(r, 0).text() == fname:
                st = self.file_table.item(r, 2)
                if summary["status"] == "SUCCESS":
                    st.setText("已完成")
                    st.setForeground(Qt.darkGreen)
                elif summary["status"] == "PARTIAL":
                    st.setText("部分待处理")
                    st.setForeground(Qt.darkYellow)
                else:
                    st.setText("失败")
                    st.setForeground(Qt.darkRed)
                break

    @Slot(dict)
    def _on_batch_finished(self, overall: dict):
        self.last_summary = overall
        self.btn_start.setEnabled(True)
        self.btn_add_files.setEnabled(True)
        self.btn_clear_files.setEnabled(True)
        self.finish_actions_widget.setVisible(True)

        self.metric_total.set_value(str(overall["total_records"]))
        self.metric_success.set_value(str(overall["total_success"]))
        self.metric_pending.set_value(str(overall["total_pending"]))

        tip_msg = (
            f"转换全部完成！识别总数={overall['total_records']}, "
            f"成功={overall['total_success']}条, 待处理={overall['total_pending']}条"
        )
        self.status_tip_lbl.setText(tip_msg)

        # 检查是否自动打开目录
        cfg = ConfigManager.load()
        if cfg.get("auto_open_output", True) and overall["total_success"] > 0:
            self.open_output_dir()

    @Slot(str)
    def _on_error(self, err_msg: str):
        self.btn_start.setEnabled(True)
        self.btn_add_files.setEnabled(True)
        self.btn_clear_files.setEnabled(True)
        QMessageBox.critical(self, "转换异常", err_msg)

    def open_output_dir(self):
        """在 Windows 资源管理器中打开导出文件夹"""
        if os.path.exists(self.output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir))
        else:
            QMessageBox.warning(self, "提示", f"输出目录不存在: {self.output_dir}")

    def open_pending_file(self):
        """一键打开最后生成的待处理明细 Excel 表"""
        if not self.last_summary:
            QMessageBox.information(self, "提示", "暂无待处理明细。")
            return

        pending_files = [
            f["pending_file"]
            for f in self.last_summary.get("file_results", [])
            if f.get("pending_file") and os.path.isfile(f["pending_file"])
        ]

        if pending_files:
            target = pending_files[0]
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))
        else:
            QMessageBox.information(self, "提示", "所有点位均成功转换，未生成待处理明细文件！🎉")
