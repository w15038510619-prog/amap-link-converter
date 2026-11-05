# -*- coding: utf-8 -*-
"""
地图位置转换器 V2.0 入口模块
支持:
1. 无参数直接启动: 唤起现代化 Windows 11 Fluent 桌面 GUI 窗口
2. 命令行参数启动: 静默批处理模式 (兼容自动化脚本调用，不弹界面)
"""

import sys
import argparse
from typing import List


def run_gui():
    """启动 Windows 11 Fluent Design 桌面图形界面"""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    # 启用高 DPI 适配与抗锯齿渲染
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("地图位置转换器")
    app.setApplicationVersion("2.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def run_cli(args):
    """静默命令行模式 (沿用已有核心转换能力)"""
    import os
    from map_link_converter import run_batch_conversion
    from core.template_manager import TemplateManager

    source_files: List[str] = args.input
    output_dir: str = args.output_dir or "./导出结果"
    template_path: str = args.template or TemplateManager.get_active_template_path()
    allow_network: bool = not args.offline

    for sf in source_files:
        if not os.path.exists(sf):
            print(f"错误: 源文件不存在 -> {sf}")
            sys.exit(1)

    if not os.path.exists(template_path):
        print(f"错误: 模板文件不存在 -> {template_path}")
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
        sys.exit(1)
    else:
        print("\n[成功] 转换完成！结果已保存至输出目录。")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="地图位置转换器 V2.0 - 高德/百度位置链接转 GCJ-02 地图导入规范"
    )
    parser.add_argument(
        "-i", "--input", nargs="+", help="待处理的 Excel 源文件路径 (支持多个文件)"
    )
    parser.add_argument(
        "-t", "--template", help="地图导入模板文件路径 (留空则自动使用内置官方模板)"
    )
    parser.add_argument("-o", "--output-dir", help="结果输出目录 (默认 ./导出结果)")
    parser.add_argument(
        "--offline", action="store_true", help="离线模式 (禁止请求高德分享接口)"
    )

    # 检查是否传入了输入文件参数
    args, unknown = parser.parse_known_args()

    if args.input:
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
