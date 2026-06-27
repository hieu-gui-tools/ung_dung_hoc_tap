"""
app/ui/widgets/video_widget.py — Video player + YouTube download
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QSplitter,
    QGroupBox, QMessageBox, QFileDialog, QSizePolicy, QFrame, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QUrl, QTimer, QObject


from app.data.database import get_session, Video, Bai, Chuong, ChuDe, DoanLap
from app.core.workers import YtDlpWorker
from app.ui.widgets.common import ABBar, _ms_to_str, DoanLapDialog


def get_video_dir():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    d = os.path.join(base, "media", "video")
    os.makedirs(d, exist_ok=True)
    return d


class MpvSignals(QObject):
    time_pos_changed = Signal(float)
    duration_changed = Signal(float)
    eof_reached = Signal()


class VideoWidget(QWidget):
    playback_started = Signal()
    def __init__(self, topic_bar, parent=None):
        super().__init__(parent)
        self.topic_bar = topic_bar
        self._yt_worker = None
        self._current_video_id = None
        self._duration_ms = 0
        self._dragging = False
        self._ab_a = None
        self._ab_b = None
        self._loop_state = 0
        self._is_playing = False

        self._build_ui()
        
        try:
            import os
            # Thêm thư mục gốc vào PATH để python-mpv tìm thấy libmpv-2.dll
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            os.environ["PATH"] = root_dir + os.pathsep + os.environ.get("PATH", "")
            
            import mpv
            # wid must be set to the container's winId
            self.player = mpv.MPV(ytdl=True, wid=str(int(self.video_container.winId())))
            self.player.volume = 90

            self.mpv_signals = MpvSignals()
            self.mpv_signals.time_pos_changed.connect(self._on_time_pos)
            self.mpv_signals.duration_changed.connect(self._on_duration)
            self.mpv_signals.eof_reached.connect(self._on_eof)

            @self.player.property_observer('time-pos')
            def on_time_pos(_name, value):
                if value is not None:
                    self.mpv_signals.time_pos_changed.emit(value)

            @self.player.property_observer('duration')
            def on_duration(_name, value):
                if value is not None:
                    self.mpv_signals.duration_changed.emit(value)

            @self.player.property_observer('eof-reached')
            def on_eof_reached(_name, value):
                if value:
                    self.mpv_signals.eof_reached.emit()

        except Exception as e:
            print(f"Không thể khởi tạo MPV: {e}")
            self.player = None

        topic_bar.selection_changed.connect(self._refresh_list)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # ─── LEFT: danh sách video ───────────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setSpacing(6)
        lv.setContentsMargins(8, 8, 4, 8)

        lv.addWidget(QLabel("🎬 Danh sách Video"))
        self.video_list = QListWidget()
        self.video_list.currentItemChanged.connect(self._on_video_selected)
        self.video_list.itemDoubleClicked.connect(self._play_selected)
        lv.addWidget(self.video_list, 1)

        list_btns = QHBoxLayout()
        self.btn_play_video   = QPushButton("▶ Phát")
        self.btn_delete_video = QPushButton("🗑 Xóa")
        for b in [self.btn_play_video, self.btn_delete_video]:
            b.setFixedHeight(28)
            list_btns.addWidget(b)
        lv.addLayout(list_btns)

        # Add video section
        add_group = QGroupBox("➕ Thêm Video")
        ag = QVBoxLayout(add_group)

        # From file
        self.btn_add_file = QPushButton("📁 Thêm từ file")
        ag.addWidget(self.btn_add_file)

        # From YouTube
        yt_row = QHBoxLayout()
        self.inp_yt_url = QLineEdit()
        self.inp_yt_url.setPlaceholderText("YouTube URL...")
        self.btn_yt_stream = QPushButton("▶ Stream")
        self.btn_yt_download = QPushButton("⬇ Tải")
        for b in [self.btn_yt_stream, self.btn_yt_download]:
            b.setFixedHeight(28)
        yt_row.addWidget(self.inp_yt_url, 1)
        yt_row.addWidget(self.btn_yt_stream)
        yt_row.addWidget(self.btn_yt_download)
        ag.addLayout(yt_row)

        self.lbl_yt_status = QLabel("")
        self.lbl_yt_status.setObjectName("muted")
        self.lbl_yt_status.setWordWrap(True)
        ag.addWidget(self.lbl_yt_status)
        lv.addWidget(add_group)

        splitter.addWidget(left)

        # ─── RIGHT: video player ───────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setSpacing(4)
        rv.setContentsMargins(4, 8, 8, 8)

        self.video_container = QWidget()
        self.video_container.setObjectName("videoFrame")
        self.video_container.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video_container.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.video_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_container.setMinimumHeight(300)
        # Background color to match the frame style if necessary
        self.video_container.setStyleSheet("background-color: black;")
        rv.addWidget(self.video_container, 1)

        self.lbl_title = QLabel("Chưa có video nào được chọn")
        self.lbl_title.setObjectName("h3")
        self.lbl_title.setWordWrap(True)
        rv.addWidget(self.lbl_title)

        # AB Bar
        self.ab_bar = ABBar()
        rv.addWidget(self.ab_bar)

        # Slider
        from PySide6.QtWidgets import QSlider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_dragging", True))
        self.slider.sliderReleased.connect(self._seek_from_slider)
        rv.addWidget(self.slider)

        # Controls
        ctrl = QHBoxLayout()
        
        font_large = self.font()
        font_large.setPointSize(14)
        
        self.btn_prev  = QPushButton("⏮")
        self.btn_play  = QPushButton("▶")
        self.btn_stop  = QPushButton("⏹")
        self.btn_next  = QPushButton("⏭")
        self.btn_play.setToolTip("Phát / tạm dừng")
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
        self.btn_loop.setToolTip("Phát tiếp")
        ctrl.addWidget(self.btn_loop)

        # A-B controls
        self.btn_set_a   = QPushButton("A")
        self.btn_set_b   = QPushButton("B")
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

        # Volume
        from PySide6.QtWidgets import QSlider as Sl
        self.vol_slider = Sl(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100); self.vol_slider.setValue(90)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(self._on_vol_changed)
        ctrl.addWidget(QLabel("🔊"))
        ctrl.addWidget(self.vol_slider)
        rv.addLayout(ctrl)

        splitter.addWidget(right)
        splitter.setSizes([300, 700])

        # Connections
        self.btn_play.clicked.connect(self._play_pause)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_prev.clicked.connect(self._play_prev)
        self.btn_next.clicked.connect(self._play_next)
        self.btn_set_a.clicked.connect(self._set_a)
        self.btn_set_b.clicked.connect(self._set_b)
        self.btn_clear_ab.clicked.connect(self._clear_ab)
        self.btn_loop.clicked.connect(self._toggle_loop)
        self.btn_save_ab.clicked.connect(self._save_ab)
        self.btn_list_ab.clicked.connect(self._show_ab_list)
        self.btn_play_video.clicked.connect(self._play_selected)
        self.btn_delete_video.clicked.connect(self._delete_video)
        self.btn_add_file.clicked.connect(self._add_file)
        self.btn_yt_stream.clicked.connect(lambda: self._yt_fetch(download=False))
        self.btn_yt_download.clicked.connect(lambda: self._yt_fetch(download=True))

        self._refresh_list()

    # ─── List management ──────────────────────────────────────────────

    def _refresh_list(self, *_):
        session = get_session()
        try:
            q = session.query(Video)
            cd, ch, bai = (
                self.topic_bar.get_chu_de_id(),
                self.topic_bar.get_chuong_id(),
                self.topic_bar.get_bai_id(),
            )
            if bai:
                q = q.filter(Video.bai_id == bai)
            elif ch:
                ids = [b.id for b in session.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter(Video.bai_id.in_(ids))
            elif cd:
                cids = [c.id for c in session.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter(Video.bai_id.in_(bids))
            videos = q.order_by(Video.tao_luc).all()
            self.video_list.clear()
            for v in videos:
                icon = "📺" if v.loai == "youtube" else "🎬"
                item = QListWidgetItem(f"{icon} {v.ten}")
                item.setData(Qt.ItemDataRole.UserRole, v.id)
                self.video_list.addItem(item)
        finally:
            session.close()

    def _on_video_selected(self, item):
        if item:
            self._current_video_id = item.data(Qt.ItemDataRole.UserRole)
            session = get_session()
            try:
                v = session.get(Video, self._current_video_id)
                if v:
                    self.lbl_title.setText(v.ten)
            finally:
                session.close()

    def _play_selected(self, *_):
        if not self._current_video_id:
            return
        session = get_session()
        try:
            v = session.get(Video, self._current_video_id)
            if not v:
                return
            if v.loai == "youtube":
                self.lbl_yt_status.setText("Đang lấy stream YouTube...")
                w = YtDlpWorker(v.duong_dan, video=True)
                w.finished.connect(lambda d: self._load_video_url(d["stream"]))
                w.error.connect(lambda e: self.lbl_yt_status.setText(f"Lỗi: {e}"))
                w.start()
                self._yt_worker = w
            else:
                if v.duong_dan and os.path.exists(v.duong_dan):
                    self._load_video_url(v.duong_dan)
        finally:
            session.close()

    def _update_play_button(self):
        self.btn_play.setText("⏸" if self._is_playing else "▶")

    def _play_pause(self):
        if self._is_playing:
            self._pause()
        else:
            self._play()

    def _play(self):
        if self.player:
            self.player.pause = False
            self._is_playing = True
            self._update_play_button()
            self.playback_started.emit()

    def _pause(self):
        if self.player:
            self.player.pause = True
        self._is_playing = False
        self._update_play_button()

    def _stop(self):
        if self.player:
            self.player.stop()
            self._duration_ms = 0
            self.slider.setValue(0)
            self.lbl_time.setText("00:00 / 00:00")
        self._is_playing = False
        self._update_play_button()

    def _on_vol_changed(self, v):
        if self.player:
            self.player.volume = v

    def _load_video_url(self, url):
        self.lbl_yt_status.setText("")
        if self.player:
            self.player.play(url)
            self.player.pause = False
            self._is_playing = True
            self._update_play_button()
            self.playback_started.emit()

    def _play_prev(self):
        r = self.video_list.currentRow()
        if r > 0:
            self.video_list.setCurrentRow(r - 1)
            self._play_selected()

    def _play_next(self):
        r = self.video_list.currentRow()
        if r < self.video_list.count() - 1:
            self.video_list.setCurrentRow(r + 1)
            self._play_selected()

    def _delete_video(self):
        if not self._current_video_id:
            return
        if QMessageBox.question(self, "Xóa", "Xóa video này?") == QMessageBox.StandardButton.Yes:
            self._stop()
            session = get_session()
            try:
                v = session.get(Video, self._current_video_id)
                if v:
                    if v.loai == "file" and v.duong_dan and os.path.exists(v.duong_dan):
                        try:
                            import time
                            time.sleep(0.1)
                            os.remove(v.duong_dan)
                        except OSError as e:
                            print(f"Lỗi khi xóa file video: {e}")
                    session.delete(v)
                    session.commit()
            finally:
                session.close()
            self._refresh_list()

    def _add_file(self):
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Chọn Bài trước khi thêm video!")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn video", "",
            "Video (*.mp4 *.mkv *.avi *.mov *.webm *.flv)"
        )
        if path:
            session = get_session()
            try:
                v = Video(ten=os.path.basename(path), duong_dan=path, loai="file", bai_id=bai_id)
                session.add(v); session.commit()
            finally:
                session.close()
            self._refresh_list()

    def _yt_fetch(self, download: bool):
        url = self.inp_yt_url.text().strip()
        if not url:
            return
        bai_id = self.topic_bar.get_bai_id()
        if not bai_id:
            QMessageBox.warning(self, "Lỗi", "Chọn Bài trước!")
            return
        self.lbl_yt_status.setText("Đang xử lý YouTube...")
        self.btn_yt_stream.setEnabled(False)
        self.btn_yt_download.setEnabled(False)

        out_dir = get_video_dir() if download else ""
        w = YtDlpWorker(url, download=download, video=True, out_dir=out_dir)
        w.progress.connect(lambda s: self.lbl_yt_status.setText(s))
        w.finished.connect(lambda d: self._on_yt_done(d, bai_id, download))
        w.error.connect(lambda e: (self.lbl_yt_status.setText(f"Lỗi: {e}"),
                                   self.btn_yt_stream.setEnabled(True),
                                   self.btn_yt_download.setEnabled(True)))
        w.start()
        self._yt_worker = w

    def _on_yt_done(self, info: dict, bai_id: int, downloaded: bool):
        self.btn_yt_stream.setEnabled(True)
        self.btn_yt_download.setEnabled(True)
        session = get_session()
        try:
            if downloaded and info.get("file"):
                v = Video(ten=info["title"], duong_dan=info["file"], loai="file", bai_id=bai_id)
                self.lbl_yt_status.setText(f"✅ Đã tải: {info['title']}")
            else:
                v = Video(ten=info["title"], duong_dan=info["url"], loai="youtube", bai_id=bai_id)
                self.lbl_yt_status.setText(f"✅ Đã thêm: {info['title']}")
            session.add(v); session.commit()
            self._refresh_list()
            self._load_video_url(info["stream"])
        finally:
            session.close()

    # ─── Playback ─────────────────────────────────────────────────────

    def _on_time_pos(self, pos_sec):
        pos_ms = int(pos_sec * 1000)
        if not self._dragging and self._duration_ms > 0:
            self.slider.setValue(int(pos_ms / self._duration_ms * 1000))
        self.lbl_time.setText(f"{_ms_to_str(pos_ms)} / {_ms_to_str(self._duration_ms)}")
        if self._ab_a is not None and self._ab_b is not None and pos_ms >= self._ab_b:
            if self.player:
                self.player.seek(self._ab_a / 1000.0, reference="absolute")

    def _on_duration(self, dur_sec):
        self._duration_ms = int(dur_sec * 1000)

    def _on_eof(self):
        if self.player:
            if self._loop_state != 1:
                self._is_playing = False
                self._update_play_button()
                # auto play next if requested or loop all
                if self._loop_state == 2:
                    row = self.video_list.currentRow()
                    if row < self.video_list.count() - 1:
                        self.video_list.setCurrentRow(row + 1)
                        self._play_selected()
                    elif self.video_list.count() > 0:
                        self.video_list.setCurrentRow(0)
                        self._play_selected()
                else:
                    self._play_next() # Reset handled elsewhere or just stops

    def _seek_from_slider(self):
        self._dragging = False
        if self.player and self._duration_ms > 0:
            pos_sec = (self.slider.value() / 1000.0) * (self._duration_ms / 1000.0)
            self.player.seek(pos_sec, reference="absolute")

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

    def _toggle_loop(self):
        self._loop_state = (self._loop_state + 1) % 3
        if self._loop_state == 0:
            self.btn_loop.setText("➡️")
            self.btn_loop.setToolTip("Phát tiếp")
            if self.player:
                self.player.loop_file = 'no'
        elif self._loop_state == 1:
            self.btn_loop.setText("🔂")
            self.btn_loop.setToolTip("Lặp 1 bài")
            if self.player:
                self.player.loop_file = 'inf'
        else:
            self.btn_loop.setText("🔁")
            self.btn_loop.setToolTip("Lặp danh sách")
            if self.player:
                self.player.loop_file = 'no'

    def play_segment(self, a_ms: int, b_ms: int):
        self._ab_a = a_ms
        self._ab_b = b_ms
        self._update_ab_bar()
        if self.player:
            self.player.seek(a_ms / 1000.0, reference="absolute")
            self.player.pause = False
            self._is_playing = True
            self._update_play_button()
            self.playback_started.emit()

    def _save_ab(self):
        if not self._current_video_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn video trước khi lưu đoạn lặp!")
            return
        if self._ab_a is None or self._ab_b is None:
            QMessageBox.warning(self, "Lỗi", "Vui lòng đặt cả mốc A và B trước khi lưu!")
            return
        
        session = get_session()
        try:
            count = session.query(DoanLap).filter(
                DoanLap.media_id == self._current_video_id,
                DoanLap.loai_media == "video"
            ).count()
            default_name = f"Đoạn lặp {count + 1}"
            
            name, ok = QInputDialog.getText(self, "Lưu Đoạn Lặp", "Nhập tên đoạn lặp:", text=default_name)
            if ok and name.strip():
                lap = DoanLap(
                    ten=name.strip(),
                    loai_media="video",
                    media_id=self._current_video_id,
                    thoi_gian_a=self._ab_a,
                    thoi_gian_b=self._ab_b
                )
                session.add(lap)
                session.commit()
                QMessageBox.information(self, "Thành công", "Đã lưu đoạn lặp thành công!")
        finally:
            session.close()

    def _show_ab_list(self):
        if not self._current_video_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn video trước!")
            return
        dlg = DoanLapDialog(self._current_video_id, "video", self)
        dlg.exec()
