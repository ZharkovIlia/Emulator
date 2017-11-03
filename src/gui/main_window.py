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
        viewer = CodeViewer(self.emulator)
        screen = Screen(self.emulator)
        layout = QHBoxLayout()
        layout.addWidget(screen)
        layout.addWidget(viewer)
        self.setLayout(layout)
        self.show()


app = QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec_())