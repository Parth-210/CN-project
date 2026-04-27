import io
import tkinter as tk
from PIL import Image, ImageTk

class ScreenViewer:
    def __init__(self, parent):
        self.can = tk.Canvas(parent, bg="#000", highlightthickness=0, cursor="cross")
        self.can.pack(fill="both", expand=True)
        self.photo, self.img_id = None, None
        self.cw, self.ch = 1, 1
        self.can.bind("<Configure>", self._rsz)

    def _rsz(self, e):
        self.cw, self.ch = e.width, e.height

    def update(self, b):
        try: img = Image.open(io.BytesIO(b))
        except: return self.cw, self.ch
        iw, ih = img.size
        if self.cw < 1 or self.ch < 1: return 1, 1
        s = min(self.cw / iw, self.ch / ih)
        nw, nh = int(iw * s), int(ih * s)
        if nw < 1 or nh < 1: return 1, 1
        img = img.resize((nw, nh), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        x, y = self.cw // 2, self.ch // 2
        if self.img_id is None: self.img_id = self.can.create_image(x, y, image=self.photo, anchor="center")
        else:
            self.can.coords(self.img_id, x, y)
            self.can.itemconfig(self.img_id, image=self.photo)
        return nw, nh

    def offset(self):
        if self.img_id is None: return 0, 0
        cx, cy = self.can.coords(self.img_id)
        if self.photo: return int(cx - self.photo.width() // 2), int(cy - self.photo.height() // 2)
        return int(cx), int(cy)
