from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import re

BG         = "#090b0f"
FG_LIGHT   = "#e8dcc8"
FG_MUTED   = "#7a7060"
RED_CLR    = "#c0392b"
BLUE_CLR   = "#2060a0"
HIDDEN_CLR = "#1e2530"
BAR_BG     = "#060810"
GOLD       = "#c9a84c"
DIM_MAP    = {
    "red":   ("#6e1515", "#a05050"),
    "blue":  ("#142040", "#4a7090"),
    "white": ("#505558", "#909498"),
    "black": ("#0d0d10", "#4a4a55"),
}

_tagger = None

def _get_tagger():
    global _tagger
    if _tagger is None:
        try:
            from HanTa import HanoverTagger as ht
            _tagger = ht.HanoverTagger('morphmodel_ger.pgz')
        except ImportError:
            print("[HanTa] nicht installiert – bitte: pip install HanTa")
        except Exception as e:
            print(f"[HanTa] Fehler beim Laden: {e}")
    return _tagger

def _normalize(w: str) -> str:
    """Lowercase + keep only German letters (including umlauts)."""
    return re.sub(r'[^a-zäöüß]', '', w.lower())

def _flatten(w: str) -> str:
    """Like _normalize but also converts umlauts to base vowels for fuzzy compound matching."""
    s = _normalize(w)
    return s.replace('ä', 'a').replace('ö', 'o').replace('ü', 'u').replace('ß', 'ss')

