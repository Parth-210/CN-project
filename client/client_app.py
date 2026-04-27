"""
RDP Simulation — Client Application

Tkinter GUI that:
  - Connects to the RDP server via IP + port
  - Displays the remote screen in real-time
  - Captures mouse/keyboard input and forwards to server
  - Supports bidirectional file transfer
"""

import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog
import logging
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from protocol.protocol import MessageType, send_message, recv_message
from networking.connection import connect_to_server, close_connection
from client.screen_viewer import ScreenViewer
from client.input_capture import InputCapture
from client.file_handler import send_file as client_send_file, receive_file
from utils.helpers import DEFAULT_PORT, RECV_DIR

logger = logging.getLogger(__name__)


class ClientApp:
    """Main client GUI and logic."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RDP Client — Viewer")
        self.root.geometry("1024x720")
        self.root.configure(bg="#1a1a2e")
        self.root.minsize(640, 480)

        # State
        self.sock = None
        self.connected = False
        self.server_w = 1
        self.server_h = 1
        self._send_lock = threading.Lock()

        self._build_ui()

        self.input_capture = InputCapture(self.viewer.canvas, self._send_lock)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"),
                        foreground="#e94560", background="#1a1a2e")
        style.configure("Info.TLabel", font=("Segoe UI", 10),
                        foreground="#eee", background="#16213e")
        style.configure("Card.TFrame", background="#16213e")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("StatusBar.TLabel", font=("Segoe UI", 9),
                        foreground="#aaa", background="#0f3460")

        # Top bar
        top = ttk.Frame(self.root, style="Card.TFrame", padding=8)
        top.pack(fill="x", side="top")

        ttk.Label(top, text="⚡ RDP Client", style="Title.TLabel",
                  background="#16213e").pack(side="left", padx=(8, 20))

        ttk.Label(top, text="Server IP:", style="Info.TLabel").pack(side="left", padx=(4, 2))
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.ip_entry = ttk.Entry(top, textvariable=self.ip_var, width=15,
                                   font=("Segoe UI", 10))
        self.ip_entry.pack(side="left", padx=2)

        ttk.Label(top, text="Port:", style="Info.TLabel").pack(side="left", padx=(8, 2))
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.port_entry = ttk.Entry(top, textvariable=self.port_var, width=6,
                                     font=("Segoe UI", 10))
        self.port_entry.pack(side="left", padx=2)

        self.connect_btn = ttk.Button(top, text="🔗 Connect", style="Accent.TButton",
                                       command=self._connect)
        self.connect_btn.pack(side="left", padx=8)

        self.disconnect_btn = ttk.Button(top, text="✖ Disconnect", style="Accent.TButton",
                                          command=self._disconnect, state="disabled")
        self.disconnect_btn.pack(side="left", padx=4)

        self.file_btn = ttk.Button(top, text="📁 Send File", style="Accent.TButton",
                                    command=self._send_file_dialog, state="disabled")
        self.file_btn.pack(side="left", padx=4)

        # Screen viewer
        viewer_frame = tk.Frame(self.root, bg="#000000")
        viewer_frame.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        self.viewer = ScreenViewer(viewer_frame)

        # Status bar
        self.status_var = tk.StringVar(value="Disconnected")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               style="StatusBar.TLabel", anchor="w", padding=(12, 4))
        status_bar.pack(fill="x", side="bottom")

    # --------------------------------------------------------------- Connect
    def _connect(self):
        ip = self.ip_var.get().strip()
        port = int(self.port_var.get())
        self.status_var.set(f"Connecting to {ip}:{port} …")
        threading.Thread(target=self._do_connect, args=(ip, port), daemon=True).start()

    def _do_connect(self, ip: str, port: int):
        try:
            self.sock = connect_to_server(ip, port)
        except Exception as exc:
            self.root.after(0, lambda: self.status_var.set(f"❌ Connection failed: {exc}"))
            return

        self.connected = True
        self.root.after(0, lambda: self.status_var.set(f"🟢 Connected to {ip}:{port}"))
        self.root.after(0, lambda: self.connect_btn.config(state="disabled"))
        self.root.after(0, lambda: self.disconnect_btn.config(state="normal"))
        self.root.after(0, lambda: self.file_btn.config(state="normal"))
        self.root.after(0, lambda: self.ip_entry.config(state="disabled"))
        self.root.after(0, lambda: self.port_entry.config(state="disabled"))

        # Receive loop
        self._receive_loop()

    # --------------------------------------------------------------- Disconnect
    def _disconnect(self):
        self.connected = False
        try:
            with self._send_lock:
                send_message(self.sock, MessageType.DISCONNECT)
        except Exception:
            pass
        self.input_capture.stop()
        close_connection(self.sock)
        self.sock = None
        self.status_var.set("Disconnected")
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.file_btn.config(state="disabled")
        self.ip_entry.config(state="normal")
        self.port_entry.config(state="normal")

    # -------------------------------------------------------------- Receive
    def _receive_loop(self):
        while self.connected:
            try:
                msg_type, data = recv_message(self.sock)
            except (ConnectionError, ValueError, OSError):
                break

            if msg_type == MessageType.SCREEN_INFO:
                try:
                    info = json.loads(data)
                    self.server_w = info["width"]
                    self.server_h = info["height"]
                    self.input_capture.start(self.sock, self.server_w, self.server_h)
                    logger.info("Server screen: %dx%d", self.server_w, self.server_h)
                except Exception:
                    pass

            elif msg_type == MessageType.FRAME:
                # Schedule GUI update on main thread
                self.root.after(0, self._render_frame, data)

            elif msg_type == MessageType.FILE_META:
                try:
                    path = receive_file(data, self.sock, save_dir=RECV_DIR)
                    self.root.after(0, lambda p=path: self.status_var.set(f"📥 File received: {p}"))
                except Exception as exc:
                    self.root.after(0, lambda e=exc: self.status_var.set(f"❌ File error: {e}"))

            elif msg_type == MessageType.DISCONNECT:
                break

        # Connection ended
        if self.connected:
            self.root.after(0, self._disconnect)

    def _render_frame(self, jpeg_bytes: bytes):
        dw, dh = self.viewer.update_frame(jpeg_bytes)
        ox, oy = self.viewer.get_image_offset()
        self.input_capture.update_display_info(dw, dh, ox, oy)

    # ----------------------------------------------------------- File send
    def _send_file_dialog(self):
        filepath = filedialog.askopenfilename(title="Select file to send")
        if not filepath:
            return
        threading.Thread(target=self._do_send_file, args=(filepath,), daemon=True).start()

    def _do_send_file(self, filepath: str):
        try:
            with self._send_lock:
                client_send_file(self.sock, filepath)
            self.root.after(0, lambda: self.status_var.set(
                f"📤 File sent: {os.path.basename(filepath)}"))
        except Exception as exc:
            self.root.after(0, lambda: self.status_var.set(f"❌ File send error: {exc}"))

    # ----------------------------------------------------------------- Run
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self.connected:
            self._disconnect()
        self.root.destroy()


def main():
    from utils.helpers import setup_logging
    setup_logging()
    app = ClientApp()
    app.run()


if __name__ == "__main__":
    main()
