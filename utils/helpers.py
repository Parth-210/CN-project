"""
Shared constants and utility functions used by both client and server.
"""

import socket
import logging
import sys

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_PORT    = 5900       # Default RDP-sim port
FPS             = 10         # Target frames per second
JPEG_QUALITY    = 50         # JPEG compression quality (0-100)
FILE_CHUNK_SIZE = 65536      # 64 KB per file-transfer chunk
RECV_DIR        = "received_files"  # Default download folder name

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_local_ip() -> str:
    """
    Return the machine's LAN IP address.

    Uses a UDP trick (no actual data is sent) to determine which
    interface the OS would use to reach an external address.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger for console output."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stdout)
