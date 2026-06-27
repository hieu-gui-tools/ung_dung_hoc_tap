"""
app/main.py — Entry point
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from app.ui.main_window import MainWindow
from app.resources import app_icon


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("HocTap.UngDungHocTap")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setApplicationName("Ứng Dụng Học Tập")
    app.setOrganizationName("HocTap")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
