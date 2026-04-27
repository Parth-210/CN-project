"""
Custom RDP Protocol — TYPE-LENGTH-DATA binary framing.

Every message on the wire:
  [TYPE: 1 byte] [LENGTH: 4 bytes big-endian] [DATA: LENGTH bytes]

This keeps parsing trivial and is easy to explain in a viva.
"""

import struct
import enum
import socket
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------

class MessageType(enum.IntEnum):
    """One-byte identifiers for each message kind."""
    FRAME        = 0x01  # Server → Client: JPEG screen frame
    MOUSE        = 0x02  # Client → Server: mouse event (JSON)
    KEY          = 0x03  # Client → Server: keyboard event (JSON)
    FILE_META    = 0x04  # Either direction: file metadata (JSON)
    FILE_CHUNK   = 0x05  # Either direction: raw file bytes
    FILE_DONE    = 0x06  # Either direction: transfer complete
    DISCONNECT   = 0x07  # Either direction: graceful disconnect
    SCREEN_INFO  = 0x08  # Server → Client: screen resolution (JSON)


# Header: 1 byte type + 4 bytes length = 5 bytes total
HEADER_FORMAT = "!BI"      # unsigned char + unsigned int (big-endian)
HEADER_SIZE   = struct.calcsize(HEADER_FORMAT)  # 5


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly *n* bytes from *sock*, or raise ConnectionError."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed while reading data")
        buf.extend(chunk)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_message(sock: socket.socket, msg_type: MessageType, data: bytes = b"") -> None:
    """
    Pack and send a single protocol message.

    Parameters
    ----------
    sock : socket
        Connected TCP socket.
    msg_type : MessageType
        The message type tag.
    data : bytes
        Payload (may be empty, e.g. for DISCONNECT / FILE_DONE).
    """
    header = struct.pack(HEADER_FORMAT, int(msg_type), len(data))
    try:
        sock.sendall(header + data)
    except (BrokenPipeError, ConnectionResetError, OSError) as exc:
        raise ConnectionError(f"Failed to send message: {exc}") from exc


def recv_message(sock: socket.socket) -> tuple[MessageType, bytes]:
    """
    Receive a single protocol message.

    Returns
    -------
    (MessageType, bytes)
        The type tag and raw payload.

    Raises
    ------
    ConnectionError
        If the connection drops mid-read.
    ValueError
        If the type byte is unknown.
    """
    header = _recv_exact(sock, HEADER_SIZE)
    raw_type, length = struct.unpack(HEADER_FORMAT, header)

    try:
        msg_type = MessageType(raw_type)
    except ValueError:
        raise ValueError(f"Unknown message type: 0x{raw_type:02x}")

    data = _recv_exact(sock, length) if length > 0 else b""
    return msg_type, data
