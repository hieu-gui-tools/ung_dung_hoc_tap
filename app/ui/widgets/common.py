"""
app/ui/widgets/common.py — TopicBar, AudioPlayer widget dùng chung
"""
import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QFrame, QSizePolicy, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QObject, QUrl
from app.data.database import get_session, ChuDe, Chuong, Bai, DoanLap

class TopicBar(QWidget):
    """3-column topic selector: Chủ đề / Chương / Bài + Add/Delete/Edit buttons"""
    selection_changed = Signal(int, int, int)   # chu_de_id, chuong_id, bai_id
    add_requested    = Signal(str)   # "chu_de" | "chuong" | "bai"
    delete_requested = Signal(str)
    edit_requested   = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topicBar")
        self._chu_de_data = []   # list of (id, ten)
        self._chuong_data = []
        self._bai_data    = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(8, 6, 8, 6)

        # Main horizontal layout
        h_layout = QHBoxLayout()
        h_layout.setSpacing(8)

        self.cb_chu_de = QComboBox(); self.cb_chu_de.addItem("-- Tất cả --", 0)
        self.cb_chuong = QComboBox(); self.cb_chuong.addItem("-- Tất cả --", 0)
        self.cb_bai    = QComboBox(); self.cb_bai.addItem("-- Tất cả --", 0)

        levels = [
            ("Chủ đề", self.cb_chu_de, "chu_de"),
            ("Chương", self.cb_chuong, "chuong"),
            ("Bài", self.cb_bai, "bai")
        ]

        for lbl_text, cb, level_id in levels:
            v = QVBoxLayout()
            v.setSpacing(2)
            l = QLabel(lbl_text)
            l.setObjectName("h3")
            v.addWidget(l)
            
            row_h = QHBoxLayout()
            row_h.setSpacing(2)
            cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cb.setMinimumHeight(30)
            row_h.addWidget(cb, 1)

            btn_add = QPushButton("➕")
            btn_add.setToolTip(f"Thêm {lbl_text}")
            btn_add.setFixedSize(30, 30)
            btn_add.setStyleSheet("padding: 0;")
            btn_add.clicked.connect(lambda _, lvl=level_id: self.add_requested.emit(lvl))
            
            btn_edit = QPushButton("✏️")
            btn_edit.setToolTip(f"Sửa {lbl_text}")
            btn_edit.setFixedSize(30, 30)
            btn_edit.setStyleSheet("padding: 0;")
            btn_edit.clicked.connect(lambda _, lvl=level_id: self.edit_requested.emit(lvl))
            
            btn_delete = QPushButton("🗑️")
            btn_delete.setToolTip(f"Xóa {lbl_text}")
            btn_delete.setFixedSize(30, 30)
            btn_delete.setStyleSheet("padding: 0;")
            btn_delete.clicked.connect(lambda _, lvl=level_id: self.delete_requested.emit(lvl))
            
            row_h.addWidget(btn_add)
            row_h.addWidget(btn_edit)
            row_h.addWidget(btn_delete)
            
            v.addLayout(row_h)
            h_layout.addLayout(v, 1)

        root.addLayout(h_layout)

        # Signals
        self.cb_chu_de.currentIndexChanged.connect(self._on_chu_de_changed)
        self.cb_chuong.currentIndexChanged.connect(self._on_chuong_changed)
        self.cb_bai.currentIndexChanged.connect(self._on_bai_changed)

    def load_data(self, chu_de_list, chuong_list, bai_list):
        self._target_chu_de = self.get_chu_de_id()
        self._target_chuong = self.get_chuong_id()
        self._target_bai    = self.get_bai_id()

        self._chu_de_data = chu_de_list
        self._chuong_data = chuong_list
        self._bai_data    = bai_list
        self._refresh_chu_de()

    def _refresh_chu_de(self):
        self.cb_chu_de.blockSignals(True)
        self.cb_chu_de.clear()
        self.cb_chu_de.addItem("-- Tất cả --", 0)
        for id_, ten in self._chu_de_data:
            self.cb_chu_de.addItem(ten, id_)
            
        idx = self.cb_chu_de.findData(getattr(self, '_target_chu_de', 0))
        if idx >= 0:
            self.cb_chu_de.setCurrentIndex(idx)
            self._target_chu_de = 0
            
        self.cb_chu_de.blockSignals(False)
        self._on_chu_de_changed()

    def _on_chu_de_changed(self, index=None):
        chu_de_id = self.cb_chu_de.currentData() or 0
        self.cb_chuong.blockSignals(True)
        self.cb_chuong.clear()
        self.cb_chuong.addItem("-- Tất cả --", 0)
        for id_, ten, parent_id in self._chuong_data:
            if chu_de_id == 0 or parent_id == chu_de_id:
                self.cb_chuong.addItem(ten, id_)
                
        idx = self.cb_chuong.findData(getattr(self, '_target_chuong', 0))
        if idx >= 0:
            self.cb_chuong.setCurrentIndex(idx)
            self._target_chuong = 0
            
        self.cb_chuong.blockSignals(False)
        self._on_chuong_changed()

    def _on_chuong_changed(self, index=None):
        chuong_id = self.cb_chuong.currentData() or 0
        chu_de_id = self.cb_chu_de.currentData() or 0
        
        # Auto-resolve parent chu_de if needed
        if chuong_id != 0:
            parent_chu_de_id = next((pid for cid, cname, pid in self._chuong_data if cid == chuong_id), 0)
            if parent_chu_de_id and self.cb_chu_de.currentData() != parent_chu_de_id:
                self._target_chuong = chuong_id
                idx = self.cb_chu_de.findData(parent_chu_de_id)
                if idx >= 0:
                    self.cb_chu_de.setCurrentIndex(idx)
                    return
        
        self.cb_bai.blockSignals(True)
        self.cb_bai.clear()
        self.cb_bai.addItem("-- Tất cả --", 0)
        visible_chuong_ids = {
            cid for cid, _ten, parent_id in self._chuong_data
            if chu_de_id == 0 or parent_id == chu_de_id
        }
        for id_, ten, parent_id in self._bai_data:
            if chuong_id != 0:
                visible = parent_id == chuong_id
            else:
                visible = chu_de_id == 0 or parent_id in visible_chuong_ids
            if visible:
                self.cb_bai.addItem(ten, id_)
                
        idx = self.cb_bai.findData(getattr(self, '_target_bai', 0))
        if idx >= 0:
            self.cb_bai.setCurrentIndex(idx)
            self._target_bai = 0
            
        self.cb_bai.blockSignals(False)
        self._emit_selection()

    def _on_bai_changed(self, index=None):
        bai_id = self.cb_bai.currentData() or 0
        
        # Auto-resolve parent chuong if needed
        if bai_id != 0:
            parent_chuong_id = next((pid for bid, bname, pid in self._bai_data if bid == bai_id), 0)
            if parent_chuong_id and self.cb_chuong.currentData() != parent_chuong_id:
                self._target_bai = bai_id
                idx = self.cb_chuong.findData(parent_chuong_id)
                if idx >= 0:
                    self.cb_chuong.setCurrentIndex(idx)
                    return
                    
        self._emit_selection()

    def _emit_selection(self):
        self.selection_changed.emit(
            self.cb_chu_de.currentData() or 0,
            self.cb_chuong.currentData() or 0,
            self.cb_bai.currentData() or 0,
        )

    def get_bai_id(self) -> int:
        return self.cb_bai.currentData() or 0

    def get_chuong_id(self) -> int:
        return self.cb_chuong.currentData() or 0

    def get_chu_de_id(self) -> int:
        return self.cb_chu_de.currentData() or 0

    def set_selection(self, chu_de_id=None, chuong_id=None, bai_id=None):
        """Đặt lại selection về chu_de/chuong/bai chỉ định (dùng để restore state)."""
        self._target_chu_de = chu_de_id or 0
        self._target_chuong = chuong_id or 0
        self._target_bai    = bai_id    or 0
        self._refresh_chu_de()


