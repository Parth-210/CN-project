# Remote Desktop Protocol (RDP) Simulation Project — CN Lab

## Goal
Build a simplified Remote Desktop system over LAN to demonstrate:
- Client-server architecture
- Custom application-layer protocol
- TCP-based communication
- Real-time screen + input control

This is NOT a production-grade RDP clone. Focus on clarity, correctness, and demo value.

---

## HARD CONSTRAINTS (NON-NEGOTIABLE)

- MUST be a **desktop application**, NOT a web app
- MUST run locally over LAN (no internet dependency)
- MUST be packaged as **.exe files** for:
  - Server
  - Client
- Use tools like **PyInstaller** or equivalent for packaging
- Final output should be runnable without requiring Python installed

---

## Core Features

1. Screen sharing (server → client)
2. Mouse + keyboard control (client → server)
3. Basic file transfer (both directions)
4. GUI for both client and server
5. Connection via IP + port

---

## Tech Stack

- Choose best suitable language for fast GUI + networking
- Strong preference: Python
- Allowed libraries (example):
  - socket (networking)
  - threading / asyncio
  - mss / PIL (screen capture)
  - OpenCV (optional compression)
  - pynput / pyautogui (input simulation)
  - tkinter / PyQt (GUI)

Avoid heavy or complex frameworks

---

## Architecture

### Server (Host)
- Capture screen periodically
- Compress frames (JPEG/PNG)
- Send frames via TCP
- Receive:
  - Mouse events
  - Keyboard events
  - File transfer data
- Execute input locally

---

### Client (Viewer)
- Connect to server via TCP
- Render incoming frames in GUI window
- Capture mouse + keyboard inside window
- Send input events to server
- Handle file upload/download

---

## Networking

- Use TCP sockets (mandatory)
- Design should allow future UDP extension (optional)

---

## Custom Protocol (IMPORTANT)

Design a simple structured protocol.

Each message:
- TYPE
- LENGTH
- DATA

Example message types:
- FRAME
- MOUSE
- KEY
- FILE_SEND
- FILE_REQUEST

Protocol must be:
- Clearly defined
- Easy to explain in viva
- Implemented cleanly in code

---

## Screen Streaming

- Capture screen using mss or equivalent
- Compress to reduce size
- Send frames at controlled FPS (5–15)

Optional:
- Basic optimization if simple

---

## Input Handling

- Capture client-side input
- Serialize and send
- Execute on server using OS-level libraries

---

## File Transfer

- Send metadata (name, size)
- Transfer in chunks
- Reconstruct on receiver side

---

## GUI

### Server GUI
- Show:
  - Local IP
  - Port
  - Status (waiting / connected)
- Start/Stop server

### Client GUI
- Input:
  - Server IP
  - Port
- Connect button
- Display remote screen
- Capture input

---

## Code Structure

- Modular:
  - networking/
  - protocol/
  - server/
  - client/
  - utils/

Avoid single-file mess

---

## Packaging (VERY IMPORTANT)

Provide:
1. Steps to convert both client and server into `.exe`
2. Use **PyInstaller** (or equivalent)
3. Include:
   - Required flags
   - Handling of dependencies
   - Instructions to run executables

Goal:
- User should run `.exe` directly without setup

---

## Error Handling

- Handle disconnects
- Prevent crashes on bad data
- Minimal logging

---

## Deliverables

1. Working client + server code
2. Protocol definition
3. `.exe` packaging instructions
4. Run instructions
5. Brief explanation for viva:
   - TCP usage
   - Protocol design
   - Data flow

---

## Constraints

- Keep it simple and understandable
- Do NOT over-engineer
- Do NOT convert into web-based solution
- Prioritize working demo

---

## Freedom

You may:
- Choose libraries
- Improve structure
- Optimize lightly

But avoid unnecessary complexity

---

## Output Expectations

- Clean, runnable code
- Minimal but useful documentation
- No fluff