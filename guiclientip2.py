


import os
import sys
import socket
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QMessageBox, QInputDialog, QFileDialog
)
from PyQt6.QtCore import QThread, pyqtSignal

# Network Thread to handle server communication
class NetworkThread(QThread):
    update_message = pyqtSignal(str)
    connection_status = pyqtSignal(str)
    pair_request = pyqtSignal(str)
    file_received = pyqtSignal(str)

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.running = True

    def run(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.connection_status.emit(f"Connected to {self.host}:{self.port}")

            while self.running:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message.startswith("PAIR_REQUEST:"):
                    sender_ip = message.split(":")[1]
                    self.pair_request.emit(sender_ip)
                elif message.startswith("FILE:"):
                    file_name, file_size = message.split(":")[1], int(message.split(":")[2])
                    self.receive_file(file_name, file_size)
                elif message:
                    self.update_message.emit(message)
        except Exception as e:
            self.connection_status.emit(f"Error: {str(e)}")
        finally:
            if self.client_socket:
                self.client_socket.close()
            self.connection_status.emit("Disconnected from server")

    def send_message(self, message):
        if self.client_socket:
            self.client_socket.send(message.encode('utf-8'))

    def send_file(self, file_path):
        try:
            if self.client_socket and os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                # Notify the receiver about the incoming file
                self.client_socket.send(f"FILE:{file_name}:{file_size}".encode('utf-8'))

                with open(file_path, "rb") as f:
                    while chunk := f.read(4096):  # Increased buffer size to 4 KB
                        self.client_socket.send(chunk)

                self.client_socket.send(b"EOF")  # End-of-file marker
                self.connection_status.emit(f"File '{file_name}' sent successfully.")
            else:
                self.connection_status.emit("File not found.")
        except Exception as e:
            self.connection_status.emit(f"Error sending file: {str(e)}")

    def receive_file(self, file_name, file_size):
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            file_path = os.path.join(desktop, file_name)

            received_size = 0
            with open(file_path, "wb") as f:
                while received_size < file_size:
                    chunk = self.client_socket.recv(4096)  # Receive in chunks of 4 KB
                    if chunk == b"EOF":
                        break
                    f.write(chunk)
                    received_size += len(chunk)

            self.file_received.emit(f"File '{file_name}' received and saved to Desktop.")
        except Exception as e:
            self.file_received.emit(f"Error receiving file: {str(e)}")

    def stop(self):
        self.running = False
        self.quit()


# GUI Application
class MessengerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Messenger App")
        self.setGeometry(100, 100, 400, 400)

        self.layout = QVBoxLayout()
        self.status_label = QLabel("Status: Not connected")
        self.layout.addWidget(self.status_label)

        self.message_input = QLineEdit(self)
        self.layout.addWidget(self.message_input)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        self.pair_button = QPushButton("Pair", self)
        self.pair_button.clicked.connect(self.pair)
        self.layout.addWidget(self.pair_button)

        self.file_button = QPushButton("Send File", self)
        self.file_button.clicked.connect(self.send_file)
        self.layout.addWidget(self.file_button)

        self.setLayout(self.layout)

        self.network_thread = NetworkThread("127.0.0.1", 12345)
        self.network_thread.update_message.connect(self.receive_message)
        self.network_thread.connection_status.connect(self.update_status)
        self.network_thread.pair_request.connect(self.handle_pair_request)
        self.network_thread.file_received.connect(self.file_received)
        self.network_thread.start()

    def update_status(self, status):
        self.status_label.setText(f"Status: {status}")

    def send_message(self):
        message = self.message_input.text().strip()
        if message:
            self.network_thread.send_message(f"MESSAGE:{message}")
            self.message_input.clear()
        else:
            self.update_status("Message cannot be empty!")

    def pair(self):
        ip, ok = QInputDialog.getText(self, 'Pair with Peer', 'Enter IP address of peer:')
        if ok:
            self.network_thread.send_message(f"PAIR:{ip}")
            self.update_status(f"Pairing with {ip}...")

    def send_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if file_path:
            self.network_thread.send_file(file_path)

    def receive_message(self, message):
        QMessageBox.information(self, "Message Received", message)

    def file_received(self, message):
        QMessageBox.information(self, "File Received", message)

    def handle_pair_request(self, sender_ip):
        reply = QMessageBox.question(self, "Pair Request", f"Accept pair request from {sender_ip}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.network_thread.send_message(f"PAIR_ACCEPT:{sender_ip}")
        else:
            self.network_thread.send_message(f"PAIR_REJECT:{sender_ip}")

    def closeEvent(self, event):
        self.network_thread.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MessengerApp()
    window.show()
    sys.exit(app.exec())
