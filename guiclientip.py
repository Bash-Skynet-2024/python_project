import socket
import threading
import os
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QInputDialog, QMessageBox, QLineEdit, QTextEdit, QFileDialog
from PyQt6.QtCore import Qt

class MessengerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('127.0.0.1', 12345))  # Connect to server
        self.init_ui()
        self.paired_with = None  # IP of the client we are paired with

    def init_ui(self):
        self.setWindowTitle('Messenger')
        self.setGeometry(200, 200, 500, 400)

        layout = QVBoxLayout()

        # Pair button
        self.pair_button = QPushButton('Pair with Client', self)
        self.pair_button.clicked.connect(self.initiate_pairing)
        layout.addWidget(self.pair_button)

        # Chat display area
        self.chat_display = QTextEdit(self)
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Message input
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText("Type your message here...")
        layout.addWidget(self.message_input)

        # Send button
        self.send_button = QPushButton('Send Message', self)
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        # File button
        self.file_button = QPushButton('Send File', self)
        self.file_button.clicked.connect(self.send_file)
        layout.addWidget(self.file_button)

        self.setLayout(layout)
        self.show()

        # Start the listener thread to listen for messages
        listener_thread = threading.Thread(target=self.listen_for_messages)
        listener_thread.daemon = True
        listener_thread.start()

    def initiate_pairing(self):
        ip_address, ok = QInputDialog.getText(self, "Pair with Client", "Enter the IP address of the client:")
        if ok and ip_address:
            self.client_socket.sendall(f"PAIR:{ip_address}".encode('utf-8'))

    def listen_for_messages(self):
        while True:
            message = self.client_socket.recv(1024).decode('utf-8')

            # Handle pairing requests
            if message.startswith("PAIR_REQUEST:"):
                sender_ip = message.split(":")[1]
                reply = QMessageBox.question(self, "Pairing Request", f"{sender_ip} wants to pair with you. Accept?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

                if reply == QMessageBox.StandardButton.Yes:
                    self.client_socket.sendall(f"PAIR_ACCEPTED:{sender_ip}".encode('utf-8'))
                    self.paired_with = sender_ip
                    self.chat_display.append(f"Pairing successful with {sender_ip}. You can now send messages.")
                else:
                    self.client_socket.sendall(f"PAIR_REJECTED:{sender_ip}".encode('utf-8'))
                    self.chat_display.append(f"Pairing request from {sender_ip} rejected.")

            elif message.startswith("PAIR_ACCEPTED:"):
                self.paired_with = message.split(":")[1]
                self.chat_display.append(f"Successfully paired with {self.paired_with}.")

            elif message.startswith("PAIR_REJECTED:"):
                self.chat_display.append(f"Pairing request rejected by {message.split(':')[1]}.")

            else:
                # Display incoming messages
                self.chat_display.append(message)

    def send_message(self):
        if not self.paired_with:
            self.chat_display.append("You are not paired with anyone yet.")
            return

        message = self.message_input.text().strip()
        if message:
            self.client_socket.sendall(f"Message from you: {message}".encode('utf-8'))
            self.chat_display.append(f"You: {message}")
            self.message_input.clear()  # Clear the message input field
        else:
            QMessageBox.warning(self, "Warning", "Message cannot be empty!")

    def send_file(self):
        if not self.paired_with:
            self.chat_display.append("You are not paired with anyone yet.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Select a File")
        if file_path:
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as file:
                file_data = file.read()
                self.client_socket.sendall(f"FILE:{file_name}:{len(file_data)}".encode('utf-8'))
                self.client_socket.sendall(file_data)  # Send the file data
            self.chat_display.append(f"You sent a file: {file_name}")

    def closeEvent(self, event):
        self.client_socket.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication([])
    messenger = MessengerApp()
    app.exec()
