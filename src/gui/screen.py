from src.backend.engine.emulator import Emulator

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


class Box(QWidget):
    def __init__(self, nlines):
        super().__init__()
        self.checkEnabled = QCheckBox()
        self.labelEnabled = QLabel()
        fields = QVBoxLayout()
        self.enabled = QHBoxLayout()
        self.enabled.setAlignment(Qt.AlignLeft)
        self.enabled.addWidget(self.checkEnabled)
        self.enabled.addWidget(self.labelEnabled)
        fields.addLayout(self.enabled)
        self.lines = list(QHBoxLayout() for _ in range(nlines))
        self.label = list(QLabel() for _ in range(nlines))
        self.text = list(QLineEdit() for _ in range(nlines))
        for i in range(nlines):
            self.text[i].setReadOnly(True)
            self.text[i].setFrame(False)
            self.lines[i].addWidget(self.label[i])
            self.lines[i].addWidget(self.text[i])
            self.lines[i].setAlignment(Qt.AlignLeft)
            fields.addLayout(self.lines[i])

        fields.setAlignment(Qt.AlignBottom)
        self.setLayout(fields)


class CashBox(Box):
    def __init__(self, emulator: Emulator):
        super().__init__(3)
        self.emulator = emulator
        self.labelEnabled.setText("Cash enabled")
        self.label[0].setText("Cash hits: ")
        self.label[1].setText("Cash misses: ")
        self.label[2].setText("Rate: ")
        self.checkEnabled.stateChanged.connect(self.turn)

    def turn(self):
        print("cash")


class PipeBox(Box):
    def __init__(self, emulator: Emulator):
        super().__init__(3)
        self.emulator = emulator
        self.labelEnabled.setText("Pipe enabled")
        self.label[0].setText("Pipe cycles: ")
        self.label[1].setText("Instructions: ")
        self.label[2].setText("Instructions per cycle: ")
        self.checkEnabled.stateChanged.connect(self.turn)

    def turn(self):
        print("pipe")

class Screen(QWidget):
    def __init__(self, emulator: Emulator):
        super().__init__()
        self.emulator = emulator
        self.initUI()

    def initUI(self):
        self.screen = QLabel()
        self.show_monitor(self.emulator.memory.video.image)
        self.emulator.memory.video.set_on_show(self.show_monitor)

        self.start = QPushButton("run", self)
        self.step = QPushButton("step", self)
        self.stop = QPushButton("stop", self)
        self.reset = QPushButton("reset", self)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start)
        buttons.addWidget(self.step)
        buttons.addWidget(self.stop)
        buttons.addWidget(self.reset)

        self.screen.setAlignment(Qt.AlignHCenter)
        self.cash = CashBox(self.emulator)
        self.pipe = PipeBox(self.emulator)
        stat = QHBoxLayout()

        stat.addWidget(self.cash)
        stat.addWidget(self.pipe)

        layout = QGridLayout()
        layout.addWidget(self.screen, 1, 0, 3, 3)
        layout.addLayout(buttons, 4, 0, 1, 3)
        layout.addLayout(stat, 5, 0, 1, 3)

        #layout = QVBoxLayout()
        #layout.addWidget(self.screen)
        #layout.addLayout(buttons)
        #layout.addLayout(stat)
        #layout.setAlignment(Qt.AlignVCenter)

        self.setLayout(layout)

    def show_monitor(self, image: QImage):
        self.screen.setPixmap(QPixmap.fromImage(image))

    def ereset(self, emu: Emulator):
        self.emulator = emu
        self.show_monitor(self.emulator.memory.video.image)
        self.emulator.memory.video.set_on_show(self.show_monitor)

