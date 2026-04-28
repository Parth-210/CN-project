import json, socket, threading, time, os, sys, logging
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

from protocol.protocol import MsgType, send_msg, recv_msg
from networking.connection import create_srv, accept_cli, close_conn
from server.screen_capture import capture_screen
from server.input_handler import handle_mouse, handle_key
from server.file_handler import send_file, receive_file
from utils.helpers import get_ip, PORT, FPS, RECV_DIR

class ServerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RDP Server")
        self.root.geometry("520x600")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(0, 0)
        self.srv_sock, self.cli_sock = None, None
        self.running, self.connected = False, False
        self.sw, self.sh = 0, 0
        self.lock = threading.Lock()
        self._ui()

    def _ui(self):
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("T.TLabel", font=("Segoe UI", 18, "bold"), foreground="#e94560", background="#1a1a2e")
        st.configure("I.TLabel", font=("Segoe UI", 11), foreground="#eee", background="#16213e")
        st.configure("C.TFrame", background="#16213e")
        st.configure("B.TButton", font=("Segoe UI", 11, "bold"))

        ttk.Label(self.root, text="⚡ RDP Server", style="T.TLabel").pack(pady=15)
        c = ttk.Frame(self.root, style="C.TFrame", padding=15)
        c.pack(fill="x", padx=20, pady=5)
        ttk.Label(c, text=f"🌐 IP: {get_ip()}", style="I.TLabel").pack(anchor="w")
        
        pf = ttk.Frame(c, style="C.TFrame")
        pf.pack(anchor="w", fill="x", pady=2)
        ttk.Label(pf, text="🔌 Port: ", style="I.TLabel").pack(side="left")
        self.port_var = tk.StringVar(value=str(PORT))
        self.port_ent = ttk.Entry(pf, textvariable=self.port_var, width=8)
        self.port_ent.pack(side="left")

        self.stat_var = tk.StringVar(value="⏸ Stopped")
        ttk.Label(c, textvariable=self.stat_var, style="I.TLabel").pack(anchor="w", pady=5)
        self.cli_var = tk.StringVar(value="")
        ttk.Label(c, textvariable=self.cli_var, style="I.TLabel").pack(anchor="w")

        bf = ttk.Frame(self.root, style="C.TFrame", padding=5)
        bf.pack(fill="x", padx=20)
        self.start_btn = ttk.Button(bf, text="▶ Start", style="B.TButton", command=self._start)
        self.start_btn.pack(side="left", padx=2, expand=True, fill="x")
        self.stop_btn = ttk.Button(bf, text="⏹ Stop", style="B.TButton", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=2, expand=True, fill="x")
        self.file_btn = ttk.Button(bf, text="📁 File", style="B.TButton", command=self._send_file_dlg, state="disabled")
        self.file_btn.pack(side="left", padx=2, expand=True, fill="x")

        self.log_area = scrolledtext.ScrolledText(self.root, height=15, bg="#0f3460", fg="#e0e0e0", bd=0)
        self.log_area.pack(fill="both", expand=True, padx=20, pady=15)

    def _log(self, m):
        self.root.after(0, lambda: (self.log_area.insert(tk.END, m + "\n"), self.log_area.see(tk.END)))

    def _start(self):
        p = int(self.port_var.get())
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.port_ent.config(state="disabled")
        self.stat_var.set("🟡 Waiting...")
        self._log(f"Starting on {p}")
        threading.Thread(target=self._loop, args=(p,), daemon=True).start()

    def _stop(self):
        self.running = False
        self.connected = False
        close_conn(self.cli_sock)
        self.cli_sock = None
        if self.srv_sock:
            try: self.srv_sock.close()
            except: pass
            self.srv_sock = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.file_btn.config(state="disabled")
        self.port_ent.config(state="normal")
        self.stat_var.set("⏸ Stopped")
        self.cli_var.set("")
        self._log("Stopped")

    def _loop(self, p):
        try:
            self.srv_sock = create_srv("0.0.0.0", p)
            self.srv_sock.settimeout(1.0)
        except Exception as e:
            self._log(f"❌ Error: {e}")
            self.root.after(0, self._stop)
            return

        while self.running:
            try:
                self.cli_sock, addr = accept_cli(self.srv_sock)
                self.connected = True
                self.root.after(0, lambda: (self.stat_var.set("🟢 Connected"), self.cli_var.set(f"👤 {addr[0]}:{addr[1]}"), self.file_btn.config(state="normal")))
                self._log(f"Connected: {addr[0]}")
                
                _, sw, sh = capture_screen()
                self.sw, self.sh = sw, sh
                with self.lock: send_msg(self.cli_sock, MsgType.SCREEN_INFO, json.dumps({"width": sw, "height": sh}).encode())
                
                t1 = threading.Thread(target=self._stream, daemon=True)
                t2 = threading.Thread(target=self._recv, daemon=True)
                t1.start(); t2.start()
                t1.join(); t2.join()
                
                self._log("Disconnected")
                self.connected = False
                close_conn(self.cli_sock)
                self.cli_sock = None
                self.root.after(0, lambda: (self.stat_var.set("🟡 Waiting..."), self.cli_var.set(""), self.file_btn.config(state="disabled")))
            except socket.timeout: continue
            except: break

    def _stream(self):
        delay = 1.0 / FPS
        while self.running and self.connected:
            t0 = time.time()
            try:
                b, w, h = capture_screen()
                self.sw, self.sh = w, h
                with self.lock: send_msg(self.cli_sock, MsgType.FRAME, b)
            except: break
            time.sleep(max(0, delay - (time.time() - t0)))

    def _recv(self):
        while self.running and self.connected:
            try:
                mt, d = recv_msg(self.cli_sock)
                if mt == MsgType.MOUSE: handle_mouse(d, self.sw, self.sh, self.sw, self.sh)
                elif mt == MsgType.KEY: handle_key(d)
                elif mt == MsgType.FILE_META:
                    path = receive_file(d, self.cli_sock)
                    self._log(f"📥 Received: {os.path.basename(path)}")
                elif mt == MsgType.DISCONNECT: break
            except: break
        self.connected = False

    def _send_file_dlg(self):
        f = filedialog.askopenfilename()
        if f: threading.Thread(target=self._do_send, args=(f,), daemon=True).start()

    def _do_send(self, f):
        try:
            with self.lock: send_file(self.cli_sock, f)
            self._log(f"📤 Sent: {os.path.basename(f)}")
        except Exception as e: self._log(f"❌ Error: {e}")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self._stop()
        self.root.destroy()

def main():
    from utils.helpers import setup_log
    setup_log()
    ServerApp().run()

if __name__ == "__main__":
    main()
