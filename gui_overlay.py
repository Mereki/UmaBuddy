from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class OverlayWindow(QWidget):
    """A transparent, always-on-top window to display OCR results."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(50, 50, 400, 300)  # Initial position and size

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # We'll use up to 3 labels to display outcomes
        self.outcome_labels = []
        for _ in range(3):
            label = QLabel("")
            label.setStyleSheet("""
                background-color: rgba(0, 0, 0, 180);
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            """)
            label.hide()  # Initially hidden
            self.layout.addWidget(label)
            self.outcome_labels.append(label)

    def update_outcomes(self, outcomes):
        """Displays a list of outcome strings on the overlay."""
        for i, label in enumerate(self.outcome_labels):
            if i < len(outcomes):
                label.setText(outcomes[i])
                label.show()
            else:
                label.hide()

    def clear_outcomes(self):
        """Hides all outcome labels."""
        for label in self.outcome_labels:
            label.hide()

    def show_status_message(self, message):
        """Displays a single, central status message."""
        # Hide all regular labels first
        self.clear_outcomes()
        # Use the first label to show the status
        status_label = self.outcome_labels[0]
        status_label.setText(message)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the text
        status_label.show()

