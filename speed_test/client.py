import socket
import threading
import time
from packet_formats import PacketFormats

BUFFER_SIZE = 1024
UDP_PORT = 13117

def tcp_transfer(server_ip, tcp_port, file_size):
    """Handles TCP transfer by connecting to the server and receiving the file."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, tcp_port))
            tcp_socket.sendall(f"{file_size}\n".encode())
            start_time = time.time()
            total_bytes = 0
            while True:
                data = tcp_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                total_bytes += len(data)
            duration = time.time() - start_time
            speed = (total_bytes * 8) / duration  # bits per second
            print(f"[INFO] TCP transfer finished: {total_bytes} bytes in {duration:.2f} seconds, speed: {speed:.2f} bps")
    except Exception as e:
        print(f"[ERROR] TCP transfer failed: {e}")

def udp_transfer(server_ip, udp_port, file_size):
    """Handles UDP transfer by connecting to the server and receiving the file in segments."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(("", 0))
            request_packet = PacketFormats.create_request_packet(file_size)
            udp_socket.sendto(request_packet, (server_ip, udp_port))
            start_time = time.time()
            total_bytes = 0
            received_packets = 0
            while True:
                try:
                    udp_socket.settimeout(1)
                    data, _ = udp_socket.recvfrom(BUFFER_SIZE + 21)
                    total_segments, current_segment, payload = PacketFormats.parse_payload_packet(data)
                    total_bytes += len(payload)
                    received_packets += 1
                except socket.timeout:
                    break
            duration = time.time() - start_time
            expected_packets = (file_size + BUFFER_SIZE - 1) // BUFFER_SIZE
            loss_percentage = 100 * (1 - received_packets / expected_packets)
            speed = (total_bytes * 8) / duration  # bits per second
            print(f"[INFO] UDP transfer finished: {total_bytes} bytes in {duration:.2f} seconds, speed: {speed:.2f} bps, packet loss: {loss_percentage:.2f}%")
    except Exception as e:
        print(f"[ERROR] UDP transfer failed: {e}")

def client_listener():
    """Listens for server offers and initiates transfers based on user input."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(("", UDP_PORT))

        print("[INFO] Client listening for offers...")

        while True:
            try:
                data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                print(f"[DEBUG] Received data: {data} from {addr}")
                offer = PacketFormats.parse_offer_packet(data)
                if offer:
                    udp_port, tcp_port = offer
                    server_ip = addr[0]
                    print(f"[INFO] Received offer from {server_ip}")
                    file_size = int(input("Enter file size (bytes): "))
                    tcp_connections = int(input("Enter number of TCP connections: "))
                    udp_connections = int(input("Enter number of UDP connections: "))

                    threads = []
                    for _ in range(tcp_connections):
                        t = threading.Thread(target=tcp_transfer, args=(server_ip, tcp_port, file_size))
                        threads.append(t)
                        t.start()

                    for _ in range(udp_connections):
                        t = threading.Thread(target=udp_transfer, args=(server_ip, udp_port, file_size))
                        threads.append(t)
                        t.start()

                    for t in threads:
                        t.join()

                    print("[INFO] All transfers complete, listening to offer requests")
            except Exception as e:
                print(f"[ERROR] Failed to receive data: {e}")

if __name__ == "__main__":
    client_listener()