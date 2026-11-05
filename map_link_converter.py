# -*- coding: utf-8 -*-
"""
高德/百度地图位置链接批量转换工具 (主程序)
功能:
1. 批量读取 Excel (.xlsx / .xls) 中的点位名称及地图链接。
2. 自动识别多表头或无表头数据，提取单元格文本、真实超链接及 HYPERLINK 静态公式。
3. 准确提取目的地 GCJ-02 经纬度，兼容高德 __r, r, daddr, to[lnglat], schema, 动态分享页及百度 en= (BD09MC)。
4. 清除模板中旧的 18 条历史记录，保留说明表与图片，严格按导入模板输出。
5. 生成清晰的待处理明细表，保证“有效记录数 = 成功导入数 + 待处理数”。
6. 支持 GUI 文件对话框及 CLI 命令行参数两种使用模式。
"""

import argparse
import datetime
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

import openpyxl
import xlrd

from coord_extractor import extract_destination, CoordExtractionError
from coord_transform import is_valid_lnglat, is_xiamen_region

# 确保控制台支持 UTF-8 打印
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("map_converter")

TEMPLATE_SHEET_MAIN = "标记位置"
TEMPLATE_SHEET_DESC = "导入说明"
TEMPLATE_SHEET_COLOR = "颜色说明"
EXPECTED_HEADERS = [
    "名称",
    "*经度",
    "*纬度",
    "*地址",
    "颜色",
    "图标(外轮廓)",
    "图标(填充物)",
    "描述",
    "文件夹",
]

EXACT_NAME_HEADERS = {
    "名称", "台区", "台区名称", "点位名称", "配电站名称", "设备名称",
    "开闭所名称", "环网柜名称", "站名", "点位", "设备", "台区/位置", "台区/链接"
}
EXACT_LOCATION_HEADERS = {
    "位置", "链接", "高德地址", "导航链接", "定位链接", "地图链接",
    "地址", "url", "高德链接", "高德地图", "地图", "经纬度", "坐标"
}
IGNORE_SERIAL_KEYWORDS = {"序号", "id", "no", "编号", "项次"}


@dataclass
class Record:
    source_file: str
    sheet_name: str
    row_idx: int
    name: str
    raw_location: str
    hyperlink_target: Optional[str] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    status: str = "PENDING"  # SUCCESS or PENDING
    method: str = ""
    intermediate_info: str = ""
    error_reason: str = ""


