import os

path = r'd:\ProjectRoot\PythonProject\ung_dung_hoc_tap\app\ui\main_window.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add QSettings import
if 'QSettings' not in content:
    content = content.replace(
        'from PySide6.QtCore import Qt, QTimer',
        'from PySide6.QtCore import Qt, QTimer, QSettings'
    )

# 2. Add setting load in __init__
init_find = '''        self.setWindowTitle("Ứng dụng Học Tập")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        # Khởi tạo DB
        init_db()

        self._font_family = "Segoe UI"
        self._font_size = 10
        self._font_label = "Mặc định"
        self._answer_font_size = 14
        self._keep_screen_on = False
        self.setStyleSheet(MAIN_STYLE)'''

init_replace = '''        self.setWindowTitle("Ứng dụng Học Tập")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        # Khởi tạo DB
        init_db()

        # Load settings
        self.settings = QSettings("HocTap", "HocTapApp")
        self._font_family = self.settings.value("font_family", "Segoe UI")
        self._font_size = int(self.settings.value("font_size", 10))
        self._font_label = self.settings.value("font_label", "Mặc định")
        self._answer_font_size = int(self.settings.value("answer_font_size", 14))
        self._keep_screen_on = str(self.settings.value("keep_screen_on", "False")).lower() == "true"
        
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        windowState = self.settings.value("windowState")
        if windowState:
            self.restoreState(windowState)

        self.setStyleSheet(self._main_style_for_font(self._font_family))'''

if init_find in content:
    content = content.replace(init_find, init_replace)
else:
    print("Failed to patch __init__")

# 3. Update menu builder to check the loaded settings
menu_find = '''        act_font_default = QAction("Mặc định - Segoe UI", self, checkable=True)
        act_font_default.setChecked(True)
        act_font_default.triggered.connect(lambda: self._set_app_font("Segoe UI", 10, "Mặc định"))
        font_group.addAction(act_font_default)
        font_menu.addAction(act_font_default)

        act_font_readable = QAction("Dễ đọc - Verdana", self, checkable=True)
        act_font_readable.triggered.connect(lambda: self._set_app_font("Verdana", 11, "Dễ đọc"))'''

menu_replace = '''        act_font_default = QAction("Mặc định - Segoe UI", self, checkable=True)
        act_font_default.setChecked(self._font_label == "Mặc định")
        act_font_default.triggered.connect(lambda: self._set_app_font("Segoe UI", 10, "Mặc định"))
        font_group.addAction(act_font_default)
        font_menu.addAction(act_font_default)

        act_font_readable = QAction("Dễ đọc - Verdana", self, checkable=True)
        act_font_readable.setChecked(self._font_label == "Dễ đọc")
        act_font_readable.triggered.connect(lambda: self._set_app_font("Verdana", 11, "Dễ đọc"))'''

if menu_find in content:
    content = content.replace(menu_find, menu_replace)
else:
    print("Failed to patch menu font")

keep_screen_on_find = '''        self.act_keep_screen_on = QAction("💡 Chống tắt màn hình", self, checkable=True)
        self.act_keep_screen_on.triggered.connect(self._toggle_keep_screen_on)
        view_menu.addAction(self.act_keep_screen_on)'''

keep_screen_on_replace = '''        self.act_keep_screen_on = QAction("💡 Chống tắt màn hình", self, checkable=True)
        self.act_keep_screen_on.setChecked(self._keep_screen_on)
        self.act_keep_screen_on.triggered.connect(self._toggle_keep_screen_on)
        if self._keep_screen_on:
            self._toggle_keep_screen_on(True)
        view_menu.addAction(self.act_keep_screen_on)'''

if keep_screen_on_find in content:
    content = content.replace(keep_screen_on_find, keep_screen_on_replace)
else:
    print("Failed to patch menu screen on")

# 4. Save settings when changed
set_app_font_find = '''    def _set_app_font(self, family: str, size: int, label: str):
        self._font_family = family
        self._font_size = size
        self._font_label = label
        self._apply_app_font()
        self.status_bar.showMessage(f"Font chữ: {label} ({family}) - cỡ {size}")'''

set_app_font_replace = '''    def _set_app_font(self, family: str, size: int, label: str):
        self._font_family = family
        self._font_size = size
        self._font_label = label
        self.settings.setValue("font_family", family)
        self.settings.setValue("font_size", size)
        self.settings.setValue("font_label", label)
        self._apply_app_font()
        self.status_bar.showMessage(f"Font chữ: {label} ({family}) - cỡ {size}")'''

if set_app_font_find in content:
    content = content.replace(set_app_font_find, set_app_font_replace)
else:
    print("Failed to patch set_app_font")

set_answer_font_size_find = '''    def _set_answer_font_size(self, size: int):
        self._answer_font_size = max(10, min(28, size))
        if hasattr(self, "w_quiz"):
            self.w_quiz.set_answer_font_size(self._answer_font_size)
        self.status_bar.showMessage(f"Cỡ chữ đáp án: {self._answer_font_size}")'''

set_answer_font_size_replace = '''    def _set_answer_font_size(self, size: int):
        self._answer_font_size = max(10, min(28, size))
        self.settings.setValue("answer_font_size", self._answer_font_size)
        if hasattr(self, "w_quiz"):
            self.w_quiz.set_answer_font_size(self._answer_font_size)
        self.status_bar.showMessage(f"Cỡ chữ đáp án: {self._answer_font_size}")'''

if set_answer_font_size_find in content:
    content = content.replace(set_answer_font_size_find, set_answer_font_size_replace)
else:
    print("Failed to patch set_answer_font_size")

toggle_keep_screen_on_find = '''    def _toggle_keep_screen_on(self, checked: bool):
        self._keep_screen_on = checked
        if os.name == "nt":'''

toggle_keep_screen_on_replace = '''    def _toggle_keep_screen_on(self, checked: bool):
        self._keep_screen_on = checked
        self.settings.setValue("keep_screen_on", checked)
        if os.name == "nt":'''

if toggle_keep_screen_on_find in content:
    content = content.replace(toggle_keep_screen_on_find, toggle_keep_screen_on_replace)
else:
    print("Failed to patch toggle_keep_screen_on")

# 5. Add closeEvent to save geometry
close_event_find = '''    def _restart_app(self):
        """Restart ứng dụng."""
        QApplication.quit()
        subprocess.Popen([sys.executable] + sys.argv)'''

close_event_replace = '''    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

    def _restart_app(self):
        """Restart ứng dụng."""
        QApplication.quit()
        subprocess.Popen([sys.executable] + sys.argv)'''

if close_event_find in content:
    content = content.replace(close_event_find, close_event_replace)
else:
    print("Failed to patch closeEvent")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Settings saving implemented successfully.")
