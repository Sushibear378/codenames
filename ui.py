import tkinter as tk
from tkinter import messagebox
import re

BG       = "#0f1923"
FG_LIGHT = "#f1faee"
FG_MUTED = "#8d99ae"
RED_CLR  = "#e63946"
BLUE_CLR = "#457b9d"


class CodenamesUI:
    def __init__(self, role: str = None, color: str = None):
        self.root = tk.Tk()
        self.root.title("Codenames")
        self.root.configure(bg=BG)
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda _: self.root.attributes('-fullscreen', False))
        
        self.role = role
        self.color = color
        self.grid_words = []  # Store grid words for validation
        
        if role and color:
            self.show_role(role, color)
        else:
            self._show_waiting()

    # ── helpers ────────────────────────────────────────────────────────────

    def _clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _center_frame(self) -> tk.Frame:
        """Returns a frame centered in the window."""
        outer = tk.Frame(self.root, bg=BG)
        outer.place(relx=0.5, rely=0.5, anchor="center")
        return outer

    def _btn(self, parent, text, color, command):
        return tk.Button(
            parent, text=text,
            font=("Helvetica Neue", 14, "bold"),
            fg=FG_LIGHT, bg=color,
            activeforeground=FG_LIGHT, activebackground=color,
            relief="flat", padx=32, pady=12, cursor="hand2",
            command=command,
        )

    def _is_valid_hint(self, hint: str, grid_words: list) -> tuple[bool, str]:
        """
        Validates the hint:
        1. Only connected nouns (uppercase words)
        2. No parts of grid words
        
        Returns: (is_valid, error_message)
        """
        hint = hint.strip()
        
        # Check if hint is empty
        if not hint:
            return False, "Hinweis darf nicht leer sein"
        
        # Split hint into words
        hint_words = hint.split()
        
        # Check if all words are uppercase (nouns in German)
        for word in hint_words:
            if not word[0].isupper():
                return False, "Alle Wörter müssen mit Großbuchstaben beginnen (Substantive)"
        
        # Normalize for comparison (remove special chars, lowercase)
        def normalize(word):
            return re.sub(r'[^a-zäöü]', '', word.lower())
        
        normalized_grid_words = [normalize(w) for w in grid_words]
        normalized_hint_words = [normalize(w) for w in hint_words]
        
        # Check if any hint word is a complete grid word
        for hint_word in normalized_hint_words:
            if hint_word in normalized_grid_words:
                return False, f"'{hint_word}' ist ein Wort aus dem Spielfeld!"
        
        # Check if any hint word contains a grid word or vice versa
        for hint_word in normalized_hint_words:
            for grid_word in normalized_grid_words:
                if grid_word in hint_word or hint_word in grid_word:
                    return False, f"'{hint_word}' enthält Teile von Wörtern aus dem Spielfeld"
        
        return True, ""

    def _send_hint(self, number_var, text_var, number_input, text_input):
        """Sends the hint to agents"""
        try:
            number = int(number_var.get())
            if number < 0:
                messagebox.showerror("Fehler", "Die Zahl muss positiv sein")
                return
        except ValueError:
            messagebox.showerror("Fehler", "Bitte geben Sie eine gültige Zahl ein")
            return
        
        hint_text = text_var.get()
        is_valid, error_msg = self._is_valid_hint(hint_text, self.grid_words)
        
        if not is_valid:
            messagebox.showerror("Ungültiger Hinweis", error_msg)
            return
        
        # TODO: Send hint to agents (implement network communication)
        print(f"Hinweis gesendet: {number} - {hint_text}")
        messagebox.showinfo("Erfolg", f"Hinweis gesendet: {number} - {hint_text}")
        
        # Clear inputs
        number_input.delete(0, tk.END)
        text_input.delete(0, tk.END)

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
        self._clear()

        team_clr  = RED_CLR     if color.lower() == "red"        else BLUE_CLR
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
                 font=("Helvetica Neue", 14), fg=FG_MUTED, bg=BG).pack(pady=(0, 36))
        self._btn(f, "Weiter →", team_clr, self._show_game).pack()

    def _show_game(self):
        from controller import assign_colors_to_words
        assignments = assign_colors_to_words()
        words  = list(assignments.keys())
        colors = list(assignments.values())
        
        # Store grid words for hint validation
        self.grid_words = words

        self._clear()

        color_map = {
            "red":   (RED_CLR,  FG_LIGHT),
            "blue":  (BLUE_CLR, FG_LIGHT),
            "white": ("#dde1e7", "#0f1923"),
            "black": ("#1c1c1e", FG_LIGHT),
        }

        # Main container with grid on left and controls on right
        main_frame = tk.Frame(self.root, bg=BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Grid frame (left side)
        grid_frame = tk.Frame(main_frame, bg=BG)
        grid_frame.pack(side=tk.LEFT, padx=(0, 40))

        for i in range(5):
            for j in range(5):
                idx    = i * 5 + j
                bg, fg = color_map[colors[idx]]
                tk.Label(
                    grid_frame, text=words[idx],
                    font=("Helvetica Neue", 13, "bold"),
                    width=14, height=4,
                    bg=bg, fg=fg, relief="flat",
                ).grid(row=i, column=j, padx=5, pady=5)

        # Spymaster controls (right side, only for instructors)
        if self.role and self.role.lower() == "instructor":
            controls_frame = tk.Frame(main_frame, bg=BG)
            controls_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

            tk.Label(
                controls_frame, text="Hinweis geben",
                font=("Helvetica Neue", 18, "bold"),
                fg=FG_LIGHT, bg=BG
            ).pack(pady=(0, 20))

            # Number input
            tk.Label(
                controls_frame, text="Anzahl:",
                font=("Helvetica Neue", 12),
                fg=FG_LIGHT, bg=BG
            ).pack(anchor=tk.W, pady=(10, 5))

            number_var = tk.StringVar()
            number_input = tk.Entry(
                controls_frame,
                textvariable=number_var,
                font=("Helvetica Neue", 12),
                width=20,
                bg="#1c2333", fg=FG_LIGHT,
                insertbackground=FG_LIGHT
            )
            number_input.pack(anchor=tk.W, pady=(0, 20))

            # Text input
            tk.Label(
                controls_frame, text="Hinweis (Substantive):",
                font=("Helvetica Neue", 12),
                fg=FG_LIGHT, bg=BG
            ).pack(anchor=tk.W, pady=(10, 5))

            text_var = tk.StringVar()
            text_input = tk.Entry(
                controls_frame,
                textvariable=text_var,
                font=("Helvetica Neue", 12),
                width=20,
                bg="#1c2333", fg=FG_LIGHT,
                insertbackground=FG_LIGHT
            )
            text_input.pack(anchor=tk.W, pady=(0, 20))

            # Send button
            send_btn = tk.Button(
                controls_frame, text="Hinweis senden",
                font=("Helvetica Neue", 12, "bold"),
                fg=FG_LIGHT, bg=(RED_CLR if self.color.lower() == "red" else BLUE_CLR),
                activeforeground=FG_LIGHT,
                relief="flat", padx=16, pady=8, cursor="hand2",
                command=lambda: self._send_hint(number_var, text_var, number_input, text_input)
            )
            send_btn.pack(pady=(10, 0))

            # Info text
            tk.Label(
                controls_frame, text="Nur großgeschriebene\nSubstantive erlaubt.\nKeine Teile der Gitter-\nwörter.",
                font=("Helvetica Neue", 9),
                fg=FG_MUTED, bg=BG, justify=tk.LEFT
            ).pack(anchor=tk.W, pady=(20, 0))

    # ── entry point ────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()