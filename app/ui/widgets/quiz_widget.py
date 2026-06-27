"""
app/ui/widgets/quiz_widget.py — Kiểm tra trắc nghiệm A/B/C/D
"""
import json
import random
import re
import unicodedata
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QFrame,
    QMessageBox, QDialog, QFormLayout, QLineEdit,
    QTextEdit, QDialogButtonBox, QComboBox, QGroupBox,
    QScrollArea, QStyle, QStyleOptionButton, QSizePolicy,
    QInputDialog, QFileDialog, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QRect, QSize, QTimer, QSettings
from PySide6.QtGui import QPainter, QKeySequence, QShortcut, QPixmap

from app.data.database import get_session, CauHoi, Bai, Chuong, ChuDe
from app.ui.styles import DIALOG_STYLE


QUESTION_NUMBER_RE = re.compile(r"^\s*(?:Câu\s*)?\d+\s*[\.\):\-–—]\s*", re.IGNORECASE)
OPTION_LABEL_RE = re.compile(r"(?im)(?:^|\s{2,})\s*(\*)?\s*([ABCDE])\s*[\.\):,/]+\s*")
ANSWER_LINE_RE = re.compile(
    r"^\s*[-–—•]*\s*(?:đáp\s*án|dap\s*an|answer)\s*[:：]\s*([ABCDE])(?:\s*\)?\s*[\.\):,/]?)?(?:\s+.*)?$",
    re.IGNORECASE,
)
QUESTION_BLOCK_START_RE = re.compile(
    r"(?im)^\s*(?:Câu\s*)?\d+\s*[\.\):\-–—]\s*\S+"
)
ANSWER_KEY_TOKEN_RE = re.compile(
    r"(?i)(?:\bcâu\s*)?(\d+)\s*(?:[\.\):,\-/–—]\s*)?"
    r"(?:đáp\s*án|dap\s*an|answer)?\s*[:：]?\s*([ABCDE])\b"
)
ANSWER_REFERENCE_CONTEXT_RE = re.compile(r"\b(?:y|dap\s*an|phuong\s*an)\b", re.IGNORECASE)
ANSWER_REFERENCE_LABEL_RE = re.compile(r"(?<![a-z0-9])([abcde])(?=\s*(?:[,.;:]|\bva\b|$))", re.IGNORECASE)


def _clean_multiline_text(text: str) -> str:
    return " ".join(line.strip() for line in text.strip().splitlines() if line.strip())


def _normalize_answer_reference_text(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return normalized.lower()


def _option_references_answer_labels(text: str) -> bool:
    normalized = _normalize_answer_reference_text(text).strip()
    
    exact_matches = [
        "tat ca", "ca hai", "ca 2", "ca ba", "ca 3", "deu dung", "deu sai",
        "ca a", "ca b", "ca c", "ca a va b", "ca a, b", "khong co", "khong co y nao"
    ]
    if normalized in exact_matches:
        return True
        
    collective_phrases = [
        "tat ca deu", "tat ca cac", "ca hai deu", "ca 2 deu", "ca ba deu", "ca 3 deu",
        "y tren", "cau tren", "dap an tren", "phuong an tren",
        "all of the above", "none of the above", "both a and b", "ca a va b", "ca a, b",
        "phuong an con lai", "dap an con lai", "cac y con lai", "cac dap an con lai",
        "cac phuong an khac"
    ]
    if any(phrase in normalized for phrase in collective_phrases):
        return True
        
    if re.search(r'\b([abcde])\s*(?:va|hay|hoac|and|or|,|&|\+|-)\s*([abcde])\b', normalized):
        return True
        
    if re.search(r'\b(?:dap an|phuong an|y|cau)\s+([abcde])\b', normalized):
        return True
        
    if re.search(r'\b([abcde])\s+(?:dung|sai)\b', normalized):
        return True
        
    return False


def _strip_question_number(text: str) -> str:
    return QUESTION_NUMBER_RE.sub("", text, count=1).strip()


def _extract_answer_line(text: str) -> tuple[str, str | None]:
    lines = (text or "").splitlines()
    last_line_index = None
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].strip():
            last_line_index = index
            break

    if last_line_index is None:
        return text, None

    match = ANSWER_LINE_RE.match(lines[last_line_index])
    if not match:
        return text, None

    answer = match.group(1).upper()
    cleaned_lines = lines[:last_line_index] + lines[last_line_index + 1:]
    return "\n".join(cleaned_lines).strip(), answer


def _numbered_question_text(index: int, text: str) -> str:
    content = _clean_multiline_text(_strip_question_number(text or ""))
    if content:
        return f"Câu {index + 1}. {content}"
    return f"Câu {index + 1}."


def parse_question_block(raw_text: str) -> dict | None:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None

    raw_text, parsed_answer = _extract_answer_line(raw_text)

    matches = list(OPTION_LABEL_RE.finditer(raw_text))
    option_matches = {}
    starred_answer = None
    for match in matches:
        label = match.group(2).upper()
        if match.group(1) and starred_answer is None:
            starred_answer = label
        option_matches.setdefault(label, match)

    labels = ["A", "B", "C", "D", "E"]
    if len(option_matches) < 2:
        return None

    ordered_matches = sorted(option_matches.items(), key=lambda item: item[1].start())

    question_text = _clean_multiline_text(_strip_question_number(raw_text[:ordered_matches[0][1].start()]))
    if not question_text:
        return None

    options = {}
    original_keys = [item[0] for item in ordered_matches]
    for index, (label, match) in enumerate(ordered_matches):
        start = match.end()
        end = ordered_matches[index + 1][1].start() if index + 1 < len(ordered_matches) else len(raw_text)
        options[labels[index]] = _clean_multiline_text(raw_text[start:end])

    for label in labels:
        options.setdefault(label, "")

    mapped_dap_an = None
    target_answer = starred_answer or parsed_answer
    if target_answer and target_answer in original_keys:
        mapped_dap_an = labels[original_keys.index(target_answer)]

    return {
        "noi_dung": question_text,
        "lua_chon_a": options["A"],
        "lua_chon_b": options["B"],
        "lua_chon_c": options["C"],
        "lua_chon_d": options["D"],
        "lua_chon_e": options["E"],
        "dap_an": mapped_dap_an or "A",
    }


def parse_question_batch(raw_text: str) -> list[dict]:
    questions, _errors = check_question_batch(raw_text)
    return questions


def check_question_batch(raw_text: str) -> tuple[list[dict], list[str]]:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return [], ["Chưa có nội dung để kiểm tra."]

    questions = []
    errors = []
    starts = [match.start() for match in QUESTION_BLOCK_START_RE.finditer(raw_text)]
    if len(starts) > 1:
        starts.append(len(raw_text))
        for index in range(len(starts) - 1):
            block = raw_text[starts[index]:starts[index + 1]].strip()
            parsed = parse_question_block(block)
            if parsed:
                questions.append(parsed)
            elif block:
                preview = block.splitlines()[0].strip()[:90]
                errors.append(f"Block {index + 1}: không parse được ({preview})")
        return questions, errors

    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw_text) if block.strip()]
    for index, block in enumerate(blocks, 1):
        parsed = parse_question_block(block)
        if parsed:
            questions.append(parsed)
        else:
            preview = block.splitlines()[0].strip()[:90]
            errors.append(f"Block {index}: không parse được ({preview})")
    if questions:
        return questions, errors

    parsed = parse_question_block(raw_text)
    if parsed:
        return [parsed], []
    return [], errors or ["Không tìm thấy câu hỏi hợp lệ."]


