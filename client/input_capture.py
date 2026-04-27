import json
import threading
import logging
import ctypes
from pynput import keyboard as kb
from protocol.protocol import MsgType, send_msg

log = logging.getLogger(__name__)
TK_BTN = {1: "left", 2: "middle", 3: "right"}
user32 = ctypes.windll.user32

class InputCapture:
    def __init__(self, canvas, lock, hwnd_fn=None):
        self.can, self.lock, self.hwnd_fn = canvas, lock, hwnd_fn
        self.sock = None
        self.sw, self.sh = 1, 1
        self.dw, self.dh = 1, 1
        self.ox, self.oy = 0, 0
        self.kb_lis = None
        self.active = False

    def start(self, s, sw, sh):
        self.sock, self.sw, self.sh, self.active = s, sw, sh, True
        for ev, fn in [("<Motion>", self._mv), ("<ButtonPress>", self._pr), ("<ButtonRelease>", self._rl), ("<MouseWheel>", self._sc)]:
            self.can.bind(ev, fn)
        self.kb_lis = kb.Listener(on_press=self._kp, on_release=self._kr, suppress=True)
        self.kb_lis.start()

    def stop(self):
        self.active = False
        if self.kb_lis: self.kb_lis.stop(); self.kb_lis = None
        for ev in ["<Motion>", "<ButtonPress>", "<ButtonRelease>", "<MouseWheel>"]:
            try: self.can.unbind(ev)
            except: pass

    def update(self, dw, dh, ox, oy):
        self.dw, self.dh, self.ox, self.oy = dw, dh, ox, oy

    def _map(self, cx, cy):
        ix, iy = max(0, min(cx - self.ox, self.dw - 1)), max(0, min(cy - self.oy, self.dh - 1))
        sx = int(ix * self.sw / self.dw) if self.dw > 0 else 0
        sy = int(iy * self.sh / self.dh) if self.dh > 0 else 0
        return sx, sy

    def _send(self, mt, p):
        if not self.active or not self.sock: return
        try:
            with self.lock: send_msg(self.sock, mt, json.dumps(p).encode())
        except: pass

    def _mv(self, e):
        x, y = self._map(e.x, e.y)
        self._send(MsgType.MOUSE, {"event": "move", "x": x, "y": y})

    def _pr(self, e):
        x, y = self._map(e.x, e.y)
        self._send(MsgType.MOUSE, {"event": "click", "x": x, "y": y, "button": TK_BTN.get(e.num, "left"), "pressed": True})

    def _rl(self, e):
        x, y = self._map(e.x, e.y)
        self._send(MsgType.MOUSE, {"event": "click", "x": x, "y": y, "button": TK_BTN.get(e.num, "left"), "pressed": False})

    def _sc(self, e):
        x, y = self._map(e.x, e.y)
        self._send(MsgType.MOUSE, {"event": "scroll", "x": x, "y": y, "dx": 0, "dy": int(e.delta/120) if e.delta else 0})

    def _k_str(self, k):
        return k.char if hasattr(k, "char") and k.char is not None else (k.name if hasattr(k, "name") else str(k))

    def _kp(self, k): self._send(MsgType.KEY, {"event": "press", "key": self._k_str(k)})
    def _kr(self, k): self._send(MsgType.KEY, {"event": "release", "key": self._k_str(k)})
