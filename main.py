import sys
import socket
import threading
from login import assign_role_color

SERVER_IP = '10.97.36.101'
PORT      = 50001


def run_server() -> tuple[str, str]:
    assignments = assign_role_color()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', PORT))
    srv.listen(3)
    print("Server listening...")
    for i in range(1, 4):
        conn, addr = srv.accept()
        print(f"Client {i} connected: {addr}")
        role, color = assignments[f'client_{i}']
        conn.sendall(f"{role},{color}".encode())
        conn.close()
    srv.close()
    return assignments['server']


def run_client() -> tuple[str, str]:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER_IP, PORT))
    data = client.recv(1024).decode()
    client.close()
    role, color = data.split(',')
    return role, color


if __name__ == "__main__":
    from ui import CodenamesUI
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        ui = CodenamesUI()
        def _server():
            role, color = run_server()
            ui.root.after(0, ui.show_role, role, color)
        threading.Thread(target=_server, daemon=True).start()
        ui.run()
    else:
        role, color = run_client()
        CodenamesUI(role, color).run()
