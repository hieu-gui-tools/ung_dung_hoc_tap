"""
app/ui/styles.py — QSS stylesheet toàn bộ app Ứng Dụng Học Tập
"""

MAIN_STYLE = """
/* ─── GLOBAL ─── */
QMainWindow, QWidget {
    background-color: #0f0f1a;
    color: #e8e8f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
}
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #1a1a2e; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3a3a5c; border-radius: 4px; min-height: 20px;
}
QScrollBar:horizontal {
    background: #1a1a2e; height: 8px; border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #3a3a5c; border-radius: 4px; min-width: 20px;
}

/* ─── LEFT SIDEBAR ─── */
#leftSidebar {
    background-color: #0d0d1f;
    border-right: 1px solid #1a1a35;
    min-width: 200px;
    max-width: 200px;
}

/* ─── TIMER ─── */
#timerDisplay {
    font-size: 32px;
    font-weight: bold;
    color: #7c7cff;
    font-family: 'Courier New', monospace;
    background: #12122a;
    border: 1px solid #2a2a50;
    border-radius: 10px;
    padding: 12px;
    qproperty-alignment: AlignCenter;
}
#timerDisplay[running="true"] { color: #5cff8c; }
#timerDisplay[paused="true"]  { color: #ffc040; }

/* ─── NAV BUTTONS (function icons) ─── */
QPushButton#navBtn {
    background: transparent;
    color: #7070a0;
    border: none;
    border-radius: 8px;
    padding: 10px 8px 10px 14px;
    font-size: 12px;
    text-align: left;
}
QPushButton#navBtn:hover {
    background: #1e1e40;
    color: #ffffff;
}
QPushButton#navBtn[active="true"] {
    background: #1e2050;
    color: #7c7cff;
    border-left: 3px solid #7c7cff;
    font-weight: bold;
}

/* ─── RIGHT PANEL ─── */
#rightPanel {
    background: #0f0f1a;
}
#topicBar {
    background: #12122a;
    border-bottom: 1px solid #1e1e3a;
    padding: 8px;
}

/* ─── COMMON BUTTONS ─── */
QPushButton {
    background: #1e1e3a;
    color: #c0c0e0;
    border: 1px solid #2e2e4e;
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 13px;
}
QPushButton:hover { background: #28284a; color: white; }
QPushButton:pressed { background: #141430; }
QPushButton:disabled { color: #404060; border-color: #1a1a30; }

QPushButton#primaryBtn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #5c5cff,stop:1 #8c5cff);
    color: white; border: none; border-radius: 8px;
    padding: 8px 20px; font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7070ff,stop:1 #a070ff);
}
QPushButton#successBtn {
    background: #1a5c2a; color: #5cff8c;
    border: 1px solid #2a8c3a; border-radius: 8px; padding: 7px 14px; font-weight: bold;
}
QPushButton#successBtn:hover { background: #206c34; }
QPushButton#dangerBtn {
    background: #5c1a1a; color: #ff6c6c;
    border: 1px solid #8c2a2a; border-radius: 8px; padding: 7px 14px; font-weight: bold;
}
QPushButton#dangerBtn:hover { background: #6c2020; }
QPushButton#warningBtn {
    background: #4a3a00; color: #ffc040;
    border: 1px solid #7a6000; border-radius: 8px; padding: 7px 14px; font-weight: bold;
}
QPushButton#warningBtn:hover { background: #5a4800; }

/* record button */
QPushButton#recordBtn {
    background: #3a0a0a;
    color: #ff4040;
    border: 2px solid #ff4040;
    border-radius: 20px;
    min-width: 40px; min-height: 40px;
    max-width: 40px; max-height: 40px;
    font-size: 18px;
    font-weight: bold;
}
QPushButton#recordBtn[recording="true"] {
    background: #ff2020;
    color: white;
    border-color: #ff8080;
}
QPushButton#recordBtn:hover { background: #5a1010; }

/* play/stop button */
QPushButton#playBtn {
    background: #0a2a0a;
    color: #40ff40;
    border: 2px solid #40ff40;
    border-radius: 18px;
    min-width: 36px; min-height: 36px;
    max-width: 36px; max-height: 36px;
    font-size: 16px;
}
QPushButton#playBtn:hover { background: #0d3a0d; }

/* ─── TRACKPAD TOGGLE BUTTON ─── */
QPushButton#trackpadBtn {
    background: #0d2a0d;
    color: #5cff8c;
    border: 1px solid #2a6c3a;
    border-radius: 8px;
    padding: 6px 8px;
    font-size: 11px;
    font-weight: bold;
    text-align: center;
}
QPushButton#trackpadBtn:hover {
    background: #123515;
    color: #80ffaa;
    border-color: #40aa60;
}
QPushButton#trackpadBtn[state="off"] {
    background: #2a0d0d;
    color: #ff6c6c;
    border: 1px solid #6c2a2a;
}
QPushButton#trackpadBtn[state="off"]:hover {
    background: #3a1010;
    color: #ff9090;
    border-color: #aa4040;
}
QPushButton#trackpadBtn[state="sim"] {
    background: #2a2a0d;
    color: #ffc040;
    border: 1px solid #6c6020;
}

/* ─── TRACKPAD TIMER LABEL ─── */
QLabel#trackpadTimer {
    color: #ffc040;
    font-size: 10px;
    font-family: 'Courier New', monospace;
    background: #1a1a0a;
    border: 1px solid #3a3a10;
    border-radius: 5px;
    padding: 2px 6px;
    qproperty-alignment: AlignCenter;
}

/* ─── COMBO BOX ─── */
QComboBox {
    background: #1a1a32; border: 1px solid #2a2a4a;
    border-radius: 7px; padding: 6px 10px; color: #c0c0e0;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #1a1a32; border: 1px solid #2a2a4a;
    color: #c0c0e0; selection-background-color: #2a2a5a;
}

/* ─── LIST WIDGET ─── */
QListWidget {
    background: #12122a; border: 1px solid #1e1e3a; border-radius: 7px;
    color: #c0c0e0; outline: none;
}
QListWidget::item { padding: 8px 10px; border-radius: 4px; }
QListWidget::item:hover { background: #1e1e40; }
QListWidget::item:selected { background: #252560; color: white; border-left: 3px solid #7c7cff; }

/* ─── TEXT EDIT / LINE EDIT ─── */
QTextEdit, QPlainTextEdit {
    background: #141428; border: 1px solid #2a2a4a;
    border-radius: 7px; color: #d0d0e8; padding: 8px;
}
QLineEdit {
    background: #141428; border: 1px solid #2a2a4a;
    border-radius: 7px; color: #d0d0e8; padding: 6px 10px;
}
QLineEdit:focus, QTextEdit:focus { border-color: #5c5cff; }

/* ─── LABELS ─── */
QLabel#h1 { font-size: 22px; font-weight: bold; color: #ffffff; }
QLabel#h2 { font-size: 17px; font-weight: bold; color: #e0e0ff; }
QLabel#h3 { font-size: 14px; font-weight: 600; color: #c0c0e0; }
QLabel#muted { color: #6060a0; font-size: 12px; }
QLabel#accent { color: #7c7cff; font-weight: bold; }
QLabel#success { color: #5cff8c; }
QLabel#danger  { color: #ff6c6c; }
QLabel#warning { color: #ffc040; }

/* ─── SLIDER (audio progress) ─── */
QSlider::groove:horizontal {
    background: #1e1e3a; height: 5px; border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #7c7cff; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #5c5cff; border-radius: 3px; }

/* ─── SPIN BOX ─── */
QSpinBox, QDoubleSpinBox {
    background: #141428; border: 1px solid #2a2a4a;
    border-radius: 7px; color: #d0d0e8; padding: 4px 8px;
}

/* ─── GROUP BOX ─── */
QGroupBox {
    border: 1px solid #2a2a4a; border-radius: 8px;
    margin-top: 12px; padding-top: 10px; color: #9090c0;
    font-size: 12px; font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; color: #7c7cff; }

/* ─── SPLITTER ─── */
QSplitter::handle { background: #1e1e3a; width: 2px; height: 2px; }
QSplitter::handle:hover { background: #5c5cff; }

/* ─── TAB WIDGET ─── */
QTabWidget::pane { border: 1px solid #2a2a4a; border-radius: 8px; background: #12122a; }
QTabBar::tab {
    background: #0f0f1a; color: #7070a0;
    padding: 8px 18px; border-radius: 7px 7px 0 0; margin-right: 2px;
}
QTabBar::tab:selected { background: #1e1e40; color: #7c7cff; font-weight: bold; }
QTabBar::tab:hover { background: #1a1a38; color: #c0c0ff; }

/* ─── DIALOG ─── */
QDialog { background: #0d0d1a; color: #e0e0f0; }
QDialog QLabel { color: #a0a0c0; }

/* ─── FLASHCARD ─── */
#flashcardWidget {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1a1a38,stop:1 #12122a);
    border: 1px solid #2a2a50; border-radius: 18px;
}
#flashcardWord { font-size: 34px; font-weight: bold; color: #ffffff; }
#flashcardPhonetic { font-size: 15px; color: #7070c0; }
#flashcardMeaning { font-size: 16px; color: #c0c0e0; }
#flashcardExample { font-size: 13px; color: #909090; font-style: italic; }

/* ─── QUIZ ─── */
QLabel#quizQuestion {
    color: #dcdce6;
    font-size: 17px;
    font-weight: 500;
    padding: 12px;
    background: #141428;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
}
QPushButton#optionBtn {
    background: #1a1a32; border: 2px solid #2a2a4a;
    border-radius: 10px; color: #c0c0e0;
    padding: 12px 16px; text-align: left;
}
QPushButton#optionBtn:hover { background: #22224a; border-color: #5c5cff; color: white; }
QPushButton#optionBtn[state="correct"] { background: #0d3320; border-color: #3ccc6c; color: #5cff8c; }
QPushButton#optionBtn[state="wrong"]   { background: #330d0d; border-color: #cc3c3c; color: #ff6c6c; }
QPushButton#optionBtn[state="reveal"]  { background: #1a3a1a; border-color: #3ccc6c; color: #5cff8c; }

/* ─── PROGRESS ─── */
QProgressBar {
    background: #1a1a32; border-radius: 5px; height: 10px;
    border: none; text-align: center; font-size: 10px; color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #5c5cff,stop:1 #8c5cff);
    border-radius: 5px;
}

/* ─── VIDEO FRAME ─── */
#videoFrame { background: #000000; border-radius: 8px; }

/* ─── STATUS BAR ─── */
QStatusBar { background: #0a0a18; color: #6060a0; font-size: 11px; border-top: 1px solid #1a1a30; }
"""

DIALOG_STYLE = """
QDialog { background: #0d0d1a; color: #e0e0f0; font-family: 'Segoe UI', Arial; font-size: 13px; }
QLabel { color: #a0a0c0; }
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #141428; border: 1px solid #2a2a4a; border-radius: 6px;
    padding: 6px; color: #e0e0f0;
}
QLineEdit:focus, QTextEdit:focus { border-color: #5c5cff; }
QPushButton {
    background: #1e1e3a; color: #c0c0e0;
    border: 1px solid #2e2e4e; border-radius: 6px; padding: 7px 16px;
}
QPushButton:hover { background: #28284a; color: white; }
QPushButton#primaryBtn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #5c5cff,stop:1 #8c5cff);
    color: white; border: none; font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7070ff,stop:1 #a070ff);
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #1a1a32; color: #c0c0e0; selection-background-color: #2a2a5a; }
"""
