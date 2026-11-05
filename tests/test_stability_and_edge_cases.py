# -*- coding: utf-8 -*-
"""
稳定性与极端边界用例自动化测试
覆盖:
1. 至少两个 Excel 文件快速连续切换预览 (验证 QThread 生命周期与请求标识安全)
2. 多个文件批量转换队列
3. 包含无效/恶意坏链接 (部分待处理与待处理明细生成)
4. 完全失败用例 (无有效数据或解析崩溃，严禁误标"已导出")
5. 连续重复转换 (无残留状态)
6. 正在异步预览时关闭窗口 (安全退出验证)
7. 大数据量 Excel (2,000+ 点位) 性能与增量加载测试
8. 右键上下文菜单复制完整链接测试
"""

import os
import sys
import time
import tempfile
import pytest
import openpyxl
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from map_link_converter import Record


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def _create_sample_excel(path: str, rows_data: list):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["点位名称", "高德链接"])
    for row in rows_data:
        ws.append(row)
    wb.save(path)


def test_rapid_file_preview_switching(qapp):
    """测试至少两个 Excel 文件快速来回点击切换预览，验证不发生 QThread 崩溃且数据不混淆"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_a = os.path.join(tmpdir, "file_a.xlsx")
        file_b = os.path.join(tmpdir, "file_b.xlsx")

        _create_sample_excel(
            file_a,
            [[f"A点位_{i}", f"https://ditu.amap.com/dir?daddr=118.{200000+i},24.{600000+i},终点"] for i in range(12)]
        )
        _create_sample_excel(
            file_b,
            [[f"B点位_{i}", f"https://ditu.amap.com/dir?daddr=120.{300000+i},30.{500000+i},终点"] for i in range(25)]
        )

        window = MainWindow()
        window.resize(1000, 680)
        window.show()
        qapp.processEvents()

        convert_page = window.convert_page
        convert_page.add_files([file_a, file_b])
        assert convert_page.file_table.rowCount() == 2

        # 快速连续来回点击切换行 (不等待上一次线程完成)
        for _ in range(5):
            convert_page.file_table.selectRow(0)
            convert_page._on_file_selected(0, 0)
            convert_page.file_table.selectRow(1)
            convert_page._on_file_selected(1, 0)
            convert_page.file_table.selectRow(0)
            convert_page._on_file_selected(0, 0)
            qapp.processEvents()

        # 等待所有后台预览线程完成并分发事件
        deadline = time.time() + 5.0
        while (convert_page._active_preview_workers or convert_page.preview_table.table.rowCount() == 0) and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.02)
        qapp.processEvents()

        # 当前选中应当是 file_a (12 条点位)
        assert convert_page.preview_table.table.rowCount() == 12
        assert "A点位_0" in convert_page.preview_table.table.item(0, 1).text()
        assert "file_a.xlsx" in convert_page.preview_current_file_lbl.text()

        window.close()


def test_multi_file_batch_conversion(qapp):
    """测试多文件排队批量转换全流程"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "batch_1.xlsx")
        file2 = os.path.join(tmpdir, "batch_2.xlsx")
        out_dir = os.path.join(tmpdir, "output")
        os.makedirs(out_dir, exist_ok=True)

        _create_sample_excel(
            file1,
            [[f"一期_{i}", f"https://ditu.amap.com/dir?daddr=118.{200000+i},24.{600000+i},终点"] for i in range(5)]
        )
        _create_sample_excel(
            file2,
            [[f"二期_{i}", f"https://ditu.amap.com/dir?daddr=120.{300000+i},30.{500000+i},终点"] for i in range(8)]
        )

        window = MainWindow()
        window.show()
        qapp.processEvents()

        convert_page = window.convert_page
        convert_page.output_dir = out_dir
        convert_page.out_dir_lbl.setText(out_dir)

        convert_page.add_files([file1, file2])
        assert convert_page.file_table.rowCount() == 2

        # 启动批量转换
        convert_page.start_conversion()
        assert convert_page.is_converting is True
        assert not convert_page.btn_add_files.isEnabled()
        assert not convert_page.btn_choose_out.isEnabled()

        while convert_page.worker and convert_page.worker.isRunning():
            qapp.processEvents()
            time.sleep(0.02)
        qapp.processEvents()

        assert convert_page.is_converting is False
        assert convert_page.btn_add_files.isEnabled()
        assert convert_page.btn_choose_out.isEnabled()
        assert convert_page.file_table.item(0, 2).text() == "已导出"
        assert convert_page.file_table.item(1, 2).text() == "已导出"

        # 验证两个输出 Excel 均真实生成
        exported_files = [f for f in os.listdir(out_dir) if f.endswith(".xlsx")]
        assert len(exported_files) == 2

        window.close()


