from src.backend.engine.emulator import Emulator
from src.backend.model.memory import Memory
from src.backend.utils.exceptions import *
from src.gui.breakpoints_view import BreakpointsView

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class CodeViewer(QWidget):
    def __init__(self, emulator: Emulator):
        super().__init__()
        self.emulator = emulator
        self.setWindowTitle("Emulator")
        self.initUI()

    def initUI(self):
        address_label = QLabel('Address')
        self.address_editor = QLineEdit(format(self.emulator.current_pc, 'o'))
        self.address_editor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.address_description = QLabel("Please, type address in OCTAL format")
        self.address_description.setStyleSheet("color: red")

        format_label = QLabel('Data type')
        self.format_box = QComboBox()
        self.format_box.addItems(['instructions', 'octal'])

        self.go_to_pc = QPushButton('  Go to current pc  ', self)
        self.go_to_pc.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        choose_address = QHBoxLayout()
        choose_address.setAlignment(Qt.AlignLeft)
        choose_address.addWidget(address_label)
        choose_address.addWidget(self.address_editor)
        choose_address.addWidget(format_label)
        choose_address.addWidget(self.format_box)
        #choose_address.addWidget(self.go_to_pc)
        self._numLinesInTable = 15
        self.breakpoint_table = BreakpointsView(self.emulator,
                                                self._numLinesInTable,
                                                self.format_box.currentText())
        self.address_editor.editingFinished.connect(self.get_chosen_address)
        self.format_box.currentIndexChanged.connect(self.get_after_type_changed)
        self.go_to_pc.clicked.connect(self.get_current)

        self.editor_layout = QVBoxLayout()
        self.editor_layout.setAlignment(Qt.AlignTop)
        self.editor_layout.addWidget(self.address_description)
        self.editor_layout.addLayout(choose_address)
        self.editor_layout.addWidget(self.go_to_pc)
        self.editor_layout.addWidget(self.breakpoint_table)

        self.address_description.hide()

        self.setLayout(self.editor_layout)

    def get_address(self, address: int):
        if address % 2 == 1:
            address -= 1
        try:
            self.breakpoint_table.fill(address, self.format_box.currentText())
            self.address_description.hide()
        except EmulatorWrongAddress as err:
            error_text = "\n\nType NON_NEGATIVE number LESS than " + oct(Memory.SIZE)
            QMessageBox.warning(self, 'Error',
                                err.__str__() + error_text,
                                QMessageBox.Ok,
                                QMessageBox.Ok)

    def get_chosen_address(self):
        address_text = self.address_editor.text()
        try:
            address = int(address_text, 8)
            self.get_address(address)
        except ValueError:
            self.address_description.show()

    def get_after_type_changed(self):
        address_text = self.breakpoint_table.line_widgets[0].address.text()
        address = int(address_text, 8)
        self.get_address(address)

    def get_current(self):
        self.get_address(self.emulator.current_pc)

    def reset(self, emu: Emulator):
        self.emulator = emu
        self.breakpoint_table.reset(self.emulator)
