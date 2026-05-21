import tkinter as tk

BG         = "#0f1923"
FG_LIGHT   = "#f1faee"
FG_MUTED   = "#8d99ae"
RED_CLR    = "#e63946"
BLUE_CLR   = "#457b9d"
HIDDEN_CLR = "#2e3a47"  # verdeckte Kachel (Agenten-Ansicht)


class CodenamesUI:
    def __init__(self, role: str = None, color: str = None):
        self.root = tk.Tk()
        self.root.title("Codenames")
        self.root.configure(bg=BG)
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda _: self.root.attributes('-fullscreen', False))
        self.role  = role
        self.color = color
        if role and color:
            self.show_role(role, color)
        else:
            self._show_waiting()

    # ── helpers ────────────────────────────────────────────────────────────

    def _clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _center_frame(self) -> tk.Frame:
        outer = tk.Frame(self.root, bg=BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")
        return outer

    # ── screens ────────────────────────────────────────────────────────────

    def _show_waiting(self):
        self._clear()
        f = self._center_frame()
        tk.Label(f, text="CODENAMES",
                 font=("Helvetica Neue", 52, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 8))
        tk.Frame(f, height=3, width=320, bg=FG_MUTED).pack()
        tk.Label(f, text="Warte auf Spieler…",
                 font=("Helvetica Neue", 20), fg=FG_MUTED, bg=BG).pack(pady=(32, 0))

    def show_role(self, role: str, color: str):
        self.role  = role
        self.color = color
        self._clear()

        team_clr  = RED_CLR  if color.lower() == "red"        else BLUE_CLR
        team_name = "Rot"    if color.lower() == "red"        else "Blau"
        role_name = "Spymaster" if role.lower() == "instructor" else "Agent"

        f = self._center_frame()
        tk.Label(f, text="CODENAMES",
                 font=("Helvetica Neue", 52, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 8))
        tk.Frame(f, height=3, width=320, bg=team_clr).pack()
        tk.Label(f, text=f"Team {team_name}",
                 font=("Helvetica Neue", 18), fg=team_clr, bg=BG).pack(pady=(24, 4))
        tk.Label(f, text=role_name,
                 font=("Helvetica Neue", 36, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 8))
        tk.Label(f, text="Viel Erfolg!",
                 font=("Helvetica Neue", 14), fg=FG_MUTED, bg=BG).pack(pady=(0, 24))
        tk.Label(f, text="Warte auf andere Spieler…",
                 font=("Helvetica Neue", 14), fg=FG_MUTED, bg=BG).pack()

    def show_game_from_state(self, state: dict):
        """
        Rendert das Spielfeld aus dem Server-Zustand.
        Instruktoren sehen alle Farben; Agenten nur aufgedeckte Kacheln.

        UI-Anbindung:
          - Wird vom Server per game_start-Broadcast ausgelöst, nie manuell.
          - Auch bei späteren Zustandsupdates (reveal_tile etc.) wieder aufrufen.
        """
        self._clear()

        if self.role == "instructor":
            board = state["board_full"]    # word -> color (immer sichtbar)
        else:
            board = state["board_agents"]  # word -> color | None

        color_map = {
            "red":   (RED_CLR,    FG_LIGHT),
            "blue":  (BLUE_CLR,   FG_LIGHT),
            "white": ("#dde1e7",  "#0f1923"),
            "black": ("#1c1c1e",  FG_LIGHT),
            None:    (HIDDEN_CLR, FG_MUTED),  # verdeckt (nur Agenten)
        }

        words  = list(board.keys())
        colors = list(board.values())

        grid = tk.Frame(self.root, bg=BG)
        grid.place(relx=0.5, rely=0.5, anchor="center")

        for i in range(5):
            for j in range(5):
                idx    = i * 5 + j
                bg, fg = color_map.get(colors[idx], color_map[None])
                tk.Label(
                    grid, text=words[idx],
                    font=("Helvetica Neue", 13, "bold"),
                    width=14, height=4,
                    bg=bg, fg=fg, relief="flat",
                ).grid(row=i, column=j, padx=5, pady=5)

    # ── entry point ────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
