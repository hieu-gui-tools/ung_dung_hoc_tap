import os

path = r'd:\ProjectRoot\PythonProject\ung_dung_hoc_tap\app\ui\widgets\video_widget.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

bad_str = """    def _play_prev(self):
            try:
                v = Video(ten=os.path.basename(path), duong_dan=path, loai="file", bai_id=bai_id)
                session.add(v); session.commit()
            finally:
                session.close()
            self._refresh_list()"""

good_str = """    def _play_prev(self):
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
            self._refresh_list()"""

if bad_str in content:
    content = content.replace(bad_str, good_str)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed successfully")
else:
    print("bad_str not found!")
