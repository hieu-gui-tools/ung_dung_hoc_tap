"""
app/ui/widgets/recall_widget.py — Luyện nhớ đoạn văn (Cloze Deletion)
"""
import re
import random
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QComboBox, QLineEdit, QScrollArea, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QSizePolicy, QInputDialog,
    QSlider, QSpinBox, QLayout, QTabWidget, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QSize, QPoint
from PySide6.QtGui import QFont, QTextCursor, QColor, QFontMetrics

from app.data.database import get_session, VanBanLuyenNho, Bai, Chuong, ChuDe
from app.ui.styles import DIALOG_STYLE

# ─── FlowLayout ───────────────────────────────────────────────────────────────
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        
        for item in self._item_list:
            wid = item.widget()
            space_x = spacing
            space_y = spacing
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
                
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
            
        return y + line_height - rect.y()


# ─── Stopwords Tiếng Việt + Tiếng Anh ────────────────────────────────────────
STOPWORDS = {
    # Tiếng Việt
    "là","và","của","trong","một","các","có","được","từ","để","với",
    "cho","khi","mà","này","đó","những","theo","vào","ra","lên","xuống",
    "tại","qua","sau","trước","về","trên","dưới","hay","hoặc","cũng",
    "đã","sẽ","đang","bị","rất","như","thì","nếu","vì","do","bởi",
    "tuy","nhưng","mặc","dù","thế","nên","vậy","tôi","bạn","họ","chúng",
    "ta","anh","chị","em","ông","bà","nó","người","khi","nơi","cái",
    "con","điều","việc","lúc","năm","ngày","tháng","thứ","số","loại",
    # Tiếng Anh
    "the","a","an","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","could",
    "should","may","might","shall","to","of","in","on","at","by",
    "for","with","about","from","as","it","its","this","that",
    "these","those","i","you","he","she","we","they","and","or",
    "but","if","so","not","no","nor","yet","both","either","each",
}

LEVEL_CONFIG = {
    30: {"pct": 0.30, "hint": True,  "label": "Dễ (30%)",          "color": "#1a5c2a"},
    60: {"pct": 0.60, "hint": False, "label": "Trung bình (60%)",  "color": "#4a3a00"},
    90: {"pct": 0.90, "hint": False, "label": "Khó (90%)",         "color": "#5c1a1a"},
}


