# Entspricht: python main.py  -> Client

import sys
import threading
from ui import CodenamesUI, ask_server_ip
import main

if __name__ == "__main__":
    # IP-Dialog zuerst öffnen; Vollbild erst danach, damit kein Verbindungsfehler entsteht
    server_ip = ask_server_ip()
    if server_ip is None:
        sys.exit(0)

    ui = CodenamesUI()

    def _client():
        role, color, send_fn = main.run_client(
            server_ip,
            on_game_start=lambda state: ui.root.after(0, ui.show_game_from_state, state),
            on_state_update=lambda state: ui.root.after(0, ui.show_game_from_state, state),
            on_role_update=lambda r, _: ui.root.after(0, lambda: ui.update_role(r)),
        )
        ui.on_submit_hint = lambda word, count: send_fn({"type": "submit_hint", "word": word, "count": count}) #instructor
        ui.on_tile_click  = lambda word: send_fn({"type": "reveal_tile", "word": word}) #agent
        ui.on_end_turn    = lambda: send_fn({"type": "end_turn"}) #agent
        ui.root.after(0, ui.show_role, role, color)

    threading.Thread(target=_client, daemon=True).start()
    ui.run()
