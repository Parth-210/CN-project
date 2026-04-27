"""
Input capture — forwards mouse and keyboard to the server, and
SUPPRESSES all keyboard input on the local machine while connected.

How blocking works:
  - Keyboard: pynput Listener(suppress=True) intercepts every keypress
    before it reaches the OS, so typing in the RDP viewer never affects
    local applications (no accidental Alt-F4, Win key, etc.).
  - Mouse inside the canvas: Tkinter consumes the event, so local apps
    never see the click.  We deliberately do NOT suppress mouse globally
    so the user can still click the Disconnect / Send-File buttons.
"""

import json
import threading
import logging
import ctypes
import ctypes.wintypes

from pynput import keyboard as kb
from pynput import mouse as ms
from protocol.protocol import MessageType, send_message

logger = logging.getLogger(__name__)

# Map Tkinter button numbers → names
_TK_BTN_MAP = {1: "left", 2: "middle", 3: "right"}

# Win32 helper to check if our window is in the foreground
_user32 = ctypes.windll.user32


def _our_window_focused(root_hwnd: int) -> bool:
    """Return True when the root Tk window is the foreground window."""
    try:
        fg = _user32.GetForegroundWindow()
        return fg == root_hwnd
    except Exception:
        return True  # Safer to suppress if we can't tell


class InputCapture:
    """
    Captures mouse/keyboard and forwards them to the server.

    While connected:
      - Every key press/release is intercepted (suppress=True) so the local
        OS never sees it — only the server processes it.
      - Mouse events inside the canvas are forwarded via Tkinter bindings;
        mouse events in the toolbar area work normally (for Disconnect etc.)
    """

    def __init__(self, canvas, send_lock: threading.Lock, root_hwnd_getter=None):
        self.canvas = canvas
        self.sock = None
        self.send_lock = send_lock
        self._root_hwnd_getter = root_hwnd_getter  # callable → int

        self.server_w = 1
        self.server_h = 1
        self.display_w = 1
        self.display_h = 1
        self.img_offset_x = 0
        self.img_offset_y = 0

        self._kb_listener = None
        self._active = False

    # ---------------------------------------------------------------- lifecycle

    def start(self, sock, server_w: int, server_h: int):
        """
        Begin capturing. Keyboard events will be SUPPRESSED locally.
        Call this only after a successful connection is established.
        """
        self.sock = sock
        self.server_w = server_w
        self.server_h = server_h
        self._active = True

        # Canvas mouse bindings
        self.canvas.bind("<Motion>",       self._on_mouse_move)
        self.canvas.bind("<ButtonPress>",  self._on_mouse_press)
        self.canvas.bind("<ButtonRelease>",self._on_mouse_release)
        self.canvas.bind("<MouseWheel>",   self._on_mouse_scroll)

        # Keyboard: suppress=True blocks the key from reaching the local OS
        self._kb_listener = kb.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
            suppress=True,          # ← local keyboard is blocked
        )
        self._kb_listener.start()
        logger.info("Input capture started — local keyboard suppressed")

    def stop(self):
        """Release all hooks and restore normal local input."""
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
        logger.info("Input capture stopped — local keyboard restored")

    def update_display_info(self, display_w: int, display_h: int,
                            offset_x: int, offset_y: int):
        """Called by the client app on each new rendered frame."""
        self.display_w = display_w
        self.display_h = display_h
        self.img_offset_x = offset_x
        self.img_offset_y = offset_y

    # --------------------------------------------------------- coordinate mapping

    def _map_coords(self, canvas_x: int, canvas_y: int) -> tuple[int, int]:
        """Canvas pixel → server screen pixel."""
        ix = canvas_x - self.img_offset_x
        iy = canvas_y - self.img_offset_y
        ix = max(0, min(ix, self.display_w - 1))
        iy = max(0, min(iy, self.display_h - 1))
        sx = int(ix * self.server_w / self.display_w) if self.display_w > 0 else 0
        sy = int(iy * self.server_h / self.display_h) if self.display_h > 0 else 0
        return sx, sy

    # ------------------------------------------------------------------ senders

    def _send(self, msg_type, payload: dict):
        if not self._active or self.sock is None:
            return
        try:
            data = json.dumps(payload).encode()
            with self.send_lock:
                send_message(self.sock, msg_type, data)
        except Exception:
            pass

    # --------------------------------------------------------------- mouse events
    # (Tkinter only fires these when the pointer is inside the canvas,
    #  so toolbar clicks fall through to the local OS normally.)

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
        dy = int(event.delta / 120) if event.delta else 0
        self._send(MessageType.MOUSE, {"event": "scroll", "x": sx, "y": sy,
                                        "dx": 0, "dy": dy})

    # ------------------------------------------------------------- keyboard events
    # These fire for EVERY key, even when the RDP window is not focused,
    # because we use a global pynput listener with suppress=True.

    def _key_to_str(self, key) -> str:
        if hasattr(key, "char") and key.char is not None:
            return key.char
        if hasattr(key, "name"):
            return key.name
        return str(key)

    def _on_key_press(self, key):
        self._send(MessageType.KEY, {"event": "press", "key": self._key_to_str(key)})
        # suppress=True on the listener already blocks the key locally

    def _on_key_release(self, key):
        self._send(MessageType.KEY, {"event": "release", "key": self._key_to_str(key)})
