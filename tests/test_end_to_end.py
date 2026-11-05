# -*- coding: utf-8 -*-
"""
真实附件端到端完整验证测试
输入: 新建 XLSX 工作表.xlsx (18条开闭所无表头记录)
模板: 导入模板 (9).xlsx
"""

import os
import shutil
import tempfile
import openpyxl
import pytest

from map_link_converter import run_batch_conversion, EXPECTED_HEADERS


@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp(prefix="test_e2e_output_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_real_attachment_end_to_end(temp_output_dir):
    src_file = os.path.abspath("新建 XLSX 工作表.xlsx")
    tpl_file = os.path.abspath("导入模板 (9).xlsx")

    assert os.path.exists(src_file), f"找不到源文件: {src_file}"
    assert os.path.exists(tpl_file), f"找不到模板文件: {tpl_file}"

    summary = run_batch_conversion(
        source_files=[src_file],
        template_path=tpl_file,
        output_dir=temp_output_dir,
        allow_network=True,
    )

    assert summary["total_files"] == 1
    assert summary["total_records"] == 18
    assert summary["total_success"] == 18
    assert summary["total_pending"] == 0

    file_res = summary["file_results"][0]
    out_file = file_res["import_file"]
    assert out_file is not None and os.path.exists(out_file)
    assert file_res["pending_file"] is None  # 无失败项时不生成待处理文件

    # 重新加载生成的文件进行严格的物理结构核验
    wb_out = openpyxl.load_workbook(out_file)
    assert wb_out.sheetnames == ["标记位置", "导入说明", "颜色说明"]

    ws_main = wb_out["标记位置"]

    # 1. 核验表头 9 列
    actual_headers = [ws_main.cell(1, c).value for c in range(1, 10)]
    assert actual_headers == EXPECTED_HEADERS

    # 2. 核验数据行数：第 1 行为表头，第 2~19 行为 18 条记录
    assert ws_main.max_row == 19

    # 3. 核验首行与尾行数据内容及数值类型
    # 首行: 尚都开闭所
    assert ws_main.cell(2, 1).value == "尚都开闭所"
    lon_first = ws_main.cell(2, 2).value
    lat_first = ws_main.cell(2, 3).value
    assert isinstance(lon_first, (int, float))
    assert isinstance(lat_first, (int, float))
    assert abs(lon_first - 118.238461464643) < 1e-6
    assert abs(lat_first - 24.6583148404981) < 1e-6

    # 尾行: 何厝开闭所
    assert ws_main.cell(19, 1).value == "何厝开闭所"
    lon_last = ws_main.cell(19, 2).value
    lat_last = ws_main.cell(19, 3).value
    assert isinstance(lon_last, (int, float))
    assert isinstance(lat_last, (int, float))
    assert abs(lon_last - 118.207707256079) < 1e-6
    assert abs(lat_last - 24.6792400844233) < 1e-6

    # 4. 核验说明表及嵌入图片是否完整保留
    assert len(getattr(wb_out["导入说明"], "_images", [])) == 2
    assert len(getattr(wb_out["颜色说明"], "_images", [])) == 2
