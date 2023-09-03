from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import pyqtSignal


class CustomPbar(QProgressBar):
    progressSignal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_progress(self):
        self.setValue(self.value() + 1)

class SelectDirectoryLayout(QWidget):
    def __init__(self, label, button_target=None) -> None:
        super().__init__()
        self.directory_layout = QVBoxLayout()
        self.__label_layout = QHBoxLayout()

        self.directory_label = QLabel(label)
        self.directory_textfield = QLineEdit(self)

        self.button = QPushButton('...')
        self.button.setMaximumSize(25,25)
        if button_target:
            self.button.clicked.connect(button_target)

        self.__label_layout.addWidget(self.directory_textfield)
        self.__label_layout.addWidget(self.button)
        
        self.directory_layout.addWidget(self.directory_label)
        self.directory_layout.addLayout(self.__label_layout)

    def set_button_target(self, button_target):
        self.button.clicked.connect(button_target)
