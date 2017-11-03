from src.backend.engine.emulator import Emulator
from src.gui.code_viewer import CodeViewer
from src.gui.screen import Screen

import sys

from PyQt5.QtWidgets import *


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.emulator = Emulator()
        self.initUI()

    def initUI(self):
        self.viewer = CodeViewer(self.emulator)
        self.screen = Screen(self.emulator)
        layout = QHBoxLayout()
        layout.addWidget(self.screen)
        layout.addWidget(self.viewer)
        self.screen.start.clicked.connect(self.start)
        self.screen.step.clicked.connect(self.step)
        self.setLayout(layout)
        self.show()

    def start(self):
        self.emulator.run()
        self.viewer.get_current()

    def step(self):
        self.emulator.step()
        self.viewer.get_current()

app = QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec_())