# -*- coding: utf-8 -*-
"""
Excel 输入输出与模板约束全场景测试
包含:
1. .xlsx 读写与表头自适应 (有表头、无表头第一行、多工作表)
2. .xls 旧版表格读取
3. 真实超链接 cell.hyperlink.target 提取
4. HYPERLINK 静态公式解析与动态拼接公式异常处理
5. 坏链接夹在正常链接之间 (单条错误不中断整批)
6. 名称超长 (>40字) 进入待处理且不截断
7. 模板旧 18 条记录清空、图片与说明页完整保留验证
8. 记录数守恒验证 (总数 = 成功数 + 待处理数)
"""

import os
import shutil
import tempfile
import openpyxl
import xlwt
import pytest

from map_link_converter import TableReader, TemplateWriter, Record, run_batch_conversion

VALID_AMAP_URL_1 = (
    "https://m.amap.com/navigation/carmap/__r=24.525608,118.145143,起点,"
    "24.658314840498143,118.23846146464349,终点,,0,0"
)
VALID_AMAP_URL_2 = (
    "https://m.amap.com/navigation/carmap/__r=24.52523,118.145304,起点,"
    "24.685318349880024,118.23948472738267,终点,,0,0"
)
INVALID_URL = "https://invalid-map.example.com/dir?xyz=123"


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="test_map_converter_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_no_header_xlsx_row1_preserved(temp_dir):
    """测试无表头文件，第 1 行数据必须正常提取，不得丢弃"""
    test_file = os.path.join(temp_dir, "no_header.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["尚都开闭所", VALID_AMAP_URL_1])
    ws.append(["汽车城开闭所", VALID_AMAP_URL_2])
    wb.save(test_file)

    records = TableReader.read_file(test_file, allow_network=False)
    assert len(records) == 2
    assert records[0].name == "尚都开闭所"
    assert records[0].status == "SUCCESS"
    assert abs(records[0].lon - 118.238461) < 1e-5
    assert records[1].name == "汽车城开闭所"
    assert records[1].status == "SUCCESS"


def test_with_header_xlsx(temp_dir):
    """测试带表头文件 (包含序号、台区名称、高德地址)"""
    test_file = os.path.join(temp_dir, "with_header.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["序号", "台区名称", "高德地址"])
    ws.append([1, "点位A", VALID_AMAP_URL_1])
    ws.append([2, "点位B", VALID_AMAP_URL_2])
    wb.save(test_file)

    records = TableReader.read_file(test_file, allow_network=False)
    assert len(records) == 2
    assert records[0].name == "点位A"
    assert records[1].name == "点位B"
    assert records[0].status == "SUCCESS"
    assert records[1].status == "SUCCESS"


def test_hyperlinks_and_formula(temp_dir):
    """测试真实单元格超链接与 HYPERLINK 公式 (静态支持、动态报错)"""
    test_file = os.path.join(temp_dir, "hyperlinks.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active

    # 行 1: 真实超链接 target
    cell_name = ws.cell(1, 1, "点位超链接")
    cell_loc = ws.cell(1, 2, "点击前往地图")
    cell_loc.hyperlink = VALID_AMAP_URL_1

    # 行 2: 静态 HYPERLINK 公式
    ws.cell(2, 1, "点位静态公式")
    ws.cell(2, 2, f'=HYPERLINK("{VALID_AMAP_URL_2}", "导航")')

    # 行 3: 动态 HYPERLINK 公式 (不支持)
    ws.cell(3, 1, "点位动态公式")
    ws.cell(3, 2, '=HYPERLINK("https://" & "m.amap.com", "动态")')

    wb.save(test_file)

    records = TableReader.read_file(test_file, allow_network=False)
    assert len(records) == 3
    assert records[0].status == "SUCCESS"
    assert abs(records[0].lon - 118.238461) < 1e-5

    assert records[1].status == "SUCCESS"
    assert abs(records[1].lon - 118.239484) < 1e-5

    assert records[2].status == "PENDING"
    assert "不支持动态拼接公式" in records[2].error_reason


def test_xls_reading(temp_dir):
    """测试旧版 .xls 格式文件读取 (xlrd)"""
    test_file = os.path.join(temp_dir, "legacy.xls")
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("点位表")
    ws.write(0, 0, "序号")
    ws.write(0, 1, "设备名称")
    ws.write(0, 2, "定位链接")

    ws.write(1, 0, 1)
    ws.write(1, 1, "旧版开闭所A")
    ws.write(1, 2, VALID_AMAP_URL_1)

    wb.save(test_file)

    records = TableReader.read_file(test_file, allow_network=False)
    assert len(records) == 1
    assert records[0].name == "旧版开闭所A"
    assert records[0].status == "SUCCESS"
    assert abs(records[0].lon - 118.238461) < 1e-5


def test_bad_link_between_good_links(temp_dir):
    """测试坏链接夹在正常链接之间，单条错误不影响其他正常记录"""
    test_file = os.path.join(temp_dir, "mixed.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["名称", "链接"])
    ws.append(["正常点位1", VALID_AMAP_URL_1])
    ws.append(["损坏点位2", INVALID_URL])
    ws.append(["正常点位3", VALID_AMAP_URL_2])
    wb.save(test_file)

    records = TableReader.read_file(test_file, allow_network=False)
    assert len(records) == 3
    assert records[0].status == "SUCCESS"
    assert records[1].status == "PENDING"
    assert "不支持" in records[1].error_reason
    assert records[2].status == "SUCCESS"


def test_name_length_limit_and_empty_location(temp_dir):
    """测试名称超长 (>40字) 和空位置处理"""
    test_file = os.path.join(temp_dir, "limits.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["名称", "链接"])

    long_name = "这是超过四十个字符的非常非常长的一个配电站开闭所点位名称测试数据用来验证系统不会静默截断"
    ws.append([long_name, VALID_AMAP_URL_1])
    ws.append(["空位置点位", ""])
    wb.save(test_file)

    records = TableReader.read_file(test_file, allow_network=False)
    assert len(records) == 2
    # 超长名称进入待处理，保留完整全称
    assert records[0].status == "PENDING"
    assert "40字上限" in records[0].error_reason
    assert records[0].name == long_name

    # 空位置链接进入待处理
    assert records[1].status == "PENDING"
    assert "位置链接为空" in records[1].error_reason


def test_template_writer_and_image_preservation(temp_dir):
    """
    测试导出到实际模板:
    1. 清除模板中原本旧的 18 条数据
    2. 写入本次新数据
    3. 保留说明表和说明表中的图片
    4. 记录数守恒
    """
    tpl_path = os.path.abspath("导入模板 (9).xlsx")
    assert os.path.exists(tpl_path)

    records = [
        Record(
            source_file="test.xlsx",
            sheet_name="Sheet1",
            row_idx=1,
            name="测试新点位1",
            raw_location=VALID_AMAP_URL_1,
            lon=118.111111,
            lat=24.222222,
            status="SUCCESS",
        ),
        Record(
            source_file="test.xlsx",
            sheet_name="Sheet1",
            row_idx=2,
            name="测试失败点位2",
            raw_location=INVALID_URL,
            status="PENDING",
            error_reason="测试失败原因",
        ),
    ]

    import_path, pending_path, succ_cnt, pend_cnt = TemplateWriter.write_results(
        template_path=tpl_path,
        output_dir=temp_dir,
        source_file_path="test.xlsx",
        records=records,
    )

    assert succ_cnt == 1
    assert pend_cnt == 1
    assert import_path is not None and os.path.exists(import_path)
    assert pending_path is not None and os.path.exists(pending_path)

    # 验证导入文件结构
    wb_out = openpyxl.load_workbook(import_path)
    assert "标记位置" in wb_out.sheetnames
    assert "导入说明" in wb_out.sheetnames
    assert "颜色说明" in wb_out.sheetnames

    # 检查图片是否保留 (导入说明与颜色说明各有 2 张图片)
    assert len(getattr(wb_out["导入说明"], "_images", [])) == 2
    assert len(getattr(wb_out["颜色说明"], "_images", [])) == 2

    # 检查标记位置主表：只有表头 (row 1) + 1 行新数据 (row 2)
    ws_main = wb_out["标记位置"]
    assert ws_main.max_row == 2
    assert ws_main.cell(2, 1).value == "测试新点位1"
    assert abs(ws_main.cell(2, 2).value - 118.111111) < 1e-6
    assert abs(ws_main.cell(2, 3).value - 24.222222) < 1e-6

    # 验证原模板旧的 18 条记录没有残留
    old_names = ["尚都开闭所", "汽车城开闭所", "东固开闭所"]
    all_col1_vals = [ws_main.cell(r, 1).value for r in range(1, ws_main.max_row + 1)]
    for old_n in old_names:
        assert old_n not in all_col1_vals