class TableReader:
    """Excel 表格读取与结构自适应识别器"""

    @staticmethod
    def _is_url_like(val: Any) -> bool:
        if not val or not isinstance(val, str):
            return False
        s = val.strip().lower()
        return (
            "http://" in s
            or "https://" in s
            or "amap.com" in s
            or "baidu.com" in s
            or "__r=" in s
            or "daddr=" in s
            or "to[lnglat]" in s
            or "=hyperlink" in s
        )

    @classmethod
    def _extract_openpyxl_cell_location(cls, cell) -> Tuple[str, Optional[str], Optional[str]]:
        """
        从 openpyxl 单元格中提取位置文本、超链接目标及公式
        返回: (location_str, hyperlink_target, formula_err)
        """
        val = cell.value
        hyperlink_target = None
        formula_err = None

        if cell.hyperlink and cell.hyperlink.target:
            hyperlink_target = str(cell.hyperlink.target).strip()

        if isinstance(val, str) and val.strip().startswith("="):
            raw_formula = val.strip()
            # 严格匹配静态字符串: =HYPERLINK("https://...", ...)
            m_static = re.match(
                r'^=\s*HYPERLINK\s*\(\s*"([^"]+)"\s*(?:,\s*.*)?\)$',
                raw_formula,
                re.IGNORECASE,
            )
            if m_static:
                return m_static.group(1).strip(), hyperlink_target, None
            else:
                formula_err = f"不支持动态拼接公式: {raw_formula}"
                return "", hyperlink_target, formula_err

        loc_str = str(val).strip() if val is not None else ""
        return loc_str, hyperlink_target, None

    @classmethod
    def _inspect_header_or_content(
        cls,
        rows_data: List[List[Tuple[Any, Optional[str]]]],
        max_inspect: int = 6
    ) -> Tuple[int, int, int]:
        """
        自动分析表格结构，返回 (header_row_idx, name_col, location_col)
        rows_data: 每行每个单元格为 (cell_value, hyperlink_target)
        header_row_idx = -1 表示无表头，第 1 行即为数据行。
        """
        if not rows_data:
            return -1, -1, -1

        num_cols = max(len(r) for r in rows_data)

        # 1. 尝试在前几行匹配明确表头关键字
        for r_idx in range(min(len(rows_data), max_inspect)):
            row = rows_data[r_idx]

            # 表头行绝对不能包含 URL 链接或 HYPERLINK 公式
            has_url_or_formula = False
            for val, target in row:
                if cls._is_url_like(val) or cls._is_url_like(target):
                    has_url_or_formula = True
                    break
            if has_url_or_formula:
                continue

            name_candidates = []
            loc_candidates = []

            for c_idx, (cell_val, _) in enumerate(row):
                if cell_val is None:
                    continue
                s = str(cell_val).strip()
                if not s or len(s) > 20:
                    continue

                # 排除序号列
                if s.lower() in IGNORE_SERIAL_KEYWORDS or s in IGNORE_SERIAL_KEYWORDS:
                    continue

                # 匹配名称表头
                if s in EXACT_NAME_HEADERS or s.endswith("名称") or s.endswith("台区"):
                    name_candidates.append(c_idx)
                # 匹配位置表头
                elif s in EXACT_LOCATION_HEADERS or s.endswith("链接") or s.endswith("地址"):
                    loc_candidates.append(c_idx)

            if name_candidates and loc_candidates:
                n_col = name_candidates[0]
                l_col = loc_candidates[0]
                if n_col != l_col:
                    return r_idx, n_col, l_col

        # 2. 未匹配到明确表头 -> 无表头模式，通过内容特征分析
        url_scores = [0] * num_cols
        text_scores = [0] * num_cols

        sample_rows = rows_data[:min(len(rows_data), 15)]
        for row in sample_rows:
            for c_idx in range(min(len(row), num_cols)):
                val, target = row[c_idx]
                if cls._is_url_like(val) or cls._is_url_like(target):
                    url_scores[c_idx] += 1
                elif val is not None and str(val).strip():
                    text_scores[c_idx] += 1

        best_loc_col = -1
        max_url_score = 0
        for c_idx in range(num_cols):
            if url_scores[c_idx] > max_url_score:
                max_url_score = url_scores[c_idx]
                best_loc_col = c_idx

        if best_loc_col != -1 and max_url_score > 0:
            best_name_col = -1
            # 优先选择相邻列 (左侧优先)
            for offset in [-1, 1, -2, 2]:
                cand = best_loc_col + offset
                if 0 <= cand < num_cols:
                    is_serial = True
                    for r in sample_rows:
                        if cand < len(r) and r[cand][0] is not None:
                            val_str = str(r[cand][0]).strip()
                            if val_str and not val_str.isdigit():
                                is_serial = False
                                break
                    if not is_serial and text_scores[cand] > 0:
                        best_name_col = cand
                        break

            if best_name_col == -1:
                for c_idx in range(num_cols):
                    if c_idx != best_loc_col and text_scores[c_idx] > 0:
                        best_name_col = c_idx
                        break

            if best_name_col != -1:
                return -1, best_name_col, best_loc_col

        # 3. 兜底 2 列模式
        if num_cols >= 2:
            return -1, 0, 1

        return -1, -1, -1

    @classmethod
    def read_file(cls, file_path: str, allow_network: bool = True) -> List[Record]:
        """读取单个 Excel 文件并解析出所有有效及待处理记录"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".xlsx":
            return cls._read_xlsx(file_path, allow_network)
        elif ext == ".xls":
            return cls._read_xls(file_path, allow_network)
        else:
            raise ValueError(f"不支持的文件格式: {ext} (仅支持 .xlsx 与 .xls)")

    @classmethod
    def _read_xlsx(cls, file_path: str, allow_network: bool) -> List[Record]:
        records: List[Record] = []
        wb = openpyxl.load_workbook(file_path, data_only=False)
        base_name = os.path.basename(file_path)

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            if ws.max_row is None or ws.max_row <= 0:
                continue

            # 读取整表数据矩阵用于表头识别
            raw_matrix = []
            cell_matrix = []
            for r in range(1, ws.max_row + 1):
                row_vals = []
                row_cells = []
                has_any = False
                for c in range(1, ws.max_column + 1):
                    cell = ws.cell(r, c)
                    row_cells.append(cell)
                    val = cell.value
                    tgt = str(cell.hyperlink.target).strip() if (cell.hyperlink and cell.hyperlink.target) else None
                    if (val is not None and str(val).strip()) or tgt:
                        has_any = True
                    row_vals.append((val, tgt))
                if has_any:
                    raw_matrix.append(row_vals)
                    cell_matrix.append((r, row_cells))

            if not raw_matrix:
                continue  # 空工作表跳过

            header_row_idx, name_col, loc_col = cls._inspect_header_or_content(raw_matrix)

            if name_col == -1 or loc_col == -1:
                logger.warning("[%s] 工作表 [%s] 无法识别名称列与链接列，跳过", base_name, sheet_name)
                continue

            # 数据起始行
            start_idx = 0 if header_row_idx == -1 else header_row_idx + 1

            for idx in range(start_idx, len(cell_matrix)):
                orig_row_num, row_cells = cell_matrix[idx]

                # 提取名称
                name_cell = row_cells[name_col] if name_col < len(row_cells) else None
                raw_name = str(name_cell.value).strip() if (name_cell and name_cell.value is not None) else ""

                # 提取位置与超链接
                loc_cell = row_cells[loc_col] if loc_col < len(row_cells) else None
                raw_loc, target_link, formula_err = (
                    cls._extract_openpyxl_cell_location(loc_cell) if loc_cell else ("", None, None)
                )

                # 优先选用有效超链接目标
                effective_loc = target_link if (target_link and cls._is_url_like(target_link)) else raw_loc
                if not effective_loc and target_link:
                    effective_loc = target_link

                # 空行跳过（名称与位置均为空）
                if not raw_name and not effective_loc:
                    continue

                rec = Record(
                    source_file=base_name,
                    sheet_name=sheet_name,
                    row_idx=orig_row_num,
                    name=raw_name,
                    raw_location=effective_loc,
                    hyperlink_target=target_link,
                )

                # 校验点位名称
                if not raw_name:
                    rec.status = "PENDING"
                    rec.error_reason = "点位名称为空"
                    records.append(rec)
                    continue

                if len(raw_name) > 40:
                    rec.status = "PENDING"
                    rec.error_reason = f"名称长度超限 ({len(raw_name)}字 > 40字上限)"
                    records.append(rec)
                    continue

                # 校验位置
                if not effective_loc:
                    rec.status = "PENDING"
                    rec.error_reason = formula_err if formula_err else "位置链接为空"
                    records.append(rec)
                    continue

                if formula_err:
                    rec.status = "PENDING"
                    rec.error_reason = formula_err
                    records.append(rec)
                    continue

                # 解析坐标
                try:
                    res = extract_destination(effective_loc, allow_network=allow_network)
                    valid, msg = is_valid_lnglat(res.lon, res.lat)
                    if not valid:
                        rec.status = "PENDING"
                        rec.error_reason = f"经纬度非法: {msg}"
                    else:
                        rec.lon = res.lon
                        rec.lat = res.lat
                        rec.status = "SUCCESS"
                        rec.method = res.method
                        rec.intermediate_info = res.intermediate_info
                        if not is_xiamen_region(res.lon, res.lat):
                            logger.info(
                                "第 %d 行点位 [%s] 坐标 (%.6f, %.6f) 处于厦门主区域外 (正常写入)",
                                orig_row_num, raw_name, res.lon, res.lat
                            )
                except CoordExtractionError as e:
                    rec.status = "PENDING"
                    rec.error_reason = str(e)
                except Exception as e:
                    rec.status = "PENDING"
                    rec.error_reason = f"解析异常: {e}"

                records.append(rec)

        return records

    @classmethod
    def _read_xls(cls, file_path: str, allow_network: bool) -> List[Record]:
        records: List[Record] = []
        base_name = os.path.basename(file_path)
        wb = xlrd.open_workbook(file_path, formatting_info=False)

        for sheet_idx in range(wb.nsheets):
            ws = wb.sheet_by_index(sheet_idx)
            sheet_name = ws.name
            if ws.nrows <= 0:
                continue

            raw_matrix = []
            row_map = []
            for r in range(ws.nrows):
                row_vals = [(ws.cell_value(r, c), None) for c in range(ws.ncols)]
                if any(v is not None and str(v).strip() for v, _ in row_vals):
                    raw_matrix.append(row_vals)
                    row_map.append(r + 1)

            if not raw_matrix:
                continue

            header_row_idx, name_col, loc_col = cls._inspect_header_or_content(raw_matrix)
            if name_col == -1 or loc_col == -1:
                logger.warning("[%s] 工作表 [%s] 无法识别列结构，跳过", base_name, sheet_name)
                continue

            start_idx = 0 if header_row_idx == -1 else header_row_idx + 1

            for idx in range(start_idx, len(raw_matrix)):
                orig_row_num = row_map[idx]
                row = raw_matrix[idx]

                raw_name = str(row[name_col][0]).strip() if name_col < len(row) and row[name_col][0] is not None else ""
                effective_loc = str(row[loc_col][0]).strip() if loc_col < len(row) and row[loc_col][0] is not None else ""

                if not raw_name and not effective_loc:
                    continue

                rec = Record(
                    source_file=base_name,
                    sheet_name=sheet_name,
                    row_idx=orig_row_num,
                    name=raw_name,
                    raw_location=effective_loc,
                )

                if not raw_name:
                    rec.status = "PENDING"
                    rec.error_reason = "点位名称为空"
                    records.append(rec)
                    continue

                if len(raw_name) > 40:
                    rec.status = "PENDING"
                    rec.error_reason = f"名称长度超限 ({len(raw_name)}字 > 40字上限)"
                    records.append(rec)
                    continue

                if not effective_loc:
                    rec.status = "PENDING"
                    rec.error_reason = "位置链接为空"
                    records.append(rec)
                    continue

                try:
                    res = extract_destination(effective_loc, allow_network=allow_network)
                    valid, msg = is_valid_lnglat(res.lon, res.lat)
                    if not valid:
                        rec.status = "PENDING"
                        rec.error_reason = f"经纬度非法: {msg}"
                    else:
                        rec.lon = res.lon
                        rec.lat = res.lat
                        rec.status = "SUCCESS"
                        rec.method = res.method
                        rec.intermediate_info = res.intermediate_info
                except CoordExtractionError as e:
                    rec.status = "PENDING"
                    rec.error_reason = str(e)
                except Exception as e:
                    rec.status = "PENDING"
                    rec.error_reason = f"解析异常: {e}"

                records.append(rec)

        return records


class TemplateWriter:
    """地图导入模板导出与待处理明细生成器"""

    @classmethod
    def verify_template(cls, template_path: str):
        """核验模板完整性"""
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"找不到导入模板文件: {template_path}")

        wb = openpyxl.load_workbook(template_path, data_only=True)
        if TEMPLATE_SHEET_MAIN not in wb.sheetnames:
            raise ValueError(f"导入模板缺少主数据页: {TEMPLATE_SHEET_MAIN}")

        ws = wb[TEMPLATE_SHEET_MAIN]
        headers = [ws.cell(1, c).value for c in range(1, 10)]
        for i, expected in enumerate(EXPECTED_HEADERS):
            actual = headers[i]
            if actual != expected:
                raise ValueError(
                    f"模板表头第 {i+1} 列不符合规范: 期望 '{expected}', 实际 '{actual}'"
                )

    @classmethod
    def write_results(
        cls,
        template_path: str,
        output_dir: str,
        source_file_path: str,
        records: List[Record],
    ) -> Tuple[Optional[str], Optional[str], int, int]:
        """
        导出结果文件
        返回: (import_file_path, pending_file_path, success_count, pending_count)
        """
        cls.verify_template(template_path)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(source_file_path))[0]

        success_records = [r for r in records if r.status == "SUCCESS"]
        pending_records = [r for r in records if r.status == "PENDING"]

        import_file_path = None
        pending_file_path = None

        # 1. 导出主数据文件 (有成功记录时才生成，杜绝空表声称成功)
        if success_records:
            import_file_path = os.path.join(output_dir, f"{base_name}_地图导入_{timestamp}.xlsx")
            wb_out = openpyxl.load_workbook(template_path)
            ws_main = wb_out[TEMPLATE_SHEET_MAIN]

            # 彻底清除模板第 2 行起的旧数据，杜绝追加历史记录
            if ws_main.max_row > 1:
                ws_main.delete_rows(2, ws_main.max_row - 1)

            # 写入成功记录
            for rec in success_records:
                # 写入数值型经纬度，保留原精度
                ws_main.append([
                    rec.name,
                    float(rec.lon) if rec.lon is not None else None,
                    float(rec.lat) if rec.lat is not None else None,
                    None,  # *地址 留空
                    None,  # 颜色
                    None,  # 图标(外轮廓)
                    None,  # 图标(填充物)
                    None,  # 描述
                    None,  # 文件夹
                ])

            wb_out.save(import_file_path)
            logger.info("已生成地图导入文件: %s (共 %d 条有效点位)", import_file_path, len(success_records))
        else:
            logger.warning("文件 [%s] 无成功解析点位，不生成空白导入文件", base_name)

        # 2. 导出待处理明细文件 (有失败/异常项时生成)
        if pending_records:
            pending_file_path = os.path.join(output_dir, f"{base_name}_待处理明细_{timestamp}.xlsx")
            wb_pending = openpyxl.Workbook()
            ws_p = wb_pending.active
            ws_p.title = "待处理明细"

            headers = [
                "源文件名",
                "工作表",
                "原行号",
                "点位名称",
                "原始位置内容",
                "超链接目标",
                "解析模式",
                "中间信息/坐标系",
                "失败原因",
            ]
            ws_p.append(headers)

            for rec in pending_records:
                ws_p.append([
                    rec.source_file,
                    rec.sheet_name,
                    rec.row_idx,
                    rec.name,
                    rec.raw_location,
                    rec.hyperlink_target or "",
                    rec.method,
                    rec.intermediate_info,
                    rec.error_reason,
                ])

            wb_pending.save(pending_file_path)
            logger.info("已生成待处理明细文件: %s (共 %d 条待处理记录)", pending_file_path, len(pending_records))

        return import_file_path, pending_file_path, len(success_records), len(pending_records)


def setup_file_logger(output_dir: str) -> str:
    """初始化 UTF-8 中文文件日志"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(output_dir, f"converter_{timestamp}.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_log = logging.getLogger()
    root_log.setLevel(logging.DEBUG)
    root_log.handlers = [file_handler, console_handler]

    return log_file


