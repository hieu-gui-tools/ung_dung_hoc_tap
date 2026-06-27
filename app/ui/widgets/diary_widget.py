"""
app/ui/widgets/diary_widget.py — Nhật kí theo ngày (text + ghi âm)
"""
import os
import time
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QFrame,
    QMessageBox, QTextEdit, QGroupBox
)
from PySide6.QtCore import Qt, QTimer

from app.data.database import get_session, NhatKi, Bai, Chuong, ChuDe
from app.core.workers import AudioRecorder
from app.ui.widgets.common import AudioPlayerBar


def get_diary_audio_dir():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    d = os.path.join(base, "media", "diary")
    os.makedirs(d, exist_ok=True)
    return d


class DiaryWidget(QWidget):
    def __init__(self, topic_bar, parent=None):
        super().__init__(parent)
        self.topic_bar = topic_bar
        self.recorder = AudioRecorder()
        self._current_id = None
        self._rec_seconds = 0
        self._rec_timer = QTimer()
        self._rec_timer.setInterval(1000)
        self._rec_timer.timeout.connect(self._update_rec_time)
        self._build_ui()
        topic_bar.selection_changed.connect(self._refresh_list)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ─── LEFT: danh sách nhật kí ────────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setSpacing(6)
        lv.setContentsMargins(8, 8, 4, 8)

        lv.addWidget(QLabel("📅 Nhật kí theo ngày"))
        self.diary_list = QListWidget()
        self.diary_list.currentItemChanged.connect(self._on_entry_selected)
        lv.addWidget(self.diary_list, 1)

        list_btns = QHBoxLayout()
        self.btn_new    = QPushButton("➕ Mới")
        self.btn_delete = QPushButton("🗑 Xóa")
        self.btn_new.setObjectName("primaryBtn")
        self.btn_delete.setObjectName("dangerBtn")
        for b in [self.btn_new, self.btn_delete]:
            b.setFixedHeight(30)
            list_btns.addWidget(b)
        lv.addLayout(list_btns)

        self.lbl_entry_count = QLabel("0 mục")
        self.lbl_entry_count.setObjectName("muted")
        lv.addWidget(self.lbl_entry_count)

        splitter.addWidget(left)

        # ─── RIGHT: viết nhật kí ────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setSpacing(8)
        rv.setContentsMargins(8, 12, 8, 8)

        # Header
        hdr_row = QHBoxLayout()
        self.lbl_date = QLabel("📅 Chọn mục nhật kí hoặc tạo mới")
        self.lbl_date.setObjectName("accent")
        hdr_row.addWidget(self.lbl_date, 1)
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.setFixedHeight(32)
        hdr_row.addWidget(self.btn_save)
        rv.addLayout(hdr_row)

        # Text editor
        lbl_text = QLabel("✍️ Nội dung nhật kí:")
        lbl_text.setObjectName("h3")
        rv.addWidget(lbl_text)
        self.inp_text = QTextEdit()
        self.inp_text.setPlaceholderText(
            "Hôm nay bạn đã học gì?\n"
            "Ghi chú lại cảm nhận, kiến thức mới, từ vựng đã học..."
        )
        rv.addWidget(self.inp_text, 1)

        # Record section
        rec_group = QGroupBox("🎙 Ghi âm nhật kí")
        rg = QHBoxLayout(rec_group)
        self.btn_record = QPushButton("🔴")
        self.btn_record.setObjectName("recordBtn")
        self.btn_record.setToolTip("Bắt đầu / Dừng ghi âm nhật kí")
        self.lbl_rec = QLabel("Sẵn sàng ghi âm")
        self.lbl_rec.setObjectName("muted")
        self.lbl_audio_file = QLabel("")
        self.lbl_audio_file.setObjectName("muted")
        self.lbl_audio_file.setWordWrap(True)
        rg.addWidget(self.btn_record)
        rg.addWidget(self.lbl_rec)
        rg.addWidget(self.lbl_audio_file, 1)
        rv.addWidget(rec_group)

        # Audio player for playing diary recordings
        self.player_bar = AudioPlayerBar()
        rv.addWidget(self.player_bar)

        splitter.addWidget(right)
        splitter.setSizes([280, 600])

        # Connections
        self.btn_new.clicked.connect(self._new_entry)
        self.btn_delete.clicked.connect(self._delete_entry)
        self.btn_save.clicked.connect(self._save_entry)
        self.btn_record.clicked.connect(self._toggle_record)

        self._refresh_list()

    # ─── List ─────────────────────────────────────────────────────────

    def _refresh_list(self, *_):
        session = get_session()
        try:
            q = session.query(NhatKi)
            cd = self.topic_bar.get_chu_de_id()
            ch = self.topic_bar.get_chuong_id()
            bai = self.topic_bar.get_bai_id()
            if bai:
                q = q.filter(NhatKi.bai_id == bai)
            elif ch:
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter((NhatKi.chuong_id == ch) | (NhatKi.bai_id.in_(bids)))
            elif cd:
                cids = [c.id for c in session.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter((NhatKi.chu_de_id == cd) | (NhatKi.chuong_id.in_(cids)) | (NhatKi.bai_id.in_(bids)))
            entries = q.order_by(NhatKi.ngay.desc()).all()
            self.diary_list.clear()
            for e in entries:
                icon = "🎙" if e.loai == "record" else "📝"
                date_str = e.ngay.strftime("%d/%m/%Y %H:%M") if e.ngay else "?"
                preview = ""
                if e.noi_dung:
                    preview = e.noi_dung[:45].replace("\n", " ")
                    if len(e.noi_dung) > 45:
                        preview += "..."
                item = QListWidgetItem(f"{icon} {date_str}\n{preview}")
                item.setData(Qt.ItemDataRole.UserRole, e.id)
                self.diary_list.addItem(item)
            self.lbl_entry_count.setText(f"{len(entries)} mục")
        finally:
            session.close()

    def _on_entry_selected(self, item):
        if not item:
            return
        eid = item.data(Qt.ItemDataRole.UserRole)
        self._current_id = eid
        session = get_session()
        try:
            e = session.get(NhatKi, eid)
            if not e:
                return
            self.inp_text.setPlainText(e.noi_dung or "")
            date_str = e.ngay.strftime("%d/%m/%Y  %H:%M") if e.ngay else "?"
            self.lbl_date.setText(f"📅 {date_str}")
            if e.audio_path and os.path.exists(e.audio_path):
                self.lbl_audio_file.setText(f"🎙 {os.path.basename(e.audio_path)}")
                self.player_bar.load(e.audio_path)
            else:
                self.lbl_audio_file.setText("")
        finally:
            session.close()

    # ─── CRUD ─────────────────────────────────────────────────────────

    def _new_entry(self):
        cd = self.topic_bar.get_chu_de_id()
        ch = self.topic_bar.get_chuong_id()
        bai = self.topic_bar.get_bai_id()

        if not cd and not ch and not bai:
            QMessageBox.warning(self, "Lỗi", "Chọn ít nhất Chủ đề, Chương hoặc Bài trước khi tạo nhật kí!")
            return

        session = get_session()
        try:
            e = NhatKi(
                noi_dung="",
                loai="text",
                ngay=datetime.datetime.now(),
                chu_de_id=cd if not ch and not bai else None,
                chuong_id=ch if not bai else None,
                bai_id=bai
            )
            session.add(e)
            session.commit()
            new_id = e.id
        finally:
            session.close()
        self._refresh_list()
        # Auto-select new entry
        for i in range(self.diary_list.count()):
            if self.diary_list.item(i).data(Qt.ItemDataRole.UserRole) == new_id:
                self.diary_list.setCurrentRow(i)
                break
        self.inp_text.clear()
        self.lbl_date.setText(f"📅 {datetime.datetime.now().strftime('%d/%m/%Y  %H:%M')}")
        self.inp_text.setFocus()

    def _save_entry(self):
        if not self._current_id:
            QMessageBox.warning(self, "Lỗi", "Chọn hoặc tạo nhật kí trước!")
            return
        session = get_session()
        try:
            e = session.get(NhatKi, self._current_id)
            if e:
                e.noi_dung = self.inp_text.toPlainText()
                session.commit()
        finally:
            session.close()
        self._refresh_list()

    def _delete_entry(self):
        if not self._current_id:
            return
        if QMessageBox.question(self, "Xóa", "Xóa nhật kí này?") == QMessageBox.StandardButton.Yes:
            # Dừng trình phát để nhả file (tránh lỗi file đang được sử dụng)
            self.player_bar._stop()
            session = get_session()
            try:
                e = session.get(NhatKi, self._current_id)
                if e:
                    if e.audio_path and os.path.exists(e.audio_path):
                        try:
                            os.remove(e.audio_path)
                        except OSError:
                            pass
                    session.delete(e)
                    session.commit()
            finally:
                session.close()
            self._current_id = None
            self.inp_text.clear()
            self.lbl_date.setText("📅 Chọn mục nhật kí hoặc tạo mới")
            self.lbl_audio_file.setText("")
            self._refresh_list()

    # ─── Recording ────────────────────────────────────────────────────

    def _toggle_record(self):
        if self.recorder.is_recording():
            out = self.recorder.stop()
            self._rec_timer.stop()
            self._rec_seconds = 0
            self.btn_record.setProperty("recording", "false")
            self.btn_record.style().unpolish(self.btn_record)
            self.btn_record.style().polish(self.btn_record)
            self.lbl_rec.setText("✅ Đã lưu ghi âm")
            if self._current_id and out and os.path.exists(out):
                session = get_session()
                try:
                    e = session.get(NhatKi, self._current_id)
                    if e:
                        e.audio_path = out
                        e.loai = "record"
                        session.commit()
                        self.lbl_audio_file.setText(f"🎙 {os.path.basename(out)}")
                        self.player_bar.load(out)
                finally:
                    session.close()
            self._refresh_list()
        else:
            if not self._current_id:
                QMessageBox.warning(self, "Lỗi", "Chọn hoặc tạo nhật kí trước khi ghi âm!")
                return
            out_path = os.path.join(get_diary_audio_dir(), f"diary_{int(time.time())}.wav")
            try:
                self.recorder.start(out_path)
                self.btn_record.setProperty("recording", "true")
                self.btn_record.style().unpolish(self.btn_record)
                self.btn_record.style().polish(self.btn_record)
                self.lbl_rec.setText("🔴 Đang ghi âm 0s")
                self._rec_seconds = 0
                self._rec_timer.start()
            except RuntimeError as ex:
                QMessageBox.critical(self, "Lỗi ghi âm", str(ex))

    def _update_rec_time(self):
        self._rec_seconds += 1
        m = self._rec_seconds // 60
        s = self._rec_seconds % 60
        self.lbl_rec.setText(f"🔴 Đang ghi âm {m:02d}:{s:02d}")
