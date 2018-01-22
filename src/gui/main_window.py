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
        self.viewer = CodeViewer(self.emulator)
        self.registers = RegisterWindow(self.emulator)
        self.screen = Screen(self.emulator)
        #self.timer = QTimer()
        #self.timer.timeout.connect(self.load)

        right_part = QVBoxLayout()
        right_part.addWidget(self.registers)
        right_part.addWidget(self.viewer)

        layout = QHBoxLayout()
        layout.addWidget(self.screen)
        layout.addLayout(right_part)

        self.screen.start.clicked.connect(self.start)
        self.screen.step.clicked.connect(self.step)
        self.screen.stop.clicked.connect(self.stop)
        self.screen.reset.clicked.connect(self.reset)
        self.setLayout(layout)
        self.show()

    def start(self):
        self.screen.cash.checkEnabled.setEnabled(False)
        self.screen.pipe.checkEnabled.setEnabled(False)
        #self.timer.start(100)
        self.screen.start.setEnabled(False)
        self.screen.step.setEnabled(False)
        self.screen.reset.setEnabled(False)
        self.viewer.setEnabled(False)
        self.registers.setEnabled(False)
        self.emulator.stopped = False

        self.emuThread = EmulatorThread(self.emulator)
        self.emuThread.finished.connect(self.pause)
        self.emuThread.start()
        #self.emulator.run()

    def step(self):
        self.screen.cash.checkEnabled.setEnabled(False)
        self.screen.pipe.checkEnabled.setEnabled(False)
        self.emulator.step()
        self.viewer.get_current()
        self.registers.update()

    def pause(self):
        #self.timer.stop()
        self.screen.start.setEnabled(True)
        self.screen.step.setEnabled(True)
        self.screen.reset.setEnabled(True)
        self.viewer.setEnabled(True)
        self.registers.setEnabled(True)
        self.viewer.get_current()
        self.registers.update()
        self.emulator.memory.video.show()

    def stop(self):
        self.emulator.stopped = True

    #def load(self):
    #    self.emulator.memory.video.show()

    def reset(self):
        self.screen.cash.checkEnabled.setEnabled(True)
        self.screen.pipe.checkEnabled.setEnabled(True)
        self.emulator = Emulator()
        self.viewer.reset(self.emulator)
        self.registers.reset(self.emulator)
        self.screen.ereset(self.emulator)

        self.viewer.get_current()
        self.registers.update()
        self.emulator.memory.video.show()


app = QApplication(sys.argv)
window = MainWindow()

sys.exit(app.exec_())

