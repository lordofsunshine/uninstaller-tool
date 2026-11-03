import os
import tempfile

from app.config import ARROW_ICON, CHECK_ICON

APP_STYLE = """
* {
    outline: none;
}

QWidget {
    background: transparent;
    color: %(text)s;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
}

QMainWindow, QDialog {
    background-color: %(background)s;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    color: %(text)s;
}

QWidget#centralHost {
    background-color: %(background)s;
}

QLabel#appTitle {
    font-size: 21px;
    font-weight: 700;
    color: %(text)s;
    letter-spacing: -0.3px;
}

QLabel#appSubtitle {
    font-size: 13px;
    color: %(text_secondary)s;
}

QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 600;
    color: %(text)s;
}

QLabel#versionBadge {
    background-color: %(primary_soft)s;
    color: %(primary)s;
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
}

QLabel#summaryText {
    font-size: 13px;
    color: %(text_secondary)s;
}

QLabel#summaryText strong {
    color: %(text)s;
}

QLineEdit#searchField {
    background-color: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 9px 14px;
    font-size: 14px;
    color: %(text)s;
}

QLineEdit#searchField:focus {
    border: 1px solid %(primary)s;
    background-color: %(surface)s;
}

QComboBox#sortCombo {
    background-color: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 8px 34px 8px 14px;
    font-size: 13px;
    color: %(text)s;
}

QComboBox#sortCombo:hover {
    border-color: %(border_hover)s;
}

QComboBox#sortCombo:focus {
    border-color: %(primary)s;
}

QComboBox#sortCombo::drop-down {
    border: none;
    width: 28px;
}

QComboBox#sortCombo::down-arrow {
    image: url("%(arrow)s");
    width: 12px;
    height: 12px;
    margin-right: 8px;
}

QComboBox#sortCombo QAbstractItemView {
    background-color: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 10px;
    selection-background-color: %(primary_soft)s;
    selection-color: %(text)s;
    padding: 4px;
}

QPushButton#primaryButton {
    background-color: %(primary)s;
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 10px 22px;
    font-size: 14px;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: %(primary_hover)s;
}

QPushButton#primaryButton:pressed {
    background-color: %(primary_pressed)s;
}

QPushButton#primaryButton:focus {
    background-color: %(primary_hover)s;
}

QPushButton#primaryButton:disabled {
    background-color: %(border)s;
    color: %(text_tertiary)s;
}

QPushButton#secondaryButton {
    background-color: %(surface)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 9px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#secondaryButton:hover {
    border-color: %(border_hover)s;
    background-color: %(surface_alt)s;
}

QPushButton#secondaryButton:pressed {
    background-color: %(progress_bg)s;
}

QPushButton#secondaryButton:focus {
    border-color: %(primary)s;
}

QPushButton#secondaryButton:disabled {
    color: %(text_tertiary)s;
    border-color: %(border)s;
}

QListView#programList {
    background: transparent;
    border: none;
    outline: none;
    padding: 0;
}

QFrame#detailPanel {
    background-color: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 16px;
}

QFrame#detailPanel QLabel {
    background: transparent;
    border: none;
}

QLabel#detailPlaceholder {
    font-size: 13px;
    color: %(text_tertiary)s;
}

QLabel#detailName {
    font-size: 16px;
    font-weight: 700;
    color: %(text)s;
    letter-spacing: -0.2px;
}

QLabel#detailCaption {
    font-size: 11px;
    font-weight: 600;
    color: %(text_tertiary)s;
    letter-spacing: 0.5px;
}

QLabel#detailValue {
    font-size: 13px;
    color: %(text)s;
}

QCheckBox {
    spacing: 8px;
    font-size: 13px;
    color: %(text)s;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid %(scroll_handle)s;
    background-color: %(surface)s;
}

QCheckBox::indicator:hover {
    border-color: %(primary)s;
}

QCheckBox::indicator:focus {
    border-color: %(primary)s;
}

QCheckBox::indicator:checked {
    background-color: %(primary)s;
    border-color: %(primary)s;
    image: url("%(check)s");
}

QListWidget::indicator {
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 2px solid %(scroll_handle)s;
    background-color: %(surface)s;
}

QListWidget::indicator:hover,
QListWidget::indicator:focus {
    border-color: %(primary)s;
}

QListWidget::indicator:checked {
    background-color: %(primary)s;
    border-color: %(primary)s;
    image: url("%(check)s");
}

QProgressBar#topProgress {
    background-color: %(progress_bg)s;
    border: none;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
    text-align: center;
    color: transparent;
}

QProgressBar#topProgress::chunk {
    background-color: %(primary)s;
    border-radius: 2px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: %(scroll_handle)s;
    border-radius: 4px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background-color: %(primary)s;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

QListWidget {
    border: 1px solid %(border)s;
    border-radius: 12px;
    background-color: %(surface)s;
    outline: none;
    padding: 2px;
}

QListWidget::item {
    border-radius: 8px;
    padding: 10px 14px;
    color: %(text)s;
}

QListWidget::item:hover {
    background-color: %(surface_alt)s;
}

QListWidget::item:selected {
    background-color: %(primary_soft)s;
    color: %(text)s;
}

QGroupBox {
    font-weight: 600;
    border: 1px solid %(border)s;
    border-radius: 14px;
    margin-top: 18px;
    padding-top: 18px;
    background-color: %(surface)s;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: %(primary)s;
}

QMenu {
    background-color: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 12px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px 8px 12px;
    border-radius: 8px;
    color: %(text)s;
}

QMenu::item:selected {
    background-color: %(primary_soft)s;
}

QMenu::separator {
    height: 1px;
    background-color: %(border)s;
    margin: 6px 8px;
}

QMessageBox {
    background-color: %(background)s;
}

QMessageBox QLabel {
    color: %(text)s;
    background: transparent;
    font-size: 14px;
}

QMessageBox QPushButton {
    background-color: %(surface)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: 10px;
    padding: 7px 18px;
    min-width: 70px;
    font-size: 13px;
    font-weight: 600;
}

QMessageBox QPushButton:hover {
    border-color: %(border_hover)s;
    background-color: %(surface_alt)s;
}

QMessageBox QPushButton:default {
    background-color: %(primary)s;
    color: #FFFFFF;
    border: none;
}

QMessageBox QPushButton:default:hover {
    background-color: %(primary_hover)s;
}
"""


def _write_svg(name: str, template: str, color: str = "") -> str:
    safe_color = color.lstrip("#") or "888888"
    target = os.path.join(tempfile.gettempdir(), f"uninstaller_{name}_{safe_color}.svg")
    if not os.path.isfile(target):
        try:
            content = template.replace("{color}", safe_color)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError:
            return ""
    return target.replace("\\", "/")


def _arrow_image(colors) -> str:
    return _write_svg("arrow", ARROW_ICON, colors.get("text_secondary", "#888888"))


def _check_image() -> str:
    return _write_svg("check", CHECK_ICON, "#FFFFFF")


def build_style(colors) -> str:
    keys = [
        "background",
        "surface",
        "surface_alt",
        "text",
        "text_secondary",
        "text_tertiary",
        "border",
        "border_hover",
        "primary",
        "primary_hover",
        "primary_pressed",
        "primary_soft",
        "success",
        "success_bg",
        "error",
        "error_bg",
        "progress_bg",
        "scroll_handle",
    ]
    values = {key: colors[key] for key in keys}
    values["arrow"] = _arrow_image(colors)
    values["check"] = _check_image()
    return APP_STYLE % values
