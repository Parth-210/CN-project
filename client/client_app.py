import json, threading, os, sys, logging
import tkinter as tk
from tkinter import ttk, filedialog

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

from protocol.protocol import MsgType, send_msg, recv_msg
from networking.connection import connect_srv, close_conn
from client.screen_viewer import ScreenViewer
from client.input_capture import InputCapture
from client.file_handler import send_file, receive_file
from utils.helpers import PORT, RECV_DIR

class ClientApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RDP Viewer")
        self.root.geometry("1024x720")
        self.root.configure(bg="#1a1a2e")
        self.sock, self.connected = None, False
        self.sw, self.sh = 1, 1
        self.lock = threading.Lock()
        self._ui()
        self.ic = InputCapture(self.view.can, self.lock)

    def _ui(self):
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("T.TLabel", font=("Segoe UI", 16, "bold"), foreground="#e94560", background="#1a1a2e")
        st.configure("I.TLabel", font=("Segoe UI", 10), foreground="#eee", background="#16213e")
        st.configure("C.TFrame", background="#16213e")
        st.configure("B.TButton", font=("Segoe UI", 10, "bold"))
        st.configure("S.TLabel", font=("Segoe UI", 9), foreground="#aaa", background="#0f3460")

        t = ttk.Frame(self.root, style="C.TFrame", padding=8); t.pack(fill="x")
        ttk.Label(t, text="⚡ RDP Client", style="T.TLabel", background="#16213e").pack(side="left", padx=10)
        
        ttk.Label(t, text="IP:", style="I.TLabel").pack(side="left")
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.ip_ent = ttk.Entry(t, textvariable=self.ip_var, width=15); self.ip_ent.pack(side="left", padx=2)
        
        ttk.Label(t, text="Port:", style="I.TLabel").pack(side="left", padx=5)
        self.port_var = tk.StringVar(value=str(PORT))
        self.port_ent = ttk.Entry(t, textvariable=self.port_var, width=6); self.port_ent.pack(side="left", padx=2)

        self.conn_btn = ttk.Button(t, text="🔗 Connect", style="B.TButton", command=self._connect)
        self.conn_btn.pack(side="left", padx=5)
        self.disc_btn = ttk.Button(t, text="✖ Disc", style="B.TButton", command=self._disc, state="disabled")
        self.disc_btn.pack(side="left", padx=2)
        self.file_btn = ttk.Button(t, text="📁 File", style="B.TButton", command=self._file_dlg, state="disabled")
        self.file_btn.pack(side="left", padx=2)

        vf = tk.Frame(self.root, bg="#000"); vf.pack(fill="both", expand=1, padx=4, pady=2)
        self.view = ScreenViewer(vf)

        self.stat_var = tk.StringVar(value="Disconnected")
        ttk.Label(self.root, textvariable=self.stat_var, style="S.TLabel", anchor="w", padding=8).pack(fill="x", side="bottom")

    def _connect(self):
        ip, p = self.ip_var.get().strip(), int(self.port_var.get())
        self.stat_var.set(f"Connecting to {ip}:{p}...")
        threading.Thread(target=self._do_conn, args=(ip, p), daemon=True).start()

    def _do_conn(self, ip, p):
        try: self.sock = connect_srv(ip, p)
        except Exception as e:
            self.root.after(0, lambda: self.stat_var.set(f"❌ Failed: {e}"))
            return
        self.connected = True
        self.root.after(0, self._on_conn)
        self._recv_loop()

    def _on_conn(self):
        self.stat_var.set(f"🟢 Connected")
        self.conn_btn.config(state="disabled"); self.disc_btn.config(state="normal")
        self.file_btn.config(state="normal"); self.ip_ent.config(state="disabled"); self.port_ent.config(state="disabled")

    def _disc(self):
        self.connected = False
        try:
            with self.lock: send_msg(self.sock, MsgType.DISCONNECT)
        except: pass
        self.ic.stop(); close_conn(self.sock); self.sock = None
        self.stat_var.set("Disconnected")
        self.conn_btn.config(state="normal"); self.disc_btn.config(state="disabled")
        self.file_btn.config(state="disabled"); self.ip_ent.config(state="normal"); self.port_ent.config(state="normal")

    def _recv_loop(self):
        while self.connected:
            try:
                mt, d = recv_msg(self.sock)
                if mt == MsgType.SCREEN_INFO:
                    m = json.loads(d); self.sw, self.sh = m["width"], m["height"]
                    self.ic.start(self.sock, self.sw, self.sh)
                elif mt == MsgType.FRAME: self.root.after(0, self._render, d)
                elif mt == MsgType.FILE_META:
                    p = receive_file(d, self.sock)
                    self.root.after(0, lambda p=p: self.stat_var.set(f"📥 Received: {os.path.basename(p)}"))
                elif mt == MsgType.DISCONNECT: break
            except: break
        if self.connected: self.root.after(0, self._disc)

    def _render(self, b):
        dw, dh = self.view.update(b)
        ox, oy = self.view.offset()
        self.ic.update(dw, dh, ox, oy)

    def _file_dlg(self):
        f = filedialog.askopenfilename()
        if f: threading.Thread(target=self._do_send, args=(f,), daemon=True).start()

    def _do_send(self, f):
        try:
            with self.lock: send_file(self.sock, f)
            self.root.after(0, lambda: self.stat_var.set(f"📤 Sent: {os.path.basename(f)}"))
        except Exception as e: self.root.after(0, lambda: self.stat_var.set(f"❌ Error: {e}"))

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self.connected: self._disc()
        self.root.destroy()

def main():
    from utils.helpers import setup_log
    setup_log()
    ClientApp().run()

if __name__ == "__main__": main()
