from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import re

BG         = "#0f1923"
FG_LIGHT   = "#f1faee"
FG_MUTED   = "#8d99ae"
RED_CLR    = "#e63946"
BLUE_CLR   = "#457b9d"
HIDDEN_CLR = "#2e3a47"   # verdeckte Kachel (Agenten-Ansicht)
BAR_BG     = "#0d1520"   # Hintergrund der Score-Leiste


class CodenamesUI:
    def __init__(self, role: str = None, color: str = None):
        self.root = tk.Tk()
        self.root.title("Codenames")
        self.root.configure(bg=BG)
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda _: self.root.attributes('-fullscreen', False))

        self.role  = role
        self.color = color

        # Callbacks – werden von main.py gesetzt, sobald das Spiel läuft
        self.on_tile_click:   callable | None = None   # fn(word)
        self.on_end_turn:     callable | None = None   # fn()
        self.on_submit_hint:  callable | None = None   # fn(word, count)

        self._grid_words: list[str] = []

        if role and color:
            self.show_role(role, color)
        else:
            self._show_waiting()

    # ── helpers ────────────────────────────────────────────────────────────

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def _center_frame(self) -> tk.Frame:
        outer = tk.Frame(self.root, bg=BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")
        return outer

    def _team_color(self, team: str) -> str:
        return RED_CLR if team.lower() == "red" else BLUE_CLR

    # ── hint validation ────────────────────────────────────────────────────

    def _is_valid_hint(self, hint: str, grid_words: list) -> tuple[bool, str]:
        hint = hint.strip()
        if not hint:
            return False, "Hinweis darf nicht leer sein"

        hint_words = hint.split()
        for word in hint_words:
            if not word[0].isupper():
                return False, "Alle Wörter müssen mit Großbuchstaben beginnen (Substantive)"

        def normalize(w):
            return re.sub(r'[^a-zäöü]', '', w.lower())

        norm_grid  = [normalize(w) for w in grid_words]
        norm_hints = [normalize(w) for w in hint_words]

        for hw in norm_hints:
            if hw in norm_grid:
                return False, f"'{hw}' ist ein Wort aus dem Spielfeld!"
        for hw in norm_hints:
            for gw in norm_grid:
                if gw in hw or hw in gw:
                    return False, f"'{hw}' enthält Teile von Wörtern aus dem Spielfeld"
        return True, ""

    def _send_hint(self, number_var, text_var, number_input, text_input):
        try:
            count = int(number_var.get())
            if count < 1:
                messagebox.showerror("Fehler", "Die Zahl muss mindestens 1 sein")
                return
        except ValueError:
            messagebox.showerror("Fehler", "Bitte eine gültige Zahl eingeben")
            return

        word = text_var.get().strip()
        valid, err = self._is_valid_hint(word, self._grid_words)
        if not valid:
            messagebox.showerror("Ungültiger Hinweis", err)
            return

        if self.on_submit_hint:
            self.on_submit_hint(word, count)
        else:
            # TODO: Netzwerkverbindung herstellen (on_submit_hint setzen)
            print(f"Hinweis: {word} ({count})")

        number_input.delete(0, tk.END)
        text_input.delete(0, tk.END)

    def _tile_clicked(self, word: str):
        if self.on_tile_click:
            self.on_tile_click(word)

    def _end_turn_clicked(self):
        if self.on_end_turn:
            self.on_end_turn()

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

        team_clr  = self._team_color(color)
        team_name = "Rot"       if color.lower() == "red"        else "Blau"
        role_name = "Spymaster" if role.lower()  == "instructor" else "Agent"

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
        # Kein "Weiter"-Button – das Spiel startet automatisch wenn alle 4 Spieler da sind
        tk.Label(f, text="Warte auf andere Spieler…",
                 font=("Helvetica Neue", 14), fg=FG_MUTED, bg=BG).pack()

    def show_game_from_state(self, state: dict):
        """
        Rendert das komplette Spielfeld aus dem Server-Zustand.

        Instruktoren: alle Kachelfarben sichtbar + Hinweis-Formular.
        Agenten:      nur aufgedeckte Farben; eigene Kacheln anklickbar wenn dran.

        UI-Anbindung:
          - Wird automatisch via on_game_start ausgelöst (kein manueller Aufruf).
          - Bei jedem State-Update (reveal_tile, end_turn …) erneut aufrufen.
          - Callbacks vor dem ersten Aufruf setzen:
              ui.on_tile_click  = lambda word: …
              ui.on_end_turn    = lambda: …
              ui.on_submit_hint = lambda word, count: …
        """
        self._clear()

        active_team = state["active_team"]        # "Red" | "Blue"
        hint        = state["current_hint"]        # (word, count) | None
        guesses     = state["guesses_remaining"]

        is_agent        = self.role and self.role.lower() == "agent"
        is_active_agent = (is_agent and
                           self.color and
                           self.color.lower() == active_team.lower() and
                           not state["round_over"])
        can_guess       = is_active_agent and hint is not None and guesses > 0

        # ── score bar ──────────────────────────────────────────────────────
        self._build_score_bar(state, active_team)

        # ── main area ──────────────────────────────────────────────────────
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # grid side (left)
        grid_side = tk.Frame(main, bg=BG)
        grid_side.pack(side=tk.LEFT, anchor=tk.N)

        # colored border when this player is the active agent
        border_clr = self._team_color(self.color) if is_active_agent else BG
        border = tk.Frame(grid_side, bg=border_clr, padx=5, pady=5)
        border.pack()

        grid_inner = tk.Frame(border, bg=BG)
        grid_inner.pack()

        # choose board data
        if self.role and self.role.lower() == "instructor":
            board = state["board_full"]
        else:
            board = state["board_agents"]

        self._grid_words = list(board.keys())

        color_map = {
            "red":   (RED_CLR,    FG_LIGHT),
            "blue":  (BLUE_CLR,   FG_LIGHT),
            "white": ("#dde1e7",  "#0f1923"),
            "black": ("#1c1c1e",  FG_LIGHT),
            None:    (HIDDEN_CLR, FG_MUTED),
        }

        words  = list(board.keys())
        colors = list(board.values())

        for i in range(5):
            for j in range(5):
                idx   = i * 5 + j
                word  = words[idx]
                col   = colors[idx]
                bg, fg = color_map.get(col, color_map[None])
                is_unrevealed = col is None   # only possible in board_agents

                if can_guess and is_unrevealed:
                    # clickable button for the active agent
                    tk.Button(
                        grid_inner, text=word,
                        font=("Helvetica Neue", 13, "bold"),
                        width=14, height=4,
                        bg=HIDDEN_CLR, fg=FG_LIGHT,
                        activebackground="#3d5166",
                        activeforeground=FG_LIGHT,
                        relief="flat", cursor="hand2",
                        command=lambda w=word: self._tile_clicked(w),
                    ).grid(row=i, column=j, padx=5, pady=5)
                else:
                    tk.Label(
                        grid_inner, text=word,
                        font=("Helvetica Neue", 13, "bold"),
                        width=14, height=4,
                        bg=bg, fg=fg, relief="flat",
                    ).grid(row=i, column=j, padx=5, pady=5)

        # hint display + "Zug beenden" below grid (agents only)
        if is_agent:
            self._build_agent_controls(grid_side, state, active_team, can_guess)

        # instructor hint form (right panel)
        is_active_instructor = (
            self.role and self.role.lower() == "instructor" and
            self.color and self.color.lower() == active_team.lower() and
            hint is None and not state["round_over"]
        )
        if self.role and self.role.lower() == "instructor":
            self._build_instructor_panel(main, is_active_instructor)

    # ── sub-builders ───────────────────────────────────────────────────────

    def _build_score_bar(self, state: dict, active_team: str):
        bar = tk.Frame(self.root, bg=BAR_BG, pady=10)
        bar.pack(side=tk.TOP, fill=tk.X)

        for team, clr in (("Red", RED_CLR), ("Blue", BLUE_CLR)):
            is_active  = team.lower() == active_team.lower()
            name       = "ROT" if team == "Red" else "BLAU"
            wins       = state["red_wins"]   if team == "Red" else state["blue_wins"]
            found      = state["red_found"]  if team == "Red" else state["blue_found"]
            total      = state["red_total"]  if team == "Red" else state["blue_total"]
            label_fg   = clr if is_active else FG_MUTED
            indicator  = "▶ " if is_active else "   "

            panel = tk.Frame(bar, bg=BAR_BG)
            panel.pack(side=tk.LEFT, expand=True)

            tk.Label(panel, text=f"{indicator}{name}",
                     font=("Helvetica Neue", 15, "bold"),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=(12, 6))
            tk.Label(panel, text=f"Runden: {wins}",
                     font=("Helvetica Neue", 13),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=6)
            tk.Label(panel, text=f"Karten: {found}/{total}",
                     font=("Helvetica Neue", 13),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=6)

    def _build_agent_controls(self, parent, state: dict, active_team: str, can_guess: bool):
        hint    = state["current_hint"]
        guesses = state["guesses_remaining"]

        ctrl = tk.Frame(parent, bg=BG)
        ctrl.pack(pady=(12, 0))

        if hint is not None:
            word, count = hint
            tk.Label(ctrl,
                     text=f'Hinweis: "{word}"  ({count})',
                     font=("Helvetica Neue", 16, "bold"),
                     fg=self._team_color(active_team), bg=BG).pack(side=tk.LEFT, padx=(0, 24))
            tk.Label(ctrl,
                     text=f"Versuche: {guesses}",
                     font=("Helvetica Neue", 14),
                     fg=FG_MUTED, bg=BG).pack(side=tk.LEFT, padx=(0, 24))
        else:
            tk.Label(ctrl,
                     text="Warte auf Hinweis…",
                     font=("Helvetica Neue", 14), fg=FG_MUTED, bg=BG).pack(side=tk.LEFT, padx=(0, 24))

        if can_guess:
            tk.Button(ctrl, text="Zug beenden",
                      font=("Helvetica Neue", 12, "bold"),
                      fg=FG_LIGHT, bg=FG_MUTED,
                      activeforeground=FG_LIGHT, activebackground=FG_MUTED,
                      relief="flat", padx=16, pady=6, cursor="hand2",
                      command=self._end_turn_clicked).pack(side=tk.LEFT)

    def _build_instructor_panel(self, parent, is_active: bool):
        panel = tk.Frame(parent, bg=BG)
        panel.pack(side=tk.RIGHT, anchor=tk.N, padx=(40, 0))

        tk.Label(panel, text="Hinweis geben",
                 font=("Helvetica Neue", 18, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 16))

        tk.Label(panel, text="Anzahl:",
                 font=("Helvetica Neue", 12), fg=FG_LIGHT, bg=BG).pack(anchor=tk.W, pady=(0, 4))
        number_var   = tk.StringVar()
        number_input = tk.Entry(panel, textvariable=number_var,
                                font=("Helvetica Neue", 12), width=20,
                                bg="#1c2333", fg=FG_LIGHT, insertbackground=FG_LIGHT,
                                state=tk.NORMAL if is_active else tk.DISABLED)
        number_input.pack(anchor=tk.W, pady=(0, 16))

        tk.Label(panel, text="Hinweis (Substantive):",
                 font=("Helvetica Neue", 12), fg=FG_LIGHT, bg=BG).pack(anchor=tk.W, pady=(0, 4))
        text_var   = tk.StringVar()
        text_input = tk.Entry(panel, textvariable=text_var,
                              font=("Helvetica Neue", 12), width=20,
                              bg="#1c2333", fg=FG_LIGHT, insertbackground=FG_LIGHT,
                              state=tk.NORMAL if is_active else tk.DISABLED)
        text_input.pack(anchor=tk.W, pady=(0, 16))

        team_clr = self._team_color(self.color) if self.color else FG_MUTED
        tk.Button(panel, text="Hinweis senden",
                  font=("Helvetica Neue", 12, "bold"),
                  fg=FG_LIGHT, bg=team_clr if is_active else FG_MUTED,
                  activeforeground=FG_LIGHT, activebackground=team_clr,
                  relief="flat", padx=16, pady=8, cursor="hand2" if is_active else "arrow",
                  state=tk.NORMAL if is_active else tk.DISABLED,
                  command=lambda: self._send_hint(number_var, text_var, number_input, text_input),
                  ).pack(pady=(0, 12))

        tk.Label(panel,
                 text="Nur großgeschriebene Substantive.\nKeine Teile der Gitterwörter.",
                 font=("Helvetica Neue", 9), fg=FG_MUTED, bg=BG, justify=tk.LEFT).pack(anchor=tk.W)

        if not is_active:
            tk.Label(panel, text="Warte auf deinen Zug…",
                     font=("Helvetica Neue", 12), fg=FG_MUTED, bg=BG).pack(pady=(16, 0))

    # ── entry point ────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
