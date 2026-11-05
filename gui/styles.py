# -*- coding: utf-8 -*-
"""
精简现代 Windows 11 Fluent Design 样式系统
- 浅色主题: 清爽、精致、呼吸感留白，以微软蓝 (#0067C0) 为主交互色
- 深色主题: 纯正暗色调 (#18181B / #222225)，彻底解决背景发白与对比度失衡
- 统一圆角 (6~8px)、统一微边框 (1px)、无刺眼渐变与多余装饰
"""

LIGHT_THEME_QSS = """
* {
    font-family: "Segoe UI Variable Text", "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    color: #1F2937;
}

QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #F8F9FA;
}

/* 顶部导航与操作栏 */
#topHeader {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
}

#appLogoTitle {
    font-size: 15px;
    font-weight: 700;
    color: #0F172A;
}

#appSubTag {
    font-size: 11px;
    color: #64748B;
    background-color: #F1F5F9;
    padding: 2px 6px;
    border-radius: 4px;
}

/* 头部导航分段药丸按钮 */
QPushButton.header-nav-btn {
    background-color: transparent;
    color: #4B5563;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton.header-nav-btn:hover {
    background-color: #F3F4F6;
    color: #111827;
}

QPushButton.header-nav-btn:checked {
    background-color: #EFF6FF;
    color: #0067C0;
    font-weight: 600;
}

/* 现代化精致卡片 */
QFrame.fluent-card {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
}

/* 主操作按钮 (Win11 Accent Blue) */
QPushButton.btn-primary {
    background-color: #0067C0;
    color: #FFFFFF;
    border: 1px solid #005FB8;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
}

QPushButton.btn-primary:hover {
    background-color: #00529F;
    border-color: #004A8F;
}

QPushButton.btn-primary:pressed {
    background-color: #004A8F;
}

QPushButton.btn-primary:disabled {
    background-color: #E2E8F0;
    border-color: #E2E8F0;
    color: #94A3B8;
}

/* 次级操作按钮 */
QPushButton.btn-secondary {
    background-color: #FFFFFF;
    color: #374151;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px 14px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #F9FAFB;
    border-color: #9CA3AF;
    color: #111827;
}

QPushButton.btn-secondary:pressed {
    background-color: #F3F4F6;
}

QPushButton.btn-ghost {
    background-color: transparent;
    color: #64748B;
    border: none;
    padding: 4px 8px;
}

QPushButton.btn-ghost:hover {
    color: #0F172A;
    background-color: #F1F5F9;
    border-radius: 4px;
}

/* 紧凑型拖拽导入区 */
#dropArea {
    background-color: #FBFBFD;
    border: 1px dashed #CBD5E1;
    border-radius: 8px;
}

#dropArea:hover {
    background-color: #F0F9FF;
    border-color: #0067C0;
}

/* 输入框与检索栏 */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px 9px;
    color: #111827;
}

QLineEdit:focus {
    border: 1px solid #0067C0;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px 8px;
    color: #111827;
}

QComboBox::drop-down {
    border: none;
    width: 18px;
}

/* 数据表格 */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    selection-background-color: #EFF6FF;
    selection-color: #0F172A;
}

QHeaderView::section {
    background-color: #F9FAFB;
    color: #4B5563;
    font-weight: 600;
    font-size: 12px;
    padding: 7px 8px;
    border: none;
    border-bottom: 1px solid #E5E7EB;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #F8FAFC;
}

QTableWidget::item:hover {
    background-color: #F8FAFC;
}

/* 进度条 */
QProgressBar {
    background-color: #E2E8F0;
    border: none;
    border-radius: 3px;
    height: 5px;
}

QProgressBar::chunk {
    background-color: #0067C0;
    border-radius: 3px;
}

/* 现代化极细滚动条 */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 6px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    min-width: 20px;
    border-radius: 3px;
}

/* 徽章与标签状态 */
QLabel.badge-ready {
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 500;
}

QLabel.badge-success {
    background-color: #DCFCE7;
    color: #15803D;
    border: 1px solid #BBF7D0;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.badge-warning {
    background-color: #FEF9C3;
    color: #A16207;
    border: 1px solid #FEF08A;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.badge-error {
    background-color: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FECACA;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.path-box {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 4px 8px;
    color: #334155;
    font-size: 12px;
}
"""

