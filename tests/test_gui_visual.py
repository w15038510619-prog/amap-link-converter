# -*- coding: utf-8 -*-
"""
GUI 交互与视觉截图验收测试
覆盖:
1. 主界面初始状态
2. 文件导入与数据即时预览
3. 真实转换执行与完成状态展示
4. 历史记录页面
5. 设置与模板管理页面
6. 深色主题切换效果
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

    # 1. 截图: 初始空白主界面
    shot1 = os.path.join(screenshots_dir, "01_main_window_empty.png")
    window.grab().save(shot1)
    assert os.path.isfile(shot1)

    # 2. 导入文件并加载数据预览
    src_file = os.path.abspath("新建 XLSX 工作表.xlsx")
    assert os.path.isfile(src_file)

    convert_page = window.convert_page
    convert_page.add_files([src_file])
    qapp.processEvents()

    # 验证文件列表及预览表数据
    assert convert_page.file_table.rowCount() == 1
    assert convert_page.preview_table.table.rowCount() == 18
    assert convert_page.metric_total.value_lbl.text() == "18"

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

        assert convert_page.metric_success.value_lbl.text() == "18"
        assert convert_page.metric_pending.value_lbl.text() == "0"
        assert convert_page.finish_actions_widget.isVisible()

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
    window.settings_page.combo_theme.setCurrentIndex(1)
    qapp.processEvents()

    shot6 = os.path.join(screenshots_dir, "06_dark_theme.png")
    window.grab().save(shot6)
    assert os.path.isfile(shot6)

    # 恢复浅色主题
    window.settings_page.combo_theme.setCurrentIndex(0)
    qapp.processEvents()
    window.close()
