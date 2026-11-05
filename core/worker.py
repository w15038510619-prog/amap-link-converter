# -*- coding: utf-8 -*-
"""
后台工作线程模块 (基于 PySide6 QThread)
包含:
1. ConversionWorker: 异步执行批量 Excel 文件转换并生成导入模板与待处理明细
2. PreviewWorker: 异步读取并解析 Excel 数据用于即时只读预览，避免阻塞 GUI 主线程
"""

import datetime
import os
from typing import List, Optional

from PySide6.QtCore import QThread, Signal

from map_link_converter import TableReader, TemplateWriter, Record
from core.template_manager import TemplateManager
from core.history_manager import HistoryManager


class PreviewWorker(QThread):
    """异步数据预览读取线程，避免大文件阻塞界面"""

    preview_done = Signal(str, list)  # (file_path, records)
    preview_failed = Signal(str, str)  # (file_path, error_msg)

    def __init__(self, file_path: str, allow_network: bool = False, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.allow_network = allow_network

    def run(self):
        try:
            records = TableReader.read_file(self.file_path, allow_network=self.allow_network)
            self.preview_done.emit(self.file_path, records)
        except Exception as e:
            self.preview_failed.emit(self.file_path, str(e))


class ConversionWorker(QThread):
    """批量转换工作线程"""

    # 信号定义
    started_signal = Signal(int, int)  # (总文件数, 0)
    file_started_signal = Signal(int, int, str)  # (当前索引, 总文件数, 文件名)
    record_progress_signal = Signal(int, int)  # (当前记录, 总记录)
    log_signal = Signal(str, str)  # (level, message)
    file_finished_signal = Signal(dict)  # 单文件摘要
    batch_finished_signal = Signal(dict)  # 全局汇总
    error_signal = Signal(str)  # 错误信号

    def __init__(
        self,
        source_files: List[str],
        output_dir: str,
        template_path: Optional[str] = None,
        allow_network: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.source_files = list(source_files)
        self.output_dir = output_dir
        self.template_path = template_path or TemplateManager.get_active_template_path()
        self.allow_network = allow_network
        self._is_cancelled = False

    def cancel(self):
        """请求取消转换"""
        self._is_cancelled = True
        self.log_signal.emit("WARNING", "正在终止转换任务...")

    def run(self):
        total_files = len(self.source_files)
        self.started_signal.emit(total_files, 0)
        self.log_signal.emit(
            "INFO",
            f"转换任务启动: 共 {total_files} 个文件, 使用模板: {os.path.basename(self.template_path)}"
        )

        overall = {
            "total_files": total_files,
            "total_records": 0,
            "total_success": 0,
            "total_pending": 0,
            "file_results": [],
            "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": "",
            "output_dir": self.output_dir,
            "cancelled": False,
        }

        try:
            os.makedirs(self.output_dir, exist_ok=True)
            # 预检验模板
            TemplateWriter.verify_template(self.template_path)
        except Exception as e:
            self.error_signal.emit(f"初始化模板或输出目录失败: {e}")
            self.log_signal.emit("ERROR", f"初始化失败: {e}")
            return

        for idx, src_file in enumerate(self.source_files, 1):
            if self._is_cancelled:
                overall["cancelled"] = True
                self.log_signal.emit("WARNING", "转换已被用户取消")
                break

            base_name = os.path.basename(src_file)
            self.file_started_signal.emit(idx, total_files, base_name)
            self.log_signal.emit("INFO", f"[{idx}/{total_files}] 开始解析: {base_name}")

            try:
                records = TableReader.read_file(src_file, allow_network=self.allow_network)
                total_rec = len(records)
                self.record_progress_signal.emit(total_rec, total_rec)

                import_path, pending_path, succ_cnt, pend_cnt = TemplateWriter.write_results(
                    self.template_path, self.output_dir, src_file, records
                )

                file_summary = {
                    "file": src_file,
                    "source_file": src_file,
                    "filename": base_name,
                    "total": total_rec,
                    "success": succ_cnt,
                    "pending": pend_cnt,
                    "import_file": import_path,
                    "pending_file": pending_path,
                    "records": records,  # 供 GUI 刷新预览
                    "status": "SUCCESS" if (pend_cnt == 0 and succ_cnt > 0) else (
                        "PARTIAL" if succ_cnt > 0 else "FAILED"
                    ),
                }

                overall["total_records"] += total_rec
                overall["total_success"] += succ_cnt
                overall["total_pending"] += pend_cnt

                # 存入历史记录时剔除不可 JSON 序列化的 Record 实例对象
                file_summary_clean = {k: v for k, v in file_summary.items() if k != "records"}
                overall["file_results"].append(file_summary_clean)

                self.file_finished_signal.emit(file_summary)
                self.log_signal.emit(
                    "INFO",
                    f"[{idx}/{total_files}] 处理完成: 识别={total_rec}, 成功={succ_cnt}, 待处理={pend_cnt}"
                )

            except Exception as e:
                err_msg = f"处理文件 [{base_name}] 失败: {e}"
                self.log_signal.emit("ERROR", err_msg)
                file_summary = {
                    "file": src_file,
                    "source_file": src_file,
                    "filename": base_name,
                    "total": 0,
                    "success": 0,
                    "pending": 0,
                    "import_file": None,
                    "pending_file": None,
                    "records": [],
                    "status": f"FAILED: {e}",
                }
                file_summary_clean = {k: v for k, v in file_summary.items() if k != "records"}
                overall["file_results"].append(file_summary_clean)
                self.file_finished_signal.emit(file_summary)

        overall["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 准确判定历史记录状态
        if overall["cancelled"]:
            hist_status = "CANCELLED"
        elif overall["total_records"] == 0:
            hist_status = "FAILED"
        elif any(f.get("status", "").startswith("FAILED") for f in overall["file_results"]):
            hist_status = "PARTIAL" if overall["total_success"] > 0 else "FAILED"
        elif overall["total_pending"] > 0:
            hist_status = "PARTIAL"
        elif overall["total_success"] == overall["total_records"] and overall["total_records"] > 0:
            hist_status = "SUCCESS"
        else:
            hist_status = "PARTIAL"

        try:
            hist_item = {
                "id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                "start_time": overall["start_time"],
                "total_files": overall["total_files"],
                "total_records": overall["total_records"],
                "total_success": overall["total_success"],
                "total_pending": overall["total_pending"],
                "output_dir": overall["output_dir"],
                "file_results": overall["file_results"],
                "status": hist_status,
            }
            HistoryManager.add(hist_item)
        except Exception as e:
            self.log_signal.emit("WARNING", f"保存历史记录失败: {e}")

        self.batch_finished_signal.emit(overall)
        self.log_signal.emit(
            "INFO",
            f"所有任务已结束: 成功导入 {overall['total_success']} 条, 待处理 {overall['total_pending']} 条"
        )
