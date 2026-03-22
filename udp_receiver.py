import socket

def main():
    UDP_IP = "127.0.0.1"
    UDP_PORT = 5005

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Bind socket to IP and port
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"Error binding to {UDP_IP}:{UDP_PORT}: {e}")
        return

    print(f"UDP Receiver started on {UDP_IP}:{UDP_PORT}")
    print("Waiting for marker data... (Press Ctrl+C to stop)")

    try:
        while True:
            # Receive data (1024 bytes buffer)
            data, addr = sock.recvfrom(1024)
            message = data.decode()
            
            # Output received message
            print(f"Received from {addr}: {message}")
            
    except KeyboardInterrupt:
        print("\nStopping UDP Receiver...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
