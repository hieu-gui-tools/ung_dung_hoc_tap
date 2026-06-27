# Ứng Dụng Học Tập (Learning App)

Ứng dụng học tập đa năng được xây dựng bằng Python với giao diện người dùng đồ họa PySide6. Quản lý môi trường và dependency bằng `uv`. Ứng dụng cung cấp các công cụ mạnh mẽ để luyện tập ngoại ngữ, ghi nhớ kiến thức và quản lý quá trình học tập.

## 🌟 Tính Năng Nổi Bật

| Module | Tính năng chi tiết |
|---|---|
| **🔊 TTS / Ghi âm** | • Chuyển văn bản thành giọng nói (TTS) tiếng Việt qua `gTTS` và hỗ trợ đa ngôn ngữ qua `edge-tts`.<br>• Chế độ Batch TTS để tạo hàng loạt file âm thanh.<br>• Tính năng ghi âm giọng nói người dùng (cần cài đặt thêm thư viện `pyaudio`).<br>• Trình phát âm thanh tích hợp với chức năng lặp đoạn **A-B Repeat**. |
| **🎬 Video** | • Trình phát video cho các tệp cục bộ.<br>• Hỗ trợ phát trực tiếp hoặc tải xuống video từ YouTube qua `yt-dlp`.<br>• Chức năng lặp đoạn **A-B Repeat** chính xác, hỗ trợ học qua video hiệu quả. |
| **🃏 Flashcard** | • Hệ thống thẻ ghi nhớ thông minh.<br>• Các thao tác lật thẻ, trộn thẻ.<br>• Dễ dàng thêm, sửa, xóa thẻ ghi nhớ. |
| **📝 Kiểm tra (Quiz)** | • Hệ thống trắc nghiệm nhiều lựa chọn (A/B/C/D).<br>• Tự động tính điểm và đánh giá.<br>• Ghi chú riêng cho từng câu hỏi giúp ôn tập hiệu quả. |
| **📔 Nhật kí (Diary)** | • Viết nhật kí học tập dạng văn bản.<br>• Đính kèm file ghi âm nhật kí theo ngày hoặc theo bài học. |

## 🏗️ Cấu Trúc Dự Án

```
ung_dung_hoc_tap/
├── app/
│   ├── core/
│   │   └── workers.py          # Xử lý đa luồng: TTSWorker, BatchTTSWorker, YtDlpWorker, AudioRecorder
│   ├── data/
│   │   └── database.py         # Quản lý Database bằng SQLAlchemy (Các bảng: ChuDe, Chuong, Bai, Audio, Video, Flashcard, CauHoi, NhatKi)
│   ├── ui/
│   │   ├── styles.py           # Giao diện Dark theme sử dụng QSS
│   │   ├── main_window.py      # Cửa sổ chính tích hợp Sidebar, Timer, Navigation
│   │   └── widgets/
│   │       ├── common.py       # Các thành phần dùng chung: TopicBar, AudioPlayerBar, ABBar
│   │       ├── topic_dialogs.py
│   │       ├── tts_widget.py
│   │       ├── video_widget.py
│   │       ├── flashcard_widget.py
│   │       ├── quiz_widget.py
│   │       └── diary_widget.py
│   └── main.py
├── media/                      # Chứa các tệp đa phương tiện
│   ├── audio/                  # Âm thanh được tạo từ TTS hoặc tải xuống
│   ├── video/                  # Video được tải từ YouTube
│   └── diary/                  # Các file ghi âm nhật kí
├── hoctap.db                   # Cơ sở dữ liệu SQLite (Tự động sinh ra khi chạy ứng dụng lần đầu)
├── pyproject.toml              # Cấu hình dependency cho uv
├── Hoc Tap.cmd                 # Script khởi động nhanh qua Command Prompt
└── Hoc Tap.vbs                 # Script chạy ứng dụng ẩn cửa sổ Command Prompt
```

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### Yêu Cầu Hệ Thống
- Đã cài đặt **Python 3.10+** (hoặc quản lý qua `uv`).
- Công cụ **uv** của Astral để cài đặt môi trường.

### 1. Cài Đặt Dependencies

Clone dự án và mở terminal tại thư mục dự án:
```bash
# Cài đặt và đồng bộ toàn bộ thư viện cần thiết
uv sync
```

### 2. Chạy Ứng Dụng

**Cách 1:** Chạy qua terminal
```bash
uv run python main.py
```

**Cách 2:** Chạy bằng Script (Chỉ cho Windows)
- Nhấp đúp vào file **`Hoc Tap.vbs`** để khởi chạy ứng dụng mà không hiện cửa sổ Command Prompt.
- Hoặc chạy qua **`Hoc Tap.cmd`**.

### 3. Cấu Hình Bổ Sung

#### Kích Hoạt Tính Năng Ghi Âm
Tính năng ghi âm yêu cầu sử dụng thư viện `pyaudio`. Để cài đặt:
```bash
uv add pyaudio
```

#### Xử Lý Video & Tải File
- Video từ YouTube tải qua `yt-dlp` sẽ được lưu trữ tự động vào mục `media/video/`.
- File âm thanh TTS mặc định lưu tại `media/audio/`.

## 📦 Các Thư Viện Sử Dụng (Dependencies)

- **PySide6**: Xây dựng giao diện ứng dụng (GUI).
- **SQLAlchemy**: Ánh xạ đối tượng quan hệ (ORM) cho SQLite.
- **gTTS**: Hỗ trợ chuyển đổi văn bản sang giọng nói tiếng Việt cơ bản.
- **edge-tts**: Cung cấp giọng đọc TTS chất lượng cao từ Microsoft Edge (Không yêu cầu API key).
- **yt-dlp**: Thư viện mạnh mẽ để stream và tải video từ nền tảng YouTube.
- **pyaudio** *(Tùy chọn)*: Hỗ trợ ghi âm microphone.

## 🔒 Lưu Ý Bảo Mật
- Không chia sẻ file `hoctap.db` chứa các dữ liệu học tập cá nhân của bạn.
- Thư mục `.venv` và `__pycache__` đã được bỏ qua bằng `.gitignore`.
