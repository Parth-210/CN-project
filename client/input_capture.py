"""
Input capture — binds mouse and keyboard events on the viewer canvas and
serialises them into protocol messages.
"""

import json
import threading
import logging
from pynput import keyboard as kb
from protocol.protocol import MessageType, send_message

logger = logging.getLogger(__name__)

# Map Tkinter button numbers to names
_TK_BTN_MAP = {1: "left", 2: "middle", 3: "right"}


class InputCapture:
    """
    Captures mouse events from the Tkinter canvas and keyboard events
    globally (via pynput listener) and sends them to the server.
    """

    def __init__(self, canvas, send_lock: threading.Lock):
        self.canvas = canvas
        self.sock = None
        self.send_lock = send_lock
        self.server_w = 1
        self.server_h = 1
        self.display_w = 1
        self.display_h = 1
        self.img_offset_x = 0
        self.img_offset_y = 0
        self._kb_listener = None
        self._active = False

    def start(self, sock, server_w: int, server_h: int):
        """Begin capturing input and forwarding to *sock*."""
        self.sock = sock
        self.server_w = server_w
        self.server_h = server_h
        self._active = True

        # Mouse bindings on the canvas
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonPress>", self._on_mouse_press)
        self.canvas.bind("<ButtonRelease>", self._on_mouse_release)
        self.canvas.bind("<MouseWheel>", self._on_mouse_scroll)

        # Global keyboard listener via pynput (works even when canvas
        # doesn't have OS-level focus for key events)
        self._kb_listener = kb.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._kb_listener.start()

    def stop(self):
        self._active = False
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None
        try:
            self.canvas.unbind("<Motion>")
            self.canvas.unbind("<ButtonPress>")
            self.canvas.unbind("<ButtonRelease>")
            self.canvas.unbind("<MouseWheel>")
        except Exception:
            pass

    def update_display_info(self, display_w: int, display_h: int,
                            offset_x: int, offset_y: int):
        """Called by the client app whenever a new frame is rendered."""
        self.display_w = display_w
        self.display_h = display_h
        self.img_offset_x = offset_x
        self.img_offset_y = offset_y

    # --------------------------------------------------------- coordinate mapping
    def _map_coords(self, canvas_x: int, canvas_y: int) -> tuple[int, int]:
        """Map canvas pixel → server screen pixel."""
        # Offset to image top-left
        ix = canvas_x - self.img_offset_x
        iy = canvas_y - self.img_offset_y

        # Clamp to image bounds
        ix = max(0, min(ix, self.display_w - 1))
        iy = max(0, min(iy, self.display_h - 1))

        # Scale to server resolution
        sx = int(ix * self.server_w / self.display_w) if self.display_w > 0 else 0
        sy = int(iy * self.server_h / self.display_h) if self.display_h > 0 else 0
        return sx, sy

    # --------------------------------------------------------- senders
    def _send(self, msg_type, payload: dict):
        if not self._active or self.sock is None:
            return
        try:
            data = json.dumps(payload).encode()
            with self.send_lock:
                send_message(self.sock, msg_type, data)
        except Exception:
            pass  # Connection may have dropped; ignore

    # --------------------------------------------------------- mouse events
    def _on_mouse_move(self, event):
        sx, sy = self._map_coords(event.x, event.y)
        self._send(MessageType.MOUSE, {"event": "move", "x": sx, "y": sy})

    def _on_mouse_press(self, event):
        sx, sy = self._map_coords(event.x, event.y)
        btn = _TK_BTN_MAP.get(event.num, "left")
        self._send(MessageType.MOUSE, {"event": "click", "x": sx, "y": sy,
                                        "button": btn, "pressed": True})

    def _on_mouse_release(self, event):
        sx, sy = self._map_coords(event.x, event.y)
        btn = _TK_BTN_MAP.get(event.num, "left")
        self._send(MessageType.MOUSE, {"event": "click", "x": sx, "y": sy,
                                        "button": btn, "pressed": False})

    def _on_mouse_scroll(self, event):
        sx, sy = self._map_coords(event.x, event.y)
        # On Windows event.delta is typically ±120
        dy = int(event.delta / 120) if event.delta else 0
        self._send(MessageType.MOUSE, {"event": "scroll", "x": sx, "y": sy,
                                        "dx": 0, "dy": dy})

    # --------------------------------------------------------- keyboard events
    def _key_to_str(self, key) -> str:
        """Convert a pynput key to a string suitable for the server."""
        if hasattr(key, "char") and key.char is not None:
            return key.char
        if hasattr(key, "name"):
            return key.name
        return str(key)

    def _on_key_press(self, key):
        self._send(MessageType.KEY, {"event": "press", "key": self._key_to_str(key)})

    def _on_key_release(self, key):
        self._send(MessageType.KEY, {"event": "release", "key": self._key_to_str(key)})
