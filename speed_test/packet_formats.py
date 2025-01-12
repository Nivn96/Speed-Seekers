import struct

class PacketFormats:
    MAGIC_COOKIE = 0xabcddcba
    OFFER_MESSAGE_TYPE = 0x2
    REQUEST_MESSAGE_TYPE = 0x3
    PAYLOAD_MESSAGE_TYPE = 0x4

    @staticmethod
    def create_offer_packet(udp_port, tcp_port):
        return struct.pack('!IBHH', PacketFormats.MAGIC_COOKIE, PacketFormats.OFFER_MESSAGE_TYPE, udp_port, tcp_port)

    @staticmethod
    def parse_offer_packet(data):
        try:
            magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!IBHH', data)
            if magic_cookie == PacketFormats.MAGIC_COOKIE and message_type == PacketFormats.OFFER_MESSAGE_TYPE:
                return udp_port, tcp_port
        except struct.error:
            pass
        return None

    @staticmethod
    def create_request_packet(file_size):
        return struct.pack('!IBQ', PacketFormats.MAGIC_COOKIE, PacketFormats.REQUEST_MESSAGE_TYPE, file_size)

    @staticmethod
    def parse_request_packet(data):
        try:
            magic_cookie, message_type, file_size = struct.unpack('!IBQ', data)
            if magic_cookie == PacketFormats.MAGIC_COOKIE and message_type == PacketFormats.REQUEST_MESSAGE_TYPE:
                return file_size
        except struct.error:
            pass
        return None

    @staticmethod
    def create_payload_packet(total_segments, current_segment, payload):
        return struct.pack('!IBQQ', PacketFormats.MAGIC_COOKIE, PacketFormats.PAYLOAD_MESSAGE_TYPE, total_segments, current_segment) + payload

    @staticmethod
    def parse_payload_packet(data):
        try:
            header = struct.unpack('!IBQQ', data[:21])
            magic_cookie, message_type, total_segments, current_segment = header
            if magic_cookie == PacketFormats.MAGIC_COOKIE and message_type == PacketFormats.PAYLOAD_MESSAGE_TYPE:
                payload = data[21:]
                return total_segments, current_segment, payload
        except struct.error:
            pass
        return None