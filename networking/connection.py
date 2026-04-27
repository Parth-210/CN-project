"""
Networking helpers — thin wrappers around Python's socket API.

All actual message framing is handled by the protocol module;
this module only deals with connection lifecycle.
"""

import socket
import logging

logger = logging.getLogger(__name__)


def create_server(host: str, port: int, backlog: int = 1) -> socket.socket:
    """
    Create, bind, and listen on a TCP server socket.

    Parameters
    ----------
    host : str
        Interface to bind (use "0.0.0.0" for all interfaces).
    port : int
        Port number.
    backlog : int
        Listen backlog.

    Returns
    -------
    socket.socket
        A listening server socket with SO_REUSEADDR set.
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(backlog)
    logger.info("Server listening on %s:%d", host, port)
    return srv


def accept_client(server_socket: socket.socket) -> tuple[socket.socket, tuple[str, int]]:
    """
    Accept a single incoming client connection.

    Returns
    -------
    (socket, (ip, port))
    """
    conn, addr = server_socket.accept()
    logger.info("Client connected from %s:%d", *addr)
    return conn, addr


def connect_to_server(host: str, port: int, timeout: float = 10.0) -> socket.socket:
    """
    Connect to a remote server.

    Parameters
    ----------
    host : str
        Server IP / hostname.
    port : int
        Server port.
    timeout : float
        Connection timeout in seconds.

    Returns
    -------
    socket.socket
        Connected client socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    # After connecting, switch to blocking mode for normal I/O
    sock.settimeout(None)
    logger.info("Connected to server %s:%d", host, port)
    return sock


def close_connection(sock: socket.socket) -> None:
    """Safely shut down and close a socket."""
    if sock is None:
        return
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass
    logger.info("Connection closed")
