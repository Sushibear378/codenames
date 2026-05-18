import tkinter as tk
from words import woerter
import random

MainWords = woerter

def SpielrundeUI():
    random.shuffle(MainWords)

    root = tk.Tk()
    root.title("grid")

    for i in range(5):
        for j in range(5):
            wort = woerter[i * 5 + j]
            label = tk.Label(root, text=wort, width=12, height=3, borderwidth=2, relief="groove")
            label.grid(row=i, column=j, padx=2, pady=2)

    root.mainloop()

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
