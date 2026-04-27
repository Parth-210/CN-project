"""
Input handler — executes mouse and keyboard events received from the client.

Uses pynput controllers to perform OS-level input simulation.
"""

import json
import logging
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

logger = logging.getLogger(__name__)

_mouse = MouseController()
_keyboard = KeyboardController()

# Map string button names to pynput Button enums
_BUTTON_MAP = {
    "left":   Button.left,
    "right":  Button.right,
    "middle": Button.middle,
}

# Map special key names to pynput Key enums
_SPECIAL_KEYS = {name: getattr(Key, name) for name in dir(Key) if not name.startswith("_")}


def handle_mouse(data: bytes, server_w: int, server_h: int,
                 client_w: int, client_h: int) -> None:
    """
    Process a MOUSE message payload.

    Expected JSON fields:
        event  : "move" | "click" | "scroll"
        x, y   : coordinates in *client* viewport pixels
        button : "left" | "right" | "middle"  (for click)
        pressed: true/false                     (for click)
        dx, dy : scroll deltas                  (for scroll)
    """
    try:
        info = json.loads(data)
    except json.JSONDecodeError:
        logger.warning("Bad MOUSE JSON: %s", data[:200])
        return

    event = info.get("event")

    # Scale client coordinates → server screen coordinates
    if client_w > 0 and client_h > 0:
        sx = int(info.get("x", 0) * server_w / client_w)
        sy = int(info.get("y", 0) * server_h / client_h)
    else:
        sx = int(info.get("x", 0))
        sy = int(info.get("y", 0))

    if event == "move":
        _mouse.position = (sx, sy)

    elif event == "click":
        _mouse.position = (sx, sy)
        btn = _BUTTON_MAP.get(info.get("button", "left"), Button.left)
        if info.get("pressed", True):
            _mouse.press(btn)
        else:
            _mouse.release(btn)

    elif event == "scroll":
        _mouse.position = (sx, sy)
        dx = int(info.get("dx", 0))
        dy = int(info.get("dy", 0))
        _mouse.scroll(dx, dy)


def handle_key(data: bytes) -> None:
    """
    Process a KEY message payload.

    Expected JSON fields:
        event : "press" | "release"
        key   : key character or special-key name (e.g. "a", "enter", "shift")
    """
    try:
        info = json.loads(data)
    except json.JSONDecodeError:
        logger.warning("Bad KEY JSON: %s", data[:200])
        return

    event = info.get("event")
    key_str = info.get("key", "")

    # Resolve to pynput key
    if key_str in _SPECIAL_KEYS:
        key = _SPECIAL_KEYS[key_str]
    elif len(key_str) == 1:
        key = key_str
    else:
        logger.warning("Unknown key: %s", key_str)
        return

    try:
        if event == "press":
            _keyboard.press(key)
        elif event == "release":
            _keyboard.release(key)
    except Exception as exc:
        logger.warning("Key simulation failed for '%s': %s", key_str, exc)
