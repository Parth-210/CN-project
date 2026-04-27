"""
Screen viewer — renders JPEG frames on a Tkinter Canvas.
"""

import io
import tkinter as tk
from PIL import Image, ImageTk


class ScreenViewer:
    """Displays received JPEG frames on a Tkinter Canvas, scaling to fit."""

    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.canvas = tk.Canvas(parent, bg="#000000", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self._photo = None  # prevent GC of PhotoImage
        self._img_id = None
        self._canvas_w = 1
        self._canvas_h = 1

        # Track canvas resizes
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self._canvas_w = event.width
        self._canvas_h = event.height

    def update_frame(self, jpeg_bytes: bytes) -> tuple[int, int]:
        """
        Decode JPEG bytes and display on the canvas, scaled to fill.

        Returns the displayed (width, height) in canvas pixels so the
        input capture module can scale coordinates correctly.
        """
        try:
            img = Image.open(io.BytesIO(jpeg_bytes))
        except Exception:
            return (self._canvas_w, self._canvas_h)

        # Scale image to fit canvas while maintaining aspect ratio
        img_w, img_h = img.size
        cw, ch = self._canvas_w, self._canvas_h
        if cw < 1 or ch < 1:
            return (1, 1)

        scale = min(cw / img_w, ch / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        if new_w < 1 or new_h < 1:
            return (1, 1)

        img = img.resize((new_w, new_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)

        # Center on canvas
        x = cw // 2
        y = ch // 2
        if self._img_id is None:
            self._img_id = self.canvas.create_image(x, y, image=self._photo, anchor="center")
        else:
            self.canvas.coords(self._img_id, x, y)
            self.canvas.itemconfig(self._img_id, image=self._photo)

        return (new_w, new_h)

    def get_image_offset(self) -> tuple[int, int]:
        """Return the (x, y) offset of the image's top-left corner on the canvas."""
        if self._img_id is None:
            return (0, 0)
        cx, cy = self.canvas.coords(self._img_id)
        if self._photo:
            pw, ph = self._photo.width(), self._photo.height()
            return (int(cx - pw // 2), int(cy - ph // 2))
        return (int(cx), int(cy))
