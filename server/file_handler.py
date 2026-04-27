import os
import json
import logging
from protocol.protocol import MsgType, send_msg, recv_msg
from utils.helpers import CHUNK_SIZE, RECV_DIR

log = logging.getLogger(__name__)

def send_file(s, path):
    name = os.path.basename(path)
    sz = os.path.getsize(path)
    meta = json.dumps({"filename": name, "filesize": sz}).encode()
    send_msg(s, MsgType.FILE_META, meta)
    
    with open(path, "rb") as f:
        while True:
            c = f.read(CHUNK_SIZE)
            if not c: break
            send_msg(s, MsgType.FILE_CHUNK, c)
            
    send_msg(s, MsgType.FILE_DONE)
    log.info(f"Sent: {name}")

def receive_file(meta_bytes, s, d=None):
    if d is None: d = RECV_DIR
    os.makedirs(d, exist_ok=True)
    
    m = json.loads(meta_bytes)
    name = os.path.basename(m["filename"])
    path = os.path.join(d, name)
    
    with open(path, "wb") as f:
        while True:
            mt, data = recv_msg(s)
            if mt == MsgType.FILE_CHUNK: f.write(data)
            elif mt == MsgType.FILE_DONE: break
            else: break
            
    log.info(f"Received: {name}")
    return path
