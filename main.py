from __future__ import annotations
import sys
import json
import socket
import threading
from login import assign_role_color
from controller import GameController

SERVER_IP = '10.97.36.101'
PORT      = 50001

# ── Shared server state ───────────────────────────────────────────────────────

_clients:      list                    = []
_clients_lock                          = threading.Lock()
_controller:   GameController | None   = None
_game_started                          = threading.Event()


def _send(conn: socket.socket, msg: dict):
    conn.sendall((json.dumps(msg) + "\n").encode())


def _broadcast(msg: dict):
    data = (json.dumps(msg) + "\n").encode()
    with _clients_lock:
        for conn, _, _ in _clients:
            try:
                conn.sendall(data)
            except OSError:
                pass


def _client_thread(conn: socket.socket, role: str, color: str):
    global _controller
    _send(conn, {"type": "login", "role": role, "color": color})

    with _clients_lock:
        _clients.append((conn, role, color))
        count = len(_clients)

    if count == 3:  # alle 4 Spieler verbunden (Server + 3 Clients)
        _controller = GameController()
        _game_started.set()
        _broadcast({"type": "game_start", "state": _controller.get_state()})

    try:
        buf = ""
        while True:
            chunk = conn.recv(4096).decode()
            if not chunk:
                break
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if line.strip():
                    _handle_msg(conn, role, color, json.loads(line))
    except OSError:
        pass
    finally:
        conn.close()
        with _clients_lock:
            _clients[:] = [(c, r, col) for c, r, col in _clients if c is not conn]


def _handle_msg(*_):
    # Platzhalter für spätere Spielaktionen (submit_hint, reveal_tile, end_turn)
    pass


# ── Public API ────────────────────────────────────────────────────────────────

def run_server(on_game_start=None) -> tuple[str, str]:
    """
    Bindet den Server-Socket, nimmt 3 Clients an und startet Runde 1
    automatisch, sobald alle 4 Spieler verbunden sind.
    on_game_start(state) wird aus dem Accept-Thread aufgerufen
    (in tkinter-Apps: als lambda mit root.after(0, ...) übergeben).
    Gibt sofort die Rolle des Server-Spielers zurück.
    """
    assignments = assign_role_color()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', PORT))
    srv.listen(3)
    print("Server listening...")

    def _accept_loop():
        for i in range(1, 4):
            conn, addr = srv.accept()
            print(f"Client {i} connected: {addr}")
            role, color = assignments[f'client_{i}']
            threading.Thread(
                target=_client_thread,
                args=(conn, role, color),
                daemon=True,
            ).start()
        _game_started.wait()
        if on_game_start:
            on_game_start(_controller.get_state())

    threading.Thread(target=_accept_loop, daemon=True).start()
    return assignments['server']


def run_client(on_game_start=None) -> tuple[str, str]:
    """
    Verbindet mit dem Server, empfängt die Rollenzuweisung und wartet im
    Hintergrund auf game_start.
    on_game_start(state) wird aus dem Listener-Thread aufgerufen
    (in tkinter-Apps: als lambda mit root.after(0, ...) übergeben).
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER_IP, PORT))

    buf = ""
    while "\n" not in buf:
        buf += client.recv(4096).decode()
    line, buf = buf.split("\n", 1)
    msg   = json.loads(line)
    role  = msg["role"]
    color = msg["color"]

    def _listen():
        nonlocal buf
        while True:
            try:
                chunk = client.recv(4096).decode()
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if not line.strip():
                        continue
                    m = json.loads(line)
                    if m.get("type") == "game_start" and on_game_start:
                        on_game_start(m["state"])
            except OSError:
                break

    threading.Thread(target=_listen, daemon=True).start()
    return role, color


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from ui import CodenamesUI

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        ui = CodenamesUI()
        def _server():
            role, color = run_server(
                on_game_start=lambda state: ui.root.after(0, ui.show_game_from_state, state),
            )
            ui.root.after(0, ui.show_role, role, color)
        threading.Thread(target=_server, daemon=True).start()
        ui.run()
    else:
        ui = CodenamesUI()
        def _client():
            role, color = run_client(
                on_game_start=lambda state: ui.root.after(0, ui.show_game_from_state, state),
            )
            ui.root.after(0, ui.show_role, role, color)
        threading.Thread(target=_client, daemon=True).start()
        ui.run()
