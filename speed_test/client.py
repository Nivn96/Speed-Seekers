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
                magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data)
                
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
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Bind to a random available port
            local_port = self._get_available_port()
            sock.bind(('', local_port))
            
            # Send request
            request = struct.pack('!IbQ',
                self.MAGIC_COOKIE,
                0x3,  # request message type
                file_size
            )
            sock.sendto(request, (server_ip, server_port))
            
            # Receive data
            received_segments = set()
            total_segments = None
            bytes_received = 0
            last_receive_time = time.time()
            
            while True:
                try:
                    sock.settimeout(1)
                    data, _ = sock.recvfrom(8192)
                    last_receive_time = time.time()
                    
                    # Unpack payload header
                    header_size = struct.calcsize('!IbQQ')
                    magic_cookie, msg_type, total_segs, seg_num = struct.unpack(
                        '!IbQQ', data[:header_size]
                    )
                    
                    if magic_cookie != self.MAGIC_COOKIE or msg_type != 0x4:
                        continue
                        
                    total_segments = total_segs
                    received_segments.add(seg_num)
                    bytes_received += len(data) - header_size
                    
                except socket.timeout:
                    if time.time() - last_receive_time > 1 and total_segments is not None:
                        break
                        
            duration = time.time() - start_time
            speed = (bytes_received * 8) / duration  # bits per second
            success_rate = (len(received_segments) / total_segments * 100) if total_segments else 0
            
            print(f"\033[92mUDP transfer #{conn_id} finished, "
                  f"total time: {duration:.2f} seconds, "
                  f"total speed: {speed:.1f} bits/second, "
                  f"percentage of packets received successfully: {success_rate:.1f}%\033[0m")
                  
            self.transfer_results.append(('UDP', conn_id, duration, speed, success_rate))
            
        except Exception as e:
            print(f"\033[91mError in UDP transfer #{conn_id}: {e}\033[0m")
        finally:
            sock.close()
            
    def start(self):
        """Start the client."""
        self.running = True
        
        while self.running:
            try:
                # Get user input
                file_size = int(input("Enter file size (bytes): "))
                tcp_connections = int(input("Enter number of TCP connections: "))
                udp_connections = int(input("Enter number of UDP connections: "))
                
                # Wait for server offer
                server_ip, udp_port, tcp_port = self._receive_offers()
                self.current_server = (server_ip, tcp_port)
                
                # Start transfers
                threads = []
                self.transfer_results = []
                
                # Launch TCP transfers
                for i in range(tcp_connections):
                    thread = threading.Thread(
                        target=self._tcp_transfer,
                        args=(server_ip, tcp_port, file_size, i + 1)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
                    
                # Launch UDP transfers
                for i in range(udp_connections):
                    thread = threading.Thread(
                        target=self._udp_transfer,
                        args=(server_ip, udp_port, file_size, i + 1)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
                    
                # Wait for all transfers to complete
                for thread in threads:
                    thread.join()
                    
                print("\033[94mAll transfers complete, listening for offer requests\033[0m")
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"\033[91mClient error: {e}\033[0m")
                
if __name__ == "__main__":
    client = SpeedTestClient()
    client.start()