import sys
from PyQt6.QtWidgets import QApplication
from gui_setup import SettingsWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # THE FIX: This crucial line tells the application not to exit when the
    # settings window is closed, allowing the overlay to remain open.
    app.setQuitOnLastWindowClosed(False)

    settings_window = SettingsWindow()
    settings_window.show()

    sys.exit(app.exec())

