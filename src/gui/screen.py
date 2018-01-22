from src.backend.engine.emulator import Emulator

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


class Box(QWidget):
    def __init__(self, nlines):
        super().__init__()
        self.checkEnabled = QCheckBox()
        self.checkEnabled.setChecked(False)
        fields = QVBoxLayout()
        fields.addWidget(self.checkEnabled)
        self.lines = list(QHBoxLayout() for _ in range(nlines))
        self.label = list(QLabel() for _ in range(nlines))
        self.text = list(QLabel() for _ in range(nlines))
        for i in range(nlines):
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
        self.emulator.dcash.enabled = False
        self.emulator.icash.enabled = False
        self.checkEnabled.setText("Cash enabled")
        self.label[0].setText("Cash hits: ")
        self.label[1].setText("Cash misses: ")
        self.label[2].setText("Cash rate: ")
        self.checkEnabled.stateChanged.connect(self.turn)

        hits = self.emulator.icash.hits + self.emulator.dcash.hits
        misses = self.emulator.icash.misses + self.emulator.dcash.misses
        self.text[0].setText(str(hits))
        self.text[1].setText(str(misses))
        if hits + misses != 0:
            self.text[2].setText('%.2f' % (hits / (hits + misses)))
        else:
            self.text[2].setText('-')

    def turn(self):
        self.emulator.dcash.enabled = self.checkEnabled.isChecked()
        self.emulator.icash.enabled = self.checkEnabled.isChecked()

    def get_stat(self):
        hits = self.emulator.icash.hits + self.emulator.dcash.hits
        misses = self.emulator.icash.misses + self.emulator.dcash.misses
        self.text[0].setText(str(hits))
        self.text[1].setText(str(misses))
        if hits + misses != 0:
            self.text[2].setText('%.2f' % (hits / (hits + misses)))
        else:
            self.text[2].setText('-')

    def reset(self, emu: Emulator):
        self.emulator = emu
        self.get_stat()
        self.checkEnabled.setChecked(False)
        self.emulator.dcash.enabled = False
        self.emulator.icash.enabled = False


class PipeBox(Box):
    def __init__(self, emulator: Emulator):
        super().__init__(3)
        self.emulator = emulator
        self.emulator.pipe.enabled = False
        self.checkEnabled.setText("Pipe enabled")
        self.label[0].setText("Cpu cycles: ")
        self.label[1].setText("Instructions: ")
        self.label[2].setText("cycles/instruction: ")
        self.checkEnabled.stateChanged.connect(self.turn)

        cycles = self.emulator.pipe.cycles
        instructions = self.emulator.pipe.instructions
        self.text[0].setText(str(cycles))
        self.text[1].setText(str(instructions))
        if instructions != 0:
            self.text[2].setText('%.2f' % (cycles / instructions))
        else:
            self.text[2].setText('-')

    def turn(self):
        self.emulator.pipe.enabled = self.checkEnabled.isChecked()

    def get_stat(self):
        cycles = self.emulator.pipe.cycles
        instructions = self.emulator.pipe.instructions
        self.text[0].setText(str(cycles))
        self.text[1].setText(str(instructions))
        if instructions != 0:
            self.text[2].setText('%.2f' % (cycles / instructions))
        else:
            self.text[2].setText('-')

    def reset(self, emu: Emulator):
        self.emulator = emu
        self.get_stat()
        self.checkEnabled.setChecked(False)
        self.emulator.pipe.enabled = False


class ScreenField(QLabel):
    def __init__(self, emu: Emulator):
        super().__init__()
        self.emulator = emu
        self.show_monitor(self.emulator.memory.video.image)
        self.emulator.memory.video.set_on_show(self.show_monitor)
        self.setFocusPolicy(Qt.ClickFocus)
        #self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(self.emulator.memory.video.mode.height,
                          self.emulator.memory.video.mode.width)


    def keyPressEvent(self, e):
        print(e.text())

    def focusInEvent(self, QFocusEvent):
        self.setFrameStyle(1)

    def focusOutEvent(self, QFocusEvent):
        self.setFrameStyle(0)

    def show_monitor(self, image: QImage):
        self.setPixmap(QPixmap.fromImage(image))

    def reset(self, emu: Emulator):
        self.emulator = emu
        self.show_monitor(self.emulator.memory.video.image)
        self.emulator.memory.video.set_on_show(self.show_monitor)


class Screen(QWidget):
    def __init__(self, emulator: Emulator):
        super().__init__()
        self.emulator = emulator
        self.initUI()

    def initUI(self):
        self.screen = ScreenField(self.emulator)

        self.start = QPushButton("run", self)
        self.step = QPushButton("step", self)
        self.stop = QPushButton("stop", self)
        self.reset = QPushButton("reset", self)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start)
        buttons.addWidget(self.step)
        buttons.addWidget(self.stop)
        buttons.addWidget(self.reset)
        buttons.setContentsMargins(10, 10, 10, 10)

        l = QHBoxLayout()
        l.addWidget(self.screen)
        l.setContentsMargins(10, 10, 10, 10)

#        self.screen.setAlignment(Qt.AlignCenter)
        self.cash = CashBox(self.emulator)
        self.pipe = PipeBox(self.emulator)
        stat = QHBoxLayout()

        stat.addWidget(self.cash)
        stat.addWidget(self.pipe)

        layout = QGridLayout()
        #layout.addWidget(self.screen, 1, 0, 2, 2)
        layout.addLayout(l, 0, 0, 2, 2)
        layout.addLayout(buttons, 3, 0, 1, 2)
        layout.addWidget(self.cash, 4, 0)
        layout.addWidget(self.pipe, 4, 1)
        #layout.addLayout(stat, 5, 0, 1, 3)

        #layout = QVBoxLayout()
        #layout.addWidget(self.screen)
        #layout.addLayout(buttons)
        #layout.addLayout(stat)
        layout.setAlignment(Qt.AlignTop)

        self.setLayout(layout)

    def ereset(self, emu: Emulator):
        self.emulator = emu
        self.cash.reset(emu)
        self.pipe.reset(emu)
        self.screen.reset(emu)

