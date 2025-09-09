import sys
import json
import threading
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                             QPushButton, QFileDialog, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QScreen

from ocr_logic import run_ocr_engine
from gui_overlay import OverlayWindow


class SelectionOverlay(QWidget):
    """A semi-transparent overlay for selecting a screen region."""
    regionSelected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geometry)

        self.begin = QPoint()
        self.end = QPoint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        pen = QPen(Qt.GlobalColor.red, 2)
        painter.setPen(pen)
        painter.drawRect(QRect(self.begin, self.end))

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()

        x1, y1 = self.begin.x(), self.begin.y()
        x2, y2 = self.end.x(), self.end.y()

        rect = {
            'left': min(x1, x2),
            'top': min(y1, y2),
            'width': abs(x1 - x2),
            'height': abs(y1 - y2)
        }

        self.regionSelected.emit(rect)


class SettingsWindow(QWidget):
    """The main settings GUI for the application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Umamusume OCR Helper - Settings")
        self.setGeometry(100, 100, 500, 250)
        self.settings = self.load_settings()

        self.selection_overlay = SelectionOverlay(self)
        self.selection_overlay.hide()

        self.selection_overlay.regionSelected.connect(self.region_selected)

        # --- Main Layout ---
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # --- Title ---
        title_label = QLabel("Welcome to UmaBuddy!")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(title_label)

        # --- Section 1: Region Selection ---
        char_region_button = QPushButton("Select Character Name Region")
        char_region_button.clicked.connect(lambda: self.start_selection("character_region"))
        self.char_region_label = QLabel(f"Current: {self.settings.get('character_region', 'Not set')}")
        self.layout.addWidget(char_region_button)
        self.layout.addWidget(self.char_region_label)

        event_region_button = QPushButton("Select Event Title Region")
        event_region_button.clicked.connect(lambda: self.start_selection("event_region"))
        self.event_region_label = QLabel(f"Current: {self.settings.get('event_region', 'Not set')}")
        self.layout.addWidget(event_region_button)
        self.layout.addWidget(self.event_region_label)

        # --- Spacer ---
        self.layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # --- Section 2: Start Button ---
        start_button = QPushButton("Save Settings and Start")
        start_button.setStyleSheet("font-size: 16px; padding: 10px;")
        start_button.clicked.connect(self.save_and_start)
        self.layout.addWidget(start_button)

        # --- Status Label ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.status_label)

    def start_selection(self, region_key):
        """Hides the main window and shows the selection overlay."""
        self.hide()
        self.region_key_to_set = region_key
        self.selection_overlay.show()

    def region_selected(self, rect):
        """Callback (slot) for when a region is selected in the overlay."""
        self.selection_overlay.hide()

        self.settings[self.region_key_to_set] = rect

        if self.region_key_to_set == "character_region":
            self.char_region_label.setText(f"Current: {rect}")
        elif self.region_key_to_set == "event_region":
            self.event_region_label.setText(f"Current: {rect}")

        self.show()

    def save_settings(self):
        """Saves the current settings to a JSON file."""
        try:
            with open("settings.json", "w") as f:
                json.dump(self.settings, f, indent=4)
            self.status_label.setText("Settings saved to settings.json")
            print("Settings saved to settings.json")
        except Exception as e:
            self.status_label.setText(f"Error saving settings: {e}")
            print(f"Error saving settings: {e}")

    def load_settings(self):
        """Loads settings from a JSON file if it exists."""
        try:
            with open("settings.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_and_start(self):
        """Saves settings and launches the OCR engine."""
        self.save_settings()
        self.status_label.setText("Settings saved. Initializing overlay and starting OCR engine...")
        print("Settings saved. Initializing overlay and starting OCR engine...")

        # Create the overlay window
        self.overlay_window = OverlayWindow()
        self.overlay_window.show_status_message("Initializing EasyOCR...\n(This may take a moment)")
        self.overlay_window.show()

        # Start the OCR engine in a separate thread
        self.ocr_thread = threading.Thread(target=run_ocr_engine, args=(self.overlay_window,))
        self.ocr_thread.daemon = True
        self.ocr_thread.start()

        self.close()
