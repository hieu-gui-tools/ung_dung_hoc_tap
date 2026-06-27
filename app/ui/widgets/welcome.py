"""
app/ui/widgets/welcome.py — Màn hình chào khi chưa có dữ liệu
(Hiển thị trong stacked widget dưới dạng overlay)
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal


TIPS = [
    ("🔊", "TTS / Ghi âm",
     "Tạo audio từ văn bản với gTTS/Edge TTS, ghi âm giọng nói,\n"
     "phát lại với A-B repeat chính xác đến millisecond."),
    ("🎬", "Video",
     "Xem video local hoặc stream YouTube,\n"
     "lặp đoạn A-B, tải video về máy."),
    ("🃏", "Flashcard",
     "Tạo thẻ ghi nhớ, lật thẻ, trộn thẻ ngẫu nhiên,\n"
     "tổ chức theo Chủ đề / Chương / Bài."),
    ("📝", "Kiểm tra",
     "Trắc nghiệm A/B/C/D, tính điểm tự động,\n"
     "ghi chú từng câu hỏi, trộn câu ngẫu nhiên."),
    ("📔", "Nhật kí",
     "Viết nhật kí học tập theo ngày,\n"
     "kết hợp text và ghi âm giọng nói."),
]


class WelcomeOverlay(QWidget):
    """Overlay hướng dẫn bắt đầu"""
    start_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        layout.setContentsMargins(60, 40, 60, 40)

        title = QLabel("📚 Chào mừng đến với Ứng Dụng Học Tập!")
        title.setObjectName("h1")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Bắt đầu bằng cách tạo Chủ đề → Chương → Bài ở thanh trên cùng bên phải.")
        sub.setObjectName("h3")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # Feature cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for icon, name, desc in TIPS:
            card = QWidget()
            card.setStyleSheet(
                "QWidget { background: #14142a; border: 1px solid #2a2a4a; "
                "border-radius: 12px; padding: 12px; }"
            )
            cv = QVBoxLayout(card)
            cv.setSpacing(6)
            lbl_icon = QLabel(icon)
            lbl_icon.setStyleSheet("font-size: 28px;")
            lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_name = QLabel(name)
            lbl_name.setObjectName("h3")
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_desc = QLabel(desc)
            lbl_desc.setObjectName("muted")
            lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_desc.setWordWrap(True)
            for w in [lbl_icon, lbl_name, lbl_desc]:
                cv.addWidget(w)
            cards_row.addWidget(card, 1)
        layout.addLayout(cards_row)

        # Quick start note
        note = QLabel(
            "💡 Bấm  ➕ Thêm  ở phần Chủ đề bên phải để bắt đầu tổ chức nội dung học tập."
        )
        note.setObjectName("muted")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        layout.addWidget(note)
