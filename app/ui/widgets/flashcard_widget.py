"""
app/ui/widgets/flashcard_widget.py — Flashcard module giống Vocabulary EnglishMaster
"""
import json
import re
import random
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QFrame,
    QMessageBox, QDialog, QFormLayout, QLineEdit,
    QTextEdit, QDialogButtonBox, QGroupBox, QSizePolicy,
    QInputDialog, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.data.database import get_session, Flashcard, Bai, Chuong, ChuDe
from app.ui.styles import DIALOG_STYLE


FLASHCARD_LABEL_RE = re.compile(
    r"(?i)(câu\s*hỏi|cau\s*hoi|mặt\s*trước|mat\s*truoc|front|question|"
    r"đáp\s*án|dap\s*an|mặt\s*sau|mat\s*sau|back|answer)\s*[:：]"
)
SENTENCE_RE = re.compile(r"[^.!?。！？]+[.!?。！？]+|[^.!?。！？]+$")


def _clean_flashcard_text(text: str) -> str:
    return " ".join(line.strip() for line in (text or "").strip().splitlines() if line.strip())


def _flashcard_label_kind(label: str) -> str:
    label = label.lower()
    if any(word in label for word in ["đáp", "dap", "sau", "back", "answer"]):
        return "back"
    return "front"


def _split_two_sentences(text: str) -> tuple[str, str] | None:
    parts = [_clean_flashcard_text(match.group(0)) for match in SENTENCE_RE.finditer(text or "")]
    parts = [part for part in parts if part]
    if len(parts) == 2:
        return parts[0], parts[1]
    return None


def parse_flashcard_text(raw_text: str) -> dict | None:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None

    labels = [
        (_flashcard_label_kind(match.group(1)), match.start(), match.end())
        for match in FLASHCARD_LABEL_RE.finditer(raw_text)
    ]
    for i, (kind, _start, end) in enumerate(labels):
        if kind != "front":
            continue
        next_back = next(
            ((j, label) for j, label in enumerate(labels[i + 1:], i + 1) if label[0] == "back"),
            None,
        )
        if not next_back:
            continue
        back_index, (_back_kind, back_start, back_end) = next_back
        next_front = next(
            (label for label in labels[back_index + 1:] if label[0] == "front"),
            None,
        )
        front = _clean_flashcard_text(raw_text[end:back_start])
        back_end_pos = next_front[1] if next_front else len(raw_text)
        back = _clean_flashcard_text(raw_text[back_end:back_end_pos])
        if front and back:
            return {"mat_truoc": front, "mat_sau": back}

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if len(lines) == 2:
        return {"mat_truoc": lines[0], "mat_sau": lines[1]}

    split_sentences = _split_two_sentences(raw_text)
    if split_sentences:
        front, back = split_sentences
        return {"mat_truoc": front, "mat_sau": back}

    return None


def parse_flashcard_batch(raw_text: str) -> list[dict]:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return []

    labels = [
        (_flashcard_label_kind(match.group(1)), match.start(), match.end())
        for match in FLASHCARD_LABEL_RE.finditer(raw_text)
    ]
    cards = []
    i = 0
    while i < len(labels):
        kind, _start, end = labels[i]
        if kind != "front":
            i += 1
            continue

        back_index = None
        for j in range(i + 1, len(labels)):
            if labels[j][0] == "back":
                back_index = j
                break
        if back_index is None:
            break

        _back_kind, back_start, back_end = labels[back_index]
        next_front_index = None
        for j in range(back_index + 1, len(labels)):
            if labels[j][0] == "front":
                next_front_index = j
                break

        front = _clean_flashcard_text(raw_text[end:back_start])
        back_end_pos = labels[next_front_index][1] if next_front_index is not None else len(raw_text)
        back = _clean_flashcard_text(raw_text[back_end:back_end_pos])
        if front and back:
            cards.append({"mat_truoc": front, "mat_sau": back})

        i = next_front_index if next_front_index is not None else len(labels)

    if cards:
        return cards

    blocks = [block.strip() for block in re.split(r"\n\s*\n+", raw_text) if block.strip()]
    for block in blocks:
        parsed = parse_flashcard_text(block)
        if parsed:
            cards.append(parsed)
    if cards:
        return cards

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if len(lines) >= 2:
        for i in range(0, len(lines) - 1, 2):
            cards.append({"mat_truoc": lines[i], "mat_sau": lines[i + 1]})

    return cards