def test_bad_links_and_partial_success(qapp):
    """测试包含坏链接时的'部分待处理'状态与待处理明细生成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_file = os.path.join(tmpdir, "mixed.xlsx")
        out_dir = os.path.join(tmpdir, "output")
        os.makedirs(out_dir, exist_ok=True)

        _create_sample_excel(
            bad_file,
            [
                ["正常点位", "https://ditu.amap.com/dir?daddr=118.238461,24.658314,终点"],
                ["损坏的链接", "https://invalid-map.example.com/not_exist"],
                ["空白内容", ""],
            ]
        )

        window = MainWindow()
        window.show()
        qapp.processEvents()

        convert_page = window.convert_page
        convert_page.output_dir = out_dir
        convert_page.out_dir_lbl.setText(out_dir)

        convert_page.add_files([bad_file])
        deadline = time.time() + 5.0
        while (convert_page.preview_worker and convert_page.preview_worker.isRunning()) and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()

        # 预览期状态
        assert convert_page.preview_table.table.rowCount() == 3

        # 执行转换
        convert_page.start_conversion()
        while convert_page.worker and convert_page.worker.isRunning():
            qapp.processEvents()
            time.sleep(0.02)
        qapp.processEvents()

        assert convert_page.file_table.item(0, 2).text() == "部分待处理"
        assert convert_page.btn_open_pending.isVisible()
        assert convert_page.btn_open_pending.isEnabled()  # 存在待处理记录，按钮必须可用

        # 验证待处理 Excel 表已生成
        pending_files = [f for f in os.listdir(out_dir) if "待处理" in f]
        assert len(pending_files) == 1

        window.close()


def test_complete_failure_file(qapp):
    """测试全失败用例 (如全是坏链接或非法数据)，确保不误标记为'已导出'"""
    with tempfile.TemporaryDirectory() as tmpdir:
        fail_file = os.path.join(tmpdir, "all_bad.xlsx")
        out_dir = os.path.join(tmpdir, "output")
        os.makedirs(out_dir, exist_ok=True)

        _create_sample_excel(
            fail_file,
            [
                ["坏点位1", "https://foo.bar/xyz"],
                ["坏点位2", "http://bar.baz/123"],
            ]
        )

        window = MainWindow()
        window.show()
        qapp.processEvents()

        convert_page = window.convert_page
        convert_page.output_dir = out_dir
        convert_page.out_dir_lbl.setText(out_dir)

        convert_page.add_files([fail_file])
        deadline = time.time() + 5.0
        while (convert_page.preview_worker and convert_page.preview_worker.isRunning()) and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()

        convert_page.start_conversion()
        while convert_page.worker and convert_page.worker.isRunning():
            qapp.processEvents()
            time.sleep(0.02)
        qapp.processEvents()

        # 全失败时状态必须显示为'转换失败'，严禁误标'已导出'
        assert convert_page.file_table.item(0, 2).text() == "转换失败"
        assert convert_page.file_converted_cache.get(fail_file) is False

        window.close()


def test_consecutive_repeated_conversions(qapp):
    """测试对同一组文件连续执行多次转换，状态与缓存重置正确"""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "repeat.xlsx")
        out_dir = os.path.join(tmpdir, "output")
        os.makedirs(out_dir, exist_ok=True)

        _create_sample_excel(
            src,
            [["点位1", "https://ditu.amap.com/dir?daddr=118.238461,24.658314,终点"]]
        )

        window = MainWindow()
        window.show()
        qapp.processEvents()

        convert_page = window.convert_page
        convert_page.output_dir = out_dir

        convert_page.add_files([src])
        deadline = time.time() + 5.0
        while (convert_page.preview_worker and convert_page.preview_worker.isRunning()) and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()

        # 第一次转换
        convert_page.start_conversion()
        while convert_page.worker and convert_page.worker.isRunning():
            qapp.processEvents()
            time.sleep(0.02)
        qapp.processEvents()
        assert convert_page.file_table.item(0, 2).text() == "已导出"

        # 不清空列表，直接发起第二次转换
        convert_page.start_conversion()
        while convert_page.worker and convert_page.worker.isRunning():
            qapp.processEvents()
            time.sleep(0.02)
        qapp.processEvents()
        assert convert_page.file_table.item(0, 2).text() == "已导出"

        window.close()


def test_close_window_while_previewing(qapp):
    """测试在后台异步预览尚未完成时直接关闭主窗口，确保安全释放线程无崩溃"""
    with tempfile.TemporaryDirectory() as tmpdir:
        big_file = os.path.join(tmpdir, "big.xlsx")
        _create_sample_excel(
            big_file,
            [[f"点位_{i}", f"https://ditu.amap.com/dir?daddr=118.{200000+i},24.{600000+i},终点"] for i in range(300)]
        )

        window = MainWindow()
        window.show()
        qapp.processEvents()

        convert_page = window.convert_page
        convert_page.add_files([big_file])

        # 在 worker 仍在运行时立即触发窗口 close
        window.close()
        qapp.processEvents()


def test_large_excel_performance_and_chunked_rendering(qapp):
    """针对包含 2,000 条点位的大表测试性能与增量渲染流畅度"""
    with tempfile.TemporaryDirectory() as tmpdir:
        large_file = os.path.join(tmpdir, "large_2000.xlsx")
        rows = [
            [f"大批量测试点位_{i:04d}", f"https://ditu.amap.com/dir?daddr=118.{i:06d},24.{i:06d},终点"]
            for i in range(2000)
        ]
        _create_sample_excel(large_file, rows)

        window = MainWindow()
        window.show()
        qapp.processEvents()

        convert_page = window.convert_page

        t0 = time.time()
        convert_page.add_files([large_file])

        # 等待后台读取解析并传递至主线程
        deadline = time.time() + 8.0
        while (convert_page.preview_worker and convert_page.preview_worker.isRunning()) and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()

        # 等待首屏分块渲染完成
        deadline = time.time() + 3.0
        while convert_page.preview_table.table.rowCount() == 0 and time.time() < deadline:
            qapp.processEvents()
            time.sleep(0.02)
        qapp.processEvents()

        parse_time = time.time() - t0
        # 2,000 条读取时间应当在合理区间 (通常 < 5.0s)
        assert parse_time < 8.0

        # 检查首屏增量渲染是否立即完成
        assert convert_page.preview_table.table.rowCount() == 2000
        first_item = convert_page.preview_table.table.item(0, 1)
        assert first_item is not None
        assert "大批量测试点位_0000" in first_item.text()

        # 运转 Qt 事件循环让分帧 Timer 跑完后续 chunks
        t_render_start = time.time()
        while convert_page.preview_table._render_offset < 2000 and (time.time() - t_render_start) < 6.0:
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()

        last_item = convert_page.preview_table.table.item(1999, 1)
        assert last_item is not None
        assert "大批量测试点位_1999" in last_item.text()

        window.close()


def test_clipboard_copy_context_menu(qapp):
    """测试数据预览表行信息复制到剪贴板功能"""
    window = MainWindow()
    ptable = window.convert_page.preview_table

    rec = Record(
        source_file="test.xlsx",
        sheet_name="Sheet1",
        row_idx=10,
        name="测试点位复制",
        raw_location="https://ditu.amap.com/dir?daddr=118.200000,24.500000,终点",
        method="amap_daddr",
        lon=118.200000,
        lat=24.500000,
        status="SUCCESS",
        error_reason=None
    )
    ptable.set_records([rec])
    qapp.processEvents()

    # 测试复制行方法
    copied_str = ptable._copy_row_tsv(rec)
    assert "测试点位复制" in copied_str
    assert "118.200000" in copied_str
    assert "24.500000" in copied_str
    assert "https://ditu.amap.com" in copied_str

    window.close()
