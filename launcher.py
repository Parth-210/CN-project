import sys
import os
import tkinter as tk
from tkinter import ttk

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

def launch_srv():
    root.destroy()
    from server.server_app import main
    main()

def launch_cli():
    root.destroy()
    from client.client_app import main
    main()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("RDP")
    root.geometry("400x250")
    root.configure(bg="#1a1a2e")
    root.resizable(False, False)

    st = ttk.Style()
    st.theme_use("clam")
    st.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#e94560", background="#1a1a2e")
    st.configure("Accent.TButton", font=("Segoe UI", 12, "bold"), padding=10)
    st.configure("Dark.TFrame", background="#1a1a2e")

    ttk.Label(root, text="⚡ RDP Simulation!", style="Title.TLabel").pack(pady=(30, 20))

    f = ttk.Frame(root, padding=20, style="Dark.TFrame")
    f.pack(fill="both", expand=True)

    ttk.Button(f, text="🖥 Host", style="Accent.TButton", command=launch_srv).pack(fill="x", pady=5)
    ttk.Button(f, text="🔗 Viewer", style="Accent.TButton", command=launch_cli).pack(fill="x", pady=5)

    root.mainloop()
