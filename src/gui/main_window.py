from src.backend.engine.emulator import Emulator
from src.backend.model.memory import Memory
from src.backend.utils.exceptions import *
from src.gui.breakpoints_view import BreakpointsView

import sys

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.emulator = Emulator()

        self.initUI()

    def initUI(self):
        address_label = QLabel('Address')
        self.address_editor = QLineEdit()
        self.address_description = QLabel("Please, type address in OCTAL format")
        self.address_description.setStyleSheet("color: red")

        performance_label = QLabel('Performance')
        self.performance_box = QComboBox()
        self.performance_box.addItems(['data', 'instruction'])

        self.get_button = QPushButton('get', self)
        self.get_button.clicked.connect(self.get_address)

        choose_address = QGridLayout()
        choose_address.addWidget(address_label, 1, 0)
        choose_address.addWidget(self.address_editor, 1, 1)
        choose_address.addWidget(performance_label, 1, 2)
        choose_address.addWidget(self.performance_box, 1, 3)
        choose_address.addWidget(self.get_button, 1, 4)

        instruction_label = QLabel('Instruction')
        self.instruction_string = QLineEdit()
        self.instruction_string.setReadOnly(True)

        show_address = QHBoxLayout()
        show_address.addWidget(instruction_label)
        show_address.addWidget(self.instruction_string)

        self.breakpoint_table = BreakpointsView(self.emulator, 10)

        self.editor_layout = QVBoxLayout()
        self.editor_layout.setAlignment(Qt.AlignTop)
        self.editor_layout.addWidget(self.address_description)
        self.editor_layout.addLayout(choose_address)
        self.editor_layout.addLayout(show_address)
        self.editor_layout.addWidget(self.breakpoint_table)

        self.address_description.hide()

        self.setLayout(self.editor_layout)
        self.center()

        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def get_address(self):
        address_text = self.address_editor.text()
        try:
            address = int(address_text, 8)
            if address % 2 == 1:
                address -= 1

            try:
                if self.performance_box.currentIndex() == 0:
                    data_string = self.emulator.code(address)
                    self.instruction_string.setText(data_string)
                    self.address_description.hide()
                else:
                    data_string, _ = self.emulator.disasm(address)
                    self.instruction_string.setText(data_string)
                    self.address_description.hide()

                self.breakpoint_table.fill(address)

            except EmulatorWrongAddress as err:
                error_text = "\n\nType NON_NEGATIVE number less than " + oct(Memory.SIZE)
                QMessageBox.warning(self, 'Error',
                                    err.__str__() + error_text,
                                    QMessageBox.Ok,
                                    QMessageBox.Ok)
        except ValueError:
            self.address_description.show()


app = QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec_())