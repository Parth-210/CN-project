import io
import mss
from PIL import Image
from utils.helpers import QUALITY

_sct = None

def get_sct():
    global _sct
    if _sct is None: _sct = mss.mss()
    return _sct

def capture_screen(q=QUALITY):
    s = get_sct()
    mon = s.monitors[1]
    raw = s.grab(mon)
    img = Image.frombytes("RGB", raw.size, raw.rgb)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=q)
    return buf.getvalue(), img.width, img.height
