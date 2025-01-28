import socket
import threading
import os

clients = {}


def handle_client(client_socket, client_address):
    print(f"[+] New connection from {client_address}")
    clients[client_address] = client_socket
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:  # If no data is received, the client has disconnected
                break

            data = data.decode('utf-8', errors='ignore')

            if data.startswith("PAIR:"):
                peer_ip = data.split(":")[1]
                print(f"[PAIR] Client {client_address} requests pairing with {peer_ip}")
                client_socket.send(f"PAIR_REQUEST:{client_address[0]}".encode('utf-8'))

            elif data.startswith("PAIR_ACCEPT:"):
                peer_ip = data.split(":")[1]
                print(f"[PAIR_ACCEPT] Client {client_address} accepted pair with {peer_ip}")

            elif data.startswith("FILE:"):
                _, file_name, file_size = data.split(":")
                file_size = int(file_size)
                print(f"[FILE] Receiving '{file_name}' ({file_size} bytes) from {client_address}")

                # Receive file in chunks
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                file_path = os.path.join(desktop, file_name)

                with open(file_path, "wb") as f:
                    received_size = 0
                    while received_size < file_size:
                        chunk = client_socket.recv(4096)
                        if not chunk or chunk == b"EOF":
                            break
                        f.write(chunk)
                        received_size += len(chunk)

                print(f"[FILE] File '{file_name}' saved to {file_path}")
                client_socket.send(f"File '{file_name}' received successfully.".encode('utf-8'))

            elif data.startswith("MESSAGE:"):
                message = data.split(":", 1)[1]
                print(f"[MESSAGE] {client_address}: {message}")
                client_socket.send(f"Message received: {message}".encode('utf-8'))

            else:
                print(f"[UNKNOWN] {client_address}: {data}")

    except ConnectionResetError:
        print(f"[!] Client {client_address} disconnected abruptly.")
    except Exception as e:
        print(f"[ERROR] {client_address}: {str(e)}")
    finally:
        disconnect_client(client_address)


def disconnect_client(client_address):
    """Cleanly disconnect a client and remove it from the list."""
    if client_address in clients:
        try:
            clients[client_address].close()
        except Exception as e:
            print(f"[ERROR] Closing socket for {client_address}: {e}")
        del clients[client_address]
    print(f"[-] Client {client_address} disconnected.")


def start_server(host="127.0.0.1", port=12345):
    """Start the server and listen for incoming connections."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Server listening on {host}:{port}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down.")
    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()