class FlashcardDialog(QDialog):
    def __init__(self, card: Flashcard = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm / Sửa Flashcard")
        self.setMinimumSize(480, 380)
        self.setStyleSheet(DIALOG_STYLE)
        self._is_parsing_flashcard = False

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.inp_front = QTextEdit()
        self.inp_front.setPlaceholderText(
            "Mặt trước (từ / câu hỏi / khái niệm)...\n"
            "Có thể dán: Câu hỏi: ... Đáp án: ..."
        )
        self.inp_front.setMinimumHeight(80)

        self.inp_back = QTextEdit()
        self.inp_back.setPlaceholderText("Mặt sau (nghĩa / giải thích / đáp án)...")
        self.inp_back.setMinimumHeight(80)

        self.inp_note = QLineEdit()
        self.inp_note.setPlaceholderText("Ghi chú thêm (ví dụ, ngữ cảnh)...")

        form.addRow("Mặt trước:", self.inp_front)
        form.addRow("Mặt sau:", self.inp_back)
        form.addRow("Ghi chú:", self.inp_note)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if card:
            self.inp_front.setPlainText(card.mat_truoc)
            self.inp_back.setPlainText(card.mat_sau)
            self.inp_note.setText(card.ghi_chu)
        self.inp_front.textChanged.connect(self._try_parse_front_text)

    def _try_parse_front_text(self):
        if self._is_parsing_flashcard:
            return

        raw_text = self.inp_front.toPlainText()
        parsed = parse_flashcard_text(raw_text)
        if not parsed:
            return

        has_labels = bool(FLASHCARD_LABEL_RE.search(raw_text))
        if self.inp_back.toPlainText().strip() and not has_labels:
            return

        self._is_parsing_flashcard = True
        try:
            self.inp_front.setPlainText(parsed["mat_truoc"])
            self.inp_back.setPlainText(parsed["mat_sau"])
        finally:
            self._is_parsing_flashcard = False

    def get_data(self):
        return {
            "mat_truoc": self.inp_front.toPlainText().strip(),
            "mat_sau":   self.inp_back.toPlainText().strip(),
            "ghi_chu":   self.inp_note.text().strip(),
        }


class BatchFlashcardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm hàng loạt Flashcard")
        self.setMinimumSize(620, 480)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Dán nhiều flashcard. Mỗi thẻ có thể dùng 'Câu hỏi: ... Đáp án: ...' "
            "hoặc hai dòng liên tiếp: dòng 1 là mặt trước, dòng 2 là mặt sau."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.inp = QTextEdit()
        self.inp.setPlaceholderText(
            "Câu hỏi: Nội dung câu hỏi 1\n"
            "Đáp án: Nội dung đáp án 1\n\n"
            "Câu hỏi: Nội dung câu hỏi 2\n"
            "Đáp án: Nội dung đáp án 2\n\n"
            "Mặt trước dòng 1\n"
            "Mặt sau dòng 2"
        )
        layout.addWidget(self.inp, 1)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Thêm hàng loạt")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_text(self):
        return self.inp.toPlainText().strip()


class TopicFlashCard(QFrame):
    next_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card_data = None
        self.front = True
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0f766e,stop:1 #134e4a);"
            "border-radius:18px;border:2px solid #14b8a6;}"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(24, 18, 24, 18)
        self.lay.setSpacing(8)
        self._show()

    def _clear(self):
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show(self):
        self._clear()
        if not self.card_data:
            title = QLabel("Question")
            title.setStyleSheet("color:#ccfbf1;font-size:16px;font-weight:700;border:none;")
            self.lay.addWidget(title)
            lbl = QLabel("Chọn thẻ để bắt đầu")
            lbl.setStyleSheet("color:#f0fdfa;background:transparent;border:none;font-size:28px;font-weight:800;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lay.addWidget(lbl, stretch=1)
            return

        if self.front:
            title = QLabel("Question")
            title.setStyleSheet("color:#ccfbf1;font-size:16px;font-weight:700;border:none;")
            self.lay.addWidget(title)
            
            question = QLabel(self.card_data.get("front", ""))
            question.setWordWrap(True)
            question.setAlignment(Qt.AlignmentFlag.AlignCenter)
            question.setStyleSheet("color:#f0fdfa;background:transparent;border:none;font-size:28px;font-weight:800;line-height:1.3;")
            self.lay.addWidget(question, stretch=1)
            
            hint = QLabel("Chạm để lật xem Đáp án")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setStyleSheet("color:#5eead4;font-size:14px;background:transparent;border:none;")
            self.lay.addWidget(hint)
        else:
            title = QLabel("Answer")
            title.setStyleSheet("color:#99f6e4;font-size:16px;font-weight:700;border:none;")
            self.lay.addWidget(title)
            
            answer = QLabel(self.card_data.get("back", ""))
            answer.setWordWrap(True)
            answer.setAlignment(Qt.AlignmentFlag.AlignCenter)
            answer.setStyleSheet("color:#fef3c7;background:transparent;border:none;font-size:28px;font-weight:800;")
            self.lay.addWidget(answer, stretch=1)
            
            note = self.card_data.get("note", "").strip()
            if note:
                note_lbl = QLabel(f"💡 Note: {note}")
                note_lbl.setWordWrap(True)
                note_lbl.setStyleSheet("color:#e2e8f0;background:transparent;border:none;font-size:18px;")
                self.lay.addWidget(note_lbl)
                
            hint = QLabel("Chạm để lật lại Câu hỏi")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setStyleSheet("color:#5eead4;font-size:14px;background:transparent;border:none;")
            self.lay.addWidget(hint)

    def set_card(self, data: dict):
        self.card_data = data
        self.front = True
        self._show()

    def mousePressEvent(self, event):
        if self.card_data and event.button() == Qt.MouseButton.LeftButton:
            self.front = not self.front
            self._show()
            event.accept()
        elif self.card_data and event.button() == Qt.MouseButton.RightButton:
            self.next_requested.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class FlashcardWidget(QWidget):
    def __init__(self, topic_bar, parent=None):
        super().__init__(parent)
        self.topic_bar = topic_bar
        self._current_id = None
        self._all_cards = []
        self._cards = []
        self._card_index = 0
        self._revealed = False
        self._study_n_count = None
        self._build_ui()
        topic_bar.selection_changed.connect(self._refresh_list)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ─── LEFT: danh sách card ─────────────────────────────────────
        left = QWidget()
        self.left_cards_panel = left
        lv = QVBoxLayout(left)
        lv.setSpacing(6)
        lv.setContentsMargins(8, 8, 4, 8)

        lv.addWidget(QLabel("📋 Danh sách Flashcard"))
        self.card_list = QListWidget()
        self.card_list.currentItemChanged.connect(self._on_card_selected)
        self.card_list.itemDoubleClicked.connect(lambda _: self._edit_card())
        lv.addWidget(self.card_list, 1)

        list_btns = QHBoxLayout()
        self.btn_add    = QPushButton("➕ Thêm")
        self.btn_bulk   = QPushButton("📥 Hàng loạt")
        self.btn_edit   = QPushButton("✏️ Sửa")
        self.btn_delete = QPushButton("🗑 Xóa")
        self.btn_add.setObjectName("primaryBtn")
        self.btn_delete.setObjectName("dangerBtn")
        for b in [self.btn_add, self.btn_bulk, self.btn_edit, self.btn_delete]:
            b.setFixedHeight(30)
            list_btns.addWidget(b)
        lv.addLayout(list_btns)

        backup_btns = QHBoxLayout()
        self.btn_backup = QPushButton("💾 Backup")
        self.btn_restore = QPushButton("📂 Restore")
        self.btn_backup.setToolTip("Xuất các flashcard đang hiển thị ra file JSON")
        self.btn_restore.setToolTip("Nhập flashcard từ file JSON vào Bài đang chọn")
        for b in [self.btn_backup, self.btn_restore]:
            b.setFixedHeight(30)
            backup_btns.addWidget(b)
        lv.addLayout(backup_btns)

        self.lbl_count = QLabel("0 thẻ")
        self.lbl_count.setObjectName("muted")
        lv.addWidget(self.lbl_count)

        splitter.addWidget(left)

        # ─── RIGHT: flashcard display ──────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setSpacing(12)
        rv.setContentsMargins(8, 16, 8, 8)

        # Header row
        hdr = QHBoxLayout()
        self.lbl_progress = QLabel("0 / 0")
        self.lbl_progress.setObjectName("muted")
        hdr.addWidget(self.lbl_progress)
        hdr.addStretch()
        self.btn_toggle_list = QPushButton("📋 Ẩn DS")
        self.btn_toggle_list.setFixedHeight(30)
        self.btn_toggle_list.setToolTip("Ẩn/hiện danh sách flashcard")
        self.btn_toggle_list.clicked.connect(self._toggle_card_list)
        hdr.addWidget(self.btn_toggle_list)
        self.btn_study_n = QPushButton("🎯 Study N")
        self.btn_study_n.setFixedHeight(30)
        self.btn_study_n.setToolTip("Chọn ngẫu nhiên N flashcard để học")
        self.btn_study_n.clicked.connect(self._study_n_cards)
        hdr.addWidget(self.btn_study_n)
        self.btn_study_all = QPushButton("📚 Học tất cả")
        self.btn_study_all.setFixedHeight(30)
        self.btn_study_all.setToolTip("Học tất cả flashcard trong danh sách")
        self.btn_study_all.clicked.connect(self._study_all_cards)
        hdr.addWidget(self.btn_study_all)
        self.btn_shuffle = QPushButton("🔀 Trộn")
        self.btn_shuffle.setFixedHeight(30)
        self.btn_shuffle.clicked.connect(self._shuffle_cards)
        hdr.addWidget(self.btn_shuffle)
        rv.addLayout(hdr)

        # Card widget
        self.card_frame = TopicFlashCard(self)
        self.card_frame.next_requested.connect(self._next_card)
        rv.addWidget(self.card_frame, 1)

        # Navigation
        nav = QHBoxLayout()
        self.btn_prev_card = QPushButton("◀ Trước")
        self.btn_next_card = QPushButton("Tiếp ▶")
        self.btn_prev_card.setFixedHeight(36)
        self.btn_next_card.setFixedHeight(36)
        nav.addWidget(self.btn_prev_card)
        nav.addStretch()
        nav.addWidget(self.btn_next_card)
        rv.addLayout(nav)

        splitter.addWidget(right)
        splitter.setSizes([280, 600])

        # Connections
        self.btn_add.clicked.connect(self._add_card)
        self.btn_bulk.clicked.connect(self._add_bulk_cards)
        self.btn_edit.clicked.connect(self._edit_card)
        self.btn_delete.clicked.connect(self._delete_card)
        self.btn_backup.clicked.connect(self._backup_cards)
        self.btn_restore.clicked.connect(self._restore_cards)
        self.btn_prev_card.clicked.connect(self._prev_card)
        self.btn_next_card.clicked.connect(self._next_card)

        self._refresh_list()

    def _refresh_list(self, *_):
        session = get_session()
        try:
            q = session.query(Flashcard)
            cd, ch, bai = (
                self.topic_bar.get_chu_de_id(),
                self.topic_bar.get_chuong_id(),
                self.topic_bar.get_bai_id(),
            )
            if bai:
                q = q.filter(Flashcard.bai_id == bai)
            elif ch:
                ids = [b.id for b in session.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter(Flashcard.bai_id.in_(ids))
            elif cd:
                cids = [c.id for c in session.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter(Flashcard.bai_id.in_(bids))
            cards = q.order_by(Flashcard.tao_luc).all()
            self._all_cards = [{"id": c.id, "front": c.mat_truoc, "back": c.mat_sau, "note": c.ghi_chu} for c in cards]
            self._cards = list(self._all_cards)
            self._study_n_count = None
            self._update_count_label()
            if self._cards:
                self._card_index = 0
                self._rebuild_card_list(current_row=0)
                self._show_card(0)
            else:
                self._rebuild_card_list()
                self.lbl_progress.setText("0 / 0")
        finally:
            session.close()

    def _rebuild_card_list(self, current_row=None):
        self.card_list.blockSignals(True)
        try:
            self.card_list.clear()
            if not self._cards:
                self._current_id = None
                return

            for c in self._cards:
                front = c["front"]
                preview = front[:60] + ("..." if len(front) > 60 else "")
                item = QListWidgetItem(f"🃏 {preview}")
                item.setData(Qt.ItemDataRole.UserRole, c["id"])
                self.card_list.addItem(item)

            if current_row is not None and 0 <= current_row < len(self._cards):
                self.card_list.setCurrentRow(current_row)
                self._current_id = self._cards[current_row]["id"]
        finally:
            self.card_list.blockSignals(False)

    def _update_count_label(self):
        if self._study_n_count is not None:
            self.lbl_count.setText(f"{len(self._cards)} / {len(self._all_cards)} thẻ")
        else:
            self.lbl_count.setText(f"{len(self._all_cards)} thẻ")

    def _select_card_row(self, row):
        if not self._cards:
            self._current_id = None
            return
        self.card_list.blockSignals(True)
        try:
            self.card_list.setCurrentRow(row)
            self._current_id = self._cards[row]["id"]
        finally:
            self.card_list.blockSignals(False)

    def _on_card_selected(self, item):
        if not item:
            return
        cid = item.data(Qt.ItemDataRole.UserRole)
        self._current_id = cid
        for i, c in enumerate(self._cards):
            if c["id"] == cid:
                self._card_index = i
                self._show_card(i)
                break

    def _show_card(self, index):
        if not self._cards or index < 0 or index >= len(self._cards):
            return
        c = self._cards[index]
        self.card_frame.set_card(c)
        self.lbl_progress.setText(f"{index+1} / {len(self._cards)}")

    def _prev_card(self):
        if self._card_index > 0:
            self._card_index -= 1
            self._show_card(self._card_index)
            self._select_card_row(self._card_index)

    def _next_card(self):
        if not self._cards:
            return
        self._card_index = (self._card_index + 1) % len(self._cards)
        self._show_card(self._card_index)
        self._select_card_row(self._card_index)

    def _shuffle_cards(self):
        if not self._cards:
            return
        shuffled_cards = list(self._cards)
        random.shuffle(shuffled_cards)
        self._cards = shuffled_cards
        self._card_index = 0
        self._rebuild_card_list(current_row=0)
        self._show_card(0)
        self._update_count_label()

    def _study_n_cards(self):
        total = len(self._all_cards)
        if total == 0:
            QMessageBox.information(self, "Study N", "Chưa có flashcard nào để học.")
            return

        default_count = min(10, total)
        count, ok = QInputDialog.getInt(
            self,
            "Study N flashcard",
            f"Nhập số flashcard muốn học (1-{total}):",
            default_count,
            1,
            total,
            1,
        )
        if not ok:
            return

        self._cards = random.sample(self._all_cards, count)
        random.shuffle(self._cards)
        self._study_n_count = count
        self._card_index = 0
        self._rebuild_card_list(current_row=0)
        self._show_card(0)
        self._update_count_label()

    def _study_all_cards(self):
        if not self._all_cards:
            QMessageBox.information(self, "Học tất cả", "Chưa có flashcard nào để học.")
            return

        self._cards = list(self._all_cards)
        self._study_n_count = None
        self._card_index = 0
        self._rebuild_card_list(current_row=0)
        self._show_card(0)
        self._update_count_label()

    def _toggle_card_list(self):
        visible = not self.left_cards_panel.isVisible()
        self.left_cards_panel.setVisible(visible)
        self.btn_toggle_list.setText("📋 Ẩn DS" if visible else "📋 Hiện DS")

    def _add_card(self):
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Chọn Bài trước khi thêm flashcard!")
            return
        dlg = FlashcardDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if not d["mat_truoc"]:
                return
            session = get_session()
            try:
                fc = Flashcard(mat_truoc=d["mat_truoc"], mat_sau=d["mat_sau"], ghi_chu=d["ghi_chu"], bai_id=bai_id)
                session.add(fc); session.commit()
            finally:
                session.close()
            self._refresh_list()

    def _add_bulk_cards(self):
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Chọn Bài trước khi thêm flashcard!")
            return

        dlg = BatchFlashcardDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        cards = parse_flashcard_batch(dlg.get_text())
        if not cards:
            QMessageBox.warning(
                self,
                "Không parse được",
                "Không tìm thấy flashcard hợp lệ. Dùng dạng 'Câu hỏi: ... Đáp án: ...' hoặc từng cặp 2 dòng.",
            )
            return

        session = get_session()
        try:
            for card in cards:
                session.add(
                    Flashcard(
                        mat_truoc=card["mat_truoc"],
                        mat_sau=card["mat_sau"],
                        ghi_chu="",
                        bai_id=bai_id,
                    )
                )
            session.commit()
        finally:
            session.close()

        QMessageBox.information(self, "Thêm hàng loạt", f"Đã thêm {len(cards)} flashcard.")
        self._refresh_list()

    def _backup_cards(self):
        if not self._all_cards:
            QMessageBox.information(self, "Backup flashcard", "Không có flashcard nào để backup.")
            return

        default_name = f"backup_flashcard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup flashcard",
            default_name,
            "JSON (*.json)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"

        data = {
            "type": "hoc_tap_flashcard_backup",
            "version": 1,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "count": len(self._all_cards),
            "flashcards": [
                {
                    "mat_truoc": c["front"],
                    "mat_sau": c["back"],
                    "ghi_chu": c.get("note") or "",
                }
                for c in self._all_cards
            ],
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.warning(self, "Backup flashcard", f"Không ghi được file backup:\n{exc}")
            return

        QMessageBox.information(self, "Backup flashcard", f"Đã backup {len(self._all_cards)} flashcard.")

    def _restore_cards(self):
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Restore flashcard", "Chọn Bài trước khi restore flashcard!")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore flashcard",
            "",
            "JSON (*.json)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Restore flashcard", f"Không đọc được file backup:\n{exc}")
            return

        if data.get("type") != "hoc_tap_flashcard_backup":
            QMessageBox.warning(self, "Restore flashcard", "File này không phải backup flashcard hợp lệ.")
            return

        cards = data.get("flashcards")
        if not isinstance(cards, list):
            QMessageBox.warning(self, "Restore flashcard", "File backup không có danh sách flashcard hợp lệ.")
            return

        valid_cards = []
        for item in cards:
            if not isinstance(item, dict):
                continue
            front = (item.get("mat_truoc") or item.get("front") or "").strip()
            if not front:
                continue
            valid_cards.append({
                "mat_truoc": front,
                "mat_sau": (item.get("mat_sau") or item.get("back") or "").strip(),
                "ghi_chu": (item.get("ghi_chu") or item.get("note") or "").strip(),
            })

        if not valid_cards:
            QMessageBox.warning(self, "Restore flashcard", "Không tìm thấy flashcard hợp lệ trong file backup.")
            return

        if QMessageBox.question(
            self,
            "Restore flashcard",
            f"Nhập {len(valid_cards)} flashcard vào Bài đang chọn?",
        ) != QMessageBox.StandardButton.Yes:
            return

        session = get_session()
        try:
            for item in valid_cards:
                session.add(Flashcard(bai_id=bai_id, **item))
            session.commit()
        finally:
            session.close()

        self._refresh_list()
        QMessageBox.information(self, "Restore flashcard", f"Đã restore {len(valid_cards)} flashcard.")

    def _edit_card(self):
        if not self._current_id:
            return
        session = get_session()
        try:
            fc = session.get(Flashcard, self._current_id)
            if not fc: return
            dlg = FlashcardDialog(card=fc, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                d = dlg.get_data()
                fc.mat_truoc = d["mat_truoc"]
                fc.mat_sau   = d["mat_sau"]
                fc.ghi_chu   = d["ghi_chu"]
                session.commit()
        finally:
            session.close()
        self._refresh_list()

    def _delete_card(self):
        if not self._current_id:
            return
        if QMessageBox.question(self, "Xóa", "Xóa thẻ này?") == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                fc = session.get(Flashcard, self._current_id)
                if fc:
                    session.delete(fc); session.commit()
            finally:
                session.close()
            self._current_id = None
            self._refresh_list()
