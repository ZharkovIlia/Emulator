from src.backend.engine.emulator import Emulator
from src.gui.code_viewer import CodeViewer
from src.gui.screen import Screen
from src.gui.registers import RegisterWindow

import sys

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
#from PyQt5.QtCore import QThread
#from PyQt5.QtCore import QTimer


class EmulatorThread(QThread):
    def __init__(self, emulator: Emulator):
        super().__init__()
        self.emu = emulator

    def run(self):
        self.emu.run()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.emulator = Emulator()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('pdp11 emulator viewer')
        self.viewer = CodeViewer(self.emulator)
        self.registers = RegisterWindow(self.emulator)
        self.screen = Screen(self.emulator)
        self.timer = QTimer()
        self.timer.timeout.connect(self.load)

        right_part = QGridLayout()
        right_part.addWidget(self.registers, 0, 0, 1, 1)
        right_part.addWidget(self.viewer, 1, 0, 2, 1)
        right_part.setAlignment(Qt.AlignTop)

        #layout = QHBoxLayout()
        #layout.addWidget(self.screen)
        #layout.addLayout(right_part)

        layout = QGridLayout()
        layout.addWidget(self.screen, 0, 0)
        layout.addLayout(right_part, 0, 1)
        layout.setColumnStretch(1, 2)

        self.screen.start.clicked.connect(self.start)
        self.screen.step.clicked.connect(self.step)
        self.screen.stop.clicked.connect(self.stop)
        self.screen.reset.clicked.connect(self.reset)
        self.setLayout(layout)
        self.show()

    def start(self):
        self.screen.cash.checkEnabled.setEnabled(False)
        self.screen.pipe.checkEnabled.setEnabled(False)
        self.screen.clearStat.setEnabled(False)
        self.timer.start(100)
        self.screen.start.setEnabled(False)
        self.screen.step.setEnabled(False)
        self.screen.reset.setEnabled(False)
        self.viewer.setEnabled(False)
        self.registers.setEnabled(False)
        self.emulator.stopped = False
        self.screen.screen.setFocus()

        self.emuThread = EmulatorThread(self.emulator)
        self.emuThread.finished.connect(self.pause)
        self.emuThread.start()
        #self.emulator.run()

    def step(self):
        self.screen.cash.checkEnabled.setEnabled(False)
        self.screen.pipe.checkEnabled.setEnabled(False)
        self.screen.screen.setFocus()
        self.emulator.step()
        self.viewer.get_current()
        self.registers.update()
        self.screen.pipe.get_stat()
        self.screen.cash.get_stat()

    def pause(self):
        self.timer.stop()
        self.screen.start.setEnabled(True)
        self.screen.step.setEnabled(True)
        self.screen.clearStat.setEnabled(True)
        self.screen.reset.setEnabled(True)
        self.viewer.setEnabled(True)
        self.registers.setEnabled(True)
        self.viewer.get_current()
        self.registers.update()
        self.screen.pipe.get_stat()
        self.screen.cash.get_stat()

    def stop(self):
        self.emulator.stopped = True

    def load(self):
        #self.emulator.memory.video.show()
        self.screen.pipe.get_stat()
        self.screen.cash.get_stat()

    def reset(self):
        self.screen.cash.checkEnabled.setEnabled(True)
        self.screen.pipe.checkEnabled.setEnabled(True)
        self.emulator = Emulator()
        self.viewer.reset(self.emulator)
        self.registers.reset(self.emulator)
        self.screen.ereset(self.emulator)

        self.viewer.get_current()
        self.registers.update()

app = QApplication(sys.argv)
window = MainWindow()

sys.exit(app.exec_())

