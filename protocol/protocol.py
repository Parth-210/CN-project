import struct
import enum
import socket

class MsgType(enum.IntEnum):
    FRAME = 1
    MOUSE = 2
    KEY = 3
    FILE_META = 4
    FILE_CHUNK = 5
    FILE_DONE = 6
    DISCONNECT = 7
    SCREEN_INFO = 8

HDR_FMT = "!BI"
HDR_SZ = 5

def _read(s, n):
    b = bytearray()
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c: raise ConnectionError("Closed")
        b.extend(c)
    return bytes(b)

def send_msg(s, mt, data=b""):
    hdr = struct.pack(HDR_FMT, int(mt), len(data))
    try:
        s.sendall(hdr + data)
    except Exception as e:
        raise ConnectionError(f"Send failed: {e}")

def recv_msg(s):
    hdr = _read(s, HDR_SZ)
    mt_raw, ln = struct.unpack(HDR_FMT, hdr)
    try:
        mt = MsgType(mt_raw)
    except:
        raise ValueError(f"Bad type: {mt_raw}")
    data = _read(s, ln) if ln > 0 else b""
    return mt, data
