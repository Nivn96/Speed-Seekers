import socket
import struct
import threading
import time

# Constants
MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4
UDP_PORT = 13117
BUFFER_SIZE = 1024

# Helper functions
def parse_offer_packet(data):
    """Parse the offer packet and extract details."""
    try:
        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IBHH', data)
        if magic_cookie != MAGIC_COOKIE or message_type != OFFER_MESSAGE_TYPE:
            return None
        return udp_port, tcp_port
    except struct.error:
        return None

def create_request_packet(file_size):
    """Create a request packet for file transfer."""
    return struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size)

def measure_tcp_transfer(tcp_address, file_size):
    """Measure the speed of a TCP transfer."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect(tcp_address)
            tcp_socket.sendall(f"{file_size}\n".encode())

            start_time = time.time()
            received_bytes = 0

            while received_bytes < file_size:
                data = tcp_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                received_bytes += len(data)

            end_time = time.time()
            duration = end_time - start_time
            speed = (received_bytes * 8) / duration  # bits per second
            print(f"[INFO] TCP transfer finished: {received_bytes} bytes in {duration:.2f} seconds, speed: {speed:.2f} bps")
    except Exception as e:
        print(f"[ERROR] TCP transfer failed: {e}")

def measure_udp_transfer(udp_address, file_size):
    """Measure the speed and packet loss of a UDP transfer."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.settimeout(1)
            request_packet = create_request_packet(file_size)
            udp_socket.sendto(request_packet, udp_address)

            received_packets = 0
            total_bytes = 0
            start_time = time.time()

            while True:
                try:
                    data, _ = udp_socket.recvfrom(BUFFER_SIZE)
                    if len(data) < 20:
                        break
                    total_bytes += len(data[20:])  # Skip the header
                    received_packets += 1
                except socket.timeout:
                    break

            end_time = time.time()
            duration = end_time - start_time
            expected_packets = file_size // BUFFER_SIZE
            loss_percentage = 100 * (1 - received_packets / expected_packets)
            speed = (total_bytes * 8) / duration  # bits per second
            print(f"[INFO] UDP transfer finished: {total_bytes} bytes in {duration:.2f} seconds, speed: {speed:.2f} bps, packet loss: {loss_percentage:.2f}%")
    except Exception as e:
        print(f"[ERROR] UDP transfer failed: {e}")

def client_listener():
    """Listen for UDP offers and initiate transfers."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        udp_socket.bind(("", UDP_PORT))

        print("[INFO] Client listening for offers...")

        while True:
            data, addr = udp_socket.recvfrom(BUFFER_SIZE)
            offer = parse_offer_packet(data)
            if offer:
                udp_port, tcp_port = offer
                print(f"[INFO] Received offer from {addr[0]}: UDP port {udp_port}, TCP port {tcp_port}")
                
                file_size = int(input("Enter file size (in bytes): "))
                threading.Thread(target=measure_tcp_transfer, args=((addr[0], tcp_port), file_size)).start()
                threading.Thread(target=measure_udp_transfer, args=((addr[0], udp_port), file_size)).start()

if __name__ == "__main__":
    client_listener()
