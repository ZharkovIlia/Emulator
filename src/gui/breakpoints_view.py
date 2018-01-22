from src.backend.engine.emulator import Emulator
from src.backend.model.memory import Memory
from src.backend.utils.disasm_instruction import DisasmInstruction, DisasmState
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class BreakpointsView(QWidget):
    class BreakpointLine(QLabel):
        def __init__(self, emu: Emulator, address: str, data: str):
            super().__init__()
            self.emu = emu
            self.point = QCheckBox()
            self.point.setChecked(False)
            self.point.setEnabled(False)
            self.point.stateChanged.connect(self.send_breakpoint)
            self.address = QLabel(address)
            self.data = QLineEdit()
            self.data.setFrame(False)
            self.data.setReadOnly(True)
            self.data.setText(data)

            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.point)
            layout.addWidget(self.address)
            layout.addWidget(self.data)

            self.setAutoFillBackground(True)
            self.setStyleSheet("background: white")
            self.setLayout(layout)

        def send_breakpoint(self, state):
            self.set_checked(state == Qt.Checked)
            self.emu.breakpoint(address=int(self.address.text(), 8), set=self.point.isChecked())

        def set_current(self, c: bool):
            self.set_color(c, self.point.isChecked())

        def set_checked(self, c: bool):
            self.point.setChecked(c)
            p = (int(self.address.text(), 8) == self.emu.current_pc)
            self.set_color(c, p)

        def set_color(self, check: bool, current: bool):
            if check and current:
                self.setStyleSheet("background: #C896FF")
                self.data.setStyleSheet("background: #C896FF")
            elif check:
                self.setStyleSheet("background: #FAB4BE")
                self.data.setStyleSheet("background: #FAB4BE")
            elif current:
                self.setStyleSheet("background: #96C8FA")
                self.data.setStyleSheet("background: #96C8FA")
            else:
                self.setStyleSheet("background: white")
                self.data.setStyleSheet("background: white")

        def reset(self, emu: Emulator):
            self.emu = emu

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
        wlay = QFrame()
        wlay.setLayout(lay)
        wlay.setObjectName("kyky")
        wlay.setStyleSheet("#kyky{border: 7px solid white}")

        up = QToolButton()
        up.setArrowType(Qt.UpArrow)
        up.setAutoRepeat(True)
        up.clicked.connect(self.move_up)

        down = QToolButton()
        down.setArrowType(Qt.DownArrow)
        down.setAutoRepeat(True)
        down.clicked.connect(self.move_down)

        buttons = QVBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setAlignment(Qt.AlignCenter)
        buttons.addWidget(up)
        buttons.addWidget(down)

        wrap = QHBoxLayout()
        wrap.addWidget(wlay)
        wrap.addLayout(buttons)

        self.setFocusPolicy(Qt.ClickFocus)

        self.setLayout(wrap)
        self.show()

    def fill(self, address, format_str):
        self.format_str = format_str

        data_list = self.emu.disasm(address, self.lines, format_str)
        for i in range(self.lines):
            add, data, breakpoint = data_list[i]
            self.line_widgets[i].address.setText(format(add, self.add_format))
            self.line_widgets[i].data.setText(str(data))
            self.line_widgets[i].set_current(add == self.emu.current_pc)
            self.change_box(self.line_widgets[i], data, breakpoint)

    def move_down(self):
        add = int(self.line_widgets[1].address.text(), 8)
        self.fill(add, self.format_str)

    def move_up(self):
        add = int(self.line_widgets[0].address.text(), 8) - 2
        if add < 0:
            return
        self.fill(add, self.format_str)

    def change_box(self, line: BreakpointLine, data: DisasmInstruction, breakpoint: bool):
        if data.state is DisasmState.NOT_AN_INSTRUCTION:
            line.point.setEnabled(False)
        else:
            line.point.setEnabled(True)

        line.set_checked(breakpoint)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Up:
            self.move_up()
        elif e.key() == Qt.Key_Down:
            self.move_down()

    def reset(self, emu: Emulator):
        self.emu = emu
        for i in range(self.lines):
            self.line_widgets[i].reset(self.emu)
        self.fill(self.emu.current_pc, self.format_str)
