#python
import tkinter as tk
from tkinter import simpledialog, messagebox
import subprocess
import sys

class CodenamesUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Codenames")
        self.is_host = False
        self.server_proc = None
        self.client_proc = None
        self.setup_start_screen()

    def setup_start_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        tk.Label(self.root, text="Codenames", font=("Arial", 18)).pack(pady=10)
        tk.Button(self.root, text="Host", width=20, command=self.start_host).pack(pady=5)
        tk.Button(self.root, text="Client", width=20, command=self.start_client).pack(pady=5)

    def start_host(self):
        self.is_host = True
        # Start main.py as server (non-blocking)
        self.server_proc = subprocess.Popen([sys.executable, "main.py", "server"])
        self.show_lobby()

    def start_client(self):
        self.is_host = False
        server_ip = simpledialog.askstring("Server IP", "Enter server IP:")
        if not server_ip:
            return
        # Start main.py as client (non-blocking)
        self.client_proc = subprocess.Popen([sys.executable, "main.py"], stdin=subprocess.PIPE)
        self.client_proc.stdin.write((server_ip + "\n").encode())
        self.client_proc.stdin.flush()
        self.show_lobby()

    def show_lobby(self):
        lobby = tk.Toplevel(self.root)
        lobby.title("Lobby")
        tk.Label(lobby, text="Waiting for 4 players...", font=("Arial", 14)).pack(pady=10)
        if self.is_host:
            tk.Button(lobby, text="Start Game", command=lambda: [lobby.destroy(), self.show_game_grid()]).pack(pady=10)

    def show_game_grid(self):
        # Dummy data, replace with real data from controller.py
        words = [f"Word{i+1}" for i in range(25)]
        colors = ['red']*8 + ['blue']*8 + ['white']*8 + ['black']
        import random
        random.shuffle(words)
        random.shuffle(colors)
        grid = tk.Toplevel(self.root)
        grid.title("Codenames Game")
        for i in range(5):
            for j in range(5):
                idx = i*5 + j
                word = words[idx]
                color = colors[idx]
                bg = {"red": "#ffcccc", "blue": "#ccccff", "white": "#f8f8f8", "black": "#222222"}[color]
                fg = "black" if color != "black" else "white"
                tk.Label(grid, text=word, width=12, height=3, borderwidth=2, relief="groove", bg=bg, fg=fg).grid(row=i, column=j, padx=2, pady=2)

    def run(self):
        self.root.mainloop()

def StartingScreenUI(role: str, color: str):
    BG        = "#0f1923"
    FG_LIGHT  = "#f1faee"
    FG_MUTED  = "#8d99ae"
    TEAM_CLR  = "#e63946" if color.lower() == "red" else "#457b9d"
    TEAM_NAME = "Rot"     if color.lower() == "red" else "Blau"
    ROLE_NAME = "Spymaster" if role.lower() == "instructor" else "Agent"

    window = tk.Tk()
    window.title("Codenames")
    window.configure(bg=BG)
    window.resizable(False, False)

    W, H = 460, 300
    window.update_idletasks()
    sx = (window.winfo_screenwidth()  - W) // 2
    sy = (window.winfo_screenheight() - H) // 2
    window.geometry(f"{W}x{H}+{sx}+{sy}")

    tk.Label(window, text="CODENAMES",
             font=("Helvetica Neue", 30, "bold"),
             fg=FG_LIGHT, bg=BG).pack(pady=(38, 6))

    tk.Frame(window, height=2, width=220, bg=TEAM_CLR).pack()

    tk.Label(window, text=f"Team {TEAM_NAME}",
             font=("Helvetica Neue", 13),
             fg=TEAM_CLR, bg=BG).pack(pady=(18, 2))

    tk.Label(window, text=ROLE_NAME,
             font=("Helvetica Neue", 22, "bold"),
             fg=FG_LIGHT, bg=BG).pack(pady=(0, 6))

    tk.Label(window, text="Viel Erfolg!",
             font=("Helvetica Neue", 11),
             fg=FG_MUTED, bg=BG).pack(pady=(0, 24))

    btn = tk.Button(
        window, text="Weiter →",
        font=("Helvetica Neue", 12, "bold"),
        fg=FG_LIGHT, bg=TEAM_CLR,
        activeforeground=FG_LIGHT, activebackground=TEAM_CLR,
        relief="flat", padx=22, pady=9,
        cursor="hand2", command=window.destroy,
    )
    btn.pack()

    window.mainloop()

if __name__ == "__main__":
    ui = CodenamesUI()
    ui.run()