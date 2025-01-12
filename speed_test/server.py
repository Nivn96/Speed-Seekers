import socket
import threading
import time
from packet_formats import PacketFormats

BUFFER_SIZE = 1024
UDP_BROADCAST_INTERVAL = 1  # seconds

def handle_tcp_client(client_conn, client_addr, file_size):
    """Handles TCP client by sending the requested file size."""
    try:
        data = b'X' * file_size
        client_conn.sendall(data)
        print(f"[INFO] Sent {file_size} bytes to TCP client {client_addr}")
    except Exception as e:
        print(f"[ERROR] TCP client error: {e}")
    finally:
        client_conn.close()

def handle_udp_client(udp_socket, client_address, file_size):
    """Handles UDP client by sending the requested file size in segments."""
    try:
        num_packets = (file_size + BUFFER_SIZE - 1) // BUFFER_SIZE
        for i in range(num_packets):
            payload = b'X' * BUFFER_SIZE
            packet = PacketFormats.create_payload_packet(num_packets, i, payload)
            udp_socket.sendto(packet, client_address)
        print(f"[INFO] Sent {file_size} bytes to UDP client {client_address}")
    except Exception as e:
        print(f"[ERROR] UDP client error: {e}")

def broadcast_offers(udp_port, tcp_port):
    """Broadcasts offers via UDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(("", 0))  # Bind to an available port
        offer_packet = PacketFormats.create_offer_packet(udp_port, tcp_port)

        while True:
            udp_socket.sendto(offer_packet, ("<broadcast>", 13117))
            print(f"[INFO] Broadcast offer on UDP port {udp_socket.getsockname()[1]}")
            time.sleep(UDP_BROADCAST_INTERVAL)

if __name__ == "__main__":
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("", 0))
    udp_port = udp_socket.getsockname()[1]

    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(("", 0))
    tcp_port = tcp_socket.getsockname()[1]

    threading.Thread(target=broadcast_offers, args=(udp_port, tcp_port), daemon=True).start()

    tcp_socket.listen(5)
    print(f"[INFO] Server started:  listening on IP address {socket.gethostbyname(socket.gethostname())}")

    while True:
        client_conn, client_addr = tcp_socket.accept()
        try:
            file_size = int(client_conn.recv(BUFFER_SIZE).decode().strip())
            threading.Thread(target=handle_tcp_client, args=(client_conn, client_addr, file_size)).start()
        except Exception as e:
            print(f"[ERROR] Failed to handle client: {e}")