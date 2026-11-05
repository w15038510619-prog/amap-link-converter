# -*- coding: utf-8 -*-
"""
模板管理与配置模块测试
"""

import os
import shutil
import tempfile
import openpyxl
import pytest

from core.template_manager import (
    get_builtin_template_path,
    verify_template_file,
    TemplateManager,
    ConfigManager,
    EXPECTED_HEADERS,
)


@pytest.fixture
def temp_env():
    d = tempfile.mkdtemp(prefix="test_tpl_mgr_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_builtin_template_integrity():
    """测试内置官方模板的有效性与表头规范"""
    path = get_builtin_template_path()
    assert os.path.isfile(path)
    ok, err = verify_template_file(path)
    assert ok, f"内置模板校验失败: {err}"

    # 进一步核验工作表
    wb = openpyxl.load_workbook(path, data_only=True)
    assert "标记位置" in wb.sheetnames
    assert "导入说明" in wb.sheetnames
    assert "颜色说明" in wb.sheetnames

    ws = wb["标记位置"]
    headers = [ws.cell(1, c).value for c in range(1, 10)]
    assert headers == EXPECTED_HEADERS


def test_export_blank_template(temp_env):
    """测试导出一份空白导入模板副本"""
    out_file = os.path.join(temp_env, "blank_template.xlsx")
    ok, msg = TemplateManager.export_blank_template(out_file)
    assert ok, msg
    assert os.path.isfile(out_file)

    wb = openpyxl.load_workbook(out_file, data_only=True)
    ws = wb["标记位置"]
    # 历史记录必须已清空 (仅保留第1行表头)
    assert ws.max_row == 1
    headers = [ws.cell(1, c).value for c in range(1, 10)]
    assert headers == EXPECTED_HEADERS


def test_custom_template_rejection_invalid(temp_env):
    """测试无效自定义模板被严格拒绝"""
    invalid_file = os.path.join(temp_env, "invalid.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "错误表名"
    ws.append(["列1", "列2"])
    wb.save(invalid_file)

    ok, msg = TemplateManager.set_custom_template(invalid_file)
    assert not ok
    assert "缺少必要的工作表" in msg


def test_reset_to_builtin():
    """测试恢复内置模板设置"""
    TemplateManager.reset_to_builtin()
    assert TemplateManager.is_using_builtin()
