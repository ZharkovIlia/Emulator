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
        self.setWindowTitle("Emulator")
        self.initUI()

    def initUI(self):
        address_label = QLabel('Address')
        self.address_editor = QLineEdit(format(self.emulator.current_pc, 'o'))
        self.address_editor.editingFinished.connect(self.get_address)
        self.address_description = QLabel("Please, type address in OCTAL format")
        self.address_description.setStyleSheet("color: red")

        format_label = QLabel('Data type')
        self.format_box = QComboBox()
        self.format_box.addItems(['octal', 'instructions'])
        self.format_box.currentIndexChanged.connect(self.get_address)

        self.go_to_pc = QPushButton('Go to current pc', self)
        self.go_to_pc.clicked.connect(self.get_current)

        choose_address = QGridLayout()
        choose_address.addWidget(address_label, 1, 0)
        choose_address.addWidget(self.address_editor, 1, 1)
        choose_address.addWidget(format_label, 1, 2)
        choose_address.addWidget(self.format_box, 1, 3)
        choose_address.addWidget(self.go_to_pc, 2, 0, 1, 2)

        self.breakpoint_table = BreakpointsView(self.emulator, 10, self.format_box.currentText())

        self.editor_layout = QVBoxLayout()
        self.editor_layout.setAlignment(Qt.AlignTop)
        self.editor_layout.addWidget(self.address_description)
        self.editor_layout.addLayout(choose_address)
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

            self.breakpoint_table.fill(address, self.format_box.currentText())
            self.address_description.hide()

        except ValueError:
            self.address_description.show()
        except EmulatorWrongAddress as err:
            error_text = "\n\nType NON_NEGATIVE number LESS than " + oct(Memory.SIZE)
            QMessageBox.warning(self, 'Error',
                                err.__str__() + error_text,
                                QMessageBox.Ok,
                                QMessageBox.Ok)
    def get_current(self):
        self.address_editor.setText(format(self.emulator.current_pc, 'o'))
        self.get_address()

app = QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec_())