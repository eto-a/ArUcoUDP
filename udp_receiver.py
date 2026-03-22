import socket

def main():
    UDP_IP = "127.0.0.1"
    UDP_PORT = 5005

    # Создаем UDP сокет
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Привязываем сокет к IP и порту
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"Error binding to {UDP_IP}:{UDP_PORT}: {e}")
        return

    print(f"UDP Receiver started on {UDP_IP}:{UDP_PORT}")
    print("Waiting for marker data... (Press Ctrl+C to stop)")

    try:
        while True:
            # Получаем данные (буфер 1024 байта)
            data, addr = sock.recvfrom(1024)
            message = data.decode()
            
            # Выводим полученное сообщение
            print(f"Received from {addr}: {message}")
            
    except KeyboardInterrupt:
        print("\nStopping UDP Receiver...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
