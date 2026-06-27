"""Resource helpers for app assets."""
import os

from PySide6.QtGui import QIcon


import sys
def project_root() -> str:
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_icon_path() -> str:
    return os.path.join(project_root(), "media", "assets", "app_icon.ico")


def app_icon() -> QIcon:
    icon = QIcon(app_icon_path())
    if icon.isNull():
        png_path = os.path.join(project_root(), "media", "assets", "app_icon.png")
        icon = QIcon(png_path)
    return icon
