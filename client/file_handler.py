"""
Client-side file transfer helpers.

Re-uses the same send_file / receive_file logic as the server module.
"""

import os
import json
import logging
from protocol.protocol import MessageType, send_message, recv_message
from utils.helpers import FILE_CHUNK_SIZE, RECV_DIR

logger = logging.getLogger(__name__)


def send_file(sock, filepath: str) -> None:
    """Read a local file and stream it to the server."""
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)

    meta = json.dumps({"filename": filename, "filesize": filesize}).encode()
    send_message(sock, MessageType.FILE_META, meta)
    logger.info("Sending file: %s (%d bytes)", filename, filesize)

    sent = 0
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(FILE_CHUNK_SIZE)
            if not chunk:
                break
            send_message(sock, MessageType.FILE_CHUNK, chunk)
            sent += len(chunk)

    send_message(sock, MessageType.FILE_DONE)
    logger.info("File sent: %s (%d bytes)", filename, sent)


def receive_file(meta_data: bytes, sock, save_dir: str | None = None) -> str:
    """Receive a file given the FILE_META payload already read."""
    if save_dir is None:
        save_dir = RECV_DIR
    os.makedirs(save_dir, exist_ok=True)

    meta = json.loads(meta_data)
    filename = os.path.basename(meta["filename"])
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
                logger.warning("Unexpected message during file transfer: %s", msg_type)
                break

    logger.info("File received: %s (%d bytes) → %s", filename, received, filepath)
    return filepath
