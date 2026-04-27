import socket
import logging

log = logging.getLogger(__name__)

def create_srv(host, port, bkl=1):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(bkl)
    log.info(f"Server on {host}:{port}")
    return s

def accept_cli(srv):
    c, a = srv.accept()
    log.info(f"Client {a[0]}:{a[1]}")
    return c, a

def connect_srv(host, port, to=10.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(to)
    s.connect((host, port))
    s.settimeout(None)
    log.info(f"Connected to {host}:{port}")
    return s

def close_conn(s):
    if not s: return
    try: s.shutdown(socket.SHUT_RDWR)
    except: pass
    try: s.close()
    except: pass
    log.info("Closed")
