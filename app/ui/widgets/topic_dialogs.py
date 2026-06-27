"""
app/ui/widgets/topic_dialogs.py — Dialog thêm/sửa Chủ đề, Chương, Bài
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QDialogButtonBox, QLabel, QComboBox
)
from app.ui.styles import DIALOG_STYLE


class ChuDeDialog(QDialog):
    def __init__(self, ten="", mo_ta="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chủ đề")
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.inp_ten = QLineEdit(ten)
        self.inp_ten.setPlaceholderText("Tên chủ đề...")
        self.inp_mota = QTextEdit()
        self.inp_mota.setPlainText(mo_ta)
        self.inp_mota.setPlaceholderText("Mô tả (tùy chọn)...")
        self.inp_mota.setMaximumHeight(80)
        form.addRow("Tên:", self.inp_ten)
        form.addRow("Mô tả:", self.inp_mota)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {"ten": self.inp_ten.text().strip(), "mo_ta": self.inp_mota.toPlainText().strip()}


class ChuongDialog(QDialog):
    def __init__(self, chu_de_list, ten="", chu_de_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chương")
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.cb_chu_de = QComboBox()
        for id_, name in chu_de_list:
            self.cb_chu_de.addItem(name, id_)
        if chu_de_id:
            idx = self.cb_chu_de.findData(chu_de_id)
            if idx >= 0:
                self.cb_chu_de.setCurrentIndex(idx)
        self.inp_ten = QLineEdit(ten)
        self.inp_ten.setPlaceholderText("Tên chương...")
        form.addRow("Chủ đề:", self.cb_chu_de)
        form.addRow("Tên chương:", self.inp_ten)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {"ten": self.inp_ten.text().strip(), "chu_de_id": self.cb_chu_de.currentData()}


class BaiDialog(QDialog):
    def __init__(self, chuong_list, ten="", chuong_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bài")
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_STYLE)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.cb_chuong = QComboBox()
        for id_, name in chuong_list:
            self.cb_chuong.addItem(name, id_)
        if chuong_id:
            idx = self.cb_chuong.findData(chuong_id)
            if idx >= 0:
                self.cb_chuong.setCurrentIndex(idx)
        self.inp_ten = QLineEdit(ten)
        self.inp_ten.setPlaceholderText("Tên bài...")
        form.addRow("Chương:", self.cb_chuong)
        form.addRow("Tên bài:", self.inp_ten)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primaryBtn")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {"ten": self.inp_ten.text().strip(), "chuong_id": self.cb_chuong.currentData()}
