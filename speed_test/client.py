# client.py
import socket
import threading
import struct
import time
from typing import List, Tuple
import sys
import random

class SpeedTestClient:
    MAGIC_COOKIE = 0xabcddcba
    BROADCAST_PORT = 13117
    
    def __init__(self):
        self.running = False
        self.current_server: Tuple[str, int] = None
        self.transfer_results = []
        
    def _receive_offers(self) -> Tuple[str, int, int]:
        """Listen for server offers and return server details."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.BROADCAST_PORT))
        
        print("\033[94mClient started, listening for offer requests...\033[0m")
        
        while True:
            try:
                data, (server_ip, _) = sock.recvfrom(1024)
                
                # Unpack offer message
                magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IBHH', data)
                
                if magic_cookie == self.MAGIC_COOKIE and msg_type == 0x2:
                    print(f"\033[94mReceived offer from {server_ip}\033[0m")
                    sock.close()
                    return server_ip, udp_port, tcp_port
                    
            except Exception as e:
                print(f"\033[91mError receiving offers: {e}\033[0m")
                
    def _tcp_transfer(self, server_ip: str, port: int, file_size: int, conn_id: int):
        """Perform TCP transfer."""
        start_time = time.time()
        
        try:
            # Connect to server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server_ip, port))
            
            # Send file size request
            sock.send(f"{file_size}\n".encode())
            
            # Receive data
            bytes_received = 0
            while bytes_received < file_size:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                bytes_received += len(chunk)
                
            duration = time.time() - start_time
            speed = (file_size * 8) / duration  # bits per second
            
            print(f"\033[92mTCP transfer #{conn_id} finished, "
                  f"total time: {duration:.2f} seconds, "
                  f"total speed: {speed:.1f} bits/second\033[0m")
                  
            self.transfer_results.append(('TCP', conn_id, duration, speed, 100))
            
        except Exception as e:
            print(f"\033[91mError in TCP transfer #{conn_id}: {e}\033[0m")
        finally:
            sock.close()
            
    def _get_available_port(self) -> int:
        """Get an available port number."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
            
    def _udp_transfer(self, server_ip: str, server_port: int, file_size: int, conn_id: int):
        """Perform UDP transfer."""
        start_time = time.time()
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                udp_socket.bind(('', 0))
                request_packet = struct.pack('!IBQ', self.MAGIC_COOKIE, 0x3, file_size)
                udp_socket.sendto(request_packet, (server_ip, server_port))
                total_bytes = 0
                received_packets = 0
                while True:
                    try:
                        udp_socket.settimeout(1)
                        data, _ = udp_socket.recvfrom(1024 + 21)
                        header = struct.unpack('!IBQQ', data[:21])
                        magic_cookie, msg_type, total_segments, current_segment = header
                        payload = data[21:]
                        if magic_cookie == self.MAGIC_COOKIE and msg_type == 0x4:
                            total_bytes += len(payload)
                            received_packets += 1
                    except socket.timeout:
                        break
                duration = time.time() - start_time
                expected_packets = (file_size + 1024 - 1) // 1024
                loss_percentage = 100 * (1 - received_packets / expected_packets)
                speed = (total_bytes * 8) / duration  # bits per second
                print(f"\033[92mUDP transfer #{conn_id} finished, "
                      f"total time: {duration:.2f} seconds, "
                      f"total speed: {speed:.1f} bits/second, "
                      f"percentage of packets received successfully: {100 - loss_percentage:.2f}%\033[0m")
                self.transfer_results.append(('UDP', conn_id, duration, speed, 100 - loss_percentage))
        except Exception as e:
            print(f"\033[91mError in UDP transfer #{conn_id}: {e}\033[0m")
                
    def start(self):
        """Start the client and handle transfers."""
        while True:
            server_ip, udp_port, tcp_port = self._receive_offers()
            
            file_size = int(input("Enter file size (bytes): "))
            tcp_connections = int(input("Enter number of TCP connections: "))
            udp_connections = int(input("Enter number of UDP connections: "))
            
            threads = []
            for i in range(tcp_connections):
                t = threading.Thread(target=self._tcp_transfer, args=(server_ip, tcp_port, file_size, i + 1))
                threads.append(t)
                t.start()

            for i in range(udp_connections):
                t = threading.Thread(target=self._udp_transfer, args=(server_ip, udp_port, file_size, i + 1))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            print("[INFO] All transfers complete, listening to offer requests")

if __name__ == "__main__":
    client = SpeedTestClient()
    client.start()