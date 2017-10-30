from src.backend.engine.emulator import Emulator
from src.backend.model.memory import Memory
from src.backend.utils.disasm_instruction import DisasmInstruction, DisasmState
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
            self.style = ""

            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.point)
            layout.addWidget(self.address)
            layout.addWidget(self.data)

            self.setLayout(layout)

        def send_breakpoint(self, state):
            self.set_checked(state == Qt.Checked)
            self.emu.toggle_breakpoint(int(self.address.text(), 8))

        def set_checked(self, c: bool):
            if c:
                style = "background: yellow"
            else:
                style = ""
            self.point.setStyleSheet(style)
            self.address.setStyleSheet(style)
            self.data.setStyleSheet(style)

    def assign_line(self, one: BreakpointLine, another: BreakpointLine):
        one.address.setText(another.address.text())
        one.data.setText(another.data.text())
        one.point.setEnabled(another.point.isEnabled())
        one.point.setChecked(another.point.isChecked())

    def __init__(self, emu: Emulator, lines: int, format_str: str):
        super().__init__()
        self.emu = emu
        self.lines = lines
        self.format_str = format_str
        self.initUI()

    def initUI(self):
        width = len(oct(Memory.SIZE)) -2
        self.add_format = '0{}o'.format(width)
        self.line_widgets = list(self.BreakpointLine(self.emu, "", "")
                                 for _ in range(self.lines))
        self.fill(self.emu.current_pc, self.format_str)
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

    def fill(self, address, format_str):
        self.format_str = format_str

        data_list = self.emu.disasm(address, self.lines, format_str)
        for i in range(self.lines):
            add, data, breakpoint = data_list[i]
            self.line_widgets[i].address.setText(format(add, self.add_format))
            self.line_widgets[i].data.setText(str(data))
            self.change_box(self.line_widgets[i].point, data, breakpoint)

    def move_down(self):
        add = int(self.line_widgets[1].address.text(), 8)
        self.fill(add, self.format_str)

    def move_up(self):
        add = int(self.line_widgets[0].address.text(), 8) - 2
        if add < 0:
            return
        self.fill(add, self.format_str)

    def change_box(self, point: QCheckBox, data: DisasmInstruction, breakpoint: bool):
        if data.state is DisasmState.NOT_AN_INSTRUCTION:
            point.setEnabled(False)
        else:
            point.setEnabled(True)

        point.setChecked(breakpoint)