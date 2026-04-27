"""
File transfer helpers — used by both server and client.

Protocol:
  1.  Sender  → FILE_META  (JSON: {"filename": ..., "filesize": ...})
  2.  Sender  → FILE_CHUNK × N  (raw bytes, up to FILE_CHUNK_SIZE each)
  3.  Sender  → FILE_DONE  (empty payload)
"""

import os
import json
import logging
from protocol.protocol import MessageType, send_message, recv_message
from utils.helpers import FILE_CHUNK_SIZE, RECV_DIR

logger = logging.getLogger(__name__)


def send_file(sock, filepath: str) -> None:
    """Read a local file and stream it over the protocol."""
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)

    # 1. Send metadata
    meta = json.dumps({"filename": filename, "filesize": filesize}).encode()
    send_message(sock, MessageType.FILE_META, meta)
    logger.info("Sending file: %s (%d bytes)", filename, filesize)

    # 2. Send chunks
    sent = 0
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(FILE_CHUNK_SIZE)
            if not chunk:
                break
            send_message(sock, MessageType.FILE_CHUNK, chunk)
            sent += len(chunk)

    # 3. Signal completion
    send_message(sock, MessageType.FILE_DONE)
    logger.info("File sent: %s (%d bytes)", filename, sent)


def receive_file(meta_data: bytes, sock, save_dir: str | None = None) -> str:
    """
    Receive a file given that the FILE_META message has already been read.

    Parameters
    ----------
    meta_data : bytes
        The payload from the FILE_META message (JSON).
    sock : socket
        The connection socket to read FILE_CHUNK / FILE_DONE from.
    save_dir : str or None
        Directory to save the file into. Defaults to RECV_DIR.

    Returns
    -------
    str
        Absolute path to the saved file.
    """
    if save_dir is None:
        save_dir = RECV_DIR
    os.makedirs(save_dir, exist_ok=True)

    meta = json.loads(meta_data)
    filename = os.path.basename(meta["filename"])  # Sanitise
    filesize = meta["filesize"]
    filepath = os.path.join(save_dir, filename)

    logger.info("Receiving file: %s (%d bytes)", filename, filesize)

    received = 0
    with open(filepath, "wb") as f:
        while True:
            msg_type, data = recv_message(sock)
            if msg_type == MessageType.FILE_CHUNK:
                f.write(data)
                received += len(data)
            elif msg_type == MessageType.FILE_DONE:
                break
            else:
                logger.warning("Unexpected message type during file transfer: %s", msg_type)
                break

    logger.info("File received: %s (%d bytes) → %s", filename, received, filepath)
    return filepath
