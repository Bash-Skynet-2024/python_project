import os
import sys
import socket
import base64
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QMessageBox, 
    QInputDialog, QFileDialog, QTextEdit, QHBoxLayout, QScrollArea, QProgressBar
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

# Simple encryption/decryption key (a simple XOR key)
ENCRYPTION_KEY = b'SIMPLEKEYFORXOR123456789012345678901234567890'

# Network Thread to handle server communication
class NetworkThread(QThread):
    update_message = pyqtSignal(str)
    connection_status = pyqtSignal(str)
    pair_request = pyqtSignal(str)
    file_received = pyqtSignal(str)
    file_progress = pyqtSignal(int, str)

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.running = True
            
        # File receiving state
        self.receiving_file = False
        self.file_data = bytearray()
        self.current_file_path = ""
        self.current_file_size = 0
        self.received_bytes = 0

    def run(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            self.connection_status.emit(f"Connected to {self.host}:{self.port}")

            while self.running:
                message_data = self.client_socket.recv(65536)  # Use larger buffer size
                if not message_data:
                    break
                
                # Try to decode as text first
                try:
                    # If we're in file receiving mode
                    if self.receiving_file:
                        try:
                            # First, check if it's a text message like EOF
                            try:
                                message_str = message_data.decode('utf-8')
                                
                                # Check for EOF marker
                                if message_str == "EOF":
                                    # File transfer is complete - close the file
                                    if hasattr(self, 'current_file') and self.current_file:
                                        self.current_file.close()
                                        
                                        # Verify file was created with content
                                        if os.path.exists(self.current_file_path):
                                            file_size = os.path.getsize(self.current_file_path)
                                            self.file_received.emit(f"File saved to {self.current_file_path} ({file_size} bytes)")
                                        else:
                                            self.file_received.emit(f"Error: File not created at {self.current_file_path}")
                                    
                                    self.file_progress.emit(100, "Complete")
                                    
                                    # Reset file receiving state
                                    self.receiving_file = False
                                    self.current_file_path = ""
                                    self.current_file_size = 0
                                    self.received_bytes = 0
                                    continue
                            except UnicodeDecodeError:
                                # This is binary data (most likely a file chunk)
                                pass
                            
                            # If it's not EOF, then it's file data
                            if message_data.startswith(b'FILECHUNK:'):
                                # Extract binary data after the marker
                                binary_data = message_data[10:]  # Skip "FILECHUNK:"
                                
                                # Decrypt the binary data
                                decrypted_data = self.simple_decrypt(binary_data)
                                
                                self.file_received.emit(f"Received encrypted chunk: {len(binary_data)} bytes")
                                
                                if hasattr(self, 'current_file') and self.current_file:
                                    # Write the chunk to file
                                    self.current_file.write(decrypted_data)
                                    self.current_file.flush()  # Force flush to disk
                                    os.fsync(self.current_file.fileno())  # Ensure it's written to disk
                                    
                                    # Update progress
                                    self.received_bytes += len(decrypted_data)
                                    if self.current_file_size > 0:
                                        progress = min(99, int((self.received_bytes / self.current_file_size) * 100))
                                        self.file_progress.emit(progress, f"Receiving: {progress}%")
                                        
                                    self.file_received.emit(f"Wrote chunk: {len(decrypted_data)} bytes, total: {self.received_bytes}/{self.current_file_size}")
                                    
                                # Continue to next message
                                continue
                                
                        except Exception as e:
                            self.file_received.emit(f"Error processing file data: {str(e)}")
                        
                        # Continue to next message
                        continue
                    
                    # Regular message handling for non-file-transfer mode
                    message = message_data.decode('utf-8')
                    
                    # Handle various message types (PAIR, FILE, etc.)
                    if message.startswith("MSG:"):
                        # Extract the actual message content
                        actual_message = message[4:]  # Skip "MSG:" prefix
                        self.update_message.emit(f"Received: {actual_message}")
                    elif message.startswith("PAIR_REQUEST:"):
                        sender_ip = message.split(":")[1]
                        self.pair_request.emit(sender_ip)
                    elif message.startswith("PAIR_SUCCESS"):
                        self.connection_status.emit("Pairing successful!")
                    elif message.startswith("PAIR_FAILED"):
                        self.connection_status.emit("Pairing failed. Try again.")
                    elif message.startswith("FILE:"):
                        file_parts = message.split(":")
                        if len(file_parts) >= 3:
                            file_name = file_parts[1]
                            file_size = int(file_parts[2])
                            self.start_receiving_file(file_name, file_size)
                    elif message == "ACK":
                        # Simply acknowledge - don't need to display this
                        pass
                    else:
                        self.update_message.emit(f"Server: {message}")
                        
                except UnicodeDecodeError:
                    # This is binary data outside file mode - unusual but handle it
                    self.connection_status.emit(f"Received unexpected binary data: {len(message_data)} bytes")
                
                except Exception as e:
                    self.connection_status.emit(f"Error processing message: {str(e)}")
                    
        except Exception as e:
            self.connection_status.emit(f"Error: {str(e)}")
        finally:
            if self.client_socket:
                self.client_socket.close()
            self.connection_status.emit("Disconnected from server")

    def simple_encrypt(self, data):
        """Simple XOR encryption for data"""
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        encrypted = bytearray()
        for i, byte in enumerate(data):
            key_byte = ENCRYPTION_KEY[i % len(ENCRYPTION_KEY)]
            encrypted.append(byte ^ key_byte)
        return bytes(encrypted)
    
    def simple_decrypt(self, data):
        """Simple XOR decryption for data"""
        # XOR decryption is the same as encryption
        return self.simple_encrypt(data)

    def send_message(self, message):
        if self.client_socket:
            self.client_socket.send(message.encode('utf-8'))

    def send_file(self, file_path):
        try:
            if self.client_socket and os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                # Step 1: Send file header and get acknowledgment
                file_header = f"FILE:{file_name}:{file_size}"
                self.client_socket.send(file_header.encode())
                
                # Wait for ACK from server before proceeding
                ack_received = False
                try:
                    ack_data = self.client_socket.recv(4096).decode()
                    if ack_data == "ACK":
                        ack_received = True
                except Exception as e:
                    self.connection_status.emit(f"Error waiting for ACK: {str(e)}")
                    return
                
                if not ack_received:
                    self.connection_status.emit("Did not receive ACK from server.")
                    return
                
                # Update progress display
                self.file_progress.emit(0, "Starting")
                sent_bytes = 0

                # Step 2: Send file in manageable chunks
                with open(file_path, "rb") as f:
                    # Use a larger chunk size for better performance
                    chunk_size = 65000  # 64KB-ish chunks (with room for header)
                    
                    # Send the file in chunks
                    while chunk := f.read(chunk_size):
                        # Encrypt the chunk
                        encrypted_chunk = self.simple_encrypt(chunk)
                        
                        # Prefix with FILECHUNK: marker
                        chunk_with_marker = b'FILECHUNK:' + encrypted_chunk
                        
                        # Send the encrypted chunk
                        self.client_socket.send(chunk_with_marker)
                        
                        # Wait for ACK after each chunk for better reliability
                        try:
                            ack = self.client_socket.recv(4096).decode()
                            if ack != "ACK":
                                self.connection_status.emit(f"Warning: Expected ACK, got: {ack}")
                        except Exception as e:
                            self.connection_status.emit(f"Error getting chunk ACK: {str(e)}")
                        
                        # Update progress
                        sent_bytes += len(chunk)
                        progress = int((sent_bytes / file_size) * 100)
                        self.file_progress.emit(progress, f"Sending: {progress}%")
                
                # Step 3: Send EOF marker to signal end of transfer
                self.client_socket.send(b"EOF")
                    
                self.connection_status.emit(f"File '{file_name}' sent successfully.")
                self.file_progress.emit(100, "Complete")
            else:
                self.connection_status.emit("File not found.")
        except Exception as e:
            self.connection_status.emit(f"Error sending file: {str(e)}")
            self.file_progress.emit(0, "Failed")

    def start_receiving_file(self, file_name, file_size):
        """Prepare to receive a file."""
        try:
            # Get Desktop path - works on Windows, Linux and macOS
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            file_path = os.path.join(desktop, file_name)

            # Initialize file receiving variables
            self.receiving_file = True
            self.current_file_path = file_path
            self.current_file_size = file_size
            self.received_bytes = 0
            
            # Create the file and open it for writing
            self.current_file = open(file_path, 'wb')
            
            # Notify the user
            self.file_received.emit(f"Receiving file '{file_name}' ({file_size} bytes)...")
            self.file_progress.emit(0, "Started")
            
            # Add debug message
            self.file_received.emit(f"File will be saved to: {file_path}")
            
            # Send ACK to indicate we're ready to receive the file
            self.client_socket.send("ACK".encode())
            
        except Exception as e:
            self.file_received.emit(f"Error preparing to receive file: {str(e)}")
            self.receiving_file = False
            self.file_progress.emit(0, "Failed")

    def stop(self):
        self.running = False
        self.quit()


# GUI Application
class MessengerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Messenger App")
        self.setGeometry(100, 100, 500, 600)

        self.layout = QVBoxLayout()
        
        # Status section
        self.status_label = QLabel("Status: Not connected")
        self.layout.addWidget(self.status_label)
        
        # Message display area
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        self.message_display.setFont(QFont("Courier New", 10))
        self.message_display.setMinimumHeight(300)
        self.layout.addWidget(self.message_display)
        
        # File transfer progress
        self.progress_label = QLabel("File Transfer:")
        self.layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText("Type your message here...")
        input_layout.addWidget(self.message_input, 4)

        self.send_button = QPushButton("Send", self)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button, 1)
        
        self.layout.addLayout(input_layout)
        
        # Button area
        button_layout = QHBoxLayout()
        
        self.pair_button = QPushButton("Pair", self)
        self.pair_button.clicked.connect(self.pair)
        button_layout.addWidget(self.pair_button)

        self.file_button = QPushButton("Send File", self)
        self.file_button.clicked.connect(self.send_file)
        button_layout.addWidget(self.file_button)
        
        self.clear_button = QPushButton("Clear Messages", self)
        self.clear_button.clicked.connect(self.clear_messages)
        button_layout.addWidget(self.clear_button)
        
        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)
        
        # Connect to the server immediately instead of requiring a key
        self.initialize_connection()

    def initialize_connection(self):
        try:
            # Start network thread and connect to server
            if hasattr(self, 'network_thread') and self.network_thread:
                self.network_thread.stop()
            
            self.network_thread = NetworkThread("127.0.0.1", 12345)
            self.network_thread.update_message.connect(self.add_message)
            self.network_thread.connection_status.connect(self.update_status)
            self.network_thread.pair_request.connect(self.handle_pair_request)
            self.network_thread.file_received.connect(self.add_message)
            self.network_thread.file_progress.connect(self.update_progress)
            self.network_thread.start()
            
            self.update_status("Connecting to server...")
        except Exception as e:
            self.update_status(f"Connection error: {str(e)}")

    def update_status(self, status):
        self.status_label.setText(f"Status: {status}")
        # Also add to message display
        self.add_message(f"System: {status}")

    def update_progress(self, value, status):
        """Update the file transfer progress bar."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"File Transfer: {status}")

    def add_message(self, message):
        """Add a message to the text display area."""
        self.message_display.append(message)
        # Auto-scroll to the bottom
        scrollbar = self.message_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_messages(self):
        """Clear all messages from the display area."""
        self.message_display.clear()

    def send_message(self):
        if not hasattr(self, 'network_thread') or not self.network_thread:
            self.update_status("Not connected! Reconnecting...")
            self.initialize_connection()
            return
            
        message = self.message_input.text().strip()
        if message:
            self.network_thread.send_message(message)
            # Add the sent message to our display
            self.add_message(f"You: {message}")
            self.message_input.clear()
        else:
            self.update_status("Message cannot be empty!")

    def pair(self):
        if not hasattr(self, 'network_thread') or not self.network_thread:
            self.update_status("Not connected! Reconnecting...")
            self.initialize_connection()
            return
            
        ip, ok = QInputDialog.getText(self, 'Pair with Peer', 'Enter IP address of peer:')
        if ok:
            self.network_thread.send_message(f"PAIR:{ip}")
            self.update_status(f"Pairing with {ip}...")

    def send_file(self):
        if not hasattr(self, 'network_thread') or not self.network_thread:
            self.update_status("Not connected! Reconnecting...")
            self.initialize_connection()
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if file_path:
            self.add_message(f"Sending file: {os.path.basename(file_path)}")
            self.network_thread.send_file(file_path)

    def handle_pair_request(self, sender_ip):
        reply = QMessageBox.question(self, "Pair Request", f"Accept pair request from {sender_ip}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.network_thread.send_message(f"PAIR_ACCEPT:{sender_ip}")
        else:
            self.network_thread.send_message(f"PAIR_REJECT:{sender_ip}")

    def closeEvent(self, event):
        if hasattr(self, 'network_thread') and self.network_thread:
            self.network_thread.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MessengerApp()
    window.show()
    sys.exit(app.exec())