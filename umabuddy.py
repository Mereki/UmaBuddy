import sys
from PyQt6.QtWidgets import QApplication
from gui_setup import SettingsWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    settings_window = SettingsWindow()
    settings_window.show()

    sys.exit(app.exec())