class MpvSignals(QObject):
    """Signals bridge: MPV observer threads → Qt main thread."""
    time_pos_changed = Signal(float)
    duration_changed = Signal(float)
    eof_reached      = Signal()
    pause_changed    = Signal(bool)


class AudioPlayerBar(QWidget):
    """
    Thanh phát audio dùng MPV.
    - Play/Pause hoạt động đúng sau khi file load xong
    - Tự phát bài tiếp theo khi hết (loop off / loop all)
    - _is_playing phản ánh state thực của MPV qua observer 'pause'
    """
    play_next_requested = Signal(bool)   # arg: loop_all
    playback_started    = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration_ms  = 0
        self._ab_a         = None
        self._ab_b         = None
        self._dragging     = False
        self._loop_state   = 0   # 0=Off 1=Loop1 2=LoopAll
        self._media_id     = None
        self._media_type   = None
        self._is_playing   = False
        self._file_loaded  = False   # True sau khi MPV báo duration > 0
        self._current_path = None    # path/url đang phát, dùng cho loop 1 bài

        self._build_ui()
        self._init_mpv()

    # ── MPV init ──────────────────────────────────────────────────────

    def _init_mpv(self):
        try:
            import os as _os
            root_dir = _os.path.dirname(
                _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
            )
            _os.environ["PATH"] = root_dir + _os.pathsep + _os.environ.get("PATH", "")
            import mpv
            # KHÔNG dùng keep_open=True — nó ngăn end-file event khi hết bài
            self.player = mpv.MPV(ytdl=True)
            self.player.volume = 90

            self._sig = MpvSignals()
            self._sig.time_pos_changed.connect(self._on_time_pos)
            self._sig.duration_changed.connect(self._on_duration)
            self._sig.eof_reached.connect(self._on_eof)
            self._sig.pause_changed.connect(self._on_pause_changed)

            @self.player.property_observer('time-pos')
            def _obs_time(_name, value):
                if value is not None:
                    self._sig.time_pos_changed.emit(float(value))

            @self.player.property_observer('duration')
            def _obs_dur(_name, value):
                if value is not None:
                    self._sig.duration_changed.emit(float(value))

            @self.player.property_observer('pause')
            def _obs_pause(_name, value):
                # value: True = đang pause, False = đang play
                if value is not None:
                    self._sig.pause_changed.emit(bool(value))

            # FILE_LOADED: file đã sẵn sàng → đảm bảo đang phát
            @self.player.event_callback('file-loaded')
            def _obs_file_loaded(event):
                # Gọi từ MPV thread — emit signal để main thread xử lý
                self._sig.pause_changed.emit(False)

            # END_FILE: đọc reason từ MpvEventEndFile struct
            @self.player.event_callback('end-file')
            def _obs_end_file(event):
                try:
                    import mpv as _mpv
                    end_data = event.data
                    # reason 0 = EOF (kết thúc tự nhiên)
                    # reason 2 = ABORTED (stop thủ công)
                    # reason 3 = QUIT
                    reason = int(end_data.reason) if end_data is not None else -1
                    if reason == _mpv.MpvEventEndFile.EOF:
                        self._sig.eof_reached.emit()
                except Exception:
                    # fallback: nếu không đọc được reason thì emit luôn
                    self._sig.eof_reached.emit()

        except Exception as e:
            print(f"[AudioPlayerBar] Không thể khởi tạo MPV: {e}")
            self.player = None

    # ── Build UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(8, 6, 8, 6)

        self.ab_bar = ABBar()
        root.addWidget(self.ab_bar)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_dragging", True))
        self.slider.sliderReleased.connect(self._seek_from_slider)
        root.addWidget(self.slider)

        ctrl = QHBoxLayout()
        font_large = self.font()
        font_large.setPointSize(14)

        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("▶")
        self.btn_stop = QPushButton("⏹")
        self.btn_next = QPushButton("⏭")
        self.btn_play.setToolTip("Phát / tạm dừng  [Space]")
        for b in [self.btn_prev, self.btn_play, self.btn_stop, self.btn_next]:
            b.setFixedSize(44, 44)
            b.setFont(font_large)
            ctrl.addWidget(b)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setObjectName("muted")
        ctrl.addSpacing(8)
        ctrl.addWidget(self.lbl_time)
        ctrl.addStretch()

        self.btn_loop = QPushButton("➡️")
        self.btn_loop.setFixedSize(44, 44)
        self.btn_loop.setFont(font_large)
        self.btn_loop.setToolTip("Chế độ lặp")
        ctrl.addWidget(self.btn_loop)

        self.btn_set_a    = QPushButton("A")
        self.btn_set_b    = QPushButton("B")
        self.btn_clear_ab = QPushButton("✕ A-B")
        for b in [self.btn_set_a, self.btn_set_b, self.btn_clear_ab]:
            b.setFixedHeight(36)
            b.setFont(font_large)
            ctrl.addWidget(b)

        self.btn_save_ab = QPushButton("💾 Lưu A-B")
        self.btn_save_ab.setFixedHeight(36)
        ctrl.addWidget(self.btn_save_ab)

        self.btn_list_ab = QPushButton("📋 DS Lặp")
        self.btn_list_ab.setFixedHeight(36)
        ctrl.addWidget(self.btn_list_ab)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(90)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        ctrl.addWidget(QLabel("🔊"))
        ctrl.addWidget(self.vol_slider)

        root.addLayout(ctrl)

        self.btn_play.clicked.connect(self._play_pause)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_set_a.clicked.connect(self._set_a)
        self.btn_set_b.clicked.connect(self._set_b)
        self.btn_clear_ab.clicked.connect(self._clear_ab)
        self.btn_loop.clicked.connect(self._toggle_loop)
        self.btn_save_ab.clicked.connect(self._save_ab)
        self.btn_list_ab.clicked.connect(self._show_ab_list)

    # ── MPV callbacks (Qt main thread) ───────────────────────────────

    def _on_pause_changed(self, paused: bool):
        """Phản ánh state thực của MPV → cập nhật nút play/pause."""
        # Bỏ qua khi không có file đang load (sau stop/trước load)
        if not self._current_path and paused:
            return
        self._is_playing = not paused
        self._update_play_btn()

    def _on_time_pos(self, pos_sec: float):
        pos_ms = int(pos_sec * 1000)
        if not self._dragging and self._duration_ms > 0:
            self.slider.setValue(int(pos_ms / self._duration_ms * 1000))
        self.lbl_time.setText(f"{_ms_to_str(pos_ms)} / {_ms_to_str(self._duration_ms)}")
        # A-B repeat
        if self._ab_a is not None and self._ab_b is not None and pos_ms >= self._ab_b:
            if self.player:
                self.player.seek(self._ab_a / 1000.0, reference="absolute")

    def _on_duration(self, dur_sec: float):
        self._duration_ms = int(dur_sec * 1000)
        self._file_loaded = True

    def _on_eof(self):
        """File kết thúc tự nhiên (reason=EOF từ end-file event)."""
        if self._loop_state == 1:
            # Loop 1 bài: load lại file hiện tại từ đầu
            if self.player and self._current_path:
                self.player.command('loadfile', self._current_path, 'replace')
                # file-loaded observer sẽ emit pause_changed(False) → sync state
        else:
            # Loop off hoặc Loop all → chuyển bài tiếp
            self._is_playing = False
            self._update_play_btn()
            self.play_next_requested.emit(self._loop_state == 2)

    # ── Public API ────────────────────────────────────────────────────

    def load(self, path_or_url: str, media_id: int = None, media_type: str = None):
        """Nạp và phát file/URL. MPV tự phát sau khi load, nút sync qua pause observer."""
        self._media_id    = media_id
        self._media_type  = media_type
        self._file_loaded = False
        self._duration_ms = 0
        self.slider.setValue(0)
        self.lbl_time.setText("00:00 / 00:00")

        if self.player:
            self._current_path = path_or_url
            # loadfile replace → MPV tự phát ngay (pause=no là default)
            self.player.command('loadfile', path_or_url, 'replace')
            # Optimistically set playing — observer sẽ confirm sau
            self._is_playing = True
            self._update_play_btn()
            self.playback_started.emit()

    def play_segment(self, a_ms: int, b_ms: int):
        self._ab_a = a_ms
        self._ab_b = b_ms
        self._update_ab_bar()
        if self.player:
            self.player.seek(a_ms / 1000.0, reference="absolute")
            self.player.pause = False
            self._is_playing  = True
            self._update_play_btn()
            self.playback_started.emit()

    # ── Play / Pause / Stop ───────────────────────────────────────────

    def _play_pause(self):
        if not self.player:
            return
        if self._is_playing:
            self._pause()
        else:
            self._play()

    def _play(self):
        if self.player:
            self.player.pause = False
            # _on_pause_changed sẽ cập nhật _is_playing và nút

    def _pause(self):
        if self.player:
            self.player.pause = True
        # _on_pause_changed sẽ cập nhật _is_playing và nút

    def _stop(self):
        if self.player:
            self.player.command('stop')
        self._is_playing   = False
        self._file_loaded  = False
        self._duration_ms  = 0
        self._current_path = None
        self.slider.setValue(0)
        self.lbl_time.setText("00:00 / 00:00")
        self._update_play_btn()

    def _update_play_btn(self):
        self.btn_play.setText("⏸" if self._is_playing else "▶")

    # ── Volume / Seek ─────────────────────────────────────────────────

    def _on_vol_changed(self, v: int):
        if self.player:
            self.player.volume = v

    def _seek_from_slider(self):
        self._dragging = False
        if self.player and self._duration_ms > 0:
            pos_sec = (self.slider.value() / 1000.0) * (self._duration_ms / 1000.0)
            self.player.seek(pos_sec, reference="absolute")

    # ── Loop ──────────────────────────────────────────────────────────

    def _toggle_loop(self):
        self._loop_state = (self._loop_state + 1) % 3
        labels   = ["➡️", "🔂", "🔁"]
        tooltips = ["Phát tiếp (không lặp)", "Lặp 1 bài", "Lặp danh sách"]
        self.btn_loop.setText(labels[self._loop_state])
        self.btn_loop.setToolTip(tooltips[self._loop_state])

    # ── A-B ───────────────────────────────────────────────────────────

    def _set_a(self):
        if self.player and self.player.time_pos is not None:
            self._ab_a = int(self.player.time_pos * 1000)
            self._update_ab_bar()

    def _set_b(self):
        if self.player and self.player.time_pos is not None:
            self._ab_b = int(self.player.time_pos * 1000)
            self._update_ab_bar()

    def _clear_ab(self):
        self._ab_a = self._ab_b = None
        self.ab_bar.clear_markers()

    def _update_ab_bar(self):
        if self._duration_ms > 0:
            a = self._ab_a / self._duration_ms if self._ab_a is not None else None
            b = self._ab_b / self._duration_ms if self._ab_b is not None else None
            self.ab_bar.set_markers(a, b)

    def _save_ab(self):
        if self._media_id is None or self._media_type is None:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn bài trước khi lưu đoạn lặp!")
            return
        if self._ab_a is None or self._ab_b is None:
            QMessageBox.warning(self, "Lỗi", "Vui lòng đặt cả mốc A và B trước khi lưu!")
            return
        session = get_session()
        try:
            count = session.query(DoanLap).filter(
                DoanLap.media_id   == self._media_id,
                DoanLap.loai_media == self._media_type
            ).count()
            default_name = f"Đoạn lặp {count + 1}"
            name, ok = QInputDialog.getText(
                self, "Lưu Đoạn Lặp", "Nhập tên đoạn lặp:", text=default_name
            )
            if ok and name.strip():
                lap = DoanLap(
                    ten=name.strip(),
                    loai_media=self._media_type,
                    media_id=self._media_id,
                    thoi_gian_a=self._ab_a,
                    thoi_gian_b=self._ab_b,
                )
                session.add(lap)
                session.commit()
                QMessageBox.information(self, "Thành công", "Đã lưu đoạn lặp thành công!")
        finally:
            session.close()

    def _show_ab_list(self):
        if self._media_id is None or self._media_type is None:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn bài trước!")
            return
        dlg = DoanLapDialog(self._media_id, self._media_type, self)
        dlg.exec()


