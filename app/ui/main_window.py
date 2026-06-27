"""
app/ui/main_window.py — Cửa sổ chính với sidebar timer + 5 nav buttons
"""
import os
import subprocess
import sys
import ctypes

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QMessageBox, QStatusBar, QSplitter,
    QToolBar, QMenuBar, QMenu, QInputDialog, QApplication,
    QDialog, QFormLayout, QDialogButtonBox, QLineEdit,
    QSystemTrayIcon,
)

from PySide6.QtCore import Qt, QTimer, QSettings, QProcess, QMetaObject, Q_ARG
from PySide6.QtGui import QFont, QAction, QActionGroup, QKeySequence

from app.ui.styles import MAIN_STYLE, DIALOG_STYLE
from app.ui.widgets.common import TopicBar
from app.ui.widgets.tts_widget import TTSWidget
from app.ui.widgets.video_widget import VideoWidget
from app.ui.widgets.flashcard_widget import FlashcardWidget
from app.ui.widgets.quiz_widget import QuizWidget
from app.ui.widgets.diary_widget import DiaryWidget
from app.ui.widgets.recall_widget import RecallWidget
from app.ui.widgets.topic_dialogs import ChuDeDialog, ChuongDialog, BaiDialog
from app.data.database import get_session, init_db, ChuDe, Chuong, Bai
from app.resources import app_icon, project_root
from app.core.trackpad_controller import (
    TrackpadController, hotkey_display, parse_hotkey,
    DEFAULT_HOTKEY_TOGGLE,
)


NAV_ITEMS = [
    ("🔊", "TTS / Ghi âm",  0),
    ("🎬", "Video",          1),
    ("🃏", "Flashcard",      2),
    ("📝", "Kiểm tra",       3),
    ("🧠", "Luyện nhớ",      4),
    ("📔", "Nhật kí",        5),
]

# ─── Dialog cài đặt hotkey ────────────────────────────────────────────────────

