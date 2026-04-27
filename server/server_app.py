"""
RDP Simulation — Server Application

Tkinter GUI that:
  - Shows local IP / port / connection status
  - Starts/stops the server
  - Streams screen frames to a connected client
  - Receives mouse/keyboard/file commands from the client
  - Allows sending files to the client
"""

import json
import socket
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import logging
import os
import sys

# Ensure project root is on the path so imports work both
# when running as a script and after PyInstaller bundling.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from protocol.protocol import MessageType, send_message, recv_message
from networking.connection import create_server, accept_client, close_connection
from server.screen_capture import capture_screen
from server.input_handler import handle_mouse, handle_key
from server.file_handler import send_file, receive_file
from utils.helpers import get_local_ip, DEFAULT_PORT, FPS, RECV_DIR

logger = logging.getLogger(__name__)


class ServerApp:
    """Main server GUI and logic."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RDP Server")
        self.root.geometry("520x600")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        # State
        self.server_socket: socket.socket | None = None
        self.client_socket: socket.socket | None = None
        self.running = False
        self.connected = False
        self.screen_w = 0
        self.screen_h = 0
        self._send_lock = threading.Lock()

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"),
                        foreground="#e94560", background="#1a1a2e")
        style.configure("Info.TLabel", font=("Segoe UI", 11),
                        foreground="#eee", background="#16213e")
        style.configure("Card.TFrame", background="#16213e")
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))

        # Title
        ttk.Label(self.root, text="⚡  RDP Server", style="Title.TLabel").pack(pady=(18, 6))

        # Info card
        card = ttk.Frame(self.root, style="Card.TFrame", padding=18)
        card.pack(fill="x", padx=24, pady=8)

        local_ip = get_local_ip()
        ttk.Label(card, text=f"🌐  Local IP:   {local_ip}", style="Info.TLabel").pack(anchor="w", pady=2)

        port_frame = ttk.Frame(card, style="Card.TFrame")
        port_frame.pack(anchor="w", fill="x", pady=2)
        ttk.Label(port_frame, text="🔌  Port:         ", style="Info.TLabel").pack(side="left")
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=8,
                                     font=("Segoe UI", 11))
        self.port_entry.pack(side="left")

        self.status_var = tk.StringVar(value="⏸  Stopped")
        self.status_label = ttk.Label(card, textvariable=self.status_var, style="Info.TLabel")
        self.status_label.pack(anchor="w", pady=(6, 0))

        self.client_var = tk.StringVar(value="")
        self.client_label = ttk.Label(card, textvariable=self.client_var, style="Info.TLabel")
        self.client_label.pack(anchor="w", pady=2)

        # Buttons
        btn_frame = ttk.Frame(self.root, style="Card.TFrame", padding=8)
        btn_frame.pack(fill="x", padx=24, pady=6)

        self.start_btn = ttk.Button(btn_frame, text="▶  Start Server",
                                     style="Accent.TButton", command=self._start_server)
        self.start_btn.pack(side="left", padx=4, expand=True, fill="x")

        self.stop_btn = ttk.Button(btn_frame, text="⏹  Stop Server",
                                    style="Accent.TButton", command=self._stop_server,
                                    state="disabled")
        self.stop_btn.pack(side="left", padx=4, expand=True, fill="x")

        self.file_btn = ttk.Button(btn_frame, text="📁  Send File",
                                    style="Accent.TButton", command=self._send_file_dialog,
                                    state="disabled")
        self.file_btn.pack(side="left", padx=4, expand=True, fill="x")

        # Log area
        ttk.Label(self.root, text="📋  Log", style="Title.TLabel",
                  font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=28, pady=(10, 2))
        self.log_area = scrolledtext.ScrolledText(self.root, height=16, font=("Consolas", 9),
                                                   bg="#0f3460", fg="#e0e0e0",
                                                   insertbackground="#e94560",
                                                   relief="flat", bd=0, padx=8, pady=8)
        self.log_area.pack(fill="both", expand=True, padx=24, pady=(0, 18))

    # --------------------------------------------------------------- Logging
    def _log(self, msg: str):
        def _append():
            self.log_area.insert(tk.END, msg + "\n")
            self.log_area.see(tk.END)
        self.root.after(0, _append)

    # -------------------------------------------------------------- Server
    def _start_server(self):
        port = int(self.port_var.get())
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.port_entry.config(state="disabled")
        self.status_var.set("🟡  Waiting for client …")
        self._log(f"Server starting on port {port} …")
        threading.Thread(target=self._server_loop, args=(port,), daemon=True).start()

    def _stop_server(self):
        self.running = False
        self.connected = False
        close_connection(self.client_socket)
        self.client_socket = None
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.file_btn.config(state="disabled")
        self.port_entry.config(state="normal")
        self.status_var.set("⏸  Stopped")
        self.client_var.set("")
        self._log("Server stopped.")

    def _server_loop(self, port: int):
        try:
            self.server_socket = create_server("0.0.0.0", port)
            # Allow accept to be interrupted by closing the socket
            self.server_socket.settimeout(1.0)
        except OSError as exc:
            self._log(f"❌ Cannot bind port {port}: {exc}")
            self.root.after(0, self._stop_server)
            return

        # Wait for a client
        while self.running:
            try:
                self.client_socket, addr = accept_client(self.server_socket)
                break
            except socket.timeout:
                continue
            except OSError:
                break

        if not self.running or self.client_socket is None:
            return

        self.connected = True
        self.root.after(0, lambda: self.status_var.set("🟢  Connected"))
        self.root.after(0, lambda: self.client_var.set(f"👤  Client: {addr[0]}:{addr[1]}"))
        self.root.after(0, lambda: self.file_btn.config(state="normal"))
        self._log(f"Client connected: {addr[0]}:{addr[1]}")

        # Send server screen resolution
        try:
            _, sw, sh = capture_screen()
            self.screen_w, self.screen_h = sw, sh
            info = json.dumps({"width": sw, "height": sh}).encode()
            with self._send_lock:
                send_message(self.client_socket, MessageType.SCREEN_INFO, info)
        except Exception as exc:
            self._log(f"Error sending screen info: {exc}")

        # Spawn sub-threads
        t_send = threading.Thread(target=self._stream_frames, daemon=True)
        t_recv = threading.Thread(target=self._receive_commands, daemon=True)
        t_send.start()
        t_recv.start()
        t_send.join()
        t_recv.join()

        # Client disconnected
        self._log("Client disconnected.")
        self.connected = False
        close_connection(self.client_socket)
        self.client_socket = None
        self.root.after(0, lambda: self.status_var.set("🟡  Waiting for client …"))
        self.root.after(0, lambda: self.client_var.set(""))
        self.root.after(0, lambda: self.file_btn.config(state="disabled"))

        # Re-enter wait loop for next client
        if self.running:
            self._server_loop_accept()

    def _server_loop_accept(self):
        """Wait for another client after one disconnects."""
        while self.running:
            try:
                self.client_socket, addr = accept_client(self.server_socket)
                break
            except socket.timeout:
                continue
            except OSError:
                break

        if not self.running or self.client_socket is None:
            return

        self.connected = True
        self.root.after(0, lambda: self.status_var.set("🟢  Connected"))
        self.root.after(0, lambda a=addr: self.client_var.set(f"👤  Client: {a[0]}:{a[1]}"))
        self.root.after(0, lambda: self.file_btn.config(state="normal"))
        self._log(f"Client connected: {addr[0]}:{addr[1]}")

        try:
            _, sw, sh = capture_screen()
            self.screen_w, self.screen_h = sw, sh
            info = json.dumps({"width": sw, "height": sh}).encode()
            with self._send_lock:
                send_message(self.client_socket, MessageType.SCREEN_INFO, info)
        except Exception:
            pass

        t_send = threading.Thread(target=self._stream_frames, daemon=True)
        t_recv = threading.Thread(target=self._receive_commands, daemon=True)
        t_send.start()
        t_recv.start()
        t_send.join()
        t_recv.join()

        self._log("Client disconnected.")
        self.connected = False
        close_connection(self.client_socket)
        self.client_socket = None
        self.root.after(0, lambda: self.status_var.set("🟡  Waiting for client …"))
        self.root.after(0, lambda: self.client_var.set(""))
        self.root.after(0, lambda: self.file_btn.config(state="disabled"))
        if self.running:
            self._server_loop_accept()

    # -------------------------------------------------------- Frame streaming
    def _stream_frames(self):
        interval = 1.0 / FPS
        while self.running and self.connected:
            t0 = time.time()
            try:
                jpeg_bytes, w, h = capture_screen()
                self.screen_w, self.screen_h = w, h
                with self._send_lock:
                    send_message(self.client_socket, MessageType.FRAME, jpeg_bytes)
            except ConnectionError:
                self.connected = False
                break
            except Exception as exc:
                logger.debug("Frame error: %s", exc)
                continue
            elapsed = time.time() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ------------------------------------------------------- Command receiver
    def _receive_commands(self):
        while self.running and self.connected:
            try:
                msg_type, data = recv_message(self.client_socket)
            except (ConnectionError, ValueError, OSError):
                self.connected = False
                break

            if msg_type == MessageType.MOUSE:
                handle_mouse(data, self.screen_w, self.screen_h,
                             self.screen_w, self.screen_h)  # client sends scaled coords

            elif msg_type == MessageType.KEY:
                handle_key(data)

            elif msg_type == MessageType.FILE_META:
                try:
                    path = receive_file(data, self.client_socket, save_dir=RECV_DIR)
                    self._log(f"📥 File received: {path}")
                except Exception as exc:
                    self._log(f"❌ File receive error: {exc}")

            elif msg_type == MessageType.DISCONNECT:
                self._log("Client sent DISCONNECT.")
                self.connected = False
                break

    # ----------------------------------------------------------- File send
    def _send_file_dialog(self):
        filepath = filedialog.askopenfilename(title="Select file to send")
        if not filepath:
            return
        threading.Thread(target=self._do_send_file, args=(filepath,), daemon=True).start()

    def _do_send_file(self, filepath: str):
        try:
            with self._send_lock:
                send_file(self.client_socket, filepath)
            self._log(f"📤 File sent: {os.path.basename(filepath)}")
        except Exception as exc:
            self._log(f"❌ File send error: {exc}")

    # ----------------------------------------------------------------- Run
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._stop_server()
        self.root.destroy()


def main():
    from utils.helpers import setup_logging
    setup_logging()
    app = ServerApp()
    app.run()


if __name__ == "__main__":
    main()
