# -*- coding: utf-8 -*-
"""
Fluent Design (WinUI 3) 样式系统
提供浅色 (默认) 与深色主题 QSS，遵循 Windows 11 视觉规范
"""

LIGHT_THEME_QSS = """
/* 全局基础设置 */
* {
    font-family: "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #1F2937;
}

QMainWindow, QDialog {
    background-color: #F8F9FA;
}

/* 侧边导航栏 */
#sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E7EB;
}

#navTitle {
    font-size: 16px;
    font-weight: 700;
    color: #0F172A;
    padding-left: 6px;
}

#navSubtitle {
    font-size: 11px;
    color: #64748B;
    padding-left: 6px;
}

/* 侧边导航按钮 */
QPushButton.nav-btn {
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    border: none;
    background-color: transparent;
    font-size: 13px;
    font-weight: 500;
    color: #475569;
}

QPushButton.nav-btn:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

QPushButton.nav-btn:checked {
    background-color: #EFF6FF;
    color: #0066CC;
    font-weight: 600;
    border-left: 3px solid #0066CC;
}

/* 页面级大标题与副标题 */
QLabel.page-title {
    font-size: 20px;
    font-weight: 700;
    color: #0F172A;
}

QLabel.page-subtitle {
    font-size: 12px;
    color: #64748B;
}

QLabel.path-display {
    background-color: #F1F5F9;
    color: #1E293B;
    padding: 6px 10px;
    border-radius: 6px;
}

QLabel.field-label {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
}

/* 现代化卡片容器 */
QLabel.page-title {
    font-size: 20px;
    font-weight: 700;
    color: #F9FAFB;
}

QLabel.page-subtitle {
    font-size: 12px;
    color: #9CA3AF;
}

QLabel.path-display {
    background-color: #374151;
    color: #F9FAFB;
    padding: 6px 10px;
    border-radius: 6px;
}

QLabel.field-label {
    font-size: 12px;
    font-weight: 600;
    color: #D1D5DB;
}

QFrame.fluent-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}

/* 卡片标题 */
QLabel.card-title {
    font-size: 15px;
    font-weight: 600;
    color: #0F172A;
}

QLabel.card-desc {
    font-size: 12px;
    color: #64748B;
}

/* 主要操作按钮 (Fluent Accent Blue) */
QPushButton.btn-primary {
    background-color: #0066CC;
    color: #FFFFFF;
    border: 1px solid #0055AA;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton.btn-primary:hover {
    background-color: #0052A3;
    border-color: #004080;
}

QPushButton.btn-primary:pressed {
    background-color: #004080;
}

QPushButton.btn-primary:disabled {
    background-color: #CBD5E1;
    border-color: #CBD5E1;
    color: #94A3B8;
}

/* 次要操作按钮 (白色描边) */
QPushButton.btn-secondary {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton.btn-secondary:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
    color: #0F172A;
}

QPushButton.btn-secondary:pressed {
    background-color: #F1F5F9;
}

/* 危险/清理按钮 */
QPushButton.btn-danger {
    background-color: #FFFFFF;
    color: #DC2626;
    border: 1px solid #FCA5A5;
    border-radius: 6px;
    padding: 6px 14px;
}

QPushButton.btn-danger:hover {
    background-color: #FEF2F2;
    border-color: #DC2626;
}

/* 拖拽释放区域 */
#dropArea {
    background-color: #FAFAFA;
    border: 2px dashed #CBD5E1;
    border-radius: 10px;
}

#dropArea:hover {
    background-color: #F0F9FF;
    border-color: #0066CC;
}

/* 输入框与搜索栏 */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
}

QLineEdit:focus {
    border: 1px solid #0066CC;
    background-color: #FFFFFF;
}

/* 下拉框 */
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* 数据表格 */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #F1F5F9;
    selection-background-color: #EFF6FF;
    selection-color: #0F172A;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #F8FAFC;
}

QTableWidget::item:hover {
    background-color: #F8FAFC;
}

/* 进度条 */
QProgressBar {
    background-color: #E2E8F0;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: right;
}

QProgressBar::chunk {
    background-color: #0066CC;
    border-radius: 4px;
}

/* 现代化滚动条 */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 24px;
    border-radius: 4px;
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
    height: 8px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    min-width: 24px;
    border-radius: 4px;
}

/* 徽标标签 */
QLabel.badge-success {
    background-color: #DCFCE7;
    color: #15803D;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel.badge-warning {
    background-color: #FEF9C3;
    color: #A16207;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel.badge-error {
    background-color: #FEE2E2;
    color: #B91C1C;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}

QLabel.badge-info {
    background-color: #E0F2FE;
    color: #0369A1;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
    font-size: 11px;
}
"""

DARK_THEME_QSS = """
* {
    font-family: "Microsoft YaHei UI", -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #F3F4F6;
}

QMainWindow, QDialog {
    background-color: #111827;
}

#sidebar {
    background-color: #1F2937;
    border-right: 1px solid #374151;
}

#navTitle {
    font-size: 16px;
    font-weight: 700;
    color: #F9FAFB;
    padding-left: 6px;
}

#navSubtitle {
    font-size: 11px;
    color: #9CA3AF;
    padding-left: 6px;
}

QPushButton.nav-btn {
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    border: none;
    background-color: transparent;
    color: #D1D5DB;
}

QPushButton.nav-btn:hover {
    background-color: #374151;
    color: #FFFFFF;
}

QPushButton.nav-btn:checked {
    background-color: #1E3A8A;
    color: #60A5FA;
    border-left: 3px solid #60A5FA;
}

QLabel.page-title {
    font-size: 20px;
    font-weight: 700;
    color: #F9FAFB;
}

QLabel.page-subtitle {
    font-size: 12px;
    color: #9CA3AF;
}

QLabel.path-display {
    background-color: #374151;
    color: #F9FAFB;
    padding: 6px 10px;
    border-radius: 6px;
}

QLabel.field-label {
    font-size: 12px;
    font-weight: 600;
    color: #D1D5DB;
}

QFrame.fluent-card {
    background-color: #1F2937;
    border: 1px solid #374151;
    border-radius: 10px;
}

QLabel.card-title {
    font-size: 15px;
    font-weight: 600;
    color: #F9FAFB;
}

QLabel.card-desc {
    font-size: 12px;
    color: #9CA3AF;
}

QPushButton.btn-primary {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}

QPushButton.btn-primary:hover {
    background-color: #1D4ED8;
}

QPushButton.btn-secondary {
    background-color: #374151;
    color: #F3F4F6;
    border: 1px solid #4B5563;
    border-radius: 6px;
    padding: 7px 16px;
}

QPushButton.btn-secondary:hover {
    background-color: #4B5563;
}

#dropArea {
    background-color: #182234;
    border: 2px dashed #4B5563;
    border-radius: 10px;
}

#dropArea:hover {
    background-color: #1E293B;
    border-color: #60A5FA;
}

QLineEdit, QComboBox {
    background-color: #374151;
    border: 1px solid #4B5563;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F9FAFB;
}

QTableWidget {
    background-color: #1F2937;
    border: 1px solid #374151;
    border-radius: 8px;
    gridline-color: #374151;
    selection-background-color: #1E3A8A;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #111827;
    color: #9CA3AF;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #374151;
}

QProgressBar {
    background-color: #374151;
    border: none;
    border-radius: 4px;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 4px;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #4B5563;
    border-radius: 4px;
}
"""


def get_stylesheet(theme: str = "light") -> str:
    return DARK_THEME_QSS if theme == "dark" else LIGHT_THEME_QSS
