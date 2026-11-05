# -*- coding: utf-8 -*-
"""
模板管理与配置持久化模块
负责:
1. 定位和读取内置官方导入模板 (resources/templates/default.xlsx)
2. 兼容 PyInstaller 打包环境与本地源码环境
3. 严格校验模板合规性 (工作表完整性、9列表头与列顺序)
4. 支持导出空白模板副本、加载自定义模板及恢复默认内置模板
5. 记忆和管理用户偏好设置 (输出目录、主题、网络开关)
"""

import json
import logging
import os
import shutil
import sys
from typing import Optional, Tuple

import openpyxl

logger = logging.getLogger(__name__)

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


def get_app_dir() -> str:
    """获取程序所在的真实根目录 (兼容 PyInstaller 冻结环境)"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_builtin_template_path() -> str:
    """
    获取内置官方模板的物理路径。
    在 PyInstaller 单文件打包模式下，资源位于 sys._MEIPASS 中；
    在源码模式下，位于 resources/templates/default.xlsx。
    """
    candidates = []

    # 1. PyInstaller 运行时临时解压目录
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "resources", "templates", "default.xlsx"))
        candidates.append(os.path.join(sys._MEIPASS, "default.xlsx"))

    # 2. 应用程序根目录下的 resources/templates/default.xlsx
    app_root = get_app_dir()
    candidates.append(os.path.join(app_root, "resources", "templates", "default.xlsx"))

    # 3. 本模块上一级源码目录 (开发环境)
    cur_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(cur_dir, "resources", "templates", "default.xlsx"))
    candidates.append(os.path.join(cur_dir, "导入模板 (9).xlsx"))

    for p in candidates:
        if os.path.isfile(p):
            return os.path.abspath(p)

    raise FileNotFoundError(
        f"未找到内置模板文件！尝试过的候选路径: {candidates}"
    )


def get_config_dir() -> str:
    """获取应用配置保存目录 (~/.amap_link_converter)"""
    home = os.path.expanduser("~")
    config_dir = os.path.join(home, ".amap_link_converter")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_file_path() -> str:
    return os.path.join(get_config_dir(), "config.json")


def verify_template_file(template_path: str) -> Tuple[bool, str]:
    """
    严格校验模板完整性:
    1. 文件存在且可被 openpyxl 正常解析
    2. 必须包含 '标记位置'、'导入说明'、'颜色说明' 三个工作表
    3. '标记位置' 第 1 行必须包含 9 列固定表头且顺序、字符完全一致
    返回: (is_valid, error_message)
    """
    if not os.path.exists(template_path):
        return False, f"模板文件不存在: {template_path}"

    try:
        wb = openpyxl.load_workbook(template_path, data_only=True)
    except Exception as e:
        return False, f"无法以 Excel 格式打开模板文件: {e}"

    # 检查工作表完整性
    for required_sheet in [TEMPLATE_SHEET_MAIN, TEMPLATE_SHEET_DESC, TEMPLATE_SHEET_COLOR]:
        if required_sheet not in wb.sheetnames:
            return False, f"模板缺少必要的工作表: [{required_sheet}]"

    # 检查主表头
    ws = wb[TEMPLATE_SHEET_MAIN]
    actual_headers = [ws.cell(1, c).value for c in range(1, 10)]
    for idx, expected in enumerate(EXPECTED_HEADERS):
        actual = actual_headers[idx]
        if actual != expected:
            return False, (
                f"主数据页表头第 {idx+1} 列不合规: "
                f"期望 '{expected}', 实际为 '{actual}'"
            )

    return True, ""


class ConfigManager:
    """配置项管理与读写"""

    DEFAULT_CONFIG = {
        "custom_template_path": None,
        "default_output_dir": None,
        "enable_share_api": True,
        "theme": "light",
        "auto_open_output": True,
    }

    @classmethod
    def load(cls) -> dict:
        config_path = get_config_file_path()
        if not os.path.exists(config_path):
            return dict(cls.DEFAULT_CONFIG)
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                res = dict(cls.DEFAULT_CONFIG)
                res.update(data)
                return res
        except Exception as e:
            logger.warning("读取配置文件失败，使用默认配置: %s", e)
            return dict(cls.DEFAULT_CONFIG)

    @classmethod
    def save(cls, data: dict):
        config_path = get_config_file_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存配置文件失败: %s", e)


class TemplateManager:
    """模板生命周期与操作管理"""

    @classmethod
    def get_active_template_path(cls) -> str:
        """
        获取当前生效的模板路径:
        优先返回用户自定义且校验通过的模板路径；
        若未配置自定义或自定义模板无效，自动回退至内置官方模板。
        """
        cfg = ConfigManager.load()
        custom_path = cfg.get("custom_template_path")

        if custom_path and os.path.isfile(custom_path):
            ok, msg = verify_template_file(custom_path)
            if ok:
                return os.path.abspath(custom_path)
            else:
                logger.warning("自定义模板校验失败，自动回退到内置模板: %s", msg)

        # 默认使用内置官方模板
        return get_builtin_template_path()

    @classmethod
    def is_using_builtin(cls) -> bool:
        """是否正在使用内置模板"""
        cfg = ConfigManager.load()
        custom_path = cfg.get("custom_template_path")
        if not custom_path:
            return True
        if not os.path.isfile(custom_path):
            return True
        ok, _ = verify_template_file(custom_path)
        return not ok

    @classmethod
    def set_custom_template(cls, template_path: str) -> Tuple[bool, str]:
        """
        设置自定义模板。必须先执行格式校验，校验通过才保存至配置。
        """
        ok, msg = verify_template_file(template_path)
        if not ok:
            return False, f"模板格式校验未通过: {msg}"

        cfg = ConfigManager.load()
        cfg["custom_template_path"] = os.path.abspath(template_path)
        ConfigManager.save(cfg)
        return True, "自定义模板已设置并保存"

    @classmethod
    def reset_to_builtin(cls):
        """恢复为使用内置官方模板"""
        cfg = ConfigManager.load()
        cfg["custom_template_path"] = None
        ConfigManager.save(cfg)

    @classmethod
    def export_blank_template(cls, target_file_path: str) -> Tuple[bool, str]:
        """
        导出当前有效模板的一份空白副本给用户使用
        清除原模板中的历史记录后导出
        """
        src_path = cls.get_active_template_path()
        try:
            wb = openpyxl.load_workbook(src_path)
            ws_main = wb[TEMPLATE_SHEET_MAIN]
            # 清理历史示例数据 (A2起)
            if ws_main.max_row > 1:
                ws_main.delete_rows(2, ws_main.max_row - 1)

            os.makedirs(os.path.dirname(os.path.abspath(target_file_path)), exist_ok=True)
            wb.save(target_file_path)
            return True, f"已成功导出空白模板至: {target_file_path}"
        except Exception as e:
            return False, f"导出空白模板失败: {e}"
