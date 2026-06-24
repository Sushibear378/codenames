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

_clients:                list                   = []
_clients_lock                                   = threading.Lock()
_controller:             GameController | None  = None
_game_started                                   = threading.Event()
_server_on_state_update: callable | None        = None
_server_on_role_update:  callable | None        = None
_server_role:            str                    = ""
_server_color:           str                    = ""


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


def _start_new_round():
    """Startet eine neue Runde, tauscht Rollen und sendet den neuen Zustand an alle."""
    global _controller, _server_role
    if _controller is None:
        return
    _controller.start_new_round()

    # Instructor ↔ Agent innerhalb jedes Teams tauschen
    _server_role = "agent" if _server_role == "instructor" else "instructor"
    with _clients_lock:
        _clients[:] = [
            (conn, "agent" if role == "instructor" else "instructor", color)
            for conn, role, color in _clients
        ]
        clients_snapshot = list(_clients)

    # Jeden Client vor dem State-Broadcast über seine neue Rolle informieren
    for conn, role, color in clients_snapshot:
        try:
            _send(conn, {"type": "role_update", "role": role, "color": color})
        except OSError:
            pass

    state = _controller.get_state()
    _broadcast({"type": "state_update", "state": state})
    if _server_on_role_update:
        _server_on_role_update(_server_role, _server_color)
    if _server_on_state_update:
        _server_on_state_update(state)


def _handle_action(color: str, msg: dict) -> None:
    """Verarbeitet eine Spielaktion (submit_hint / reveal_tile / end_turn)
    und sendet den neuen Zustand an alle Clients und den Server-Spieler."""
    global _controller
    if _controller is None:
        return

    mtype  = msg.get("type")
    result = None

    if mtype == "submit_hint":
        result = _controller.submit_hint(color, msg["word"], msg["count"])
    elif mtype == "reveal_tile":
        result = _controller.reveal_tile(color, msg["word"])
    elif mtype == "end_turn":
        result = _controller.end_turn(color)

    if result and result.get("ok"):
        state = result["state"]
        _broadcast({"type": "state_update", "state": state})
        if _server_on_state_update:
            _server_on_state_update(state)
        if state.get("round_over") and not state.get("game_over"):
            threading.Timer(5.0, _start_new_round).start()


def _client_thread(conn: socket.socket, role: str, color: str):
    global _controller
    _send(conn, {"type": "login", "role": role, "color": color})

    with _clients_lock:
        _clients.append((conn, role, color))
        count = len(_clients)

    if count == 3:  # alle 3 Clients verbunden → Spiel startet
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
                    _handle_action(color, json.loads(line))
    except OSError:
        pass
    finally:
        conn.close()
        with _clients_lock:
            _clients[:] = [(c, r, col) for c, r, col in _clients if c is not conn]


# ── Public API ────────────────────────────────────────────────────────────────

def run_server(on_game_start=None, on_state_update=None, on_role_update=None) -> tuple[str, str, callable]:
    """
    Startet den Server, nimmt 3 Clients an und gibt (role, color, send_fn) zurück.
    send_fn(msg) schickt eine Spielaktion des Server-Spielers direkt an den Controller.
    on_state_update(state) wird aufgerufen, wenn sich der Spielzustand ändert.
    on_role_update(role, color) wird aufgerufen, wenn die Rolle des Server-Spielers wechselt.
    """
    global _server_on_state_update, _server_on_role_update, _server_role, _server_color
    _server_on_state_update = on_state_update
    _server_on_role_update  = on_role_update

    assignments = assign_role_color()
    server_role, server_color = assignments['server']
    _server_role  = server_role
    _server_color = server_color

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

    def send_fn(msg: dict):
        _handle_action(server_color, msg)

    return server_role, server_color, send_fn


def run_client(server_ip: str, on_game_start=None, on_state_update=None, on_role_update=None) -> tuple[str, str, callable]:
    """
    Verbindet mit dem Server und gibt (role, color, send_fn) zurück.
    send_fn(msg) sendet eine Spielaktion an den Server.
    on_state_update(state) wird aufgerufen, wenn der Server einen neuen Zustand schickt.
    on_role_update(role, color) wird aufgerufen, wenn die Rolle des Spielers wechselt.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, PORT))

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
                    if m["type"] == "game_start" and on_game_start:
                        on_game_start(m["state"])
                    elif m["type"] == "state_update" and on_state_update:
                        on_state_update(m["state"])
                    elif m["type"] == "role_update" and on_role_update:
                        on_role_update(m["role"], m["color"])
            except OSError:
                break

    threading.Thread(target=_listen, daemon=True).start()

    def send_fn(msg: dict):
        client.sendall((json.dumps(msg) + "\n").encode())

    return role, color, send_fn


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from ui import CodenamesUI

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        ui = CodenamesUI()

        def _server():
            role, color, send_fn = run_server(
                on_game_start=lambda state: ui.root.after(0, ui.show_game_from_state, state),
                on_state_update=lambda state: ui.root.after(0, ui.show_game_from_state, state),
                on_role_update=lambda r, _: ui.root.after(0, lambda: ui.update_role(r)),
            )
            ui.on_submit_hint = lambda word, count: send_fn({"type": "submit_hint", "word": word, "count": count})
            ui.on_tile_click  = lambda word: send_fn({"type": "reveal_tile", "word": word})
            ui.on_end_turn    = lambda: send_fn({"type": "end_turn"})
            ui.root.after(0, ui.show_role, role, color)

        threading.Thread(target=_server, daemon=True).start()
        ui.run()
    else:
        ui = CodenamesUI()

        def _start_client(ip: str):
            def _client():
                role, color, send_fn = run_client(
                    ip,
                    on_game_start=lambda state: ui.root.after(0, ui.show_game_from_state, state),
                    on_state_update=lambda state: ui.root.after(0, ui.show_game_from_state, state),
                    on_role_update=lambda r, _: ui.root.after(0, lambda: ui.update_role(r)),
                )
                ui.on_submit_hint = lambda word, count: send_fn({"type": "submit_hint", "word": word, "count": count})
                ui.on_tile_click  = lambda word: send_fn({"type": "reveal_tile", "word": word})
                ui.on_end_turn    = lambda: send_fn({"type": "end_turn"})
                ui.root.after(0, ui.show_role, role, color)

            threading.Thread(target=_client, daemon=True).start()

        ui.root.after(0, lambda: ui.show_ip_dialog(_start_client))
        ui.run()
