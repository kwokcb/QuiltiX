import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QHBoxLayout, QVBoxLayout, QDialog, QLabel, QCheckBox, QLineEdit, QPushButton, QWidget
from PyQt5 import QtGui  
from functools import partial

options = {}
options["bake_textures"] = False
options["bake_resolution"] = 1024

class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super(OptionsDialog, self).__init__(parent)
        self.setWindowTitle("Options")

        # Initialize boolean flag and integer value
        self.flag_value = False
        self.int_value = 0

        # Create widgets
        self.checkbox = QCheckBox("Bake Textures:")
        self.checkbox.setChecked(options["bake_textures"])

        self.int_label = QLabel("Bake Resolution:")
        self.int_input = QLineEdit()
        self.int_input.setText(str(options["bake_resolution"]))
        self.int_input.setValidator(QtGui.QIntValidator())
        self.int_input.setMaxLength(4)  # Set maximum length to 4 digits

        # Create OK and Cancel buttons
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        # Connect buttons to slots
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Connect signals to custom functions
        self.checkbox.stateChanged.connect(self.onCheckboxStateChanged)
        self.int_input.textChanged.connect(self.onIntInputChanged)

        # Create layout
        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)

        # Create a horizontal layout for the label and integer input
        int_layout = QHBoxLayout()
        int_layout.addWidget(self.int_label)
        int_layout.addWidget(self.int_input)
        layout.addLayout(int_layout)

        layout.addWidget(self.ok_button)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def setFlagValue(self, value):
        self.flag_value = value

    def getFlagValue(self):
        return self.flag_value

    def setIntValue(self, value):
        self.int_value = value

    def getIntValue(self):
        return self.int_value

    def onCheckboxStateChanged(self, state):
        # Custom function for checkbox state change
        options["bake_textures"] = (state == Qt.Checked)
        print("Checkbox state changed:", state)

    def onIntInputChanged(self, text):
        # Custom function for integer input change
        value = int(text) if text else 0
        options["bake_resolution"] = value
        print("Integer state changed:", value)

class OptionsDialog2(QDialog):
    def __init__(self, options, parent=None):
        super(OptionsDialog, self).__init__(parent)
        self.setWindowTitle("Options")

        # Initialize boolean flag and integer value
        self.flag_value = options["bake_textures"]        
        self.int_value = options["bake_resolution"]

        # Create widgets
        self.checkbox = QCheckBox("Bake Textures")
        self.int_label = QLabel("Bake Resolution:")
        self.int_input = QLineEdit()
        self.int_input.setText(str(self.int_value))
        self.int_input.setValidator(QtGui.QIntValidator())
        self.int_input.setMaxLength(4)  # Set maximum length to 4 digits

        # Create OK and Cancel buttons
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        # Connect buttons to slots
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Create layout
        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)

        # Create a horizontal layout for the label and integer input
        int_layout = QHBoxLayout()
        int_layout.addWidget(self.int_label)
        int_layout.addWidget(self.int_input)
        layout.addLayout(int_layout)

        layout.addWidget(self.ok_button)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def setFlagValue(self, value):
        self.flag_value = value

    def getFlagValue(self):
        return self.flag_value

    def setIntValue(self, value):
        self.int_value = value

    def getIntValue(self):
        return self.int_value

class ExampleApp(QMainWindow):


    def __init__(self):
        super().__init__()

        # Create a menu bar
        menubar = self.menuBar()

        # Create a file menu
        fileMenu = menubar.addMenu('File')

        # Add an option to the file menu
        optionsAction = fileMenu.addAction('Options')
        optionsAction.triggered.connect(self.showOptionsDialog)

    def showOptionsDialog(self):
        dialog = OptionsDialog(self)

        # Display the dialog and handle the result
        result = dialog.exec_()
        if result == QDialog.Accepted:
            # Retrieve the values from the dialog
            flag_value = dialog.getFlagValue()
            int_value = int(dialog.getIntValue())  # Convert to integer
            
            # Use the retrieved values as needed (e.g., print them)
            print("Flag Value:", flag_value)
            print("Integer Value:", int_value)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ExampleApp()
    window.setGeometry(100, 100, 500, 300)
    window.show()
    sys.exit(app.exec_())
