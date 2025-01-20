import socket
import threading

# List to store client connections
clients = []


# Function to handle client communication
def handle_client(client_socket, client_address):
    print(f"New connection: {client_address}")

    # Add client to the list
    clients.append(client_socket)

    try:
        while True:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                # If no message is received, it means the client has disconnected
                break
            print(f"Message from {client_address}: {message}")

            # Broadcast message to all clients
            for client in clients:
                if client != client_socket:
                    try:
                        client.send(message.encode('utf-8'))
                    except:
                        continue  # If the message cannot be sent, skip the client
    except (ConnectionResetError, BrokenPipeError):
        # If the client has unexpectedly disconnected
        print(f"{client_address} disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # If a client disconnects, remove them from the client list
        if client_socket in clients:
            clients.remove(client_socket)
        client_socket.close()
        print(f"Connection with {client_address} closed.")


# Function to start the server
def start_server(host='127.0.0.1', port=12345):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, client_address = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()


# Run the server
if __name__ == "__main__":
    start_server()
