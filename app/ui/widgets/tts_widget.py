"""
app/ui/widgets/tts_widget.py — TTS / Ghi âm module

Tính năng:
  - Khi phát audio: hiển thị nội dung + bản dịch ngay dưới ô văn bản
  - Bản dịch được lưu vào DB, chỉ cập nhật khi nhấn Sửa → Lưu
  - Tạo audio mới → dừng audio đang phát + xóa nội dung ô nhập
"""
import os
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QTextEdit,
    QLineEdit, QSpinBox, QSplitter, QGroupBox, QDialog,
    QFormLayout, QDialogButtonBox, QCheckBox, QMessageBox,
    QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer

from app.data.database import get_session, Audio, Bai, Chuong, ChuDe
from app.core.workers import TTSWorker, BatchTTSWorker, AudioRecorder, TTS_VOICE_CHOICES, TranslateWorker
from app.ui.widgets.common import AudioPlayerBar


def get_media_dir():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    d = os.path.join(base, "media", "audio")
    os.makedirs(d, exist_ok=True)
    return d


class TTSWidget(QWidget):
    """TTS + Ghi âm panel"""

    def __init__(self, topic_bar, parent=None):
        super().__init__(parent)
        self.topic_bar = topic_bar
        self.recorder  = AudioRecorder()

        self._tts_worker       = None
        self._translate_worker = None
        self._batch_entries    = []
        self._current_audio_id = None
        self._editing_audio_id = None
        self._playing_audio_id = None
        self._rec_seconds      = 0
        self._pending_translation = ""

        self._build_ui()
        topic_bar.selection_changed.connect(self._refresh_list)

    # ══════════════════════════════════════════════════════════════════
    #  UI
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # ── LEFT: danh sách audio ─────────────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setSpacing(6)
        lv.setContentsMargins(8, 8, 4, 8)

        lv.addWidget(QLabel("📋 Danh sách Audio"))
        self.audio_list = QListWidget()
        self.audio_list.currentItemChanged.connect(self._on_audio_selected)
        self.audio_list.itemDoubleClicked.connect(self._play_selected)
        lv.addWidget(self.audio_list, 1)

        list_btns = QHBoxLayout()
        self.btn_play_audio   = QPushButton("▶ Phát")
        self.btn_delete_audio = QPushButton("🗑 Xóa")
        self.btn_edit_audio   = QPushButton("✏️ Sửa")
        for b in [self.btn_play_audio, self.btn_delete_audio, self.btn_edit_audio]:
            b.setFixedHeight(28)
            list_btns.addWidget(b)
        lv.addLayout(list_btns)

        self.lbl_audio_count = QLabel("0 audio")
        self.lbl_audio_count.setObjectName("muted")
        lv.addWidget(self.lbl_audio_count)

        splitter.addWidget(left)

        # ── RIGHT: TTS settings + ghi âm ─────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setSpacing(8)
        rv.setContentsMargins(4, 8, 8, 8)

        # ── TTS group ─────────────────────────────────────────────────
        tts_group = QGroupBox("🔊 Tạo Audio TTS")
        tg = QVBoxLayout(tts_group)
        tg.setSpacing(6)

        form_row1 = QHBoxLayout()
        form_row1.addWidget(QLabel("Tên audio:"))
        self.inp_title = QLineEdit("English_Audio")
        form_row1.addWidget(self.inp_title, 1)
        tg.addLayout(form_row1)

        batch_row = QHBoxLayout()
        self.chk_batch = QCheckBox("Batch (nhiều audio theo dòng)")
        self.spin_lines = QSpinBox()
        self.spin_lines.setRange(1, 20)
        self.spin_lines.setValue(1)
        self.spin_lines.setEnabled(False)
        self.chk_batch.toggled.connect(self.spin_lines.setEnabled)
        batch_row.addWidget(self.chk_batch)
        batch_row.addWidget(QLabel("Dòng/audio:"))
        batch_row.addWidget(self.spin_lines)
        batch_row.addStretch()
        tg.addLayout(batch_row)

        lang_voice_row = QHBoxLayout()
        self.cb_lang = QComboBox()
        self.cb_lang.addItem("Tiếng Việt", "vi")
        self.cb_lang.addItem("Tiếng Anh", "en")
        self.cb_voice = QComboBox()
        for name, vid in TTS_VOICE_CHOICES:
            self.cb_voice.addItem(name, vid)
        self.cb_lang.currentIndexChanged.connect(self._filter_voices)
        lang_voice_row.addWidget(QLabel("Ngôn ngữ:"))
        lang_voice_row.addWidget(self.cb_lang)
        lang_voice_row.addWidget(QLabel("Giọng:"))
        lang_voice_row.addWidget(self.cb_voice, 1)
        tg.addLayout(lang_voice_row)

        tg.addWidget(QLabel("Nội dung văn bản:"))
        self.inp_text = QTextEdit()
        self.inp_text.setPlaceholderText("Nhập văn bản cần chuyển thành audio...")
        self.inp_text.setMinimumHeight(100)
        tg.addWidget(self.inp_text, 1)

        # ── Khung hiển thị audio đang phát ────────────────────────────
        self.frame_playing = QFrame()
        self.frame_playing.setStyleSheet(
            "QFrame { background:#0a0a1e; border:1px solid #2a2a5a; border-radius:7px; }"
        )
        playing_layout = QVBoxLayout(self.frame_playing)
        playing_layout.setSpacing(4)
        playing_layout.setContentsMargins(10, 8, 10, 8)

        playing_header = QHBoxLayout()
        self.lbl_playing_icon = QLabel("▶")
        self.lbl_playing_icon.setStyleSheet("color:#5cff8c; font-size:13px;")
        self.lbl_playing_name = QLabel("Đang phát:")
        self.lbl_playing_name.setStyleSheet(
            "color:#5cff8c; font-weight:bold; font-size:12px;"
        )
        playing_header.addWidget(self.lbl_playing_icon)
        playing_header.addWidget(self.lbl_playing_name)
        playing_header.addStretch()
        playing_layout.addLayout(playing_header)

        self.lbl_playing_content = QLabel("")
        self.lbl_playing_content.setWordWrap(True)
        self.lbl_playing_content.setStyleSheet("color:#d0d0f0; font-size:12px; padding:2px 4px;")
        self.lbl_playing_content.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        playing_layout.addWidget(self.lbl_playing_content)

        self.sep_translation = QFrame()
        self.sep_translation.setFrameShape(QFrame.Shape.HLine)
        self.sep_translation.setStyleSheet("background:#2a2a5a; max-height:1px;")
        playing_layout.addWidget(self.sep_translation)

        self.lbl_playing_translation = QLabel("")
        self.lbl_playing_translation.setWordWrap(True)
        self.lbl_playing_translation.setStyleSheet(
            "color:#aaaaff; font-style:italic; font-size:11px; padding:2px 4px;"
        )
        self.lbl_playing_translation.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        playing_layout.addWidget(self.lbl_playing_translation)

        self.frame_playing.hide()
        tg.addWidget(self.frame_playing)

        # ── Bản dịch preview (khi đang soạn) ──────────────────────────
        self.lbl_translation_preview = QLabel("")
        self.lbl_translation_preview.setWordWrap(True)
        self.lbl_translation_preview.setStyleSheet(
            "color:#8888cc; font-style:italic; font-size:11px;"
            "background:#0d0d20; border-left:3px solid #3a3a6a;"
            "padding:6px 8px; border-radius:4px;"
        )
        self.lbl_translation_preview.hide()
        tg.addWidget(self.lbl_translation_preview)

        self._translate_timer = QTimer()
        self._translate_timer.setSingleShot(True)
        self._translate_timer.setInterval(800)
        self._translate_timer.timeout.connect(self._do_translate_preview)

        # ── Buttons ────────────────────────────────────────────────────
        tts_btn_row = QHBoxLayout()
        self.btn_tts_create = QPushButton("🔊 Tạo TTS")
        self.btn_tts_create.setObjectName("primaryBtn")
        self.btn_tts_update = QPushButton("💾 Ghi đè (Update)")
        self.btn_tts_update.setEnabled(False)
        self.btn_import_txt = QPushButton("📄 Import TXT")
        self.lbl_tts_status = QLabel("")
        self.lbl_tts_status.setObjectName("muted")
        tts_btn_row.addWidget(self.btn_tts_create)
        tts_btn_row.addWidget(self.btn_tts_update)
        tts_btn_row.addWidget(self.btn_import_txt)
        tts_btn_row.addWidget(self.lbl_tts_status, 1)
        tg.addLayout(tts_btn_row)

        rv.addWidget(tts_group)

        # ── Record section ─────────────────────────────────────────────
        rec_group = QGroupBox("🎙 Ghi Âm")
        rg = QHBoxLayout(rec_group)

        self.cb_mic = QComboBox()
        mics = self.recorder.list_input_devices()
        if not mics:
            self.cb_mic.addItem("Không tìm thấy Mic", -1)
        else:
            for i, name in mics:
                self.cb_mic.addItem(name, i)

        self.btn_record = QPushButton("🔴")
        self.btn_record.setObjectName("recordBtn")
        self.btn_record.setToolTip("Bắt đầu / Dừng ghi âm")
        self.lbl_rec_status = QLabel("Sẵn sàng ghi âm")
        self.lbl_rec_status.setObjectName("muted")
        self._rec_timer = QTimer()
        self._rec_timer.setInterval(1000)
        self._rec_timer.timeout.connect(self._update_rec_time)

        rg.addWidget(QLabel("Mic:"))
        rg.addWidget(self.cb_mic)
        rg.addWidget(self.btn_record)
        rg.addWidget(self.lbl_rec_status, 1)
        rv.addWidget(rec_group)

        # ── Player bar ─────────────────────────────────────────────────
        self.player_bar = AudioPlayerBar()
        self.player_bar.btn_prev.clicked.connect(self._play_prev)
        self.player_bar.btn_next.clicked.connect(self._play_next)
        self.player_bar.play_next_requested.connect(self._on_play_next_requested)
        rv.addWidget(self.player_bar)

        splitter.addWidget(right)
        splitter.setSizes([280, 600])

        # ── Connections ────────────────────────────────────────────────
        self.btn_tts_create.clicked.connect(self._create_tts)
        self.btn_tts_update.clicked.connect(self._update_audio)
        self.btn_import_txt.clicked.connect(self._import_txt)
        self.btn_play_audio.clicked.connect(self._play_selected)
        self.btn_delete_audio.clicked.connect(self._delete_audio)
        self.btn_edit_audio.clicked.connect(self._edit_audio)
        self.btn_record.clicked.connect(self._toggle_record)
        self.inp_text.textChanged.connect(self._on_text_changed)

        self._filter_voices()
        self._refresh_list()

    # ══════════════════════════════════════════════════════════════════
    #  Playing info display
    # ══════════════════════════════════════════════════════════════════

    def _show_playing_info(self, audio_id: int):
        self._playing_audio_id = audio_id
        session = get_session()
        try:
            a = session.get(Audio, audio_id)
            if not a:
                self.frame_playing.hide()
                return
            name        = a.ten or ""
            content     = (a.noi_dung or "").strip()
            translation = (a.ban_dich or "").strip()

            self.lbl_playing_name.setText(f"▶ {name}")

            if content:
                preview = content[:300] + ("…" if len(content) > 300 else "")
                self.lbl_playing_content.setText(preview)
                self.lbl_playing_content.show()
            else:
                self.lbl_playing_content.hide()

            if translation:
                self.lbl_playing_translation.setText(f"🇻🇳 {translation}")
                self.lbl_playing_translation.show()
                self.sep_translation.show()
            else:
                self.lbl_playing_translation.hide()
                self.sep_translation.hide()

            self.frame_playing.show()
        finally:
            session.close()

    def _hide_playing_info(self):
        self._playing_audio_id = None
        self.frame_playing.hide()

    # ══════════════════════════════════════════════════════════════════
    #  Translation preview
    # ══════════════════════════════════════════════════════════════════

    def _on_text_changed(self):
        if self.cb_lang.currentData() != "en":
            self.lbl_translation_preview.hide()
            self._pending_translation = ""
            return
        text = self.inp_text.toPlainText().strip()
        if not text:
            self.lbl_translation_preview.hide()
            self._pending_translation = ""
            return
        self.lbl_translation_preview.setText("⏳ Đang dịch...")
        self.lbl_translation_preview.show()
        self._translate_timer.start()

    def _do_translate_preview(self):
        text = self.inp_text.toPlainText().strip()
        if not text:
            self.lbl_translation_preview.hide()
            return
        if self._translate_worker and self._translate_worker.isRunning():
            self._translate_worker.quit()
        w = TranslateWorker(text, src="en", dest="vi")
        w.finished.connect(self._on_translation_preview_done)
        w.error.connect(lambda e: self.lbl_translation_preview.setText(f"⚠ Lỗi dịch: {e}"))
        w.start()
        self._translate_worker = w

    def _on_translation_preview_done(self, translated: str):
        self._pending_translation = translated
        if translated:
            self.lbl_translation_preview.setText(f"🇻🇳 {translated}")
            self.lbl_translation_preview.show()
        else:
            self.lbl_translation_preview.hide()

    # ══════════════════════════════════════════════════════════════════
    #  Voice filter
    # ══════════════════════════════════════════════════════════════════

    def _filter_voices(self):
        lang = self.cb_lang.currentData()
        self.cb_voice.clear()
        for name, vid in TTS_VOICE_CHOICES:
            if lang == "vi" and (vid.startswith("vi-") or vid == "gtts:vi"):
                self.cb_voice.addItem(name, vid)
            elif lang == "en" and not vid.startswith("vi-") and not vid.startswith("gtts:"):
                self.cb_voice.addItem(name, vid)
        self._update_auto_name()
        if lang != "en":
            self.lbl_translation_preview.hide()
            self._pending_translation = ""
        else:
            self._on_text_changed()

    def _update_auto_name(self):
        n = self.audio_list.count() + 1
        self.inp_title.setText(f"audio_{n}")

    # ══════════════════════════════════════════════════════════════════
    #  Audio list
    # ══════════════════════════════════════════════════════════════════

    def _refresh_list(self, *_):
        session = get_session()
        try:
            q   = session.query(Audio)
            cd  = self.topic_bar.get_chu_de_id()
            ch  = self.topic_bar.get_chuong_id()
            bai = self.topic_bar.get_bai_id()
            if bai:
                q = q.filter(Audio.bai_id == bai)
            elif ch:
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter(Audio.bai_id.in_(bids))
            elif cd:
                cids = [c.id for c in session.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter(Audio.bai_id.in_(bids))
            audios = q.order_by(Audio.tao_luc).all()
            self.audio_list.clear()
            for a in audios:
                icon = "🎙" if a.loai == "record" else "🔊"
                item = QListWidgetItem(f"{icon} {a.ten}")
                item.setData(Qt.ItemDataRole.UserRole, a.id)
                self.audio_list.addItem(item)
            self.lbl_audio_count.setText(f"{len(audios)} audio")
            self._update_auto_name()
        finally:
            session.close()

    def _on_audio_selected(self, item):
        if item:
            self._current_audio_id = item.data(Qt.ItemDataRole.UserRole)

    def _play_selected(self, *_):
        if not self._current_audio_id:
            return
        session = get_session()
        try:
            a = session.get(Audio, self._current_audio_id)
            if a and a.duong_dan and os.path.exists(a.duong_dan):
                self.player_bar.load(a.duong_dan, media_id=a.id, media_type="audio")
                self._show_playing_info(a.id)
            elif a and a.duong_dan:
                self.lbl_tts_status.setText(f"⚠ File không tồn tại: {a.duong_dan}")
        finally:
            session.close()

    def _play_prev(self):
        row = self.audio_list.currentRow()
        if row > 0:
            self.audio_list.setCurrentRow(row - 1)
            self._play_selected()

    def _play_next(self):
        row = self.audio_list.currentRow()
        if row < self.audio_list.count() - 1:
            self.audio_list.setCurrentRow(row + 1)
            self._play_selected()

    def _on_play_next_requested(self, loop_all: bool):
        row = self.audio_list.currentRow()
        if row < self.audio_list.count() - 1:
            self.audio_list.setCurrentRow(row + 1)
            self._play_selected()
        elif loop_all and self.audio_list.count() > 0:
            self.audio_list.setCurrentRow(0)
            self._play_selected()

    def _delete_audio(self):
        if not self._current_audio_id:
            return
        if QMessageBox.question(self, "Xóa", "Xóa audio này?") == QMessageBox.StandardButton.Yes:
            if self._playing_audio_id == self._current_audio_id:
                self._pause_current()
                self._hide_playing_info()
            session = get_session()
            try:
                a = session.get(Audio, self._current_audio_id)
                if a:
                    if a.duong_dan and os.path.exists(a.duong_dan):
                        try:
                            os.remove(a.duong_dan)
                        except OSError:
                            pass
                    session.delete(a)
                    session.commit()
            finally:
                session.close()
            self._current_audio_id = None
            self._refresh_list()

    # ══════════════════════════════════════════════════════════════════
    #  Edit mode
    # ══════════════════════════════════════════════════════════════════

    def _edit_audio(self):
        if not self._current_audio_id:
            return
        session = get_session()
        try:
            a = session.get(Audio, self._current_audio_id)
            if not a:
                return
            self._editing_audio_id = a.id
            self.inp_title.setText(a.ten or "")
            if a.noi_dung:
                self.inp_text.blockSignals(True)
                self.inp_text.setPlainText(a.noi_dung)
                self.inp_text.blockSignals(False)
            if a.ngon_ngu:
                idx = self.cb_lang.findData(a.ngon_ngu)
                if idx >= 0:
                    self.cb_lang.setCurrentIndex(idx)
            if a.giong_doc:
                idx = self.cb_voice.findData(a.giong_doc)
                if idx >= 0:
                    self.cb_voice.setCurrentIndex(idx)

            saved_translation = (a.ban_dich or "").strip()
            if saved_translation:
                self._pending_translation = saved_translation
                self.lbl_translation_preview.setText(f"🇻🇳 {saved_translation}  *(đã lưu)*")
                self.lbl_translation_preview.show()
            else:
                self._pending_translation = ""
                self.lbl_translation_preview.hide()

            self.btn_tts_update.setEnabled(True)
            self.btn_tts_create.setText("❌ Hủy sửa")
            self.lbl_tts_status.setText(f"Đang sửa: {a.ten}")
        finally:
            session.close()

    def _update_audio(self):
        if not self._editing_audio_id:
            return
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Chọn Bài trước!")
            return
        text = self.inp_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Lỗi", "Nhập văn bản!")
            return

        self.btn_tts_create.setEnabled(False)
        self.btn_tts_update.setEnabled(False)
        self.lbl_tts_status.setText("Đang tạo TTS ghi đè...")

        media_dir = get_media_dir()
        out_path  = os.path.join(media_dir, f"tts_update_{int(time.time())}.mp3")
        voice     = self.cb_voice.currentData()
        lang      = self.cb_lang.currentData()
        translation_to_save = self._pending_translation

        w = TTSWorker(text, voice, out_path)
        w.finished.connect(
            lambda p: self._on_update_done(p, text, voice, lang, translation_to_save)
        )
        w.error.connect(lambda e: (
            self.lbl_tts_status.setText(f"Lỗi: {e}"),
            self.btn_tts_create.setEnabled(True),
            self.btn_tts_update.setEnabled(True),
        ))
        w.start()
        self._tts_worker = w

    def _on_update_done(self, file_path: str, text: str, voice: str,
                         lang: str, translation: str):
        self.btn_tts_create.setEnabled(True)
        self.btn_tts_update.setEnabled(False)
        self.lbl_tts_status.setText("✅ Đã cập nhật xong")

        saved_id = None
        session = get_session()
        try:
            a = session.get(Audio, self._editing_audio_id)
            if a:
                if a.duong_dan and os.path.exists(a.duong_dan):
                    try:
                        os.remove(a.duong_dan)
                    except:
                        pass
                a.ten       = self.inp_title.text().strip() or a.ten
                a.duong_dan = file_path
                a.loai      = "tts"
                a.noi_dung  = text
                a.ban_dich  = translation
                a.ngon_ngu  = lang
                a.giong_doc = voice
                session.commit()
                saved_id = a.id
        finally:
            session.close()

        if saved_id and self._playing_audio_id == saved_id:
            self._show_playing_info(saved_id)

        self._editing_audio_id    = None
        self._pending_translation = ""
        self.inp_title.clear()
        self.inp_text.clear()
        self.lbl_translation_preview.hide()
        self.btn_tts_create.setText("🔊 Tạo TTS")
        self._update_auto_name()
        self._refresh_list()

    # ══════════════════════════════════════════════════════════════════
    #  TTS creation
    # ══════════════════════════════════════════════════════════════════

    def _create_tts(self):
        # Chế độ hủy sửa
        if self._editing_audio_id:
            self._editing_audio_id    = None
            self._pending_translation = ""
            self.inp_title.clear()
            self.inp_text.clear()
            self.lbl_translation_preview.hide()
            self.btn_tts_update.setEnabled(False)
            self.btn_tts_create.setText("🔊 Tạo TTS")
            self.lbl_tts_status.setText("Đã hủy chế độ sửa.")
            self._update_auto_name()
            return

        text = self.inp_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập văn bản!")
            return
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn Bài trước khi tạo TTS!")
            return
        voice = self.cb_voice.currentData()
        if not voice:
            QMessageBox.warning(self, "Lỗi", "Chọn giọng đọc!")
            return

        # Dừng audio đang phát
        self._pause_current()
        self._hide_playing_info()

        title      = self.inp_title.text().strip() or "audio"
        lang       = self.cb_lang.currentData()
        media_dir  = get_media_dir()
        translation_to_save = self._pending_translation

        if self.chk_batch.isChecked():
            lines_per = self.spin_lines.value()
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if not lines:
                QMessageBox.warning(self, "Lỗi", "Không có dòng nào để batch!")
                return
            entries = []
            ts = int(time.time())
            for i in range(0, len(lines), lines_per):
                chunk = "\n".join(lines[i:i + lines_per])
                t = f"{title}_{i // lines_per + 1:03d}"
                entries.append({
                    "title":       t,
                    "text":        chunk,
                    "voice":       voice,
                    "output_path": os.path.join(media_dir, f"{t}_{ts}_{i}.mp3"),
                    "bai_id":      bai_id,
                    "lang":        lang,
                    "translation": "",
                })
            self._batch_entries = entries
            self.btn_tts_create.setEnabled(False)
            self.lbl_tts_status.setText("Đang tạo batch TTS...")
            worker = BatchTTSWorker(entries)
            worker.progress.connect(lambda s: self.lbl_tts_status.setText(s))
            worker.finished.connect(self._on_batch_done)
            worker.error.connect(self._on_tts_error)
            worker.start()
            self._tts_worker = worker
        else:
            ts       = int(time.time())
            out_path = os.path.join(media_dir, f"{title}_{ts}.mp3")
            self.btn_tts_create.setEnabled(False)
            self.lbl_tts_status.setText("Đang tạo TTS...")
            worker = TTSWorker(text, voice, out_path)
            worker.finished.connect(
                lambda p: self._save_audio_record(
                    title, p, bai_id, "tts", text, voice, lang, translation_to_save
                )
            )
            worker.error.connect(self._on_tts_error)
            worker.start()
            self._tts_worker = worker

    def _on_tts_error(self, msg: str):
        QMessageBox.critical(self, "Lỗi TTS", msg)
        self.btn_tts_create.setEnabled(True)
        self.lbl_tts_status.setText("")

    def _save_audio_record(self, title, path, bai_id, loai,
                            text="", voice="", lang="en", translation=""):
        session = get_session()
        try:
            a = Audio(
                ten=title, duong_dan=path, loai=loai,
                noi_dung=text, ban_dich=translation,
                giong_doc=voice, ngon_ngu=lang,
                bai_id=bai_id,
            )
            session.add(a)
            session.commit()
        finally:
            session.close()
        self.lbl_tts_status.setText(f"✅ Đã tạo: {os.path.basename(path)}")
        self.btn_tts_create.setEnabled(True)
        # ← Xóa nội dung ô nhập sau khi tạo xong
        self.inp_text.clear()
        self._pending_translation = ""
        self.lbl_translation_preview.hide()
        self._update_auto_name()
        self._refresh_list()

    def _on_batch_done(self, paths):
        session = get_session()
        try:
            for i, e in enumerate(self._batch_entries):
                saved_path = paths[i] if i < len(paths) else e["output_path"]
                a = Audio(
                    ten=e["title"], duong_dan=saved_path, loai="tts",
                    noi_dung=e["text"], ban_dich=e.get("translation", ""),
                    giong_doc=e["voice"], ngon_ngu=e["lang"],
                    bai_id=e["bai_id"],
                )
                session.add(a)
            session.commit()
        finally:
            session.close()
        self.lbl_tts_status.setText(f"✅ Batch hoàn thành ({len(paths)} audio)")
        self.btn_tts_create.setEnabled(True)
        # ← Xóa nội dung ô nhập sau khi batch xong
        self.inp_text.clear()
        self._pending_translation = ""
        self.lbl_translation_preview.hide()
        self._update_auto_name()
        self._refresh_list()

    def _import_txt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file TXT", "", "Text (*.txt)")
        if path:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    self.inp_text.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Lỗi đọc file", str(e))

    # ══════════════════════════════════════════════════════════════════
    #  Recording
    # ══════════════════════════════════════════════════════════════════

    def _toggle_record(self):
        if self.recorder.is_recording():
            out = self.recorder.stop()
            self._rec_timer.stop()
            self._rec_seconds = 0
            self.btn_record.setProperty("recording", "false")
            self.btn_record.style().unpolish(self.btn_record)
            self.btn_record.style().polish(self.btn_record)
            self.lbl_rec_status.setText("✅ Đã lưu ghi âm")
            bai_id = self.topic_bar.get_bai_id()
            if bai_id and out and os.path.exists(out):
                rec_name = self.inp_title.text().strip() or "record"
                if self._editing_audio_id:
                    session = get_session()
                    try:
                        a = session.get(Audio, self._editing_audio_id)
                        if a:
                            if a.duong_dan and os.path.exists(a.duong_dan):
                                try:
                                    os.remove(a.duong_dan)
                                except:
                                    pass
                            a.ten       = rec_name
                            a.duong_dan = out
                            a.loai      = "record"
                            a.noi_dung  = self.inp_text.toPlainText().strip()
                            a.ban_dich  = self._pending_translation
                            a.ngon_ngu  = self.cb_lang.currentData()
                            a.giong_doc = ""
                            session.commit()
                            self._editing_audio_id    = None
                            self._pending_translation = ""
                            self.btn_tts_update.setEnabled(False)
                            self.btn_tts_create.setText("🔊 Tạo TTS")
                            self.lbl_translation_preview.hide()
                            self._update_auto_name()
                    finally:
                        session.close()
                    self._refresh_list()
                else:
                    # Tạo mới → dừng phát + clear ô nhập
                    self._pause_current()
                    self._hide_playing_info()
                    self._save_audio_record(
                        rec_name, out, bai_id, "record",
                        text=self.inp_text.toPlainText().strip(),
                        translation=self._pending_translation,
                    )
        else:
            bai_id = self.topic_bar.get_bai_id()
            if not bai_id:
                QMessageBox.warning(self, "Lỗi", "Chọn Bài trước khi ghi âm!")
                return
            mic_id = self.cb_mic.currentData()
            if mic_id == -1:
                QMessageBox.warning(self, "Lỗi", "Không có Microphone!")
                return
            media_dir = get_media_dir()
            rec_name  = self.inp_title.text().strip() or "record"
            out_path  = os.path.join(media_dir, f"{rec_name}_{int(time.time())}.wav")
            try:
                self.recorder.start(out_path, device_index=mic_id)
                self.btn_record.setProperty("recording", "true")
                self.btn_record.style().unpolish(self.btn_record)
                self.btn_record.style().polish(self.btn_record)
                self.lbl_rec_status.setText("🔴 Đang ghi âm 0s")
                self._rec_seconds = 0
                self._rec_timer.start()
            except RuntimeError as e:
                QMessageBox.critical(self, "Lỗi ghi âm", str(e))

    def _update_rec_time(self):
        self._rec_seconds += 1
        self.lbl_rec_status.setText(f"🔴 Đang ghi âm {self._rec_seconds}s")

    # ══════════════════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════════════════

    def _pause_current(self):
        try:
            if hasattr(self.player_bar, "_pause"):
                self.player_bar._pause()
            elif hasattr(self.player_bar, "stop"):
                self.player_bar.stop()
        except Exception:
            pass
