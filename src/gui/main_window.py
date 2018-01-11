from src.backend.engine.emulator import Emulator
from src.gui.code_viewer import CodeViewer
from src.gui.screen import Screen
from src.gui.registers import RegisterWindow

import sys

from PyQt5.QtWidgets import *


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.emulator = Emulator()
        self.initUI()

    def initUI(self):
        self.viewer = CodeViewer(self.emulator)
        self.registers = RegisterWindow(self.emulator)
        self.screen = Screen(self.emulator)

        right_part = QVBoxLayout()
        right_part.addWidget(self.registers)
        right_part.addWidget(self.viewer)

        layout = QHBoxLayout()
        layout.addWidget(self.screen)
        layout.addLayout(right_part)

        self.screen.start.clicked.connect(self.start)
        self.screen.step.clicked.connect(self.step)
        self.setLayout(layout)
        self.show()

    def start(self):
        self.emulator.run()
        self.viewer.get_current()
        self.registers.update()

    def step(self):
        self.emulator.step()
        self.viewer.get_current()
        self.registers.update()


from bitarray import bitarray

address = 36
bitarr = bitarray(endian='big')
bitarr.frombytes(address.to_bytes(2, byteorder='big', signed=False))
print(bitarr.to01())
string = int(bitarr[7:13].to01(), 2)
print(string)
exit(0)

app = QApplication(sys.argv)
window = MainWindow()

sys.exit(app.exec_())

