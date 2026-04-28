# RDP Simulation — CN Lab Project

A simplified Remote Desktop Protocol simulation over LAN demonstrating **client-server architecture**, a **custom application-layer protocol**, **TCP-based communication**, and **real-time screen + input control**.

---

## Features

| Feature | Description |
|---------|-------------|
| Screen Sharing | Server captures and streams its screen to the client in real-time (JPEG, ~10 FPS) |
| Mouse Control | Client captures mouse events (move, click, scroll) and replays them on the server |
| Keyboard Control | Client captures key presses/releases and replays them on the server |
| File Transfer | Bidirectional file transfer between client and server (chunked, any file type) |
| GUI | Tkinter-based GUI for both server and client |
| LAN Connectivity | Connects over TCP via IP address + port |

---

## Project Structure

```
CN-project/
├── protocol/
│   ├── __init__.py
│   └── protocol.py          # Custom TYPE-LENGTH-DATA binary protocol
├── networking/
│   ├── __init__.py
│   └── connection.py         # TCP socket lifecycle helpers
├── server/
│   ├── __init__.py
│   ├── screen_capture.py     # Screen grab + JPEG compression (mss + Pillow)
│   ├── input_handler.py      # Execute mouse/key events (pynput)
│   ├── file_handler.py       # File send/receive logic
│   └── server_app.py         # Server GUI + main loop
├── client/
│   ├── __init__.py
│   ├── screen_viewer.py      # Render JPEG frames on Tkinter Canvas
│   ├── input_capture.py      # Capture mouse/keyboard → send to server
│   ├── file_handler.py       # File send/receive logic
│   └── client_app.py         # Client GUI + main loop
├── utils/
│   ├── __init__.py
│   └── helpers.py            # Constants, IP detection, logging setup
├── run_server.py              # Entry point: Server
├── run_client.py              # Entry point: Client
├── requirements.txt
├── test_integration.py        # Automated integration test
└── README.md
```

---

## Custom Protocol Specification

Every message follows a **TYPE-LENGTH-DATA** binary format:

```
[TYPE: 1 byte] [LENGTH: 4 bytes, big-endian] [DATA: LENGTH bytes]
```

### Message Types

| Code | Name | Direction | Payload |
|------|------|-----------|---------|
| `0x01` | FRAME | Server → Client | Raw JPEG bytes |
| `0x02` | MOUSE | Client → Server | JSON: `{"event","x","y","button","pressed","dx","dy"}` |
| `0x03` | KEY | Client → Server | JSON: `{"event","key"}` |
| `0x04` | FILE_META | Either | JSON: `{"filename","filesize"}` |
| `0x05` | FILE_CHUNK | Either | Raw file bytes (up to 64 KB) |
| `0x06` | FILE_DONE | Either | Empty (signals transfer complete) |
| `0x07` | DISCONNECT | Either | Empty (graceful disconnect) |
| `0x08` | SCREEN_INFO | Server → Client | JSON: `{"width","height"}` |

**Header size:** 5 bytes (1 type + 4 length) — trivially parseable.

---

## How to Run

### Prerequisites

- Python 3.10+ installed
- Windows OS (for screen capture and input simulation)

### 1. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Start the Server

On the **host machine** (the one you want to control remotely):

```bash
python run_server.py
```

The server GUI shows your LAN IP and port. Click **▶ Start Server**.

### 3. Start the Client

On the **viewer machine** (the one you want to control from):

```bash
python run_client.py
```

Enter the server's IP address and port, then click **🔗 Connect**.

### 4. Using the Application

- **View remote screen**: Frames automatically stream to the client canvas
- **Control mouse**: Move/click/scroll inside the client's viewer canvas
- **Control keyboard**: Press keys while the client window is focused
- **Transfer files**: Click **📁 Send File** on either side to send a file to the other
- **Disconnect**: Click **✖ Disconnect** on client or **⏹ Stop** on server

### 4. Start the Universal Launcher

