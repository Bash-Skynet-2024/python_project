import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt


class MessengerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up the main window
        self.setWindowTitle("Dark Mode Messenger")
        self.setGeometry(100, 100, 500, 600)
        self.setStyleSheet("background-color: #2a2f32;")

        # Main Widget and Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header_label = QLabel("Messenger", self)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet(
            "background-color: #202c33; color: white; font-size: 18px; font-weight: bold; padding: 10px;"
        )
        main_layout.addWidget(header_label)

        # Chat Display Area
        self.chat_display = QTextEdit(self)
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(
            "background-color: #131c21; color: #e1e1e1; font-size: 14px; padding: 10px; border: none;"
        )
        main_layout.addWidget(self.chat_display)

        # Bottom Input and Buttons
        bottom_layout = QHBoxLayout()
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setStyleSheet(
            "background-color: #1e282e; color: #e1e1e1; font-size: 14px; padding: 5px; border: none;"
        )
        bottom_layout.addWidget(self.message_input)

        send_button = QPushButton("Send", self)
        send_button.setStyleSheet(
            "background-color: #075e54; color: white; font-size: 14px; font-weight: bold; padding: 5px;"
        )
        send_button.clicked.connect(self.send_message)
        bottom_layout.addWidget(send_button)

        file_button = QPushButton("Add File", self)
        file_button.setStyleSheet(
            "background-color: #128c7e; color: white; font-size: 14px; font-weight: bold; padding: 5px;"
        )
        file_button.clicked.connect(self.add_file)
        bottom_layout.addWidget(file_button)

        main_layout.addLayout(bottom_layout)

    def send_message(self):
        """Handles sending a message."""
        message = self.message_input.text().strip()
        if message:
            self.display_message("You", message)
            self.message_input.clear()
        else:
            QMessageBox.warning(self, "Warning", "Message cannot be empty!")

    def display_message(self, sender, message):
        """Displays a message in the chat window."""
        self.chat_display.append(f"<b>{sender}:</b> {message}")

    def add_file(self):
        """Opens a file dialog to select a file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.display_message("You", f"Sent a file: {file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MessengerApp()
    window.show()
    sys.exit(app.exec())
