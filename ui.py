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
    window = tk.Tk()
    window.title("Codenames")
    label = tk.Label(
        window,
        text=f"Willkommen bei Codenames. Du bist im Team {color}. Deine Rolle in der ersten Runde ist {role}. Viel Spaß!"
    )
    label.pack(padx=20, pady=20)
    window.mainloop()
