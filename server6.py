import socket
import threading
import base64
import os

# Dictionary to store connected clients
clients = {}
# Dictionary to track paired clients
paired_clients = {}
# Dictionary to track file transfers
file_transfers = {}

def handle_client(client_socket, address):
    """Handles communication with a connected client."""
    print(f"[*] Accepted connection from {address}")

    try:
        buffer_size = 65536  # 64KB buffer size
        while True:
            # Receive raw data bytes (don't decode yet)
            raw_data = client_socket.recv(buffer_size)
            if not raw_data:
                break  # Client disconnected
                
            # First check if this is a binary file chunk (starts with FILECHUNK:)
            if raw_data.startswith(b'FILECHUNK:'):
                print(f"[+] Forwarding file chunk from {address} ({len(raw_data)} bytes)")
                
                # Find the paired client
                if address in paired_clients:
                    paired_addr = paired_clients[address]
                    if paired_addr in clients:
                        try:
                            # Forward the raw data as is (preserving encryption)
                            clients[paired_addr].send(raw_data)
                            print(f"[+] Forwarded {len(raw_data)} bytes chunk to {paired_addr}.")
                            
                            # Send ACK back to the sender
                            client_socket.send("ACK".encode('utf-8'))
                        except Exception as e:
                            print(f"[-] Error forwarding file chunk: {str(e)}")
                            # Try to inform the sender
                            try:
                                client_socket.send(f"ERROR: Failed to forward chunk - {str(e)}".encode('utf-8'))
                            except:
                                pass
                
                # Skip further processing for file chunks
                continue
            
            # Try to handle as text data
            try:
                # Try to decode as text
                text_data = raw_data.decode('utf-8')
                
                # Check for EOF marker (end of file)
                if text_data == "EOF":
                    print(f"[+] EOF marker detected from {address}")
                    # Find the paired client
                    if address in paired_clients:
                        paired_addr = paired_clients[address]
                        if paired_addr in clients:
                            try:
                                # Forward the EOF marker
                                clients[paired_addr].send(raw_data)
                                print(f"[+] File transfer completed from {address} to {paired_addr}")
                                
                                # Clear file transfer tracking if needed
                                if (address, paired_addr) in file_transfers:
                                    print(f"[+] Removing file transfer tracking: {file_transfers[(address, paired_addr)]}")
                                    del file_transfers[(address, paired_addr)]
                            except Exception as e:
                                print(f"[-] Error forwarding EOF: {str(e)}")
                    
                    # Skip further processing for EOF marker
                    continue
                
                # Process other messages
                print(f"[{address}] Message: {text_data}")

                # Handle Pairing (Direct IP Input Allowed)
                if text_data.startswith("PAIR:"):
                    pair_ip = text_data.split(":")[1]
                    
                    # Modified pairing logic to match only the IP part
                    pair_found = False
                    for client_addr in clients:
                        # Check if the first element (IP address) of the client_addr tuple matches
                        if isinstance(client_addr, tuple) and client_addr[0] == pair_ip:
                            # Store the pairing information in both directions
                            paired_clients[address] = client_addr
                            paired_clients[client_addr] = address
                            
                            print(f"[+] {address} paired with {client_addr}")
                            client_socket.send("PAIR_SUCCESS".encode('utf-8'))
                            
                            # Also notify the other client about successful pairing
                            try:
                                clients[client_addr].send("PAIR_SUCCESS".encode('utf-8'))
                            except Exception:
                                pass
                                
                            pair_found = True
                            break
                    
                    if not pair_found:
                        client_socket.send("PAIR_FAILED".encode('utf-8'))
                
                # Handle pairing acceptance/rejection
                elif text_data.startswith("PAIR_ACCEPT:") or text_data.startswith("PAIR_REJECT:"):
                    parts = text_data.split(":")
                    action = parts[0]
                    target_ip = parts[1]
                    
                    # Find the client with the matching IP
                    for client_addr in clients:
                        if isinstance(client_addr, tuple) and client_addr[0] == target_ip:
                            if action == "PAIR_ACCEPT":
                                # Set up pairing
                                paired_clients[address] = client_addr
                                paired_clients[client_addr] = address
                                
                                print(f"[+] {address} accepted pairing with {client_addr}")
                                client_socket.send("PAIR_SUCCESS".encode('utf-8'))
                                clients[client_addr].send("PAIR_SUCCESS".encode('utf-8'))
                            else:
                                print(f"[-] {address} rejected pairing with {client_addr}")
                                clients[client_addr].send("PAIR_FAILED".encode('utf-8'))
                            break
                
                # Handle file transfer initiation
                elif text_data.startswith("FILE:"):
                    print(f"[+] File transfer initiated from {address}: {text_data}")
                    
                    # Acknowledge receipt to the sender
                    client_socket.send("ACK".encode('utf-8'))
                    
                    # If this client is paired, forward the file info to its paired client
                    if address in paired_clients:
                        paired_addr = paired_clients[address]
                        if paired_addr in clients:
                            try:
                                # Forward the original message
                                clients[paired_addr].send(text_data.encode('utf-8'))
                                print(f"[+] Forwarded file info from {address} to {paired_addr}")
                                
                                # Wait for ACK from receiver before proceeding
                                try:
                                    ack_data = clients[paired_addr].recv(4096).decode('utf-8')
                                    if ack_data == "ACK":
                                        print(f"[+] Received ACK from {paired_addr} for file info")
                                        # Forward ACK back to sender
                                        client_socket.send("ACK".encode('utf-8'))
                                    else:
                                        print(f"[?] Received non-ACK from receiver: {ack_data}")
                                except Exception as e:
                                    print(f"[-] Error getting ACK from receiver: {str(e)}")
                                
                                # Track this file transfer
                                file_parts = text_data.split(":")
                                if len(file_parts) >= 3:
                                    file_name = file_parts[1]
                                    file_size = int(file_parts[2])
                                    print(f"[+] Tracking file transfer: {file_name} ({file_size} bytes)")
                                    file_transfers[(address, paired_addr)] = {
                                        "name": file_name,
                                        "size": file_size,
                                        "started": True
                                    }
                            except Exception as e:
                                print(f"[-] Error forwarding file to {paired_addr}: {str(e)}")
                                # Try to inform the sender
                                try:
                                    client_socket.send(f"ERROR: Failed to forward file info - {str(e)}".encode('utf-8'))
                                except:
                                    pass
                
                # Handle regular messages
                else:
                    # Acknowledge receipt to the sender
                    client_socket.send("ACK".encode('utf-8'))
                    
                    # If this client is paired, forward the message to its paired client
                    if address in paired_clients:
                        paired_addr = paired_clients[address]
                        if paired_addr in clients:
                            try:
                                # Add a prefix to indicate it's a forwarded message
                                forward_msg = f"MSG:{text_data}"
                                clients[paired_addr].send(forward_msg.encode('utf-8'))
                                print(f"[+] Forwarded message from {address} to {paired_addr}")
                            except Exception as e:
                                print(f"[-] Error forwarding message to {paired_addr}: {str(e)}")
            
            except UnicodeDecodeError:
                # This is binary data but not a file chunk - unusual
                print(f"[?] Received unknown binary data from {address} of length {len(raw_data)}")
            
            except Exception as e:
                print(f"[-] Error processing message: {str(e)}")
    
    except Exception as e:
        print(f"[-] General error: {str(e)}")
    finally:
        print(f"[*] Connection closed: {address}")
        client_socket.close()
        
        # Clean up file transfers
        for key in list(file_transfers.keys()):
            if address in key:
                del file_transfers[key]
        
        # Clean up paired clients
        if address in paired_clients:
            paired_addr = paired_clients[address]
            if paired_addr in paired_clients:
                del paired_clients[paired_addr]
            del paired_clients[address]
        
        # Remove from clients dictionary
        if address in clients:
            del clients[address]

def start_server():
    """Starts the server and listens for incoming connections."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 12345))
    server.listen(5)
    
    print("[*] Listening on 0.0.0.0:12345")
    print("[*] No encryption key needed - using built-in XOR encryption")

    while True:
        client_socket, address = server.accept()
        clients[address] = client_socket  # Store connected client
        client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
        client_thread.start()

if __name__ == "__main__":
    start_server()
