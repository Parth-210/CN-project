"""
Universal Launcher for RDP Simulation.
Provides a simple GUI to choose between starting the Server or the Client.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk

# Ensure the project root is importable
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

def launch_server():
    root.destroy()
    from server.server_app import main as server_main
    server_main()

def launch_client():
    root.destroy()
    from client.client_app import main as client_main
    client_main()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("RDP")
    root.geometry("400x250")
    root.configure(bg="#1a1a2e")
    root.resizable(False, False)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"),
                    foreground="#e94560", background="#1a1a2e")
    style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"), padding=10)

    ttk.Label(root, text="⚡ RDP Simulation", style="Title.TLabel").pack(pady=(30, 20))

    btn_frame = ttk.Frame(root, padding=20)
    btn_frame.pack(fill="both", expand=True)
    btn_frame.configure(style="TFrame") # Default frame style

    # Custom frame style for dark background
    style.configure("Dark.TFrame", background="#1a1a2e")
    btn_frame.configure(style="Dark.TFrame")

    server_btn = ttk.Button(btn_frame, text="🖥 Start Server (Host)", 
                            style="Accent.TButton", command=launch_server)
    server_btn.pack(fill="x", pady=5)

    client_btn = ttk.Button(btn_frame, text="🔗 Start Client (Viewer)", 
                            style="Accent.TButton", command=launch_client)
    client_btn.pack(fill="x", pady=5)

    ttk.Label(root, text="CN Lab Project — 2026", 
              font=("Segoe UI", 9), foreground="#aaa", background="#1a1a2e").pack(pady=10)

    root.mainloop()
