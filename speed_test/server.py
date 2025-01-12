import socket
import struct
import threading
import time

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4
UDP_BROADCAST_INTERVAL = 1
BUFFER_SIZE = 1024

# Server Ports
UDP_PORT = 0  # OS will assign an available port
TCP_PORT = 0  # OS will assign an available port

# Helper functions
def create_offer_packet(udp_port, tcp_port):
    """Create an offer packet for broadcasting."""
    return struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, udp_port, tcp_port)

def handle_tcp_client(connection, address, file_size):
    """Handle file transfer for a TCP client."""
    print(f"[INFO] Handling TCP client {address}")
    try:
        data = b'X' * file_size  # Dummy data
        connection.sendall(data)
        print(f"[INFO] Sent {file_size} bytes to TCP client {address}")
    except Exception as e:
        print(f"[ERROR] TCP client error: {e}")
    finally:
        connection.close()

def handle_udp_client(udp_socket, client_address, file_size):
    """Handle file transfer for a UDP client."""
    print(f"[INFO] Handling UDP client {client_address}")
    try:
        num_packets = file_size // BUFFER_SIZE
        for i in range(num_packets):
            payload = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, num_packets, i) + b'X' * (BUFFER_SIZE - 20)
            udp_socket.sendto(payload, client_address)
        print(f"[INFO] Sent {file_size} bytes to UDP client {client_address}")
    except Exception as e:
        print(f"[ERROR] UDP client error: {e}")

def broadcast_offers(udp_port, tcp_port):
    """Broadcast offers via UDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        udp_socket.bind(("", udp_port))
        offer_packet = create_offer_packet(udp_port, tcp_port)

        while True:
            udp_socket.sendto(offer_packet, ("<broadcast>", udp_port))
            print(f"[INFO] Broadcast offer on UDP port {udp_port}")
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
    print(f"[INFO] Server started: UDP port {udp_port}, TCP port {tcp_port}")

    while True:
        client_conn, client_addr = tcp_socket.accept()
        file_size = int(client_conn.recv(BUFFER_SIZE).decode().strip())
        threading.Thread(target=handle_tcp_client, args=(client_conn, client_addr, file_size)).start()
