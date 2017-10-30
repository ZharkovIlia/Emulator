from src.backend.engine.emulator import Emulator
from src.backend.model.memory import Memory
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


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

    def assign_line(self, one: BreakpointLine, another: BreakpointLine):
        one.address.setText(another.address.text())
        one.data.setText(another.data.text())
        one.point.setEnabled(another.point.isEnabled())
        one.point.setChecked(another.point.isChecked())

    def __init__(self, emu: Emulator, lines: int, format_index: int):
        super().__init__()
        self.emu = emu
        self.lines = lines
        self.format_index = format_index
        self.initUI()

    def initUI(self):
        wight = len(oct(Memory.SIZE)) -2
        self.add_format = '0{}o'.format(wight)
        self.line_widgets = list(self.BreakpointLine(self.emu, "", "")
                                 for _ in range(self.lines))
        self.fill(0, self.format_index)
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        for line in self.line_widgets:
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

    def fill(self, address, format_index):
        self.format_index = format_index
        for i in range(self.lines):
            add = address + i * 2

            if self.format_index == 0:
                data, breakpoint = self.emu.code(add)
            else:
                data, breakpoint = self.emu.disasm(add)

            self.line_widgets[i].address.setText(format(add, self.add_format))
            self.line_widgets[i].data.setText(data)
            self.change_box(self.line_widgets[i].point, data, breakpoint)

    def move_down(self):
        add = int(self.line_widgets[self.lines - 1].address.text(), 8) + 2
        if add < 0 or add >= Memory.SIZE:
            return

        if self.format_index == 0:
            data, breakpoint = self.emu.code(add)
        else:
            data, breakpoint = self.emu.disasm(add)

        for i in range(self.lines - 1):
            self.assign_line(self.line_widgets[i], self.line_widgets[i + 1])

        self.line_widgets[self.lines - 1].address.setText(format(add, self.add_format))
        self.line_widgets[self.lines - 1].data.setText(data)
        self.change_box(self.line_widgets[self.lines - 1].point, data, breakpoint)

    def move_up(self):
        add = int(self.line_widgets[0].address.text(), 8) - 2
        if add < 0 or add >= Memory.SIZE:
            return

        if self.format_index == 0:
            data, breakpoint = self.emu.code(add)
        else:
            data, breakpoint = self.emu.disasm(add)

        for i in range(self.lines - 1, 0, -1):
            self.assign_line(self.line_widgets[i], self.line_widgets[i - 1])

        self.line_widgets[0].address.setText(format(add, self.add_format))
        self.line_widgets[0].data.setText(data)
        self.change_box(self.line_widgets[0].point, data, breakpoint)

    def change_box(self, point: QCheckBox, data: str, breakpoint: bool):
        if self.format_index == 0:
            point.setEnabled(False)
        elif data != "Not an instruction" and data is not None:
            point.setEnabled(True)
        else:
            point.setEnabled(False)
        point.setChecked(breakpoint)