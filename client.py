import socket
import threading

# Global client socket
client = None


# Function to handle receiving messages
def receive_messages():
    global client
    try:
        while True:
            if client:
                message = client.recv(1024).decode('utf-8')
                if not message:
                    break  # Break the loop if the connection is closed
                print(f"Received: {message}")
    except Exception as e:
        print(f"Error receiving messages: {e}")
    finally:
        if client:
            client.close()
            print("Connection closed!")


# Function to send messages
def send_message():
    global client
    try:
        while True:
            message = input("Enter message to send: ")
            if message.lower() == "exit":
                client.send(message.encode('utf-8'))
                break  # Exit the loop if "exit" is entered
            client.send(message.encode('utf-8'))
    except Exception as e:
        print(f"Error sending message: {e}")
    finally:
        if client:
            client.close()
            print("Connection closed!")


# Function to connect to another client
def connect_to_client(client_ip):
    global client
    port = 12345  # Same port as server

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((client_ip, port))

        print(f"Connected as {client.getsockname()}")

        # Start the receive messages thread
        receive_thread = threading.Thread(target=receive_messages)
        receive_thread.start()

        # Start sending messages
        send_message()
    except Exception as e:
        print(f"Error connecting to client: {e}")
    finally:
        if client:
            client.close()
            print("Connection closed!")


# Main function to prompt user for connection and pairing
def main():
    print("Available Clients:")
    print("1. Enter IP address of the client you want to pair with.")

    client_ip = input("Enter the IP address of the client you want to pair with: ")

    # Connect to the client
    connect_to_client(client_ip)


# Start the process
if __name__ == "__main__":
    main()