class HotkeySettingsDialog(QDialog):
    """
    Dialog cho phép người dùng tùy chỉnh global hotkey của trackpad.
    Hiển thị hotkey hiện tại, cho nhập hotkey mới, validate trực tiếp.
    """

    def __init__(self, specs: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("⌨ Cài đặt Global Hotkey – Trackpad")
        self.setMinimumWidth(460)
        self.setStyleSheet(DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        # Hướng dẫn
        hint = QLabel(
            "Nhập tổ hợp phím theo dạng <b>modifier+modifier+key</b><br>"
            "Modifier hợp lệ: <code>ctrl</code>, <code>alt</code>, "
            "<code>shift</code>, <code>win</code><br>"
            "Ví dụ: <code>ctrl+alt+t</code> &nbsp; <code>ctrl+shift+F9</code> "
            "&nbsp; <code>alt+F12</code>"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9090c0; font-size:12px; "
                           "background:#0d0d20; border-radius:6px; padding:8px;")
        root.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)

        self._fields: dict[str, QLineEdit] = {}
        labels = {
            "toggle":  "Toggle bật/tắt",
        }
        for action, lbl in labels.items():
            field = QLineEdit(specs.get(action, ""))
            field.setMinimumHeight(32)
            field.setPlaceholderText("vd: ctrl+alt+t")
            field.textChanged.connect(lambda text, f=field: self._validate_field(f))
            self._fields[action] = field
            form.addRow(f"{lbl}:", field)
        root.addLayout(form)

        # Trạng thái validate
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size:11px; color:#ff8080; padding:4px;")
        root.addWidget(self.lbl_status)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("💾  Lưu")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        # Validate ngay lần đầu
        for f in self._fields.values():
            self._validate_field(f)

    def _validate_field(self, field: QLineEdit):
        text = field.text().strip()
        if not text:
            field.setStyleSheet("")
            return
        try:
            parse_hotkey(text)
            field.setStyleSheet("border:1px solid #3c8c3c;")
        except ValueError:
            field.setStyleSheet("border:1px solid #cc3c3c;")

    def _on_accept(self):
        errors = []
        for action, field in self._fields.items():
            text = field.text().strip()
            if not text:
                errors.append(f"• {action}: không được để trống")
                continue
            try:
                parse_hotkey(text)
            except ValueError as e:
                errors.append(f"• {action}: {e}")

        if errors:
            self.lbl_status.setText("Lỗi:\n" + "\n".join(errors))
            return
        self.accept()

    def get_specs(self) -> dict[str, str]:
        return {action: field.text().strip().lower()
                for action, field in self._fields.items()}


# ══════════════════════════════════════════════════════════════════════════════
#  MainWindow
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("Ứng Dụng Học Tập")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1100, 700)
        self.resize(1400, 860)
        
        self.settings = QSettings("HocTap", "HocTapApp")
        self._font_family = self.settings.value("font_family", "Segoe UI")
        self._font_size = int(self.settings.value("font_size", 10))
        self._font_label = self.settings.value("font_label", "Mặc định")
        self._answer_font_size = int(self.settings.value("answer_font_size", 14))
        self._explanation_font_size = int(self.settings.value("explanation_font_size", 13))
        self._quiz_image_height = int(self.settings.value("quiz_image_height", 300))
        self._keep_screen_on = str(self.settings.value("keep_screen_on", "False")).lower() == "true"
        
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        windowState = self.settings.value("windowState")
        if windowState:
            self.restoreState(windowState)
            
        self.setStyleSheet(self._main_style_for_font(self._font_family))

        # Timer state
        self._timer_running = False
        self._timer_paused  = False
        self._elapsed_secs  = 0
        self._timer_mode = "countup"
        self._countdown_total_secs = 0
        self._countdown_remaining_secs = 0
        self._qtimer = QTimer()
        self._qtimer.setInterval(1000)
        self._qtimer.timeout.connect(self._tick)

        # ── Trackpad controller ────────────────────────────────────
        self._trackpad = TrackpadController()
        self._trackpad.on_change(self._on_trackpad_state_changed)

        # Khôi phục hotkey specs đã lưu
        self._load_hotkey_settings()

        self._build_ui()
        self._apply_app_font()
        self._build_menu()
        self._load_topic_data()
        if hasattr(self, "w_quiz"):
            self.w_quiz.restore_state()
            self.w_quiz.set_image_height(self._quiz_image_height)
        if hasattr(self, "w_recall"):
            self.w_recall.restore_state()

        # Đồng bộ trạng thái trackpad ban đầu với UI
        self._refresh_trackpad_ui(self._trackpad.state)

        # Kích hoạt hotkey sau khi UI sẵn sàng
        self._apply_hotkeys()
        
        self._setup_system_tray()

    def _main_style_for_font(self, family: str):
        return MAIN_STYLE.replace(
            "font-family: 'Segoe UI', Arial, sans-serif;",
            f"font-family: '{family}', 'Segoe UI', Arial, sans-serif;",
        )

    # ─── Hotkey settings persistence ─────────────────────────────────

    def _load_hotkey_settings(self):
        """Đọc hotkey specs từ QSettings, fallback về default nếu chưa có."""
        toggle  = self.settings.value("hotkey_toggle",  DEFAULT_HOTKEY_TOGGLE)
        # Validate; nếu corrupt thì reset về default
        try:
            parse_hotkey(toggle)
        except Exception:
            toggle = DEFAULT_HOTKEY_TOGGLE

        self._trackpad.update_hotkey("toggle",  toggle)

    def _save_hotkey_settings(self):
        specs = self._trackpad.hotkey_specs
        self.settings.setValue("hotkey_toggle",  specs["toggle"])
        self.settings.sync()

    def _apply_hotkeys(self):
        """Đăng ký global hotkey với specs hiện tại."""
        results = self._trackpad.register_hotkeys()
        ok_count = sum(v for v in results.values())
        if ok_count > 0:
            self._update_hotkey_menu_label(enabled=True)
        else:
            failed = [k for k, v in results.items() if not v]
            import logging
            logging.getLogger("MainWindow").warning(
                "Một số hotkey đăng ký thất bại: %s", failed
            )
            self._update_hotkey_menu_label(enabled=ok_count > 0)

    # ─── UI Construction ──────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── LEFT SIDEBAR ────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("leftSidebar")
        sidebar.setFixedWidth(200)
        sv = QVBoxLayout(sidebar)
        sv.setSpacing(6)
        sv.setContentsMargins(10, 14, 10, 14)

        app_title = QLabel("📚 Học Tập")
        app_title.setObjectName("h2")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(app_title)

        sep0 = QFrame()
        sep0.setFrameShape(QFrame.Shape.HLine)
        sep0.setStyleSheet("color: #1e1e3a;")
        sv.addWidget(sep0)

        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setObjectName("timerDisplay")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(self.lbl_timer)

        timer_btns = QHBoxLayout()
        timer_btns.setSpacing(4)
        self.btn_start = QPushButton("▶")
        self.btn_stop  = QPushButton("⏹")
        self.btn_countdown = QPushButton("⏳")
        self.btn_start.setToolTip("Bắt đầu / tạm dừng đồng hồ  [Space]")
        self.btn_stop.setToolTip("Reset về đếm xuôi")
        self.btn_countdown.setToolTip("Cài đếm ngược theo số phút")
        for b in [self.btn_start, self.btn_stop, self.btn_countdown]:
            b.setFixedHeight(32)
            b.setFixedWidth(50)
            timer_btns.addWidget(b)
        sv.addLayout(timer_btns)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #1e1e3a;")
        sv.addWidget(sep1)
        sv.addSpacing(4)

        # Trackpad widgets (ẩn khỏi sidebar)
        self.btn_trackpad = QPushButton()
        self.btn_trackpad.hide()
        self.btn_trackpad.setProperty("state", "on")
        self.btn_trackpad.clicked.connect(self._on_trackpad_toggle)
        self.lbl_trackpad_timer = QLabel("")
        self.lbl_trackpad_timer.hide()

        # Nav buttons
        lbl_modules = QLabel("CHỨC NĂNG")
        lbl_modules.setObjectName("muted")
        lbl_modules.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_modules.setStyleSheet("font-size:10px; letter-spacing:1px;")
        sv.addWidget(lbl_modules)
        sv.addSpacing(4)

        self._nav_btns = []
        for icon, label, idx in NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("navBtn")
            btn.setProperty("active", "false")
            btn.setMinimumHeight(46)
            btn.setToolTip(label)
            btn.clicked.connect(lambda _, i=idx: self._switch_module(i))
            sv.addWidget(btn)
            self._nav_btns.append(btn)

        sv.addStretch()

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #1e1e3a;")
        sv.addWidget(sep2)

        self.lbl_session = QLabel("Phiên học: 0 phút")
        self.lbl_session.setObjectName("muted")
        self.lbl_session.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_session.setStyleSheet("font-size:11px;")
        sv.addWidget(self.lbl_session)

        self.btn_restart = QPushButton("🔄 Restart app")
        self.btn_restart.setObjectName("navBtn")
        self.btn_restart.setProperty("active", "false")
        self.btn_restart.setMinimumHeight(38)
        self.btn_restart.setToolTip("Khởi động lại ứng dụng")
        self.btn_restart.setStyleSheet("text-align: center;")
        sv.addWidget(self.btn_restart)

        lbl_ver = QLabel("v1.0.0  •  PySide6")
        lbl_ver.setObjectName("muted")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(lbl_ver)

        root.addWidget(sidebar)

        # ── RIGHT PANEL ─────────────────────────────────────────────
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        rv = QVBoxLayout(right_panel)
        rv.setSpacing(0)
        rv.setContentsMargins(0, 0, 0, 0)

        self.topic_bar = TopicBar()
        rv.addWidget(self.topic_bar)

        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.Shape.HLine)
        sep_h.setStyleSheet("background:#1e1e3a; max-height:1px;")
        rv.addWidget(sep_h)

        self.stack = QStackedWidget()
        rv.addWidget(self.stack, 1)

        self.w_tts    = TTSWidget(self.topic_bar)
        self.w_video  = VideoWidget(self.topic_bar)
        self.w_flash  = FlashcardWidget(self.topic_bar)
        self.w_quiz   = QuizWidget(self.topic_bar)
        self.w_recall = RecallWidget(self.topic_bar)
        self.w_diary  = DiaryWidget(self.topic_bar)

        for w in [self.w_tts, self.w_video, self.w_flash, self.w_quiz, self.w_recall, self.w_diary]:
            self.stack.addWidget(w)

        root.addWidget(right_panel, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng • Bắt đầu bằng cách tạo Chủ đề ở phần bên phải")

        self.btn_start.clicked.connect(self._timer_toggle)
        self.btn_stop.clicked.connect(self._timer_stop)
        self.btn_countdown.clicked.connect(self._set_countdown_timer)
        self.btn_restart.clicked.connect(self._restart_app)

        self.topic_bar.add_requested.connect(self._on_topic_add)
        self.topic_bar.edit_requested.connect(self._on_topic_edit)
        self.topic_bar.delete_requested.connect(self._on_topic_delete)
        self.topic_bar.selection_changed.connect(self._on_topic_changed)

        self.w_tts.player_bar.playback_started.connect(self.w_video._pause)
        self.w_video.playback_started.connect(self.w_tts.player_bar._pause)

        from PySide6.QtGui import QShortcut
        QShortcut(QKeySequence("Space"), self, self._timer_toggle)
        QShortcut(QKeySequence("P"),     self, self._timer_toggle)
        QShortcut(QKeySequence("1"),     self, lambda: self._switch_module(0))
        QShortcut(QKeySequence("2"),     self, lambda: self._switch_module(1))
        QShortcut(QKeySequence("3"),     self, lambda: self._switch_module(2))
        QShortcut(QKeySequence("4"),     self, lambda: self._switch_module(3))
        QShortcut(QKeySequence("5"),     self, lambda: self._switch_module(4))
        QShortcut(QKeySequence("T"),     self, self._on_trackpad_toggle)

        self._switch_module(0)

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("📁 File")
        act_new_topic = QAction("➕ Tạo Chủ đề mới", self)
        act_new_topic.triggered.connect(lambda: self._on_topic_add("chu_de"))
        act_new_topic.setShortcut(QKeySequence("Ctrl+N"))
        file_menu.addAction(act_new_topic)
        file_menu.addSeparator()
        act_restart = QAction("🔄 Restart app", self)
        act_restart.triggered.connect(self._restart_app)
        act_restart.setShortcut(QKeySequence("Ctrl+R"))
        file_menu.addAction(act_restart)
        file_menu.addSeparator()
        act_quit = QAction("❌ Thoát", self)
        act_quit.triggered.connect(self.quit_app)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        file_menu.addAction(act_quit)

        # Module
        mod_menu = mb.addMenu("📋 Module")
        for icon, label, idx in NAV_ITEMS:
            act = QAction(f"{icon} {label}", self)
            act.triggered.connect(lambda _, i=idx: self._switch_module(i))
            act.setShortcut(QKeySequence(str(idx + 1)))
            mod_menu.addAction(act)

        # Timer
        timer_menu = mb.addMenu("⏱ Đồng hồ")
        act_start = QAction("▶/⏸ Bắt đầu / tạm dừng  [Space/P]", self)
        act_start.triggered.connect(self._timer_toggle)
        act_stop = QAction("⏹ Reset về đếm xuôi", self)
        act_stop.triggered.connect(self._timer_stop)
        act_countdown = QAction("⏳ Cài đếm ngược", self)
        act_countdown.triggered.connect(self._set_countdown_timer)
        timer_menu.addActions([act_start, act_stop])
        timer_menu.addSeparator()
        timer_menu.addAction(act_countdown)

        # ── Trackpad menu ──────────────────────────────────────────
        trackpad_menu = mb.addMenu("🖱 Trackpad")

        self.act_trackpad_toggle = QAction("🚫 Tắt Trackpad  [T]", self)
        self.act_trackpad_toggle.triggered.connect(self._on_trackpad_toggle)
        trackpad_menu.addAction(self.act_trackpad_toggle)

        trackpad_menu.addSeparator()

        # ── Global hotkey sub-section ──────────────────────────────
        specs = self._trackpad.hotkey_specs
        self.act_hotkey_toggle_label = QAction(
            f"⌨ Toggle:  {hotkey_display(specs['toggle'])}", self)
        self.act_hotkey_toggle_label.setEnabled(False)   # label only

        trackpad_menu.addAction(self.act_hotkey_toggle_label)

        trackpad_menu.addSeparator()

        act_hotkey_settings = QAction("⚙ Cài đặt hotkey…", self)
        act_hotkey_settings.triggered.connect(self._on_hotkey_settings)
        trackpad_menu.addAction(act_hotkey_settings)

        self.act_hotkey_onoff = QAction("🔴 Tắt global hotkey", self)
        self.act_hotkey_onoff.triggered.connect(self._on_hotkey_toggle_active)
        trackpad_menu.addAction(self.act_hotkey_onoff)

        act_hotkey_reset = QAction("↩ Reset hotkey về mặc định", self)
        act_hotkey_reset.triggered.connect(self._on_hotkey_reset)
        trackpad_menu.addAction(act_hotkey_reset)

        trackpad_menu.addSeparator()

        act_tp_refresh = QAction("🔄 Làm mới thiết bị", self)
        act_tp_refresh.triggered.connect(self._on_trackpad_refresh)
        trackpad_menu.addAction(act_tp_refresh)

        act_tp_info = QAction("ℹ️ Thông tin thiết bị", self)
        act_tp_info.triggered.connect(self._on_trackpad_info)
        trackpad_menu.addAction(act_tp_info)

        # View
        view_menu = mb.addMenu("👁 Giao diện")
        font_menu = view_menu.addMenu("🔤 Font chữ")
        font_group = QActionGroup(self)
        font_group.setExclusive(True)

        act_font_default = QAction("Mặc định - Segoe UI", self, checkable=True)
        act_font_default.setChecked(self._font_family == "Segoe UI")
        act_font_default.triggered.connect(lambda: self._set_app_font("Segoe UI", 10, "Mặc định"))
        font_group.addAction(act_font_default)
        font_menu.addAction(act_font_default)

        act_font_readable = QAction("Dễ đọc - Verdana", self, checkable=True)
        act_font_readable.setChecked(self._font_family == "Verdana")
        act_font_readable.triggered.connect(lambda: self._set_app_font("Verdana", 11, "Dễ đọc"))
        font_group.addAction(act_font_readable)
        font_menu.addAction(act_font_readable)

        size_menu = view_menu.addMenu("🔎 Cỡ chữ đáp án")
        act_font_smaller = QAction("A- Giảm cỡ chữ đáp án", self)
        act_font_smaller.triggered.connect(lambda: self._change_answer_font_size(-1))
        size_menu.addAction(act_font_smaller)
        act_font_larger = QAction("A+ Tăng cỡ chữ đáp án", self)
        act_font_larger.triggered.connect(lambda: self._change_answer_font_size(1))
        size_menu.addAction(act_font_larger)
        act_font_size = QAction("Nhập cỡ chữ đáp án...", self)
        act_font_size.triggered.connect(self._choose_answer_font_size)
        size_menu.addAction(act_font_size)
        act_font_reset_size = QAction("Reset cỡ chữ đáp án", self)
        act_font_reset_size.triggered.connect(lambda: self._set_answer_font_size(14))
        size_menu.addAction(act_font_reset_size)

        explain_size_menu = view_menu.addMenu("💡 Cỡ chữ giải thích")
        act_explain_smaller = QAction("A- Giảm cỡ chữ giải thích", self)
        act_explain_smaller.triggered.connect(lambda: self._change_explanation_font_size(-1))
        explain_size_menu.addAction(act_explain_smaller)
        act_explain_larger = QAction("A+ Tăng cỡ chữ giải thích", self)
        act_explain_larger.triggered.connect(lambda: self._change_explanation_font_size(1))
        explain_size_menu.addAction(act_explain_larger)
        act_explain_size = QAction("Nhập cỡ chữ giải thích...", self)
        act_explain_size.triggered.connect(self._choose_explanation_font_size)
        explain_size_menu.addAction(act_explain_size)
        act_explain_reset_size = QAction("Reset cỡ chữ giải thích", self)
        act_explain_reset_size.triggered.connect(lambda: self._set_explanation_font_size(13))
        explain_size_menu.addAction(act_explain_reset_size)

        view_menu.addSeparator()
        state_str = "Đang Bật" if self._keep_screen_on else "Đang Tắt"
        self.act_keep_screen_on = QAction(f"💡 Screen Lock ({state_str})", self, checkable=True)
        self.act_keep_screen_on.setChecked(self._keep_screen_on)
        self.act_keep_screen_on.triggered.connect(self._toggle_keep_screen_on)
        if self._keep_screen_on:
            self._toggle_keep_screen_on(True)
        view_menu.addAction(self.act_keep_screen_on)

        act_quiz_image_height = QAction("🖼 Cỡ ảnh bài kiểm tra...", self)
        act_quiz_image_height.triggered.connect(self._choose_quiz_image_height)
        view_menu.addAction(act_quiz_image_height)

        # Help
        help_menu = mb.addMenu("❓ Trợ giúp")
        act_about = QAction("ℹ️ Về ứng dụng", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ─── Hotkey menu label sync ────────────────────────────────────────

    def _update_hotkey_menu_label(self, enabled: bool):
        """Cập nhật text nút bật/tắt hotkey và label hotkey trong menu."""
        if enabled:
            self.act_hotkey_onoff.setText("🔴 Tắt global hotkey")
        else:
            self.act_hotkey_onoff.setText("🟢 Bật global hotkey")

        specs = self._trackpad.hotkey_specs
        if hasattr(self, "act_hotkey_toggle_label"):
            self.act_hotkey_toggle_label.setText(
                f"⌨ Toggle:  {hotkey_display(specs['toggle'])}"
            )

    # ─── Hotkey action handlers ────────────────────────────────────────

    def _on_hotkey_settings(self):
        """Mở dialog cài đặt hotkey, áp dụng ngay nếu user nhấn Lưu."""
        dlg = HotkeySettingsDialog(self._trackpad.hotkey_specs, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_specs = dlg.get_specs()
        was_active = self._trackpad.hotkeys_active

        # Cập nhật từng action
        for action, spec in new_specs.items():
            self._trackpad.update_hotkey(action, spec)

        self._save_hotkey_settings()

        # Đăng ký lại nếu đang bật
        if was_active:
            results = self._trackpad.register_hotkeys()
            ok_count = sum(v for v in results.values())
            self._update_hotkey_menu_label(enabled=ok_count > 0)
            failed = [k for k, v in results.items() if not v]
            if failed:
                QMessageBox.warning(
                    self, "Hotkey",
                    f"Một số hotkey đăng ký thất bại: {', '.join(failed)}\n\n"
                    "Tổ hợp phím này có thể đã bị ứng dụng khác chiếm dụng."
                )
            else:
                self.status_bar.showMessage(
                    f"✅ Đã cập nhật hotkey: "
                    f"{hotkey_display(new_specs['toggle'])}"
                )
        else:
            self._update_hotkey_menu_label(enabled=False)
            self.status_bar.showMessage("⌨ Hotkey đã cập nhật (đang tắt)")

    def _on_hotkey_toggle_active(self):
        """Bật / tắt toàn bộ global hotkey."""
        if self._trackpad.hotkeys_active:
            self._trackpad.unregister_hotkeys()
            self._update_hotkey_menu_label(enabled=False)
            self.status_bar.showMessage("🔴 Đã TẮT global hotkey trackpad")
        else:
            results = self._trackpad.register_hotkeys()
            ok = any(results.values())
            self._update_hotkey_menu_label(enabled=ok)
            if ok:
                self.status_bar.showMessage("🟢 Đã BẬT global hotkey trackpad")
            else:
                QMessageBox.warning(
                    self, "Hotkey",
                    "Không thể đăng ký hotkey.\n"
                    "Hãy thử đổi tổ hợp phím khác trong ⚙ Cài đặt hotkey."
                )

    def _on_hotkey_reset(self):
        """Reset tất cả hotkey về giá trị mặc định."""
        reply = QMessageBox.question(
            self, "Reset hotkey",
            f"Reset về mặc định?\n\n"
            f"  Toggle:  {hotkey_display(DEFAULT_HOTKEY_TOGGLE)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        was_active = self._trackpad.hotkeys_active
        self._trackpad.update_hotkey("toggle", DEFAULT_HOTKEY_TOGGLE)
        self._save_hotkey_settings()

        if was_active:
            self._trackpad.register_hotkeys()

        self._update_hotkey_menu_label(enabled=was_active)
        self.status_bar.showMessage("↩ Đã reset hotkey về mặc định")

    # ─── Trackpad callbacks (called from background thread) ───────────

    def _on_trackpad_state_changed(self, state: str):
        QMetaObject.invokeMethod(
            self, "_refresh_trackpad_ui",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, state)
        )

    # ─── Trackpad UI update (must run on main thread) ─────────────────

    from PySide6.QtCore import Slot

    @Slot(str)
    def _refresh_trackpad_ui(self, state: str):
        if state == "off":
            self.btn_trackpad.setText("🚫 Trackpad: TẮT")
            self.btn_trackpad.setProperty("state", "off")
            self.btn_trackpad.setToolTip(
                f"Trackpad đang TẮT — nhấn để bật lại\nThiết bị: {self._trackpad.device_name}"
            )
            if hasattr(self, "act_trackpad_toggle"):
                self.act_trackpad_toggle.setText("✅ Bật Trackpad  [T]")
        elif state == "sim":
            self.btn_trackpad.setText("⚠ Trackpad: SIM")
            self.btn_trackpad.setProperty("state", "sim")
            self.btn_trackpad.setToolTip(
                "Chế độ mô phỏng — không tìm thấy thiết bị phù hợp"
            )
            if hasattr(self, "act_trackpad_toggle"):
                self.act_trackpad_toggle.setText("🔄 Toggle (Simulation)  [T]")
        else:
            self.btn_trackpad.setText("🖱 Trackpad: BẬT")
            self.btn_trackpad.setProperty("state", "on")
            self.btn_trackpad.setToolTip(
                f"Trackpad đang BẬT — nhấn để tắt\nThiết bị: {self._trackpad.device_name}"
            )
            if hasattr(self, "act_trackpad_toggle"):
                self.act_trackpad_toggle.setText("🚫 Tắt Trackpad  [T]")

        self.btn_trackpad.style().unpolish(self.btn_trackpad)
        self.btn_trackpad.style().polish(self.btn_trackpad)

        labels = {"on": "🖱 Trackpad BẬT", "off": "🚫 Trackpad TẮT", "sim": "⚠ Trackpad (Sim)"}
        self.status_bar.showMessage(labels.get(state, "Trackpad"))

    # ─── Trackpad action handlers ─────────────────────────────────────

    def _on_trackpad_toggle(self):
        import threading
        from app.core.trackpad_controller import _is_admin
        if not _is_admin():
            reply = QMessageBox.question(
                self,
                "Cần quyền Administrator",
                "Tắt/bật trackpad yêu cầu quyền Administrator.\n\n"
                "Khởi động lại ứng dụng với quyền Admin ngay bây giờ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._restart_as_admin()
            return
        threading.Thread(target=self._trackpad.toggle, daemon=True).start()

    def _restart_as_admin(self):
        import ctypes
        if getattr(sys, "frozen", False):
            program = sys.executable
            params  = " ".join(sys.argv[1:])
        else:
            from app.resources import project_root
            program = sys.executable
            params  = f'"{os.path.join(project_root(), "main.py")}"'
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", program, params, None, 1
            )
            if int(result) > 32:
                self.close()
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể chạy với quyền Admin:\n{e}")

    def _on_trackpad_refresh(self):
        import threading
        threading.Thread(target=self._trackpad.refresh_device, daemon=True).start()
        self.status_bar.showMessage("Đang làm mới thông tin trackpad…")

    def _on_trackpad_info(self):
        from app.core.trackpad_controller import OS
        state_map = {"on": "BẬT ✅", "off": "TẮT 🚫", "sim": "Mô phỏng ⚠"}
        specs = self._trackpad.hotkey_specs
        hk_status = "🟢 Đang hoạt động" if self._trackpad.hotkeys_active else "🔴 Đã tắt"
        msg = (
            f"<b>Thông tin Trackpad</b><br><br>"
            f"Thiết bị: <b>{self._trackpad.device_name}</b><br>"
            f"Trạng thái: <b>{state_map.get(self._trackpad.state, '?')}</b><br>"
            f"Hệ điều hành: {OS}<br>"
            f"Chế độ mô phỏng: {'Có ⚠' if self._trackpad.is_simulation else 'Không'}<br><br>"
            f"<b>Global Hotkey</b> — {hk_status}<br>"
            f"&nbsp;&nbsp;Toggle: <code>{hotkey_display(specs['toggle'])}</code>"
        )
        QMessageBox.information(self, "Trackpad Manager", msg)

    # ─── Font / display ───────────────────────────────────────────────

    def _set_app_font(self, family: str, size: int, label: str):
        self._font_family = family
        self._font_size = size
        self._font_label = label
        self.settings.setValue("font_family", family)
        self.settings.setValue("font_size", size)
        self.settings.setValue("font_label", label)
        self.settings.sync()
        self._apply_app_font()
        self.status_bar.showMessage(f"Font chữ: {label} ({family}) - cỡ {size}")

    def _set_answer_font_size(self, size: int):
        self._answer_font_size = max(10, min(28, size))
        self.settings.setValue("answer_font_size", self._answer_font_size)
        self.settings.sync()
        if hasattr(self, "w_quiz"):
            self.w_quiz.set_answer_font_size(self._answer_font_size)
        self.status_bar.showMessage(f"Cỡ chữ đáp án: {self._answer_font_size}")

    def _change_answer_font_size(self, delta: int):
        self._set_answer_font_size(self._answer_font_size + delta)

    def _choose_answer_font_size(self):
        size, ok = QInputDialog.getInt(self, "Cỡ chữ đáp án", "Nhập cỡ chữ đáp án A/B/C/D:",
                                        self._answer_font_size, 10, 28, 1)
        if ok:
            self._set_answer_font_size(size)

    def _set_explanation_font_size(self, size: int):
        self._explanation_font_size = max(10, min(28, size))
        self.settings.setValue("explanation_font_size", self._explanation_font_size)
        self.settings.sync()
        if hasattr(self, "w_quiz"):
            self.w_quiz.set_explanation_font_size(self._explanation_font_size)

    def _choose_quiz_image_height(self):
        val, ok = QInputDialog.getInt(self, "Cỡ ảnh bài kiểm tra", "Nhập chiều cao tối đa ảnh (px):", self._quiz_image_height, 100, 2000, 50)
        if ok:
            self._quiz_image_height = val
            self.settings.setValue("quiz_image_height", val)
            self.settings.sync()
            if hasattr(self, "w_quiz"):
                self.w_quiz.set_image_height(val)
            self.status_bar.showMessage(f"Đã cập nhật cỡ ảnh bài kiểm tra: {val}px")
        self.status_bar.showMessage(f"Cỡ chữ giải thích: {self._explanation_font_size}")

    def _change_explanation_font_size(self, delta: int):
        self._set_explanation_font_size(self._explanation_font_size + delta)

    def _choose_explanation_font_size(self):
        size, ok = QInputDialog.getInt(self, "Cỡ chữ giải thích", "Nhập cỡ chữ phần giải thích:",
                                        self._explanation_font_size, 10, 28, 1)
        if ok:
            self._set_explanation_font_size(size)

    def _apply_app_font(self):
        font = QFont(self._font_family, self._font_size)
        app = QApplication.instance()
        if app:
            app.setFont(font)
        self.setFont(font)
        self.setStyleSheet(self._main_style_for_font(self._font_family))
        if hasattr(self, "w_quiz"):
            self.w_quiz.set_answer_font_size(self._answer_font_size)
            self.w_quiz.set_explanation_font_size(self._explanation_font_size)

    def _toggle_keep_screen_on(self, checked: bool):
        self._keep_screen_on = checked
        self.settings.setValue("keep_screen_on", checked)
        state_str = "ON" if checked else "OFF"
        self.act_keep_screen_on.setText(f"💡 Screen Lock ({state_str})")
        if os.name == "nt":
            try:
                ES_CONTINUOUS       = 0x80000000
                ES_DISPLAY_REQUIRED = 0x00000002
                if checked:
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED)
                    self.status_bar.showMessage("💡 Đã BẬT chống tắt màn hình")
                else:
                    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                    self.status_bar.showMessage("💡 Đã TẮT chống tắt màn hình")
            except Exception as e:
                self.status_bar.showMessage(f"Lỗi khi set màn hình: {e}")

    # ─── Module Switch ────────────────────────────────────────────────

    def _switch_module(self, index: int):
        self.stack.setCurrentIndex(index)
        names = ["TTS / Ghi âm", "Video", "Flashcard", "Kiểm tra", "Luyện nhớ", "Nhật kí"]
        for i, btn in enumerate(self._nav_btns):
            active = (i == index)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.status_bar.showMessage(f"Module: {names[index]}")

    # ─── Timer ────────────────────────────────────────────────────────

    def _format_timer(self, seconds: int, compact: bool = False):
        seconds = max(0, seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if compact and h == 0:
            return f"{m:02d}:{s:02d}"
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _update_timer_toggle_button(self):
        if self._timer_running and not self._timer_paused:
            self.btn_start.setText("⏸")
            self.btn_start.setToolTip("Tạm dừng đồng hồ  [Space/P]")
        else:
            self.btn_start.setText("▶")
            self.btn_start.setToolTip("Bắt đầu / tiếp tục đồng hồ  [Space/P]")

    def _tick(self):
        if self._timer_mode == "countdown":
            self._countdown_remaining_secs = max(0, self._countdown_remaining_secs - 1)
            self.lbl_timer.setText(self._format_timer(self._countdown_remaining_secs, compact=True))
            elapsed = self._countdown_total_secs - self._countdown_remaining_secs
            if elapsed > 0 and elapsed % 60 == 0:
                self.lbl_session.setText(f"Còn lại: {self._countdown_remaining_secs // 60} phút")
            if self._countdown_remaining_secs <= 0:
                self._finish_countdown_timer()
            return
        self._elapsed_secs += 1
        self.lbl_timer.setText(self._format_timer(self._elapsed_secs))
        if self._elapsed_secs % 60 == 0:
            self.lbl_session.setText(f"Phiên học: {self._elapsed_secs // 60} phút")

    def _timer_toggle(self):
        if not self._timer_running:
            self._timer_start()
        elif self._timer_paused:
            self._timer_start()
        else:
            self._timer_pause()

    def _timer_start(self):
        if self._timer_paused:
            self._timer_paused = False
            self.lbl_timer.setProperty("paused",  "false")
            self.lbl_timer.setProperty("running", "true")
        elif not self._timer_running:
            if self._timer_mode == "countdown":
                if self._countdown_total_secs <= 0:
                    self._set_countdown_timer(start_after_set=True)
                    return
                if self._countdown_remaining_secs <= 0:
                    self._countdown_remaining_secs = self._countdown_total_secs
                self.lbl_timer.setText(self._format_timer(self._countdown_remaining_secs, compact=True))
                self.lbl_session.setText(f"Đếm ngược: {self._countdown_total_secs // 60} phút")
            else:
                self._elapsed_secs = 0
                self.lbl_session.setText("Phiên học: 0 phút")
            self._timer_running = True
            self.lbl_timer.setProperty("running", "true")
            self.lbl_timer.setProperty("paused",  "false")
        self.lbl_timer.style().unpolish(self.lbl_timer)
        self.lbl_timer.style().polish(self.lbl_timer)
        self._update_timer_toggle_button()
        self._qtimer.start()
        self.status_bar.showMessage(
            "⏳ Đếm ngược đang chạy…" if self._timer_mode == "countdown" else "⏱ Đồng hồ đang chạy…"
        )

    def _timer_pause(self):
        if self._timer_running and not self._timer_paused:
            self._timer_paused = True
            self._qtimer.stop()
            self.lbl_timer.setProperty("running", "false")
            self.lbl_timer.setProperty("paused",  "true")
            self.lbl_timer.style().unpolish(self.lbl_timer)
            self.lbl_timer.style().polish(self.lbl_timer)
            self._update_timer_toggle_button()
            self.status_bar.showMessage("⏸ Đồng hồ tạm dừng")

    def _timer_stop(self):
        self._qtimer.stop()
        mins = self._elapsed_secs // 60
        secs = self._elapsed_secs % 60
        self._timer_running = False
        self._timer_paused  = False
        self._elapsed_secs  = 0
        self._timer_mode = "countup"
        self._countdown_total_secs = 0
        self._countdown_remaining_secs = 0
        self.lbl_timer.setText("00:00:00")
        self.lbl_session.setText("Phiên học: 0 phút")
        self.lbl_timer.setProperty("running", "false")
        self.lbl_timer.setProperty("paused",  "false")
        self.lbl_timer.style().unpolish(self.lbl_timer)
        self.lbl_timer.style().polish(self.lbl_timer)
        self._update_timer_toggle_button()
        self.status_bar.showMessage(f"⏹ Đã reset • Thời gian phiên: {mins}p {secs}s")

    def _set_countdown_timer(self, start_after_set=False):
        minutes, ok = QInputDialog.getInt(self, "Cài đếm ngược",
                                           "Nhập số phút muốn đếm ngược:", 45, 1, 24*60, 1)
        if not ok:
            return
        self._qtimer.stop()
        self._timer_running = False
        self._timer_paused = False
        self._timer_mode = "countdown"
        self._countdown_total_secs = minutes * 60
        self._countdown_remaining_secs = self._countdown_total_secs
        self._elapsed_secs = 0
        self.lbl_timer.setText(self._format_timer(self._countdown_remaining_secs, compact=True))
        self.lbl_session.setText(f"Đếm ngược: {minutes} phút")
        self.lbl_timer.setProperty("running", "false")
        self.lbl_timer.setProperty("paused",  "false")
        self.lbl_timer.style().unpolish(self.lbl_timer)
        self.lbl_timer.style().polish(self.lbl_timer)
        self._update_timer_toggle_button()
        self.status_bar.showMessage(f"⏳ Đã cài đếm ngược {minutes} phút")
        if start_after_set:
            self._timer_start()

    def _finish_countdown_timer(self):
        self._qtimer.stop()
        self._timer_running = False
        self._timer_paused = False
        self._countdown_remaining_secs = 0
        self.lbl_timer.setText("00:00")
        self.lbl_timer.setProperty("running", "false")
        self.lbl_timer.setProperty("paused",  "false")
        self.lbl_timer.style().unpolish(self.lbl_timer)
        self.lbl_timer.style().polish(self.lbl_timer)
        self._update_timer_toggle_button()
        self.lbl_session.setText("Hết giờ")
        self.status_bar.showMessage("⏳ Hết giờ đếm ngược")

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Hết giờ")
        msg.setText("Đã hết thời gian học.")
        msg.setInformativeText("Bạn muốn nghỉ giải lao hay tiếp tục học?")
        btn_break    = msg.addButton("Nghỉ giải lao", QMessageBox.ButtonRole.AcceptRole)
        btn_continue = msg.addButton("Tiếp tục học",  QMessageBox.ButtonRole.ActionRole)
        msg.setDefaultButton(btn_break)
        msg.exec()

        if msg.clickedButton() == btn_continue:
            self._countdown_remaining_secs = self._countdown_total_secs
            self.lbl_timer.setText(self._format_timer(self._countdown_remaining_secs, compact=True))
            self.lbl_session.setText(f"Đếm ngược: {self._countdown_total_secs // 60} phút")
            self._timer_start()
        else:
            self.status_bar.showMessage("Nghỉ giải lao")

    # ─── Restart ─────────────────────────────────────────────────────

    def _restart_app(self):
        reply = QMessageBox.question(
            self, "Restart app", "Khởi động lại ứng dụng ngay bây giờ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if getattr(sys, "frozen", False):
            program = sys.executable
            args    = sys.argv[1:]
            workdir = os.path.dirname(sys.executable)
        else:
            program = sys.executable
            args    = [os.path.join(project_root(), "main.py"), *sys.argv[1:]]
            workdir = project_root()

        startupinfo  = None
        creationflags = 0
        if os.name == "nt":
            if os.path.basename(program).lower() == "python.exe":
                pythonw = os.path.join(os.path.dirname(program), "pythonw.exe")
                if os.path.exists(pythonw):
                    program = pythonw
            creationflags = (subprocess.DETACHED_PROCESS
                             | subprocess.CREATE_NEW_PROCESS_GROUP
                             | subprocess.CREATE_NO_WINDOW)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        restarted = False
        if os.name == "nt":
            try:
                result    = QProcess.startDetached(program, args, workdir)
                restarted = bool(result[0] if isinstance(result, tuple) else result)
            except Exception:
                restarted = False
        if not restarted:
            try:
                subprocess.Popen([program, *args], cwd=workdir, close_fds=True,
                                  creationflags=creationflags, startupinfo=startupinfo)
            except OSError as exc:
                QMessageBox.warning(self, "Restart app", f"Không thể khởi động lại:\n{exc}")
                return

        self.status_bar.showMessage("Đang khởi động lại ứng dụng...")
        self.close()

    # ─── Topic bar callbacks ───────────────────────────────────────────

    def _on_topic_changed(self, cd_id, ch_id, bai_id):
        parts = []
        if cd_id or ch_id or bai_id:
            session = get_session()
            try:
                if cd_id:
                    obj = session.get(ChuDe, cd_id); parts.append(obj.ten) if obj else None
                if ch_id:
                    obj = session.get(Chuong, ch_id); parts.append(obj.ten) if obj else None
                if bai_id:
                    obj = session.get(Bai, bai_id); parts.append(obj.ten) if obj else None
            finally:
                session.close()
        crumb = " › ".join(parts) if parts else "Tất cả"
        self.status_bar.showMessage(f"📂 {crumb}")

    # ─── Topic CRUD ───────────────────────────────────────────────────

    def _load_topic_data(self):
        session = get_session()
        try:
            chu_des = [(c.id, c.ten) for c in session.query(ChuDe).order_by(ChuDe.tao_luc)]
            chuongs = [(c.id, c.ten, c.chu_de_id) for c in session.query(Chuong).order_by(Chuong.tao_luc)]
            bais    = [(b.id, b.ten, b.chuong_id) for b in session.query(Bai).order_by(Bai.tao_luc)]
        finally:
            session.close()
        self.topic_bar.load_data(chu_des, chuongs, bais)

    def _on_topic_add(self, level: str):
        session = get_session()
        try:
            if level == "chu_de":
                dlg = ChuDeDialog(parent=self)
                if dlg.exec() == ChuDeDialog.DialogCode.Accepted:
                    d = dlg.get_data()
                    if d["ten"]:
                        session.add(ChuDe(ten=d["ten"], mo_ta=d["mo_ta"]))
                        session.commit()
                        self.status_bar.showMessage(f"✅ Đã tạo chủ đề: {d['ten']}")
            elif level == "chuong":
                chu_des = [(c.id, c.ten) for c in session.query(ChuDe).order_by(ChuDe.tao_luc)]
                if not chu_des:
                    QMessageBox.warning(self, "Lỗi", "Tạo Chủ đề trước!"); return
                dlg = ChuongDialog(chu_des, chu_de_id=self.topic_bar.get_chu_de_id(), parent=self)
                if dlg.exec() == ChuongDialog.DialogCode.Accepted:
                    d = dlg.get_data()
                    if d["ten"] and d["chu_de_id"]:
                        session.add(Chuong(ten=d["ten"], chu_de_id=d["chu_de_id"]))
                        session.commit()
                        self.status_bar.showMessage(f"✅ Đã tạo chương: {d['ten']}")
            elif level == "bai":
                chuongs = [(c.id, c.ten) for c in session.query(Chuong).order_by(Chuong.tao_luc)]
                if not chuongs:
                    QMessageBox.warning(self, "Lỗi", "Tạo Chương trước!"); return
                dlg = BaiDialog(chuongs, chuong_id=self.topic_bar.get_chuong_id(), parent=self)
                if dlg.exec() == BaiDialog.DialogCode.Accepted:
                    d = dlg.get_data()
                    if d["ten"] and d["chuong_id"]:
                        session.add(Bai(ten=d["ten"], chuong_id=d["chuong_id"]))
                        session.commit()
                        self.status_bar.showMessage(f"✅ Đã tạo bài: {d['ten']}")
        finally:
            session.close()
        self._load_topic_data()

    def _on_topic_edit(self, level: str):
        session = get_session()
        try:
            if level == "chu_de":
                cid = self.topic_bar.get_chu_de_id()
                if not cid: QMessageBox.information(self, "Thông báo", "Chọn Chủ đề để sửa!"); return
                obj = session.get(ChuDe, cid)
                if not obj: return
                dlg = ChuDeDialog(ten=obj.ten, mo_ta=obj.mo_ta, parent=self)
                if dlg.exec() == ChuDeDialog.DialogCode.Accepted:
                    d = dlg.get_data()
                    if d["ten"]: obj.ten = d["ten"]; obj.mo_ta = d["mo_ta"]; session.commit()
            elif level == "chuong":
                cid = self.topic_bar.get_chuong_id()
                if not cid: QMessageBox.information(self, "Thông báo", "Chọn Chương để sửa!"); return
                obj = session.get(Chuong, cid)
                if not obj: return
                chu_des = [(c.id, c.ten) for c in session.query(ChuDe).order_by(ChuDe.tao_luc)]
                dlg = ChuongDialog(chu_des, ten=obj.ten, chu_de_id=obj.chu_de_id, parent=self)
                if dlg.exec() == ChuongDialog.DialogCode.Accepted:
                    d = dlg.get_data()
                    if d["ten"]: obj.ten = d["ten"]; obj.chu_de_id = d["chu_de_id"]; session.commit()
            elif level == "bai":
                bid = self.topic_bar.get_bai_id()
                if not bid: QMessageBox.information(self, "Thông báo", "Chọn Bài để sửa!"); return
                obj = session.get(Bai, bid)
                if not obj: return
                chuongs = [(c.id, c.ten) for c in session.query(Chuong).order_by(Chuong.tao_luc)]
                dlg = BaiDialog(chuongs, ten=obj.ten, chuong_id=obj.chuong_id, parent=self)
                if dlg.exec() == BaiDialog.DialogCode.Accepted:
                    d = dlg.get_data()
                    if d["ten"]: obj.ten = d["ten"]; obj.chuong_id = d["chuong_id"]; session.commit()
        finally:
            session.close()
        self._load_topic_data()

    def _on_topic_delete(self, level: str):
        session = get_session()
        from app.data.database import DoanLap

        def _delete_bai(b):
            for a in b.audios:
                if a.duong_dan and os.path.exists(a.duong_dan):
                    try: os.remove(a.duong_dan)
                    except: pass
                session.query(DoanLap).filter(DoanLap.media_id == a.id, DoanLap.loai_media == "audio").delete()
            for v in b.videos:
                if v.duong_dan and os.path.exists(v.duong_dan):
                    try: os.remove(v.duong_dan)
                    except: pass
                session.query(DoanLap).filter(DoanLap.media_id == v.id, DoanLap.loai_media == "video").delete()
            for f in b.flashcards:
                if f.hinh_anh and os.path.exists(f.hinh_anh):
                    try: os.remove(f.hinh_anh)
                    except: pass
            for n in b.nhat_kis:
                if n.audio_path and os.path.exists(n.audio_path):
                    try: os.remove(n.audio_path)
                    except: pass
            session.delete(b)

        def _delete_chuong(c):
            for b in c.bais: _delete_bai(b)
            session.delete(c)

        def _delete_chu_de(cd):
            for c in cd.chapters: _delete_chuong(c)
            session.delete(cd)

        try:
            if level == "chu_de":
                cid = self.topic_bar.get_chu_de_id()
                if not cid: QMessageBox.information(self, "Thông báo", "Chọn Chủ đề để xóa!"); return
                obj = session.get(ChuDe, cid)
                if not obj: return
                if QMessageBox.question(self, "Xóa chủ đề",
                    f"Xóa '{obj.ten}' và TOÀN BỘ dữ liệu bên trong?") == QMessageBox.StandardButton.Yes:
                    _delete_chu_de(obj); session.commit()
            elif level == "chuong":
                cid = self.topic_bar.get_chuong_id()
                if not cid: QMessageBox.information(self, "Thông báo", "Chọn Chương để xóa!"); return
                obj = session.get(Chuong, cid)
                if not obj: return
                if QMessageBox.question(self, "Xóa chương",
                    f"Xóa '{obj.ten}' và toàn bộ dữ liệu bên trong?") == QMessageBox.StandardButton.Yes:
                    _delete_chuong(obj); session.commit()
            elif level == "bai":
                bid = self.topic_bar.get_bai_id()
                if not bid: QMessageBox.information(self, "Thông báo", "Chọn Bài để xóa!"); return
                obj = session.get(Bai, bid)
                if not obj: return
                if QMessageBox.question(self, "Xóa bài",
                    f"Xóa '{obj.ten}' và toàn bộ dữ liệu bên trong?") == QMessageBox.StandardButton.Yes:
                    _delete_bai(obj); session.commit()
        finally:
            session.close()
        self._load_topic_data()

    # ─── About ────────────────────────────────────────────────────────

    def _show_about(self):
        specs = self._trackpad.hotkey_specs
        QMessageBox.about(
            self, "Ứng Dụng Học Tập — v1.0.0",
            "<b>Ứng Dụng Học Tập</b><br><br>"
            "Công cụ học tập đa năng với:<br>"
            "• 🔊 TTS / Ghi âm (gTTS tiếng Việt + Edge TTS)<br>"
            "• 🎬 Video player + YouTube<br>"
            "• 🃏 Flashcard lật thẻ<br>"
            "• 📝 Kiểm tra trắc nghiệm A/B/C/D<br>"
            "• 🖱 Quản lý Trackpad + Global Hotkey<br>"
            "• 📔 Nhật kí text + ghi âm<br><br>"
            "Quản lý bởi <b>uv</b> + <b>PySide6</b> + <b>SQLAlchemy</b><br><br>"
            "<b>Phím tắt trong app:</b><br>"
            "Space/P — Start/Pause đồng hồ<br>"
            "T — Toggle trackpad (khi app focus)<br>"
            "1–5 — Chuyển module<br>"
            "Ctrl+N — Tạo chủ đề  &nbsp; Ctrl+R — Restart  &nbsp; Ctrl+Q — Thoát<br><br>"
            f"<b>Global Hotkey (mọi lúc):</b><br>"
            f"Toggle: <code>{hotkey_display(specs['toggle'])}</code><br>"
            f"Tắt:   <code>{hotkey_display(specs['disable'])}</code><br>"
            f"Bật:   <code>{hotkey_display(specs['enable'])}</code>"
        )

    # ─── Close ────────────────────────────────────────────────────────

    def _setup_system_tray(self):
        self.really_quit = False
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(app_icon())
        
        tray_menu = QMenu()
        show_action = QAction("Hiển thị", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Thoát", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def quit_app(self):
        self.really_quit = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if not getattr(self, "really_quit", False):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Ứng Dụng Học Tập",
                "Ứng dụng đang chạy ngầm trong khay hệ thống.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            return

        self._qtimer.stop()
        self.settings.setValue("geometry",    self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.sync()
        if hasattr(self, "w_quiz"):
            self.w_quiz.save_state()
        if hasattr(self, "w_recall"):
            self.w_recall.save_state()
        # Hủy hotkey trước khi thoát
        self._trackpad.unregister_hotkeys()
        # Bật lại trackpad khi đóng app
        if self._trackpad.state == "off":
            self._trackpad.enable()
        event.accept()