def parse_answer_key(raw_text: str, question_count: int | None = None) -> tuple[dict[int, str], list[str]]:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return {}, ["Chưa có nội dung đáp án để kiểm tra."]

    answers = {}
    errors = []
    spans = []
    for match in ANSWER_KEY_TOKEN_RE.finditer(raw_text):
        number = int(match.group(1))
        answer = match.group(2).upper()
        spans.append(match.span())

        if question_count is not None and not 1 <= number <= question_count:
            errors.append(f"Câu {number}: vượt quá số câu hiện có ({question_count}).")
            continue
        if number in answers:
            errors.append(f"Câu {number}: bị lặp đáp án, giữ đáp án {answers[number]}.")
            continue
        answers[number] = answer

    if not answers:
        return {}, errors or ["Không tìm thấy đáp án dạng 1a, 2b, 3c..."]

    leftovers = []
    cursor = 0
    for start, end in spans:
        leftovers.append(raw_text[cursor:start])
        cursor = end
    leftovers.append(raw_text[cursor:])
    leftover_text = "".join(leftovers)
    leftover_text = re.sub(r"[\s,;|/\\\.\-–—:：()\[\]{}]+", "", leftover_text)
    if leftover_text:
        errors.append(f"Còn nội dung chưa parse được: {leftover_text[:80]}")

    return answers, errors


class WrappedOptionButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__("", parent)
        self._display_text = ""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setText(text)

    def setText(self, text: str):
        self._display_text = text
        super().setText("")
        self.updateGeometry()
        self.update()

    def text(self) -> str:
        return self._display_text

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        text_width = max(40, width - 32)
        rect = QRect(0, 0, text_width, 10000)
        text_rect = self.fontMetrics().boundingRect(
            rect,
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            self._display_text,
        )
        return max(50, text_rect.height() + 24)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), self.heightForWidth(max(hint.width(), 240)))

    def paintEvent(self, event):
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""

        painter = QPainter(self)
        self.style().drawControl(QStyle.ControlElement.CE_PushButton, option, painter, self)

        text_rect = self.rect().adjusted(16, 10, -16, -10)
        painter.setPen(option.palette.buttonText().color())
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
            self._display_text,
        )