def _get_stem(w: str) -> str:
    """Entfernt gängige deutsche Präfixe und Suffixe für einen groben Wortfamilien-Abgleich."""
    w = _flatten(w)
    
    prefixes = ['ge', 'be', 'ver', 'zer', 'ent', 'emp', 'er', 'ur', 'miss', 
                'auf', 'ab', 'an', 'zu', 'ein', 'aus', 'vor', 'nach', 'mit', 'um', 'durch', 'uber', 'unter']
    
    for _ in range(2):
        for pref in prefixes:
            if w.startswith(pref) and len(w) > len(pref) + 2:
                w = w[len(pref):]
                break
                
    suffixes = ['innen', 'ium', 'ung', 'heit', 'keit', 'schaft', 'lein', 'chen', 
                'lich', 'isch', 'haft', 'itat', 'ismus', 'enz', 'anz', 'nis',
                'ent', 'ant', 'ist', 'ial', 'sam', 'bar', 'tum',
                'en', 'er', 'ig', 'al', 'ie', 'ik', 'ion', 'or', 'ur', 'in', 'um',
                'es', 'st', 'nd', 'e', 's', 'n', 't']
    
    suffixes.sort(key=len, reverse=True)
    
    for _ in range(2):
        for suff in suffixes:
            if w.endswith(suff) and len(w) > len(suff) + 2:
                w = w[:-len(suff)]
                break
                
    return w



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
        self._current_state: dict | None = None
        self._resize_after = None

        self.root.bind('<Configure>', self._on_configure)

        if role and color:
            self.show_role(role, color)
        else:
            self._show_waiting()

    def update_role(self, role: str):
        self.role = role
        if self._current_state is not None:
            self._build_game_ui(self._current_state)

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

        if ' ' in hint:
            return False, "Hinweis darf nur ein Wort sein"

        hint_words = hint.split()
        tagger     = _get_tagger()
        _vowels    = set('aeiouäöüAEIOUÄÖÜ')

        for word in hint_words:
            # ── Basis-Plausibilitätsprüfung ────────────────────────────────
            if not re.match(r'^[a-zA-ZäöüÄÖÜß]+$', word):
                return False, f"'{word}' enthält ungültige Zeichen"
            if len(word) < 2:
                return False, f"'{word}' ist zu kurz"
            if not any(c in _vowels for c in word):
                return False, f"'{word}' enthält keine Vokale"
            if sum(1 for c in word if c in _vowels) / len(word) < 0.10:
                return False, f"'{word}' sieht nicht wie ein deutsches Wort aus"
            if re.search(r'(.)\1{3,}', word, re.IGNORECASE):
                return False, f"'{word}' enthält zu viele gleiche Zeichen"

            # ── POS-Check via HanTa ────────────────────────────────────────
            norm_lemma = _normalize(word)
            if tagger:
                try:
                    result = tagger.tag_word(word, taglevel=1)
                    if result:
                        norm_lemma = _normalize(result[0][1])
                        pos        = result[0][2]
                        if pos not in ("NN", "NE"):
                            return False, f"'{word}' ist kein deutsches Substantiv"
                except Exception:
                    pass
            else:
                if not word[0].isupper():
                    return False, "Alle Wörter müssen mit Großbuchstaben beginnen"

            # ── Spielfeld-Abgleich (Oberfläche + Lemma + Umlaut-geglättet) ──
            norm_hint  = _normalize(word)
            flat_hint  = _flatten(word)
            flat_lemma = _flatten(norm_lemma)

            for gw in grid_words:
                norm_gw = _normalize(gw)
                flat_gw = _flatten(gw)

                if norm_hint == norm_gw or norm_lemma == norm_gw:
                    return False, f"'{word}' ist ein Wort aus dem Spielfeld!"

                for h in (norm_hint, flat_hint, norm_lemma, flat_lemma):
                    for g in (norm_gw, flat_gw):
                        if g and g in h:
                            return False, f"'{word}' enthält das Spielfeldwort '{gw}'"

                for h in (norm_hint, flat_hint, norm_lemma, flat_lemma):
                    for g in (norm_gw, flat_gw):
                        if h and h in g:
                            return False, f"'{word}' ist Teil des Spielfeldworts '{gw}'"

                hint_stem = _get_stem(word)
                gw_stem = _get_stem(gw)
                if hint_stem and gw_stem:
                    if hint_stem == gw_stem or hint_stem in gw_stem or gw_stem in hint_stem:
                        return False, f"'{word}' gehört zur selben Wortfamilie wie '{gw}'"
                    
                    hint_cons = re.sub(r'[aeiou]', '', hint_stem)
                    gw_cons = re.sub(r'[aeiou]', '', gw_stem)
                    if hint_cons == gw_cons and len(hint_cons) >= 3:
                        return False, f"'{word}' ähnelt '{gw}' zu stark (gleiche Konsonanten)"

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

    def _on_configure(self, event):
        if event.widget is self.root and self._current_state is not None:
            if self._resize_after is not None:
                self.root.after_cancel(self._resize_after)
            self._resize_after = self.root.after(
                120, lambda: self._build_game_ui(self._current_state)
            )

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
        self._current_state = state
        self._build_game_ui(state)

    def _build_game_ui(self, state: dict):
        self._clear()

        active_team  = state["active_team"]
        hint         = state["current_hint"]
        guesses      = state["guesses_remaining"]
        revealed_set = set(state.get("revealed", []))
        round_over   = state.get("round_over", False)

        is_agent        = self.role and self.role.lower() == "agent"
        is_instructor   = self.role and self.role.lower() == "instructor"
        is_active_agent = (is_agent and
                           self.color and
                           self.color.lower() == active_team.lower() and
                           not round_over)
        can_guess       = is_active_agent and hint is not None and (guesses > 0 or guesses == -1)
        is_active_instructor = (
            is_instructor and
            self.color and self.color.lower() == active_team.lower() and
            hint is None and not round_over
        )

        # ── score bar ──────────────────────────────────────────────────────
        self._build_score_bar(state, active_team)

        # ── round over banner ──────────────────────────────────────────────
        if round_over:
            self._build_round_over_banner(state)

        # ── calculate tile size from available window space ─────────────────
        self.root.update_idletasks()
        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()
        if win_w < 100:   # window not yet measured (first paint)
            win_w = self.root.winfo_screenwidth()
            win_h = self.root.winfo_screenheight()

        bar_h      = 54
        ctrl_h     = 60 if is_agent else 0
        panel_w    = 280 if is_instructor else 0
        gap        = 48 if is_instructor else 0
        h_padding  = 48
        v_padding  = 40

        avail_w = win_w - panel_w - gap - h_padding
        avail_h = win_h - bar_h - ctrl_h - v_padding

        tile_w   = max(120, int(avail_w / 5 * 0.91))
        tile_h   = max(55,  int(avail_h / 5 * 0.75))
        tile_pad = max(3, tile_h // 20)
        font_sz  = max(8, tile_h // 7)

        # ── main area ──────────────────────────────────────────────────────
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True)

        content = tk.Frame(main, bg=BG)
        content.place(relx=0.5, rely=0.5, anchor="center")

        grid_side = tk.Frame(content, bg=BG)
        grid_side.pack(side=tk.LEFT)

        # colored border when this player is the active agent
        border_clr = self._team_color(self.color) if is_active_agent else BG
        border = tk.Frame(grid_side, bg=border_clr, padx=5, pady=5)
        border.pack()

        grid_inner = tk.Frame(border, bg=BG)
        grid_inner.pack()

        # choose board data
        board = state["board_full"] if is_instructor else state["board_agents"]
        self._grid_words = list(board.keys())

        color_map = {
            "red":   (RED_CLR,    FG_LIGHT),
            "blue":  (BLUE_CLR,   FG_LIGHT),
            "white": ("#b8b0a4",  "#1a1610"),
            "black": ("#0d0d10",  GOLD),
            None:    (HIDDEN_CLR, FG_MUTED),
        }

        words  = list(board.keys())
        colors = list(board.values())

        for i in range(5):
            for j in range(5):
                idx          = i * 5 + j
                word         = words[idx]
                col          = colors[idx]
                bg, fg       = color_map.get(col, color_map[None])
                is_unrevealed = col is None

                # pixel-sized container so tiles scale with the window
                cell = tk.Frame(grid_inner, width=tile_w, height=tile_h, bg=bg)
                cell.grid(row=i, column=j, padx=tile_pad, pady=tile_pad)
                cell.pack_propagate(False)

                if is_instructor and word in revealed_set:
                    dim_bg, dim_fg = DIM_MAP.get(col, (bg, FG_MUTED))
                    tk.Label(
                        cell, text=f"{word}  ✓",
                        font=("Helvetica Neue", font_sz, "bold"),
                        bg=dim_bg, fg=dim_fg, relief="flat",
                    ).pack(fill=tk.BOTH, expand=True)
                elif can_guess and is_unrevealed:
                    tk.Button(
                        cell, text=word,
                        font=("Helvetica Neue", font_sz, "bold"),
                        bg=HIDDEN_CLR, fg=FG_LIGHT,
                        activebackground="#2a3d52",
                        activeforeground=FG_LIGHT,
                        relief="flat", cursor="hand2",
                        command=lambda w=word: self._tile_clicked(w),
                    ).pack(fill=tk.BOTH, expand=True)
                else:
                    tk.Label(
                        cell, text=word,
                        font=("Helvetica Neue", font_sz, "bold"),
                        bg=bg, fg=fg, relief="flat",
                    ).pack(fill=tk.BOTH, expand=True)

        # hint display + "Zug beenden" below grid (agents only)
        if is_agent:
            self._build_agent_controls(grid_side, state, active_team, can_guess)

        # instructor hint form (right panel)
        if is_instructor:
            panel_frame = tk.Frame(content, bg=BG)
            panel_frame.pack(side=tk.LEFT, anchor=tk.N, padx=(40, 0))
            self._build_instructor_panel(panel_frame, is_active_instructor)

    # ── sub-builders ───────────────────────────────────────────────────────

    def _build_round_over_banner(self, state: dict):
        winner    = state.get("winner", "")
        reason    = state.get("end_reason", "")
        team_clr  = self._team_color(winner) if winner else FG_MUTED
        team_name = "Rot" if winner and winner.lower() == "red" else "Blau"

        if reason == "assassin":
            detail = "Die schwarze Karte wurde aufgedeckt!"
        else:
            detail = "Alle eigenen Karten gefunden!"

        banner = tk.Frame(self.root, bg=team_clr, pady=10)
        banner.pack(fill=tk.X)
        tk.Label(banner,
                 text=f"Team {team_name} gewinnt die Runde!  —  {detail}",
                 font=("Helvetica Neue", 15, "bold"),
                 fg=FG_LIGHT, bg=team_clr).pack()
        tk.Label(banner,
                 text="Neue Runde startet in 5 Sekunden…",
                 font=("Helvetica Neue", 11),
                 fg=FG_LIGHT, bg=team_clr).pack()

    def _build_score_bar(self, state: dict, active_team: str):
        bar = tk.Frame(self.root, bg=BAR_BG, pady=10)
        bar.pack(side=tk.TOP, fill=tk.X)

        starting_team = state.get("starting_team", "")

        for i, (team, clr) in enumerate((("Red", RED_CLR), ("Blue", BLUE_CLR))):
            is_active  = team.lower() == active_team.lower()
            is_starter = team == starting_team
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
            if is_starter:
                tk.Label(panel, text="angefangen",
                         font=("Helvetica Neue", 9), fg=clr, bg=BAR_BG).pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(panel, text=f"Runden: {wins}",
                     font=("Helvetica Neue", 13),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=6)
            tk.Label(panel, text=f"Karten: {found}/{total}",
                     font=("Helvetica Neue", 13),
                     fg=label_fg, bg=BAR_BG).pack(side=tk.LEFT, padx=6)

            if i == 0:
                tk.Label(bar, text="▬ 007 ▬",
                         font=("Helvetica Neue", 16, "bold"),
                         fg=GOLD, bg=BAR_BG).pack(side=tk.LEFT, padx=12)

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
        else:
            tk.Label(ctrl,
                     text="Warte auf Hinweis…",
                     font=("Helvetica Neue", 14), fg=FG_MUTED, bg=BG).pack(side=tk.LEFT, padx=(0, 24))

        if can_guess:
            _, hint_count  = hint
            tile_clicked   = guesses < hint_count + 1
            btn_bg         = FG_MUTED if tile_clicked else HIDDEN_CLR
            tk.Button(ctrl, text="Zug beenden",
                      font=("Helvetica Neue", 12, "bold"),
                      fg=FG_LIGHT, bg=btn_bg,
                      activeforeground=FG_LIGHT, activebackground=FG_MUTED,
                      relief="flat", padx=16, pady=6,
                      cursor="hand2" if tile_clicked else "arrow",
                      state=tk.NORMAL if tile_clicked else tk.DISABLED,
                      command=self._end_turn_clicked).pack(side=tk.LEFT)

    def _build_instructor_panel(self, parent, is_active: bool):
        panel = parent

        tk.Label(panel, text="Hinweis geben",
                 font=("Helvetica Neue", 18, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 16))

        

        tk.Label(panel, text="Hinweis (Substantive):",
                 font=("Helvetica Neue", 12), fg=FG_LIGHT, bg=BG).pack(anchor=tk.W, pady=(0, 4))
        text_var   = tk.StringVar()
        text_input = tk.Entry(panel, textvariable=text_var,
                              font=("Helvetica Neue", 12), width=20,
                              bg="#0f1420", fg=FG_LIGHT, insertbackground=FG_LIGHT,
                              state=tk.NORMAL if is_active else tk.DISABLED)
        text_input.pack(anchor=tk.W, pady=(0, 16))

        tk.Label(panel, text="Anzahl:",
                 font=("Helvetica Neue", 12), fg=FG_LIGHT, bg=BG).pack(anchor=tk.W, pady=(0, 4))
        number_var   = tk.StringVar()
        only_digits  = (self.root.register(lambda P: P == "" or P.isdigit()), "%P")
        number_input = tk.Entry(panel, textvariable=number_var,
                                font=("Helvetica Neue", 12), width=20,
                                bg="#0f1420", fg=FG_LIGHT, insertbackground=FG_LIGHT,
                                validate="key", validatecommand=only_digits,
                                state=tk.NORMAL if is_active else tk.DISABLED)
        number_input.pack(anchor=tk.W, pady=(0, 16))

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