def run_batch_conversion(
    source_files: List[str],
    template_path: str,
    output_dir: str,
    allow_network: bool = True
) -> dict:
    """执行批量转换任务核心逻辑"""
    log_file = setup_file_logger(output_dir)
    logger.info("==========================================")
    logger.info("高德/百度链接转地图导入模板 任务启动")
    logger.info("待处理文件数: %d", len(source_files))
    logger.info("使用模板: %s", template_path)
    logger.info("输出目录: %s", output_dir)
    logger.info("允许网络解析: %s", allow_network)
    logger.info("日志文件: %s", log_file)
    logger.info("==========================================")

    summary = {
        "total_files": len(source_files),
        "total_records": 0,
        "total_success": 0,
        "total_pending": 0,
        "file_results": [],
    }

    for idx, src_file in enumerate(source_files, 1):
        logger.info("\n[%d/%d] 正在处理: %s", idx, len(source_files), src_file)
        try:
            records = TableReader.read_file(src_file, allow_network=allow_network)
            total_rec = len(records)
            import_path, pending_path, succ_cnt, pend_cnt = TemplateWriter.write_results(
                template_path, output_dir, src_file, records
            )

            # 守恒校验
            assert total_rec == succ_cnt + pend_cnt, "记录数校验不守恒"

            summary["total_records"] += total_rec
            summary["total_success"] += succ_cnt
            summary["total_pending"] += pend_cnt

            file_info = {
                "file": src_file,
                "total": total_rec,
                "success": succ_cnt,
                "pending": pend_cnt,
                "import_file": import_path,
                "pending_file": pending_path,
                "status": "OK",
            }
            summary["file_results"].append(file_info)

            logger.info(
                "[%d/%d] 处理完成: 识别总记录=%d, 成功导入=%d, 待处理=%d",
                idx, len(source_files), total_rec, succ_cnt, pend_cnt
            )

        except Exception as e:
            logger.exception("处理文件 [%s] 发生严重异常: %s", src_file, e)
            summary["file_results"].append({
                "file": src_file,
                "total": 0,
                "success": 0,
                "pending": 0,
                "import_file": None,
                "pending_file": None,
                "status": f"ERROR: {e}",
            })

    logger.info("\n================ 汇总报告 ================")
    logger.info("处理文件总数: %d", summary["total_files"])
    logger.info("识别业务记录总数: %d", summary["total_records"])
    logger.info("成功导入点位数: %d", summary["total_success"])
    logger.info("待处理明细数: %d", summary["total_pending"])
    logger.info("==========================================")

    return summary


