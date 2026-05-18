import tkinter as tk

BG       = "#0f1923"
FG_LIGHT = "#f1faee"
FG_MUTED = "#8d99ae"
RED_CLR  = "#e63946"
BLUE_CLR = "#457b9d"


class CodenamesUI:
    def __init__(self, role: str, color: str):
        self.role  = role
        self.color = color
        self.root  = tk.Tk()
        self.root.title("Codenames")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self._show_role()

    # ── helpers ────────────────────────────────────────────────────────────

    def _center(self, w: int, h: int):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _btn(self, text, color, command):
        return tk.Button(
            self.root, text=text,
            font=("Helvetica Neue", 12, "bold"),
            fg=FG_LIGHT, bg=color,
            activeforeground=FG_LIGHT, activebackground=color,
            relief="flat", padx=28, pady=9, cursor="hand2",
            command=command,
        )

    # ── screens ────────────────────────────────────────────────────────────

    def _show_role(self):
        self._clear()
        self._center(460, 300)

        team_clr  = RED_CLR  if self.color.lower() == "red"        else BLUE_CLR
        team_name = "Rot"    if self.color.lower() == "red"        else "Blau"
        role_name = "Spymaster" if self.role.lower() == "instructor" else "Agent"

        tk.Label(self.root, text="CODENAMES",
                 font=("Helvetica Neue", 30, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(38, 6))
        tk.Frame(self.root, height=2, width=220, bg=team_clr).pack()
        tk.Label(self.root, text=f"Team {team_name}",
                 font=("Helvetica Neue", 13), fg=team_clr, bg=BG).pack(pady=(18, 2))
        tk.Label(self.root, text=role_name,
                 font=("Helvetica Neue", 22, "bold"),
                 fg=FG_LIGHT, bg=BG).pack(pady=(0, 6))
        tk.Label(self.root, text="Viel Erfolg!",
                 font=("Helvetica Neue", 11), fg=FG_MUTED, bg=BG).pack(pady=(0, 24))
        self._btn("Weiter →", team_clr, self._show_game).pack()

    def _show_game(self):
        from controller import assign_colors_to_words
        assignments = assign_colors_to_words()
        words  = list(assignments.keys())
        colors = list(assignments.values())

        self._clear()
        self._center(700, 500)

        color_map = {
            "red":   (RED_CLR,  FG_LIGHT),
            "blue":  (BLUE_CLR, FG_LIGHT),
            "white": ("#dde1e7", "#0f1923"),
            "black": ("#1c1c1e", FG_LIGHT),
        }
        for i in range(5):
            for j in range(5):
                idx    = i * 5 + j
                bg, fg = color_map[colors[idx]]
                tk.Label(
                    self.root, text=words[idx],
                    font=("Helvetica Neue", 12, "bold"),
                    width=12, height=3,
                    bg=bg, fg=fg, relief="flat",
                ).grid(row=i, column=j, padx=4, pady=4)

    # ── entry point ────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
