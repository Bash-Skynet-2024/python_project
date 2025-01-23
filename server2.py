import socket
import threading

clients = {}

def handle_client(client_socket, client_address):
    global clients

    # Receive the initial message from the client
    client_ip = client_address[0]
    print(f"New connection from {client_ip}")

    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break

            # If message starts with 'PAIR:', handle the pairing request
            if message.startswith("PAIR:"):
                target_ip = message.split(":")[1]
                print(f"Pairing request from {client_ip} to {target_ip}")

                # Notify the target client about the pairing request
                if target_ip in clients:
                    target_client = clients[target_ip]
                    target_client.sendall(f"PAIR_REQUEST:{client_ip}".encode('utf-8'))
                else:
                    print(f"Target client {target_ip} not found")

        except Exception as e:
            print(f"Error: {e}")
            break

    client_socket.close()
    del clients[client_ip]
    print(f"Client {client_ip} disconnected.")

def start_server():
    global clients
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', 12345))
    server.listen(5)

    print("Server listening on 127.0.0.1:12345")

    while True:
        client_socket, client_address = server.accept()
        clients[client_address[0]] = client_socket
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == "__main__":
    start_server()