def get_app_dir() -> str:
    """获取程序所在的真实目录 (兼容 PyInstaller 打包环境)"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def prompt_gui_selection() -> Tuple[Optional[List[str]], Optional[str], Optional[str]]:
    """通过 Tkinter 标准文件对话框引导用户选择路径"""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except ImportError:
        print("错误: 当前 Python 环境缺少 tkinter 图形库，请使用命令行参数运行。")
        return None, None, None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    # 1. 选择待处理源文件
    print("请在弹出的对话框中选择待处理的 Excel 源文件 (支持多选)...")
    source_files = filedialog.askopenfilenames(
        title="1. 请选择待处理的 Excel 源文件 (支持按住Ctrl多选)",
        filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")],
    )
    if not source_files:
        print("用户取消了源文件选择，程序退出。")
        return None, None, None

    # 2. 选择模板文件 (默认优先检查程序同级目录下是否有 导入模板*.xlsx)
    default_tpl = None
    cur_dir = get_app_dir()
    for f in os.listdir(cur_dir):
        if f.startswith("导入模板") and f.endswith(".xlsx"):
            default_tpl = os.path.join(cur_dir, f)
            break

    print("请在弹出的对话框中选择地图导入模板文件...")
    template_file = filedialog.askopenfilename(
        title="2. 请选择地图导入模板文件 (导入模板 (9).xlsx)",
        initialfile=os.path.basename(default_tpl) if default_tpl else "",
        initialdir=cur_dir,
        filetypes=[("Excel 模板文件", "*.xlsx"), ("所有文件", "*.*")],
    )
    if not template_file:
        print("用户取消了模板选择，程序退出。")
        return None, None, None

    # 3. 选择输出目录
    print("请在弹出的对话框中选择结果输出目录...")
    output_dir = filedialog.askdirectory(
        title="3. 请选择结果输出保存目录",
        initialdir=os.path.dirname(source_files[0]),
    )
    if not output_dir:
        print("用户取消了输出目录选择，程序退出。")
        return None, None, None

    return list(source_files), template_file, output_dir


def main():
    parser = argparse.ArgumentParser(
        description="高德/百度地图位置链接批量转换提取工具 (GCJ-02 地图导入模板)"
    )
    parser.add_argument(
        "-i", "--input", nargs="+", help="待处理的 Excel 源文件路径 (支持多个文件)"
    )
    parser.add_argument("-t", "--template", help="地图导入模板文件路径 (.xlsx)")
    parser.add_argument("-o", "--output-dir", help="结果输出目录")
    parser.add_argument(
        "--offline", action="store_true", help="离线模式 (禁止请求高德分享接口)"
    )

    args = parser.parse_args()

    source_files = args.input
    template_path = args.template
    output_dir = args.output_dir
    allow_network = not args.offline
    is_gui = False

    # 如果未提供必要命令行参数，自动进入 Tkinter 交互选择
    if not (source_files and template_path and output_dir):
        is_gui = True
        gui_src, gui_tpl, gui_out = prompt_gui_selection()
        if not (gui_src and gui_tpl and gui_out):
            if is_gui and sys.stdin and sys.stdin.isatty():
                input("\n按回车键退出程序...")
            sys.exit(0)
        source_files = gui_src
        template_path = gui_tpl
        output_dir = gui_out

    # 校验输入有效性
    for sf in source_files:
        if not os.path.exists(sf):
            print(f"错误: 源文件不存在 -> {sf}")
            if is_gui and sys.stdin and sys.stdin.isatty():
                input("\n按回车键退出程序...")
            sys.exit(1)

    if not os.path.exists(template_path):
        print(f"错误: 模板文件不存在 -> {template_path}")
        if is_gui and sys.stdin and sys.stdin.isatty():
            input("\n按回车键退出程序...")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    summary = run_batch_conversion(
        source_files=source_files,
        template_path=template_path,
        output_dir=output_dir,
        allow_network=allow_network,
    )

    if summary["total_success"] == 0 and summary["total_records"] > 0:
        print("\n[警告] 本次处理的所有点位均未能成功解析，请查看待处理明细表！")
        msg = f"处理完成，但所有 {summary['total_records']} 条点位均未成功解析。\n详情请查看待处理明细表！"
    elif summary["total_success"] > 0:
        print("\n[成功] 转换完成！结果已保存至输出目录。")
        msg = (
            f"转换完成！\n"
            f"处理文件数: {summary['total_files']}\n"
            f"识别总记录: {summary['total_records']}\n"
            f"成功导入: {summary['total_success']} 条\n"
            f"待处理: {summary['total_pending']} 条\n\n"
            f"结果已保存至:\n{output_dir}"
        )
    else:
        msg = "未发现任何有效记录。"

    if is_gui:
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo("处理结果", msg)
        except Exception:
            pass
        if sys.stdin and sys.stdin.isatty():
            input("\n按回车键退出程序...")


if __name__ == "__main__":
    main()