Alternatively, use the universal launcher to choose between Server and Client:

```bash
python launcher.py
```

---

## Packaging as .exe (PyInstaller)

### Install PyInstaller

```bash
python -m pip install pyinstaller
```

### Build Universal Executable

```bash
python -m PyInstaller --onefile --windowed --name RDP_Universal launcher.py
```

### Build Separate Executables (Optional)

```bash
python -m PyInstaller --onefile --windowed --name RDP_Server run_server.py
python -m PyInstaller --onefile --windowed --name RDP_Client run_client.py
```

### Output

Executables will be in the `dist/` folder:
- `dist/RDP_Universal.exe`
- `dist/RDP_Server.exe`
- `dist/RDP_Client.exe`

Run them directly — no Python installation required on the target machine.

### Notes

- `--onefile`: Bundles everything into a single `.exe`
- `--windowed`: Hides the console window (GUI-only)
- If Windows Defender flags the exe, add an exclusion or use `--uac-admin` flag

---

## Data Flow

```
┌──────────────────┐                          ┌──────────────────┐
│     SERVER       │                          │     CLIENT       │
│                  │    SCREEN_INFO (JSON)     │                  │
│  Screen Capture ─┼──────────────────────────►│  Set up scaling  │
│                  │    FRAME (JPEG bytes)     │                  │
│  mss + Pillow   ─┼──────────────────────────►│  Canvas render   │
│                  │                          │                  │
│                  │    MOUSE (JSON)           │                  │
│  pynput execute ◄┼──────────────────────────┤  Mouse capture   │
│                  │    KEY (JSON)             │                  │
│  pynput execute ◄┼──────────────────────────┤  Key capture     │
│                  │                          │                  │
│                  │    FILE_META + CHUNKS     │                  │
│  File I/O       ◄┼─────────────────────────►│  File I/O        │
│                  │                          │                  │
│                  │    DISCONNECT             │                  │
│  Cleanup        ◄┼──────────────────────────┤  Cleanup         │
└──────────────────┘                          └──────────────────┘
```

---

## Viva Talking Points

### TCP Usage
- All communication uses **TCP sockets** for reliable, ordered delivery
- Server binds on `0.0.0.0:<port>` and accepts one client at a time
- Client connects via `socket.connect((ip, port))`
- TCP guarantees frames and input events arrive in order and without corruption

### Protocol Design
- Custom **TYPE-LENGTH-DATA** binary protocol (5-byte header)
- 8 distinct message types cover all features
- Binary framing makes it easy to multiplex frames, input, and file data on a single TCP connection
- `recv_exact()` handles TCP's stream nature — reads exactly N bytes even if they arrive in fragments

### Screen Streaming
- `mss` captures the primary monitor as raw BGRA pixels
- Pillow converts to RGB and compresses as JPEG (quality ~50) reducing ~6 MB raw → ~130 KB per frame
- Frames sent at 10 FPS; client scales to fit its window

### Input Forwarding
- Client captures mouse events (Tkinter bindings) and keyboard events (pynput listener)
- Coordinates are mapped from client's scaled display → server's actual screen resolution
- Server uses pynput controllers to simulate the received input at the OS level

### File Transfer
- Chunked transfer protocol: FILE_META → N × FILE_CHUNK → FILE_DONE
- 64 KB chunks keep memory usage low
- Works for any file type and size

---

## Libraries Used

| Library | Purpose |
|---------|---------|
| `socket` | TCP networking (stdlib) |
| `threading` | Concurrent frame sending + command receiving (stdlib) |
| `struct` | Binary protocol header packing/unpacking (stdlib) |
| `tkinter` | GUI for both server and client (stdlib) |
| `mss` | Fast screen capture |
| `Pillow` | Image processing + JPEG compression |
| `pynput` | Mouse/keyboard capture + simulation |

---

## Testing

Run the automated integration test:

```bash
python test_integration.py
```

This tests: TCP connection → screen info exchange → frame streaming → mouse event round-trip → graceful disconnect.