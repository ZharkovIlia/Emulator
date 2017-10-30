from PyQt5.QtGui import *
from src.backend.engine.emulator import Emulator
from src.backend.model.memory import Memory
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import sys


class BreakpointsView(QWidget):
    class BreakpointLine(QWidget):
        def __init__(self, emu: Emulator, address: str, data: str):
            super().__init__()
            self.emu = emu
            self.point = QCheckBox()
            self.point.setChecked(False)
            self.point.setEnabled(False)
            self.point.stateChanged.connect(self.send_breakpoint)
            self.address = QLabel(address)
            self.data = QLineEdit()
            self.data.setReadOnly(True)
            self.data.setText(data)

            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.point)
            layout.addWidget(self.address)
            layout.addWidget(self.data)

            self.setLayout(layout)

        def send_breakpoint(self, state):
            self.emu.toggle_breakpoint(int(self.address.text(), 8))

    def __init__(self, emu: Emulator, lines: int):
        super().__init__()
        self.emu = emu
        self.lines = lines
        self.initUI()

    def initUI(self):
        wight = len(oct(Memory.SIZE))
        self.add_format = '#0{}o'.format(wight)
        self.line_wigets = list(self.BreakpointLine(self.emu, "", "")
                                for _ in range(self.lines))
        self.fill(0)
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        for line in self.line_wigets:
            lay.addWidget(line)

        up = QPushButton("up")
        up.clicked.connect(self.move_up)

        down = QPushButton("down")
        down.clicked.connect(self.move_down)

        buttons = QVBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setAlignment(Qt.AlignCenter)
        buttons.addWidget(up)
        buttons.addWidget(down)

        wrap = QHBoxLayout()
        wrap.addLayout(lay)
        wrap.addLayout(buttons)

        self.setLayout(wrap)
        self.show()

    def fill(self, address):
        for i in range(self.lines):
            add = address + i * 2
            data, breakpoint = self.emu.disasm(add)

            self.line_wigets[i].address.setText(format(add, self.add_format))
            self.line_wigets[i].data.setText(data)
            self.change_box(self.line_wigets[i].point, data, breakpoint)

    def move_down(self):
        add = int(self.line_wigets[self.lines - 1].address.text(), 8) + 2
        if add < 0 or add >= Memory.SIZE:
            return

        data, breakpoint = self.emu.disasm(add)
        for i in range(self.lines - 1):
            self.line_wigets[i].address.setText(self.line_wigets[i + 1].address.text())
            self.line_wigets[i].data.setText(self.line_wigets[i + 1].data.text())
            self.line_wigets[i].point.setEnabled(self.line_wigets[i + 1].point.isEnabled())
            self.line_wigets[i].point.setChecked(self.line_wigets[i + 1].point.isChecked())

        self.line_wigets[self.lines - 1].address.setText(format(add, self.add_format))
        self.line_wigets[self.lines - 1].data.setText(data)

        self.change_box(self.line_wigets[self.lines - 1].point, data, breakpoint)

    def move_up(self):
        add = int(self.line_wigets[0].address.text(), 8) - 2
        if add < 0 or add >= Memory.SIZE:
            return
        data, breakpoint = self.emu.disasm(add)
        for i in range(self.lines - 1, -1, -1):
            self.line_wigets[i].address.setText(self.line_wigets[i - 1].address.text())
            self.line_wigets[i].data.setText(self.line_wigets[i - 1].data.text())
            self.line_wigets[i].point.setEnabled(self.line_wigets[i - 1].point.isEnabled())
            self.line_wigets[i].point.setChecked(self.line_wigets[i - 1].point.isChecked())

        self.line_wigets[0].address.setText(format(add, self.add_format))
        self.line_wigets[0].data.setText(data)
        
        self.change_box(self.line_wigets[0].point, data, breakpoint)

    def change_box(self, point: QCheckBox, data: str, breakpoint: bool):
        if data != "Not an instruction":
            point.setEnabled(True)
        else:
            point.setEnabled(False)
        point.setChecked(breakpoint)