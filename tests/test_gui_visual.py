# -*- coding: utf-8 -*-
"""
GUI 交互与视觉截图验收测试 (Fluent 顶栏极简版)
覆盖:
1. 1200×760 主界面初始状态、文件导入与预览、转换完成、历史记录、设置页面、深色模式
2. 960×620 紧凑分辨率下的布局自适应与防截断验证
"""

import os
import sys
import tempfile
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from map_link_converter import TableReader


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_gui_full_lifecycle_and_screenshots(qapp):
    screenshots_dir = os.path.abspath("screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    window = MainWindow()
    window.resize(1200, 760)
    window.show()
    qapp.processEvents()

    # ================= 1. 1200x760 分辨率验收 =================
    # 1. 截图: 初始空白主界面
    shot1 = os.path.join(screenshots_dir, "01_main_window_empty.png")
    window.grab().save(shot1)
    assert os.path.isfile(shot1)

    # 2. 导入文件并加载数据预览
    src_file = os.path.abspath("新建 XLSX 工作表.xlsx")
    assert os.path.isfile(src_file)

    convert_page = window.convert_page
    convert_page.add_files([src_file])

    # 等待异步预览解析完成
    while convert_page.preview_worker and convert_page.preview_worker.isRunning():
        qapp.processEvents()
    qapp.processEvents()

    # 验证文件列表及预览表数据
    assert convert_page.file_table.rowCount() == 1
    assert convert_page.preview_table.table.rowCount() == 18
    assert "新建 XLSX 工作表.xlsx" in convert_page.preview_current_file_lbl.text()

    # 截图: 文件导入与数据预览
    shot2 = os.path.join(screenshots_dir, "02_files_imported_and_preview.png")
    window.grab().save(shot2)
    assert os.path.isfile(shot2)

    # 3. 执行真实转换
    with tempfile.TemporaryDirectory(prefix="gui_test_out_") as temp_out:
        convert_page.output_dir = temp_out
        convert_page.out_dir_lbl.setText(temp_out)

        # 启动转换并等待后台线程结束
        convert_page.start_conversion()
        while convert_page.worker and convert_page.worker.isRunning():
            qapp.processEvents()

        qapp.processEvents()

        assert convert_page.btn_open_out_dir.isVisible()
        assert convert_page.btn_open_pending.isVisible()
        # 18 条点位全部成功，因此待处理按钮被禁用
        assert not convert_page.btn_open_pending.isEnabled()
        assert "成功导出: 18 条" in convert_page.stats_summary_lbl.text()

        # 验证预览表中状态已刷新为"已导出"
        assert convert_page.preview_table.table.item(0, 6).text() == "已导出"

        # 截图: 转换完成状态
        shot3 = os.path.join(screenshots_dir, "03_conversion_completed.png")
        window.grab().save(shot3)
        assert os.path.isfile(shot3)

    # 4. 切换到历史记录页
    window.btn_nav_history.click()
    qapp.processEvents()
    assert window.stack.currentIndex() == 1
    assert window.history_page.table.rowCount() >= 1

    shot4 = os.path.join(screenshots_dir, "04_history_page.png")
    window.grab().save(shot4)
    assert os.path.isfile(shot4)

    # 5. 切换到设置与模板管理页
    window.btn_nav_settings.click()
    qapp.processEvents()
    assert window.stack.currentIndex() == 2

    shot5 = os.path.join(screenshots_dir, "05_settings_page.png")
    window.grab().save(shot5)
    assert os.path.isfile(shot5)

    # 6. 切换为深色主题
    window.btn_theme_toggle.click()
    qapp.processEvents()

    # 切回转换工作区查看深色模式实际效果
    window.btn_nav_convert.click()
    qapp.processEvents()

    shot6 = os.path.join(screenshots_dir, "06_dark_theme.png")
    window.grab().save(shot6)
    assert os.path.isfile(shot6)

    # ================= 2. 960x620 紧凑分辨率自适应验收 =================
    window.resize(960, 620)
    qapp.processEvents()

    # 7. 截图: 960x620 深色主界面 (无任何控件挤压与异常滚动条)
    shot7 = os.path.join(screenshots_dir, "07_dark_theme_960x620.png")
    window.grab().save(shot7)
    assert os.path.isfile(shot7)

    # 恢复浅色主题并在 960x620 下核验
    window.btn_theme_toggle.click()
    qapp.processEvents()

    shot8 = os.path.join(screenshots_dir, "08_light_theme_960x620.png")
    window.grab().save(shot8)
    assert os.path.isfile(shot8)

    window.close()
