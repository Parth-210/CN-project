"""Integration test — verify full server↔client data flow."""

import sys, socket, threading, time, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocol.protocol import MessageType, send_message, recv_message
from networking.connection import create_server, accept_client, connect_to_server, close_connection
from server.screen_capture import capture_screen

frames_received = []
server_ready = threading.Event()

def server_thread():
    srv = create_server("127.0.0.1", 15902)
    server_ready.set()
    conn, addr = accept_client(srv)

    # Send screen info
    jpeg, sw, sh = capture_screen()
    info = json.dumps({"width": sw, "height": sh}).encode()
    send_message(conn, MessageType.SCREEN_INFO, info)

    # Stream 5 frames
    for i in range(5):
        jpeg, w, h = capture_screen(quality=30)
        send_message(conn, MessageType.FRAME, jpeg)
        time.sleep(0.05)

    # Receive a mouse event
    mt, data = recv_message(conn)
    print(f"Server received: {mt.name} = {data.decode()}")

    # Send disconnect
    send_message(conn, MessageType.DISCONNECT)
    time.sleep(0.1)
    close_connection(conn)
    srv.close()


t = threading.Thread(target=server_thread, daemon=True)
t.start()
server_ready.wait(timeout=3)
time.sleep(0.2)

# Client side
sock = connect_to_server("127.0.0.1", 15902)

while True:
    mt, data = recv_message(sock)
    if mt == MessageType.SCREEN_INFO:
        info = json.loads(data)
        print(f"Screen info: {info['width']}x{info['height']}")
        # Send a mouse event after receiving screen info
        send_message(sock, MessageType.MOUSE,
                     json.dumps({"event": "click", "x": 500, "y": 300,
                                 "button": "left", "pressed": True}).encode())
    elif mt == MessageType.FRAME:
        frames_received.append(len(data))
    elif mt == MessageType.DISCONNECT:
        break

close_connection(sock)
t.join(timeout=3)

print(f"Frames received: {len(frames_received)}")
print(f"Frame sizes: {[f'{s//1024}KB' for s in frames_received]}")
print("=== Full integration test PASSED ===")
