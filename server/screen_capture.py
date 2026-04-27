"""
Screen capture module — grabs the primary monitor and returns JPEG bytes.

Uses the 'mss' library for fast, cross-platform screen capture and
Pillow for JPEG compression.
"""

import io
import mss
import mss.tools
from PIL import Image
from utils.helpers import JPEG_QUALITY


# Persistent screenshotter (reusing it is faster than recreating each frame)
_sct = None


def _get_sct() -> mss.mss:
    global _sct
    if _sct is None:
        _sct = mss.mss()
    return _sct


def capture_screen(quality: int = JPEG_QUALITY) -> tuple[bytes, int, int]:
    """
    Capture the primary monitor and return compressed JPEG bytes.

    Returns
    -------
    (jpeg_bytes, width, height)
    """
    sct = _get_sct()
    monitor = sct.monitors[1]  # Primary monitor (index 0 is "all monitors")
    raw = sct.grab(monitor)

    # Convert BGRA → RGB via Pillow
    img = Image.frombytes("RGB", raw.size, raw.rgb)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue(), img.width, img.height
