# server.py
import socket
import threading
import struct
import time
import sys
from typing import Tuple

class SpeedTestServer:
    MAGIC_COOKIE = 0xabcddcba
    OFFER_MESSAGE_TYPE = 0x2
    
    def __init__(self, broadcast_port: int = 13117):
        self.broadcast_port = broadcast_port
        self.tcp_port = self._get_available_port()
        self.udp_port = self._get_available_port()
        self.running = False
        self.ip_address = self._get_local_ip()
        
    def _get_local_ip(self) -> str:
        """Get the local IP address of the server."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
            
    def _get_available_port(self) -> int:
        """Get an available port number."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
        
    def _create_offer_message(self) -> bytes:
        """Create the offer message packet."""
        return struct.pack('!IbHH', 
            self.MAGIC_COOKIE,
            self.OFFER_MESSAGE_TYPE,
            self.udp_port,
            self.tcp_port
        )
        
    def _broadcast_offers(self):
        """Continuously broadcast offer messages."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print(f"\033[92mServer started, listening on IP address {self.ip_address}\033[0m")
        
        while self.running:
            try:
                message = self._create_offer_message()
                sock.sendto(message, ('<broadcast>', self.broadcast_port))
                time.sleep(1)
            except Exception as e:
                print(f"\033[91mError broadcasting offer: {e}\033[0m")
                
        sock.close()
        
    def _handle_tcp_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Handle TCP client connection."""
        try:
            # Receive file size request
            data = client_socket.makefile().readline()
            file_size = int(data.strip())
            
            # Generate and send random data
            chunk_size = 8192
            bytes_sent = 0
            
            while bytes_sent < file_size:
                remaining = file_size - bytes_sent
                to_send = min(chunk_size, remaining)
                client_socket.send(b'0' * to_send)
                bytes_sent += to_send
                
        except Exception as e:
            print(f"\033[91mError handling TCP client {address}: {e}\033[0m")
        finally:
            client_socket.close()
            
    def _handle_udp_client(self, request: bytes, address: Tuple[str, int]):
        """Handle UDP client request."""
        try:
            # Unpack request message
            magic_cookie, msg_type, file_size = struct.unpack('!IbQ', request)
            
            if magic_cookie != self.MAGIC_COOKIE or msg_type != 0x3:
                return
                
            # Calculate number of segments
            segment_size = 1024
            total_segments = (file_size + segment_size - 1) // segment_size
            
            # Create UDP socket for sending data
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for segment_num in range(total_segments):
                remaining = file_size - (segment_num * segment_size)
                payload_size = min(segment_size, remaining)
                
                # Create payload packet
                header = struct.pack('!IbQQ', 
                    self.MAGIC_COOKIE,
                    0x4,  # payload message type
                    total_segments,
                    segment_num
                )
                
                payload = header + b'0' * payload_size
                sock.sendto(payload, address)

                
            sock.close()
            
        except Exception as e:
            print(f"\033[91mError handling UDP client {address}: {e}\033[0m")
            
    def start(self):
        """Start the server."""
        self.running = True
        
        # Start broadcast thread
        broadcast_thread = threading.Thread(target=self._broadcast_offers)
        broadcast_thread.daemon = True
        broadcast_thread.start()
        
        # Start TCP listener
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind(('', self.tcp_port))
        tcp_socket.listen(5)
        
        # Start UDP listener
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(('', self.udp_port))
        
        while self.running:
            try:
                # Handle TCP connections
                tcp_socket.settimeout(1)
                try:
                    client_socket, address = tcp_socket.accept()
                    thread = threading.Thread(
                        target=self._handle_tcp_client,
                        args=(client_socket, address)
                    )
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    pass
                    
                # Handle UDP requests
                udp_socket.settimeout(1)
                try:
                    #data, address = udp_socket.recvfrom(512)
                    data, address = udp_socket.recvfrom(1024)
                    thread = threading.Thread(
                        target=self._handle_udp_client,
                        args=(data, address)
                    )
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    pass
                    
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"\033[91mServer error: {e}\033[0m")
                
        tcp_socket.close()
        udp_socket.close()
        
if __name__ == "__main__":
    server = SpeedTestServer()
    server.start()