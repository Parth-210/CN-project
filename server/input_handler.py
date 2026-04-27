import json
import logging
from pynput.mouse import Button, Controller as Mouse
from pynput.keyboard import Key, Controller as Kbd

log = logging.getLogger(__name__)
m_ctl = Mouse()
k_ctl = Kbd()

BTN_MAP = {"left": Button.left, "right": Button.right, "middle": Button.middle}
SPECIAL = {n: getattr(Key, n) for n in dir(Key) if not n.startswith("_")}

def handle_mouse(data, sw, sh, cw, ch):
    try: info = json.loads(data)
    except: return
    ev = info.get("event")
    x, y = info.get("x", 0), info.get("y", 0)
    sx = int(x * sw / cw) if cw > 0 else int(x)
    sy = int(y * sh / ch) if ch > 0 else int(y)

    if ev == "move": m_ctl.position = (sx, sy)
    elif ev == "click":
        m_ctl.position = (sx, sy)
        b = BTN_MAP.get(info.get("button", "left"), Button.left)
        m_ctl.press(b) if info.get("pressed", True) else m_ctl.release(b)
    elif ev == "scroll":
        m_ctl.position = (sx, sy)
        m_ctl.scroll(info.get("dx", 0), info.get("dy", 0))

def handle_key(data):
    try: info = json.loads(data)
    except: return
    ev, k_str = info.get("event"), info.get("key", "")
    k = SPECIAL.get(k_str) or (k_str if len(k_str) == 1 else None)
    if not k: return
    try:
        if ev == "press": k_ctl.press(k)
        elif ev == "release": k_ctl.release(k)
    except: pass