DARK_THEME_QSS = """
* {
    font-family: "Segoe UI Variable Text", "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    color: #F4F4F5;
}

QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #18181B;
}

#topHeader {
    background-color: #202023;
    border-bottom: 1px solid #2E2E32;
}

#appLogoTitle {
    font-size: 15px;
    font-weight: 700;
    color: #F4F4F5;
}

#appSubTag {
    font-size: 11px;
    color: #A1A1AA;
    background-color: #27272A;
    padding: 2px 6px;
    border-radius: 4px;
}

QPushButton.header-nav-btn {
    background-color: transparent;
    color: #A1A1AA;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton.header-nav-btn:hover {
    background-color: #27272A;
    color: #F4F4F5;
}

QPushButton.header-nav-btn:checked {
    background-color: #1E293B;
    color: #38BDF8;
    font-weight: 600;
}

QFrame.fluent-card {
    background-color: #222225;
    border: 1px solid #303035;
    border-radius: 8px;
}

QPushButton.btn-primary {
    background-color: #0284C7;
    color: #FFFFFF;
    border: 1px solid #0369A1;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
}

QPushButton.btn-primary:hover {
    background-color: #0369A1;
}

QPushButton.btn-primary:disabled {
    background-color: #27272A;
    border-color: #27272A;
    color: #71717A;
}

QPushButton.btn-secondary {
    background-color: #2A2A2E;
    color: #F4F4F5;
    border: 1px solid #3F3F46;
    border-radius: 6px;
    padding: 5px 14px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #36363B;
    border-color: #52525B;
}

QPushButton.btn-ghost {
    background-color: transparent;
    color: #A1A1AA;
    border: none;
    padding: 4px 8px;
}

QPushButton.btn-ghost:hover {
    color: #F4F4F5;
    background-color: #27272A;
    border-radius: 4px;
}

#dropArea {
    background-color: #1E1E22;
    border: 1px dashed #3F3F46;
    border-radius: 8px;
}

#dropArea:hover {
    background-color: #1E293B;
    border-color: #38BDF8;
}

QLineEdit, QComboBox {
    background-color: #2A2A2E;
    border: 1px solid #3F3F46;
    border-radius: 6px;
    padding: 5px 8px;
    color: #F4F4F5;
}

QLineEdit:focus {
    border: 1px solid #38BDF8;
}

QTableWidget {
    background-color: #222225;
    border: 1px solid #303035;
    border-radius: 6px;
    gridline-color: #2A2A2E;
    selection-background-color: #1E293B;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #1E1E22;
    color: #A1A1AA;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #303035;
}

QTableWidget::item {
    border-bottom: 1px solid #26262A;
    color: #F4F4F5;
}

QTableWidget::item:hover {
    background-color: #27272A;
}

QProgressBar {
    background-color: #27272A;
    border: none;
    border-radius: 3px;
    height: 5px;
}

QProgressBar::chunk {
    background-color: #38BDF8;
    border-radius: 3px;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
}

QScrollBar::handle:vertical {
    background: #3F3F46;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #52525B;
}

QLabel.badge-ready {
    background-color: #27272A;
    color: #94A3B8;
    border: 1px solid #3F3F46;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
}

QLabel.badge-success {
    background-color: #064E3B;
    color: #6EE7B7;
    border: 1px solid #047857;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
}

QLabel.badge-warning {
    background-color: #713F12;
    color: #FDE047;
    border: 1px solid #A16207;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
}

QLabel.path-box {
    background-color: #2A2A2E;
    border: 1px solid #3F3F46;
    border-radius: 6px;
    padding: 4px 8px;
    color: #E4E4E7;
    font-size: 12px;
}
"""


def get_stylesheet(theme: str = "light") -> str:
    return DARK_THEME_QSS if theme == "dark" else LIGHT_THEME_QSS