class QuizDialog(QDialog):
    SAVE_AND_NEXT = 2

    def __init__(
        self,
        q: CauHoi = None,
        parent=None,
        allow_save_next: bool = False,
        question_number: int | None = None,
        question_total: int | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Thêm / Sửa Câu hỏi")
        self.setMinimumSize(520, 520)
        self.setStyleSheet(DIALOG_STYLE)
        self._is_parsing_question = False

        layout = QVBoxLayout(self)
        status_text = self._question_status_text(q is not None, question_number, question_total)
        self.lbl_status = QLabel(status_text)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color:#7c7cff;font-weight:bold;font-size:15px;padding:4px;")
        layout.addWidget(self.lbl_status)

        form = QFormLayout()

        self.inp_noidung = QTextEdit()
        self.inp_noidung.setPlaceholderText("Nội dung câu hỏi...")
        self.inp_noidung.setMinimumHeight(80)

        self.inp_a = QLineEdit(); self.inp_a.setPlaceholderText("Lựa chọn A")
        self.inp_b = QLineEdit(); self.inp_b.setPlaceholderText("Lựa chọn B")
        self.inp_c = QLineEdit(); self.inp_c.setPlaceholderText("Lựa chọn C")
        self.inp_d = QLineEdit(); self.inp_d.setPlaceholderText("Lựa chọn D")
        self.inp_e = QLineEdit(); self.inp_e.setPlaceholderText("Lựa chọn E")

        self.cb_dapan = QComboBox()
        for opt in ["A", "B", "C", "D", "E"]:
            self.cb_dapan.addItem(opt, opt)

        self.inp_hinhanh = QLineEdit()
        self.inp_hinhanh.setPlaceholderText("Đường dẫn hoặc URL ảnh (tùy chọn)...")
        btn_browse_img = QPushButton("Chọn ảnh")
        btn_browse_img.clicked.connect(self._browse_image)
        btn_download_img = QPushButton("Tải từ URL")
        btn_download_img.clicked.connect(self._download_image_from_url)
        btn_download_img.setToolTip("Tải ảnh từ URL đã nhập trong ô bên trái")
        hinh_anh_layout = QHBoxLayout()
        hinh_anh_layout.addWidget(self.inp_hinhanh)
        hinh_anh_layout.addWidget(btn_browse_img)
        hinh_anh_layout.addWidget(btn_download_img)

        self.inp_giaithich = QTextEdit()
        self.inp_giaithich.setPlaceholderText("Giải thích đáp án (tùy chọn)...")
        self.inp_giaithich.setMinimumHeight(60)

        self.inp_ghichu = QLineEdit()
        self.inp_ghichu.setPlaceholderText("Ghi chú cho câu hỏi này...")

        form.addRow("Câu hỏi:", self.inp_noidung)
        form.addRow("Hình ảnh:", hinh_anh_layout)
        form.addRow("A:", self.inp_a)
        form.addRow("B:", self.inp_b)
        form.addRow("C:", self.inp_c)
        form.addRow("D:", self.inp_d)
        form.addRow("E:", self.inp_e)
        form.addRow("Đáp án:", self.cb_dapan)
        form.addRow("Giải thích:", self.inp_giaithich)
        form.addRow("Ghi chú:", self.inp_ghichu)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        if allow_save_next:
            btn_save_next = btns.addButton("Lưu và tiếp", QDialogButtonBox.ButtonRole.ActionRole)
            btn_save_next.setObjectName("primaryBtn")
            btn_save_next.clicked.connect(lambda: self.done(self.SAVE_AND_NEXT))
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if q:
            self.inp_noidung.setPlainText(q.noi_dung)
            if hasattr(q, "hinh_anh"):
                self.inp_hinhanh.setText(q.hinh_anh)
            self.inp_a.setText(q.lua_chon_a)
            self.inp_b.setText(q.lua_chon_b)
            self.inp_c.setText(q.lua_chon_c)
            self.inp_d.setText(q.lua_chon_d)
            if hasattr(q, "lua_chon_e"):
                self.inp_e.setText(q.lua_chon_e)
            
            self._update_answer_choices()
            
            idx = self.cb_dapan.findData(q.dap_an)
            if idx >= 0:
                self.cb_dapan.setCurrentIndex(idx)
            self.inp_giaithich.setPlainText(q.giai_thich)
            self.inp_ghichu.setText(q.ghi_chu)
        else:
            self.inp_noidung.textChanged.connect(self._try_parse_question_text)
            self._update_answer_choices()

        self.inp_a.textChanged.connect(self._update_answer_choices)
        self.inp_b.textChanged.connect(self._update_answer_choices)
        self.inp_c.textChanged.connect(self._update_answer_choices)
        self.inp_d.textChanged.connect(self._update_answer_choices)
        self.inp_e.textChanged.connect(self._update_answer_choices)

    def _question_status_text(self, is_editing: bool, question_number: int | None, question_total: int | None) -> str:
        if not question_number:
            return "Đang sửa câu hỏi" if is_editing else "Đang thêm câu hỏi"

        prefix = "Đang sửa" if is_editing else "Đang thêm"
        if is_editing and question_total:
            return f"{prefix}: Câu {question_number} / {question_total}"
        return f"{prefix}: Câu {question_number}"

    def _try_parse_question_text(self):
        if self._is_parsing_question:
            return

        parsed = parse_question_block(self.inp_noidung.toPlainText())
        if not parsed:
            return

        self._is_parsing_question = True
        try:
            self.inp_noidung.setPlainText(parsed["noi_dung"])
            self.inp_a.setText(parsed["lua_chon_a"])
            self.inp_b.setText(parsed["lua_chon_b"])
            self.inp_c.setText(parsed["lua_chon_c"])
            self.inp_d.setText(parsed["lua_chon_d"])
            self.inp_e.setText(parsed.get("lua_chon_e", ""))
            
            self._update_answer_choices()
            
            if parsed.get("dap_an"):
                idx = self.cb_dapan.findData(parsed["dap_an"])
                if idx >= 0:
                    self.cb_dapan.setCurrentIndex(idx)
        finally:
            self._is_parsing_question = False

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            self.inp_hinhanh.setText(path)

    def _download_image_from_url(self):
        url = self.inp_hinhanh.text().strip()
        if not url.startswith("http"):
            url, ok = QInputDialog.getText(self, "Tải ảnh từ URL", "Nhập URL hình ảnh (bắt đầu bằng http/https):")
            if not ok or not url.strip().startswith("http"):
                return
            url = url.strip()
            
        import os
        import urllib.request
        from urllib.parse import urlparse
        import time

        try:
            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[1]
            if not ext:
                ext = ".jpg"
                
            # Đảm bảo thư mục media/images tồn tại
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            media_dir = os.path.join(base_dir, "media", "images")
            os.makedirs(media_dir, exist_ok=True)
            
            filename = f"dl_{int(time.time())}{ext}"
            filepath = os.path.normpath(os.path.join(media_dir, filename))
            
            # Giả lập User-Agent để tránh bị block 403
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
                out_file.write(response.read())
                
            self.inp_hinhanh.setText(filepath)
            QMessageBox.information(self, "Tải ảnh", "Đã tải ảnh thành công và lưu vào bộ nhớ cục bộ!")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi tải ảnh", f"Không thể tải ảnh từ URL:\n{e}")

    def _update_answer_choices(self):
        current_data = self.cb_dapan.currentData()
        self.cb_dapan.clear()
        
        # Luôn cho phép A và B
        self.cb_dapan.addItem("A", "A")
        self.cb_dapan.addItem("B", "B")
        
        # Cho phép C, D, E nếu có nhập liệu
        if self.inp_c.text().strip():
            self.cb_dapan.addItem("C", "C")
        if self.inp_d.text().strip():
            self.cb_dapan.addItem("D", "D")
        if self.inp_e.text().strip():
            self.cb_dapan.addItem("E", "E")
            
        idx = self.cb_dapan.findData(current_data)
        if idx >= 0:
            self.cb_dapan.setCurrentIndex(idx)
        else:
            self.cb_dapan.setCurrentIndex(0)

    def get_data(self):
        return {
            "noi_dung":   self.inp_noidung.toPlainText().strip(),
            "hinh_anh":   self.inp_hinhanh.text().strip(),
            "lua_chon_a": self.inp_a.text().strip(),
            "lua_chon_b": self.inp_b.text().strip(),
            "lua_chon_c": self.inp_c.text().strip(),
            "lua_chon_d": self.inp_d.text().strip(),
            "lua_chon_e": self.inp_e.text().strip(),
            "dap_an":     self.cb_dapan.currentData() or "A",
            "giai_thich": self.inp_giaithich.toPlainText().strip(),
            "ghi_chu":    self.inp_ghichu.text().strip(),
        }


class NoteDialog(QDialog):
    def __init__(self, note: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ghi chú câu hỏi")
        self.setMinimumSize(400, 250)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        self.inp = QTextEdit()
        self.inp.setPlainText(note)
        layout.addWidget(self.inp)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_note(self):
        return self.inp.toPlainText().strip()


class ExplanationDialog(QDialog):
    def __init__(self, explanation: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sửa giải thích" if explanation.strip() else "Thêm giải thích")
        self.setMinimumSize(520, 320)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        hint = QLabel("Nhập giải thích cho câu hỏi hiện tại.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.inp = QTextEdit()
        self.inp.setPlaceholderText("Giải thích vì sao đáp án đúng...")
        self.inp.setPlainText(explanation or "")
        layout.addWidget(self.inp, 1)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Lưu giải thích")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_explanation(self):
        return self.inp.toPlainText().strip()


class BatchQuizDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm hàng loạt câu hỏi")
        self.setMinimumSize(700, 520)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Dán nhiều câu hỏi trắc nghiệm. Mỗi câu có thể bắt đầu bằng 'Câu 1.' hoặc cách nhau bằng dòng trống. "
            "Hỗ trợ A/B/C/D ở nhiều định dạng và dòng cuối dạng 'Đáp án: A'."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.inp = QTextEdit()
        self.inp.setPlaceholderText(
            "Câu 1. Nội dung câu hỏi...\n"
            "A. lựa chọn A\n"
            "B. lựa chọn B\n"
            "C. lựa chọn C\n"
            "D. lựa chọn D\n"
            "Đáp án: A\n\n"
            "Câu 2. Nội dung câu hỏi khác...\n"
            "A/ lựa chọn A      B/ lựa chọn B\n"
            "C/ lựa chọn C      D/ lựa chọn D\n"
            "- Đáp án: b)."
        )
        layout.addWidget(self.inp, 1)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Thêm hàng loạt")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btn_check = btns.addButton("Check", QDialogButtonBox.ButtonRole.ActionRole)
        btn_check.clicked.connect(self._check_content)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_text(self):
        return self.inp.toPlainText().strip()

    def _check_content(self):
        questions, errors = check_question_batch(self.get_text())
        message = f"Sẽ tạo được {len(questions)} câu hỏi."
        if errors:
            shown_errors = "\n".join(errors[:10])
            extra = "" if len(errors) <= 10 else f"\n... và {len(errors) - 10} lỗi khác."
            message += f"\n\nCó {len(errors)} block lỗi:\n{shown_errors}{extra}"
            QMessageBox.warning(self, "Check thêm hàng loạt", message)
        else:
            QMessageBox.information(self, "Check thêm hàng loạt", message + "\n\nKhông phát hiện lỗi parse.")


class AnswerKeyDialog(QDialog):
    def __init__(self, question_count: int, parent=None):
        super().__init__(parent)
        self.question_count = question_count
        self.setWindowTitle("Cập nhật đáp án hàng loạt")
        self.setMinimumSize(560, 420)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        hint = QLabel(
            f"Dán danh sách đáp án theo số thứ tự câu đang hiển thị (1-{question_count}). "
            "Ví dụ: 1a 2b 3c 4a 5d. Có thể dùng dạng 1. A, 2) b, Câu 3: c."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.inp = QTextEdit()
        self.inp.setPlaceholderText("1a 2b 3c 4a 5d")
        layout.addWidget(self.inp, 1)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Cập nhật đáp án")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btn_check = btns.addButton("Check", QDialogButtonBox.ButtonRole.ActionRole)
        btn_check.clicked.connect(self._check_content)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_text(self):
        return self.inp.toPlainText().strip()

    def _check_content(self):
        answers, errors = parse_answer_key(self.get_text(), self.question_count)
        message = f"Parse được {len(answers)} đáp án / {self.question_count} câu."
        if answers:
            preview = ", ".join(f"{number}{answer}" for number, answer in sorted(answers.items())[:30])
            extra = "" if len(answers) <= 30 else f", ... và {len(answers) - 30} đáp án khác"
            message += f"\n\n{preview}{extra}"

        if errors:
            shown_errors = "\n".join(errors[:10])
            extra = "" if len(errors) <= 10 else f"\n... và {len(errors) - 10} lỗi khác."
            QMessageBox.warning(self, "Check đáp án hàng loạt", f"{message}\n\n{shown_errors}{extra}")
        else:
            QMessageBox.information(self, "Check đáp án hàng loạt", message + "\n\nKhông phát hiện lỗi parse.")


class QuizFinishDialog(QDialog):
    RETRY_ALL = 1
    RETRY_WRONG = 2

    def __init__(
        self,
        correct: int,
        total: int,
        wrong_count: int,
        retry_all_text: str = "Làm lại tất cả",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Hoàn thành lượt kiểm tra")
        self.setMinimumSize(380, 180)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)

        lbl_title = QLabel("Đã đến câu cuối cùng")
        lbl_title.setObjectName("h3")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        self.lbl_result = QLabel(f"Bạn đã làm đúng {correct} / {total} câu")
        self.lbl_result.setObjectName("accent")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setStyleSheet("color:#7c7cff;font-weight:bold;font-size:16px;padding:8px;")
        layout.addWidget(self.lbl_result)

        if wrong_count:
            detail = f"Có {wrong_count} câu sai/chưa đúng để làm lại."
        else:
            detail = "Không có câu sai/chưa đúng để làm lại."
        lbl_detail = QLabel(detail)
        lbl_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_detail)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.button(QDialogButtonBox.StandardButton.Close).setText("Đóng")
        btn_retry_all = btns.addButton(retry_all_text, QDialogButtonBox.ButtonRole.ActionRole)
        btn_retry_all.setObjectName("primaryBtn")
        btn_retry_wrong = btns.addButton("Làm lại câu sai", QDialogButtonBox.ButtonRole.ActionRole)
        btn_retry_wrong.setEnabled(wrong_count > 0)
        btn_retry_all.clicked.connect(lambda: self.done(self.RETRY_ALL))
        btn_retry_wrong.clicked.connect(lambda: self.done(self.RETRY_WRONG))
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)


class QuizWidget(QWidget):
    def __init__(self, topic_bar, parent=None):
        super().__init__(parent)
        self.topic_bar = topic_bar
        self._current_id = None
        self._all_questions = []
        self._test_questions = []
        self._questions  = []
        self._q_index    = 0
        self._answered   = False
        self._question_results = {}
        self._image_height = 300
        self._quiz_mode = "all"
        self._random_test_size = None
        self._answer_font_size = 14
        self._explanation_font_size = 13
        self._answers_shuffled_session = False
        self._build_ui()
        topic_bar.selection_changed.connect(self._refresh_list)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ─── LEFT: danh sách câu hỏi ────────────────────────────────
        left = QWidget()
        self.left_questions_panel = left
        lv = QVBoxLayout(left)
        lv.setSpacing(6)
        lv.setContentsMargins(8, 8, 4, 8)

        lv.addWidget(QLabel("📋 Danh sách Câu hỏi"))
        self.q_list = QListWidget()
        self.q_list.currentItemChanged.connect(self._on_q_selected)
        self.q_list.itemDoubleClicked.connect(lambda _: self._edit_q())
        lv.addWidget(self.q_list, 1)

        list_btns = QHBoxLayout()
        self.btn_add    = QPushButton("➕ Thêm")
        self.btn_bulk   = QPushButton("📥 Hàng loạt")
        self.btn_answer_key = QPushButton("✅ Đáp án")
        self.btn_delete = QPushButton("🗑 Xóa")
        self.btn_add.setObjectName("primaryBtn")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_answer_key.setToolTip("Parse và cập nhật đáp án hàng loạt theo thứ tự câu đang hiển thị")
        for b in [self.btn_add, self.btn_bulk, self.btn_answer_key, self.btn_delete]:
            b.setFixedHeight(28)
            list_btns.addWidget(b)
        lv.addLayout(list_btns)

        backup_btns = QHBoxLayout()
        self.btn_backup = QPushButton("💾 Backup")
        self.btn_restore = QPushButton("📂 Restore")
        self.btn_backup.setToolTip("Xuất các câu hỏi đang hiển thị ra file JSON")
        self.btn_restore.setToolTip("Nhập câu hỏi từ file JSON vào Bài đang chọn")
        for b in [self.btn_backup, self.btn_restore]:
            b.setFixedHeight(28)
            backup_btns.addWidget(b)
        lv.addLayout(backup_btns)
        self._edit_buttons = [self.btn_add, self.btn_bulk, self.btn_answer_key, self.btn_delete]
        self._edit_button_tooltips = {button: button.toolTip() for button in self._edit_buttons}

        splitter.addWidget(left)

        # ─── RIGHT: quiz display ────────────────────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setSpacing(12)
        rv.setContentsMargins(8, 12, 8, 12)

        # Header
        hdr = QHBoxLayout()
        self.lbl_q_progress = QLabel("0 / 0")
        self.lbl_q_progress.setObjectName("muted")
        hdr.addWidget(self.lbl_q_progress)
        self.lbl_score = QLabel("Đúng: 0 / 0 câu")
        self.lbl_score.setObjectName("accent")
        hdr.addWidget(self.lbl_score)
        hdr.addStretch()
        self.btn_toggle_list = QPushButton("📋 Ẩn DS")
        self.btn_toggle_list.setFixedHeight(30)
        self.btn_toggle_list.setToolTip("Ẩn/hiện danh sách câu hỏi")
        self.btn_toggle_list.clicked.connect(self._toggle_question_list)
        hdr.addWidget(self.btn_toggle_list)
        self.btn_test_all = QPushButton("📋 Test All")
        self.btn_test_all.setFixedHeight(30)
        self.btn_test_all.setToolTip("Test tất cả câu hỏi trong danh sách")
        self.btn_test_all.clicked.connect(self._start_test_all)
        hdr.addWidget(self.btn_test_all)
        self.btn_random_test = QPushButton("🎯 Test N")
        self.btn_random_test.setFixedHeight(30)
        self.btn_random_test.setToolTip("Tạo bài test ngẫu nhiên theo số câu nhập vào")
        self.btn_random_test.clicked.connect(self._create_random_test)
        hdr.addWidget(self.btn_random_test)
        self.btn_starred_test = QPushButton("⭐ Test Sao")
        self.btn_starred_test.setFixedHeight(30)
        self.btn_starred_test.setToolTip("Tạo bài test với các câu hỏi được đánh dấu sao")
        self.btn_starred_test.clicked.connect(self._create_starred_test)
        hdr.addWidget(self.btn_starred_test)
        self.btn_shuffle = QPushButton("🔀 Trộn")
        self.btn_shuffle.setFixedHeight(30)
        self.btn_shuffle.setToolTip("Chỉ trộn thứ tự câu hỏi, giữ nguyên A/B/C/D")
        self.btn_shuffle.clicked.connect(self._shuffle_questions)
        hdr.addWidget(self.btn_shuffle)
        self.btn_shuffle_answers = QPushButton("🎲 Trộn C+A-D")
        self.btn_shuffle_answers.setFixedHeight(30)
        self.btn_shuffle_answers.setToolTip("Trộn thứ tự câu hỏi và vị trí A/B/C/D tạm thời, không lưu vào database")
        self.btn_shuffle_answers.clicked.connect(self._shuffle_questions_and_answers)
        hdr.addWidget(self.btn_shuffle_answers)
        rv.addLayout(hdr)

        # Question
        self.lbl_question = QLabel("")
        self.lbl_question.setObjectName("quizQuestion")
        self.lbl_question.setWordWrap(True)
        self.lbl_question.setMinimumHeight(80)
        rv.addWidget(self.lbl_question)

        # Image Label
        self.lbl_image = QLabel("")
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.hide()
        rv.addWidget(self.lbl_image)

        # Option buttons
        self._option_btns = []
        for opt in ["A", "B", "C", "D", "E"]:
            btn = WrappedOptionButton(f"{opt}. ")
            btn.setObjectName("optionBtn")
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda _, o=opt: self._answer(o))
            rv.addWidget(btn)
            self._option_btns.append(btn)
        self.set_answer_font_size(self._answer_font_size)

        # Feedback
        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setObjectName("h3")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.hide()
        rv.addWidget(self.lbl_feedback)

        self.lbl_explain = QLabel("")
        self.lbl_explain.setObjectName("muted")
        self.lbl_explain.setWordWrap(True)
        self.lbl_explain.hide()
        rv.addWidget(self.lbl_explain)
        self.set_explanation_font_size(self._explanation_font_size)

        # Navigation
        nav = QHBoxLayout()
        self.btn_prev_q = QPushButton("◀ Trước")
        self.btn_explain = QPushButton("➕ Giải thích")
        self.btn_star = QPushButton("☆ Đánh dấu")
        self.btn_next_q = QPushButton("Tiếp ▶")
        self.btn_prev_q.setFixedHeight(36)
        self.btn_explain.setFixedHeight(36)
        self.btn_explain.setToolTip("Thêm hoặc sửa giải thích của câu hỏi hiện tại")
        self.btn_star.setFixedHeight(36)
        self.btn_star.setToolTip("Đánh dấu câu hỏi này (khó/quan trọng)")
        self.btn_next_q.setFixedHeight(36)
        self.btn_next_q.setToolTip("Sang câu tiếp theo  [Tab]")
        nav.addWidget(self.btn_prev_q)
        nav.addStretch()
        nav.addWidget(self.btn_explain)
        nav.addWidget(self.btn_star)
        nav.addWidget(self.btn_next_q)
        rv.addLayout(nav)
        rv.addStretch()

        right_scroll.setWidget(right)
        splitter.addWidget(right_scroll)
        splitter.setSizes([280, 600])

        # Connections
        self.btn_add.clicked.connect(self._add_q)
        self.btn_bulk.clicked.connect(self._add_bulk_q)
        self.btn_answer_key.clicked.connect(self._apply_answer_key)
        self.btn_delete.clicked.connect(self._delete_q)
        self.btn_backup.clicked.connect(self._backup_questions)
        self.btn_restore.clicked.connect(self._restore_questions)
        self.btn_prev_q.clicked.connect(self._prev_q)
        self.btn_explain.clicked.connect(self._edit_explanation)
        self.btn_star.clicked.connect(self._toggle_star)
        self.btn_next_q.clicked.connect(self._next_q)
        shortcut_next = QShortcut(QKeySequence("Tab"), self)
        shortcut_next.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut_next.activated.connect(self._next_q)

        self._refresh_list()

    def set_image_height(self, height: int):
        self._image_height = height
        if self._questions and len(self._questions) > self._q_index:
            self._show_question(self._q_index)

    def set_answer_font_size(self, size: int):
        self._answer_font_size = max(10, min(28, size))
        for btn in getattr(self, "_option_btns", []):
            font = btn.font()
            font.setPointSize(self._answer_font_size)
            btn.setFont(font)
            btn.setStyleSheet(f"font-size: {self._answer_font_size}px;")
            btn.updateGeometry()
            btn.update()

    def set_explanation_font_size(self, size: int):
        self._explanation_font_size = max(10, min(28, size))
        if hasattr(self, "lbl_explain"):
            self.lbl_explain.setStyleSheet(f"font-size: {self._explanation_font_size}px;")

    def _set_editing_locked(self, locked: bool):
        self._answers_shuffled_session = locked
        for button in self._edit_buttons:
            button.setEnabled(not locked)
        tooltip = "Đang trộn đáp án tạm thời: hãy tạo lại bài test hoặc bấm Trộn thường trước khi sửa dữ liệu."
        for button in self._edit_buttons:
            button.setToolTip(tooltip if locked else self._edit_button_tooltips.get(button, ""))
        self.q_list.setToolTip(tooltip if locked else "")

    def _warn_editing_locked(self):
        QMessageBox.information(
            self,
            "Đang trộn đáp án",
            "Các đáp án đang được trộn tạm thời. Bấm Trộn thường hoặc tạo lại bài test trước khi thêm/sửa/xóa câu hỏi.",
        )

    def _start_test_all(self):
        self._set_editing_locked(False)
        self._start_quiz(
            questions=self._all_questions,
            shuffle=False,
            update_source=True,
            mode="all",
        )

    def _refresh_list(self, reset_test=True, *args):
        if not isinstance(reset_test, bool):
            reset_test = True
        if reset_test:
            self._set_editing_locked(False)
            
        old_all_ids = set()
        if hasattr(self, '_all_questions'):
            old_all_ids = {q["id"] for q in self._all_questions}
            
        session = get_session()
        try:
            q = session.query(CauHoi)
            cd, ch, bai = (
                self.topic_bar.get_chu_de_id(),
                self.topic_bar.get_chuong_id(),
                self.topic_bar.get_bai_id(),
            )
            if bai:
                q = q.filter(CauHoi.bai_id == bai)
            elif ch:
                ids = [b.id for b in session.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter(CauHoi.bai_id.in_(ids))
            elif cd:
                cids = [c.id for c in session.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter(CauHoi.bai_id.in_(bids))
            questions = q.order_by(CauHoi.tao_luc).all()
            self._all_questions = [{
                "id": q.id, "noi_dung": q.noi_dung, "hinh_anh": q.hinh_anh,
                "a": q.lua_chon_a, "b": q.lua_chon_b,
                "c": q.lua_chon_c, "d": q.lua_chon_d, "e": q.lua_chon_e,
                "dap_an": q.dap_an, "giai_thich": q.giai_thich,
                "ghi_chu": q.ghi_chu,
                "danh_dau": q.danh_dau,
            } for q in questions]
            
            if reset_test:
                self._test_questions = list(self._all_questions)
                self._questions = list(self._test_questions)
                self._quiz_mode = "all"
                self._random_test_size = None
                self._question_results.clear()
                self._q_index = 0
            else:
                new_all_dict = {q["id"]: q for q in self._all_questions}
                # Cập nhật self._questions giữ nguyên thứ tự
                new_questions = []
                for q in self._questions:
                    if q["id"] in new_all_dict:
                        new_questions.append(new_all_dict[q["id"]])
                # Chỉ thêm câu hỏi mới vừa được tạo
                for q in self._all_questions:
                    if q["id"] not in old_all_ids:
                        new_questions.append(q)
                self._questions = new_questions
                
                new_test_questions = []
                for q in self._test_questions:
                    if q["id"] in new_all_dict:
                        new_test_questions.append(new_all_dict[q["id"]])
                for q in self._all_questions:
                    if q["id"] not in old_all_ids:
                        new_test_questions.append(q)
                self._test_questions = new_test_questions
                
                current_ids = {q["id"] for q in self._all_questions}
                self._question_results = {
                    qid: result for qid, result in self._question_results.items()
                    if qid in current_ids
                }
                
            if self._questions:
                self._q_index = min(getattr(self, '_q_index', 0), len(self._questions) - 1)
                self._q_index = max(0, self._q_index)
                self._rebuild_question_list(current_row=self._q_index)
                self._show_question(self._q_index)
            else:
                self._rebuild_question_list()
                self.lbl_question.setText("Chưa có câu hỏi nào")
                self.lbl_q_progress.setText("0 / 0")
                self.lbl_explain.hide()
                self.btn_explain.setEnabled(False)
                self.btn_explain.setText("➕ Giải thích")
            self._update_score_label()
        finally:
            session.close()

    def _rebuild_question_list(self, current_row=None):
        self.q_list.blockSignals(True)
        try:
            self.q_list.clear()
            if not self._questions:
                self._current_id = None
                return

            for i, q in enumerate(self._questions):
                title = _numbered_question_text(i, q["noi_dung"])
                preview = title[:70] + ("..." if len(title) > 70 else "")
                if q["id"] in self._question_results:
                    if self._question_results[q["id"]]:
                        preview = f"✅ {preview}"
                    else:
                        preview = f"❌ {preview}"
                if q.get("danh_dau"):
                    preview = f"⭐ {preview}"
                item = QListWidgetItem(preview)
                item.setData(Qt.ItemDataRole.UserRole, q["id"])
                self.q_list.addItem(item)

            if current_row is not None and 0 <= current_row < len(self._questions):
                self.q_list.setCurrentRow(current_row)
                self._current_id = self._questions[current_row]["id"]
                item = self.q_list.item(current_row)
                if item:
                    self.q_list.scrollToItem(item)
        finally:
            self.q_list.blockSignals(False)

    def _start_quiz(
        self,
        questions,
        shuffle=False,
        update_source=True,
        mode=None,
        random_test_size=None,
    ):
        if not questions:
            return

        self._set_editing_locked(False)
        if update_source:
            self._test_questions = list(questions)
        if mode is not None:
            self._quiz_mode = mode
            self._random_test_size = random_test_size if mode == "random_n" else None
        elif random_test_size is not None:
            self._random_test_size = random_test_size
        self._questions = list(questions)
        if shuffle:
            random.shuffle(self._questions)

        self._question_results = {}
        self._q_index = 0
        self._answered = False
        self._rebuild_question_list(current_row=0)
        self._show_question(0)
        self._update_score_label()

    def _select_question_row(self, row):
        if not self._questions:
            self._current_id = None
            return
        self.q_list.blockSignals(True)
        try:
            self.q_list.setCurrentRow(row)
            self._current_id = self._questions[row]["id"]
            item = self.q_list.item(row)
            if item:
                self.q_list.scrollToItem(item)
        finally:
            self.q_list.blockSignals(False)

    def _on_q_selected(self, item):
        if not item:
            return
        qid = item.data(Qt.ItemDataRole.UserRole)
        self._current_id = qid
        for i, q in enumerate(self._questions):
            if q["id"] == qid:
                self._q_index = i
                self._show_question(i)
                break

    def _show_question(self, index):
        if not self._questions or index < 0 or index >= len(self._questions):
            return
        q = self._questions[index]
        self._answered = q["id"] in self._question_results
        self.lbl_question.setText(f"❓ {_numbered_question_text(index, q['noi_dung'])}")
        
        # Display Image if exists
        hinh_anh = q.get("hinh_anh")
        if hinh_anh:
            pixmap = QPixmap(hinh_anh)
            if not pixmap.isNull():
                self.lbl_image.setPixmap(pixmap.scaledToHeight(self._image_height, Qt.TransformationMode.SmoothTransformation))
                self.lbl_image.show()
            else:
                self.lbl_image.hide()
        else:
            self.lbl_image.hide()
            
        opts = [q.get("a", ""), q.get("b", ""), q.get("c", ""), q.get("d", ""), q.get("e", "")]
        labels = ["A", "B", "C", "D", "E"]
        for i, (btn, opt) in enumerate(zip(self._option_btns, opts)):
            if not opt.strip():
                btn.hide()
                continue
            btn.show()
            btn.setText(f"{labels[i]}. {opt}")
            if self._answered:
                if labels[i] == q["dap_an"]:
                    btn.setProperty("state", "correct")
                else:
                    btn.setProperty("state", "")
                btn.setEnabled(False)
            else:
                btn.setProperty("state", "")
                btn.setEnabled(True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if self._answered:
            if self._question_results[q["id"]]:
                self.lbl_feedback.setText("✅ Đúng rồi!")
                self.lbl_feedback.setObjectName("success")
            else:
                self.lbl_feedback.setText(f"❌ Sai! Đáp án đúng là: {q['dap_an']}")
                self.lbl_feedback.setObjectName("danger")
            self.lbl_feedback.show()
            if q["giai_thich"]:
                self._set_explanation_visible(True)
        else:
            self.lbl_feedback.hide()
            self._set_explanation_visible(False)
        self.btn_explain.setEnabled(True)
        self._update_explanation_button()
        self.lbl_q_progress.setText(f"{index+1} / {len(self._questions)}")
        
        if q.get("danh_dau"):
            self.btn_star.setText("⭐ Đã đánh dấu")
            self.btn_star.setStyleSheet("color: #FFC107; font-weight: bold;")
        else:
            self.btn_star.setText("☆ Đánh dấu")
            self.btn_star.setStyleSheet("")

    def _current_explanation_text(self):
        if not self._questions or self._q_index < 0 or self._q_index >= len(self._questions):
            return ""
        return (self._questions[self._q_index].get("giai_thich") or "").strip()

    def _set_explanation_visible(self, visible: bool):
        if visible:
            explanation = self._current_explanation_text()
            text = f"💡 {explanation}" if explanation else "💡 Chưa có giải thích cho câu hỏi này."
            self.lbl_explain.setText(text)
            self.lbl_explain.show()
        else:
            self.lbl_explain.hide()

    def _update_explanation_button(self):
        self.btn_explain.setText("✏️ Giải thích" if self._current_explanation_text() else "➕ Giải thích")

    def _edit_explanation(self):
        if not self._questions or self._q_index < 0 or self._q_index >= len(self._questions):
            return

        qid = self._questions[self._q_index]["id"]
        dlg = ExplanationDialog(self._current_explanation_text(), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        explanation = dlg.get_explanation()
        session = get_session()
        try:
            q = session.get(CauHoi, qid)
            if not q:
                QMessageBox.warning(self, "Giải thích", "Không tìm thấy câu hỏi để cập nhật.")
                return
            q.giai_thich = explanation
            session.commit()
        finally:
            session.close()

        for collection in (self._all_questions, self._test_questions, self._questions):
            for item in collection:
                if item["id"] == qid:
                    item["giai_thich"] = explanation

        self._update_explanation_button()
        self._set_explanation_visible(bool(explanation))

    def _answer(self, chosen: str):
        if self._answered or not self._questions:
            return
        self._answered = True
        q = self._questions[self._q_index]
        correct = q["dap_an"]
        labels = ["A", "B", "C", "D", "E"]

        for i, btn in enumerate(self._option_btns):
            lbl = labels[i]
            if lbl == correct:
                btn.setProperty("state", "correct")
            elif lbl == chosen and chosen != correct:
                btn.setProperty("state", "wrong")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.setEnabled(False)

        is_correct = chosen == correct
        self._question_results[q["id"]] = is_correct

        if is_correct:
            self.lbl_feedback.setText("✅ Đúng rồi!")
            self.lbl_feedback.setObjectName("success")
        else:
            self.lbl_feedback.setText(f"❌ Sai! Đáp án đúng là: {correct}")
            self.lbl_feedback.setObjectName("danger")
        self.lbl_feedback.show()
        self._update_score_label()

        item = self.q_list.item(self._q_index)
        if item:
            text = item.text()
            if not text.startswith("✅") and not text.startswith("❌"):
                prefix = "✅ " if is_correct else "❌ "
                item.setText(prefix + text)

        if q["giai_thich"]:
            self._set_explanation_visible(True)

    def _prev_q(self):
        if not self._questions:
            return
        self._q_index = (self._q_index - 1) % len(self._questions)
        self._show_question(self._q_index)
        self._select_question_row(self._q_index)

    def _next_q(self):
        if not self._questions:
            return
        if self._q_index >= len(self._questions) - 1:
            self._show_finish_dialog()
            return

        self._q_index += 1
        self._show_question(self._q_index)
        self._select_question_row(self._q_index)

    def _shuffle_questions(self):
        if not self._questions:
            return
        self._set_editing_locked(False)
        random.shuffle(self._questions)
        self._question_results.clear()
        self._q_index = 0
        self._rebuild_question_list(current_row=0)
        self._show_question(0)

    def _shuffle_answer_options(self, q: dict) -> dict:
        shuffled_q = dict(q)
        # Chỉ trộn các đáp án có nội dung
        labels = ["A", "B", "C", "D", "E"]
        valid_labels = [label for label in labels if q.get(label.lower(), "").strip()]
        
        if any(_option_references_answer_labels(q.get(label.lower(), "")) for label in valid_labels):
            return shuffled_q

        old_options = [(label, q[label.lower()]) for label in valid_labels]
        random.shuffle(old_options)

        correct = (q.get("dap_an") or "A").upper()
        for new_label, (old_label, text) in zip(valid_labels, old_options):
            shuffled_q[new_label.lower()] = text
            if old_label == correct:
                shuffled_q["dap_an"] = new_label
        return shuffled_q

    def _shuffle_questions_and_answers(self):
        if not self._questions:
            return
            
        shuffled_count = 0
        new_questions = []
        labels = ["A", "B", "C", "D", "E"]
        for q in self._questions:
            valid_labels = [label for label in labels if q.get(label.lower(), "").strip()]
            has_ref = any(_option_references_answer_labels(q.get(label.lower(), "")) for label in valid_labels)
            if not has_ref:
                shuffled_count += 1
            new_questions.append(self._shuffle_answer_options(q))
            
        self._questions = new_questions
        random.shuffle(self._questions)
        self._set_editing_locked(True)
        self._question_results.clear()
        self._q_index = 0
        self._answered = False
        self._rebuild_question_list(current_row=0)
        self._show_question(0)
        self._update_score_label()
        
        if hasattr(self.window(), "statusBar"):
            self.window().statusBar().showMessage(f"🔀 Đã trộn đáp án {shuffled_count} / {len(self._questions)} câu hỏi")

    def _create_random_test(self):
        total = len(self._all_questions)
        if total == 0:
            QMessageBox.information(self, "Tạo bài test", "Chưa có câu hỏi nào để tạo bài test.")
            return

        default_count = min(10, total)
        count, ok = QInputDialog.getInt(
            self,
            "Tạo bài test ngẫu nhiên",
            f"Nhập số câu hỏi muốn lấy (1-{total}):",
            default_count,
            1,
            total,
            1,
        )
        if not ok:
            return

        self._start_random_test(count)

    def _toggle_question_list(self):
        visible = not self.left_questions_panel.isVisible()
        self.left_questions_panel.setVisible(visible)
        self.btn_toggle_list.setText("📋 Ẩn DS" if visible else "📋 Hiện DS")
        if visible and self._questions and 0 <= getattr(self, '_q_index', -1) < len(self._questions):
            item = self.q_list.item(self._q_index)
            if item:
                QTimer.singleShot(0, lambda: self.q_list.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter))

    def _update_score_label(self):
        total = len(self._questions)
        correct = self._correct_count()
        self.lbl_score.setText(f"Đúng: {correct} / {total} câu")

    def _correct_count(self):
        return sum(1 for q in self._questions if self._question_results.get(q["id"]) is True)

    def _not_correct_questions(self):
        return [q for q in self._questions if self._question_results.get(q["id"]) is not True]

    def _start_random_test(self, count):
        total = len(self._all_questions)
        if total == 0:
            QMessageBox.information(self, "Tạo bài test", "Chưa có câu hỏi nào để tạo bài test.")
            return

        count = max(1, min(count, total))
        selected_questions = random.sample(self._all_questions, count)
        self._start_quiz(
            selected_questions,
            shuffle=True,
            update_source=True,
            mode="random_n",
            random_test_size=count,
        )

    def _restart_quiz_with_questions(self, questions, update_source=True):
        self._start_quiz(questions, shuffle=True, update_source=update_source)

    def _show_finish_dialog(self):
        total = len(self._questions)
        correct = self._correct_count()
        not_correct = self._not_correct_questions()

        retry_all_text = "Làm lại tất cả"
        if self._quiz_mode == "random_n" and self._random_test_size:
            retry_all_text = f"Tiếp tục {self._random_test_size} câu hỏi mới"

        dlg = QuizFinishDialog(correct, total, len(not_correct), retry_all_text, parent=self)
        result = dlg.exec()
        if result == QuizFinishDialog.RETRY_ALL:
            if self._quiz_mode == "random_n" and self._random_test_size:
                self._start_random_test(self._random_test_size)
            else:
                self._restart_quiz_with_questions(self._test_questions, update_source=False)
        elif result == QuizFinishDialog.RETRY_WRONG:
            self._restart_quiz_with_questions(not_correct, update_source=False)

    def _is_save_result(self, result):
        return result == QDialog.DialogCode.Accepted or result == QuizDialog.SAVE_AND_NEXT

    def _select_question_id(self, qid):
        for row in range(self.q_list.count()):
            item = self.q_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == qid:
                self.q_list.setCurrentRow(row)
                self.q_list.scrollToItem(item)
                return

    def _create_question(self, bai_id, data):
        session = get_session()
        try:
            q = CauHoi(bai_id=bai_id, **data)
            session.add(q)
            session.commit()
            return q.id
        finally:
            session.close()

    def _add_q(self):
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Chọn Bài trước khi thêm câu hỏi!")
            return

        selected_id = None
        added_count = 0
        while True:
            dlg = QuizDialog(
                parent=self,
                allow_save_next=True,
                question_number=len(self._questions) + added_count + 1,
            )
            result = dlg.exec()
            if not self._is_save_result(result):
                break

            d = dlg.get_data()
            if not d["noi_dung"]:
                QMessageBox.warning(self, "Lỗi", "Nhập nội dung câu hỏi trước khi lưu!")
                break

            selected_id = self._create_question(bai_id, d)
            added_count += 1
            if result != QuizDialog.SAVE_AND_NEXT:
                break

        self._refresh_list(reset_test=False)
        if selected_id:
            self._select_question_id(selected_id)

    def _add_bulk_q(self):
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Chọn Bài trước khi thêm câu hỏi!")
            return

        dlg = BatchQuizDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        questions = parse_question_batch(dlg.get_text())
        if not questions:
            QMessageBox.warning(
                self,
                "Không parse được",
                "Không tìm thấy câu hỏi hợp lệ. Dùng dạng có nội dung câu hỏi và ít nhất 3 phương án A/B/C/D.",
            )
            return

        session = get_session()
        first_id = None
        try:
            for item in questions:
                data = {
                    "noi_dung": item["noi_dung"],
                    "lua_chon_a": item["lua_chon_a"],
                    "lua_chon_b": item["lua_chon_b"],
                    "lua_chon_c": item["lua_chon_c"],
                    "lua_chon_d": item["lua_chon_d"],
                    "dap_an": item.get("dap_an") or "A",
                    "giai_thich": "",
                    "ghi_chu": "",
                }
                q = CauHoi(bai_id=bai_id, **data)
                session.add(q)
                session.flush()
                if first_id is None:
                    first_id = q.id
            session.commit()
        finally:
            session.close()

        QMessageBox.information(self, "Thêm hàng loạt", f"Đã thêm {len(questions)} câu hỏi.")
        self._refresh_list(reset_test=False)
        if first_id:
            self._select_question_id(first_id)

    def _backup_questions(self):
        if not self._all_questions:
            QMessageBox.information(self, "Backup kiểm tra", "Không có câu hỏi nào để backup.")
            return

        default_name = f"backup_kiem_tra_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup câu hỏi kiểm tra",
            default_name,
            "JSON (*.json)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"

        data = {
            "type": "hoc_tap_quiz_backup",
            "version": 1,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "count": len(self._all_questions),
            "questions": [
                {
                    "noi_dung": q["noi_dung"],
                    "hinh_anh": q.get("hinh_anh") or "",
                    "lua_chon_a": q["a"],
                    "lua_chon_b": q["b"],
                    "lua_chon_c": q["c"],
                    "lua_chon_d": q["d"],
                    "lua_chon_e": q.get("e") or "",
                    "dap_an": q["dap_an"],
                    "giai_thich": q.get("giai_thich") or "",
                    "ghi_chu": q.get("ghi_chu") or "",
                }
                for q in self._all_questions
            ],
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.warning(self, "Backup kiểm tra", f"Không ghi được file backup:\n{exc}")
            return

        QMessageBox.information(self, "Backup kiểm tra", f"Đã backup {len(self._all_questions)} câu hỏi.")

    def _restore_questions(self):
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Restore kiểm tra", "Chọn Bài trước khi restore câu hỏi!")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore câu hỏi kiểm tra",
            "",
            "JSON (*.json)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Restore kiểm tra", f"Không đọc được file backup:\n{exc}")
            return

        if data.get("type") != "hoc_tap_quiz_backup":
            QMessageBox.warning(self, "Restore kiểm tra", "File này không phải backup câu hỏi kiểm tra hợp lệ.")
            return

        questions = data.get("questions")
        if not isinstance(questions, list):
            QMessageBox.warning(self, "Restore kiểm tra", "File backup không có danh sách câu hỏi hợp lệ.")
            return

        valid_questions = []
        for item in questions:
            if not isinstance(item, dict):
                continue
            noi_dung = (item.get("noi_dung") or "").strip()
            if not noi_dung:
                continue
            valid_questions.append({
                "noi_dung": noi_dung,
                "hinh_anh": (item.get("hinh_anh") or "").strip(),
                "lua_chon_a": (item.get("lua_chon_a") or item.get("a") or "").strip(),
                "lua_chon_b": (item.get("lua_chon_b") or item.get("b") or "").strip(),
                "lua_chon_c": (item.get("lua_chon_c") or item.get("c") or "").strip(),
                "lua_chon_d": (item.get("lua_chon_d") or item.get("d") or "").strip(),
                "lua_chon_e": (item.get("lua_chon_e") or item.get("e") or "").strip(),
                "dap_an": (item.get("dap_an") or "A").strip().upper()[:1] or "A",
                "giai_thich": (item.get("giai_thich") or "").strip(),
                "ghi_chu": (item.get("ghi_chu") or "").strip(),
            })

        if not valid_questions:
            QMessageBox.warning(self, "Restore kiểm tra", "Không tìm thấy câu hỏi hợp lệ trong file backup.")
            return

        if QMessageBox.question(
            self,
            "Restore kiểm tra",
            f"Nhập {len(valid_questions)} câu hỏi vào Bài đang chọn?",
        ) != QMessageBox.StandardButton.Yes:
            return

        session = get_session()
        try:
            for item in valid_questions:
                session.add(CauHoi(bai_id=bai_id, **item))
            session.commit()
        finally:
            session.close()

        self._refresh_list(reset_test=False)
        QMessageBox.information(self, "Restore kiểm tra", f"Đã restore {len(valid_questions)} câu hỏi.")

    def _apply_answer_key(self):
        if not self._questions:
            QMessageBox.information(self, "Đáp án hàng loạt", "Chưa có câu hỏi nào để cập nhật đáp án.")
            return

        dlg = AnswerKeyDialog(len(self._questions), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        answers, errors = parse_answer_key(dlg.get_text(), len(self._questions))
        if not answers:
            message = "Không tìm thấy đáp án hợp lệ dạng 1a, 2b, 3c..."
            if errors:
                message += "\n\n" + "\n".join(errors[:10])
            QMessageBox.warning(self, "Đáp án hàng loạt", message)
            return

        if errors:
            shown_errors = "\n".join(errors[:10])
            extra = "" if len(errors) <= 10 else f"\n... và {len(errors) - 10} lỗi khác."
            if QMessageBox.question(
                self,
                "Đáp án hàng loạt",
                f"Có {len(errors)} lỗi parse:\n{shown_errors}{extra}\n\nVẫn cập nhật {len(answers)} đáp án parse được?",
            ) != QMessageBox.StandardButton.Yes:
                return

        id_to_answer = {
            self._questions[number - 1]["id"]: answer
            for number, answer in answers.items()
            if 1 <= number <= len(self._questions)
        }

        session = get_session()
        updated_count = 0
        try:
            for qid, answer in id_to_answer.items():
                q = session.get(CauHoi, qid)
                if not q:
                    continue
                q.dap_an = answer
                updated_count += 1
            session.commit()
        finally:
            session.close()

        for collection in (self._all_questions, self._test_questions, self._questions):
            for question in collection:
                answer = id_to_answer.get(question["id"])
                if answer:
                    question["dap_an"] = answer
                    self._question_results.pop(question["id"], None)

        if self._questions:
            self._q_index = min(self._q_index, len(self._questions) - 1)
            self._show_question(self._q_index)
            self._select_question_row(self._q_index)
        self._update_score_label()
        QMessageBox.information(self, "Đáp án hàng loạt", f"Đã cập nhật {updated_count} đáp án.")

    def _create_starred_test(self):
        starred_qs = [q for q in self._all_questions if q.get("danh_dau")]
        if not starred_qs:
            QMessageBox.information(self, "Test Sao", "Chưa có câu hỏi nào được đánh dấu sao trong bài này!")
            return
            
        self._set_editing_locked(False)
        self._start_quiz(
            questions=starred_qs,
            shuffle=True,
            update_source=True,
            mode="starred",
        )

    def _toggle_star(self):
        if not self._questions or self._q_index < 0 or self._q_index >= len(self._questions):
            return
        
        q_dict = self._questions[self._q_index]
        qid = q_dict["id"]
        new_status = not q_dict.get("danh_dau", False)
        
        session = get_session()
        try:
            db_q = session.get(CauHoi, qid)
            if db_q:
                db_q.danh_dau = new_status
                session.commit()
        finally:
            session.close()
            
        for collection in (self._all_questions, self._test_questions, self._questions):
            for item in collection:
                if item["id"] == qid:
                    item["danh_dau"] = new_status
                    
        self._show_question(self._q_index)
        
        item = self.q_list.item(self._q_index)
        if item:
            text = item.text()
            if new_status and not text.startswith("⭐"):
                item.setText(f"⭐ {text}")
            elif not new_status and text.startswith("⭐ "):
                item.setText(text[2:])

    def _edit_q(self):
        if getattr(self, "_answers_shuffled_session", False):
            self._warn_editing_locked()
            return
        if not self._current_id:
            return

        question_ids = [q["id"] for q in self._questions]
        if self._current_id not in question_ids:
            return

        pos = question_ids.index(self._current_id)
        selected_id = self._current_id
        while pos < len(question_ids):
            qid = question_ids[pos]
            session = get_session()
            try:
                q = session.get(CauHoi, qid)
                if not q:
                    break
                dlg = QuizDialog(
                    q=q,
                    parent=self,
                    allow_save_next=pos < len(question_ids) - 1,
                    question_number=pos + 1,
                    question_total=len(question_ids),
                )
                result = dlg.exec()
                if not self._is_save_result(result):
                    selected_id = qid
                    break
                d = dlg.get_data()
                if not d["noi_dung"]:
                    QMessageBox.warning(self, "Lỗi", "Nhập nội dung câu hỏi trước khi lưu!")
                    selected_id = qid
                    break
                for k, v in d.items():
                    setattr(q, k, v)
                session.commit()
            finally:
                session.close()

            selected_id = qid
            if result == QuizDialog.SAVE_AND_NEXT and pos < len(question_ids) - 1:
                pos += 1
                selected_id = question_ids[pos]
                continue
            break

        self._refresh_list(reset_test=False)
        self._select_question_id(selected_id)

    def _delete_q(self):
        if not self._current_id:
            return
        if QMessageBox.question(self, "Xóa", "Xóa câu hỏi này?") == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                q = session.get(CauHoi, self._current_id)
                if q:
                    session.delete(q); session.commit()
            finally:
                session.close()
            self._current_id = None
            self._refresh_list(reset_test=False)

    def _edit_note(self):
        if not self._current_id:
            return
        session = get_session()
        try:
            q = session.get(CauHoi, self._current_id)
            if not q: return
            dlg = NoteDialog(note=q.ghi_chu, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                q.ghi_chu = dlg.get_note()
                session.commit()
                # Update local cache
                for item in self._questions:
                    if item["id"] == self._current_id:
                        item["ghi_chu"] = q.ghi_chu
        finally:
            session.close()

    # ── Lưu / Khôi phục trạng thái khi thoát ─────────────────────────────

    def save_state(self):
        """Lưu trạng thái phiên kiểm tra vào QSettings (key toàn cục)."""
        import json
        s = QSettings("HocTap", "HocTapApp")

        state = {
            # Lưu topic context để restore biết cần load bài nào
            "chu_de_id":        getattr(self.topic_bar, "get_chu_de_id", lambda: None)(),
            "chuong_id":        getattr(self.topic_bar, "get_chuong_id", lambda: None)(),
            "bai_id":           getattr(self.topic_bar, "get_bai_id",    lambda: None)(),
            "q_index":          self._q_index,
            "quiz_mode":        self._quiz_mode,
            "random_test_size": self._random_test_size,
            # Thứ tự câu hỏi (list id)
            "question_ids":     [q["id"] for q in self._questions],
            # Kết quả trả lời: {str(id): True/False}
            "question_results": {str(k): v for k, v in self._question_results.items()},
        }
        s.setValue("quiz_state/last", json.dumps(state, ensure_ascii=False))
        s.sync()

    def restore_state(self):
        """
        Khôi phục trạng thái phiên kiểm tra từ QSettings.
        Gọi sau khi _all_questions đã được load (tức sau _refresh_list).
        """
        import json
        s = QSettings("HocTap", "HocTapApp")
        raw = s.value("quiz_state/last")
        if not raw:
            return

        try:
            state = json.loads(raw)
        except Exception:
            return

        saved_ids     = state.get("question_ids", [])
        saved_results = {int(k): v for k, v in state.get("question_results", {}).items()}
        saved_index   = state.get("q_index", 0)
        saved_mode    = state.get("quiz_mode", "all")
        saved_size    = state.get("random_test_size")
        saved_bai     = state.get("bai_id")
        saved_ch      = state.get("chuong_id")
        saved_cd      = state.get("chu_de_id")

        # Yêu cầu topic_bar chọn đúng bài đã lưu
        if saved_bai or saved_ch or saved_cd:
            try:
                self.topic_bar.set_selection(saved_cd, saved_ch, saved_bai)
            except Exception:
                pass  # topic_bar không hỗ trợ set_selection → bỏ qua

        if not saved_ids or not self._all_questions:
            return

        # Tái tạo thứ tự câu hỏi theo id đã lưu
        all_dict = {q["id"]: q for q in self._all_questions}
        restored = [all_dict[qid] for qid in saved_ids if qid in all_dict]
        if not restored:
            return

        self._set_editing_locked(False)
        self._questions        = restored
        self._test_questions   = list(restored)
        self._quiz_mode        = saved_mode
        self._random_test_size = saved_size
        self._question_results = {k: v for k, v in saved_results.items() if k in all_dict}
        self._answered         = False
        self._q_index          = max(0, min(saved_index, len(self._questions) - 1))

        self._rebuild_question_list(current_row=self._q_index)
        self._show_question(self._q_index)
        self._update_score_label()

