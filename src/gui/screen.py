from src.backend.engine.emulator import Emulator

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QImage


class Screen(QWidget):
    def __init__(self, emulator: Emulator):
        super().__init__()
        self.emulator = emulator
        self.initUI()

    def initUI(self):
        self.screen = QLabel()
        self.screen.setStyleSheet("border: 2px solid black")
        self.show_monitor(self.emulator.memory.video.image)

        self.start = QPushButton("run", self)
        self.step = QPushButton("step", self)
        self.stop = QPushButton("stop", self)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start)
        buttons.addWidget(self.step)
        buttons.addWidget(self.stop)

        layout = QGridLayout()
        layout.addWidget(self.screen, 1, 0, 3, 3)
        layout.addLayout(buttons, 4, 0, 1, 3)

        self.setLayout(layout)

    def show_monitor(self, image: QImage):
        self.screen.setPixmap(QPixmap.fromImage(image))