# ─── Dialog thêm / sửa một đoạn văn ─────────────────────────────────────────
class VanBanDialog(QDialog):
    def __init__(self, item: VanBanLuyenNho = None, bai_id: int = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sửa đoạn văn" if item else "Thêm đoạn văn")
        self.setMinimumSize(520, 400)
        self.setStyleSheet(DIALOG_STYLE)
        self._item = item

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_ten = QLineEdit()
        self.txt_ten.setPlaceholderText("Tên đoạn văn...")
        self.txt_ten.setMinimumHeight(32)
        form.addRow("Tên:", self.txt_ten)

        self.txt_noi_dung = QTextEdit()
        self.txt_noi_dung.setPlaceholderText("Dán đoạn văn cần ghi nhớ vào đây...")
        self.txt_noi_dung.setMinimumHeight(220)
        form.addRow("Nội dung:", self.txt_noi_dung)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._user_edited_title = False
        self.txt_ten.textEdited.connect(self._on_title_edited)
        self.txt_noi_dung.textChanged.connect(self._on_content_changed)

        if item:
            self.txt_ten.setText(item.ten or "")
            self.txt_noi_dung.setPlainText(item.noi_dung or "")
            self._user_edited_title = True

    def _on_title_edited(self):
        self._user_edited_title = True

    def _on_content_changed(self):
        if not self._user_edited_title:
            content = self.txt_noi_dung.toPlainText().strip()
            words = content.split()[:6]
            if words:
                self.txt_ten.setText(" ".join(words) + "...")
            else:
                self.txt_ten.setText("")

    def get_data(self):
        return {
            "ten": self.txt_ten.text().strip() or "Đoạn văn mới",
            "noi_dung": self.txt_noi_dung.toPlainText().strip(),
        }


# ─── Dialog thêm hàng loạt ───────────────────────────────────────────────────
class BulkAddDialog(QDialog):
    """
    Dialog thêm nhiều đoạn văn cùng lúc.

    Người dùng dán văn bản vào ô lớn và chọn cách phân tách:
      • Dòng trống (mặc định): mỗi đoạn cách nhau ≥1 dòng trống
      • Dấu phân cách tuỳ chỉnh: nhập ký tự/chuỗi phân cách (vd: ---, ===)
    Sau khi bấm "Xem trước" hiện danh sách các đoạn sẽ được thêm,
    mỗi đoạn có thể bỏ chọn để loại ra.
    """

    def __init__(self, bai_id: int = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm hàng loạt đoạn văn")
        self.setMinimumSize(680, 620)
        self.setStyleSheet(DIALOG_STYLE)
        self._bai_id = bai_id
        self._preview_items: list[dict] = []   # [{"ten": ..., "noi_dung": ...}]

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Tab: Nhập / Xem trước ─────────────────────────────────
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # Tab 1: Nhập
        tab_input = QWidget()
        iv = QVBoxLayout(tab_input)
        iv.setSpacing(8)

        iv.addWidget(QLabel("Dán toàn bộ văn bản vào đây:"))
        self.txt_raw = QTextEdit()
        self.txt_raw.setPlaceholderText(
            "Ví dụ (dùng dòng trống để phân tách):\n\n"
            "Đoạn văn thứ nhất...\n\n"
            "Đoạn văn thứ hai...\n\n"
            "Hoặc dùng dấu --- (nhập vào ô Dấu phân cách bên dưới)"
        )
        self.txt_raw.setMinimumHeight(260)
        iv.addWidget(self.txt_raw, 1)

        # Tuỳ chọn phân tách
        sep_row = QHBoxLayout()
        sep_row.addWidget(QLabel("Phân tách bằng:"))
        self.rb_blank_line = QPushButton("Dòng trống")
        self.rb_blank_line.setCheckable(True)
        self.rb_blank_line.setChecked(True)
        self.rb_blank_line.setObjectName("primaryBtn")
        self.rb_custom = QPushButton("Dấu tuỳ chỉnh")
        self.rb_custom.setCheckable(True)
        self.rb_blank_line.clicked.connect(lambda: self._set_sep_mode("blank"))
        self.rb_custom.clicked.connect(lambda: self._set_sep_mode("custom"))
        sep_row.addWidget(self.rb_blank_line)
        sep_row.addWidget(self.rb_custom)

        sep_row.addWidget(QLabel("  Ký tự:"))
        self.txt_sep = QLineEdit("---")
        self.txt_sep.setFixedWidth(120)
        self.txt_sep.setEnabled(False)
        sep_row.addWidget(self.txt_sep)
        sep_row.addStretch()
        iv.addLayout(sep_row)

        # Tuỳ chọn đặt tên tự động
        name_row = QHBoxLayout()
        self.chk_auto_name = QCheckBox("Tự động đặt tên (6 từ đầu)")
        self.chk_auto_name.setChecked(True)
        name_row.addWidget(self.chk_auto_name)
        name_row.addStretch()
        iv.addLayout(name_row)

        btn_preview = QPushButton("🔍  Xem trước danh sách đoạn văn")
        btn_preview.setObjectName("primaryBtn")
        btn_preview.setMinimumHeight(38)
        btn_preview.clicked.connect(self._do_preview)
        iv.addWidget(btn_preview)

        self.tabs.addTab(tab_input, "1. Nhập văn bản")

        # Tab 2: Xem trước & chọn
        self.tab_preview = QWidget()
        pv = QVBoxLayout(self.tab_preview)
        pv.setSpacing(8)

        self.lbl_preview_count = QLabel("Chưa có đoạn văn nào — bấm Xem trước trước.")
        self.lbl_preview_count.setStyleSheet("color:#9090c0; font-size:12px;")
        pv.addWidget(self.lbl_preview_count)

        # Nút chọn nhanh
        sel_row = QHBoxLayout()
        btn_sel_all = QPushButton("✅ Chọn tất cả")
        btn_sel_none = QPushButton("☐ Bỏ chọn tất cả")
        btn_sel_all.clicked.connect(self._select_all)
        btn_sel_none.clicked.connect(self._select_none)
        sel_row.addWidget(btn_sel_all)
        sel_row.addWidget(btn_sel_none)
        sel_row.addStretch()
        pv.addLayout(sel_row)

        self.preview_list = QListWidget()
        self.preview_list.setStyleSheet(
            "QListWidget { background:#12122a; border:1px solid #2a2a4a; border-radius:8px; }"
            "QListWidget::item { padding:8px 10px; border-bottom:1px solid #1e1e3a; }"
            "QListWidget::item:selected { background:#1e2050; }"
            "QListWidget::item:hover { background:#1a1a35; }"
        )
        pv.addWidget(self.preview_list, 1)
        self.tabs.addTab(self.tab_preview, "2. Xem trước")

        # ── Buttons ───────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("➕  Thêm các đoạn đã chọn")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._sep_mode = "blank"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_sep_mode(self, mode: str):
        self._sep_mode = mode
        self.rb_blank_line.setChecked(mode == "blank")
        self.rb_custom.setChecked(mode == "custom")
        self.rb_blank_line.setObjectName("primaryBtn" if mode == "blank" else "")
        self.rb_custom.setObjectName("primaryBtn" if mode == "custom" else "")
        self.rb_blank_line.style().unpolish(self.rb_blank_line)
        self.rb_blank_line.style().polish(self.rb_blank_line)
        self.rb_custom.style().unpolish(self.rb_custom)
        self.rb_custom.style().polish(self.rb_custom)
        self.txt_sep.setEnabled(mode == "custom")

    def _parse_passages(self) -> list[str]:
        raw = self.txt_raw.toPlainText()
        if not raw.strip():
            return []
        if self._sep_mode == "blank":
            # Phân tách bằng ≥1 dòng trống
            parts = re.split(r'\n\s*\n', raw)
        else:
            sep = self.txt_sep.text() or "---"
            parts = raw.split(sep)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _auto_name(text: str) -> str:
        words = text.split()[:6]
        name = " ".join(words)
        if len(text.split()) > 6:
            name += "..."
        return name or "Đoạn văn"

    def _do_preview(self):
        parts = self._parse_passages()
        if not parts:
            QMessageBox.warning(self, "Không có nội dung", "Không tìm thấy đoạn văn nào. Hãy kiểm tra lại văn bản và dấu phân cách.")
            return

        auto = self.chk_auto_name.isChecked()
        self._preview_items = [
            {"ten": self._auto_name(p) if auto else f"Đoạn {i+1}", "noi_dung": p}
            for i, p in enumerate(parts)
        ]

        self.preview_list.clear()
        for idx, item in enumerate(self._preview_items):
            li = QListWidgetItem()
            preview_text = item["noi_dung"][:80].replace("\n", " ")
            if len(item["noi_dung"]) > 80:
                preview_text += "…"
            li.setText(f"[{idx+1}]  {item['ten']}\n       {preview_text}")
            li.setCheckState(Qt.CheckState.Checked)
            self.preview_list.addItem(li)

        self.lbl_preview_count.setText(f"Tìm thấy {len(parts)} đoạn văn — bỏ chọn những đoạn không muốn thêm:")
        self.tabs.setCurrentIndex(1)

    def _select_all(self):
        for i in range(self.preview_list.count()):
            self.preview_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        for i in range(self.preview_list.count()):
            self.preview_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _on_accept(self):
        if not self._preview_items:
            # Nếu chưa xem trước thì tự parse
            self._do_preview()
            if not self._preview_items:
                return

        # Chỉ giữ lại những mục được check
        selected = []
        for i in range(self.preview_list.count()):
            if self.preview_list.item(i).checkState() == Qt.CheckState.Checked:
                selected.append(self._preview_items[i])

        if not selected:
            QMessageBox.warning(self, "Không có gì được chọn", "Hãy chọn ít nhất một đoạn văn.")
            return

        self._preview_items = selected
        self.accept()

    def get_items(self) -> list[dict]:
        """Trả về danh sách [{"ten": ..., "noi_dung": ...}] đã được chọn."""
        return self._preview_items


# ─── Widget luyện tập (phần bên phải) ────────────────────────────────────────
class PracticePanel(QWidget):
    """Panel hiển thị đoạn văn với ô trống để điền"""
    score_updated = Signal(int, int)   # correct, total
    request_next_passage = Signal()
    request_prev_passage = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blanks = []       # list of (QLineEdit, correct_answer, original_word)
        self._level = 30
        self._text = ""
        self._checked = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 14)

        # Stat row
        stat_row = QHBoxLayout()
        self.lbl_total  = self._stat_badge("Tổng", "0", "#1e1e3a")
        self.lbl_correct = self._stat_badge("Đúng", "0", "#1a5c2a")
        self.lbl_wrong   = self._stat_badge("Sai",  "0", "#5c1a1a")
        self.lbl_pct     = self._stat_badge("Tỉ lệ","—",  "#1a2a5c")
        for w in [self.lbl_total, self.lbl_correct, self.lbl_wrong, self.lbl_pct]:
            stat_row.addWidget(w)
        stat_row.addStretch()
        root.addLayout(stat_row)

        # Passage scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #2a2a4a; border-radius: 8px; }")

        self.passage_container = QWidget()
        self.passage_layout = QVBoxLayout(self.passage_container)
        self.passage_layout.setContentsMargins(16, 14, 16, 14)
        self.passage_layout.setSpacing(8)
        self.passage_layout.addStretch()
        self.scroll.setWidget(self.passage_container)
        root.addWidget(self.scroll, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        self.btn_check = QPushButton("✅  Kiểm tra")
        self.btn_check.setObjectName("primaryBtn")
        self.btn_check.clicked.connect(self.check_answers)

        self.btn_hint = QPushButton("💡  Gợi ý tất cả")
        self.btn_hint.clicked.connect(self.show_all_hints)

        self.btn_reveal = QPushButton("👁  Xem đáp án")
        self.btn_reveal.clicked.connect(self.reveal_all)

        self.btn_reset = QPushButton("🔄  Làm lại")
        self.btn_reset.clicked.connect(self._reset_inputs)

        for b in [self.btn_check, self.btn_hint, self.btn_reveal, self.btn_reset]:
            b.setMinimumHeight(36)
            btn_row.addWidget(b)
        root.addLayout(btn_row)

        # Nav prev/next
        nav_row = QHBoxLayout()
        self.btn_prev_panel = QPushButton("⏮  Đoạn trước")
        self.btn_next_panel = QPushButton("⏭  Đoạn tiếp (Shift+Tab)")
        self.btn_prev_panel.clicked.connect(self.request_prev_passage)
        self.btn_next_panel.clicked.connect(self.request_next_passage)
        for b in [self.btn_prev_panel, self.btn_next_panel]:
            b.setMinimumHeight(34)
            b.setStyleSheet("background:#2a2a50; color:#c0c0ff; border:none; border-radius:6px; font-weight:bold;")
            nav_row.addWidget(b)
        root.addLayout(nav_row)

        # Shift+Tab shortcut → next passage
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Shift+Tab"), self, self.request_next_passage.emit)

        # Result label (ẩn ban đầu)
        self.lbl_result = QLabel("")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setStyleSheet("font-size:14px; padding:8px; border-radius:7px;")
        self.lbl_result.hide()
        root.addWidget(self.lbl_result)

    def _stat_badge(self, label, value, bg):
        f = QFrame()
        f.setStyleSheet(f"background:{bg}; border-radius:7px; padding:1px 6px;")
        v = QVBoxLayout(f)
        v.setSpacing(2)
        v.setContentsMargins(8, 4, 8, 4)
        lbl_val = QLabel(value)
        lbl_val.setObjectName(f"stat_val_{label}")
        lbl_val.setStyleSheet("font-size:18px; font-weight:bold; color:#e0e0ff;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet("font-size:10px; color:#9090c0;")
        lbl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_val)
        v.addWidget(lbl_lbl)
        f.lbl_val = lbl_val
        return f

    def _update_stat(self, badge, value):
        badge.lbl_val.setText(str(value))

    # ── Tokenize ──────────────────────────────────────────────────────────────
    @staticmethod
    def _tokenize(text):
        """Tách text thành list token: (text, is_word)"""
        tokens = []
        pattern = re.compile(
            r'(\s+|[,\.!?;:\"\'()\[\]{}\-–—]|[^\s,\.!?;:\"\'()\[\]{}\-–—]+)'
        )
        for m in pattern.finditer(text):
            t = m.group(0)
            is_word = bool(re.match(r'[^\s,\.!?;:\"\'()\[\]{}\-–—]', t))
            tokens.append((t, is_word))
        return tokens

    @staticmethod
    def _is_important(word):
        w = word.lower()
        w_clean = re.sub(r'[^\w\s]', '', w, flags=re.UNICODE).strip()
        return (
            len(w_clean) >= 2
            and w_clean not in STOPWORDS
            and w not in STOPWORDS
            and not w.isdigit()
        )

    # ── Load text ─────────────────────────────────────────────────────────────
    def load_text(self, text: str, level: int):
        self._checked = False
        self._text = text
        self._level = level
        self._blanks = []
        self.lbl_result.hide()
        self.lbl_result.setStyleSheet("background:transparent;")
        self._update_stat(self.lbl_correct, "0")
        self._update_stat(self.lbl_wrong,   "0")
        self._update_stat(self.lbl_pct,     "—")

        while self.passage_layout.count() > 1:
            item = self.passage_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cfg = LEVEL_CONFIG.get(level, LEVEL_CONFIG[30])
        tokens = PracticePanel._tokenize(text)

        indexed = [(t, iw, i) for i, (t, iw) in enumerate(tokens)]
        important = [i for i, (t, iw) in enumerate(tokens) if iw and PracticePanel._is_important(t)]

        num_hide = max(1, round(len(important) * cfg["pct"]))
        hide_set = set(random.sample(important, min(num_hide, len(important))))
        self._update_stat(self.lbl_total, len(hide_set))

        sentences, current = [], []
        enders = {'.','!','?','。','！','？'}
        for tok, is_word, gidx in indexed:
            current.append((tok, is_word, gidx))
            if tok.strip() in enders and current:
                sentences.append(current)
                current = []
        if current:
            sentences.append(current)

        for sent in sentences:
            row = FlowWidget(sent, hide_set, cfg["hint"], self)
            for inp, ans, orig in row.blanks:
                inp.request_check_answers.connect(self._handle_enter)
                inp.request_next_passage.connect(self.request_next_passage)
            self._blanks.extend(row.blanks)
            self.passage_layout.insertWidget(self.passage_layout.count() - 1, row)

        for i in range(len(self._blanks) - 1):
            QWidget.setTabOrder(self._blanks[i][0], self._blanks[i+1][0])
        if self._blanks:
            self._blanks[0][0].setFocus()
            self._blanks[-1][0].is_last_blank = True

    def _handle_enter(self):
        if self._checked:
            self._reset_inputs()
        else:
            self.check_answers()

    # ── Check answers ─────────────────────────────────────────────────────────
    def check_answers(self):
        correct = wrong = 0
        for inp, answer, original in self._blanks:
            if inp.isReadOnly():
                if "0d3a1a" in inp.styleSheet() or "5cff8c" in inp.styleSheet():
                    correct += 1
                else:
                    wrong += 1
                continue
            user = inp.text().strip().lower()
            if not user:
                inp.setStyleSheet(
                    "background:#3a1a1a; border-bottom: 2px solid #ff4040;"
                    "color:#ff8080; border-radius:3px;"
                )
                wrong += 1
                continue
            ok = self._normalize(user) == self._normalize(answer)
            if ok:
                inp.setStyleSheet(
                    "background:#0d3a1a; border-bottom: 2px solid #5cff8c;"
                    "color:#5cff8c; border-radius:3px;"
                )
                inp.setReadOnly(True)
                correct += 1
            else:
                inp.setStyleSheet(
                    "background:#3a1a1a; border-bottom: 2px solid #ff4040;"
                    "color:#ff8080; border-radius:3px;"
                )
                wrong += 1

        total = len(self._blanks)
        pct = round(correct / total * 100) if total else 0
        self._update_stat(self.lbl_correct, correct)
        self._update_stat(self.lbl_wrong, wrong)
        self._update_stat(self.lbl_pct, f"{pct}%")

        if pct == 100:
            self.lbl_result.setText("🎉 Xuất sắc! Bạn nhớ đúng tất cả!")
            self.lbl_result.setStyleSheet(
                "font-size:14px; padding:8px; border-radius:7px;"
                "background:#0d3a1a; color:#5cff8c;"
            )
        elif pct >= 60:
            self.lbl_result.setText(f"👍 Khá tốt! {correct}/{total} từ đúng. Xem lại từ sai nhé.")
            self.lbl_result.setStyleSheet(
                "font-size:14px; padding:8px; border-radius:7px;"
                "background:#3a3000; color:#ffc040;"
            )
        else:
            self.lbl_result.setText(f"📖 Cần ôn thêm. {correct}/{total} từ đúng. Thử lại!")
            self.lbl_result.setStyleSheet(
                "font-size:14px; padding:8px; border-radius:7px;"
                "background:#3a1a1a; color:#ff8080;"
            )
        self.lbl_result.show()
        self.score_updated.emit(correct, total)
        self._checked = True

    def show_all_hints(self, *args):
        for inp, answer, original in self._blanks:
            if not inp.isReadOnly() and not inp.text().strip():
                inp.setPlaceholderText(original[0] + "_" * max(1, len(original) - 1))

    def reveal_all(self, *args):
        for inp, answer, original in self._blanks:
            if not inp.isReadOnly():
                inp.setText(original)
                inp.setStyleSheet(
                    "background:#1a1a50; border-bottom: 2px solid #7c7cff;"
                    "color:#a0a0ff; border-radius:3px;"
                )
                inp.setReadOnly(True)

    def _reset_inputs(self):
        if self._text:
            self.load_text(self._text, self._level)

    @staticmethod
    def _normalize(s):
        import unicodedata
        return unicodedata.normalize("NFC", s.strip().lower())


class BlankInput(QLineEdit):
    request_next_passage = Signal()
    request_check_answers = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_last_blank = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            # Space → sang ô tiếp theo
            if not self.is_last_blank:
                super().focusNextPrevChild(True)
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.request_check_answers.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


# ─── Widget hiển thị 1 câu theo kiểu flow (wrap) ─────────────────────────────
class FlowWidget(QWidget):
    """Hiển thị 1 câu: từ thường + QLineEdit cho từ ẩn, tự wrap"""

    def __init__(self, tokens_with_idx, hide_set, show_hint, parent=None):
        super().__init__(parent)
        layout = FlowLayout(self, margin=2, spacing=4)
        self.blanks = []

        for tok, is_word, global_idx in tokens_with_idx:
            if is_word and global_idx in hide_set:
                inp = BlankInput()
                inp.setFixedHeight(36)
                font = QFont("Segoe UI", 11)
                inp.setFont(font)
                fm = QFontMetrics(font)
                # Đo chính xác theo font + padding QLineEdit (chuẩn từ topic_recall.py)
                w = max(50, fm.horizontalAdvance(tok) + 32)
                inp.setFixedWidth(min(w, 250))
                inp.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
                if show_hint:
                    inp.setPlaceholderText(tok[0] + "·" * max(1, len(tok) - 1))
                inp.setStyleSheet(
                    "background:transparent; border:none;"
                    "border-bottom:2px solid #7c7cff;"
                    "color:#c0c0ff; padding-bottom:3px; padding-top:1px; border-radius:3px;"
                )
                layout.addWidget(inp)
                self.blanks.append((inp, tok.lower(), tok))
            else:
                lbl = QLabel(tok)
                lbl.setFixedHeight(36)
                lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                lbl.setFont(QFont("Segoe UI", 11))
                lbl.setStyleSheet("color:#d8d8f0; background:transparent;")
                layout.addWidget(lbl)


# ─── Main RecallWidget ────────────────────────────────────────────────────────
class RecallWidget(QWidget):
    def __init__(self, topic_bar, parent=None):
        super().__init__(parent)
        self.topic_bar = topic_bar
        self._current_item: VanBanLuyenNho | None = None
        self._build_ui()
        self._load_list()
        self.topic_bar.selection_changed.connect(self._load_list)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: danh sách đoạn văn ─────────────────────────────────────────
        self.left_widget = QWidget()
        self.left_widget.setMinimumWidth(240)
        self.left_widget.setMaximumWidth(320)
        lv = QVBoxLayout(self.left_widget)
        lv.setSpacing(8)
        lv.setContentsMargins(10, 10, 10, 10)

        lbl_list = QLabel("📝  Đoạn văn")
        lbl_list.setObjectName("h2")
        lv.addWidget(lbl_list)

        # Action buttons — bỏ nút Sửa, thêm nút Thêm hàng loạt
        btn_row = QHBoxLayout()
        self.btn_add      = QPushButton("➕ Thêm")
        self.btn_bulk_add = QPushButton("📋 Hàng loạt")
        self.btn_del      = QPushButton("🗑️ Xóa")
        self.btn_del.setObjectName("dangerBtn")
        self.btn_add.setToolTip("Thêm một đoạn văn mới")
        self.btn_bulk_add.setToolTip("Thêm nhiều đoạn văn cùng lúc")
        self.btn_del.setToolTip("Xóa đoạn văn đang chọn")
        for b in [self.btn_add, self.btn_bulk_add, self.btn_del]:
            b.setMinimumHeight(32)
            btn_row.addWidget(b)
        lv.addLayout(btn_row)

        # Ghi chú double-click
        lbl_hint = QLabel("💡 Nháy đúp để sửa")
        lbl_hint.setStyleSheet("color:#5050a0; font-size:10px; font-style:italic;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.addWidget(lbl_hint)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background:#12122a; border:1px solid #2a2a4a; border-radius:8px; }"
            "QListWidget::item { padding:10px 8px; border-bottom:1px solid #1e1e3a; }"
            "QListWidget::item:selected { background:#1e2050; color:#7c7cff; }"
            "QListWidget::item:hover { background:#1a1a35; }"
        )
        lv.addWidget(self.list_widget, 1)

        self.lbl_item_stats = QLabel("")
        self.lbl_item_stats.setStyleSheet("color:#6060a0; font-size:11px;")
        self.lbl_item_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.addWidget(self.lbl_item_stats)

        splitter.addWidget(self.left_widget)

        # ── RIGHT: luyện tập ──────────────────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setSpacing(8)
        rv.setContentsMargins(10, 10, 10, 10)

        header_row = QHBoxLayout()
        
        self.btn_toggle_list = QPushButton("☰")
        self.btn_toggle_list.setFixedSize(32, 32)
        self.btn_toggle_list.setToolTip("Ẩn/Hiện danh sách")
        self.btn_toggle_list.clicked.connect(self._toggle_list)
        header_row.addWidget(self.btn_toggle_list)

        self.lbl_title = QLabel("Chọn đoạn văn để bắt đầu luyện tập")
        self.lbl_title.setObjectName("h2")
        header_row.addWidget(self.lbl_title, 1)

        lbl_level = QLabel("Cấp độ:")
        lbl_level.setStyleSheet("color:#9090c0;")
        header_row.addWidget(lbl_level)

        self.cb_level = QComboBox()
        for k, v in LEVEL_CONFIG.items():
            self.cb_level.addItem(v["label"], k)
        self.cb_level.setMinimumWidth(160)
        self.cb_level.setMinimumHeight(32)
        self.cb_level.currentIndexChanged.connect(self._on_level_changed)
        header_row.addWidget(self.cb_level)

        self.btn_start = QPushButton("▶  Bắt đầu")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumHeight(36)
        self.btn_start.setMinimumWidth(120)
        self.btn_start.clicked.connect(self._start_practice)
        header_row.addWidget(self.btn_start)

        rv.addLayout(header_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#1e1e3a; max-height:1px;")
        rv.addWidget(sep)

        self.practice_panel = PracticePanel()
        self.practice_panel.score_updated.connect(self._on_score_updated)
        self.practice_panel.request_next_passage.connect(self._next_passage)
        self.practice_panel.request_prev_passage.connect(self._prev_passage)
        rv.addWidget(self.practice_panel, 1)

        splitter.addWidget(right)
        splitter.setSizes([270, 700])
        root.addWidget(splitter)

        # Signals
        self.btn_add.clicked.connect(self._add_item)
        self.btn_bulk_add.clicked.connect(self._bulk_add_items)
        self.btn_del.clicked.connect(self._del_item)
        self.list_widget.currentRowChanged.connect(self._on_select)
        # Double-click để sửa (thay nút Sửa)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click_edit)

    def _toggle_list(self):
        self.left_widget.setVisible(not self.left_widget.isVisible())

    def save_state(self):
        import json
        from PySide6.QtCore import QSettings
        s = QSettings("HocTap", "HocTapApp")
        state = {
            "chu_de_id": getattr(self.topic_bar, "get_chu_de_id", lambda: None)(),
            "chuong_id": getattr(self.topic_bar, "get_chuong_id", lambda: None)(),
            "bai_id": getattr(self.topic_bar, "get_bai_id", lambda: None)(),
            "item_id": self._current_item.id if self._current_item else None,
            "level": self.cb_level.currentData(),
        }
        s.setValue("recall_state/last", json.dumps(state, ensure_ascii=False))
        s.sync()

    def restore_state(self):
        import json
        from PySide6.QtCore import QSettings
        s = QSettings("HocTap", "HocTapApp")
        raw = s.value("recall_state/last")
        if not raw:
            return

        try:
            state = json.loads(raw)
        except Exception:
            return

        saved_bai = state.get("bai_id")
        saved_ch = state.get("chuong_id")
        saved_cd = state.get("chu_de_id")
        saved_item = state.get("item_id")
        saved_level = state.get("level")

        if saved_bai or saved_ch or saved_cd:
            try:
                self.topic_bar.set_selection(saved_cd, saved_ch, saved_bai)
            except Exception:
                pass
        
        if saved_level:
            idx = self.cb_level.findData(saved_level)
            if idx >= 0:
                self.cb_level.setCurrentIndex(idx)
        
        if saved_item:
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) == saved_item:
                    self.list_widget.setCurrentRow(i)
                    self._start_practice()
                    break

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _load_list(self, *args):
        cd = getattr(self.topic_bar, "get_chu_de_id", lambda: 0)()
        ch = getattr(self.topic_bar, "get_chuong_id", lambda: 0)()
        bai_id = self.topic_bar.get_bai_id()
        # Nhớ ID đang chọn để restore sau khi reload
        selected_id = None
        if self.list_widget.currentRow() >= 0:
            cur = self.list_widget.currentItem()
            if cur:
                selected_id = cur.data(Qt.ItemDataRole.UserRole)

        self.list_widget.clear()
        with get_session() as sess:
            q = sess.query(VanBanLuyenNho)
            if bai_id:
                q = q.filter(VanBanLuyenNho.bai_id == bai_id)
            elif ch:
                ids = [b.id for b in sess.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter(VanBanLuyenNho.bai_id.in_(ids))
            elif cd:
                cids = [c.id for c in sess.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in sess.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter(VanBanLuyenNho.bai_id.in_(bids))
            
            # ← FIX: .asc() để cái thêm trước ở trên, thêm sau ở dưới
            items = q.order_by(VanBanLuyenNho.tao_luc.asc()).all()
            for item in items:
                li = QListWidgetItem()
                li.setText(item.ten)
                li.setData(Qt.ItemDataRole.UserRole, item.id)
                self.list_widget.addItem(li)

        # Restore selection
        if selected_id is not None:
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) == selected_id:
                    self.list_widget.setCurrentRow(i)
                    break

        if self.list_widget.currentRow() < 0 and self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self._start_practice()

        if self.list_widget.currentRow() < 0:
            self._current_item = None
            self.lbl_title.setText("Chọn đoạn văn để bắt đầu")
        self.lbl_item_stats.setText(f"{self.list_widget.count()} đoạn văn")

    def _add_item(self):
        bai_id = self.topic_bar.get_bai_id()
        dlg = VanBanDialog(bai_id=bai_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["noi_dung"]:
                QMessageBox.warning(self, "Thiếu nội dung", "Vui lòng nhập nội dung đoạn văn.")
                return
            with get_session() as sess:
                item = VanBanLuyenNho(
                    ten=data["ten"],
                    noi_dung=data["noi_dung"],
                    bai_id=bai_id or None,
                )
                sess.add(item)
                sess.commit()
            self._load_list()
            # Chọn item vừa thêm (cuối danh sách)
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _bulk_add_items(self):
        """Thêm hàng loạt nhiều đoạn văn."""
        bai_id = self.topic_bar.get_bai_id()
        dlg = BulkAddDialog(bai_id=bai_id, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        items_to_add = dlg.get_items()
        if not items_to_add:
            return

        added = 0
        with get_session() as sess:
            for data in items_to_add:
                if not data["noi_dung"].strip():
                    continue
                item = VanBanLuyenNho(
                    ten=data["ten"],
                    noi_dung=data["noi_dung"],
                    bai_id=bai_id or None,
                )
                sess.add(item)
                added += 1
            sess.commit()

        self._load_list()
        # Cuộn xuống cuối để thấy các mục vừa thêm
        self.list_widget.scrollToBottom()
        QMessageBox.information(
            self, "Thêm thành công",
            f"Đã thêm {added} đoạn văn vào danh sách."
        )

    def _on_double_click_edit(self, list_item: QListWidgetItem):
        """Nháy đúp vào tên đoạn văn → mở dialog sửa."""
        item_id = list_item.data(Qt.ItemDataRole.UserRole)
        with get_session() as sess:
            db_item = sess.get(VanBanLuyenNho, item_id)
            if not db_item:
                return
            dlg = VanBanDialog(item=db_item, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                db_item.ten = data["ten"]
                db_item.noi_dung = data["noi_dung"]
                sess.commit()
                # Cập nhật tên trong list ngay lập tức
                list_item.setText(data["ten"])
                # Nếu đang luyện đoạn này → cập nhật title
                if self._current_item and self._current_item.id == item_id:
                    self._current_item = sess.get(VanBanLuyenNho, item_id)
                    self.lbl_title.setText(data["ten"])

    def _del_item(self):
        item = self._get_selected_db_item()
        if not item:
            return
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f'Xóa đoạn văn "{item.ten}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            with get_session() as sess:
                db_item = sess.get(VanBanLuyenNho, item.id)
                sess.delete(db_item)
                sess.commit()
            self._load_list()

    def _get_selected_db_item(self):
        row = self.list_widget.currentRow()
        if row < 0:
            QMessageBox.information(self, "Chưa chọn", "Vui lòng chọn một đoạn văn.")
            return None
        item_id = self.list_widget.item(row).data(Qt.ItemDataRole.UserRole)
        with get_session() as sess:
            return sess.get(VanBanLuyenNho, item_id)

    def _on_select(self, row):
        if row < 0:
            return
        item_id = self.list_widget.item(row).data(Qt.ItemDataRole.UserRole)
        with get_session() as sess:
            item = sess.get(VanBanLuyenNho, item_id)
            if item:
                self._current_item = item
                self.lbl_title.setText(item.ten)
                stats = f"Đã luyện: {item.luyen_lan} lần  •  Điểm cao: {item.diem_cao}%"
                self.lbl_item_stats.setText(stats)
        self._start_practice()

    def _on_level_changed(self):
        if self._current_item:
            self._start_practice()

    def _start_practice(self):
        if not self._current_item:
            QMessageBox.information(self, "Chưa chọn", "Vui lòng chọn đoạn văn từ danh sách.")
            return
        level = self.cb_level.currentData()
        with get_session() as sess:
            item = sess.get(VanBanLuyenNho, self._current_item.id)
            text = item.noi_dung if item else ""
        if not text.strip():
            QMessageBox.warning(self, "Rỗng", "Đoạn văn không có nội dung.")
            return
        self.practice_panel.load_text(text, level)
        with get_session() as sess:
            item = sess.get(VanBanLuyenNho, self._current_item.id)
            item.luyen_lan = (item.luyen_lan or 0) + 1
            sess.commit()

    def _next_passage(self):
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            self.list_widget.setCurrentRow(row + 1)
            self._start_practice()
        else:
            QMessageBox.information(self, "Hết", "Đã đến đoạn văn cuối cùng trong danh sách.")

    def _prev_passage(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self.list_widget.setCurrentRow(row - 1)
            self._start_practice()

    def _on_score_updated(self, correct, total):
        if total == 0 or not self._current_item:
            return
        pct = round(correct / total * 100)
        with get_session() as sess:
            item = sess.get(VanBanLuyenNho, self._current_item.id)
            if pct > (item.diem_cao or 0):
                item.diem_cao = pct
                sess.commit()
        self.lbl_item_stats.setText(
            f"Đã luyện: {self._current_item.luyen_lan} lần  •  Điểm cao: {pct}%"
        )
