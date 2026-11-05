# -*- coding: utf-8 -*-
"""
转换任务工作区 (ConvertPage)
极简、高效、现代 Windows 11 Fluent 布局:
1. 醒目主操作栏: 「添加文件」「开始转换」首屏直达
2. 单行紧凑输出目录与状态标识，内置模板零打扰就绪
3. 紧凑型文件队列与拖拽导入条
4. 单行状态与实时统计条，摒弃臃肿卡片
5. 宽敞居中的核心数据预览区，支持非阻塞异步加载与精准状态区分
"""

import os
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
    QMessageBox,
    QAbstractItemView,
    QFrame,
)

from gui.icons import get_icon
from gui.components.drop_area import FileDropWidget
from gui.components.data_table import PreviewTableWidget
from core.template_manager import ConfigManager, TemplateManager
from core.worker import ConversionWorker, PreviewWorker
from map_link_converter import Record


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小为易读形式"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


class ConvertPage(QWidget):
    """主转换任务工作区"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_list: List[str] = []
        self.file_records_cache: Dict[str, List[Record]] = {}
        self.file_converted_cache: Dict[str, bool] = {}  # 记录是否已完成转换导出
        self.worker: Optional[ConversionWorker] = None
        self.preview_worker: Optional[PreviewWorker] = None
        self.last_summary: Optional[dict] = None
        self.output_dir: str = ""

        self._init_ui()
        self._load_default_output_dir()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # ================= 1. 顶部醒目主操作栏 =================
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        # 主操作 1: 添加文件
        self.btn_add_files = QPushButton("添加文件")
        self.btn_add_files.setIcon(get_icon("file-plus", "#1F2937", 16))
        self.btn_add_files.setProperty("class", "btn-secondary")
        self.btn_add_files.setCursor(Qt.PointingHandCursor)
        self.btn_add_files.setMinimumHeight(34)
        self.btn_add_files.clicked.connect(self._browse_add_files)
        action_bar.addWidget(self.btn_add_files)

        # 主操作 2: 开始批量转换 (Fluent Primary Accent)
        self.btn_start = QPushButton("开始转换")
        self.btn_start.setIcon(get_icon("play", "#FFFFFF", 16))
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setMinimumHeight(34)
        self.btn_start.clicked.connect(self.start_conversion)
        action_bar.addWidget(self.btn_start)

        action_bar.addSpacing(6)

        # 单行输出目录设置
        out_lbl = QLabel("导出至:")
        out_lbl.setStyleSheet("color: #64748B; font-weight: 500; font-size: 12px;")
        action_bar.addWidget(out_lbl)

        self.out_dir_lbl = QLabel("./导出结果")
        self.out_dir_lbl.setProperty("class", "path-box")
        self.out_dir_lbl.setMaximumWidth(280)
        action_bar.addWidget(self.out_dir_lbl)

        self.btn_choose_out = QPushButton("更改")
        self.btn_choose_out.setProperty("class", "btn-secondary")
        self.btn_choose_out.setCursor(Qt.PointingHandCursor)
        self.btn_choose_out.setToolTip("选择导出结果保存目录")
        self.btn_choose_out.clicked.connect(self._choose_output_dir)
        action_bar.addWidget(self.btn_choose_out)

        action_bar.addStretch()

        # 转换完成后的快捷操作
        self.btn_open_out_dir = QPushButton("打开导出目录")
        self.btn_open_out_dir.setIcon(get_icon("folder-open", "#374151", 15))
        self.btn_open_out_dir.setProperty("class", "btn-secondary")
        self.btn_open_out_dir.setCursor(Qt.PointingHandCursor)
        self.btn_open_out_dir.setVisible(False)
        self.btn_open_out_dir.clicked.connect(self.open_output_dir)
        action_bar.addWidget(self.btn_open_out_dir)

        self.btn_open_pending = QPushButton("查看待处理明细")
        self.btn_open_pending.setIcon(get_icon("list", "#B45309", 15))
        self.btn_open_pending.setProperty("class", "btn-secondary")
        self.btn_open_pending.setCursor(Qt.PointingHandCursor)
        self.btn_open_pending.setVisible(False)
        self.btn_open_pending.clicked.connect(self.open_pending_file)
        action_bar.addWidget(self.btn_open_pending)

        # 模板状态小型药丸徽章
        self.template_badge = QLabel("内置模板就绪")
        self.template_badge.setProperty("class", "badge-success")
        self.template_badge.setToolTip("已内置官方 GCJ-02 模板规范，正常使用无需手动导入")
        action_bar.addWidget(self.template_badge)

        main_layout.addLayout(action_bar)

        # ================= 2. 紧凑型文件队列与拖拽导入栏 =================
        file_strip_frame = QFrame()
        file_strip_frame.setProperty("class", "fluent-card")
        file_strip_layout = QHBoxLayout(file_strip_frame)
        file_strip_layout.setContentsMargins(10, 8, 10, 8)
        file_strip_layout.setSpacing(12)

        # 左侧: 紧凑拖拽导入条
        self.drop_widget = FileDropWidget()
        self.drop_widget.setFixedWidth(230)
        self.drop_widget.files_selected.connect(self.add_files)
        file_strip_layout.addWidget(self.drop_widget)

        # 右侧: 紧凑文件列表 (高度适中，完整呈现长文件名)
        file_table_container = QVBoxLayout()
        file_table_container.setSpacing(4)

        table_header_bar = QHBoxLayout()
        self.file_queue_title = QLabel("待处理文件 (0)")
        self.file_queue_title.setStyleSheet("font-size: 12px; font-weight: 600;")
        table_header_bar.addWidget(self.file_queue_title)

        table_header_bar.addStretch()

        self.btn_clear_files = QPushButton("清空")
        self.btn_clear_files.setIcon(get_icon("trash", "#94A3B8", 13))
        self.btn_clear_files.setProperty("class", "btn-ghost")
        self.btn_clear_files.setCursor(Qt.PointingHandCursor)
        self.btn_clear_files.setToolTip("清空待处理文件列表")
        self.btn_clear_files.clicked.connect(self.clear_files)
        table_header_bar.addWidget(self.btn_clear_files)

        file_table_container.addLayout(table_header_bar)

        self.file_table = QTableWidget()
        self.file_table.setFixedHeight(82)
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["文件名", "大小", "状态", "移除"])
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setShowGrid(False)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)

        f_header = self.file_table.horizontalHeader()
        f_header.setHighlightSections(False)
        f_header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.setColumnWidth(1, 75)
        self.file_table.setColumnWidth(2, 85)
        self.file_table.setColumnWidth(3, 45)
        self.file_table.cellClicked.connect(self._on_file_selected)

        file_table_container.addWidget(self.file_table)
        file_strip_layout.addLayout(file_table_container, 1)

        main_layout.addWidget(file_strip_frame)

        # ================= 3. 单行状态与实时统计条 =================
        status_bar = QHBoxLayout()
        status_bar.setSpacing(10)

        self.stats_summary_lbl = QLabel("就绪: 支持拖拽或添加 Excel 表格 (.xlsx / .xls)")
        self.stats_summary_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        status_bar.addWidget(self.stats_summary_lbl, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        status_bar.addWidget(self.progress_bar)

        main_layout.addLayout(status_bar)

        # ================= 4. 宽敞居中的核心数据预览区 =================
        preview_frame = QFrame()
        preview_frame.setProperty("class", "fluent-card")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(8)

        # 预览区标题与当前文件名
        preview_header = QHBoxLayout()
        preview_title = QLabel("数据预览与核验")
        preview_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        preview_header.addWidget(preview_title)

        self.preview_current_file_lbl = QLabel("未选择文件")
        self.preview_current_file_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        preview_header.addWidget(self.preview_current_file_lbl)
        preview_header.addStretch()

        preview_layout.addLayout(preview_header)

        # 数据预览表
        self.preview_table = PreviewTableWidget()
        preview_layout.addWidget(self.preview_table)

        main_layout.addWidget(preview_frame, 1)

    def _load_default_output_dir(self):
        cfg = ConfigManager.load()
        saved_dir = cfg.get("default_output_dir")
        if saved_dir and os.path.isdir(saved_dir):
            self.output_dir = saved_dir
        else:
            self.output_dir = os.path.abspath("./导出结果")
        self.out_dir_lbl.setText(os.path.basename(self.output_dir) or self.output_dir)
        self.out_dir_lbl.setToolTip(self.output_dir)

    def _choose_output_dir(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "选择导出结果保存目录", self.output_dir
        )
        if chosen:
            self.output_dir = os.path.abspath(chosen)
            self.out_dir_lbl.setText(os.path.basename(self.output_dir) or self.output_dir)
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
        """添加文件到列表，自动过滤重复文件"""
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
        self.file_converted_cache = {}
        self.file_table.setRowCount(0)
        self.preview_table.clear_records()
        self.file_queue_title.setText("待处理文件 (0)")
        self.preview_current_file_lbl.setText("未选择文件")
        self.progress_bar.setVisible(False)
        self.btn_open_out_dir.setVisible(False)
        self.btn_open_pending.setVisible(False)
        self.stats_summary_lbl.setText("就绪: 支持拖拽或添加 Excel 表格 (.xlsx / .xls)")

    def _refresh_file_table(self):
        self.file_table.setRowCount(len(self.file_list))
        self.file_queue_title.setText(f"待处理文件 ({len(self.file_list)})")

        for r_idx, fpath in enumerate(self.file_list):
            bname = os.path.basename(fpath)
            try:
                fsize = format_file_size(os.path.getsize(fpath))
            except Exception:
                fsize = "未知"

            # 0: 文件名
            item_name = QTableWidgetItem(bname)
            item_name.setToolTip(fpath)
            self.file_table.setItem(r_idx, 0, item_name)

            # 1: 大小
            item_size = QTableWidgetItem(fsize)
            item_size.setTextAlignment(Qt.AlignCenter)
            self.file_table.setItem(r_idx, 1, item_size)

            # 2: 状态
            is_conv = self.file_converted_cache.get(fpath, False)
            status_text = "已转换" if is_conv else "待转换"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            item_status.setForeground(Qt.darkGreen if is_conv else Qt.darkGray)
            self.file_table.setItem(r_idx, 2, item_status)

            # 3: 删除操作
            btn_del = QPushButton()
            btn_del.setIcon(get_icon("x", "#94A3B8", 12))
            btn_del.setProperty("class", "btn-ghost")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setToolTip("从列表中移除")
            btn_del.clicked.connect(lambda _, p=fpath: self._remove_single_file(p))
            self.file_table.setCellWidget(r_idx, 3, btn_del)

    def _remove_single_file(self, target_path: str):
        if target_path in self.file_list:
            self.file_list.remove(target_path)
            self.file_records_cache.pop(target_path, None)
            self.file_converted_cache.pop(target_path, None)
            self._refresh_file_table()
            if self.file_list:
                self.file_table.selectRow(0)
                self._load_file_preview(self.file_list[0])
            else:
                self.preview_table.clear_records()
                self.preview_current_file_lbl.setText("未选择文件")
                self.stats_summary_lbl.setText("就绪: 支持拖拽或添加 Excel 表格 (.xlsx / .xls)")

    def _on_file_selected(self, row: int, col: int):
        if 0 <= row < len(self.file_list):
            fpath = self.file_list[row]
            self._load_file_preview(fpath)

    def _load_file_preview(self, fpath: str):
        """异步读取文件数据并在预览表中呈现，杜绝大文件阻塞主界面"""
        bname = os.path.basename(fpath)
        self.preview_current_file_lbl.setText(f"当前: {bname}")

        if fpath in self.file_records_cache:
            records = self.file_records_cache[fpath]
            is_converted = self.file_converted_cache.get(fpath, False)
            self._display_preview_data(fpath, records, is_converted)
            return

        # 启动非阻塞异步预览解析
        self.stats_summary_lbl.setText(f"正在加载数据预览: {bname}...")
        self.preview_worker = PreviewWorker(fpath, allow_network=False)
        self.preview_worker.preview_done.connect(self._on_preview_loaded)
        self.preview_worker.preview_failed.connect(self._on_preview_error)
        self.preview_worker.start()

    @Slot(str, list)
    def _on_preview_loaded(self, fpath: str, records: list):
        self.file_records_cache[fpath] = records
        self._display_preview_data(fpath, records, is_converted=False)

    @Slot(str, str)
    def _on_preview_error(self, fpath: str, err_msg: str):
        self.preview_table.clear_records()
        self.stats_summary_lbl.setText(f"读取文件 [{os.path.basename(fpath)}] 失败: {err_msg}")

    def _display_preview_data(self, fpath: str, records: List[Record], is_converted: bool):
        self.preview_table.set_records(records, is_converted=is_converted)
        total = len(records)
        succ = sum(1 for r in records if r.status == "SUCCESS")
        pend = sum(1 for r in records if r.status == "PENDING")

        bname = os.path.basename(fpath)
        if is_converted:
            self.stats_summary_lbl.setText(
                f"已完成转换: {bname} | 共 {total} 条点位 (已导出 {succ} 条 / 待处理 {pend} 条)"
            )
        else:
            self.stats_summary_lbl.setText(
                f"文件就绪: {bname} | 识别到 {total} 条点位 (可解析 {succ} 条 / 待核验 {pend} 条)"
            )

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
        self.btn_open_out_dir.setVisible(False)
        self.btn_open_pending.setVisible(False)
        self.stats_summary_lbl.setText("正在执行高精坐标转换与规范写入...")

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
        self.stats_summary_lbl.setText(f"[{current}/{total}] 正在转换: {filename}...")
        for r in range(self.file_table.rowCount()):
            if self.file_table.item(r, 0) and self.file_table.item(r, 0).text() == filename:
                st = self.file_table.item(r, 2)
                st.setText("转换中...")
                st.setForeground(Qt.blue)
                break

    @Slot(dict)
    def _on_file_finished(self, summary: dict):
        fname = summary["filename"]
        fpath = summary.get("source_file") or summary.get("file", "")
        self.progress_bar.setValue(self.progress_bar.value() + 1)
        if fpath:
            self.file_converted_cache[fpath] = True

        # 如果携带了转换后的真实记录，更新缓存并刷新展示
        if "records" in summary and summary["records"]:
            if fpath:
                self.file_records_cache[fpath] = summary["records"]
            self._display_preview_data(fpath, summary["records"], is_converted=True)

        for r in range(self.file_table.rowCount()):
            if self.file_table.item(r, 0) and self.file_table.item(r, 0).text() == fname:
                st = self.file_table.item(r, 2)
                if summary["status"] == "SUCCESS":
                    st.setText("已导出")
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
        self.btn_open_out_dir.setVisible(True)

        # 准确控制"查看待处理明细"状态
        total_pending = overall.get("total_pending", 0)
        self.btn_open_pending.setVisible(True)
        self.btn_open_pending.setEnabled(total_pending > 0)
        if total_pending == 0:
            self.btn_open_pending.setToolTip("所有点位均成功转换，无待处理异常记录")
        else:
            self.btn_open_pending.setToolTip(f"共 {total_pending} 条待处理点位，点击打开 Excel 明细核查")

        tip_msg = (
            f"转换全部完成！识别总点位: {overall['total_records']} 条 | "
            f"成功导出: {overall['total_success']} 条 | 待处理: {total_pending} 条"
        )
        self.stats_summary_lbl.setText(tip_msg)

        # 检查是否配置自动打开目录
        cfg = ConfigManager.load()
        if cfg.get("auto_open_output", True) and overall["total_success"] > 0:
            self.open_output_dir()

    @Slot(str)
    def _on_error(self, err_msg: str):
        self.btn_start.setEnabled(True)
        self.btn_add_files.setEnabled(True)
        self.btn_clear_files.setEnabled(True)
        self.progress_bar.setVisible(False)
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
            QMessageBox.information(self, "提示", "所有点位均成功转换，未生成待处理明细文件！")
