from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QLineEdit
from PyQt5.QtCore import Qt

from src.backend.engine.emulator import Emulator


class RegisterWindow(QWidget):
    class RegisterLine(QLabel):
        def __init__(self, name: int, value: int):
            super().__init__()
            self.name = QLabel("r{}: ".format(name))
            self.value = QLineEdit(format(value, 'o'))
            self.value.setReadOnly(True)
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.name)
            layout.addWidget(self.value)
            self.setLayout(layout)

        def set_value(self, value: int):
            self.value.setText(format(value, "o"))

    class StatusLine(QLabel):
        def __init__(self, name: str, value: bool):
            super().__init__()
            self.name = QLabel(name)
            self.value = QLineEdit(str(value))
            self.value.setReadOnly(True)
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.name)
            layout.addWidget(self.value)
            self.setLayout(layout)

        def set_value(self, value: bool):
            self.value.setText(str(value))

    def __init__(self, emulator: Emulator):
        super().__init__()
        self.emulator = emulator
        self.initUI()

    def initUI(self):
        self.num_of_registers = len(self.emulator.registers)
        self.register_lines = list()
        register_box = QVBoxLayout()
        register_box.setContentsMargins(0, 0, 0, 0)
        register_box.setSpacing(0)
        for i in range(self.num_of_registers):
            value = self.emulator.registers[i].get("word", False)
            self.register_lines.append(self.RegisterLine(i, value))
            register_box.addWidget(self.register_lines[i])

        program_st_box = QVBoxLayout()
        program_st_box.setContentsMargins(0, 0, 0, 0)
        program_st_box.setSpacing(0)
        program_st_box.setAlignment(Qt.AlignTop)
        bits = self.emulator.program_status.bits
        self.status_lines = list()
        for i in bits.keys():
            self.status_lines.append(self.StatusLine(i, bits[i]))
        for line in self.status_lines:
            program_st_box.addWidget(line)

        common_box = QHBoxLayout()
        common_box.addLayout(register_box)
        common_box.addLayout(program_st_box)
        self.setLayout(common_box)

    def update(self):
        for i in range(self.num_of_registers):
            value = self.emulator.registers[i].get("word", False)
            self.register_lines[i].set_value(value)

        for line in self.status_lines:
            line.set_value(self.emulator.program_status.get(line.name.text()))

    def reset(self, emu: Emulator):
        self.emulator = emu
        self.num_of_registers = len(self.emulator.registers)
        self.update()
