import struct

MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4

def parse_offer_packet(data):
    """Parse an offer packet."""
    try:
        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IBHH', data)
        if magic_cookie == MAGIC_COOKIE and message_type == OFFER_MESSAGE_TYPE:
            return udp_port, tcp_port
    except struct.error:
        pass
    return None

def create_request_packet(file_size):
    """Create a request packet for the client."""
    return struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size)

def parse_payload_packet(data):
    """Parse a payload packet."""
    try:
        magic_cookie, message_type, total_segments, current_segment = struct.unpack('!IBQQ', data[:20])
        if magic_cookie == MAGIC_COOKIE and message_type == PAYLOAD_MESSAGE_TYPE:
            return total_segments, current_segment, data[20:]
    except struct.error:
        pass
    return None