class ABBar(QFrame):
    """Visual A-B repeat indicator"""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(6)
        self._a = self._b = None
        from PySide6.QtGui import QPainter, QColor
        self._QPainter = QPainter
        self._QColor = QColor

    def set_markers(self, a, b):
        self._a, self._b = a, b
        self.update()

    def clear_markers(self):
        self._a = self._b = None
        self.update()

    def paintEvent(self, _):
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QColor("#1e1e32"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 1, w, h-2, 3, 3)
        if self._a is not None and self._b is not None:
            x1 = int(self._a * w)
            x2 = int(self._b * w)
            p.setBrush(QColor("#ff9900"))
            p.drawRoundedRect(x1, 0, max(4, x2-x1), h, 3, 3)
        if self._a is not None:
            p.setBrush(QColor("#ffcc00"))
            p.drawEllipse(int(self._a*w)-4, 0, 8, h)
        if self._b is not None:
            p.setBrush(QColor("#ff6600"))
            p.drawEllipse(int(self._b*w)-4, 0, 8, h)
        p.end()


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    return f"{s//60:02d}:{s%60:02d}"


class DoanLapDialog(QDialog):
    """Hộp thoại quản lý danh sách các đoạn lặp A-B đã lưu"""
    def __init__(self, media_id: int, media_type: str, player_bar, parent=None):
        super().__init__(parent)
        self.media_id = media_id
        self.media_type = media_type
        self.player_bar = player_bar
        self.setWindowTitle("Danh sách Đoạn Lặp A-B")
        self.resize(500, 300)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        vbox = QVBoxLayout(self)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tên đoạn lặp", "Mốc A (ms)", "Mốc B (ms)", "Thao tác"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.cellChanged.connect(self._on_cell_changed)
        
        vbox.addWidget(self.table)
        
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        vbox.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_data(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        session = get_session()
        try:
            laps = session.query(DoanLap).filter(
                DoanLap.media_id == self.media_id,
                DoanLap.loai_media == self.media_type
            ).order_by(DoanLap.tao_luc).all()
            
            for i, lap in enumerate(laps):
                self.table.insertRow(i)
                
                it_ten = QTableWidgetItem(lap.ten)
                it_ten.setData(Qt.ItemDataRole.UserRole, lap.id)
                self.table.setItem(i, 0, it_ten)
                
                self.table.setItem(i, 1, QTableWidgetItem(str(lap.thoi_gian_a)))
                self.table.setItem(i, 2, QTableWidgetItem(str(lap.thoi_gian_b)))
                
                # Buttons
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(2, 2, 2, 2)
                l.setSpacing(4)
                
                btn_play = QPushButton("▶ Phát")
                btn_play.clicked.connect(lambda _, a=lap.thoi_gian_a, b=lap.thoi_gian_b: self.player_bar.play_segment(a, b))
                
                btn_del = QPushButton("🗑")
                btn_del.clicked.connect(lambda _, lid=lap.id: self._delete_lap(lid))
                
                l.addWidget(btn_play)
                l.addWidget(btn_del)
                self.table.setCellWidget(i, 3, w)
        finally:
            session.close()
        self.table.blockSignals(False)

    def _on_cell_changed(self, row, col):
        it_ten = self.table.item(row, 0)
        if not it_ten: return
        lap_id = it_ten.data(Qt.ItemDataRole.UserRole)
        
        new_val = self.table.item(row, col).text().strip()
        
        session = get_session()
        try:
            lap = session.get(DoanLap, lap_id)
            if lap:
                if col == 0:
                    lap.ten = new_val
                elif col == 1:
                    try: lap.thoi_gian_a = int(new_val)
                    except ValueError: pass
                elif col == 2:
                    try: lap.thoi_gian_b = int(new_val)
                    except ValueError: pass
                session.commit()
        finally:
            session.close()

    def _delete_lap(self, lap_id):
        reply = QMessageBox.question(self, "Xóa", "Bạn có chắc muốn xóa đoạn lặp này?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                lap = session.get(DoanLap, lap_id)
                if lap:
                    session.delete(lap)
                    session.commit()
            finally:
                session.close()
            self._load_data()
