import socket
import logging
import sys

PORT = 5900
FPS = 60
QUALITY = 30
CHUNK_SIZE = 65536
RECV_DIR = "received_files"

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def setup_log(lvl=logging.INFO):
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=lvl, format=fmt, stream=sys.stdout)
